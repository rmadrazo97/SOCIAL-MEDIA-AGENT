# AGENTS.md — Tooling Reference for AI Coding Agents

This document describes all development tools, slash commands, and scripts available in this repository. Read this when starting work on the project.

> **Start here**: Read `CLAUDE.md` for full architecture, file map, models, and conventions. This file covers the _tooling_ layer only.

---

## Slash Commands

Available as `/command` in Claude Code. Located in `.claude/commands/`.

### Operations

| Command | Description |
|---------|-------------|
| `/status` | Check health of all services (Docker, backend, frontend, DB, Redis) and show data counts |
| `/deploy` | Rebuild changed services, verify startup, report errors. Run this after making code changes |
| `/sync` | Trigger data scraping for all accounts, recompute baselines, report results |
| `/debug <problem>` | Investigate an issue: gather logs, identify the failing layer, test in isolation, suggest fix |
| `/review` | Review uncommitted changes against a checklist (auth, schemas, error handling, UI, docs) |
| `/db-inspect [table]` | Show table schemas, row counts, sample data, and recent activity timestamps |

### Scaffolding

| Command | Description |
|---------|-------------|
| `/feature <description>` | Plan and implement a complete feature: model → schema → service → API → frontend → nav |
| `/add-endpoint <description>` | Add a single API endpoint: Pydantic schema → FastAPI route → `api.ts` method → SWR hook |
| `/add-model <description>` | Add a database model: SQLAlchemy model → Pydantic schema → table creation → verify |
| `/add-page <description>` | Add a frontend page: Next.js page → sidebar link → data hooks → styled with project palette |
| `/add-platform <name>` | Add a new social media platform: scraper → config → sync routing → frontend selector |
| `/add-ai-feature <description>` | Add an AI-powered feature: AI service method → API endpoint → frontend trigger + display |

### Usage

Commands that accept arguments are marked with `<description>`. Pass context after the command:

```
/feature Add a content calendar page where users can schedule posts
/add-endpoint GET /api/accounts/{id}/growth that returns follower count over time
/debug The daily brief shows "AI analysis unavailable" even though the API key is set
```

---

## Makefile

Run `make help` to see all targets. Key ones:

### Lifecycle
```bash
make up              # Start all services
make down            # Stop all services
make build           # Build and start (after Dockerfile/deps changes)
make rebuild-backend # Rebuild only backend
make rebuild-frontend # Rebuild only frontend
make restart         # Restart all services
```

### Observability
```bash
make logs            # Tail all logs
make logs-backend    # Tail backend logs
make logs-frontend   # Tail frontend logs
make status          # Container status + health check
make health          # Backend health (JSON)
```

### Data Operations
```bash
make sync-all        # Trigger sync for all accounts
make baselines       # Recompute performance baselines
make briefs          # Generate AI daily briefs
make recs            # Generate AI recommendations
make sync-status     # Check sync status
make accounts        # List all accounts
```

### Database
```bash
make db-shell        # Open interactive psql shell
make db-counts       # Row counts for every table
make db-dump         # Backup to timestamped SQL file
make db-reset        # Drop and recreate all tables (requires confirmation)
```

### Utilities
```bash
make seed            # Populate DB with sample data
make tunnel          # Expose frontend publicly via ngrok
make clean           # Remove containers, volumes, build cache
make prune           # Remove stopped containers and dangling images
```

The default password for API calls is `admin123`. Override with: `make sync-all PW=yourpassword`

---

## Scripts

Located in `scripts/`. All shell scripts are executable.

| Script | Usage | Description |
|--------|-------|-------------|
| `health_check.sh` | `./scripts/health_check.sh` | Full health report with colored output — checks all services, data counts, recent errors |
| `backup_db.sh` | `./scripts/backup_db.sh` | Backup database to `backups/` directory. Keeps last 10 backups automatically |
| `restore_db.sh` | `./scripts/restore_db.sh backups/<file>.sql` | Restore database from a backup file (destructive, requires confirmation) |
| `seed_sample_data.py` | `python3 scripts/seed_sample_data.py` | Populate the database with sample posts, metrics, briefs, and recommendations |

---

## Workflow Examples

### "I need to add a new feature"
1. Run `/status` to verify the stack is healthy
2. Run `/feature <description>` — it will plan the implementation and walk through each layer
3. Run `/deploy` to rebuild and verify
4. Run `/review` to check for issues
5. Commit

### "Something is broken"
1. Run `/debug <what's wrong>` — it gathers logs, checks services, and identifies the issue
2. Fix the code
3. Run `/deploy` to rebuild
4. Run `/status` to confirm everything is healthy

### "I want to understand the database"
1. Run `/db-inspect` for an overview of all tables and counts
2. Run `/db-inspect posts` to see the posts table schema and sample rows

### "I want to extend the platform"
- New social network: `/add-platform youtube`
- New AI capability: `/add-ai-feature Generate hashtag suggestions based on post content`
- New dashboard view: `/add-page Analytics page with charts showing follower growth over time`
- New data endpoint: `/add-endpoint GET /api/accounts/{id}/top-posts returning the 10 best performing posts`

### "I need to back up before a risky change"
```bash
./scripts/backup_db.sh              # Create backup
# ... make changes ...
./scripts/restore_db.sh backups/social_media_agent_20260328_134500.sql  # Restore if needed
```

---

## File Locations

| What | Where |
|------|-------|
| Slash commands | `.claude/commands/*.md` |
| Makefile | `Makefile` (project root) |
| Shell scripts | `scripts/*.sh` |
| Python scripts | `scripts/*.py` |
| Agent guide | `CLAUDE.md` |
| This file | `AGENTS.md` |
| DB backups | `backups/` (gitignored) |
