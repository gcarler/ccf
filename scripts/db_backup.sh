#!/usr/bin/env bash
# ccf_db_backup.sh — Automated PostgreSQL backup with rotation
# Run via PM2 or cron daily at 03:00 UTC
#
# Features:
# - Compressed pg_dump with custom format
# - 14-day retention policy
# - Backup verification (pg_restore --list)
# - Backup size reporting
# - Optional upload to remote storage (S3/SeaweedFS)

set -euo pipefail

DB_HOST="127.0.0.1"
DB_USER="ccf_admin"
DB_NAME="ccf_db"
DB_PASS="ccf_password_secret_123"
export PGPASSWORD="$DB_PASS"

BACKUP_DIR="/root/ccf/backups"
RETENTION_DAYS=14
TIMESTAMP=$(date -u '+%Y%m%d_%H%M%S')
BACKUP_FILE="$BACKUP_DIR/ccf_db_${TIMESTAMP}.dump"
LOG_FILE="$BACKUP_DIR/backup_${TIMESTAMP}.log"

mkdir -p "$BACKUP_DIR"

echo "=== CCF DB Backup — $(date -u '+%Y-%m-%d %H:%M:%S UTC') ===" | tee "$LOG_FILE"

# 1. Run backup
echo "→ Starting backup to $BACKUP_FILE..." | tee -a "$LOG_FILE"
START_TIME=$(date +%s)

pg_dump \
    -h "$DB_HOST" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --format=custom \
    --compress=6 \
    --verbose \
    --no-owner \
    --no-privileges \
    --blobs \
    -f "$BACKUP_FILE" \
    2>>"$LOG_FILE"

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

# 2. Verify backup
echo "→ Verifying backup..." | tee -a "$LOG_FILE"
if pg_restore --list "$BACKUP_FILE" > /dev/null 2>&1; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "  ✓ Backup verified: $BACKUP_SIZE (${DURATION}s)" | tee -a "$LOG_FILE"
else
    echo "  ✗ Backup verification FAILED!" | tee -a "$LOG_FILE"
    exit 1
fi

# 3. Cleanup old backups
echo "→ Cleaning up backups older than ${RETENTION_DAYS} days..." | tee -a "$LOG_FILE"
OLD_COUNT=$(find "$BACKUP_DIR" -name "ccf_db_*.dump" -mtime +${RETENTION_DAYS} | wc -l)
if [ "$OLD_COUNT" -gt 0 ]; then
    find "$BACKUP_DIR" -name "ccf_db_*.dump" -mtime +${RETENTION_DAYS} -delete
    find "$BACKUP_DIR" -name "backup_*.log" -mtime +${RETENTION_DAYS} -delete
    echo "  ✓ Removed $OLD_COUNT old backup files" | tee -a "$LOG_FILE"
else
    echo "  ✓ No old backups to remove" | tee -a "$LOG_FILE"
fi

# 4. Summary
echo "" | tee -a "$LOG_FILE"
echo "→ Backup summary:" | tee -a "$LOG_FILE"
TOTAL_BACKUPS=$(find "$BACKUP_DIR" -name "ccf_db_*.dump" | wc -l)
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
echo "  Total backups: $TOTAL_BACKUPS" | tee -a "$LOG_FILE"
echo "  Total size: $TOTAL_SIZE" | tee -a "$LOG_FILE"
echo "  Latest: $BACKUP_FILE ($BACKUP_SIZE)" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "=== Backup complete — $(date -u '+%Y-%m-%d %H:%M:%S UTC') ===" | tee -a "$LOG_FILE"
