"""
Instagram scraper using instagrapi (Instagram private mobile API).
Requires a real Instagram account to authenticate.
Session is persisted to avoid re-login on every restart.
"""
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

SESSION_FILE = "/app/ig_session.json"

try:
    from instagrapi import Client as InstaClient
    from instagrapi.exceptions import LoginRequired, ChallengeRequired
    instagrapi_available = True
except ImportError:
    instagrapi_available = False
    logger.warning("instagrapi not installed, Instagram scraping unavailable")


class InstagramScraper:
    def __init__(self):
        self._client = None
        self._logged_in = False

    def _get_client(self) -> "InstaClient | None":
        """Get or create an authenticated instagrapi client."""
        if not instagrapi_available:
            return None

        if self._client and self._logged_in:
            return self._client

        if not settings.INSTAGRAM_USERNAME or not settings.INSTAGRAM_PASSWORD:
            logger.warning("Instagram credentials not configured. Set INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD in .env")
            return None

        self._client = InstaClient()
        self._client.delay_range = [2, 5]  # Rate limit protection

        # Try to restore session
        if os.path.exists(SESSION_FILE):
            try:
                self._client.load_settings(SESSION_FILE)
                self._client.login(settings.INSTAGRAM_USERNAME, settings.INSTAGRAM_PASSWORD)
                self._client.get_timeline_feed()  # Test if session is valid
                self._logged_in = True
                logger.info("Instagram session restored from file")
                return self._client
            except Exception as e:
                logger.warning(f"Session restore failed, doing fresh login: {e}")

        # Fresh login
        try:
            self._client.login(settings.INSTAGRAM_USERNAME, settings.INSTAGRAM_PASSWORD)
            self._client.dump_settings(SESSION_FILE)
            self._logged_in = True
            logger.info(f"Instagram login successful as {settings.INSTAGRAM_USERNAME}")
            return self._client
        except ChallengeRequired:
            logger.error("Instagram challenge required (2FA/verification). Please login manually first.")
            return None
        except Exception as e:
            logger.error(f"Instagram login failed: {e}")
            return None

    async def get_profile(self, username: str) -> dict | None:
        """Fetch profile info for any public Instagram user."""
        username = username.lstrip("@")
        client = self._get_client()
        if not client:
            return None

        try:
            user_info = client.user_info_by_username(username)
            return {
                "username": user_info.username,
                "full_name": user_info.full_name,
                "biography": user_info.biography,
                "follower_count": user_info.follower_count,
                "following_count": user_info.following_count,
                "post_count": user_info.media_count,
                "profile_pic_url": str(user_info.profile_pic_url),
                "is_private": user_info.is_private,
                "platform_user_id": str(user_info.pk),
            }
        except LoginRequired:
            self._logged_in = False
            logger.error("Instagram session expired, will re-login on next sync")
            return None
        except Exception as e:
            logger.error(f"Instagram profile fetch failed for {username}: {e}")
            return None

    async def get_recent_posts(self, username: str, limit: int = 20) -> list[dict]:
        """Fetch recent posts with full metrics."""
        username = username.lstrip("@")
        client = self._get_client()
        if not client:
            return []

        try:
            user_id = client.user_id_from_username(username)
            medias = client.user_medias(user_id, amount=limit)

            posts = []
            for media in medias:
                # Determine post type
                media_type = media.media_type
                if media_type == 1:
                    post_type = "image"
                elif media_type == 2:
                    if media.product_type == "clips":
                        post_type = "reel"
                    else:
                        post_type = "video"
                elif media_type == 8:
                    post_type = "carousel"
                else:
                    post_type = "image"

                # Get metrics
                views = media.view_count or 0
                likes = media.like_count or 0
                comments = media.comment_count or 0

                # Build permalink
                permalink = f"https://www.instagram.com/p/{media.code}/" if media.code else ""

                posts.append({
                    "platform_post_id": str(media.pk),
                    "platform": "instagram",
                    "post_type": post_type,
                    "caption": media.caption_text or "",
                    "media_url": str(media.thumbnail_url or ""),
                    "permalink": permalink,
                    "posted_at": media.taken_at.isoformat() if media.taken_at else datetime.now(timezone.utc).isoformat(),
                    "metrics": {
                        "views": views,
                        "likes": likes,
                        "comments": comments,
                        "shares": 0,  # Not available via private API
                        "saves": 0,   # Available via insights (own posts only)
                        "reach": 0,
                    },
                })

            return posts

        except LoginRequired:
            self._logged_in = False
            logger.error("Instagram session expired")
            return []
        except Exception as e:
            logger.error(f"Instagram posts fetch failed for {username}: {e}")
            return []

    async def get_post_insights(self, media_pk: str) -> dict | None:
        """Get insights for your own posts (only works for posts on the logged-in account)."""
        client = self._get_client()
        if not client:
            return None

        try:
            insights = client.insights_media(int(media_pk))
            return {
                "impressions": insights.get("impressions", 0),
                "reach": insights.get("reach", 0),
                "saves": insights.get("saved", 0),
                "shares": insights.get("shares", 0),
            }
        except Exception as e:
            logger.debug(f"Insights not available for media {media_pk}: {e}")
            return None


instagram_scraper = InstagramScraper()
