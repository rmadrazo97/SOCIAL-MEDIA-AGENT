# AI Social Media Command Center — PRD Index

## Project Overview

An AI command center that monitors creator accounts (Instagram & TikTok), explains performance daily, and recommends what to do next.

**Tech Stack:** Next.js (frontend) + FastAPI (backend) + PostgreSQL (database), all containerized with Docker.

## PRD Breakdown by Domain

| # | PRD | Domain | Dependencies |
|---|-----|--------|-------------|
| 01 | [Infrastructure & DevOps](./01-infrastructure.md) | Docker, DB schema, project scaffold | None (start here) |
| 02 | [Auth & User Management](./02-auth.md) | Signup, login, sessions | PRD-01 |
| 03 | [Platform Integrations](./03-integrations.md) | TikTok & Instagram API connectors | PRD-01, PRD-02 |
| 04 | [Data Ingestion & Analytics](./04-data-analytics.md) | Metrics collection, baseline calc | PRD-01, PRD-03 |
| 05 | [AI Intelligence Layer](./05-ai-layer.md) | Diagnostics, insights, recommendations | PRD-01, PRD-04 |
| 06 | [Frontend Dashboard & UI](./06-frontend.md) | Next.js pages, components, UX | PRD-01, PRD-02 |
| 07 | [Background Workers & Scheduling](./07-workers.md) | Cron jobs, post lifecycle tracking | PRD-01, PRD-04, PRD-05 |

## Dependency Graph

```
PRD-01 (Infrastructure)
  ├── PRD-02 (Auth)
  │     └── PRD-06 (Frontend) ←── can start UI shell early
  ├── PRD-03 (Integrations)
  │     └── PRD-04 (Data/Analytics)
  │           ├── PRD-05 (AI Layer)
  │           └── PRD-07 (Workers)
  └── PRD-06 (Frontend) ←── consumes all APIs
```

## Parallel Workstreams

- **Stream A (Backend Core):** PRD-01 → PRD-02 → PRD-03 → PRD-04
- **Stream B (Frontend):** PRD-01 → PRD-06 (start with mocks, integrate as APIs land)
- **Stream C (AI + Workers):** PRD-05 + PRD-07 (start after PRD-04 data model is stable)

## Environment & Secrets

All credentials stored in `.env` files (git-ignored). Each service has its own `.env`:
- `backend/.env` — DB URL, API keys, JWT secret
- `frontend/.env.local` — API base URL, public keys
- `docker-compose.yml` references `.env` at root level
