# PRD: Instagram Post Insights Scraper

## Problem

Our current scraping pipeline captures **public-facing metrics** only: likes, comments, views, and shares. However, Instagram provides much richer **creator-only analytics** through its "View Insights" feature on each post. This data is critical for real content strategy analysis but we're not capturing it.

### What We're Missing

The insights page at `instagram.com/insights/media/{media_pk}/` exposes data that is **not available** through the standard feed/media API endpoints:

| Metric | Current Scraper | Insights Page |
|--------|:-:|:-:|
| Likes, comments, views | Yes | Yes |
| **Accounts reached** (total unique viewers) | No | Yes |
| **Reach by source** (Home, Profile, Hashtags, Explore, Other) | No | Yes |
| **Follower vs non-follower** reach breakdown (%) | No | Yes |
| **Impressions** (total, may exceed reach for repeat views) | No | Yes |
| **Interactions** (total profile visits, follows, etc. driven by post) | No | Yes |
| **Interaction follower/non-follower** breakdown (%) | No | Yes |
| **Saves** (accurate count, not just 0) | No | Yes |
| **Shares** (accurate count) | No | Yes |
| **Profile activity** from post (follows, profile visits) | No | Yes |
| **Content-type specific** (replies for stories, replays for reels) | No | Yes |

### Why This Matters

- **Reach vs impressions**: A post with 2K views but 1K unique accounts reached tells a very different story than 2K views from 2K unique accounts
- **Discovery source**: Knowing that 83% of views come from followers means the content isn't breaking out to new audiences — the #1 growth signal
- **Non-follower ratio**: The key metric for content virality. If >30% of reach is non-followers, the algorithm is pushing it
- **Saves/shares accuracy**: The feed API often returns 0 for saves/shares. Insights has the real numbers
- **AI diagnostic quality**: Our diagnostics currently analyze incomplete data. Adding insights transforms analysis from "your likes are above average" to "your reel reached 1,053 accounts, 83.5% followers — your content isn't reaching new audiences. Posts with explore-driven reach convert 3x better for follower growth"

## Research: Insights API Endpoint

### Known Endpoint

Instagram exposes insights data through a GraphQL-like API. Based on the web interface:

**URL pattern**: `https://www.instagram.com/insights/media/{media_pk}/`

This is a web page, not a JSON API. We need to investigate the underlying API call that populates this page.

### Likely API Endpoints to Investigate

1. **GraphQL media insights query**:
   - `https://www.instagram.com/graphql/query/` with `query_hash` for media insights
   - Requires session cookies (creator-only data)

2. **Private API v1 endpoint**:
   - `GET /api/v1/insights/media_organic_insights/{media_pk}/` (used by the mobile app)
   - Parameters: `ig_filters` (time period), `is_carousel_bumped_post`, `is_dash_eligible`

3. **Private API v1 alternative**:
   - `GET /api/v1/media/{media_pk}/insights/` (simpler path)

### Expected Response Structure

Based on Instagram's insights UI, the response likely contains:

```json
{
  "media_organic_insights": {
    "metrics": {
      "reach": {
        "value": 1053,
        "follower_percentage": 83.5,
        "non_follower_percentage": 16.5
      },
      "impressions": {
        "value": 2167,
        "sources": {
          "from_home": 1440,
          "from_profile": 476,
          "from_hashtags": 0,
          "from_explore": 0,
          "from_other": 10
        }
      },
      "interactions": {
        "value": 98,
        "follower_percentage": 72,
        "non_follower_percentage": 28,
        "breakdown": {
          "likes": 61,
          "comments": 11,
          "shares": 15,
          "saves": 11
        }
      },
      "profile_activity": {
        "profile_visits": 5,
        "follows": 1
      }
    }
  }
}
```

## Implementation Plan

### Phase 1: API Discovery & Validation

**Goal**: Find the exact API endpoint and confirm it works with session cookies.

1. **Browser network inspection**: Open `instagram.com/insights/media/{media_pk}/` in browser DevTools, capture the XHR/Fetch requests that load the data
2. **Identify the endpoint**: Document the exact URL, headers, and query parameters
3. **Test with httpx**: Verify the endpoint works with our existing session cookies (`INSTAGRAM_SESSION_ID` + `INSTAGRAM_CSRF_TOKEN`)
4. **Document response schema**: Map the full JSON response to our data model

**Deliverable**: A `scripts/test_insights_api.py` script that fetches insights for a single post and prints the parsed data.

### Phase 2: Database Schema Extension

**Goal**: Store insights data alongside existing metrics.

Option A — Extend `PostMetric` model:
```python
# Add to PostMetric model
reach: Mapped[int] = mapped_column(Integer, default=0)  # Already exists but always 0
reach_follower_pct: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
reach_non_follower_pct: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
impressions: Mapped[int] = mapped_column(Integer, default=0)
impression_source_home: Mapped[int] = mapped_column(Integer, default=0)
impression_source_profile: Mapped[int] = mapped_column(Integer, default=0)
impression_source_hashtags: Mapped[int] = mapped_column(Integer, default=0)
impression_source_explore: Mapped[int] = mapped_column(Integer, default=0)
impression_source_other: Mapped[int] = mapped_column(Integer, default=0)
interaction_follower_pct: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
profile_visits_from_post: Mapped[int] = mapped_column(Integer, default=0)
follows_from_post: Mapped[int] = mapped_column(Integer, default=0)
```

Option B — New `PostInsight` model (preferred, cleaner separation):
```python
class PostInsight(Base):
    __tablename__ = "post_insights"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    post_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"))
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

    post: Mapped["Post"] = relationship(back_populates="insights_data")
```

### Phase 3: Scraper Integration

**Goal**: Fetch insights during the sync pipeline.

1. **Add `fetch_post_insights()` to `scripts/ig_sync.py`**:
   - Called after fetching each post's comments
   - Uses the discovered API endpoint with session cookies
   - Respects rate limits (add 2-4s delay per insights fetch)
   - Only fetches for posts owned by the session user (insights are creator-only)

2. **Push insights data to backend**:
   - New endpoint: `POST /api/posts/{post_id}/insights`
   - Or extend existing sync data push to include `post_insights` array

3. **Rate limit considerations**:
   - Insights fetch = 1 additional API call per post
   - 50 posts × ~3s delay = ~2.5 min extra sync time
   - Consider: only fetch insights for recent posts (last 30 days) where data changes meaningfully
   - Consider: separate "insights sync" that can run independently

### Phase 4: Frontend Display

**Goal**: Show insights data on the post detail page.

1. **Post detail page** — New "Insights" section between Metrics and Comments:
   - **Reach card**: Total accounts reached + follower/non-follower bar chart
   - **Source breakdown**: Horizontal stacked bar showing Home/Profile/Hashtags/Explore/Other
   - **Interactions card**: Total interactions + follower/non-follower bar
   - **Profile activity**: Follows and profile visits driven by this post
   - **Discovery score**: Computed metric — `non_follower_reach_pct` as a key indicator

2. **Posts grid page** — Add discovery indicator:
   - Small icon/badge on posts where non-follower reach exceeds 25% (content breaking out)

3. **Dashboard summary** — Aggregate insights across recent posts:
   - Average non-follower reach %
   - Top discovery sources
   - Posts with highest non-follower ratio

### Phase 5: AI Integration

**Goal**: Feed insights data into diagnostics and copilot.

1. **AI Diagnostic enhancement**:
   - Include reach, source breakdown, and follower ratios in the diagnostic prompt
   - Add analysis of discovery potential: "Your content is primarily reaching existing followers (83.5%). To grow, focus on Explore-optimized content."
   - Compare reach sources against baseline

2. **Copilot tools**:
   - Extend `get_post_detail` to include insights data
   - New tool: `get_post_insights(post_id)` for detailed insights query
   - Copilot can now answer: "Which posts reached the most non-followers this month?" and "What content type gets the best explore distribution?"

3. **Recommendations engine**:
   - Factor in reach source data when generating recommendations
   - Flag posts that overindex on Profile traffic (captive audience) vs Explore/Hashtag (growth)
   - Recommend posting times/formats that correlate with higher non-follower reach

## Key Metrics Unlocked

| Metric | Business Value |
|--------|---------------|
| Non-follower reach % | **#1 growth indicator** — measures algorithm distribution |
| Impression sources | Tells you WHERE your content is being discovered |
| Accounts reached | True unique reach (not inflated by repeat views) |
| Saves (accurate) | Strongest engagement signal per Instagram's algorithm |
| Shares (accurate) | Virality indicator, currently underreported |
| Profile visits from post | Direct conversion metric — content → profile → follow |
| Follows from post | The ultimate ROI metric for each piece of content |

## Constraints & Risks

1. **Creator-only data**: Insights are only available for posts on accounts owned by the session user. Cannot fetch insights for competitor accounts.
2. **Rate limiting**: Additional API call per post. Budget for ~3s delay per post.
3. **API stability**: Instagram's private insights API may change without notice. Need robust error handling and fallback.
4. **Session scope**: The session cookies must belong to the account owner for insights to return data. Multi-account scenarios need per-account sessions.
5. **Minimum post age**: Instagram may not surface insights for very recent posts (< 24h).
6. **No migrations**: Schema changes require DB reset or manual `ALTER TABLE`. Plan column additions to be nullable with defaults.

## Success Criteria

- [ ] Insights data captured for 50 most recent posts during sync
- [ ] Post detail page shows reach, source breakdown, and follower ratios
- [ ] AI diagnostics reference insights data when available
- [ ] Copilot can answer questions about reach and discovery patterns
- [ ] Non-follower reach % surfaced as a key metric in dashboard and recommendations
- [ ] No increase in Instagram rate limit violations (verified over 1 week)

## Priority

**High** — This unlocks the most impactful data gap in the platform. The difference between "likes-based analysis" and "reach + discovery analysis" is the difference between a vanity metrics tool and a real growth engine.
