"""
TikTok scraper using httpx for public profile data.

Strategy:
1. Try HTML extraction (SIGI_STATE / UNIVERSAL_DATA) — works from residential IPs
2. Fall back to oembed API for basic profile info — always works (no video metrics)

Note: TikTok aggressively blocks datacenter IPs. If running in Docker/cloud,
consider configuring TIKTOK_PROXY in .env with a residential proxy.
"""
import json
import logging
import re
from datetime import datetime, timezone

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
}


def _get_proxy() -> str | None:
    """Get proxy URL from settings if configured."""
    proxy = getattr(settings, "TIKTOK_PROXY", None)
    return proxy if proxy else None


def _extract_state(html: str) -> dict | None:
    """Extract embedded JSON data from TikTok HTML."""
    for pattern in [
        r'<script\s+id="SIGI_STATE"[^>]*>(.+?)</script>',
        r'<script\s+id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.+?)</script>',
    ]:
        match = re.search(pattern, html, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                # UNIVERSAL_DATA wraps in __DEFAULT_SCOPE__
                if "__DEFAULT_SCOPE__" in data:
                    return data["__DEFAULT_SCOPE__"]
                return data
            except json.JSONDecodeError:
                continue
    return None


def _parse_user_from_state(state: dict) -> tuple[dict, dict]:
    """Extract user info and stats from state dict."""
    # SIGI_STATE format
    user_module = state.get("UserModule", {})
    if user_module.get("users"):
        username = next(iter(user_module["users"]))
        return user_module["users"][username], user_module.get("stats", {}).get(username, {})

    # UNIVERSAL_DATA format
    user_detail = state.get("webapp.user-detail", {})
    user_info = user_detail.get("userInfo", {})
    if user_info:
        return user_info.get("user", {}), user_info.get("stats", {})

    return {}, {}


def _parse_videos_from_state(state: dict) -> list[dict]:
    """Extract video items from state dict."""
    # SIGI_STATE format
    item_module = state.get("ItemModule", {})
    if item_module:
        return list(item_module.values())

    # UNIVERSAL_DATA format — items in user-detail
    user_detail = state.get("webapp.user-detail", {})
    user_info = user_detail.get("userInfo", {})
    items = user_info.get("itemList", [])
    if items:
        return items

    return []


class TikTokScraper:

    async def _fetch_page(self, username: str) -> str | None:
        """Fetch TikTok profile page HTML."""
        proxy = _get_proxy()
        async with httpx.AsyncClient(
            headers=_HEADERS,
            follow_redirects=True,
            timeout=20.0,
            proxy=proxy,
        ) as client:
            resp = await client.get(f"https://www.tiktok.com/@{username}")
            resp.raise_for_status()
            return resp.text

    async def get_profile(self, username: str) -> dict | None:
        """Fetch public profile info for a TikTok user."""
        username = username.lstrip("@")
        logger.info(f"Scraping TikTok profile: {username}")

        try:
            html = await self._fetch_page(username)
            if not html:
                return None

            state = _extract_state(html)
            if state:
                user_data, stats_data = _parse_user_from_state(state)
                if user_data:
                    return {
                        "username": user_data.get("uniqueId", username),
                        "full_name": user_data.get("nickname", ""),
                        "biography": user_data.get("signature", ""),
                        "follower_count": stats_data.get("followerCount", 0),
                        "following_count": stats_data.get("followingCount", 0),
                        "post_count": stats_data.get("videoCount", 0),
                        "likes_count": stats_data.get("heartCount", 0),
                        "profile_pic_url": user_data.get("avatarLarger", ""),
                        "is_private": user_data.get("privateAccount", False),
                        "platform_user_id": user_data.get("id"),
                    }

            # Fallback: oembed API (limited data but always works)
            logger.info(f"Falling back to oembed for {username}")
            return await self._get_profile_oembed(username)

        except httpx.HTTPStatusError as e:
            logger.error(f"TikTok HTTP error for {username}: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"TikTok profile fetch failed for {username}: {e}")
            return None

    async def _get_profile_oembed(self, username: str) -> dict | None:
        """Fallback: get basic profile info from oembed API."""
        try:
            async with httpx.AsyncClient(
                headers={"User-Agent": _HEADERS["User-Agent"]},
                follow_redirects=True,
                timeout=15.0,
            ) as client:
                resp = await client.get(
                    "https://www.tiktok.com/oembed",
                    params={"url": f"https://www.tiktok.com/@{username}"},
                )
                resp.raise_for_status()
                data = resp.json()

                return {
                    "username": username,
                    "full_name": data.get("author_name", ""),
                    "biography": "",
                    "follower_count": 0,  # oembed doesn't provide stats
                    "following_count": 0,
                    "post_count": 0,
                    "likes_count": 0,
                    "profile_pic_url": data.get("thumbnail_url", ""),
                    "is_private": False,
                    "platform_user_id": None,
                }
        except Exception as e:
            logger.error(f"TikTok oembed fallback failed for {username}: {e}")
            return None

    async def get_recent_videos(self, username: str, limit: int = 20) -> list[dict]:
        """Fetch recent videos from a public TikTok profile."""
        username = username.lstrip("@")
        logger.info(f"Scraping TikTok videos: {username}")

        try:
            html = await self._fetch_page(username)
            if not html:
                return []

            state = _extract_state(html)
            if not state:
                logger.warning(
                    f"Could not extract video data for {username}. "
                    "TikTok may be blocking datacenter IPs. "
                    "Consider setting TIKTOK_PROXY in .env."
                )
                return []

            items = _parse_videos_from_state(state)
            videos = []

            for item in items[:limit]:
                try:
                    vid_id = item.get("id", "")
                    desc = item.get("desc", "")
                    create_time = item.get("createTime", 0)
                    stats = item.get("stats", {})
                    video_info = item.get("video", {})

                    if isinstance(create_time, str):
                        create_time = int(create_time) if create_time.isdigit() else 0

                    posted_at = (
                        datetime.fromtimestamp(create_time, tz=timezone.utc)
                        if create_time
                        else datetime.now(timezone.utc)
                    )

                    videos.append({
                        "platform_post_id": str(vid_id),
                        "platform": "tiktok",
                        "post_type": "video",
                        "caption": desc,
                        "media_url": video_info.get("cover", "") if isinstance(video_info, dict) else "",
                        "permalink": f"https://www.tiktok.com/@{username}/video/{vid_id}",
                        "posted_at": posted_at.isoformat(),
                        "metrics": {
                            "views": stats.get("playCount", 0) if isinstance(stats, dict) else 0,
                            "likes": (stats.get("diggCount", 0) or stats.get("likeCount", 0)) if isinstance(stats, dict) else 0,
                            "comments": stats.get("commentCount", 0) if isinstance(stats, dict) else 0,
                            "shares": stats.get("shareCount", 0) if isinstance(stats, dict) else 0,
                            "saves": (stats.get("collectCount", 0) or stats.get("saveCount", 0)) if isinstance(stats, dict) else 0,
                            "reach": 0,
                        },
                    })
                except Exception as e:
                    logger.warning(f"Failed to parse video: {e}")
                    continue

            return videos

        except Exception as e:
            logger.error(f"TikTok videos fetch failed for {username}: {e}")
            return []


tiktok_scraper = TikTokScraper()
