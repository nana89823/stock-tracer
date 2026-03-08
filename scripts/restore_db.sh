#!/usr/bin/env bash
#
# restore_db.sh - Restore the Stock Tracer PostgreSQL database from a backup.
#
# Usage:
#   ./scripts/restore_db.sh <backup_file>
#
# Example:
#   ./scripts/restore_db.sh backups/backup_20260308_120000.sql.gz
#
# Environment variables (with defaults):
#   POSTGRES_USER     (default: stock_tracer)
#   POSTGRES_PASSWORD (default: stock_tracer_dev)
#   POSTGRES_DB       (default: stock_tracer)
#   POSTGRES_HOST     (default: localhost)
#   POSTGRES_PORT     (default: 5432)
#
# WARNING: This will DROP and recreate the target database!
#

set -euo pipefail

# --- Usage check ---
if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <backup_file>" >&2
  echo "" >&2
  echo "Example:" >&2
  echo "  $0 backups/backup_20260308_120000.sql.gz" >&2
  exit 1
fi

BACKUP_FILE="$1"

if [[ ! -f "$BACKUP_FILE" ]]; then
  echo "ERROR: Backup file not found: ${BACKUP_FILE}" >&2
  exit 1
fi

# Configuration with defaults
DB_USER="${POSTGRES_USER:-stock_tracer}"
DB_PASSWORD="${POSTGRES_PASSWORD:-stock_tracer_dev}"
DB_NAME="${POSTGRES_DB:-stock_tracer}"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"

echo "=== Stock Tracer DB Restore ==="
echo "Database: ${DB_NAME}@${DB_HOST}:${DB_PORT}"
echo "Backup:   ${BACKUP_FILE}"
echo ""

# Confirmation prompt
read -r -p "This will DROP and recreate the database '${DB_NAME}'. Continue? [y/N] " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
  echo "Aborted."
  exit 0
fi

export PGPASSWORD="$DB_PASSWORD"

echo "Dropping and recreating database '${DB_NAME}'..."
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS \"${DB_NAME}\";"
psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "CREATE DATABASE \"${DB_NAME}\";"

echo "Restoring from backup..."
if [[ "$BACKUP_FILE" == *.gz ]]; then
  gunzip -c "$BACKUP_FILE" | psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" --quiet
else
  psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" --quiet < "$BACKUP_FILE"
fi

unset PGPASSWORD

echo ""
echo "Restore completed successfully."
