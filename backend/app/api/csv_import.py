from uuid import UUID
from datetime import datetime, timezone
from io import StringIO
import csv

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import verify_password
from app.models.models import Account, Post, PostMetric
from app.schemas.schemas import ImportResult

router = APIRouter(prefix="/api", tags=["import"], dependencies=[Depends(verify_password)])


@router.post("/accounts/{account_id}/import", response_model=ImportResult)
async def import_csv(account_id: UUID, file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    account = await db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    content = await file.read()
    text = content.decode("utf-8")
    reader = csv.DictReader(StringIO(text))

    created = 0
    updated = 0
    errors = []

    for i, row in enumerate(reader):
        try:
            permalink = row.get("post_url", "").strip()
            caption = row.get("caption", "").strip()
            posted_at_str = row.get("posted_at", "").strip()
            post_type = row.get("post_type", "image").strip()

            if not posted_at_str:
                errors.append(f"Row {i+1}: missing posted_at")
                continue

            posted_at = datetime.fromisoformat(posted_at_str.replace("Z", "+00:00"))

            # Check if post exists by permalink
            existing = None
            if permalink:
                result = await db.execute(
                    select(Post).where(Post.account_id == account_id, Post.permalink == permalink)
                )
                existing = result.scalar_one_or_none()

            if existing:
                post = existing
                updated += 1
            else:
                post = Post(
                    account_id=account_id,
                    platform=account.platform,
                    post_type=post_type,
                    caption=caption,
                    permalink=permalink,
                    posted_at=posted_at,
                )
                db.add(post)
                await db.flush()
                created += 1

            # Add metrics
            metric = PostMetric(
                post_id=post.id,
                views=int(row.get("views", 0) or 0),
                likes=int(row.get("likes", 0) or 0),
                comments=int(row.get("comments", 0) or 0),
                shares=int(row.get("shares", 0) or 0),
                saves=int(row.get("saves", 0) or 0),
                reach=int(row.get("reach", 0) or 0),
            )
            total_engagement = metric.likes + metric.comments + metric.shares + metric.saves
            if metric.views > 0:
                metric.engagement_rate = round(total_engagement / metric.views, 4)
            db.add(metric)

        except Exception as e:
            errors.append(f"Row {i+1}: {str(e)}")

    await db.commit()
    return ImportResult(created=created, updated=updated, errors=errors)
