#!/bin/bash
# Backup PostgreSQL database to a timestamped SQL file
set -euo pipefail

BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/social_media_agent_${TIMESTAMP}.sql"

mkdir -p "$BACKUP_DIR"

echo "Backing up database..."
docker compose exec -T db pg_dump -U smadmin social_media_agent > "$BACKUP_FILE"

SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "Backup saved: $BACKUP_FILE ($SIZE)"

# Keep only last 10 backups
cd "$BACKUP_DIR"
ls -t *.sql 2>/dev/null | tail -n +11 | xargs -r rm --
echo "Cleanup: kept last 10 backups."
