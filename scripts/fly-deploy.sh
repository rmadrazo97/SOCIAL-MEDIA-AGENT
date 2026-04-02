#!/bin/bash
set -euo pipefail

# =============================================================================
# Fly.io Infrastructure-as-Code Deployment Script
# Social Media Agent
# =============================================================================
#
# This script is the single entry point for provisioning and deploying the
# Social Media Agent to Fly.io. All infrastructure (apps, databases, volumes)
# is created idempotently — safe to re-run at any time.
#
# Prerequisites:
#   - flyctl CLI installed (https://fly.io/docs/flyctl/install/)
#   - Authenticated: flyctl auth login
#   - .env file at project root with required secrets
#
# Usage: ./scripts/fly-deploy.sh <command>
#
# Commands:
#   setup            Provision all Fly.io infrastructure (idempotent)
#   secrets          Push secrets from .env to Fly apps
#   deploy           Build and deploy both services
#   deploy-backend   Deploy backend only
#   deploy-frontend  Deploy frontend only
#   status           Show status of all Fly resources
#   logs             Tail logs from both services
#   logs-backend     Tail backend logs
#   logs-frontend    Tail frontend logs
#   db-console       Open psql console to Fly Postgres
#   destroy          Tear down all Fly.io resources (DESTRUCTIVE)
# =============================================================================

# --- Configuration -----------------------------------------------------------
# Change these if you fork the project or want different naming.

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

BACKEND_APP="sma-backend"
FRONTEND_APP="sma-frontend"
POSTGRES_APP="sma-agent-db"
REDIS_NAME="sma-redis"
REGION="iad"                    # Primary region (Ashburn, Virginia US)
VOLUME_NAME="sma_media"
VOLUME_SIZE_GB=1
POSTGRES_VM="shared-cpu-1x"
POSTGRES_DISK_GB=1

# --- Helpers -----------------------------------------------------------------

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()     { echo -e "${GREEN}[+]${NC} $*"; }
warn()    { echo -e "${YELLOW}[!]${NC} $*"; }
error()   { echo -e "${RED}[x]${NC} $*"; exit 1; }
info()    { echo -e "${CYAN}[i]${NC} $*"; }

app_exists()    { flyctl apps list --json 2>/dev/null | grep -q "\"$1\""; }
pg_exists()     { flyctl postgres list 2>/dev/null | grep -q "$1"; }
volume_exists() { flyctl volumes list --app "$1" --json 2>/dev/null | grep -q "\"$2\""; }

require_flyctl() {
  command -v flyctl >/dev/null 2>&1 || error "flyctl not found. Install: https://fly.io/docs/flyctl/install/"
  flyctl auth whoami >/dev/null 2>&1 || error "Not logged in. Run: flyctl auth login"
  info "Authenticated as $(flyctl auth whoami)"
}

# --- Commands ----------------------------------------------------------------

cmd_setup() {
  require_flyctl
  log "Provisioning Fly.io infrastructure..."
  echo ""

  # 1. Backend app
  if app_exists "$BACKEND_APP"; then
    warn "App '$BACKEND_APP' already exists"
  else
    flyctl apps create "$BACKEND_APP" --org personal
    log "Created app: $BACKEND_APP"
  fi

  # 2. Frontend app
  if app_exists "$FRONTEND_APP"; then
    warn "App '$FRONTEND_APP' already exists"
  else
    flyctl apps create "$FRONTEND_APP" --org personal
    log "Created app: $FRONTEND_APP"
  fi

  # 3. Postgres cluster
  if pg_exists "$POSTGRES_APP"; then
    warn "Postgres '$POSTGRES_APP' already exists"
  else
    log "Creating Postgres cluster (this takes ~60s)..."
    flyctl postgres create \
      --name "$POSTGRES_APP" \
      --region "$REGION" \
      --vm-size "$POSTGRES_VM" \
      --volume-size "$POSTGRES_DISK_GB" \
      --initial-cluster-size 1
    log "Postgres cluster created"
  fi

  # 4. Attach Postgres to backend (sets DATABASE_URL secret automatically)
  if flyctl secrets list --app "$BACKEND_APP" 2>/dev/null | grep -q "DATABASE_URL"; then
    warn "DATABASE_URL already set on $BACKEND_APP (Postgres already attached)"
  else
    log "Attaching Postgres to backend..."
    flyctl postgres attach "$POSTGRES_APP" --app "$BACKEND_APP"
    log "Postgres attached — DATABASE_URL set automatically"
  fi

  # 5. Redis (Upstash via Fly)
  info "Checking Redis..."
  if flyctl redis list 2>/dev/null | grep -q "$REDIS_NAME"; then
    warn "Redis '$REDIS_NAME' already exists"
  else
    log "Creating Upstash Redis..."
    flyctl redis create \
      --name "$REDIS_NAME" \
      --region "$REGION" \
      --no-replicas \
      --no-eviction 2>/dev/null \
    && log "Redis created" \
    || warn "Auto-create failed. Create manually: flyctl redis create --name $REDIS_NAME"
  fi

  # 6. Persistent volume for media
  if volume_exists "$BACKEND_APP" "$VOLUME_NAME"; then
    warn "Volume '$VOLUME_NAME' already exists on $BACKEND_APP"
  else
    flyctl volumes create "$VOLUME_NAME" \
      --app "$BACKEND_APP" \
      --region "$REGION" \
      --size "$VOLUME_SIZE_GB" \
      --yes
    log "Created ${VOLUME_SIZE_GB}GB volume: $VOLUME_NAME"
  fi

  echo ""
  log "Infrastructure provisioned!"
  echo ""
  echo "  Apps:     $BACKEND_APP, $FRONTEND_APP"
  echo "  Postgres: $POSTGRES_APP"
  echo "  Redis:    $REDIS_NAME"
  echo "  Volume:   $VOLUME_NAME (${VOLUME_SIZE_GB}GB on $BACKEND_APP)"
  echo "  Region:   $REGION"
  echo ""
  info "Next steps:"
  echo "  1. Push secrets:  ./scripts/fly-deploy.sh secrets"
  echo "  2. Deploy:        ./scripts/fly-deploy.sh deploy"
}

cmd_secrets() {
  require_flyctl
  log "Pushing secrets from .env..."

  ENV_FILE="$PROJECT_ROOT/.env"
  [ -f "$ENV_FILE" ] || error ".env file not found at $ENV_FILE"

  # Parse .env safely — read key=value pairs without shell-sourcing
  # (handles passwords with special chars like ), #, ;, etc.)
  get_env() {
    grep -E "^${1}=" "$ENV_FILE" | head -1 | sed "s/^${1}=//"
  }

  # Backend secrets (DATABASE_URL is set by Postgres attach, not here)
  flyctl secrets set --app "$BACKEND_APP" \
    "APP_PASSWORD=$(get_env APP_PASSWORD)" \
    "MOONSHOT_API_KEY=$(get_env MOONSHOT_API_KEY)" \
    "INSTAGRAM_USERNAME=$(get_env INSTAGRAM_USERNAME)" \
    "INSTAGRAM_PASSWORD=$(get_env INSTAGRAM_PASSWORD)" \
    "INSTAGRAM_SESSION_ID=$(get_env INSTAGRAM_SESSION_ID)" \
    "INSTAGRAM_CSRF_TOKEN=$(get_env INSTAGRAM_CSRF_TOKEN)" \
    "ENCRYPTION_KEY=$(get_env ENCRYPTION_KEY)" \
    "TIKTOK_CLIENT_KEY=$(get_env TIKTOK_CLIENT_KEY)" \
    "TIKTOK_CLIENT_SECRET=$(get_env TIKTOK_CLIENT_SECRET)"

  log "Backend secrets set (9 keys)"

  # Frontend: BACKEND_URL for internal service discovery
  flyctl secrets set --app "$FRONTEND_APP" \
    "BACKEND_URL=http://${BACKEND_APP}.internal:8000"

  log "Frontend secrets set"
  echo ""
  info "DATABASE_URL is set automatically by Fly Postgres attach"
  info "REDIS_URL must be set manually if using Redis. Get it with: flyctl redis status $REDIS_NAME"
}

cmd_deploy_backend() {
  require_flyctl
  log "Deploying $BACKEND_APP..."
  cd "$PROJECT_ROOT/backend"
  flyctl deploy --app "$BACKEND_APP"
  echo ""
  log "Backend deployed: https://${BACKEND_APP}.fly.dev"
}

cmd_deploy_frontend() {
  require_flyctl
  log "Deploying $FRONTEND_APP..."
  cd "$PROJECT_ROOT/frontend"
  flyctl deploy --app "$FRONTEND_APP"
  echo ""
  log "Frontend deployed: https://${FRONTEND_APP}.fly.dev"
}

cmd_deploy() {
  cmd_deploy_backend
  echo ""
  cmd_deploy_frontend
  echo ""
  log "Full deployment complete!"
  echo ""
  echo "  Backend:  https://${BACKEND_APP}.fly.dev"
  echo "  Frontend: https://${FRONTEND_APP}.fly.dev"
}

cmd_status() {
  require_flyctl
  echo ""
  info "=== Backend ($BACKEND_APP) ==="
  flyctl status --app "$BACKEND_APP" 2>/dev/null || warn "App not found or not deployed"
  echo ""
  info "=== Frontend ($FRONTEND_APP) ==="
  flyctl status --app "$FRONTEND_APP" 2>/dev/null || warn "App not found or not deployed"
  echo ""
  info "=== Postgres ($POSTGRES_APP) ==="
  flyctl status --app "$POSTGRES_APP" 2>/dev/null || warn "Postgres not found"
  echo ""
  info "=== Volumes ==="
  flyctl volumes list --app "$BACKEND_APP" 2>/dev/null || warn "No volumes"
}

cmd_logs() {
  require_flyctl
  info "Tailing logs from both services (Ctrl+C to stop)..."
  # Run both in background, kill on exit
  trap 'kill 0' EXIT
  flyctl logs --app "$BACKEND_APP" &
  flyctl logs --app "$FRONTEND_APP" &
  wait
}

cmd_logs_backend() {
  require_flyctl
  flyctl logs --app "$BACKEND_APP"
}

cmd_logs_frontend() {
  require_flyctl
  flyctl logs --app "$FRONTEND_APP"
}

cmd_db_console() {
  require_flyctl
  log "Connecting to Fly Postgres..."
  flyctl postgres connect --app "$POSTGRES_APP"
}

cmd_destroy() {
  require_flyctl
  echo -e "${RED}WARNING: This will destroy ALL Fly.io resources for this project.${NC}"
  echo "  Apps:     $BACKEND_APP, $FRONTEND_APP"
  echo "  Postgres: $POSTGRES_APP"
  echo "  Redis:    $REDIS_NAME"
  echo ""
  read -rp "Type 'destroy' to confirm: " confirm
  [ "$confirm" = "destroy" ] || { echo "Aborted."; exit 0; }

  echo ""
  flyctl apps destroy "$FRONTEND_APP" --yes 2>/dev/null && log "Destroyed $FRONTEND_APP" || warn "$FRONTEND_APP not found"
  flyctl apps destroy "$BACKEND_APP" --yes 2>/dev/null && log "Destroyed $BACKEND_APP" || warn "$BACKEND_APP not found"
  flyctl apps destroy "$POSTGRES_APP" --yes 2>/dev/null && log "Destroyed $POSTGRES_APP" || warn "$POSTGRES_APP not found"
  flyctl redis destroy "$REDIS_NAME" --yes 2>/dev/null && log "Destroyed $REDIS_NAME" || warn "$REDIS_NAME not found"
  log "All resources destroyed."
}

# --- Entrypoint --------------------------------------------------------------

case "${1:-help}" in
  setup)            cmd_setup ;;
  secrets)          cmd_secrets ;;
  deploy)           cmd_deploy ;;
  deploy-backend)   cmd_deploy_backend ;;
  deploy-frontend)  cmd_deploy_frontend ;;
  status)           cmd_status ;;
  logs)             cmd_logs ;;
  logs-backend)     cmd_logs_backend ;;
  logs-frontend)    cmd_logs_frontend ;;
  db-console)       cmd_db_console ;;
  destroy)          cmd_destroy ;;
  help|*)
    echo "Fly.io Deployment — Social Media Agent"
    echo ""
    echo "Usage: $0 <command>"
    echo ""
    echo "Infrastructure:"
    echo "  setup            Provision apps, Postgres, Redis, volumes (idempotent)"
    echo "  secrets          Push secrets from .env to Fly apps"
    echo "  destroy          Tear down all resources (DESTRUCTIVE)"
    echo ""
    echo "Deployment:"
    echo "  deploy           Build and deploy both services"
    echo "  deploy-backend   Deploy backend only"
    echo "  deploy-frontend  Deploy frontend only"
    echo ""
    echo "Operations:"
    echo "  status           Show status of all Fly resources"
    echo "  logs             Tail logs from both services"
    echo "  logs-backend     Tail backend logs"
    echo "  logs-frontend    Tail frontend logs"
    echo "  db-console       Open psql console to Fly Postgres"
    ;;
esac
