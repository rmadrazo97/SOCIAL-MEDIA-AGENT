from pathlib import Path
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.api.deps import verify_password
from app.models.models import Post, PostMetric, PostComment
from app.schemas.schemas import PostCreate, PostOut, PostMetricCreate, PostMetricOut, PostWithMetrics, PostCommentOut
from app.config import settings

router = APIRouter(prefix="/api", tags=["posts"], dependencies=[Depends(verify_password)])
media_router = APIRouter(prefix="/api", tags=["media"])


@router.get("/accounts/{account_id}/posts", response_model=list[PostWithMetrics])
async def list_posts(
    account_id: UUID,
    platform: str | None = None,
    post_type: str | None = None,
    limit: int = Query(default=50, le=100),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    q = select(Post).where(Post.account_id == account_id).options(selectinload(Post.metrics))
    if platform:
        q = q.where(Post.platform == platform)
    if post_type:
        q = q.where(Post.post_type == post_type)
    q = q.order_by(desc(Post.posted_at)).limit(limit).offset(offset)
    result = await db.execute(q)
    posts = result.scalars().all()

    out = []
    for p in posts:
        latest = None
        if p.metrics:
            latest_m = max(p.metrics, key=lambda m: m.snapshot_at)
            latest = PostMetricOut.model_validate(latest_m)
        pw = PostWithMetrics.model_validate(p)
        pw.latest_metrics = latest
        out.append(pw)
    return out


@router.post("/posts", response_model=PostOut, status_code=201)
async def create_post(data: PostCreate, db: AsyncSession = Depends(get_db)):
    post = Post(**data.model_dump())
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return post


@router.get("/posts/{post_id}", response_model=PostWithMetrics)
async def get_post(post_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Post).where(Post.id == post_id).options(selectinload(Post.metrics))
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    latest = None
    if post.metrics:
        latest_m = max(post.metrics, key=lambda m: m.snapshot_at)
        latest = PostMetricOut.model_validate(latest_m)
    pw = PostWithMetrics.model_validate(post)
    pw.latest_metrics = latest
    return pw


@router.delete("/posts/{post_id}", status_code=204)
async def delete_post(post_id: UUID, db: AsyncSession = Depends(get_db)):
    post = await db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    await db.delete(post)
    await db.commit()


# Metrics
@router.get("/posts/{post_id}/metrics", response_model=list[PostMetricOut])
async def list_post_metrics(post_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PostMetric).where(PostMetric.post_id == post_id).order_by(PostMetric.snapshot_at)
    )
    return result.scalars().all()


@router.post("/posts/{post_id}/metrics", response_model=PostMetricOut, status_code=201)
async def create_post_metric(post_id: UUID, data: PostMetricCreate, db: AsyncSession = Depends(get_db)):
    post = await db.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    metric = PostMetric(post_id=post_id, **data.model_dump(exclude={"post_id"}))
    db.add(metric)
    await db.commit()
    await db.refresh(metric)
    return metric


# Comments
@router.get("/posts/{post_id}/comments", response_model=list[PostCommentOut])
async def list_post_comments(
    post_id: UUID,
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List comments for a post."""
    result = await db.execute(
        select(PostComment)
        .where(PostComment.post_id == post_id)
        .order_by(desc(PostComment.commented_at))
        .limit(limit)
    )
    return result.scalars().all()


# Media (public — no auth, served by <img>/<video> tags)
@media_router.get("/posts/{post_id}/media/{filename}")
async def get_post_media(post_id: UUID, filename: str, db: AsyncSession = Depends(get_db)):
    """Serve a stored media file for a post."""
    result = await db.execute(
        select(Post).where(Post.id == post_id).options(selectinload(Post.account))
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Prevent path traversal
    safe_filename = Path(filename).name
    media_path = Path(settings.INSTAGRAM_MEDIA_DIR) / post.account.username / post.platform_post_id / safe_filename

    if not media_path.exists():
        raise HTTPException(status_code=404, detail="Media file not found")

    content_type = "image/jpeg"
    if safe_filename.endswith(".mp4"):
        content_type = "video/mp4"
    elif safe_filename.endswith(".png"):
        content_type = "image/png"

    return FileResponse(media_path, media_type=content_type)


@media_router.get("/posts/{post_id}/media")
async def list_post_media(post_id: UUID, db: AsyncSession = Depends(get_db)):
    """List available media files for a post."""
    result = await db.execute(
        select(Post).where(Post.id == post_id).options(selectinload(Post.account))
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    media_dir = Path(settings.INSTAGRAM_MEDIA_DIR) / post.account.username / (post.platform_post_id or "")
    if not media_dir.exists():
        return {"files": [], "post_id": str(post_id)}

    files = []
    for f in sorted(media_dir.iterdir()):
        if f.is_file():
            files.append({
                "filename": f.name,
                "size_bytes": f.stat().st_size,
                "url": f"/api/posts/{post_id}/media/{f.name}",
            })
    return {"files": files, "post_id": str(post_id)}
