from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import verify_password
from app.models.models import Post, PostMetric
from app.schemas.schemas import RemixRequest, RemixOut
from app.services.ai_service import ai_service

router = APIRouter(prefix="/api", tags=["remix"], dependencies=[Depends(verify_password)])


@router.post("/posts/{post_id}/remix", response_model=list[RemixOut])
async def generate_remix(post_id: UUID, req: RemixRequest, db: AsyncSession = Depends(get_db)):
    post = await db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    result = await db.execute(
        select(PostMetric).where(PostMetric.post_id == post_id).order_by(desc(PostMetric.snapshot_at)).limit(1)
    )
    metrics = result.scalar_one_or_none()

    remixes = await ai_service.generate_remix(post, metrics, req.remix_type)
    return [RemixOut(format=r["format"], content=r) for r in remixes]
