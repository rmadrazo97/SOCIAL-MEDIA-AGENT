# PRD: Instagram Web Session Scraper

## Problem

The current Instagram integration uses `instagrapi` (private mobile API), which gets blocked by Instagram's IP blacklisting when running from Docker/datacenter IPs. The user has approved login challenges, but the container IP is permanently flagged. We need a reliable alternative that uses the user's authenticated browser session to fetch real data.

## Validated Approach

We tested and confirmed that Instagram's web API endpoints work when called with the user's browser session cookies (`sessionid` + `csrftoken`). These endpoints return structured JSON with full profile, post, and engagement data.

### Proven Endpoints

| Endpoint | Purpose | Status |
|---|---|---|
| `GET /api/v1/users/{user_id}/info/` | Profile info (followers, bio, posts count) | ✅ Verified |
| `GET /api/v1/feed/user/{user_id}/` | Paginated post feed with metrics | ✅ Verified (12/page, cursor pagination) |
| `GET /api/v1/media/{media_pk}/info/` | Individual post detail (carousel slides, tags) | ✅ Verified |
| `GET /api/v1/media/{media_pk}/comments/` | Post comments with threading | ✅ Verified |
| CDN URLs from media responses | Image/video binary download | ✅ Verified (JPEG, MP4) |

### Data Available Per Post

- **Engagement**: likes, comments, views (reels), shares (when available)
- **Content**: caption, post type (image/carousel/reel/video), permalink, timestamp
- **Media**: Full resolution images (1440px), video files (MP4), thumbnails
- **Carousel**: Individual slide media with type detection
- **Comments**: Author, text, timestamp, like count, reply count
- **Tags**: Tagged users per post
- **Location**: Name and city (when tagged)

## Architecture

### New Scraper: `instagram_web_scraper.py`

Replaces `instagrapi`-based scraper with `httpx`-based web API client.

**Key design decisions:**
1. **Runs from host machine** — Uses residential IP (not Docker) to avoid blocks
2. **Session cookie auth** — `INSTAGRAM_SESSION_ID` + `INSTAGRAM_CSRF_TOKEN` from `.env`
3. **Human-like request patterns** — Random delays (2-5s between requests), proper browser headers, sequential post fetching
4. **Progressive fetching** — On first sync: fetch all posts. On subsequent syncs: fetch only new posts (stop when we hit an already-known `platform_post_id`)
5. **Media download** — Downloads images/videos to local storage for multimodal AI analysis

### Data Pipeline

```
Manual Sync (dashboard button) or Cron (every 6h)
  │
  ├─ 1. Fetch profile info → Update Account (follower_count, following_count, bio, etc.)
  │     └─ Store ProfileSnapshot (follower_count, following_count, post_count at timestamp)
  │
  ├─ 2. Fetch post feed (paginated, with delays)
  │     ├─ Progressive: stop at last known post
  │     ├─ For each new post:
  │     │   ├─ Create/update Post record
  │     │   ├─ Create PostMetric snapshot (likes, comments, views, shares)
  │     │   └─ Download media → /data/media/{account}/{post_id}/
  │     └─ For existing posts (first N):
  │         └─ Create new PostMetric snapshot (track metric changes over time)
  │
  └─ 3. Fetch comments for recent posts (optional, configurable)
        └─ Store in PostComment table
```

### Storage Structure

```
/data/media/
  └─ {account_username}/
      └─ {platform_post_id}/
          ├─ image_1.jpg          # Carousel slide 1 or single image
          ├─ image_2.jpg          # Carousel slide 2
          ├─ video.mp4            # Reel/video content
          └─ thumbnail.jpg        # Video thumbnail
```

## Schema Changes

### New Model: `ProfileSnapshot`

Tracks account-level metrics over time for growth analysis.

```python
class ProfileSnapshot(Base):
    id: UUID (PK)
    account_id: UUID (FK → Account, cascade)
    follower_count: int
    following_count: int
    post_count: int
    snapshot_at: datetime (default=now, indexed)
```

### New Model: `PostComment`

Stores comments for sentiment analysis and engagement understanding.

```python
class PostComment(Base):
    id: UUID (PK)
    post_id: UUID (FK → Post, cascade)
    platform_comment_id: str (unique per post)
    username: str
    text: text
    comment_like_count: int (default=0)
    reply_count: int (default=0)
    parent_comment_id: UUID (nullable, FK → self, for replies)
    commented_at: datetime
    created_at: datetime (default=now)
```

### Updated Model: `Post`

Add fields for richer data:

```python
# New columns on Post:
location_name: str (nullable)
tagged_users: JSONB (nullable)  # ["user1", "user2"]
media_stored: bool (default=False)  # Whether media files are downloaded
carousel_count: int (default=0)  # Number of slides if carousel
video_duration: float (nullable)  # Duration in seconds for reels/videos
```

### Updated Model: `Account`

Add fields for web session tracking:

```python
# New columns on Account:
following_count: int (nullable)
biography: text (nullable)
platform_user_id: str (nullable)  # Already exists, ensure populated
profile_pic_url: text (nullable)
last_sync_at: datetime (nullable)
```

## Sync Behavior

### Manual Sync (Dashboard Button)

1. User clicks "Sync" on an account in the dashboard
2. Backend triggers background sync task
3. Frontend polls or receives status updates
4. Sync fetches profile → new posts → metrics for recent posts → media download

### Scheduled Sync (Cron)

- **Frequency**: Every 6 hours (reduced from 2h to be gentler on Instagram)
- **Scope**: All active Instagram accounts
- **Behavior**: Same as manual sync but automatic

### Progressive Post Fetching

**First sync** (no posts in DB):
- Fetch ALL posts via pagination (12 per page, with 3-5s delays between pages)
- Download media for all posts
- Create metric snapshots for all posts

**Subsequent syncs**:
- Fetch feed pages until we encounter a `platform_post_id` already in DB
- Create new Post records for new content
- For the most recent N existing posts (configurable, default=20), create fresh PostMetric snapshots to track metric changes over time
- Download media only for new posts

### Rate Limiting & Anti-Detection

- **Inter-request delay**: Random 2-5 seconds between API calls
- **Inter-page delay**: Random 4-8 seconds between pagination requests
- **Media download delay**: Random 1-3 seconds between downloads
- **Batch size**: Max 50 posts per sync session (configurable)
- **Browser headers**: Full Chrome header set including Sec-Fetch-*, User-Agent, X-IG-App-ID
- **Session validation**: Check session validity before starting sync; warn user if expired

### Session Management

- Cookies stored in `.env` (`INSTAGRAM_SESSION_ID`, `INSTAGRAM_CSRF_TOKEN`)
- Session validation endpoint check before each sync
- If session expires: sync fails gracefully with clear error message in dashboard
- Future: Could add a settings page to update session cookies from the UI

## API Endpoints

### New Endpoints

```
POST /api/accounts/{id}/sync          # Already exists — update to use new scraper
GET  /api/accounts/{id}/profile-history  # ProfileSnapshot time series
GET  /api/posts/{id}/comments         # List comments for a post
GET  /api/accounts/{id}/growth        # Follower/following growth over time
```

### Updated Endpoints

```
GET /api/accounts/{id}                # Include new fields (bio, following_count, etc.)
GET /api/posts/{id}                   # Include new fields (location, tags, media_stored)
GET /api/posts/{id}/media             # Serve stored media files
```

## Frontend Changes

### Accounts Page

- Show `last_sync_at` per account
- Show session status indicator (valid/expired)
- Sync button shows progress: "Syncing... (12/48 posts)"

### Post Detail Page

- Display stored media (images/carousel/video) inline
- Show comments section
- Show location and tagged users
- Display metric history chart (likes/comments over time from PostMetric snapshots)

### New: Account Growth Page

- Follower/following count over time (from ProfileSnapshot)
- Posts per week/month trend
- Average engagement rate trend

## Implementation Order

### Phase 1: Core Scraper + Schema
1. Add new DB models (ProfileSnapshot, PostComment) and Post/Account column additions
2. Build `instagram_web_scraper.py` with httpx
3. Update `sync_service.py` to use new scraper
4. Add media download pipeline
5. Test end-to-end with alexmadrazo97

### Phase 2: Progressive Sync + Scheduling
6. Implement progressive post detection (stop at known posts)
7. Implement metric re-snapshot for existing posts
8. Update scheduler for 6h Instagram sync interval
9. Add ProfileSnapshot recording on each sync

### Phase 3: API + Frontend
10. Add new API endpoints (profile-history, comments, growth, media serving)
11. Update frontend account/post pages with new data
12. Add sync status/progress feedback in UI

### Phase 4: Analytics Foundation
13. Comments stored for future sentiment analysis
14. Media stored for future multimodal AI analysis
15. ProfileSnapshot history enables growth tracking
16. Enhanced baselines using richer metric data

## Configuration

```env
# .env additions
INSTAGRAM_SESSION_ID=<from browser>
INSTAGRAM_CSRF_TOKEN=<from browser>
INSTAGRAM_SYNC_DELAY_MIN=2        # Min seconds between requests (default: 2)
INSTAGRAM_SYNC_DELAY_MAX=5        # Max seconds between requests (default: 5)
INSTAGRAM_SYNC_BATCH_SIZE=50      # Max posts per sync session (default: 50)
INSTAGRAM_MEDIA_DIR=/data/media   # Media storage path (default: /data/media)
```

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Session cookie expires | Clear error in dashboard; instructions to refresh from browser |
| Instagram changes API format | Response parsing with fallbacks; log unknown fields |
| Rate limiting (429) | Exponential backoff; abort sync and resume later |
| Large accounts (1000+ posts) | Batch size limit; spread initial sync across multiple runs |
| Media storage disk space | Configurable media download (on/off); cleanup old media |
| CDN URLs expire | Re-fetch media URL from post info if download fails |
