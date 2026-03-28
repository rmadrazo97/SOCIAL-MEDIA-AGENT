# PRD-04: Data Ingestion & Analytics Engine

## Domain
Metrics collection pipeline, baseline calculations, performance scoring, trend detection.

## Dependencies
- PRD-01 (database schema)
- PRD-03 (platform API clients)

## Goal
Continuously collect post metrics, compute creator baselines, and detect performance patterns that feed into the AI layer.

---

## 1. Data Collection Pipeline

### Trigger Points
1. **On account connect:** Fetch last 20 posts + metrics (backfill)
2. **On new post detected:** Schedule metric snapshots at +15min, +2h, +24h, +48h
3. **Periodic sync:** Every 6 hours, refresh metrics for posts < 7 days old
4. **Daily rollup:** Compute daily account-level aggregates

### API Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/api/accounts/{id}/metrics` | Account-level metrics summary | Token |
| GET | `/api/accounts/{id}/metrics/history` | Time-series metrics (7/30 days) | Token |
| GET | `/api/posts/{id}/metrics` | Post metric snapshots over time | Token |
| GET | `/api/accounts/{id}/posts` | List posts with latest metrics | Token |
| GET | `/api/accounts/{id}/baseline` | Current baseline values | Token |
| POST | `/api/accounts/{id}/sync` | Trigger manual sync | Token |

## 2. Metrics Collection Service

```python
class MetricsCollector:
    async def backfill_account(self, account_id: str) -> dict:
        """Fetch historical posts and metrics for newly connected account."""

    async def sync_recent_posts(self, account_id: str) -> dict:
        """Refresh metrics for posts less than 7 days old."""

    async def detect_new_posts(self, account_id: str) -> list[Post]:
        """Compare platform posts with DB, return new ones."""

    async def snapshot_post_metrics(self, post_id: str) -> PostMetric:
        """Capture current metrics for a single post."""
```

## 3. Baseline Calculation

The baseline is the creator's "normal" performance. Everything is compared against it.

### Baseline Model
```python
@dataclass
class AccountBaseline:
    account_id: str
    computed_at: datetime
    period_days: int  # typically 30

    avg_views: float
    median_views: float
    avg_likes: float
    avg_comments: float
    avg_shares: float
    avg_saves: float
    avg_engagement_rate: float

    # By post type
    by_type: dict[str, BaselineByType]  # e.g., 'reel', 'image', 'carousel'

    # By day of week
    by_day: dict[int, BaselineByDay]  # 0=Monday, 6=Sunday

    # By hour of day
    by_hour: dict[int, BaselineByHour]
```

### Calculation Logic
1. Take last 30 days of posts (or all posts if < 30 days)
2. Exclude outliers (> 3 standard deviations)
3. Compute averages, medians per metric
4. Segment by post type, day of week, hour
5. Store in `account_baselines` table (or JSONB column)
6. Recompute daily

### Storage

**account_baselines** table
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| account_id | UUID | FK → accounts.id |
| computed_at | TIMESTAMPTZ | |
| period_days | INTEGER | |
| baseline_data | JSONB | Full baseline object |

## 4. Performance Scoring

Each post gets a performance score relative to the baseline.

### Score Calculation
```python
def calculate_performance_score(post_metrics: PostMetric, baseline: AccountBaseline) -> float:
    """
    Returns a score from 0-100 where:
    - 50 = average (at baseline)
    - 75+ = above average
    - 90+ = viral/breakout
    - 25- = underperforming
    """
    factors = {
        'views': (post_metrics.views / baseline.avg_views) * weight_views,
        'engagement': (post_metrics.engagement_rate / baseline.avg_engagement_rate) * weight_engagement,
        'shares': (post_metrics.shares / baseline.avg_shares) * weight_shares,
    }
    raw_score = weighted_average(factors)
    return normalize_to_100(raw_score)
```

### Score is stored in `post_metrics.performance_score` (add column).

## 5. Trend Detection

Detect patterns over time to feed the AI layer.

### Trends We Track
| Trend | Logic |
|-------|-------|
| Growth/Decline | Compare this week avg vs last week avg |
| Best performing type | Which post_type has highest avg score |
| Best posting time | Which day/hour combo has best performance |
| Engagement shift | Is engagement rate trending up or down |
| Viral posts | Posts > 2x baseline views |

### Trend Output
```python
@dataclass
class TrendAnalysis:
    account_id: str
    period: str  # 'weekly', 'monthly'
    computed_at: datetime

    overall_direction: str  # 'growing', 'stable', 'declining'
    growth_rate: float  # percentage change
    best_post_type: str
    best_posting_day: int
    best_posting_hour: int
    viral_posts: list[str]  # post IDs
    engagement_trend: str  # 'up', 'stable', 'down'
    notable_changes: list[str]  # human-readable observations
```

## 6. Account-Level Aggregates

### Daily Aggregate
Computed once per day for each account:
```json
{
  "date": "2026-03-28",
  "total_views": 45000,
  "total_likes": 3200,
  "total_comments": 150,
  "total_shares": 89,
  "new_posts": 2,
  "avg_performance_score": 62,
  "follower_delta": "+120"
}
```

### 7-Day Rolling Metrics (for dashboard)
```json
{
  "period": "7d",
  "total_views": 320000,
  "avg_daily_views": 45714,
  "total_engagement": 25000,
  "avg_engagement_rate": 0.078,
  "top_post_id": "uuid",
  "posts_count": 12,
  "vs_baseline": "+15%"
}
```

## 7. Data Flow Diagram

```
Platform APIs
     │
     ▼
MetricsCollector ──→ posts + post_metrics tables
     │
     ▼
BaselineCalculator ──→ account_baselines table
     │
     ▼
PerformanceScorer ──→ updates post_metrics.performance_score
     │
     ▼
TrendDetector ──→ trend_analyses table / feeds AI layer
     │
     ▼
AggregateBuilder ──→ daily_aggregates table / feeds dashboard
```

## 8. Acceptance Criteria

- [ ] Backfill fetches last 20 posts on account connect
- [ ] New posts are detected within 1 hour
- [ ] Metric snapshots are captured at scheduled intervals (+15m, +2h, +24h)
- [ ] Baseline is computed from last 30 days of data
- [ ] Baseline recomputes daily
- [ ] Performance score calculated for each metric snapshot
- [ ] 7-day rolling metrics available via API
- [ ] Trend analysis runs weekly
- [ ] Manual sync endpoint triggers immediate data refresh
- [ ] All metrics endpoints return data within 500ms

## 9. Out of Scope (MVP)
- Real-time websocket updates for metrics
- Competitor benchmarking
- Cross-platform unified metrics
- Historical data older than 90 days
