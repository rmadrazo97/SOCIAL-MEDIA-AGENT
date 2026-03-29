from datetime import datetime, date
from uuid import UUID
from pydantic import BaseModel


# Auth
class LoginRequest(BaseModel):
    password: str


class LoginResponse(BaseModel):
    authenticated: bool
    message: str


# Account
class AccountCreate(BaseModel):
    platform: str
    username: str
    access_token: str | None = None
    refresh_token: str | None = None


class AccountOut(BaseModel):
    id: UUID
    platform: str
    platform_user_id: str | None = None
    username: str
    status: str
    follower_count: int | None
    following_count: int | None = None
    biography: str | None = None
    profile_pic_url: str | None = None
    last_sync_at: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True


# Post
class PostCreate(BaseModel):
    account_id: UUID
    platform: str
    post_type: str = "image"
    caption: str | None = None
    media_url: str | None = None
    permalink: str | None = None
    posted_at: datetime


class PostOut(BaseModel):
    id: UUID
    account_id: UUID
    platform: str
    post_type: str
    caption: str | None
    media_url: str | None
    permalink: str | None
    posted_at: datetime
    location_name: str | None = None
    tagged_users: list[str] | None = None
    media_stored: bool = False
    carousel_count: int = 0
    video_duration: float | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class PostWithMetrics(PostOut):
    latest_metrics: "PostMetricOut | None" = None
    latest_insight: "PostInsightOut | None" = None


# PostMetric
class PostMetricCreate(BaseModel):
    post_id: UUID
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    reach: int = 0
    engagement_rate: float = 0


class PostMetricOut(BaseModel):
    id: UUID
    post_id: UUID
    snapshot_at: datetime
    views: int
    likes: int
    comments: int
    shares: int
    saves: int
    reach: int
    engagement_rate: float
    performance_score: float | None

    class Config:
        from_attributes = True


# Post Insight (Instagram creator-only analytics)
class PostInsightCreate(BaseModel):
    post_id: UUID
    accounts_reached: int = 0
    reach_follower_pct: float | None = None
    reach_non_follower_pct: float | None = None
    impressions: int = 0
    from_home: int = 0
    from_profile: int = 0
    from_hashtags: int = 0
    from_explore: int = 0
    from_other: int = 0
    total_interactions: int = 0
    interaction_follower_pct: float | None = None
    saves: int = 0
    shares: int = 0
    profile_visits: int = 0
    follows: int = 0


class PostInsightOut(BaseModel):
    id: UUID
    post_id: UUID
    snapshot_at: datetime
    accounts_reached: int
    reach_follower_pct: float | None
    reach_non_follower_pct: float | None
    impressions: int
    from_home: int
    from_profile: int
    from_hashtags: int
    from_explore: int
    from_other: int
    total_interactions: int
    interaction_follower_pct: float | None
    saves: int
    shares: int
    profile_visits: int
    follows: int

    class Config:
        from_attributes = True


# Insight
class InsightOut(BaseModel):
    id: UUID
    post_id: UUID | None
    account_id: UUID
    insight_type: str
    content: str
    metadata_json: dict | None
    created_at: datetime

    class Config:
        from_attributes = True


# Recommendation
class RecommendationOut(BaseModel):
    id: UUID
    account_id: UUID
    recommendation_type: str
    title: str
    content: str
    priority: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class RecommendationUpdate(BaseModel):
    status: str


# DailyBrief
class DailyBriefOut(BaseModel):
    id: UUID
    account_id: UUID
    brief_date: date
    content: str
    metrics_snapshot: dict | None
    created_at: datetime

    class Config:
        from_attributes = True


# Baseline
class BaselineOut(BaseModel):
    id: UUID
    account_id: UUID
    computed_at: datetime
    period_days: int
    baseline_data: dict

    class Config:
        from_attributes = True


# Remix
class RemixRequest(BaseModel):
    remix_type: str = "carousel"


class RemixOut(BaseModel):
    format: str
    content: dict


# CSV Import
class ImportResult(BaseModel):
    created: int
    updated: int
    errors: list[str]


# Metrics summary
class AccountMetricsSummary(BaseModel):
    total_views: int
    total_likes: int
    total_comments: int
    total_shares: int
    total_saves: int
    post_count: int
    avg_engagement_rate: float
    top_post_id: UUID | None


# Artifact
class ArtifactCreate(BaseModel):
    account_id: UUID | None = None
    artifact_type: str
    title: str
    content: str
    metadata_json: dict | None = None


class ArtifactUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    status: str | None = None
    metadata_json: dict | None = None


class ArtifactOut(BaseModel):
    id: UUID
    account_id: UUID | None
    artifact_type: str
    title: str
    content: str
    metadata_json: dict | None
    status: str
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True


# Agent Conversation
class AgentConversationOut(BaseModel):
    id: UUID
    thread_id: str
    account_id: UUID | None
    summary: str | None
    created_at: datetime
    last_active_at: datetime

    class Config:
        from_attributes = True


# Profile Snapshot
class ProfileSnapshotOut(BaseModel):
    id: UUID
    account_id: UUID
    follower_count: int
    following_count: int
    post_count: int
    snapshot_at: datetime

    class Config:
        from_attributes = True


# Post Comment
class PostCommentOut(BaseModel):
    id: UUID
    post_id: UUID
    platform_comment_id: str
    username: str
    text: str
    comment_like_count: int
    reply_count: int
    parent_comment_id: UUID | None
    commented_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True
