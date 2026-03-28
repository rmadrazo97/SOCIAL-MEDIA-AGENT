from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.api.deps import verify_password
from app.models.models import Post, PostMetric
from app.schemas.schemas import PostCreate, PostOut, PostMetricCreate, PostMetricOut, PostWithMetrics

router = APIRouter(prefix="/api", tags=["posts"], dependencies=[Depends(verify_password)])


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
