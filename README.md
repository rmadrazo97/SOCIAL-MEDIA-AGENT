# AI Social Media Command Center

An AI-powered monitoring and analytics platform for Instagram and TikTok creator accounts. Track engagement metrics, get AI-generated insights, daily briefs, content recommendations, and remix suggestions — all from a single dashboard.

## Architecture Overview

```mermaid
graph TB
    subgraph Frontend["Frontend (Next.js 15)"]
        UI[Dashboard UI]
        API_CLIENT[API Client + SWR]
    end

    subgraph Backend["Backend (FastAPI)"]
        AUTH[Auth Middleware]
        ROUTES[API Routes]
        SYNC[Sync Service]
        AI[AI Service]
        SCHEDULER[APScheduler]
    end

    subgraph Scrapers["Data Collection"]
        IG[Instagram Scraper<br/>instagrapi]
        TK[TikTok Scraper<br/>httpx + oembed]
    end

    subgraph Storage["Storage Layer"]
        PG[(PostgreSQL 16)]
        REDIS[(Redis 7)]
    end

    subgraph External["External APIs"]
        INSTAGRAM[Instagram API]
        TIKTOK[TikTok Web]
        KIMI[Kimi / Moonshot AI]
    end

    UI --> API_CLIENT
    API_CLIENT -->|X-App-Password| AUTH
    AUTH --> ROUTES
    ROUTES --> SYNC
    ROUTES --> AI
    SCHEDULER -->|Cron Jobs| SYNC
    SCHEDULER -->|Cron Jobs| AI
    SYNC --> IG
    SYNC --> TK
    IG --> INSTAGRAM
    TK --> TIKTOK
    AI --> KIMI
    SYNC --> PG
    AI --> PG
    ROUTES --> PG
    ROUTES --> REDIS
```

## Data Flow

```mermaid
sequenceDiagram
    participant S as Scheduler
    participant Sync as Sync Service
    participant IG as Instagram
    participant TK as TikTok
    participant DB as PostgreSQL
    participant AI as AI Service
    participant Kimi as Moonshot API

    Note over S: Every 2 hours
    S->>Sync: sync_all_accounts()

    loop For each account
        alt Instagram
            Sync->>IG: get_profile() + get_recent_posts()
            IG-->>Sync: Profile data + posts with metrics
        else TikTok
            Sync->>TK: get_profile() + get_recent_videos()
            TK-->>Sync: Profile data + videos with metrics
        end
        Sync->>DB: Upsert account, posts, metrics
    end

    Note over S: Daily at 3:00 AM UTC
    S->>Sync: compute_all_baselines()
    Sync->>DB: Calculate 30-day rolling averages

    Note over S: Daily at 7:00 AM UTC
    S->>AI: generate_daily_briefs()
    AI->>DB: Fetch account data + recent posts
    AI->>Kimi: Generate brief with analysis
    Kimi-->>AI: AI-generated brief
    AI->>DB: Store daily brief

    Note over S: Daily at 7:30 AM UTC
    S->>AI: generate_recommendations()
    AI->>Kimi: Generate content strategy
    Kimi-->>AI: Recommendations
    AI->>DB: Store recommendations
```

## Scraping Architecture

```mermaid
graph LR
    subgraph Instagram
        IG_SCRAPER[instagrapi Client]
        IG_SESSION[Session File<br/>ig_session.json]
        IG_API[Instagram Mobile API]

        IG_SCRAPER -->|Login + persist| IG_SESSION
        IG_SCRAPER -->|Private API| IG_API
    end

    subgraph TikTok
        TK_SCRAPER[httpx Client]
        TK_HTML[HTML Extraction<br/>UNIVERSAL_DATA]
        TK_OEMBED[oembed API<br/>Fallback]
        TK_WEB[TikTok Web]

        TK_SCRAPER -->|Primary| TK_HTML
        TK_SCRAPER -->|Fallback| TK_OEMBED
        TK_HTML --> TK_WEB
        TK_OEMBED --> TK_WEB
    end

    subgraph Data["Collected Data"]
        PROFILE[Profile Info<br/>name, bio, followers]
        POSTS[Posts / Videos<br/>caption, media, date]
        METRICS[Metrics<br/>likes, views, comments,<br/>shares, saves]
    end

    IG_SCRAPER --> PROFILE
    IG_SCRAPER --> POSTS
    IG_SCRAPER --> METRICS
    TK_SCRAPER --> PROFILE
    TK_SCRAPER --> POSTS
    TK_SCRAPER --> METRICS
```

## Database Schema

```mermaid
erDiagram
    Account ||--o{ Post : has
    Account ||--o{ AccountBaseline : has
    Account ||--o{ DailyBrief : has
    Account ||--o{ Recommendation : has
    Account ||--o{ Insight : has
    Post ||--o{ PostMetric : has
    Post ||--o{ Insight : has

    Account {
        uuid id PK
        string platform
        string platform_user_id
        string username
        string status
        int follower_count
        timestamp created_at
    }

    Post {
        uuid id PK
        uuid account_id FK
        string platform_post_id
        string platform
        string post_type
        text caption
        text permalink
        timestamp posted_at
    }

    PostMetric {
        uuid id PK
        uuid post_id FK
        timestamp snapshot_at
        int views
        int likes
        int comments
        int shares
        int saves
        int reach
        numeric engagement_rate
        numeric performance_score
    }

    AccountBaseline {
        uuid id PK
        uuid account_id FK
        timestamp computed_at
        int period_days
        jsonb baseline_data
    }

    DailyBrief {
        uuid id PK
        uuid account_id FK
        date brief_date
        text content
        jsonb metrics_snapshot
    }

    Recommendation {
        uuid id PK
        uuid account_id FK
        string recommendation_type
        string title
        text content
        int priority
        string status
    }

    Insight {
        uuid id PK
        uuid post_id FK
        uuid account_id FK
        string insight_type
        text content
        jsonb metadata_json
    }
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15 (App Router), Tailwind CSS, SWR |
| Backend | FastAPI, SQLAlchemy (async), Pydantic v2 |
| Database | PostgreSQL 16, Redis 7 |
| AI | Moonshot / Kimi API (OpenAI-compatible) |
| Instagram | instagrapi (private mobile API) |
| TikTok | httpx + HTML extraction + oembed fallback |
| Scheduling | APScheduler |
| Infrastructure | Docker Compose |

## Quick Start

### 1. Clone and configure

```bash
git clone https://github.com/rmadrazo97/SOCIAL-MEDIA-AGENT.git
cd SOCIAL-MEDIA-AGENT
cp .env.example .env
```

Edit `.env` with your credentials:

```env
APP_PASSWORD=your_dashboard_password

# Instagram (required for IG scraping)
INSTAGRAM_USERNAME=your_instagram_username
INSTAGRAM_PASSWORD=your_instagram_password

# AI features (Moonshot/Kimi - OpenAI compatible)
MOONSHOT_API_KEY=your_moonshot_api_key

# Optional: residential proxy for TikTok (datacenter IPs get blocked)
TIKTOK_PROXY=http://user:pass@proxy:port
```

### 2. Start the stack

```bash
docker compose up --build -d
```

### 3. Access the dashboard

- **Frontend**: http://localhost:3001
- **Backend API**: http://localhost:8001
- **Health check**: http://localhost:8001/health

### 4. Expose publicly (optional)

The frontend proxies API requests via Next.js rewrites, so a single tunnel exposes everything:

```bash
ngrok http 3001
```

### 5. Add accounts

1. Log in with your `APP_PASSWORD`
2. Go to **Accounts** > **Add Account**
3. Enter a username and select the platform (instagram/tiktok)
4. Hit **Sync Now** to trigger an immediate data pull

## Ports

| Service | Port |
|---------|------|
| Frontend | 3001 |
| Backend API | 8001 |
| PostgreSQL | 5433 |
| Redis | 6380 |

## Cron Schedule

| Job | Schedule | Description |
|-----|----------|-------------|
| Sync all accounts | Every 2 hours | Scrape new posts and metrics |
| Compute baselines | 3:00 AM UTC | Calculate 30-day rolling averages |
| Generate briefs | 7:00 AM UTC | AI-generated daily performance summaries |
| Generate recommendations | 7:30 AM UTC | AI content strategy suggestions |

## API Reference

### Auth
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/login` | Authenticate with password |

### Accounts
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/accounts` | List all accounts |
| POST | `/api/accounts` | Add an account |
| GET | `/api/accounts/{id}` | Get account details |
| DELETE | `/api/accounts/{id}` | Remove an account |

### Posts
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/accounts/{id}/posts` | Get posts (query: platform, post_type, limit, offset) |
| POST | `/api/posts` | Create a post manually |
| GET | `/api/posts/{id}` | Get post with latest metrics |
| DELETE | `/api/posts/{id}` | Delete a post |
| GET | `/api/posts/{id}/metrics` | Get metric history (snapshots) |
| POST | `/api/posts/{id}/metrics` | Add a metric snapshot |

### AI & Insights
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/posts/{id}/diagnostic` | Get cached AI diagnostic |
| POST | `/api/posts/{id}/diagnostic` | Generate new AI diagnostic |
| GET | `/api/accounts/{id}/insights` | List account insights |
| POST | `/api/posts/{id}/remix` | Generate content remix (body: `{remix_type}`) |

### Briefs & Recommendations
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/accounts/{id}/brief` | Get today's brief |
| POST | `/api/accounts/{id}/brief` | Generate today's brief |
| GET | `/api/accounts/{id}/briefs` | List recent briefs |
| GET | `/api/accounts/{id}/recommendations` | Get recommendations (query: status) |
| PATCH | `/api/recommendations/{id}` | Update recommendation status |

### Metrics & Baselines
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/accounts/{id}/metrics` | Aggregated metrics (query: days=7) |
| GET | `/api/accounts/{id}/baseline` | Get latest baseline |

### Sync & Import
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/accounts/{id}/sync` | Sync one account |
| POST | `/api/sync/all` | Sync all accounts |
| POST | `/api/sync/baselines` | Recompute baselines |
| POST | `/api/sync/briefs` | Generate all briefs |
| POST | `/api/sync/recommendations` | Generate all recommendations |
| GET | `/api/sync/status` | Get sync status |
| POST | `/api/accounts/{id}/import` | Import CSV (multipart form) |

## Platform Notes

### Instagram
- Uses **instagrapi** (Instagram private mobile API)
- Requires real Instagram credentials in `.env`
- First login from Docker may trigger a verification challenge — temporarily disable 2FA or approve the new device
- Session is persisted to `/app/ig_session.json` to avoid re-login
- Consider using a secondary account to avoid rate limits

### TikTok
- Uses **httpx** for HTTP-based scraping (no browser needed)
- No login required — works with public profiles
- Primary: extracts `__UNIVERSAL_DATA_FOR_REHYDRATION__` JSON from HTML
- Fallback: oembed API for basic profile info (no video metrics)
- TikTok blocks datacenter IPs — configure `TIKTOK_PROXY` for full data
- Full scraping works from residential IPs

## Color Palette

Nature-inspired UI palette:

| Name | Hex | Usage |
|------|-----|-------|
| Bone | `#EBE3D2` | Backgrounds |
| Dun | `#CCBFA3` | Borders, secondary |
| Sage | `#A4AC86` | Accents, success |
| Reseda Green | `#737A5D` | Primary actions |
| Ebony | `#414833` | Text, headers |

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── api/            # FastAPI route handlers
│   │   ├── integrations/   # Instagram & TikTok scrapers
│   │   ├── models/         # SQLAlchemy ORM models
│   │   ├── schemas/        # Pydantic request/response schemas
│   │   ├── services/       # Business logic (sync, AI, baselines)
│   │   ├── workers/        # APScheduler cron setup
│   │   ├── config.py       # Pydantic Settings (env vars)
│   │   ├── database.py     # Async SQLAlchemy engine
│   │   └── main.py         # FastAPI app entry point
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/            # Next.js App Router pages
│   │   ├── components/     # React components
│   │   ├── lib/            # API client, SWR hooks
│   │   └── styles/         # Global CSS + Tailwind
│   ├── next.config.js      # API proxy rewrites
│   ├── tailwind.config.js  # Custom color palette
│   └── Dockerfile
├── docs/prds/              # Product requirement documents
├── scripts/                # Utility scripts
├── docker-compose.yml
├── CLAUDE.md               # Agent development guide
└── .env
```

## License

MIT
