# PRD-07: Background Workers & Scheduling

## Domain
Cron jobs, task queues, scheduled data collection, and async processing.

## Dependencies
- PRD-01 (Redis, database)
- PRD-04 (metrics collection services)
- PRD-05 (AI generation services)

## Goal
Reliable background processing for all recurring and async tasks — metrics collection, AI generation, token refresh — without blocking the API.

---

## 1. Architecture

### Queue System
- **Redis** as message broker
- **ARQ** (async Redis queue for Python) or **Celery** with Redis backend
- Recommended: **ARQ** — lightweight, async-native, perfect for FastAPI

### Worker Process
- Separate Docker service (shares backend codebase, different entrypoint)
- Runs alongside API server
- Can scale horizontally by adding more worker containers

### Docker Compose Addition
```yaml
  worker:
    build: ./backend
    env_file: ./backend/.env
    depends_on:
      db: { condition: service_healthy }
      redis: { condition: service_started }
    command: arq app.workers.WorkerSettings
    volumes: ["./backend:/app"]
```

## 2. Scheduled Tasks (Cron)

| Task | Schedule | Description |
|------|----------|-------------|
| `sync_all_accounts` | Every 6 hours | Refresh metrics for posts < 7 days old |
| `detect_new_posts` | Every 1 hour | Check for new posts on all active accounts |
| `compute_baselines` | Daily at 3:00 AM UTC | Recompute baselines for all accounts |
| `generate_daily_briefs` | Daily at 7:00 AM UTC | Generate daily briefs for all accounts |
| `generate_recommendations` | Daily at 7:30 AM UTC | Generate recommendations after briefs |
| `refresh_tokens` | Daily at 2:00 AM UTC | Refresh expiring platform tokens |
| `cleanup_old_metrics` | Weekly (Sunday 4 AM) | Archive metrics older than 90 days |

### Cron Registration (ARQ)
```python
class WorkerSettings:
    functions = [
        sync_all_accounts,
        detect_new_posts,
        compute_baselines,
        generate_daily_briefs,
        generate_recommendations,
        refresh_tokens,
        cleanup_old_metrics,
        # On-demand tasks
        snapshot_post_metrics,
        generate_post_diagnostic,
        generate_remix,
        backfill_account,
    ]

    cron_jobs = [
        cron(sync_all_accounts, hour={0, 6, 12, 18}),
        cron(detect_new_posts, minute={0}),  # every hour
        cron(compute_baselines, hour=3, minute=0),
        cron(generate_daily_briefs, hour=7, minute=0),
        cron(generate_recommendations, hour=7, minute=30),
        cron(refresh_tokens, hour=2, minute=0),
        cron(cleanup_old_metrics, weekday=6, hour=4),
    ]

    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
```

## 3. Event-Driven Tasks

These are triggered by API actions or other workers, not on a schedule.

### Post Lifecycle Pipeline
When a new post is detected:
```
New Post Detected
     │
     ├── Immediately: Save post to DB
     ├── +15 min: snapshot_post_metrics(post_id)
     ├── +2 hours: snapshot_post_metrics(post_id)
     ├── +24 hours: snapshot_post_metrics(post_id) + generate_post_diagnostic(post_id)
     └── +48 hours: snapshot_post_metrics(post_id) (final)
```

### Implementation
```python
async def on_new_post_detected(ctx, post_id: str):
    """Schedule the post lifecycle metric snapshots."""
    pool = ctx['redis']

    # Schedule future snapshots
    await pool.enqueue_job('snapshot_post_metrics', post_id, _defer_by=timedelta(minutes=15))
    await pool.enqueue_job('snapshot_post_metrics', post_id, _defer_by=timedelta(hours=2))
    await pool.enqueue_job('snapshot_post_metrics', post_id, _defer_by=timedelta(hours=24))
    await pool.enqueue_job('generate_post_diagnostic', post_id, _defer_by=timedelta(hours=24))
    await pool.enqueue_job('snapshot_post_metrics', post_id, _defer_by=timedelta(hours=48))
```

### Account Connection Pipeline
When a new account is connected:
```
Account Connected
     │
     ├── Immediately: backfill_account(account_id)  — fetch last 20 posts
     ├── After backfill: compute_baselines(account_id)
     └── After baseline: generate_recommendations(account_id)
```

### User-Triggered Tasks
| Trigger | Task |
|---------|------|
| "Sync Now" button | `sync_account(account_id)` |
| "Generate Remix" button | `generate_remix(post_id, format)` |
| "Regenerate Diagnostic" | `generate_post_diagnostic(post_id)` |

## 4. Task Status Tracking

For user-triggered tasks, we need to track status so the frontend can poll/display progress.

### Task Status Table

**task_runs**
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | PK |
| task_type | VARCHAR(50) | e.g., 'backfill', 'remix', 'diagnostic' |
| entity_id | UUID | The account/post this task relates to |
| status | VARCHAR(20) | 'queued', 'running', 'completed', 'failed' |
| result | JSONB | Task output (nullable) |
| error | TEXT | Error message if failed |
| created_at | TIMESTAMPTZ | |
| started_at | TIMESTAMPTZ | |
| completed_at | TIMESTAMPTZ | |

### API Endpoints for Task Status

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/api/tasks/{id}` | Get task status | Token |
| GET | `/api/tasks?entity_id=X&type=Y` | List tasks for an entity | Token |

### Frontend Polling
- Poll `/api/tasks/{id}` every 2 seconds while status is 'queued' or 'running'
- Display loading indicator with task type label
- Show result or error when complete

## 5. Error Handling & Retries

### Retry Policy
```python
max_tries = 3
retry_delay = timedelta(seconds=30)  # exponential: 30s, 60s, 120s
```

### Error Categories
| Category | Action |
|----------|--------|
| API rate limit (429) | Retry with exponential backoff |
| API auth error (401) | Mark token expired, don't retry |
| API server error (5xx) | Retry up to 3 times |
| LLM timeout | Retry once, then fallback to simpler model |
| DB connection error | Retry up to 3 times |
| Unknown error | Log, don't retry, mark task failed |

### Dead Letter Queue
- After max retries, move to dead letter queue
- Log with full context for debugging
- Admin can re-queue manually (future)

## 6. Monitoring & Logging

### Worker Logging
- Log task start, completion, failure with duration
- Log queue depth periodically
- Log token usage for AI tasks

### Health Check
```python
# /api/health/worker
async def worker_health():
    """Check if worker is processing tasks."""
    return {
        "redis_connected": True,
        "queue_depth": 5,
        "last_task_completed": "2026-03-28T07:15:00Z",
        "active_workers": 1
    }
```

### Key Metrics to Track
- Queue depth (should stay < 100)
- Task completion rate
- Average task duration by type
- Failed task rate
- LLM token usage per day

## 7. Concurrency & Safety

- **Account-level locking:** Only one sync per account at a time (use Redis lock)
- **Idempotency:** Metric snapshots check for existing snapshot at same timestamp
- **Graceful shutdown:** Worker finishes current task before stopping (SIGTERM handling)

```python
async def sync_account(ctx, account_id: str):
    lock_key = f"sync:account:{account_id}"
    lock = ctx['redis'].lock(lock_key, timeout=300)

    if not await lock.acquire(blocking=False):
        logger.info(f"Sync already running for account {account_id}, skipping")
        return

    try:
        # ... do sync
    finally:
        await lock.release()
```

## 8. Acceptance Criteria

- [ ] Worker starts as separate Docker service
- [ ] Cron jobs execute on schedule
- [ ] New post lifecycle snapshots are scheduled correctly
- [ ] Account backfill runs on connection
- [ ] Daily brief + recommendations generated every morning
- [ ] Token refresh runs daily
- [ ] Failed tasks retry with exponential backoff
- [ ] Task status trackable via API
- [ ] Account-level locking prevents concurrent syncs
- [ ] Worker health endpoint returns queue status
- [ ] Graceful shutdown on container stop

## 9. Out of Scope (MVP)
- Distributed task locking (single worker is fine for MVP)
- Priority queues
- Admin dashboard for queue monitoring
- Webhook delivery to external systems
- Real-time push notifications (polling is fine for MVP)
