import uuid
from datetime import datetime, date

from sqlalchemy import Boolean, Float, String, Text, Integer, DateTime, Date, Numeric, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform: Mapped[str] = mapped_column(String(20), nullable=False)
    platform_user_id: Mapped[str] = mapped_column(String(255), nullable=True)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    follower_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    following_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    biography: Mapped[str | None] = mapped_column(Text, nullable=True)
    profile_pic_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    posts: Mapped[list["Post"]] = relationship(back_populates="account", cascade="all, delete-orphan")
    insights: Mapped[list["Insight"]] = relationship(back_populates="account", cascade="all, delete-orphan")
    recommendations: Mapped[list["Recommendation"]] = relationship(back_populates="account", cascade="all, delete-orphan")
    daily_briefs: Mapped[list["DailyBrief"]] = relationship(back_populates="account", cascade="all, delete-orphan")
    baselines: Mapped[list["AccountBaseline"]] = relationship(back_populates="account", cascade="all, delete-orphan")
    profile_snapshots: Mapped[list["ProfileSnapshot"]] = relationship(back_populates="account", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("platform", "username", name="uq_account_platform_username"),
    )


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"))
    platform_post_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    platform: Mapped[str] = mapped_column(String(20))
    post_type: Mapped[str] = mapped_column(String(20), default="image")
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    permalink: Mapped[str | None] = mapped_column(Text, nullable=True)
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    location_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tagged_users: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    media_stored: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    carousel_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    video_duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    account: Mapped["Account"] = relationship(back_populates="posts")
    metrics: Mapped[list["PostMetric"]] = relationship(back_populates="post", cascade="all, delete-orphan")
    insights: Mapped[list["Insight"]] = relationship(back_populates="post", cascade="all, delete-orphan")
    comments: Mapped[list["PostComment"]] = relationship(back_populates="post", cascade="all, delete-orphan")
    post_insights: Mapped[list["PostInsight"]] = relationship(back_populates="post", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("account_id", "platform_post_id", name="uq_post_account_platform_id"),
        Index("ix_posts_account_posted", "account_id", "posted_at"),
    )


class PostMetric(Base):
    __tablename__ = "post_metrics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("posts.id", ondelete="CASCADE"))
    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    views: Mapped[int] = mapped_column(Integer, default=0)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    comments: Mapped[int] = mapped_column(Integer, default=0)
    shares: Mapped[int] = mapped_column(Integer, default=0)
    saves: Mapped[int] = mapped_column(Integer, default=0)
    reach: Mapped[int] = mapped_column(Integer, default=0)
    engagement_rate: Mapped[float] = mapped_column(Numeric(7, 4), default=0)
    performance_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)

    post: Mapped["Post"] = relationship(back_populates="metrics")

    __table_args__ = (
        Index("ix_post_metrics_post_snapshot", "post_id", "snapshot_at"),
    )


class Insight(Base):
    __tablename__ = "insights"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("posts.id", ondelete="CASCADE"), nullable=True)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"))
    insight_type: Mapped[str] = mapped_column(String(30))
    content: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    post: Mapped["Post | None"] = relationship(back_populates="insights")
    account: Mapped["Account"] = relationship(back_populates="insights")

    __table_args__ = (
        Index("ix_insights_account_created", "account_id", "created_at"),
    )


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"))
    recommendation_type: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    priority: Mapped[int] = mapped_column(Integer, default=3)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    account: Mapped["Account"] = relationship(back_populates="recommendations")

    __table_args__ = (
        Index("ix_recommendations_account_status", "account_id", "status"),
    )


class DailyBrief(Base):
    __tablename__ = "daily_briefs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"))
    brief_date: Mapped[date] = mapped_column(Date)
    content: Mapped[str] = mapped_column(Text)
    metrics_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    account: Mapped["Account"] = relationship(back_populates="daily_briefs")

    __table_args__ = (
        UniqueConstraint("account_id", "brief_date", name="uq_daily_brief_account_date"),
    )


class AccountBaseline(Base):
    __tablename__ = "account_baselines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"))
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    period_days: Mapped[int] = mapped_column(Integer, default=30)
    baseline_data: Mapped[dict] = mapped_column(JSONB)

    account: Mapped["Account"] = relationship(back_populates="baselines")


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=True)
    artifact_type: Mapped[str] = mapped_column(String(30))  # content_idea, copy_draft, strategy, report, trend_analysis, task
    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, archived, completed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    account: Mapped["Account | None"] = relationship(backref="artifacts")

    __table_args__ = (
        Index("ix_artifacts_account_type", "account_id", "artifact_type"),
    )


class AgentConversation(Base):
    __tablename__ = "agent_conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    account_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_active_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    account: Mapped["Account | None"] = relationship(backref="agent_conversations")


class AgentMemoryEntry(Base):
    __tablename__ = "agent_memory_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=True)
    memory_type: Mapped[str] = mapped_column(String(30))  # creator_profile, insight, preference, pattern
    key: Mapped[str] = mapped_column(String(255), index=True)
    content: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Numeric(3, 2), default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    account: Mapped["Account | None"] = relationship(backref="agent_memory_entries")

    __table_args__ = (
        Index("ix_agent_memory_account_type", "account_id", "memory_type"),
    )


class PostInsight(Base):
    """Creator-only Instagram insights data — reach, impressions, source breakdown, etc."""
    __tablename__ = "post_insights"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("posts.id", ondelete="CASCADE"))
    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Reach
    accounts_reached: Mapped[int] = mapped_column(Integer, default=0)
    reach_follower_pct: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    reach_non_follower_pct: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)

    # Impressions / Views
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    from_home: Mapped[int] = mapped_column(Integer, default=0)
    from_profile: Mapped[int] = mapped_column(Integer, default=0)
    from_hashtags: Mapped[int] = mapped_column(Integer, default=0)
    from_explore: Mapped[int] = mapped_column(Integer, default=0)
    from_other: Mapped[int] = mapped_column(Integer, default=0)

    # Interactions
    total_interactions: Mapped[int] = mapped_column(Integer, default=0)
    interaction_follower_pct: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    saves: Mapped[int] = mapped_column(Integer, default=0)
    shares: Mapped[int] = mapped_column(Integer, default=0)

    # Profile activity driven by this post
    profile_visits: Mapped[int] = mapped_column(Integer, default=0)
    follows: Mapped[int] = mapped_column(Integer, default=0)

    post: Mapped["Post"] = relationship(back_populates="post_insights")

    __table_args__ = (
        Index("ix_post_insights_post_snapshot", "post_id", "snapshot_at"),
    )


class ProfileSnapshot(Base):
    __tablename__ = "profile_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"))
    follower_count: Mapped[int] = mapped_column(Integer, default=0)
    following_count: Mapped[int] = mapped_column(Integer, default=0)
    post_count: Mapped[int] = mapped_column(Integer, default=0)
    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    account: Mapped["Account"] = relationship(back_populates="profile_snapshots")

    __table_args__ = (
        Index("ix_profile_snapshots_account_at", "account_id", "snapshot_at"),
    )


class PostComment(Base):
    __tablename__ = "post_comments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("posts.id", ondelete="CASCADE"))
    platform_comment_id: Mapped[str] = mapped_column(String(255))
    username: Mapped[str] = mapped_column(String(255))
    text: Mapped[str] = mapped_column(Text)
    comment_like_count: Mapped[int] = mapped_column(Integer, default=0)
    reply_count: Mapped[int] = mapped_column(Integer, default=0)
    parent_comment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("post_comments.id", ondelete="CASCADE"), nullable=True)
    commented_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    post: Mapped["Post"] = relationship(back_populates="comments")

    __table_args__ = (
        UniqueConstraint("post_id", "platform_comment_id", name="uq_comment_post_platform_id"),
        Index("ix_post_comments_post_at", "post_id", "commented_at"),
    )
