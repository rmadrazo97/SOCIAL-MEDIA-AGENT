#!/bin/bash
# Restore PostgreSQL database from a backup file
set -euo pipefail

if [ -z "${1:-}" ]; then
    echo "Usage: $0 <backup_file.sql>"
    echo ""
    echo "Available backups:"
    ls -lt backups/*.sql 2>/dev/null | head -10 || echo "  No backups found in ./backups/"
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: File not found: $BACKUP_FILE"
    exit 1
fi

echo "⚠ This will REPLACE all data in the database."
read -p "Type 'yes' to confirm: " confirm
if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

echo "Dropping existing schema..."
docker compose exec -T db psql -U smadmin -d social_media_agent -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

echo "Restoring from $BACKUP_FILE..."
docker compose exec -T db psql -U smadmin -d social_media_agent < "$BACKUP_FILE"

echo "Restarting backend..."
docker compose restart backend

echo "Restore complete."
