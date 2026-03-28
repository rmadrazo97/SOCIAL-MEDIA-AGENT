# CLAUDE.md — Agent Development Guide

This file is the primary reference for AI coding agents working on this project.
Read this before making any changes.

## Project Summary

AI Social Media Command Center — monitors Instagram & TikTok creator accounts,
scrapes engagement data, computes performance baselines, and generates AI-powered
daily briefs, recommendations, and content remixes.

**Owner**: Personal project (single user), not a team app.

## How to Run

```bash
docker compose up --build -d      # Start everything
docker compose logs backend -f    # Watch backend logs
docker compose logs frontend -f   # Watch frontend logs
docker compose down               # Stop everything
```

- Frontend: http://localhost:3001
- Backend API: http://localhost:8001
- PostgreSQL: localhost:5433 (user: smadmin, db: social_media_agent)
- Redis: localhost:6380

The frontend proxies `/api/*` to the backend via Next.js rewrites (see `frontend/next.config.js`).
A single `ngrok http 3001` exposes the full app publicly.

## Tech Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2.0 (async + asyncpg), Pydantic v2, APScheduler
- **Frontend**: Next.js 15 (App Router), TypeScript, Tailwind CSS, SWR
- **Database**: PostgreSQL 16, Redis 7
- **AI**: Moonshot/Kimi API (OpenAI-compatible client at `https://api.moonshot.cn/v1`, model `moonshot-v1-8k`)
- **Scraping**: instagrapi (Instagram), httpx + BeautifulSoup (TikTok)
- **Infra**: Docker Compose with hot reload

## Architecture

```
Browser → Next.js (3001) → [/api/* rewrite] → FastAPI (8001) → PostgreSQL (5432)
                                                     ↓
                                              APScheduler (cron)
                                                     ↓
                                        Instagram scraper / TikTok scraper
                                                     ↓
                                              Moonshot AI API
```

Auth is a simple password string (`APP_PASSWORD` in `.env`) sent as `X-App-Password` header.
There are no user accounts, sessions, or JWTs.

## File Map

### Backend (`backend/app/`)

| File | Purpose |
|------|---------|
| `main.py` | FastAPI app, CORS, router registration, lifespan (scheduler) |
| `config.py` | `Settings(BaseSettings)` — all env vars loaded here |
| `database.py` | Async SQLAlchemy engine, `get_db()` dependency |
| `init_db.py` | Creates tables on startup (called in docker CMD) |
| `models/models.py` | 7 SQLAlchemy models: Account, Post, PostMetric, Insight, Recommendation, DailyBrief, AccountBaseline |
| `schemas/schemas.py` | All Pydantic request/response schemas |
| `api/auth.py` | `POST /api/auth/login` |
| `api/accounts.py` | CRUD for accounts |
| `api/posts.py` | CRUD for posts + metrics |
| `api/insights.py` | AI diagnostic generation |
| `api/recommendations.py` | List + status update for recommendations |
| `api/briefs.py` | Daily brief CRUD + generation |
| `api/metrics.py` | Aggregated metrics + baselines |
| `api/remix.py` | Content remix generation |
| `api/csv_import.py` | CSV bulk import |
| `api/sync.py` | Manual sync triggers |
| `api/deps.py` | `verify_password()` — FastAPI dependency |
| `integrations/instagram_scraper.py` | instagrapi wrapper (login, profile, posts) |
| `integrations/tiktok_scraper.py` | httpx scraper (HTML extraction + oembed fallback) |
| `services/sync_service.py` | Orchestrates scraping → DB upsert pipeline |
| `services/ai_service.py` | Moonshot API calls (briefs, diagnostics, recommendations, remixes) |
| `services/baseline_service.py` | 30-day baseline computation |
| `services/brief_worker.py` | Batch brief + recommendation generation |
| `workers/scheduler.py` | APScheduler job setup (4 cron jobs) |

### Frontend (`frontend/src/`)

| File | Purpose |
|------|---------|
| `lib/api.ts` | `ApiClient` class — all HTTP calls, password auth, auto-logout |
| `lib/hooks.ts` | SWR hooks: `useAccounts`, `usePosts`, `useAccountMetrics`, etc. |
| `app/page.tsx` | Root redirect to `/login` or `/dashboard` |
| `app/login/page.tsx` | Password login form |
| `app/dashboard/page.tsx` | Main dashboard: metrics cards, brief, recommendations, recent posts |
| `app/dashboard/layout.tsx` | Dashboard shell with sidebar navigation |
| `app/dashboard/accounts/page.tsx` | Account management: add, sync, CSV import, delete |
| `app/dashboard/posts/page.tsx` | Posts table with filtering |
| `app/dashboard/posts/[id]/page.tsx` | Post detail: metrics, history, AI diagnostic, remix |
| `app/dashboard/recommendations/page.tsx` | Recommendations with accept/dismiss |
| `app/dashboard/settings/page.tsx` | Settings page |
| `components/layout/DashboardLayout.tsx` | Sidebar + header layout component |

## Database Models

All models use UUID primary keys. All timestamps are timezone-aware.

### Account
- `platform` (string): "instagram" or "tiktok"
- `username` (string): unique per platform
- `follower_count` (int, nullable)
- `status` (string): "active" (default)
- Unique constraint: `(platform, username)`

### Post
- `account_id` → Account (cascade delete)
- `platform_post_id` (string): ID from the platform
- `post_type`: "image", "carousel", "reel", "video"
- `caption`, `media_url`, `permalink` (text)
- `posted_at` (datetime)
- Unique constraint: `(account_id, platform_post_id)`

### PostMetric
- `post_id` → Post (cascade delete)
- `snapshot_at` (datetime, default now)
- `views`, `likes`, `comments`, `shares`, `saves`, `reach` (int)
- `engagement_rate` (numeric 7,4)
- `performance_score` (numeric 5,2, nullable)
- Index: `(post_id, snapshot_at)`

### Insight
- `post_id` → Post (nullable, cascade)
- `account_id` → Account (cascade)
- `insight_type`: "diagnostic"
- `content` (text), `metadata_json` (JSONB)

### Recommendation
- `account_id` → Account (cascade)
- `recommendation_type`: "content_idea", "timing", "hashtag", "format", "engagement", "remix"
- `title`, `content` (text)
- `priority` (int 1-5)
- `status`: "pending", "accepted", "dismissed"

### DailyBrief
- `account_id` → Account (cascade)
- `brief_date` (date) — unique per account per day
- `content` (text, markdown)
- `metrics_snapshot` (JSONB)

### AccountBaseline
- `account_id` → Account (cascade)
- `period_days` (int, default 30)
- `baseline_data` (JSONB): `{avg_views, avg_likes, avg_comments, avg_shares, avg_saves, avg_engagement_rate, post_count, median_views, by_type, by_day, by_hour}`

## API Conventions

- All endpoints except `/api/auth/login` and `/health` require the `X-App-Password` header
- Responses are JSON; errors return `{"detail": "message"}`
- 401 = bad password, 404 = not found, 204 = deleted
- List endpoints return arrays directly (not paginated wrappers)
- Posts endpoints return `PostWithMetrics` which includes `latest_metrics` (most recent PostMetric snapshot)
- Background tasks (sync, briefs) return `{"status": "..._started"}` immediately

## Scheduler Jobs

Defined in `backend/app/workers/scheduler.py`:

1. **sync_all** — `IntervalTrigger(hours=2)`, runs immediately on startup
2. **baselines** — `CronTrigger(hour=3)` (3:00 AM UTC)
3. **briefs** — `CronTrigger(hour=7)` (7:00 AM UTC)
4. **recommendations** — `CronTrigger(hour=7, minute=30)` (7:30 AM UTC)

## Scraping Details

### Instagram (`integrations/instagram_scraper.py`)
- Uses `instagrapi.Client` — Instagram's private mobile API
- Requires `INSTAGRAM_USERNAME` + `INSTAGRAM_PASSWORD` in `.env`
- Session persisted to `/app/ig_session.json` inside the container
- May trigger Instagram challenge (2FA) on first Docker login
- Methods: `get_profile(username)`, `get_recent_posts(username, limit)`, `get_post_insights(media_pk)`

### TikTok (`integrations/tiktok_scraper.py`)
- Uses `httpx` — pure HTTP, no browser
- No credentials needed
- Primary: extracts `__UNIVERSAL_DATA_FOR_REHYDRATION__` JSON from page HTML
- Fallback: TikTok oembed API (profile name only, no metrics)
- **TikTok blocks datacenter IPs** — from Docker, only oembed works unless `TIKTOK_PROXY` is set
- Methods: `get_profile(username)`, `get_recent_videos(username, limit)`

## AI Service (`services/ai_service.py`)

- Uses OpenAI Python client pointed at `https://api.moonshot.cn/v1`
- Model: `moonshot-v1-8k`
- Falls back to mock/template responses if API key is missing or call fails
- All prompts request JSON responses
- Methods: `generate_diagnostic()`, `generate_daily_brief()`, `generate_recommendations()`, `generate_remix()`

## Environment Variables

Required in `.env` at project root:

```
POSTGRES_USER=smadmin
POSTGRES_PASSWORD=<db_password>
POSTGRES_DB=social_media_agent
APP_PASSWORD=<dashboard_login_password>
REDIS_URL=redis://redis:6380/0
MOONSHOT_API_KEY=<kimi_api_key>
INSTAGRAM_USERNAME=<ig_username>
INSTAGRAM_PASSWORD=<ig_password>
ENCRYPTION_KEY=<32_byte_key>
```

Optional:
```
TIKTOK_PROXY=http://user:pass@host:port
TIKTOK_CLIENT_KEY=
TIKTOK_CLIENT_SECRET=
```

## UI Design

- Color palette: Bone (#EBE3D2), Dun (#CCBFA3), Sage (#A4AC86), Reseda Green (#737A5D), Ebony (#414833)
- Defined in `frontend/tailwind.config.js` as custom colors
- Dark/muted nature theme — use `bg-ebony`, `text-bone`, `border-dun`, `bg-reseda`, `text-sage` etc.
- Icons: Lucide React
- No external UI library — plain Tailwind + custom components

## Development Patterns

### Adding a new API endpoint
1. Add Pydantic schema in `backend/app/schemas/schemas.py`
2. Add route in appropriate `backend/app/api/*.py` file
3. Register router in `backend/app/main.py` if new file
4. Add corresponding method in `frontend/src/lib/api.ts`
5. Add SWR hook in `frontend/src/lib/hooks.ts` if needed

### Adding a new model
1. Define in `backend/app/models/models.py` (extends `Base`)
2. Add schema in `backend/app/schemas/schemas.py`
3. Tables auto-create on startup via `init_db.py`

### Adding a new platform scraper
1. Create `backend/app/integrations/<platform>_scraper.py`
2. Implement `get_profile(username)` and `get_recent_posts(username, limit)`
3. Add platform routing in `sync_service.py._scrape_profile()` and `_scrape_posts()`

### Adding a new AI feature
1. Add method to `backend/app/services/ai_service.py`
2. Define system + user prompt templates
3. Return structured JSON from the LLM
4. Add API endpoint to expose it

## Slash Commands (`.claude/commands/`)

These are available as `/command` in Claude Code:

| Command | Purpose |
|---------|---------|
| `/status` | Check health of all services and data counts |
| `/deploy` | Build, restart, and verify the stack after changes |
| `/sync` | Trigger data sync and report results |
| `/debug` | Debug an issue — gathers logs, checks services, tests endpoints |
| `/review` | Review recent changes for correctness and completeness |
| `/feature` | Plan and implement a full feature end-to-end |
| `/add-endpoint` | Add a new API endpoint (schema → route → frontend) |
| `/add-model` | Add a new database model with schema and migration |
| `/add-page` | Add a new frontend dashboard page |
| `/add-platform` | Add support for a new social media platform |
| `/add-ai-feature` | Add a new AI-powered feature |
| `/db-inspect` | Inspect database tables, counts, and recent activity |

## Makefile Targets

Run `make help` for the full list. Key targets:

```bash
make up                # Start all services
make build             # Build and start (after Dockerfile changes)
make logs              # Tail all logs
make logs-backend      # Tail backend logs only
make status            # Container health + API check
make sync-all          # Trigger sync for all accounts
make baselines         # Recompute performance baselines
make briefs            # Generate AI daily briefs
make recs              # Generate AI recommendations
make db-shell          # Open psql shell
make db-counts         # Show row counts for all tables
make db-reset          # Drop and recreate tables (DESTRUCTIVE)
make db-dump           # Backup database to SQL file
make seed              # Populate DB with sample data
make tunnel            # Expose frontend via ngrok
make clean             # Remove containers, volumes, build cache
```

## Scripts (`scripts/`)

| Script | Purpose |
|--------|---------|
| `health_check.sh` | Full health check with colored output |
| `backup_db.sh` | Backup database to `backups/` (keeps last 10) |
| `restore_db.sh` | Restore database from a backup file |
| `seed_sample_data.py` | Populate DB with sample posts and metrics |

## Common Commands

```bash
# Rebuild after backend dependency change
docker compose up --build -d backend

# Run a one-off Python command in the backend container
docker compose exec backend python -c "..."

# Access PostgreSQL directly
docker compose exec db psql -U smadmin -d social_media_agent

# Trigger manual sync
curl -X POST http://localhost:8001/api/sync/all -H "X-App-Password: admin123"

# Trigger baseline recomputation
curl -X POST http://localhost:8001/api/sync/baselines -H "X-App-Password: admin123"

# Check scheduler status
docker compose logs backend --tail 20 | grep -i "scheduler\|cron\|sync"
```

## Known Limitations

1. **TikTok from Docker**: TikTok blocks datacenter IPs. The scraper falls back to oembed (profile name only). Set `TIKTOK_PROXY` with a residential proxy for full data.
2. **Instagram challenge**: First login from Docker triggers Instagram's device verification. User must approve via the Instagram app or temporarily disable 2FA.
3. **No migrations**: Tables are created via `Base.metadata.create_all()`. Schema changes require manual migration or DB reset.
4. **Single user**: No multi-user support. One password, one session.
5. **AI key**: Moonshot API key may expire. The AI service gracefully falls back to mock responses.
