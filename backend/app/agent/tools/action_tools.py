"""Action tools for the Co-Pilot agent — trigger syncs, generate content, manage artifacts."""
import json
import uuid
from datetime import datetime, timezone

from langchain_core.tools import tool
from sqlalchemy import select, desc

from app.database import async_session
from app.models.models import (
    Account, Post, PostMetric, PostComment, AccountBaseline, Recommendation, Artifact,
)
from app.services.ai_service import ai_service


@tool
async def trigger_sync(account_id: str) -> str:
    """Trigger a data sync for a specific account to refresh posts and metrics from the platform.

    Args:
        account_id: UUID of the account to sync
    """
    # Import here to avoid circular imports
    from app.services.sync_service import sync_account
    try:
        result = await sync_account(account_id)
        return json.dumps({"status": "sync_completed", "result": str(result)})
    except Exception as e:
        return json.dumps({"status": "sync_failed", "error": str(e)})


@tool
async def generate_post_diagnostic(post_id: str) -> str:
    """Generate an AI diagnostic analysis for a specific post, comparing its performance to the account baseline.

    Args:
        post_id: UUID of the post to analyze
    """
    async with async_session() as session:
        post = (await session.execute(
            select(Post).where(Post.id == post_id)
        )).scalar_one_or_none()
        if not post:
            return json.dumps({"error": "Post not found"})

        metric = (await session.execute(
            select(PostMetric)
            .where(PostMetric.post_id == post_id)
            .order_by(desc(PostMetric.snapshot_at))
            .limit(1)
        )).scalar_one_or_none()

        baseline = (await session.execute(
            select(AccountBaseline)
            .where(AccountBaseline.account_id == post.account_id)
            .order_by(desc(AccountBaseline.computed_at))
            .limit(1)
        )).scalar_one_or_none()

        # Fetch top comments for analysis
        comment_rows = (await session.execute(
            select(PostComment)
            .where(PostComment.post_id == post_id)
            .order_by(desc(PostComment.comment_like_count))
            .limit(25)
        )).scalars().all()
        comments_data = [
            {"username": c.username, "text": c.text, "likes": c.comment_like_count}
            for c in comment_rows
        ] if comment_rows else None

        result = await ai_service.generate_diagnostic(post, metric, baseline, comments=comments_data)
        return json.dumps(result)


@tool
async def generate_brief(account_id: str) -> str:
    """Generate a daily performance brief for an account.

    Args:
        account_id: UUID of the account
    """
    async with async_session() as session:
        account = (await session.execute(
            select(Account).where(Account.id == account_id)
        )).scalar_one_or_none()
        if not account:
            return json.dumps({"error": "Account not found"})

        # Get recent posts with metrics
        posts = (await session.execute(
            select(Post)
            .where(Post.account_id == account_id)
            .order_by(desc(Post.posted_at))
            .limit(10)
        )).scalars().all()

        post_data = []
        for p in posts:
            m = (await session.execute(
                select(PostMetric)
                .where(PostMetric.post_id == p.id)
                .order_by(desc(PostMetric.snapshot_at))
                .limit(1)
            )).scalar_one_or_none()
            post_data.append({"post": p, "metrics": m})

        baseline = (await session.execute(
            select(AccountBaseline)
            .where(AccountBaseline.account_id == account_id)
            .order_by(desc(AccountBaseline.computed_at))
            .limit(1)
        )).scalar_one_or_none()

        result = await ai_service.generate_daily_brief(account, post_data, baseline)
        return json.dumps(result)


@tool
async def update_recommendation_status(recommendation_id: str, status: str) -> str:
    """Accept or dismiss a recommendation.

    Args:
        recommendation_id: UUID of the recommendation
        status: New status: "accepted" or "dismissed"
    """
    if status not in ("accepted", "dismissed"):
        return json.dumps({"error": "Status must be 'accepted' or 'dismissed'"})

    async with async_session() as session:
        rec = (await session.execute(
            select(Recommendation).where(Recommendation.id == recommendation_id)
        )).scalar_one_or_none()
        if not rec:
            return json.dumps({"error": "Recommendation not found"})

        rec.status = status
        await session.commit()
        return json.dumps({"status": "updated", "recommendation_id": str(rec.id), "new_status": status})


@tool
async def save_artifact(
    title: str,
    content: str,
    artifact_type: str,
    account_id: str = None,
    metadata: dict = None,
) -> str:
    """Save a generated artifact (content idea, strategy, report, etc.) for future reference.

    Args:
        title: Short title for the artifact
        content: Full content (markdown supported)
        artifact_type: One of: content_idea, copy_draft, strategy, report, trend_analysis, task
        account_id: UUID of the related account (optional)
        metadata: Additional structured data (optional)
    """
    async with async_session() as session:
        artifact = Artifact(
            id=uuid.uuid4(),
            account_id=account_id if account_id else None,
            artifact_type=artifact_type,
            title=title,
            content=content,
            metadata_json=metadata,
            status="active",
        )
        session.add(artifact)
        await session.commit()
        return json.dumps({
            "status": "saved",
            "artifact_id": str(artifact.id),
            "title": title,
            "type": artifact_type,
        })


@tool
async def retrieve_artifact(artifact_id: str) -> str:
    """Load a previously saved artifact by its ID.

    Args:
        artifact_id: UUID of the artifact
    """
    async with async_session() as session:
        artifact = (await session.execute(
            select(Artifact).where(Artifact.id == artifact_id)
        )).scalar_one_or_none()
        if not artifact:
            return json.dumps({"error": "Artifact not found"})
        return json.dumps({
            "id": str(artifact.id),
            "type": artifact.artifact_type,
            "title": artifact.title,
            "content": artifact.content,
            "metadata": artifact.metadata_json,
            "status": artifact.status,
            "created_at": artifact.created_at.isoformat(),
        })


action_tools = [
    trigger_sync,
    generate_post_diagnostic,
    generate_brief,
    update_recommendation_status,
    save_artifact,
    retrieve_artifact,
]
