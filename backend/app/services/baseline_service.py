import statistics
from uuid import UUID
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Post, PostMetric, AccountBaseline


async def compute_baseline(account_id: UUID, db: AsyncSession) -> AccountBaseline:
    since = datetime.now(timezone.utc) - timedelta(days=30)

    result = await db.execute(
        select(Post).where(Post.account_id == account_id, Post.posted_at >= since).order_by(desc(Post.posted_at))
    )
    posts = result.scalars().all()

    views_list = []
    likes_list = []
    comments_list = []
    shares_list = []
    saves_list = []
    engagement_list = []
    by_type = {}
    by_day = {}
    by_hour = {}

    for post in posts:
        result = await db.execute(
            select(PostMetric).where(PostMetric.post_id == post.id).order_by(desc(PostMetric.snapshot_at)).limit(1)
        )
        metric = result.scalar_one_or_none()
        if not metric:
            continue

        views_list.append(metric.views)
        likes_list.append(metric.likes)
        comments_list.append(metric.comments)
        shares_list.append(metric.shares)
        saves_list.append(metric.saves)
        engagement_list.append(float(metric.engagement_rate))

        # By type
        pt = post.post_type
        if pt not in by_type:
            by_type[pt] = {"views": [], "engagement": []}
        by_type[pt]["views"].append(metric.views)
        by_type[pt]["engagement"].append(float(metric.engagement_rate))

        # By day of week
        day = post.posted_at.weekday()
        if day not in by_day:
            by_day[day] = {"views": [], "count": 0}
        by_day[day]["views"].append(metric.views)
        by_day[day]["count"] += 1

        # By hour
        hour = post.posted_at.hour
        if hour not in by_hour:
            by_hour[hour] = {"views": [], "count": 0}
        by_hour[hour]["views"].append(metric.views)
        by_hour[hour]["count"] += 1

    def safe_mean(lst):
        return round(statistics.mean(lst), 2) if lst else 0

    def safe_median(lst):
        return round(statistics.median(lst), 2) if lst else 0

    # Aggregate by_type
    by_type_agg = {}
    for pt, data in by_type.items():
        by_type_agg[pt] = {
            "avg_views": safe_mean(data["views"]),
            "avg_engagement": safe_mean(data["engagement"]),
            "count": len(data["views"]),
        }

    # Aggregate by_day
    by_day_agg = {}
    for day, data in by_day.items():
        by_day_agg[str(day)] = {
            "avg_views": safe_mean(data["views"]),
            "count": data["count"],
        }

    # Aggregate by_hour
    by_hour_agg = {}
    for hour, data in by_hour.items():
        by_hour_agg[str(hour)] = {
            "avg_views": safe_mean(data["views"]),
            "count": data["count"],
        }

    baseline_data = {
        "avg_views": safe_mean(views_list),
        "median_views": safe_median(views_list),
        "avg_likes": safe_mean(likes_list),
        "avg_comments": safe_mean(comments_list),
        "avg_shares": safe_mean(shares_list),
        "avg_saves": safe_mean(saves_list),
        "avg_engagement_rate": safe_mean(engagement_list),
        "post_count": len(posts),
        "by_type": by_type_agg,
        "by_day": by_day_agg,
        "by_hour": by_hour_agg,
    }

    baseline = AccountBaseline(
        account_id=account_id,
        period_days=30,
        baseline_data=baseline_data,
    )
    db.add(baseline)
    await db.commit()
    await db.refresh(baseline)
    return baseline
