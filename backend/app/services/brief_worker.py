"""
Worker functions for generating briefs and recommendations for all accounts.
Called by the scheduler.
"""
import logging
from datetime import date

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.models import Account, Post, PostMetric, PostInsight, DailyBrief, Recommendation, AccountBaseline
from app.services.ai_service import ai_service

logger = logging.getLogger(__name__)


async def generate_all_briefs() -> int:
    """Generate daily briefs for all active accounts."""
    async with async_session() as db:
        result = await db.execute(
            select(Account).where(Account.status == "active")
        )
        accounts = result.scalars().all()

    count = 0
    for account in accounts:
        try:
            await _generate_brief_for_account(account.id)
            count += 1
        except Exception as e:
            logger.error(f"Brief generation failed for {account.username}: {e}")

    return count


async def _generate_brief_for_account(account_id) -> None:
    """Generate a daily brief for a single account."""
    async with async_session() as db:
        account = await db.get(Account, account_id)
        if not account:
            return

        # Check if today's brief already exists
        today = date.today()
        result = await db.execute(
            select(DailyBrief).where(
                DailyBrief.account_id == account_id,
                DailyBrief.brief_date == today,
            )
        )
        if result.scalar_one_or_none():
            return  # Already generated

        # Get recent posts with metrics
        result = await db.execute(
            select(Post).where(Post.account_id == account_id).order_by(desc(Post.posted_at)).limit(20)
        )
        posts = result.scalars().all()

        # Get baseline
        result = await db.execute(
            select(AccountBaseline)
            .where(AccountBaseline.account_id == account_id)
            .order_by(desc(AccountBaseline.computed_at))
            .limit(1)
        )
        baseline = result.scalar_one_or_none()

        # Collect metrics
        post_data = []
        for p in posts:
            result = await db.execute(
                select(PostMetric).where(PostMetric.post_id == p.id).order_by(desc(PostMetric.snapshot_at)).limit(1)
            )
            metric = result.scalar_one_or_none()
            post_data.append({"post": p, "metrics": metric})

        # Generate
        brief_content = await ai_service.generate_daily_brief(account, post_data, baseline)

        brief = DailyBrief(
            account_id=account_id,
            brief_date=today,
            content=brief_content.get("content", "No brief available."),
            metrics_snapshot=brief_content.get("metrics_snapshot"),
        )
        db.add(brief)
        await db.commit()


async def generate_all_recommendations() -> int:
    """Generate recommendations for all active accounts."""
    async with async_session() as db:
        result = await db.execute(
            select(Account).where(Account.status == "active")
        )
        accounts = result.scalars().all()

    count = 0
    for account in accounts:
        try:
            await _generate_recommendations_for_account(account.id)
            count += 1
        except Exception as e:
            logger.error(f"Recommendation generation failed for {account.username}: {e}")

    return count


async def _generate_recommendations_for_account(account_id) -> None:
    """Generate recommendations for a single account."""
    async with async_session() as db:
        account = await db.get(Account, account_id)
        if not account:
            return

        # Get recent posts with metrics
        result = await db.execute(
            select(Post).where(Post.account_id == account_id).order_by(desc(Post.posted_at)).limit(20)
        )
        posts = result.scalars().all()

        # Get baseline
        result = await db.execute(
            select(AccountBaseline)
            .where(AccountBaseline.account_id == account_id)
            .order_by(desc(AccountBaseline.computed_at))
            .limit(1)
        )
        baseline = result.scalar_one_or_none()

        # Collect metrics + insights
        post_data = []
        for p in posts:
            result = await db.execute(
                select(PostMetric).where(PostMetric.post_id == p.id).order_by(desc(PostMetric.snapshot_at)).limit(1)
            )
            metric = result.scalar_one_or_none()
            insight_result = await db.execute(
                select(PostInsight).where(PostInsight.post_id == p.id).order_by(desc(PostInsight.snapshot_at)).limit(1)
            )
            insight = insight_result.scalar_one_or_none()
            post_data.append({"post": p, "metrics": metric, "insight": insight})

        # Generate recommendations via AI
        recs = await ai_service.generate_recommendations(account, post_data, baseline)

        for rec in recs:
            recommendation = Recommendation(
                account_id=account_id,
                recommendation_type=rec.get("type", "content_idea"),
                title=rec.get("title", "Recommendation"),
                content=rec.get("content", ""),
                priority=rec.get("priority", 3),
                status="pending",
            )
            db.add(recommendation)

        await db.commit()
