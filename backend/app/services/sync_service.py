"""
Sync service — orchestrates scraping data from platforms and storing it in the DB.
Called by the scheduler and by manual sync triggers.
"""
import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.models import Account, Post, PostMetric, PostComment, ProfileSnapshot, PostInsight
from app.integrations.instagram_web_scraper import instagram_web_scraper
from app.integrations.tiktok_scraper import tiktok_scraper
from app.services.baseline_service import compute_baseline

logger = logging.getLogger(__name__)


async def sync_account(account_id: UUID) -> dict:
    """
    Full sync for one account:
    1. Scrape profile (update follower count, bio, etc.)
    2. Record profile snapshot for growth tracking
    3. Scrape recent posts (progressive — stops at known posts)
    4. Upsert posts into DB
    5. Snapshot metrics for all scraped posts
    6. Re-snapshot metrics for recent existing posts
    7. Download media for new posts
    8. Fetch comments for new posts
    Returns summary of what was synced.
    """
    async with async_session() as db:
        account = await db.get(Account, account_id)
        if not account:
            return {"error": "Account not found"}

        logger.info(f"Syncing account {account.username} ({account.platform})")

        # 1. Scrape profile
        profile = await _scrape_profile(account)
        if profile:
            account.follower_count = profile.get("follower_count", account.follower_count)
            account.following_count = profile.get("following_count", account.following_count)
            account.biography = profile.get("biography", account.biography)
            account.profile_pic_url = profile.get("profile_pic_url", account.profile_pic_url)
            if profile.get("platform_user_id"):
                account.platform_user_id = profile["platform_user_id"]

            # 2. Record profile snapshot
            snapshot = ProfileSnapshot(
                account_id=account.id,
                follower_count=profile.get("follower_count", 0),
                following_count=profile.get("following_count", 0),
                post_count=profile.get("post_count", 0),
            )
            db.add(snapshot)

        # Get known post IDs for progressive sync
        known_post_ids = await _get_known_post_ids(db, account.id)

        # 3. Scrape recent posts
        scraped_posts = await _scrape_posts(account, known_post_ids)
        logger.info(f"Scraped {len(scraped_posts)} posts for {account.username}")

        # 4-5. Upsert posts and snapshot metrics
        new_count = 0
        updated_count = 0
        media_downloaded = 0

        for sp in scraped_posts:
            post, is_new = await _upsert_post(db, account, sp)
            if is_new:
                new_count += 1
            else:
                updated_count += 1

            # Snapshot metrics
            if sp.get("metrics"):
                await _snapshot_metrics(db, post, sp["metrics"])

            # Download media for new posts
            if is_new and account.platform == "instagram" and sp.get("media_items"):
                try:
                    success = await instagram_web_scraper.download_media(
                        sp["media_items"],
                        account.username,
                        sp["platform_post_id"],
                    )
                    if success:
                        post.media_stored = True
                        media_downloaded += 1
                except Exception as e:
                    logger.error(f"Media download failed for post {sp['platform_post_id']}: {e}")

            # Fetch comments for new posts
            if is_new and account.platform == "instagram":
                try:
                    await instagram_web_scraper._delay(2, 4)
                    comments = await instagram_web_scraper.get_post_comments(sp["platform_post_id"])
                    for c in comments:
                        await _upsert_comment(db, post, c)
                except Exception as e:
                    logger.error(f"Comments fetch failed for post {sp['platform_post_id']}: {e}")

        # 6. Re-snapshot metrics for recent existing posts (not just scraped)
        if account.platform == "instagram":
            resnapshot_count = await _resnapshot_existing_posts(db, account)
            logger.info(f"Re-snapshotted metrics for {resnapshot_count} existing posts")

        account.last_sync_at = datetime.now(timezone.utc)
        await db.commit()

        summary = {
            "account": account.username,
            "platform": account.platform,
            "profile_updated": profile is not None,
            "follower_count": account.follower_count,
            "following_count": account.following_count,
            "posts_scraped": len(scraped_posts),
            "new_posts": new_count,
            "updated_posts": updated_count,
            "media_downloaded": media_downloaded,
        }
        logger.info(f"Sync complete for {account.username}: {summary}")
        return summary


async def sync_all_accounts() -> list[dict]:
    """
    Sync all active non-Instagram accounts. Called by the scheduler.
    Instagram accounts are synced via the host-side script (scripts/ig_sync.py)
    because the session cookies are IP-bound to the host machine.
    """
    async with async_session() as db:
        result = await db.execute(
            select(Account).where(
                Account.status == "active",
                Account.platform != "instagram",
            )
        )
        accounts = result.scalars().all()

    summaries = []
    for i, account in enumerate(accounts):
        try:
            summary = await sync_account(account.id)
            summaries.append(summary)
        except Exception as e:
            logger.error(f"Failed to sync account {account.username}: {e}")
            summaries.append({"account": account.username, "error": str(e)})
        # Delay between accounts to avoid rate limits
        if i < len(accounts) - 1:
            await asyncio.sleep(10)

    return summaries


async def compute_all_baselines() -> int:
    """Recompute baselines for all active accounts."""
    async with async_session() as db:
        result = await db.execute(
            select(Account).where(Account.status == "active")
        )
        accounts = result.scalars().all()

    count = 0
    for account in accounts:
        try:
            async with async_session() as db:
                await compute_baseline(account.id, db)
            count += 1
        except Exception as e:
            logger.error(f"Baseline computation failed for {account.username}: {e}")

    return count


# --- Internal helpers ---

async def _get_known_post_ids(db: AsyncSession, account_id: UUID) -> set[str]:
    """Get all platform_post_ids for an account (for progressive sync)."""
    result = await db.execute(
        select(Post.platform_post_id).where(
            Post.account_id == account_id,
            Post.platform_post_id.isnot(None),
        )
    )
    return {row[0] for row in result.all()}


async def _scrape_profile(account: Account) -> dict | None:
    """Scrape profile data using the appropriate platform scraper."""
    try:
        if account.platform == "instagram":
            return await instagram_web_scraper.get_profile(
                account.username,
                user_id=account.platform_user_id,
            )
        elif account.platform == "tiktok":
            return await tiktok_scraper.get_profile(account.username)
    except Exception as e:
        logger.error(f"Profile scrape failed for {account.username}: {e}")
    return None


async def _scrape_posts(account: Account, known_post_ids: set[str] | None = None) -> list[dict]:
    """Scrape recent posts using the appropriate platform scraper."""
    try:
        if account.platform == "instagram":
            return await instagram_web_scraper.get_recent_posts(
                username=account.username,
                user_id=account.platform_user_id,
                limit=50,
                known_post_ids=known_post_ids,
            )
        elif account.platform == "tiktok":
            return await tiktok_scraper.get_recent_videos(account.username, limit=20)
    except Exception as e:
        logger.error(f"Post scrape failed for {account.username}: {e}")
    return []


async def _upsert_post(db: AsyncSession, account: Account, scraped: dict) -> tuple:
    """
    Insert or update a post in the DB.
    Returns (post, is_new).
    """
    platform_post_id = scraped.get("platform_post_id")

    # Check if post already exists
    existing = None
    if platform_post_id:
        result = await db.execute(
            select(Post).where(
                Post.account_id == account.id,
                Post.platform_post_id == platform_post_id,
            )
        )
        existing = result.scalar_one_or_none()

    if existing:
        # Update caption if changed
        if scraped.get("caption") and scraped["caption"] != existing.caption:
            existing.caption = scraped["caption"]
        # Update enriched fields
        if scraped.get("location_name"):
            existing.location_name = scraped["location_name"]
        if scraped.get("tagged_users"):
            existing.tagged_users = scraped["tagged_users"]
        if scraped.get("carousel_count"):
            existing.carousel_count = scraped["carousel_count"]
        if scraped.get("video_duration"):
            existing.video_duration = scraped["video_duration"]
        return existing, False
    else:
        # Parse posted_at
        posted_at = scraped.get("posted_at")
        if isinstance(posted_at, str):
            posted_at = datetime.fromisoformat(posted_at.replace("Z", "+00:00"))

        post = Post(
            account_id=account.id,
            platform_post_id=platform_post_id,
            platform=account.platform,
            post_type=scraped.get("post_type", "image"),
            caption=scraped.get("caption", ""),
            media_url=scraped.get("media_url"),
            permalink=scraped.get("permalink"),
            posted_at=posted_at or datetime.now(timezone.utc),
            location_name=scraped.get("location_name"),
            tagged_users=scraped.get("tagged_users"),
            carousel_count=scraped.get("carousel_count", 0),
            video_duration=scraped.get("video_duration"),
        )
        db.add(post)
        await db.flush()
        return post, True


async def _snapshot_metrics(db: AsyncSession, post: Post, metrics: dict) -> PostMetric:
    """Create a new metric snapshot for a post."""
    total_engagement = (
        metrics.get("likes", 0) +
        metrics.get("comments", 0) +
        metrics.get("shares", 0) +
        metrics.get("saves", 0)
    )
    views = metrics.get("views", 0)
    engagement_rate = round(total_engagement / views, 4) if views > 0 else 0

    metric = PostMetric(
        post_id=post.id,
        views=views,
        likes=metrics.get("likes", 0),
        comments=metrics.get("comments", 0),
        shares=metrics.get("shares", 0),
        saves=metrics.get("saves", 0),
        reach=metrics.get("reach", 0),
        engagement_rate=engagement_rate,
    )
    db.add(metric)
    return metric


async def _upsert_comment(db: AsyncSession, post: Post, comment_data: dict) -> None:
    """Insert or update a comment."""
    platform_comment_id = comment_data.get("platform_comment_id", "")
    if not platform_comment_id:
        return

    result = await db.execute(
        select(PostComment).where(
            PostComment.post_id == post.id,
            PostComment.platform_comment_id == platform_comment_id,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.comment_like_count = comment_data.get("comment_like_count", 0)
        existing.reply_count = comment_data.get("reply_count", 0)
    else:
        commented_at = comment_data.get("commented_at")
        if isinstance(commented_at, str):
            commented_at = datetime.fromisoformat(commented_at.replace("Z", "+00:00"))

        comment = PostComment(
            post_id=post.id,
            platform_comment_id=platform_comment_id,
            username=comment_data.get("username", ""),
            text=comment_data.get("text", ""),
            comment_like_count=comment_data.get("comment_like_count", 0),
            reply_count=comment_data.get("reply_count", 0),
            commented_at=commented_at or datetime.now(timezone.utc),
        )
        db.add(comment)


async def _snapshot_insights(db: AsyncSession, post: Post, insights: dict) -> PostInsight:
    """Create a new insights snapshot for a post."""
    insight = PostInsight(
        post_id=post.id,
        accounts_reached=insights.get("accounts_reached", 0),
        reach_follower_pct=insights.get("reach_follower_pct"),
        reach_non_follower_pct=insights.get("reach_non_follower_pct"),
        impressions=insights.get("impressions", 0),
        from_home=insights.get("from_home", 0),
        from_profile=insights.get("from_profile", 0),
        from_hashtags=insights.get("from_hashtags", 0),
        from_explore=insights.get("from_explore", 0),
        from_other=insights.get("from_other", 0),
        total_interactions=insights.get("total_interactions", 0),
        interaction_follower_pct=insights.get("interaction_follower_pct"),
        saves=insights.get("saves", 0),
        shares=insights.get("shares", 0),
        profile_visits=insights.get("profile_visits", 0),
        follows=insights.get("follows", 0),
    )
    db.add(insight)
    return insight


async def _resnapshot_existing_posts(db: AsyncSession, account: Account, limit: int = 20) -> int:
    """
    Re-fetch metrics for the most recent existing posts to track changes over time.
    This runs after the main post sync to capture metric deltas on older posts.
    """
    if account.platform != "instagram":
        return 0

    result = await db.execute(
        select(Post).where(
            Post.account_id == account.id,
            Post.platform == "instagram",
        ).order_by(desc(Post.posted_at)).limit(limit)
    )
    recent_posts = result.scalars().all()

    count = 0
    for post in recent_posts:
        if not post.platform_post_id:
            continue
        try:
            await instagram_web_scraper._delay(2, 4)
            detail = await instagram_web_scraper.get_post_detail(post.platform_post_id)
            if detail:
                metrics = {
                    "views": detail.get("play_count") or detail.get("view_count") or 0,
                    "likes": detail.get("like_count", 0),
                    "comments": detail.get("comment_count", 0),
                    "shares": 0,
                    "saves": 0,
                    "reach": 0,
                }
                await _snapshot_metrics(db, post, metrics)
                count += 1
        except Exception as e:
            logger.error(f"Re-snapshot failed for post {post.platform_post_id}: {e}")

    return count
