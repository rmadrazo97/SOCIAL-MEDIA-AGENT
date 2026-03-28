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
from app.models.models import Account, Post, PostMetric, AccountBaseline
from app.integrations.instagram_scraper import instagram_scraper
from app.integrations.tiktok_scraper import tiktok_scraper
from app.services.baseline_service import compute_baseline

logger = logging.getLogger(__name__)


async def sync_account(account_id: UUID) -> dict:
    """
    Full sync for one account:
    1. Scrape profile (update follower count)
    2. Scrape recent posts
    3. Upsert posts into DB
    4. Snapshot metrics for all scraped posts
    5. Detect new posts
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
            if profile.get("platform_user_id"):
                account.platform_user_id = profile["platform_user_id"]

        # 2. Scrape recent posts
        scraped_posts = await _scrape_posts(account)
        logger.info(f"Scraped {len(scraped_posts)} posts for {account.username}")

        # 3-4. Upsert posts and snapshot metrics
        new_count = 0
        updated_count = 0

        for sp in scraped_posts:
            post, is_new = await _upsert_post(db, account, sp)
            if is_new:
                new_count += 1
            else:
                updated_count += 1

            # Snapshot metrics
            if sp.get("metrics"):
                await _snapshot_metrics(db, post, sp["metrics"])

        await db.commit()

        summary = {
            "account": account.username,
            "platform": account.platform,
            "profile_updated": profile is not None,
            "follower_count": account.follower_count,
            "posts_scraped": len(scraped_posts),
            "new_posts": new_count,
            "updated_posts": updated_count,
        }
        logger.info(f"Sync complete for {account.username}: {summary}")
        return summary


async def sync_all_accounts() -> list[dict]:
    """Sync all active accounts. Called by the scheduler."""
    async with async_session() as db:
        result = await db.execute(
            select(Account).where(Account.status == "active")
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

async def _scrape_profile(account: Account) -> dict | None:
    """Scrape profile data using the appropriate platform scraper."""
    try:
        if account.platform == "instagram":
            return await instagram_scraper.get_profile(account.username)
        elif account.platform == "tiktok":
            return await tiktok_scraper.get_profile(account.username)
    except Exception as e:
        logger.error(f"Profile scrape failed for {account.username}: {e}")
    return None


async def _scrape_posts(account: Account) -> list[dict]:
    """Scrape recent posts using the appropriate platform scraper."""
    try:
        if account.platform == "instagram":
            return await instagram_scraper.get_recent_posts(account.username, limit=20)
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
