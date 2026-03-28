"""
API endpoints for triggering manual syncs and viewing sync status.
"""
from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import verify_password
from app.models.models import Account, Post, PostMetric, PostComment, ProfileSnapshot
from app.services.sync_service import sync_account, sync_all_accounts, compute_all_baselines, _upsert_post, _snapshot_metrics, _upsert_comment
from app.services.brief_worker import generate_all_briefs, generate_all_recommendations
from app.integrations.instagram_web_scraper import instagram_web_scraper

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

    ig_session_valid = instagram_web_scraper.is_configured()

    return {
        "active_accounts": len(accounts),
        "instagram_session_configured": ig_session_valid,
        "accounts": [
            {
                "id": str(a.id),
                "username": a.username,
                "platform": a.platform,
                "follower_count": a.follower_count,
                "following_count": a.following_count,
                "last_sync_at": a.last_sync_at.isoformat() if a.last_sync_at else None,
            }
            for a in accounts
        ],
    }


@router.post("/accounts/{account_id}/ig-sync-data")
async def receive_ig_sync_data(account_id: UUID, data: dict, db: AsyncSession = Depends(get_db)):
    """
    Receive scraped Instagram data from the host-side sync worker.
    This endpoint processes profile, posts, comments, and metric resnapshots
    that were fetched from the host machine (not Docker).
    """
    account = await db.get(Account, account_id)
    if not account:
        return {"error": "Account not found"}

    result = {"profile_updated": False, "new_posts": 0, "updated_posts": 0, "comments": 0, "resnapshots": 0}

    # 1. Update profile
    profile = data.get("profile")
    if profile:
        account.follower_count = profile.get("follower_count", account.follower_count)
        account.following_count = profile.get("following_count", account.following_count)
        account.biography = profile.get("biography", account.biography)
        account.profile_pic_url = profile.get("profile_pic_url", account.profile_pic_url)
        if profile.get("platform_user_id"):
            account.platform_user_id = profile["platform_user_id"]

        # Profile snapshot
        snapshot = ProfileSnapshot(
            account_id=account.id,
            follower_count=profile.get("follower_count", 0),
            following_count=profile.get("following_count", 0),
            post_count=profile.get("post_count", 0),
        )
        db.add(snapshot)
        result["profile_updated"] = True

    # 2. Upsert posts + metrics + comments
    for post_data in data.get("new_posts", []):
        post, is_new = await _upsert_post(db, account, post_data)
        if is_new:
            result["new_posts"] += 1
        else:
            result["updated_posts"] += 1

        if post_data.get("metrics"):
            await _snapshot_metrics(db, post, post_data["metrics"])

        if post_data.get("media_stored"):
            post.media_stored = True

        for comment in post_data.get("comments", []):
            await _upsert_comment(db, post, comment)
            result["comments"] += 1

    # 3. Metric resnapshots for existing posts
    for rs in data.get("metric_resnapshots", []):
        pid = rs.get("platform_post_id")
        if not pid:
            continue
        post_result = await db.execute(
            select(Post).where(Post.account_id == account.id, Post.platform_post_id == pid)
        )
        post = post_result.scalar_one_or_none()
        if post and rs.get("metrics"):
            await _snapshot_metrics(db, post, rs["metrics"])
            result["resnapshots"] += 1

    account.last_sync_at = datetime.now(timezone.utc)
    await db.commit()

    return result


@router.get("/sync/session-check")
async def check_instagram_session():
    """Check if the Instagram web session is still valid."""
    if not instagram_web_scraper.is_configured():
        return {"valid": False, "reason": "Session cookies not configured in .env"}
    valid = await instagram_web_scraper.validate_session()
    return {"valid": valid, "reason": None if valid else "Session expired — update cookies from browser"}
