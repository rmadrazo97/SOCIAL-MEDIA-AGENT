from uuid import UUID
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import verify_password
from app.models.models import Post, PostMetric, AccountBaseline
from app.schemas.schemas import AccountMetricsSummary, BaselineOut

router = APIRouter(prefix="/api", tags=["metrics"], dependencies=[Depends(verify_password)])


@router.get("/accounts/{account_id}/metrics", response_model=AccountMetricsSummary)
async def get_account_metrics(
    account_id: UUID,
    days: int = Query(default=7, le=90),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Get posts in period
    result = await db.execute(
        select(Post.id).where(Post.account_id == account_id, Post.posted_at >= since)
    )
    post_ids = [row[0] for row in result.all()]

    if not post_ids:
        return AccountMetricsSummary(
            total_views=0, total_likes=0, total_comments=0,
            total_shares=0, total_saves=0, post_count=0,
            avg_engagement_rate=0, top_post_id=None,
        )

    # For each post, get the latest metric snapshot
    totals = {"views": 0, "likes": 0, "comments": 0, "shares": 0, "saves": 0, "engagement_rates": []}
    top_post_id = None
    top_views = 0

    for pid in post_ids:
        result = await db.execute(
            select(PostMetric).where(PostMetric.post_id == pid).order_by(desc(PostMetric.snapshot_at)).limit(1)
        )
        m = result.scalar_one_or_none()
        if m:
            totals["views"] += m.views
            totals["likes"] += m.likes
            totals["comments"] += m.comments
            totals["shares"] += m.shares
            totals["saves"] += m.saves
            totals["engagement_rates"].append(float(m.engagement_rate))
            if m.views > top_views:
                top_views = m.views
                top_post_id = pid

    avg_eng = sum(totals["engagement_rates"]) / len(totals["engagement_rates"]) if totals["engagement_rates"] else 0

    return AccountMetricsSummary(
        total_views=totals["views"],
        total_likes=totals["likes"],
        total_comments=totals["comments"],
        total_shares=totals["shares"],
        total_saves=totals["saves"],
        post_count=len(post_ids),
        avg_engagement_rate=round(avg_eng, 4),
        top_post_id=top_post_id,
    )


@router.get("/accounts/{account_id}/baseline", response_model=BaselineOut | None)
async def get_baseline(account_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AccountBaseline)
        .where(AccountBaseline.account_id == account_id)
        .order_by(desc(AccountBaseline.computed_at))
        .limit(1)
    )
    return result.scalar_one_or_none()
