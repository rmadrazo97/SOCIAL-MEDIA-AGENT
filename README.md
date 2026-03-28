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
    Sync->>DB: Calculate 7-day rolling averages

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
    Post ||--o{ PostMetric : has
    Post ||--o{ Insight : has

    Account {
        uuid id PK
        string platform
        string username
        string full_name
        int follower_count
        int post_count
        timestamp last_synced_at
    }

    Post {
        uuid id PK
        uuid account_id FK
        string platform_post_id
        string post_type
        string caption
        string permalink
        timestamp posted_at
    }

    PostMetric {
        uuid id PK
        uuid post_id FK
        int likes
        int comments
        int shares
        int saves
        int views
        int reach
        timestamp recorded_at
    }

    AccountBaseline {
        uuid id PK
        uuid account_id FK
        float avg_likes
        float avg_comments
        float avg_views
        float avg_reach
    }

    DailyBrief {
        uuid id PK
        uuid account_id FK
        text content
        date brief_date
    }

    Recommendation {
        uuid id PK
        uuid account_id FK
        text content
        string rec_type
    }

    Insight {
        uuid id PK
        uuid post_id FK
        text content
        string insight_type
    }
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15 (App Router), Tailwind CSS, SWR |
| Backend | FastAPI, SQLAlchemy (async), Pydantic |
| Database | PostgreSQL 16, Redis 7 |
| AI | Moonshot / Kimi API (OpenAI-compatible) |
| Instagram | instagrapi (private mobile API) |
| TikTok | httpx + HTML extraction + oembed fallback |
| Scheduling | APScheduler |
| Infrastructure | Docker Compose |

## Quick Start

### 1. Clone and configure

```bash
git clone <repo-url>
cd SOCIAL-MEDIA-AGENT
cp .env.example .env
```

Edit `.env` with your credentials:

```env
APP_PASSWORD=your_dashboard_password

# Instagram (required for IG scraping)
INSTAGRAM_USERNAME=your_instagram_username
INSTAGRAM_PASSWORD=your_instagram_password

# AI features
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

### 4. Add accounts

1. Log in with your `APP_PASSWORD`
2. Go to **Accounts** → **Add Account**
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
| Compute baselines | 3:00 AM UTC | Calculate 7-day rolling averages |
| Generate briefs | 7:00 AM UTC | AI-generated daily performance summaries |
| Generate recommendations | 7:30 AM UTC | AI content strategy suggestions |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/login` | Authenticate with password |
| GET | `/api/accounts` | List all accounts |
| POST | `/api/accounts` | Add an account |
| GET | `/api/accounts/{id}/posts` | Get posts for an account |
| GET | `/api/accounts/{id}/metrics` | Get metric timeseries |
| GET | `/api/accounts/{id}/brief` | Get latest daily brief |
| GET | `/api/accounts/{id}/recommendations` | Get AI recommendations |
| POST | `/api/accounts/{id}/sync` | Trigger manual sync |
| POST | `/api/sync/all` | Sync all accounts |
| GET | `/api/posts/{id}` | Get post details |
| POST | `/api/posts/{id}/insights` | Generate AI diagnostic |
| POST | `/api/posts/{id}/remix` | Generate content remix |
| POST | `/api/csv/import` | Import accounts from CSV |

## Platform Notes

### Instagram
- Uses **instagrapi** (Instagram private mobile API)
- Requires real Instagram credentials in `.env`
- First login from Docker may trigger a verification challenge — temporarily disable 2FA or approve the new device
- Session is persisted to avoid re-login on restart
- Consider using a secondary account to avoid rate limits on your main account

### TikTok
- Uses **httpx** for HTTP-based scraping (no browser needed)
- No login required — works with public profiles
- Primary method: extracts embedded JSON from TikTok HTML pages
- Fallback: oembed API for basic profile info (no video metrics)
- TikTok aggressively blocks datacenter IPs — configure `TIKTOK_PROXY` with a residential proxy for full data
- Full scraping (with video metrics) works from residential IPs

## Color Palette

The UI uses a nature-inspired color palette:

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
│   │   ├── api/          # FastAPI route handlers
│   │   ├── integrations/ # Instagram & TikTok scrapers
│   │   ├── models/       # SQLAlchemy models
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── services/     # Business logic (sync, AI, baselines)
│   │   └── workers/      # APScheduler setup
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/          # Next.js pages (App Router)
│   │   ├── components/   # React components
│   │   ├── lib/          # API client, hooks
│   │   └── styles/       # Global CSS
│   ├── Dockerfile
│   └── tailwind.config.js
├── docs/prds/            # Product requirement documents
├── docker-compose.yml
└── .env
```

## License

MIT
