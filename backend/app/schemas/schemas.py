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
    username: str
    status: str
    follower_count: int | None
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
    created_at: datetime

    class Config:
        from_attributes = True


class PostWithMetrics(PostOut):
    latest_metrics: "PostMetricOut | None" = None


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
