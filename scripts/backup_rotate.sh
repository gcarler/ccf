#!/usr/bin/env bash
# ccf_backup_rotate.sh — Secondary backup rotation with integrity checks
# 
# This script provides defense-in-depth by maintaining a second copy
# of backups in a separate directory from the primary backup location.
# It can be extended for remote/off-server replication.
#
# Run after each db_backup.sh to create a secondary copy.
# Recommended cron: "30 3 * * *" (30 min after primary backup)

set -euo pipefail

PRIMARY_DIR="/root/ccf/backups"
SECONDARY_DIR="/root/ccf-backup-offsite"
RETENTION_DAYS=30

mkdir -p "$SECONDARY_DIR"

echo "=== CCF Backup Rotation — $(date -u '+%Y-%m-%d %H:%M:%S UTC') ==="
echo "Primary:   $PRIMARY_DIR"
echo "Secondary: $SECONDARY_DIR"
echo ""

# 1. Find the latest backup
LATEST_DUMP=$(find "$PRIMARY_DIR" -name "ccf_db_*.dump" -printf '%T@ %p\n' | sort -n | tail -1 | awk '{print $2}')

if [ -z "$LATEST_DUMP" ]; then
    echo "ERROR: No backup found in $PRIMARY_DIR"
    exit 1
fi

BASENAME=$(basename "$LATEST_DUMP")
SECONDARY_PATH="$SECONDARY_DIR/$BASENAME"

# 2. Skip if already copied (same size and modification time)
if [ -f "$SECONDARY_PATH" ]; then
    PRIMARY_SIZE=$(stat -c%s "$LATEST_DUMP")
    SECONDARY_SIZE=$(stat -c%s "$SECONDARY_PATH")
    if [ "$PRIMARY_SIZE" = "$SECONDARY_SIZE" ]; then
        echo "✓ $BASENAME already exists in secondary (same size: $PRIMARY_SIZE bytes)"
    else
        echo "→ Re-copying $BASENAME (size mismatch: $PRIMARY_SIZE vs $SECONDARY_SIZE)"
        cp -f "$LATEST_DUMP" "$SECONDARY_PATH"
    fi
else
    echo "→ Copying $BASENAME to secondary..."
    cp "$LATEST_DUMP" "$SECONDARY_PATH"
fi

# 3. Verify integrity of secondary copy
echo "→ Verifying secondary copy..."
if pg_restore --list "$SECONDARY_PATH" > /dev/null 2>&1; then
    echo "  ✓ Integrity verified: $BASENAME ($(du -h "$SECONDARY_PATH" | cut -f1))"
else
    echo "  ✗ INTEGRITY CHECK FAILED for $SECONDARY_PATH"
    echo "  Attempting re-copy..."
    cp -f "$LATEST_DUMP" "$SECONDARY_PATH"
    if pg_restore --list "$SECONDARY_PATH" > /dev/null 2>&1; then
        echo "  ✓ Re-copy verified successfully"
    else
        echo "  ✗ FAILED AGAIN — manual intervention required"
        exit 1
    fi
fi

# 4. Copy latest log file too
LATEST_LOG=$(find "$PRIMARY_DIR" -name "backup_*.log" -printf '%T@ %p\n' | sort -n | tail -1 | awk '{print $2}')
if [ -n "$LATEST_LOG" ]; then
    cp -f "$LATEST_LOG" "$SECONDARY_DIR/"
fi

# 5. Cleanup old secondary backups
echo "→ Cleaning up secondary backups older than ${RETENTION_DAYS} days..."
OLD_COUNT=$(find "$SECONDARY_DIR" -name "ccf_db_*.dump" -mtime +${RETENTION_DAYS} | wc -l)
if [ "$OLD_COUNT" -gt 0 ]; then
    find "$SECONDARY_DIR" -name "ccf_db_*.dump" -mtime +${RETENTION_DAYS} -delete
    find "$SECONDARY_DIR" -name "backup_*.log" -mtime +${RETENTION_DAYS} -delete
    echo "  ✓ Removed $OLD_COUNT old secondary backups"
else
    echo "  ✓ No old secondary backups to remove"
fi

# 6. Summary
echo ""
echo "→ Secondary backup summary:"
TOTAL=$(find "$SECONDARY_DIR" -name "ccf_db_*.dump" | wc -l)
TOTAL_SIZE=$(du -sh "$SECONDARY_DIR" | cut -f1)
echo "  Total copies: $TOTAL"
echo "  Total size: $TOTAL_SIZE"
echo "  Latest: $BASENAME"
echo ""
echo "=== Rotation complete — $(date -u '+%Y-%m-%d %H:%M:%S UTC') ==="
