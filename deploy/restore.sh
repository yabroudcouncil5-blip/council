#!/usr/bin/env bash
set -euo pipefail
: "${DATABASE_URL:?DATABASE_URL is required}"
: "${1:?Usage: restore.sh backup.sql.gz}"
gzip -dc "$1" | psql "$DATABASE_URL"
echo "restore completed from $1"
