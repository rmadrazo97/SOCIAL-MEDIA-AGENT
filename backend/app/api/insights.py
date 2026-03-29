from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import verify_password
from app.models.models import Insight, Post, PostMetric, PostComment, PostInsight, AccountBaseline
from app.schemas.schemas import InsightOut
from app.services.ai_service import ai_service

router = APIRouter(prefix="/api", tags=["insights"], dependencies=[Depends(verify_password)])


@router.get("/posts/{post_id}/diagnostic", response_model=InsightOut | None)
async def get_post_diagnostic(post_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Insight)
        .where(Insight.post_id == post_id, Insight.insight_type == "diagnostic")
        .order_by(desc(Insight.created_at))
        .limit(1)
    )
    return result.scalar_one_or_none()


@router.post("/posts/{post_id}/diagnostic", response_model=InsightOut)
async def generate_post_diagnostic(post_id: UUID, db: AsyncSession = Depends(get_db)):
    post = await db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Get latest metrics
    result = await db.execute(
        select(PostMetric).where(PostMetric.post_id == post_id).order_by(desc(PostMetric.snapshot_at)).limit(1)
    )
    metrics = result.scalar_one_or_none()

    # Get baseline
    result = await db.execute(
        select(AccountBaseline)
        .where(AccountBaseline.account_id == post.account_id)
        .order_by(desc(AccountBaseline.computed_at))
        .limit(1)
    )
    baseline = result.scalar_one_or_none()

    # Fetch top comments for analysis
    comments_result = await db.execute(
        select(PostComment)
        .where(PostComment.post_id == post_id)
        .order_by(desc(PostComment.comment_like_count))
        .limit(25)
    )
    comment_rows = comments_result.scalars().all()
    comments_data = [
        {"username": c.username, "text": c.text, "likes": c.comment_like_count}
        for c in comment_rows
    ] if comment_rows else None

    # Fetch latest insights (creator-only analytics)
    insights_result = await db.execute(
        select(PostInsight)
        .where(PostInsight.post_id == post_id)
        .order_by(desc(PostInsight.snapshot_at))
        .limit(1)
    )
    post_insight = insights_result.scalar_one_or_none()

    diagnostic_content = await ai_service.generate_diagnostic(
        post, metrics, baseline, comments=comments_data, insights=post_insight
    )

    insight = Insight(
        post_id=post_id,
        account_id=post.account_id,
        insight_type="diagnostic",
        content=diagnostic_content["summary"],
        metadata_json=diagnostic_content,
    )
    db.add(insight)
    await db.commit()
    await db.refresh(insight)
    return insight


@router.get("/accounts/{account_id}/insights", response_model=list[InsightOut])
async def list_account_insights(account_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Insight)
        .where(Insight.account_id == account_id)
        .order_by(desc(Insight.created_at))
        .limit(50)
    )
    return result.scalars().all()
