# PRD-01: Infrastructure & DevOps

## Domain
Project scaffolding, Docker containerization, database schema, CI basics.

## Goal
Set up a portable, one-command dev environment that any contributor can clone and run.

---

## 1. Project Structure

```
SOCIAL-MEDIA-AGENT/
├── docker-compose.yml
├── .env.example              # Template for secrets
├── .gitignore
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.js
│   ├── src/
│   │   ├── app/              # Next.js App Router
│   │   ├── components/
│   │   ├── lib/
│   │   └── styles/
│   └── .env.local.example
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic/              # DB migrations
│   ├── app/
│   │   ├── main.py           # FastAPI entrypoint
│   │   ├── config.py         # Settings from env
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── api/              # Route handlers
│   │   ├── services/         # Business logic
│   │   ├── integrations/     # TikTok, Instagram clients
│   │   └── workers/          # Background tasks
│   └── .env.example
├── db/
│   └── init.sql              # Optional seed data
└── docs/
    └── prds/
```

## 2. Docker Compose Services

```yaml
services:
  db:
    image: postgres:16-alpine
    volumes: [pgdata:/var/lib/postgresql/data]
    env_file: .env
    ports: ["5432:5432"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 5s

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  backend:
    build: ./backend
    env_file: ./backend/.env
    ports: ["8000:8000"]
    depends_on:
      db: { condition: service_healthy }
      redis: { condition: service_started }
    volumes: ["./backend:/app"]  # Hot reload in dev
    command: uvicorn app.main:app --host 0.0.0.0 --reload

  frontend:
    build: ./frontend
    env_file: ./frontend/.env.local
    ports: ["3000:3000"]
    depends_on: [backend]
    volumes: ["./frontend:/app", "/app/node_modules"]
    command: npm run dev

volumes:
  pgdata:
```

## 3. Database Schema (PostgreSQL)

### Tables

**users**
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK, default gen_random_uuid() |
| email | VARCHAR(255) | UNIQUE, NOT NULL |
| password_hash | VARCHAR(255) | NOT NULL |
| name | VARCHAR(100) | |
| created_at | TIMESTAMPTZ | DEFAULT now() |
| updated_at | TIMESTAMPTZ | |

**accounts** (connected social platforms)
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| user_id | UUID | FK → users.id |
| platform | VARCHAR(20) | 'instagram' or 'tiktok' |
| platform_user_id | VARCHAR(255) | Platform-specific ID |
| username | VARCHAR(255) | |
| access_token | TEXT | Encrypted at rest |
| refresh_token | TEXT | Encrypted at rest |
| token_expires_at | TIMESTAMPTZ | |
| status | VARCHAR(20) | 'active', 'expired', 'revoked' |
| created_at | TIMESTAMPTZ | |

**posts**
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| account_id | UUID | FK → accounts.id |
| platform_post_id | VARCHAR(255) | Platform-specific post ID |
| platform | VARCHAR(20) | |
| post_type | VARCHAR(20) | 'reel', 'story', 'video', 'image', 'carousel' |
| caption | TEXT | |
| media_url | TEXT | |
| permalink | TEXT | |
| posted_at | TIMESTAMPTZ | |
| created_at | TIMESTAMPTZ | |

**post_metrics**
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| post_id | UUID | FK → posts.id |
| snapshot_at | TIMESTAMPTZ | When metrics were captured |
| views | INTEGER | |
| likes | INTEGER | |
| comments | INTEGER | |
| shares | INTEGER | |
| saves | INTEGER | |
| reach | INTEGER | |
| engagement_rate | DECIMAL(5,4) | Computed |

**insights**
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| post_id | UUID | FK → posts.id (nullable) |
| account_id | UUID | FK → accounts.id |
| insight_type | VARCHAR(30) | 'diagnostic', 'summary', 'trend' |
| content | TEXT | AI-generated text |
| metadata | JSONB | Structured data (scores, tags) |
| created_at | TIMESTAMPTZ | |

**recommendations**
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| account_id | UUID | FK → accounts.id |
| recommendation_type | VARCHAR(30) | 'content_idea', 'timing', 'hashtag', 'remix' |
| title | VARCHAR(255) | |
| content | TEXT | |
| priority | INTEGER | 1-5 |
| status | VARCHAR(20) | 'pending', 'accepted', 'dismissed' |
| created_at | TIMESTAMPTZ | |

**daily_briefs**
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| account_id | UUID | FK → accounts.id |
| brief_date | DATE | UNIQUE with account_id |
| content | TEXT | AI-generated daily summary |
| metrics_snapshot | JSONB | Key metrics for that day |
| created_at | TIMESTAMPTZ | |

### Indexes
- `accounts(user_id, platform)` — UNIQUE
- `posts(account_id, platform_post_id)` — UNIQUE
- `post_metrics(post_id, snapshot_at)`
- `daily_briefs(account_id, brief_date)` — UNIQUE
- `insights(account_id, created_at)`
- `recommendations(account_id, status)`

## 4. Environment Variables

### Root `.env`
```
POSTGRES_USER=smadmin
POSTGRES_PASSWORD=<generate>
POSTGRES_DB=social_media_agent
```

### `backend/.env`
```
DATABASE_URL=postgresql+asyncpg://smadmin:<pw>@db:5432/social_media_agent
REDIS_URL=redis://redis:6379/0
JWT_SECRET=<generate>
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=1440

# Platform APIs
TIKTOK_CLIENT_KEY=
TIKTOK_CLIENT_SECRET=
INSTAGRAM_APP_ID=
INSTAGRAM_APP_SECRET=

# AI
OPENAI_API_KEY=

# Encryption
ENCRYPTION_KEY=<generate-32-byte-key>
```

### `frontend/.env.local`
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 5. Acceptance Criteria

- [ ] `docker compose up` starts all 4 services (db, redis, backend, frontend)
- [ ] Backend responds at `http://localhost:8000/health`
- [ ] Frontend loads at `http://localhost:3000`
- [ ] Database migrations run automatically on backend start
- [ ] `.env.example` files document all required variables
- [ ] `.gitignore` excludes `.env*` (except `.example`), `node_modules`, `__pycache__`, `.next`
- [ ] Hot reload works for both frontend and backend in dev mode

## 6. Implementation Notes

- Use Alembic for database migrations (auto-generate from SQLAlchemy models)
- Backend Dockerfile: Python 3.12 slim, install deps, copy app
- Frontend Dockerfile: Node 20 alpine, install deps, copy app
- Add a `Makefile` or `scripts/` for common commands (`make up`, `make migrate`, `make seed`)
