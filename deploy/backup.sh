#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
: "${DATABASE_URL:?DATABASE_URL is required}"
BACKUP_DIR="${BACKUP_DIR:-/srv/backups/yabroud}"
mkdir -p "$BACKUP_DIR"
stamp="$(date +%Y-%m-%d_%H%M%S)"
pg_dump "$DATABASE_URL" | gzip > "$BACKUP_DIR/database-$stamp.sql.gz"
find "$BACKUP_DIR" -type f -name 'database-*.sql.gz' -mtime +30 -delete
test -s "$BACKUP_DIR/database-$stamp.sql.gz"
echo "backup created: $BACKUP_DIR/database-$stamp.sql.gz"
