# =============================================================================
# Social Media Agent — Development Makefile
# =============================================================================
# Usage: make <target>
# Run `make help` for a list of all available targets.
# =============================================================================

.PHONY: help up down build rebuild logs status health \
        sync sync-all baselines briefs recs \
        db-shell db-reset db-dump db-counts \
        seed tunnel lint test clean \
        fly-setup fly-secrets fly-deploy fly-deploy-backend fly-deploy-frontend \
        fly-status fly-logs fly-logs-backend fly-logs-frontend fly-db fly-destroy

# -- Core lifecycle -----------------------------------------------------------

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-18s\033[0m %s\n", $$1, $$2}'

up: ## Start all services
	docker compose up -d

down: ## Stop all services
	docker compose down

build: ## Build and start (first time or after Dockerfile changes)
	docker compose up --build -d

rebuild-backend: ## Rebuild only the backend
	docker compose up --build -d backend

rebuild-frontend: ## Rebuild only the frontend
	docker compose up --build -d frontend

restart: ## Restart all services
	docker compose restart

# -- Observability ------------------------------------------------------------

logs: ## Tail all logs
	docker compose logs -f --tail 50

logs-backend: ## Tail backend logs
	docker compose logs -f --tail 50 backend

logs-frontend: ## Tail frontend logs
	docker compose logs -f --tail 50 frontend

status: ## Show running containers and health
	@docker compose ps
	@echo ""
	@echo "--- Health Check ---"
	@curl -sf http://localhost:8001/health 2>/dev/null && echo " Backend: OK" || echo " Backend: DOWN"
	@curl -sf http://localhost:3001 -o /dev/null 2>/dev/null && echo " Frontend: OK" || echo " Frontend: DOWN"

health: ## Quick health check (JSON)
	@curl -s http://localhost:8001/health | python3 -m json.tool

# -- Data sync ----------------------------------------------------------------

PW ?= admin123
API = http://localhost:8001
H = -H "X-App-Password: $(PW)"

sync-all: ## Trigger sync for all accounts
	@curl -s -X POST $(API)/api/sync/all $(H) | python3 -m json.tool

ig-sync: ## Run Instagram sync from host (uses browser session)
	@python3 scripts/ig_sync.py

ig-sync-account: ## Sync specific Instagram account (usage: make ig-sync-account USERNAME=alexmadrazo97)
	@python3 scripts/ig_sync.py --username $(USERNAME)

baselines: ## Recompute performance baselines
	@curl -s -X POST $(API)/api/sync/baselines $(H) | python3 -m json.tool

briefs: ## Generate daily briefs (AI)
	@curl -s -X POST $(API)/api/sync/briefs $(H) | python3 -m json.tool

recs: ## Generate recommendations (AI)
	@curl -s -X POST $(API)/api/sync/recommendations $(H) | python3 -m json.tool

sync-status: ## Check sync status
	@curl -s $(API)/api/sync/status $(H) | python3 -m json.tool

accounts: ## List all accounts
	@curl -s $(API)/api/accounts $(H) | python3 -m json.tool

# -- Database -----------------------------------------------------------------

db-shell: ## Open psql shell
	docker compose exec db psql -U smadmin -d social_media_agent

db-counts: ## Show row counts for all tables
	@docker compose exec -T db psql -U smadmin -d social_media_agent -c "\
		SELECT 'accounts' as t, count(*) FROM accounts UNION ALL \
		SELECT 'posts', count(*) FROM posts UNION ALL \
		SELECT 'post_metrics', count(*) FROM post_metrics UNION ALL \
		SELECT 'insights', count(*) FROM insights UNION ALL \
		SELECT 'recommendations', count(*) FROM recommendations UNION ALL \
		SELECT 'daily_briefs', count(*) FROM daily_briefs UNION ALL \
		SELECT 'account_baselines', count(*) FROM account_baselines \
		ORDER BY 1;"

db-reset: ## Drop and recreate all tables (DESTRUCTIVE)
	@echo "⚠ This will delete ALL data. Press Ctrl+C to abort."
	@read -p "Type 'yes' to confirm: " confirm && [ "$$confirm" = "yes" ] || exit 1
	docker compose exec -T db psql -U smadmin -d social_media_agent -c "\
		DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
	docker compose restart backend
	@echo "Database reset. Backend will recreate tables on startup."

db-dump: ## Dump database to backup file
	docker compose exec -T db pg_dump -U smadmin social_media_agent > backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "Backup saved."

# -- Development tools --------------------------------------------------------

seed: ## Seed database with sample data
	python3 scripts/seed_sample_data.py

tunnel: ## Expose frontend publicly via ngrok
	@echo "Starting ngrok tunnel on port 3001..."
	@ngrok http 3001

exec-backend: ## Run a command in the backend container (usage: make exec-backend CMD="python -c 'print(1)'")
	docker compose exec backend $(CMD)

# -- Cleanup ------------------------------------------------------------------

clean: ## Remove containers, volumes, and build cache
	docker compose down -v --remove-orphans
	docker builder prune -f
	@echo "Cleaned up."

prune: ## Remove all stopped containers and dangling images
	docker system prune -f

# -- Fly.io deployment --------------------------------------------------------

fly-setup: ## Provision Fly.io infrastructure (apps, Postgres, Redis, volumes)
	@./scripts/fly-deploy.sh setup

fly-secrets: ## Push secrets from .env to Fly apps
	@./scripts/fly-deploy.sh secrets

fly-deploy: ## Deploy both backend and frontend to Fly.io
	@./scripts/fly-deploy.sh deploy

fly-deploy-backend: ## Deploy backend to Fly.io
	@./scripts/fly-deploy.sh deploy-backend

fly-deploy-frontend: ## Deploy frontend to Fly.io
	@./scripts/fly-deploy.sh deploy-frontend

fly-status: ## Show Fly.io resource status
	@./scripts/fly-deploy.sh status

fly-logs: ## Tail Fly.io logs (both services)
	@./scripts/fly-deploy.sh logs

fly-logs-backend: ## Tail Fly.io backend logs
	@./scripts/fly-deploy.sh logs-backend

fly-logs-frontend: ## Tail Fly.io frontend logs
	@./scripts/fly-deploy.sh logs-frontend

fly-db: ## Open psql console to Fly Postgres
	@./scripts/fly-deploy.sh db-console

fly-destroy: ## Destroy all Fly.io resources (DESTRUCTIVE)
	@./scripts/fly-deploy.sh destroy
