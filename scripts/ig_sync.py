#!/usr/bin/env python3
"""
Instagram Sync Worker — runs on the HOST machine (not Docker) to use
the browser's residential IP for Instagram API calls.

Usage:
    python scripts/ig_sync.py                    # Sync all Instagram accounts
    python scripts/ig_sync.py --username alexmadrazo97  # Sync specific account

This script:
1. Fetches data from Instagram using browser session cookies
2. Pushes the data to the backend API running in Docker
"""
import argparse
import asyncio
import json
import logging
import os
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

# Load .env from project root
PROJECT_ROOT = Path(__file__).parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

def load_env():
    """Load environment variables from .env file."""
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())

load_env()

# Configuration
INSTAGRAM_SESSION_ID = os.environ.get("INSTAGRAM_SESSION_ID", "")
INSTAGRAM_CSRF_TOKEN = os.environ.get("INSTAGRAM_CSRF_TOKEN", "")
APP_PASSWORD = os.environ.get("APP_PASSWORD", "admin123")
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8001")
MEDIA_DIR = PROJECT_ROOT / "data" / "media"

IG_APP_ID = "936619743392459"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("ig_sync")


# ─── Instagram API Client ───────────────────────────────────

def get_cookies():
    return {
        "sessionid": INSTAGRAM_SESSION_ID,
        "csrftoken": INSTAGRAM_CSRF_TOKEN,
        "ds_user_id": INSTAGRAM_SESSION_ID.split("%3A")[0] if "%3A" in INSTAGRAM_SESSION_ID else "",
    }


def get_headers(referer="https://www.instagram.com/"):
    return {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "X-CSRFToken": INSTAGRAM_CSRF_TOKEN,
        "X-IG-App-ID": IG_APP_ID,
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": referer,
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Ch-Ua": '"Chromium";v="131", "Not_A Brand";v="24"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"macOS"',
    }


def delay(min_s=2, max_s=5):
    """Human-like delay."""
    time.sleep(random.uniform(min_s, max_s))


# ─── Backend API Client ─────────────────────────────────────

class BackendClient:
    def __init__(self):
        self.client = httpx.Client(
            base_url=BACKEND_URL,
            headers={"X-App-Password": APP_PASSWORD, "Content-Type": "application/json"},
            timeout=30,
        )

    def get_accounts(self, platform="instagram"):
        r = self.client.get("/api/accounts")
        if r.status_code != 200:
            logger.error(f"Failed to get accounts: {r.status_code}")
            return []
        accounts = r.json()
        return [a for a in accounts if a["platform"] == platform]

    def update_account_profile(self, account_id, profile_data):
        """Update account with profile info via direct DB update through sync."""
        # We'll use the sync status to push data
        pass

    def get_existing_post_ids(self, account_id):
        """Get all platform_post_ids for an account."""
        r = self.client.get(f"/api/accounts/{account_id}/posts", params={"limit": 100})
        posts = r.json()
        return {p["platform_post_id"] for p in posts if p.get("platform_post_id")}

    def push_sync_data(self, account_id, data):
        """Push scraped data to the backend for processing."""
        r = self.client.post(f"/api/accounts/{account_id}/ig-sync-data", json=data)
        return r.json()


# ─── Instagram Fetching ─────────────────────────────────────

def fetch_profile(client, username, user_id=None):
    """Fetch profile info."""
    if user_id:
        r = client.get(
            f"https://www.instagram.com/api/v1/users/{user_id}/info/",
            headers=get_headers(f"https://www.instagram.com/{username}/"),
            cookies=get_cookies(),
        )
        if r.status_code == 200:
            user = r.json().get("user", {})
            return {
                "username": user.get("username"),
                "full_name": user.get("full_name"),
                "biography": user.get("biography", ""),
                "follower_count": user.get("follower_count", 0),
                "following_count": user.get("following_count", 0),
                "post_count": user.get("media_count", 0),
                "profile_pic_url": user.get("profile_pic_url", ""),
                "platform_user_id": str(user.get("pk", "")),
            }

    # Fallback: web_profile_info
    r = client.get(
        "https://www.instagram.com/api/v1/users/web_profile_info/",
        params={"username": username},
        headers=get_headers(f"https://www.instagram.com/{username}/"),
        cookies=get_cookies(),
    )
    if r.status_code == 200:
        user = r.json().get("data", {}).get("user", {})
        return {
            "username": user.get("username"),
            "full_name": user.get("full_name"),
            "biography": user.get("biography", ""),
            "follower_count": user.get("edge_followed_by", {}).get("count", 0),
            "following_count": user.get("edge_follow", {}).get("count", 0),
            "post_count": user.get("edge_owner_to_timeline_media", {}).get("count", 0),
            "profile_pic_url": user.get("profile_pic_url", ""),
            "platform_user_id": user.get("id", ""),
        }

    logger.error(f"Profile fetch failed: HTTP {r.status_code}")
    return None


def fetch_posts(client, username, user_id, limit=50, known_post_ids=None):
    """Fetch posts from feed with pagination."""
    posts = []
    max_id = ""
    stop = False

    while len(posts) < limit and not stop:
        params = {"count": 12}
        if max_id:
            params["max_id"] = max_id

        r = client.get(
            f"https://www.instagram.com/api/v1/feed/user/{user_id}/",
            params=params,
            headers=get_headers(f"https://www.instagram.com/{username}/"),
            cookies=get_cookies(),
        )

        if r.status_code == 429:
            logger.warning("Rate limited, stopping")
            break
        if r.status_code != 200:
            logger.error(f"Feed fetch failed: HTTP {r.status_code}")
            break

        data = r.json()
        items = data.get("items", [])
        if not items:
            break

        for item in items:
            post = parse_feed_item(item, username)
            if not post:
                continue

            if known_post_ids and post["platform_post_id"] in known_post_ids:
                logger.info(f"Hit known post {post['platform_post_id']}, stopping")
                stop = True
                break

            posts.append(post)
            if len(posts) >= limit:
                break

        more = data.get("more_available", False)
        max_id = data.get("next_max_id", "")
        if not more or not max_id:
            break

        delay(4, 8)

    return posts


def parse_feed_item(item, username):
    """Parse a feed item into post data."""
    try:
        media_type = item.get("media_type")
        if media_type == 1:
            post_type = "image"
        elif media_type == 2:
            post_type = "reel" if item.get("product_type") == "clips" else "video"
        elif media_type == 8:
            post_type = "carousel"
        else:
            post_type = "image"

        caption_obj = item.get("caption") or {}
        caption = caption_obj.get("text", "") or ""
        likes = item.get("like_count", 0)
        comments = item.get("comment_count", 0)
        views = item.get("play_count") or item.get("view_count") or 0
        code = item.get("code", "")
        permalink = f"https://www.instagram.com/p/{code}/" if code else ""
        ts = item.get("taken_at", 0)
        posted_at = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat() if ts else None

        # Media URLs
        image_candidates = item.get("image_versions2", {}).get("candidates", [])
        media_url = ""
        if image_candidates:
            best = max(image_candidates, key=lambda c: c.get("width", 0) * c.get("height", 0))
            media_url = best.get("url", "")

        location = item.get("location")
        location_name = location.get("name", "") if location else None

        usertags = item.get("usertags", {}).get("in", [])
        tagged_users = [t.get("user", {}).get("username", "") for t in usertags if t.get("user", {}).get("username")]

        carousel_media = item.get("carousel_media", [])
        video_duration = item.get("video_duration") if post_type in ("reel", "video") else None

        # Collect media items for download
        media_items = []
        if carousel_media:
            for i, slide in enumerate(carousel_media):
                stype = "image" if slide.get("media_type") == 1 else "video"
                imgs = slide.get("image_versions2", {}).get("candidates", [])
                img_url = max(imgs, key=lambda c: c.get("width", 0) * c.get("height", 0))["url"] if imgs else ""
                vid_url = ""
                if stype == "video":
                    vids = slide.get("video_versions", [])
                    if vids:
                        vid_url = max(vids, key=lambda v: v.get("width", 0) * v.get("height", 0))["url"]
                media_items.append({"type": stype, "image_url": img_url, "video_url": vid_url, "index": i})
        elif post_type in ("reel", "video"):
            vids = item.get("video_versions", [])
            vid_url = max(vids, key=lambda v: v.get("width", 0) * v.get("height", 0))["url"] if vids else ""
            media_items.append({"type": "video", "image_url": media_url, "video_url": vid_url, "index": 0})
        else:
            media_items.append({"type": "image", "image_url": media_url, "video_url": "", "index": 0})

        return {
            "platform_post_id": str(item.get("pk", "")),
            "platform": "instagram",
            "post_type": post_type,
            "caption": caption,
            "media_url": media_url,
            "permalink": permalink,
            "posted_at": posted_at,
            "location_name": location_name,
            "tagged_users": tagged_users or None,
            "carousel_count": len(carousel_media),
            "video_duration": video_duration,
            "media_items": media_items,
            "metrics": {
                "views": views,
                "likes": likes,
                "comments": comments,
                "shares": 0,
                "saves": 0,
                "reach": 0,
            },
        }
    except Exception as e:
        logger.error(f"Parse error: {e}")
        return None


def fetch_comments(client, media_pk):
    """Fetch comments for a post."""
    r = client.get(
        f"https://www.instagram.com/api/v1/media/{media_pk}/comments/",
        params={"can_support_threading": "true", "permalink_enabled": "false"},
        headers=get_headers(),
        cookies=get_cookies(),
    )
    if r.status_code != 200:
        return []

    comments = []
    for c in r.json().get("comments", []):
        ts = c.get("created_at", 0)
        comments.append({
            "platform_comment_id": str(c.get("pk", "")),
            "username": c.get("user", {}).get("username", ""),
            "text": c.get("text", ""),
            "comment_like_count": c.get("comment_like_count", 0),
            "reply_count": c.get("child_comment_count", 0),
            "commented_at": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat() if ts else None,
        })
    return comments


def fetch_post_detail(client, media_pk):
    """Fetch detailed info for a single post."""
    r = client.get(
        f"https://www.instagram.com/api/v1/media/{media_pk}/info/",
        headers=get_headers(),
        cookies=get_cookies(),
    )
    if r.status_code == 200:
        items = r.json().get("items", [])
        return items[0] if items else None
    return None


def download_media(client, media_items, username, post_id):
    """Download media files to local storage."""
    media_dir = MEDIA_DIR / username / post_id
    media_dir.mkdir(parents=True, exist_ok=True)

    for item in media_items:
        idx = item.get("index", 0)
        if item.get("image_url"):
            path = media_dir / f"image_{idx}.jpg"
            if not path.exists():
                try:
                    r = client.get(item["image_url"])
                    if r.status_code == 200:
                        path.write_bytes(r.content)
                        logger.debug(f"  Downloaded {path.name} ({len(r.content)//1024}KB)")
                    delay(1, 2)
                except Exception as e:
                    logger.warning(f"  Image download failed: {e}")

        if item.get("video_url"):
            path = media_dir / f"video_{idx}.mp4"
            if not path.exists():
                try:
                    r = client.get(item["video_url"], timeout=60)
                    if r.status_code == 200:
                        path.write_bytes(r.content)
                        logger.debug(f"  Downloaded {path.name} ({len(r.content)//1024}KB)")
                    delay(1, 2)
                except Exception as e:
                    logger.warning(f"  Video download failed: {e}")

    return True


# ─── Main Sync Logic ────────────────────────────────────────

def sync_account(account, backend):
    """Full sync for one Instagram account."""
    username = account["username"]
    account_id = account["id"]
    user_id = account.get("platform_user_id")

    # If no user_id, try to get it from session cookie (works for the logged-in user)
    if not user_id:
        ds_user_id = get_cookies().get("ds_user_id", "")
        if ds_user_id:
            logger.info(f"No user_id stored, using session ds_user_id={ds_user_id}")
            user_id = ds_user_id

    logger.info(f"{'='*50}")
    logger.info(f"Syncing @{username} (user_id={user_id})")

    ig_client = httpx.Client(timeout=15, follow_redirects=True)

    # 1. Profile
    logger.info("Fetching profile...")
    profile = fetch_profile(ig_client, username, user_id)
    if profile:
        logger.info(f"  Followers: {profile['follower_count']}, Posts: {profile['post_count']}")
        if not user_id:
            user_id = profile.get("platform_user_id")
    else:
        logger.warning("  Profile fetch failed")
        if not user_id:
            logger.error("  No user_id available, cannot continue")
            ig_client.close()
            return

    delay(2, 4)

    # 2. Fetch posts
    known_ids = backend.get_existing_post_ids(account_id)
    logger.info(f"Known posts in DB: {len(known_ids)}")
    logger.info("Fetching posts...")

    posts = fetch_posts(ig_client, username, user_id, limit=50, known_post_ids=known_ids)
    logger.info(f"  Fetched {len(posts)} new/updated posts")

    # 3. For each post: download media + fetch comments
    for i, post in enumerate(posts):
        pid = post["platform_post_id"]
        logger.info(f"  Post {i+1}/{len(posts)}: {post['post_type']} | likes={post['metrics']['likes']} | {post.get('permalink', '')}")

        # Download media
        if post.get("media_items"):
            download_media(ig_client, post["media_items"], username, pid)
            post["media_stored"] = True

        # Fetch comments
        delay(2, 4)
        comments = fetch_comments(ig_client, pid)
        post["comments"] = comments
        if comments:
            logger.info(f"    {len(comments)} comments")

        delay(2, 4)

    # 4. Re-fetch metrics for recent existing posts
    logger.info("Re-snapshotting metrics for existing posts...")
    resnapshots = []
    existing_posts_to_check = list(known_ids)[:20]
    for pid in existing_posts_to_check:
        delay(2, 4)
        detail = fetch_post_detail(ig_client, pid)
        if detail:
            resnapshots.append({
                "platform_post_id": pid,
                "metrics": {
                    "views": detail.get("play_count") or detail.get("view_count") or 0,
                    "likes": detail.get("like_count", 0),
                    "comments": detail.get("comment_count", 0),
                    "shares": 0,
                    "saves": 0,
                    "reach": 0,
                },
            })
    logger.info(f"  Re-snapshotted {len(resnapshots)} existing posts")

    ig_client.close()

    # 5. Push everything to backend API
    sync_data = {
        "profile": profile,
        "new_posts": posts,
        "metric_resnapshots": resnapshots,
    }

    logger.info("Pushing data to backend...")
    try:
        result = backend.push_sync_data(account_id, sync_data)
        logger.info(f"  Backend response: {result}")
    except Exception as e:
        logger.error(f"  Backend push failed: {e}")
        # Save to file as backup
        backup_path = PROJECT_ROOT / "data" / f"sync_backup_{username}_{int(time.time())}.json"
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        backup_path.write_text(json.dumps(sync_data, indent=2, default=str))
        logger.info(f"  Saved backup to {backup_path}")


def main():
    parser = argparse.ArgumentParser(description="Instagram Sync Worker")
    parser.add_argument("--username", help="Sync specific account by username")
    args = parser.parse_args()

    if not INSTAGRAM_SESSION_ID or not INSTAGRAM_CSRF_TOKEN:
        logger.error("INSTAGRAM_SESSION_ID and INSTAGRAM_CSRF_TOKEN must be set in .env")
        sys.exit(1)

    backend = BackendClient()

    # Get accounts from backend
    accounts = backend.get_accounts()
    if args.username:
        accounts = [a for a in accounts if a["username"] == args.username]

    if not accounts:
        logger.error("No Instagram accounts found")
        sys.exit(1)

    logger.info(f"Syncing {len(accounts)} Instagram account(s)")

    for account in accounts:
        try:
            sync_account(account, backend)
        except Exception as e:
            logger.error(f"Sync failed for {account['username']}: {e}")

        if len(accounts) > 1:
            delay(10, 15)

    logger.info("Sync complete!")


if __name__ == "__main__":
    main()
