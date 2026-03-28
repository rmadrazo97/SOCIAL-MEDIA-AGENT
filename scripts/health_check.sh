#!/bin/bash
# Health check script — verifies all services are running and data is flowing
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

API="http://localhost:8001"
FRONTEND="http://localhost:3001"
PW="${APP_PASSWORD:-admin123}"

pass() { echo -e "  ${GREEN}✓${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; }
warn() { echo -e "  ${YELLOW}!${NC} $1"; }

echo "=== Service Health ==="

# Docker containers
if docker compose ps --format json 2>/dev/null | python3 -c "import sys,json; [print() for l in sys.stdin]" &>/dev/null; then
    pass "Docker Compose running"
else
    fail "Docker Compose not running"
    exit 1
fi

# Backend
if curl -sf "$API/health" &>/dev/null; then
    pass "Backend API (port 8001)"
else
    fail "Backend API (port 8001)"
fi

# Frontend
if curl -sf "$FRONTEND" -o /dev/null &>/dev/null; then
    pass "Frontend (port 3001)"
else
    fail "Frontend (port 3001)"
fi

# PostgreSQL
if docker compose exec -T db pg_isready -U smadmin &>/dev/null; then
    pass "PostgreSQL (port 5433)"
else
    fail "PostgreSQL (port 5433)"
fi

# Redis
if docker compose exec -T redis redis-cli ping 2>/dev/null | grep -q PONG; then
    pass "Redis (port 6380)"
else
    fail "Redis (port 6380)"
fi

echo ""
echo "=== Data Status ==="

# Row counts
COUNTS=$(docker compose exec -T db psql -U smadmin -d social_media_agent -t -c "
SELECT json_build_object(
    'accounts', (SELECT count(*) FROM accounts),
    'posts', (SELECT count(*) FROM posts),
    'metrics', (SELECT count(*) FROM post_metrics),
    'briefs', (SELECT count(*) FROM daily_briefs),
    'recs', (SELECT count(*) FROM recommendations),
    'baselines', (SELECT count(*) FROM account_baselines)
);" 2>/dev/null || echo '{}')

echo "$COUNTS" | python3 -c "
import sys, json
try:
    d = json.loads(sys.stdin.read().strip())
    for k, v in d.items():
        status = '✓' if v > 0 else '!'
        print(f'  {status} {k}: {v}')
except:
    print('  ! Could not read database counts')
"

echo ""
echo "=== Recent Errors (last 5 min) ==="
ERRORS=$(docker compose logs backend --since 5m 2>&1 | grep -c "ERROR" || true)
if [ "$ERRORS" -gt 0 ]; then
    warn "$ERRORS error(s) in last 5 minutes"
    docker compose logs backend --since 5m 2>&1 | grep "ERROR" | tail -3 | sed 's/^/    /'
else
    pass "No errors in last 5 minutes"
fi
