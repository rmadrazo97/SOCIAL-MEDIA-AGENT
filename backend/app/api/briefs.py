from uuid import UUID
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import verify_password
from app.models.models import DailyBrief, Post, PostMetric, AccountBaseline, Account
from app.schemas.schemas import DailyBriefOut
from app.services.ai_service import ai_service

router = APIRouter(prefix="/api", tags=["briefs"], dependencies=[Depends(verify_password)])


@router.get("/accounts/{account_id}/brief", response_model=DailyBriefOut | None)
async def get_today_brief(account_id: UUID, db: AsyncSession = Depends(get_db)):
    today = date.today()
    result = await db.execute(
        select(DailyBrief).where(
            DailyBrief.account_id == account_id,
            DailyBrief.brief_date == today,
        )
    )
    return result.scalar_one_or_none()


@router.post("/accounts/{account_id}/brief", response_model=DailyBriefOut)
async def generate_brief(account_id: UUID, db: AsyncSession = Depends(get_db)):
    account = await db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

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

    # Collect metrics for recent posts
    post_data = []
    for p in posts:
        result = await db.execute(
            select(PostMetric).where(PostMetric.post_id == p.id).order_by(desc(PostMetric.snapshot_at)).limit(1)
        )
        metric = result.scalar_one_or_none()
        post_data.append({"post": p, "metrics": metric})

    brief_content = await ai_service.generate_daily_brief(account, post_data, baseline)

    today = date.today()
    # Check if exists
    result = await db.execute(
        select(DailyBrief).where(
            DailyBrief.account_id == account_id,
            DailyBrief.brief_date == today,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.content = brief_content["content"]
        existing.metrics_snapshot = brief_content.get("metrics_snapshot")
        await db.commit()
        await db.refresh(existing)
        return existing

    brief = DailyBrief(
        account_id=account_id,
        brief_date=today,
        content=brief_content["content"],
        metrics_snapshot=brief_content.get("metrics_snapshot"),
    )
    db.add(brief)
    await db.commit()
    await db.refresh(brief)
    return brief


@router.get("/accounts/{account_id}/briefs", response_model=list[DailyBriefOut])
async def list_briefs(account_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(DailyBrief)
        .where(DailyBrief.account_id == account_id)
        .order_by(desc(DailyBrief.brief_date))
        .limit(30)
    )
    return result.scalars().all()
