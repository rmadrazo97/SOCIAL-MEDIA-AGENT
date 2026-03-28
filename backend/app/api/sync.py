"""
API endpoints for triggering manual syncs and viewing sync status.
"""
from uuid import UUID
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import verify_password
from app.models.models import Account
from app.services.sync_service import sync_account, sync_all_accounts, compute_all_baselines
from app.services.brief_worker import generate_all_briefs, generate_all_recommendations

router = APIRouter(prefix="/api", tags=["sync"], dependencies=[Depends(verify_password)])


@router.post("/accounts/{account_id}/sync")
async def trigger_sync(account_id: UUID, background_tasks: BackgroundTasks):
    """Trigger a manual sync for a single account (runs in background)."""
    background_tasks.add_task(sync_account, account_id)
    return {"status": "sync_started", "account_id": str(account_id)}


@router.post("/sync/all")
async def trigger_sync_all(background_tasks: BackgroundTasks):
    """Trigger a sync for all active accounts."""
    background_tasks.add_task(sync_all_accounts)
    return {"status": "sync_all_started"}


@router.post("/sync/baselines")
async def trigger_baselines(background_tasks: BackgroundTasks):
    """Trigger baseline recomputation for all accounts."""
    background_tasks.add_task(compute_all_baselines)
    return {"status": "baselines_started"}


@router.post("/sync/briefs")
async def trigger_briefs(background_tasks: BackgroundTasks):
    """Trigger daily brief generation for all accounts."""
    background_tasks.add_task(generate_all_briefs)
    return {"status": "briefs_started"}


@router.post("/sync/recommendations")
async def trigger_recommendations(background_tasks: BackgroundTasks):
    """Trigger recommendation generation for all accounts."""
    background_tasks.add_task(generate_all_recommendations)
    return {"status": "recommendations_started"}


@router.get("/sync/status")
async def sync_status(db: AsyncSession = Depends(get_db)):
    """Get overview of sync status for all accounts."""
    result = await db.execute(select(Account).where(Account.status == "active"))
    accounts = result.scalars().all()
    return {
        "active_accounts": len(accounts),
        "accounts": [
            {
                "id": str(a.id),
                "username": a.username,
                "platform": a.platform,
                "follower_count": a.follower_count,
            }
            for a in accounts
        ],
    }
