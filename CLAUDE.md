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

The frontend proxies `/api/*` and `/copilotkit/*` to the backend via Next.js rewrites (see `frontend/next.config.js`).
A single `ngrok http 3001` exposes the full app publicly.

## Tech Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2.0 (async + asyncpg), Pydantic v2, APScheduler
- **Frontend**: Next.js 15 (App Router), TypeScript, Tailwind CSS, SWR
- **Database**: PostgreSQL 16, Redis 7
- **AI**: Moonshot/Kimi API (OpenAI-compatible client at `https://api.moonshot.ai/v1`, model `moonshot-v1-8k`)
- **Co-Pilot Agent**: LangGraph + CopilotKit (floating chat widget, LangChain tools for data access)
- **Scraping**: instagrapi (Instagram), httpx + BeautifulSoup (TikTok)
- **Infra**: Docker Compose with hot reload

## Architecture

```
Browser → Next.js (3001) → [/api/* rewrite] → FastAPI (8001) → PostgreSQL (5432)
                         → [/copilotkit/* rewrite] → CopilotKit SDK (FastAPI)
                                                     ↓
                                              LangGraph Co-Pilot Agent
                                              (17 tools: query + action)
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
| `models/models.py` | 11 SQLAlchemy models: Account, Post, PostMetric, PostInsight, PostComment, Insight, Recommendation, DailyBrief, AccountBaseline, Artifact, AgentConversation, AgentMemoryEntry |
| `schemas/schemas.py` | All Pydantic request/response schemas |
| `api/auth.py` | `POST /api/auth/login` |
| `api/accounts.py` | CRUD for accounts |
| `api/posts.py` | CRUD for posts + metrics + public media serving endpoints |
| `api/insights.py` | AI diagnostic generation (includes comments + Instagram Insights) |
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
| `agent/copilot.py` | LangGraph Co-Pilot agent definition (StateGraph + CopilotKitState) |
| `agent/tools/query_tools.py` | 11 read-only tools: accounts, posts, metrics, baselines, briefs, recommendations, artifacts, post insights, comments, media analysis |
| `agent/tools/action_tools.py` | 6 action tools: sync, diagnostic, brief generation, recommendation status, artifact CRUD |
| `agent/prompts/system.py` | Co-Pilot system prompt (persona, guidelines, capabilities) |
| `api/agent.py` | `register_copilotkit()` — registers CopilotKit SDK endpoint on FastAPI |
| `api/artifacts.py` | CRUD endpoints for artifacts (content ideas, strategies, reports, etc.) |

### Frontend (`frontend/src/`)

| File | Purpose |
|------|---------|
| `lib/api.ts` | `ApiClient` class — all HTTP calls, password auth, auto-logout |
| `lib/hooks.ts` | SWR hooks: `useAccounts`, `usePosts`, `useAccountMetrics`, etc. |
| `app/page.tsx` | Root redirect to `/login` or `/dashboard` |
| `app/login/page.tsx` | Password login form |
| `app/dashboard/page.tsx` | Main dashboard: metrics cards, brief, recommendations, recent posts |
| `app/dashboard/layout.tsx` | Dashboard shell with CopilotKit provider + floating chat popup |
| `app/dashboard/accounts/page.tsx` | Account management: add, sync, CSV import, delete |
| `app/dashboard/posts/page.tsx` | Instagram-style 3-column grid with thumbnails, hover metric overlays, type filters |
| `app/dashboard/posts/[id]/page.tsx` | Post detail: media gallery, metrics, history, comments, Instagram Insights, AI diagnostic, remix |
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

### PostInsight
- `post_id` → Post (cascade delete)
- `snapshot_at` (datetime, default now)
- `accounts_reached`, `impressions`, `total_interactions` (int)
- `reach_follower_pct`, `reach_non_follower_pct`, `interaction_follower_pct` (numeric)
- Impression sources: `from_home`, `from_profile`, `from_hashtags`, `from_explore`, `from_other` (int)
- `saves`, `shares`, `profile_visits`, `follows` (int)
- Creator-only data scraped from Instagram Insights (`/insights/media/{media_pk}/`)

### PostComment
- `post_id` → Post (cascade delete)
- `platform_comment_id` (string)
- `username` (string), `text` (text)
- `comment_like_count`, `reply_count` (int)
- `commented_at` (datetime)
- Unique constraint: `(post_id, platform_comment_id)`

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

### Artifact
- `account_id` → Account (cascade, nullable)
- `artifact_type` (string): "content_idea", "copy_draft", "strategy", "report", "trend_analysis", "task"
- `title` (string), `content` (text), `metadata_json` (JSONB)
- `status` (string): "active", "archived", "completed"

### AgentConversation
- `thread_id` (string, unique): LangGraph thread ID
- `account_id` → Account (cascade, nullable)
- `summary` (text, nullable)

### AgentMemoryEntry
- `account_id` → Account (cascade, nullable)
- `memory_type` (string): "creator_profile", "insight", "preference", "pattern"
- `key` (string, indexed), `content` (text)
- `confidence` (numeric 3,2, default 1.0)

## API Conventions

- All endpoints except `/api/auth/login`, `/health`, and media serving endpoints require the `X-App-Password` header
- Media endpoints (`/api/posts/{id}/media/*`) are public (no auth) because `<img>`/`<video>` tags can't send custom headers
- Responses are JSON; errors return `{"detail": "message"}`
- 401 = bad password, 404 = not found, 204 = deleted
- List endpoints return arrays directly (not paginated wrappers)
- Posts endpoints return `PostWithMetrics` which includes `latest_metrics` (most recent PostMetric snapshot) and `latest_insight` (most recent PostInsight)
- Background tasks (sync, briefs) return `{"status": "..._started"}` immediately
- CopilotKit agent endpoint at `/copilotkit` (registered by `register_copilotkit()`, not a standard API router)
- Artifact CRUD at `/api/artifacts` (GET, POST, PATCH, DELETE)

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

- Uses OpenAI Python client pointed at `https://api.moonshot.ai/v1`
- Model: `moonshot-v1-8k`
- Falls back to mock/template responses if API key is missing or call fails
- All prompts request JSON responses
- Methods: `generate_diagnostic()` (with comments + insights), `generate_daily_brief()`, `generate_recommendations()`, `generate_remix()`, `describe_post_media()`

## Co-Pilot Agent (`agent/`)

Conversational AI assistant embedded as a floating chat widget on all dashboard pages.

- **Framework**: LangGraph `StateGraph` with `CopilotKitState` base, served via CopilotKit Python SDK
- **LLM**: Same Moonshot/Kimi API as AI Service (`moonshot-v1-8k`)
- **Endpoint**: `/copilotkit` (registered via `add_fastapi_endpoint()`, not a standard FastAPI router)
- **Frontend**: `<CopilotKit>` provider + `<CopilotPopup>` in `dashboard/layout.tsx`
- **Tools access the DB directly** via SQLAlchemy (not HTTP calls) to avoid deadlock with single-worker uvicorn

### Agent Tools (17 total)

**Query tools** (11 — read-only):
`get_accounts`, `get_account_metrics`, `get_account_baseline`, `get_posts`, `get_post_detail`, `get_post_insights`, `get_post_comments`, `get_daily_brief`, `get_recommendations`, `list_artifacts`, `analyze_post_media`

**Action tools** (6 — mutate state):
`trigger_sync`, `generate_post_diagnostic`, `generate_brief`, `update_recommendation_status`, `save_artifact`, `retrieve_artifact`

### Adding a new Co-Pilot tool
1. Create tool function with `@tool` decorator in `backend/app/agent/tools/query_tools.py` (read) or `action_tools.py` (write)
2. Add it to the `query_tools` or `action_tools` list at the bottom of the file
3. It is automatically included via `all_tools` in `agent/tools/__init__.py`
4. Rebuild backend: `docker compose up --build -d backend`

### Key dependencies
- Backend: `copilotkit`, `langgraph`, `langchain-openai`, `langchain-core`, `ag-ui-langgraph`
- Frontend: `@copilotkit/react-core`, `@copilotkit/react-ui`

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
- Co-Pilot chat: CopilotKit `CopilotPopup` (bottom-right floating widget), themed via CSS variables in `globals.css`

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

### Adding a new Co-Pilot agent tool
1. Add `@tool` function in `backend/app/agent/tools/query_tools.py` (read) or `action_tools.py` (write)
2. Append to the `query_tools` or `action_tools` list at the bottom of the file
3. Tool auto-registers via `all_tools` in `agent/tools/__init__.py`
4. Use `async with async_session() as session:` for DB access (not HTTP calls)
5. Return `json.dumps(...)` — agent receives tool output as a string

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

## Fly.io Deployment (Production)

The app deploys to Fly.io as two separate apps communicating over Fly's private network.
All infrastructure is defined as code in `fly.toml` files and the deploy script.

### Architecture

```
Internet → sma-frontend.fly.dev (Next.js standalone)
              ↓ Next.js rewrites /api/* and /copilotkit/*
           sma-backend.internal:8000 (FastAPI, 2 workers)
              ↓
           sma-db (Fly Postgres, shared-cpu-1x, 1GB disk)
              + sma-redis (Upstash Redis via Fly)
              + sma_media volume (1GB, mounted at /data/media)
```

All services in `iad` (Ashburn, Virginia) region. Frontend → backend uses Fly internal DNS (no public internet hop).

### IaC Files

| File | Purpose |
|------|---------|
| `backend/fly.toml` | Backend Fly app config (VM size, health checks, volume mount, env) |
| `backend/Dockerfile.fly` | Production backend image (no --reload, 2 workers) |
| `frontend/fly.toml` | Frontend Fly app config (VM size, health checks, backend URL) |
| `frontend/Dockerfile.fly` | Multi-stage Next.js standalone production build |
| `scripts/fly-deploy.sh` | Idempotent provisioning + deployment script |

### Deployment Commands

```bash
# First time: provision infrastructure
make fly-setup              # Create apps, Postgres, Redis, volume
make fly-secrets            # Push .env secrets to Fly apps

# Deploy
make fly-deploy             # Deploy both services
make fly-deploy-backend     # Deploy backend only
make fly-deploy-frontend    # Deploy frontend only

# Operations
make fly-status             # Show all resource status
make fly-logs               # Tail logs (both services)
make fly-logs-backend       # Tail backend logs
make fly-logs-frontend      # Tail frontend logs
make fly-db                 # Open psql to Fly Postgres
make fly-destroy            # Tear down everything (DESTRUCTIVE)
```

### Key Details

- **DATABASE_URL**: Set automatically when Fly Postgres is attached. `config.py` auto-converts `postgres://` → `postgresql+asyncpg://`.
- **Secrets**: Pushed from `.env` via `fly-deploy.sh secrets`. Never committed to git.
- **Media volume**: 1GB persistent volume on backend at `/data/media` for downloaded Instagram media.
- **Machines**: Auto-suspend when idle, auto-start on request. Min 1 machine always running per service.
- **Config changes**: Edit `fly.toml` files, then re-deploy. Config is the source of truth.

## Makefile Targets

Run `make help` for the full list. Key targets:

```bash
# Local development
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

# Fly.io production
make fly-setup         # Provision Fly.io infrastructure
make fly-secrets       # Push secrets from .env
make fly-deploy        # Deploy both services
make fly-status        # Show resource status
make fly-logs          # Tail production logs
make fly-db            # Open Fly Postgres console
make fly-destroy       # Tear down all resources
```

## Scripts (`scripts/`)

| Script | Purpose |
|--------|---------|
| `fly-deploy.sh` | Fly.io IaC: provision, secrets, deploy, destroy |
| `health_check.sh` | Full health check with colored output |
| `backup_db.sh` | Backup database to `backups/` (keeps last 10) |
| `restore_db.sh` | Restore database from a backup file |
| `seed_sample_data.py` | Populate DB with sample posts and metrics |
| `ig_sync.py` | Standalone Instagram sync script using browser session cookies |
| `test_insights_api.py` | Test script for Instagram Insights API endpoints |

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

# Verify Co-Pilot agent is registered
docker compose logs backend --tail 30 | grep -i "copilot\|CopilotKit"

# Rebuild frontend with fresh node_modules (after adding npm packages)
docker compose up --build -V -d frontend
```

## Known Limitations

1. **TikTok from Docker**: TikTok blocks datacenter IPs. The scraper falls back to oembed (profile name only). Set `TIKTOK_PROXY` with a residential proxy for full data.
2. **Instagram challenge**: First login from Docker triggers Instagram's device verification. User must approve via the Instagram app or temporarily disable 2FA.
3. **No migrations**: Tables are created via `Base.metadata.create_all()`. Schema changes require manual migration or DB reset.
4. **Single user**: No multi-user support. One password, one session.
5. **AI key**: Moonshot API key may expire. The AI service gracefully falls back to mock responses.
6. **Co-Pilot requires Moonshot key**: The chat agent needs a valid `MOONSHOT_API_KEY`. Without it, the agent will fail to generate responses (no mock fallback like the AI service).
7. **Co-Pilot has no persistent memory yet**: Session memory only (Phase 3 of PRD). Conversations don't carry over between sessions.
8. **CopilotKit frontend volumes**: After adding CopilotKit packages, use `docker compose up --build -V -d frontend` to refresh the anonymous `node_modules` volume.
