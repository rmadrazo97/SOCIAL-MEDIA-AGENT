"""
API endpoints for profile history and growth tracking.
"""
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import verify_password
from app.models.models import ProfileSnapshot
from app.schemas.schemas import ProfileSnapshotOut

router = APIRouter(prefix="/api", tags=["profile"], dependencies=[Depends(verify_password)])


@router.get("/accounts/{account_id}/profile-history", response_model=list[ProfileSnapshotOut])
async def get_profile_history(
    account_id: UUID,
    limit: int = Query(default=90, le=365),
    db: AsyncSession = Depends(get_db),
):
    """Get historical profile snapshots for growth tracking."""
    result = await db.execute(
        select(ProfileSnapshot)
        .where(ProfileSnapshot.account_id == account_id)
        .order_by(desc(ProfileSnapshot.snapshot_at))
        .limit(limit)
    )
    snapshots = result.scalars().all()
    return list(reversed(snapshots))  # Return chronological order


@router.get("/accounts/{account_id}/growth")
async def get_account_growth(
    account_id: UUID,
    days: int = Query(default=30, le=365),
    db: AsyncSession = Depends(get_db),
):
    """Get growth summary for an account over a period."""
    result = await db.execute(
        select(ProfileSnapshot)
        .where(ProfileSnapshot.account_id == account_id)
        .order_by(ProfileSnapshot.snapshot_at)
    )
    snapshots = result.scalars().all()

    if not snapshots:
        return {"error": "No profile data yet. Sync the account first."}

    latest = snapshots[-1]
    # Find the snapshot closest to `days` ago
    earliest = snapshots[0]
    for s in snapshots:
        diff = (latest.snapshot_at - s.snapshot_at).days
        if diff <= days:
            earliest = s
            break

    follower_delta = latest.follower_count - earliest.follower_count
    following_delta = latest.following_count - earliest.following_count
    post_delta = latest.post_count - earliest.post_count
    period_days = max((latest.snapshot_at - earliest.snapshot_at).days, 1)

    return {
        "period_days": period_days,
        "current": {
            "followers": latest.follower_count,
            "following": latest.following_count,
            "posts": latest.post_count,
        },
        "previous": {
            "followers": earliest.follower_count,
            "following": earliest.following_count,
            "posts": earliest.post_count,
        },
        "delta": {
            "followers": follower_delta,
            "following": following_delta,
            "posts": post_delta,
        },
        "daily_avg": {
            "followers": round(follower_delta / period_days, 2),
            "posts": round(post_delta / period_days, 2),
        },
    }
