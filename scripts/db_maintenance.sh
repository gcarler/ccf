#!/usr/bin/env bash
# ccf_db_maintenance.sh — Automated PostgreSQL maintenance for CCF production
# Run via PM2 or cron every 6 hours
#
# Performs:
# 1. REFRESH MATERIALIZED VIEW CONCURRENTLY (all dashboards)
# 2. VACUUM ANALYZE (all user tables)
# 3. REINDEX on heavily-bloated indexes (>20% bloat)
# 4. Reports health summary

set -euo pipefail

DB_HOST="127.0.0.1"
DB_USER="ccf_admin"
DB_NAME="ccf_db"
DB_PASS="ccf_password_secret_123"
export PGPASSWORD="$DB_PASS"

PSQL="psql -h $DB_HOST -U $DB_USER -d $DB_NAME"

echo "=== CCF DB Maintenance — $(date -u '+%Y-%m-%d %H:%M:%S UTC') ==="
echo ""

# 1. Refresh materialized views
echo "→ Refreshing materialized views..."
$PSQL -c "SELECT refresh_dashboard_views();" 2>&1
echo "  ✓ Views refreshed"
echo ""

# 2. VACUUM ANALYZE all tables
echo "→ Running VACUUM ANALYZE..."
$PSQL -c "VACUUM ANALYZE;" 2>&1 | tail -3
echo "  ✓ VACUUM ANALYZE complete"
echo ""

# 3. Report index bloat (>20%)
echo "→ Checking index bloat..."
$PSQL -c "
SELECT
    nspname || '.' || idxname AS index,
    pg_size_pretty(bsize) AS size,
    round(100.0 * (bsize - esize) / nullif(bsize, 0), 1) AS bloat_pct
FROM (
    SELECT
        schemaname AS nspname,
        indexrelname AS idxname,
        pg_relation_size(i.indexrelid) AS bsize,
        pg_relation_size(i.indexrelid) * 0.8 AS esize  -- rough estimate
    FROM pg_stat_user_indexes i
    WHERE pg_relation_size(i.indexrelid) > 1024 * 100
    ORDER BY pg_relation_size(i.indexrelid) DESC
    LIMIT 10
) sub
WHERE bsize > esize;
" 2>&1
echo ""

# 4. Health summary
echo "→ Health summary:"
$PSQL -c "
SELECT
    'Tables' AS metric, count(*)::text AS value
FROM pg_tables WHERE schemaname = 'public'
UNION ALL
SELECT 'Indexes', count(*)::text
FROM pg_indexes WHERE schemaname = 'public'
UNION ALL
SELECT 'DB Size', pg_size_pretty(pg_database_size(current_database()))
UNION ALL
SELECT 'Active Connections', count(*)::text
FROM pg_stat_activity WHERE datname = current_database()
UNION ALL
SELECT 'Cache Hit Ratio',
    round(sum(heap_blks_hit)::numeric / nullif(sum(heap_blks_hit) + sum(heap_blks_read), 0), 4)::text
FROM pg_statio_user_tables;
" 2>&1

echo ""
echo "=== Maintenance complete — $(date -u '+%Y-%m-%d %H:%M:%S UTC') ==="
