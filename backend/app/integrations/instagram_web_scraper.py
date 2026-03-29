"""
Instagram Web Scraper — uses browser session cookies to fetch data via Instagram's web API.
Replaces the instagrapi-based scraper to avoid IP blocking from Docker/datacenter IPs.

Requires INSTAGRAM_SESSION_ID and INSTAGRAM_CSRF_TOKEN in .env (from browser cookies).
"""
import asyncio
import logging
import os
import random
import re
from datetime import datetime, timezone
from pathlib import Path

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Instagram web app ID (constant, used by the browser)
IG_APP_ID = "936619743392459"


class InstagramWebScraper:
    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    def _get_cookies(self) -> dict:
        return {
            "sessionid": settings.INSTAGRAM_SESSION_ID,
            "csrftoken": settings.INSTAGRAM_CSRF_TOKEN,
            "ds_user_id": self._extract_user_id_from_session(),
        }

    def _extract_user_id_from_session(self) -> str:
        """Extract ds_user_id from sessionid cookie (format: userid%3A...)."""
        sid = settings.INSTAGRAM_SESSION_ID
        if "%3A" in sid:
            return sid.split("%3A")[0]
        if ":" in sid:
            return sid.split(":")[0]
        return ""

    def _get_headers(self, referer: str = "https://www.instagram.com/") -> dict:
        return {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "X-CSRFToken": settings.INSTAGRAM_CSRF_TOKEN,
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

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                cookies=self._get_cookies(),
                timeout=15,
                follow_redirects=True,
                max_redirects=5,
            )
        return self._client

    async def _delay(self, min_s: int | None = None, max_s: int | None = None):
        """Human-like random delay between requests."""
        lo = min_s or settings.INSTAGRAM_SYNC_DELAY_MIN
        hi = max_s or settings.INSTAGRAM_SYNC_DELAY_MAX
        delay = random.uniform(lo, hi)
        await asyncio.sleep(delay)

    async def _safe_get(self, url: str, params: dict | None = None, referer: str | None = None) -> httpx.Response | None:
        """Make a GET request with error handling for rate limits and redirects."""
        try:
            client = await self._get_client()
            headers = self._get_headers(referer or "https://www.instagram.com/")
            r = await client.get(url, params=params, headers=headers)
            if r.status_code == 429:
                logger.warning(f"Rate limited on {url}, backing off")
                await self._delay(10, 20)
                return None
            if r.status_code != 200:
                logger.warning(f"HTTP {r.status_code} on {url}")
                return None
            return r
        except httpx.TooManyRedirects:
            logger.warning(f"Redirect loop on {url}, session may need refresh")
            return None
        except Exception as e:
            logger.error(f"Request failed for {url}: {e}")
            return None

    def is_configured(self) -> bool:
        return bool(settings.INSTAGRAM_SESSION_ID and settings.INSTAGRAM_CSRF_TOKEN)

    async def validate_session(self) -> bool:
        """Check if the current session cookies are still valid."""
        if not self.is_configured():
            return False
        try:
            client = await self._get_client()
            ds_user_id = self._extract_user_id_from_session()
            r = await client.get(
                f"https://www.instagram.com/api/v1/users/{ds_user_id}/info/",
                headers=self._get_headers(),
            )
            return r.status_code == 200
        except Exception as e:
            logger.error(f"Session validation failed: {e}")
            return False

    # ──────────────────────────────────────────────
    # Profile
    # ──────────────────────────────────────────────

    async def get_profile(self, username: str, user_id: str | None = None) -> dict | None:
        """Fetch profile info for an Instagram user."""
        username = username.lstrip("@")
        if not self.is_configured():
            logger.warning("Instagram web session not configured")
            return None

        try:
            # Resolve user_id if not provided
            if not user_id:
                user_id = await self._resolve_user_id(username)
            if not user_id:
                return None

            r = await self._safe_get(
                f"https://www.instagram.com/api/v1/users/{user_id}/info/",
                referer=f"https://www.instagram.com/{username}/",
            )
            if not r:
                return None

            data = r.json()
            user = data.get("user", {})

            return {
                "username": user.get("username"),
                "full_name": user.get("full_name"),
                "biography": user.get("biography", ""),
                "follower_count": user.get("follower_count", 0),
                "following_count": user.get("following_count", 0),
                "post_count": user.get("media_count", 0),
                "profile_pic_url": user.get("profile_pic_url", ""),
                "is_private": user.get("is_private", False),
                "is_business": user.get("is_business", False),
                "category": user.get("category", ""),
                "platform_user_id": str(user.get("pk", "")),
            }

        except Exception as e:
            logger.error(f"Profile fetch failed for {username}: {e}")
            return None

    async def _resolve_user_id(self, username: str) -> str | None:
        """Resolve a username to a numeric user ID."""
        try:
            # Primary: web_profile_info API
            r = await self._safe_get(
                "https://www.instagram.com/api/v1/users/web_profile_info/",
                params={"username": username},
                referer=f"https://www.instagram.com/{username}/",
            )
            if r:
                data = r.json()
                uid = data.get("data", {}).get("user", {}).get("id")
                if uid:
                    return uid

            # Fallback: load profile HTML and extract user ID
            logger.info(f"Trying HTML fallback to resolve user ID for {username}")
            await self._delay(2, 4)

            try:
                client = await self._get_client()
                html_headers = {
                    "User-Agent": self._get_headers()["User-Agent"],
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                }
                r2 = await client.get(
                    f"https://www.instagram.com/{username}/",
                    headers=html_headers,
                )
                if r2.status_code == 200:
                    match = re.search(r'"profilePage_(\d+)"', r2.text)
                    if match:
                        return match.group(1)
                    match = re.search(r'"user_id"\s*:\s*"(\d+)"', r2.text)
                    if match:
                        return match.group(1)
            except httpx.TooManyRedirects:
                logger.warning(f"Redirect loop loading profile HTML for {username}")

            logger.error(f"Could not resolve user ID for {username}")
            return None
        except Exception as e:
            logger.error(f"User ID resolution failed for {username}: {e}")
            return None

    # ──────────────────────────────────────────────
    # Posts (Feed)
    # ──────────────────────────────────────────────

    async def get_recent_posts(
        self,
        username: str,
        user_id: str | None = None,
        limit: int = 50,
        known_post_ids: set[str] | None = None,
    ) -> list[dict]:
        """
        Fetch posts from a user's feed with pagination.

        Args:
            username: Instagram username
            user_id: Numeric user ID (resolved if not provided)
            limit: Max posts to fetch
            known_post_ids: Set of platform_post_ids already in DB.
                            Stops pagination when a known post is encountered.
        """
        username = username.lstrip("@")
        if not self.is_configured():
            return []

        if not user_id:
            user_id = await self._resolve_user_id(username)
            if not user_id:
                logger.error(f"Could not resolve user ID for {username}")
                return []

        posts = []
        max_id = ""
        stop = False

        while len(posts) < limit and not stop:
            try:
                params = {"count": 12}
                if max_id:
                    params["max_id"] = max_id

                r = await self._safe_get(
                    f"https://www.instagram.com/api/v1/feed/user/{user_id}/",
                    params=params,
                    referer=f"https://www.instagram.com/{username}/",
                )

                if not r:
                    break

                data = r.json()
                items = data.get("items", [])

                # Some responses use profile_grid_items instead of items
                if not items:
                    grid_items = data.get("profile_grid_items") or []
                    items = [gi.get("media", gi) for gi in grid_items if gi.get("media") or gi.get("pk")]

                if not items:
                    logger.info(f"No more items in feed for {username}")
                    break

                for item in items:
                    post_data = self._parse_feed_item(item, username)
                    if not post_data:
                        continue

                    # Progressive sync: stop if we hit a known post
                    if known_post_ids and post_data["platform_post_id"] in known_post_ids:
                        logger.info(f"Hit known post {post_data['platform_post_id']}, stopping pagination")
                        stop = True
                        break

                    posts.append(post_data)
                    if len(posts) >= limit:
                        break

                more = data.get("more_available", False)
                max_id = data.get("next_max_id", "")
                # Also check profile_grid_items_cursor
                if not max_id:
                    max_id = data.get("profile_grid_items_cursor", "")

                if not more and not max_id:
                    break

                # Human-like delay between pages
                await self._delay(4, 8)

            except Exception as e:
                logger.error(f"Feed pagination error: {e}")
                break

        logger.info(f"Fetched {len(posts)} posts for {username}")
        return posts

    def _parse_feed_item(self, item: dict, username: str) -> dict | None:
        """Parse a single feed item into our post format."""
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
            posted_at = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat() if ts else datetime.now(timezone.utc).isoformat()

            # Get thumbnail URL (best resolution)
            image_candidates = item.get("image_versions2", {}).get("candidates", [])
            media_url = ""
            if image_candidates:
                best = max(image_candidates, key=lambda c: c.get("width", 0) * c.get("height", 0))
                media_url = best.get("url", "")

            # Location
            location = item.get("location")
            location_name = location.get("name", "") if location else None

            # Tagged users
            usertags = item.get("usertags", {}).get("in", [])
            tagged_users = [t.get("user", {}).get("username", "") for t in usertags if t.get("user", {}).get("username")]

            # Carousel info
            carousel_media = item.get("carousel_media", [])
            carousel_count = len(carousel_media)

            # Video duration
            video_duration = item.get("video_duration") if post_type in ("reel", "video") else None

            # Collect media URLs for download
            media_items = []
            if carousel_media:
                for i, slide in enumerate(carousel_media):
                    slide_type = "image" if slide.get("media_type") == 1 else "video"
                    imgs = slide.get("image_versions2", {}).get("candidates", [])
                    img_url = max(imgs, key=lambda c: c.get("width", 0) * c.get("height", 0))["url"] if imgs else ""
                    vid_url = ""
                    if slide_type == "video":
                        vids = slide.get("video_versions", [])
                        if vids:
                            vid_url = max(vids, key=lambda v: v.get("width", 0) * v.get("height", 0))["url"]
                    media_items.append({"type": slide_type, "image_url": img_url, "video_url": vid_url, "index": i})
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
                "carousel_count": carousel_count,
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
            logger.error(f"Failed to parse feed item: {e}")
            return None

    # ──────────────────────────────────────────────
    # Post Detail
    # ──────────────────────────────────────────────

    async def get_post_detail(self, media_pk: str) -> dict | None:
        """Fetch full detail for a single post by its media PK."""
        if not self.is_configured():
            return None
        try:
            r = await self._safe_get(f"https://www.instagram.com/api/v1/media/{media_pk}/info/")
            if not r:
                return None
            data = r.json()
            items = data.get("items", [])
            if items:
                return items[0]
            return None
        except Exception as e:
            logger.error(f"Post detail fetch failed for {media_pk}: {e}")
            return None

    # ──────────────────────────────────────────────
    # Post Insights (creator-only)
    # ──────────────────────────────────────────────

    async def get_post_insights(self, media_pk: str) -> dict | None:
        """
        Fetch creator-only insights for a post (reach, impressions, sources, etc.).
        Only works for posts owned by the session user.
        Uses Instagram's private API: /api/v1/insights/media_organic_insights/{media_pk}/
        """
        if not self.is_configured():
            return None

        try:
            r = await self._safe_get(
                f"https://www.instagram.com/api/v1/insights/media_organic_insights/{media_pk}/",
                params={"ig_filters": "{}"},
                referer=f"https://www.instagram.com/",
            )
            if not r:
                return None

            data = r.json()
            return self._parse_insights_response(data)

        except Exception as e:
            logger.debug(f"Insights not available for media {media_pk}: {e}")
            return None

    def _parse_insights_response(self, data: dict) -> dict | None:
        """
        Parse the insights API response into a flat dict.
        The response structure varies but typically contains metrics as a list of
        metric objects with name/value/description fields.
        """
        try:
            result = {
                "accounts_reached": 0,
                "reach_follower_pct": None,
                "reach_non_follower_pct": None,
                "impressions": 0,
                "from_home": 0,
                "from_profile": 0,
                "from_hashtags": 0,
                "from_explore": 0,
                "from_other": 0,
                "total_interactions": 0,
                "interaction_follower_pct": None,
                "saves": 0,
                "shares": 0,
                "profile_visits": 0,
                "follows": 0,
            }

            # Try parsing the organic insights format
            metrics = data.get("media_organic_insights", data)

            # Handle list-of-metric-objects format
            if isinstance(metrics, dict):
                metric_list = metrics.get("metrics", [])
                if isinstance(metric_list, list):
                    for m in metric_list:
                        name = m.get("name", "")
                        value = m.get("value", 0)

                        if name == "reach":
                            result["accounts_reached"] = value if isinstance(value, int) else 0
                            # Check for follower/non-follower breakdown
                            breakdown = m.get("inline_insights_node", {})
                            if breakdown:
                                follower_pct = breakdown.get("metrics", {}).get("follower_percentage", {}).get("value")
                                if follower_pct is not None:
                                    result["reach_follower_pct"] = float(follower_pct)
                                    result["reach_non_follower_pct"] = round(100.0 - float(follower_pct), 2)
                        elif name == "impressions":
                            result["impressions"] = value if isinstance(value, int) else 0
                            # Source breakdown
                            breakdown = m.get("inline_insights_node", {}).get("metrics", {})
                            if breakdown:
                                for source_key, dest_key in [
                                    ("impression_source_home", "from_home"),
                                    ("impression_source_feed", "from_home"),
                                    ("impression_source_profile", "from_profile"),
                                    ("impression_source_hashtag", "from_hashtags"),
                                    ("impression_source_explore", "from_explore"),
                                    ("impression_source_other", "from_other"),
                                    ("impression_source_location", "from_other"),
                                ]:
                                    source_val = breakdown.get(source_key, {})
                                    if isinstance(source_val, dict):
                                        result[dest_key] += source_val.get("value", 0)
                                    elif isinstance(source_val, int):
                                        result[dest_key] += source_val
                        elif name in ("total_interactions", "actions"):
                            result["total_interactions"] = value if isinstance(value, int) else 0
                            breakdown = m.get("inline_insights_node", {})
                            if breakdown:
                                follower_pct = breakdown.get("metrics", {}).get("follower_percentage", {}).get("value")
                                if follower_pct is not None:
                                    result["interaction_follower_pct"] = float(follower_pct)
                        elif name == "saved":
                            result["saves"] = value if isinstance(value, int) else 0
                        elif name == "shares":
                            result["shares"] = value if isinstance(value, int) else 0
                        elif name == "profile_visits":
                            result["profile_visits"] = value if isinstance(value, int) else 0
                        elif name == "follows":
                            result["follows"] = value if isinstance(value, int) else 0

                # Also try flat-dict format (alternative response shape)
                if not metric_list:
                    for key_map in [
                        ("reach", "accounts_reached"),
                        ("impressions", "impressions"),
                        ("saved", "saves"),
                        ("shares", "shares"),
                        ("profile_visits", "profile_visits"),
                        ("follows", "follows"),
                    ]:
                        src, dst = key_map
                        val = metrics.get(src)
                        if isinstance(val, int):
                            result[dst] = val
                        elif isinstance(val, dict):
                            result[dst] = val.get("value", 0)

            # Only return if we got meaningful data
            if result["accounts_reached"] > 0 or result["impressions"] > 0:
                return result

            return None

        except Exception as e:
            logger.error(f"Failed to parse insights response: {e}")
            return None

    # ──────────────────────────────────────────────
    # Comments
    # ──────────────────────────────────────────────

    async def get_post_comments(self, media_pk: str, limit: int = 50) -> list[dict]:
        """Fetch comments for a post."""
        if not self.is_configured():
            return []
        try:
            r = await self._safe_get(
                f"https://www.instagram.com/api/v1/media/{media_pk}/comments/",
                params={"can_support_threading": "true", "permalink_enabled": "false"},
            )
            if not r:
                return []

            data = r.json()
            raw_comments = data.get("comments", [])

            comments = []
            for c in raw_comments[:limit]:
                ts = c.get("created_at", 0)
                comments.append({
                    "platform_comment_id": str(c.get("pk", "")),
                    "username": c.get("user", {}).get("username", ""),
                    "text": c.get("text", ""),
                    "comment_like_count": c.get("comment_like_count", 0),
                    "reply_count": c.get("child_comment_count", 0),
                    "commented_at": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat() if ts else datetime.now(timezone.utc).isoformat(),
                })

            return comments
        except Exception as e:
            logger.error(f"Comments fetch failed for {media_pk}: {e}")
            return []

    # ──────────────────────────────────────────────
    # Media Download
    # ──────────────────────────────────────────────

    async def download_media(
        self,
        media_items: list[dict],
        account_username: str,
        platform_post_id: str,
    ) -> bool:
        """
        Download media files for a post to local storage.

        Args:
            media_items: List of {"type": "image"|"video", "image_url": ..., "video_url": ...}
            account_username: For directory naming
            platform_post_id: For directory naming

        Returns True if all downloads succeeded.
        """
        media_dir = Path(settings.INSTAGRAM_MEDIA_DIR) / account_username / platform_post_id
        media_dir.mkdir(parents=True, exist_ok=True)

        success = True
        for item in media_items:
            try:
                idx = item.get("index", 0)

                # Download image
                if item.get("image_url"):
                    img_path = media_dir / f"image_{idx}.jpg"
                    if not img_path.exists():
                        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as dl:
                            r = await dl.get(item["image_url"])
                            if r.status_code == 200:
                                img_path.write_bytes(r.content)
                            else:
                                logger.warning(f"Image download failed: HTTP {r.status_code}")
                                success = False
                        await self._delay(1, 3)

                # Download video
                if item.get("video_url"):
                    vid_path = media_dir / f"video_{idx}.mp4"
                    if not vid_path.exists():
                        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as dl:
                            r = await dl.get(item["video_url"])
                            if r.status_code == 200:
                                vid_path.write_bytes(r.content)
                            else:
                                logger.warning(f"Video download failed: HTTP {r.status_code}")
                                success = False
                        await self._delay(1, 3)

            except Exception as e:
                logger.error(f"Media download error for {platform_post_id} item {idx}: {e}")
                success = False

        return success

    def get_media_path(self, account_username: str, platform_post_id: str) -> Path:
        """Get the local media directory for a post."""
        return Path(settings.INSTAGRAM_MEDIA_DIR) / account_username / platform_post_id

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


instagram_web_scraper = InstagramWebScraper()
