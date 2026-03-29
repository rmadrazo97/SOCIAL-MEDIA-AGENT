"""Data query tools for the Co-Pilot agent — read-only access to platform data."""
import json
from datetime import datetime, timedelta, timezone

from langchain_core.tools import tool
from sqlalchemy import select, func, desc

from pathlib import Path

from app.database import async_session
from app.config import settings
from app.models.models import (
    Account, Post, PostMetric, PostComment, AccountBaseline, DailyBrief,
    Recommendation, Insight, Artifact,
)


def _serialize_datetime(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


@tool
async def get_accounts() -> str:
    """List all tracked social media accounts with their follower counts and status."""
    async with async_session() as session:
        result = await session.execute(select(Account).order_by(Account.created_at))
        accounts = result.scalars().all()
        return json.dumps([
            {
                "id": str(a.id),
                "platform": a.platform,
                "username": a.username,
                "status": a.status,
                "follower_count": a.follower_count,
            }
            for a in accounts
        ])


@tool
async def get_account_metrics(account_id: str, days: int = 7) -> str:
    """Get aggregated engagement metrics for an account over a time period.

    Args:
        account_id: UUID of the account
        days: Number of days to aggregate (default 7)
    """
    async with async_session() as session:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        # Get posts for this account
        posts_q = select(Post.id).where(
            Post.account_id == account_id,
            Post.posted_at >= cutoff,
        )
        post_ids = (await session.execute(posts_q)).scalars().all()

        if not post_ids:
            return json.dumps({"message": f"No posts found in the last {days} days", "post_count": 0})

        # Get latest metric per post using a subquery
        metrics_q = (
            select(
                func.sum(PostMetric.views).label("total_views"),
                func.sum(PostMetric.likes).label("total_likes"),
                func.sum(PostMetric.comments).label("total_comments"),
                func.sum(PostMetric.shares).label("total_shares"),
                func.sum(PostMetric.saves).label("total_saves"),
                func.avg(PostMetric.engagement_rate).label("avg_engagement_rate"),
                func.count(PostMetric.id).label("metric_count"),
            )
            .where(PostMetric.post_id.in_(post_ids))
        )
        row = (await session.execute(metrics_q)).one_or_none()

        return json.dumps({
            "post_count": len(post_ids),
            "days": days,
            "total_views": int(row.total_views or 0),
            "total_likes": int(row.total_likes or 0),
            "total_comments": int(row.total_comments or 0),
            "total_shares": int(row.total_shares or 0),
            "total_saves": int(row.total_saves or 0),
            "avg_engagement_rate": round(float(row.avg_engagement_rate or 0), 4),
        })


@tool
async def get_account_baseline(account_id: str) -> str:
    """Get the 30-day performance baseline for an account.

    Args:
        account_id: UUID of the account
    """
    async with async_session() as session:
        result = await session.execute(
            select(AccountBaseline)
            .where(AccountBaseline.account_id == account_id)
            .order_by(desc(AccountBaseline.computed_at))
            .limit(1)
        )
        baseline = result.scalar_one_or_none()
        if not baseline:
            return json.dumps({"message": "No baseline computed yet. Suggest triggering a baseline recomputation."})
        return json.dumps({
            "computed_at": baseline.computed_at.isoformat(),
            "period_days": baseline.period_days,
            "baseline_data": baseline.baseline_data,
        })


@tool
async def get_posts(account_id: str = None, post_type: str = None, limit: int = 20) -> str:
    """Get recent posts with their latest metrics.

    Args:
        account_id: Filter by account UUID (optional)
        post_type: Filter by type: image, carousel, reel, video (optional)
        limit: Max posts to return (default 20)
    """
    async with async_session() as session:
        q = select(Post).order_by(desc(Post.posted_at)).limit(limit)
        if account_id:
            q = q.where(Post.account_id == account_id)
        if post_type:
            q = q.where(Post.post_type == post_type)

        result = await session.execute(q)
        posts = result.scalars().all()

        posts_data = []
        for p in posts:
            # Get latest metric for this post
            metric_q = (
                select(PostMetric)
                .where(PostMetric.post_id == p.id)
                .order_by(desc(PostMetric.snapshot_at))
                .limit(1)
            )
            metric = (await session.execute(metric_q)).scalar_one_or_none()

            posts_data.append({
                "id": str(p.id),
                "account_id": str(p.account_id),
                "platform": p.platform,
                "post_type": p.post_type,
                "caption": (p.caption or "")[:200],
                "posted_at": p.posted_at.isoformat(),
                "permalink": p.permalink,
                "metrics": {
                    "views": metric.views if metric else 0,
                    "likes": metric.likes if metric else 0,
                    "comments": metric.comments if metric else 0,
                    "shares": metric.shares if metric else 0,
                    "saves": metric.saves if metric else 0,
                    "engagement_rate": float(metric.engagement_rate) if metric else 0,
                    "performance_score": float(metric.performance_score) if metric and metric.performance_score else None,
                } if metric else None,
            })

        return json.dumps(posts_data, default=_serialize_datetime)


@tool
async def get_post_detail(post_id: str) -> str:
    """Get detailed information about a specific post including all metric history.

    Args:
        post_id: UUID of the post
    """
    async with async_session() as session:
        post = (await session.execute(
            select(Post).where(Post.id == post_id)
        )).scalar_one_or_none()

        if not post:
            return json.dumps({"error": "Post not found"})

        metrics = (await session.execute(
            select(PostMetric)
            .where(PostMetric.post_id == post_id)
            .order_by(desc(PostMetric.snapshot_at))
        )).scalars().all()

        return json.dumps({
            "id": str(post.id),
            "platform": post.platform,
            "post_type": post.post_type,
            "caption": post.caption,
            "posted_at": post.posted_at.isoformat(),
            "permalink": post.permalink,
            "metrics_history": [
                {
                    "snapshot_at": m.snapshot_at.isoformat(),
                    "views": m.views,
                    "likes": m.likes,
                    "comments": m.comments,
                    "shares": m.shares,
                    "saves": m.saves,
                    "engagement_rate": float(m.engagement_rate),
                    "performance_score": float(m.performance_score) if m.performance_score else None,
                }
                for m in metrics
            ],
        })


@tool
async def get_daily_brief(account_id: str) -> str:
    """Get the most recent daily brief for an account.

    Args:
        account_id: UUID of the account
    """
    async with async_session() as session:
        result = await session.execute(
            select(DailyBrief)
            .where(DailyBrief.account_id == account_id)
            .order_by(desc(DailyBrief.brief_date))
            .limit(1)
        )
        brief = result.scalar_one_or_none()
        if not brief:
            return json.dumps({"message": "No daily brief available. Try generating one."})
        return json.dumps({
            "brief_date": brief.brief_date.isoformat(),
            "content": brief.content,
            "metrics_snapshot": brief.metrics_snapshot,
        })


@tool
async def get_recommendations(account_id: str, status: str = "pending") -> str:
    """Get recommendations for an account.

    Args:
        account_id: UUID of the account
        status: Filter by status: pending, accepted, dismissed (default: pending)
    """
    async with async_session() as session:
        q = (
            select(Recommendation)
            .where(Recommendation.account_id == account_id)
            .order_by(desc(Recommendation.created_at))
        )
        if status:
            q = q.where(Recommendation.status == status)

        result = await session.execute(q)
        recs = result.scalars().all()
        return json.dumps([
            {
                "id": str(r.id),
                "type": r.recommendation_type,
                "title": r.title,
                "content": r.content,
                "priority": r.priority,
                "status": r.status,
            }
            for r in recs
        ])


@tool
async def list_artifacts(account_id: str = None, artifact_type: str = None) -> str:
    """List saved artifacts (reports, strategies, content ideas, etc.).

    Args:
        account_id: Filter by account UUID (optional)
        artifact_type: Filter by type: content_idea, copy_draft, strategy, report, trend_analysis, task (optional)
    """
    async with async_session() as session:
        q = select(Artifact).order_by(desc(Artifact.created_at)).limit(20)
        if account_id:
            q = q.where(Artifact.account_id == account_id)
        if artifact_type:
            q = q.where(Artifact.artifact_type == artifact_type)
        q = q.where(Artifact.status != "archived")

        result = await session.execute(q)
        artifacts = result.scalars().all()
        return json.dumps([
            {
                "id": str(a.id),
                "type": a.artifact_type,
                "title": a.title,
                "status": a.status,
                "created_at": a.created_at.isoformat(),
            }
            for a in artifacts
        ])


@tool
async def get_post_comments(post_id: str, limit: int = 20) -> str:
    """Get comments on a post, sorted by most liked. Useful for understanding audience sentiment and engagement quality.

    Args:
        post_id: UUID of the post
        limit: Max comments to return (default 20)
    """
    async with async_session() as session:
        result = await session.execute(
            select(PostComment)
            .where(PostComment.post_id == post_id)
            .order_by(desc(PostComment.comment_like_count))
            .limit(limit)
        )
        comments = result.scalars().all()
        return json.dumps([
            {
                "username": c.username,
                "text": c.text,
                "likes": c.comment_like_count,
                "replies": c.reply_count,
                "date": c.commented_at.isoformat(),
            }
            for c in comments
        ], default=_serialize_datetime)


@tool
async def analyze_post_media(post_id: str) -> str:
    """Analyze the visual content of a post's media files. Returns descriptions of images and videos
    stored for the post, including file types, sizes, and count. Use this to understand what a post
    looks like when providing content feedback.

    Args:
        post_id: UUID of the post
    """
    async with async_session() as session:
        from sqlalchemy.orm import selectinload
        result = await session.execute(
            select(Post).where(Post.id == post_id).options(selectinload(Post.account))
        )
        post = result.scalar_one_or_none()
        if not post:
            return json.dumps({"error": "Post not found"})

        media_dir = Path(settings.INSTAGRAM_MEDIA_DIR) / post.account.username / (post.platform_post_id or "")
        if not media_dir.exists():
            return json.dumps({
                "post_id": post_id,
                "caption": post.caption,
                "post_type": post.post_type,
                "media_files": [],
                "note": "No stored media files found. Use the post caption and metrics for analysis."
            })

        media_files = []
        for f in sorted(media_dir.iterdir()):
            if f.is_file():
                file_info = {
                    "filename": f.name,
                    "type": "video" if f.suffix == ".mp4" else "image",
                    "size_kb": round(f.stat().st_size / 1024),
                    "url": f"/api/posts/{post_id}/media/{f.name}",
                }
                media_files.append(file_info)

        return json.dumps({
            "post_id": post_id,
            "caption": post.caption,
            "post_type": post.post_type,
            "platform": post.platform,
            "posted_at": post.posted_at.isoformat(),
            "permalink": post.permalink,
            "media_count": len(media_files),
            "media_files": media_files,
            "analysis_context": (
                f"This is a {post.post_type} post with {len(media_files)} media file(s). "
                f"{'It contains video content.' if any(m['type'] == 'video' for m in media_files) else 'It contains image content only.'} "
                f"To provide visual feedback, consider the post type, caption themes, and media composition."
            ),
        }, default=_serialize_datetime)


query_tools = [
    get_accounts,
    get_account_metrics,
    get_account_baseline,
    get_posts,
    get_post_detail,
    get_post_comments,
    get_daily_brief,
    get_recommendations,
    list_artifacts,
    analyze_post_media,
]
