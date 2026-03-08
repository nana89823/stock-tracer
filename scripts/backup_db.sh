#!/usr/bin/env bash
#
# backup_db.sh - Back up the Stock Tracer PostgreSQL database.
#
# Usage:
#   ./scripts/backup_db.sh
#
# Environment variables (with defaults):
#   POSTGRES_USER     (default: stock_tracer)
#   POSTGRES_PASSWORD (default: stock_tracer_dev)
#   POSTGRES_DB       (default: stock_tracer)
#   POSTGRES_HOST     (default: localhost)
#   POSTGRES_PORT     (default: 5432)
#   BACKUP_DIR        (default: <project_root>/backups)
#   BACKUP_RETAIN_DAYS (default: 7)
#
# Output:
#   Compressed backup file: backup_YYYYMMDD_HHMMSS.sql.gz
#

set -euo pipefail

# Resolve project root (parent of scripts/)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration with defaults
DB_USER="${POSTGRES_USER:-stock_tracer}"
DB_PASSWORD="${POSTGRES_PASSWORD:-stock_tracer_dev}"
DB_NAME="${POSTGRES_DB:-stock_tracer}"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_ROOT/backups}"
RETAIN_DAYS="${BACKUP_RETAIN_DAYS:-7}"

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

# Generate filename with timestamp
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_FILE="$BACKUP_DIR/backup_${TIMESTAMP}.sql.gz"

echo "=== Stock Tracer DB Backup ==="
echo "Database: ${DB_NAME}@${DB_HOST}:${DB_PORT}"
echo "Output:   ${BACKUP_FILE}"
echo ""

# Run pg_dump with gzip compression
export PGPASSWORD="$DB_PASSWORD"
pg_dump \
  -h "$DB_HOST" \
  -p "$DB_PORT" \
  -U "$DB_USER" \
  -d "$DB_NAME" \
  --no-owner \
  --no-acl \
  | gzip > "$BACKUP_FILE"
unset PGPASSWORD

# Verify the backup file was created and is non-empty
if [[ ! -s "$BACKUP_FILE" ]]; then
  echo "ERROR: Backup file is empty or was not created." >&2
  rm -f "$BACKUP_FILE"
  exit 1
fi

FILE_SIZE="$(du -h "$BACKUP_FILE" | cut -f1)"
echo "Backup completed: ${BACKUP_FILE} (${FILE_SIZE})"

# Clean up old backups (older than RETAIN_DAYS days)
echo ""
echo "Cleaning up backups older than ${RETAIN_DAYS} days..."
DELETED=$(find "$BACKUP_DIR" -name "backup_*.sql.gz" -type f -mtime +"$RETAIN_DAYS" -print -delete | wc -l)
echo "Deleted ${DELETED} old backup(s)."

echo ""
echo "Done."
