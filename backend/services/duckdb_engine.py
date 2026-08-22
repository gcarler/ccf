"""DuckDB OLAP Engine for BI and Dashboards.

Embedded in-memory DuckDB service integrating postgres_scanner (and SQLite scanner)
with fallback in-memory data ingestion for sub-50ms analytical queries:
- Church growth metrics across sedes over time.
- Attendance trends across services and age groups.
- Multi-year financial statements & KPI aggregations.
"""

from __future__ import annotations

import datetime as dt
import logging
import os
import re
import time
import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional

try:
    import duckdb
except ImportError:  # pragma: no cover
    duckdb = None  # type: ignore

from sqlalchemy.orm import Session

from backend import models
from backend.core.config import get_settings

logger = logging.getLogger("CCF-DuckDB-OLAP")
settings = get_settings()


class DuckDBAnalyticsService:
    """Embedded DuckDB OLAP Service for real-time BI aggregations."""

    def __init__(self) -> None:
        self._cached_con: Optional[duckdb.DuckDBPyConnection] = None

    def _ensure_duckdb(self) -> None:
        if duckdb is None:  # pragma: no cover
            raise RuntimeError("duckdb is required for OLAP analytics engine")

    def _init_empty_tables(self, con: duckdb.DuckDBPyConnection) -> None:
        """Create empty DuckDB tables matching the CCF analytical schema."""
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS sedes (
                id VARCHAR,
                nombre VARCHAR,
                ciudad VARCHAR,
                es_activa BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP,
                deleted_at TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS personas (
                id VARCHAR,
                sede_id VARCHAR,
                first_name VARCHAR,
                last_name VARCHAR,
                email VARCHAR,
                phone VARCHAR,
                church_role VARCHAR,
                is_baptized BOOLEAN DEFAULT FALSE,
                estado_vital VARCHAR DEFAULT 'ACTIVO',
                birthday DATE,
                registration_date DATE,
                church_join_date DATE,
                created_at TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS crm_events (
                id VARCHAR,
                sede_id VARCHAR,
                name VARCHAR,
                event_type VARCHAR DEFAULT 'DOMINICAL',
                event_date TIMESTAMP,
                location VARCHAR,
                status VARCHAR DEFAULT 'SCHEDULED',
                target_audience VARCHAR DEFAULT 'ALL',
                created_at TIMESTAMP,
                deleted_at TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS event_attendances (
                id VARCHAR,
                event_id VARCHAR,
                persona_id VARCHAR,
                session_date DATE
            );
            CREATE TABLE IF NOT EXISTS donations (
                id VARCHAR,
                persona_id VARCHAR,
                amount DOUBLE DEFAULT 0.0,
                currency VARCHAR DEFAULT 'COP',
                sede_id VARCHAR,
                donation_type VARCHAR DEFAULT 'Diezmo',
                status VARCHAR DEFAULT 'completed',
                donation_date DATE,
                created_at TIMESTAMP,
                deleted_at TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS expense_reports (
                id VARCHAR,
                sede_id VARCHAR,
                employee_id VARCHAR,
                report_number VARCHAR,
                total_amount DOUBLE DEFAULT 0.0,
                currency VARCHAR DEFAULT 'COP',
                status VARCHAR DEFAULT 'approved',
                submitted_at TIMESTAMP,
                approved_at TIMESTAMP,
                created_at TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS expense_items (
                id VARCHAR,
                expense_report_id VARCHAR,
                expense_date DATE,
                category VARCHAR DEFAULT 'Operations',
                description VARCHAR,
                amount DOUBLE DEFAULT 0.0,
                currency VARCHAR DEFAULT 'COP',
                created_at TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS financial_statements (
                id VARCHAR,
                sede_id VARCHAR,
                statement_type VARCHAR,
                period_start DATE,
                period_end DATE,
                currency VARCHAR DEFAULT 'COP',
                data_json VARCHAR,
                created_at TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS accounting_entries (
                id VARCHAR,
                sede_id VARCHAR,
                entry_date DATE,
                reference VARCHAR,
                description VARCHAR,
                total_debit DOUBLE DEFAULT 0.0,
                total_credit DOUBLE DEFAULT 0.0,
                status VARCHAR DEFAULT 'posted',
                created_at TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS sesiones_grupo (
                id VARCHAR,
                grupo_id VARCHAR,
                fecha_sesion DATE,
                estado_sesion VARCHAR DEFAULT 'REALIZADA',
                created_at TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS asistencias (
                id VARCHAR,
                sesion_id VARCHAR,
                persona_id VARCHAR,
                estado_asistencia VARCHAR DEFAULT 'ASISTIO',
                created_at TIMESTAMP
            );
            """
        )

    def _format_val(self, v: Any) -> Any:
        if v is None:
            return None
        if isinstance(v, (uuid.UUID,)):
            return str(v)
        if isinstance(v, Decimal):
            return float(v)
        if isinstance(v, (dt.datetime, dt.date)):
            return v
        return v

    def _sync_from_session(self, con: duckdb.DuckDBPyConnection, db: Session) -> None:
        """Ingest active ORM entities from SQLAlchemy session into DuckDB in-memory tables."""
        self._init_empty_tables(con)

        def _safe_query(model_cls: Any) -> List[Any]:
            try:
                return db.query(model_cls).all()
            except Exception as e:
                logger.debug("Failed querying model %s: %s", getattr(model_cls, "__name__", model_cls), e)
                return []

        # 1. Sedes
        sedes_records = _safe_query(models.Sede)
        if sedes_records:
            con.execute("DELETE FROM sedes;")
            rows = [
                (
                    self._format_val(s.id),
                    s.nombre,
                    s.ciudad,
                    bool(s.es_activa),
                    self._format_val(s.created_at),
                    self._format_val(s.deleted_at),
                )
                for s in sedes_records
            ]
            con.executemany("INSERT INTO sedes VALUES (?, ?, ?, ?, ?, ?)", rows)

        # 2. Personas
        personas_records = _safe_query(models.Persona)
        if personas_records:
            con.execute("DELETE FROM personas;")
            rows = [
                (
                    self._format_val(p.id),
                    self._format_val(p.sede_id),
                    p.first_name,
                    p.last_name,
                    p.email,
                    p.phone,
                    p.church_role,
                    bool(p.is_baptized),
                    p.estado_vital or "ACTIVO",
                    self._format_val(p.birthday),
                    self._format_val(p.registration_date),
                    self._format_val(p.church_join_date),
                    self._format_val(p.created_at),
                )
                for p in personas_records
            ]
            con.executemany("INSERT INTO personas VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)

        # 3. CRM Events
        events_records = _safe_query(models.CrmEvent)
        if events_records:
            con.execute("DELETE FROM crm_events;")
            rows = [
                (
                    self._format_val(e.id),
                    self._format_val(e.sede_id),
                    e.name,
                    e.event_type or "DOMINICAL",
                    self._format_val(e.event_date),
                    e.location,
                    e.status or "SCHEDULED",
                    e.target_audience or "ALL",
                    self._format_val(e.created_at),
                    self._format_val(e.deleted_at),
                )
                for e in events_records
            ]
            con.executemany("INSERT INTO crm_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)

        # 4. Event Attendances
        attendances_records = _safe_query(models.EventAttendance)
        if attendances_records:
            con.execute("DELETE FROM event_attendances;")
            rows = [
                (
                    self._format_val(a.id),
                    self._format_val(a.event_id),
                    self._format_val(a.persona_id),
                    self._format_val(a.session_date),
                )
                for a in attendances_records
            ]
            con.executemany("INSERT INTO event_attendances VALUES (?, ?, ?, ?)", rows)

        # 5. Donations
        donations_records = _safe_query(models.Donation)
        if donations_records:
            con.execute("DELETE FROM donations;")
            rows = [
                (
                    self._format_val(d.id),
                    self._format_val(d.persona_id),
                    self._format_val(d.amount) or 0.0,
                    d.currency or "COP",
                    self._format_val(d.sede_id),
                    d.donation_type or "Diezmo",
                    d.status or "completed",
                    self._format_val(d.donation_date),
                    self._format_val(d.created_at),
                    self._format_val(d.deleted_at),
                )
                for d in donations_records
            ]
            con.executemany("INSERT INTO donations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)

        # 6. Expense Reports & Items
        expense_reports = _safe_query(models.ExpenseReport)
        if expense_reports:
            con.execute("DELETE FROM expense_reports;")
            rows = [
                (
                    self._format_val(r.id),
                    self._format_val(r.sede_id),
                    self._format_val(r.employee_id),
                    r.report_number,
                    self._format_val(r.total_amount) or 0.0,
                    r.currency or "COP",
                    r.status or "approved",
                    self._format_val(r.submitted_at),
                    self._format_val(r.approved_at),
                    self._format_val(r.created_at),
                )
                for r in expense_reports
            ]
            con.executemany("INSERT INTO expense_reports VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)

        expense_items = _safe_query(models.ExpenseItem)
        if expense_items:
            con.execute("DELETE FROM expense_items;")
            rows = [
                (
                    self._format_val(i.id),
                    self._format_val(i.expense_report_id),
                    self._format_val(i.expense_date),
                    i.category or "Operations",
                    i.description or "",
                    self._format_val(i.amount) or 0.0,
                    i.currency or "COP",
                    self._format_val(i.created_at),
                )
                for i in expense_items
            ]
            con.executemany("INSERT INTO expense_items VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)

        # 7. Financial Statements
        statements = _safe_query(models.FinancialStatement)
        if statements:
            con.execute("DELETE FROM financial_statements;")
            rows = [
                (
                    self._format_val(s.id),
                    self._format_val(s.sede_id),
                    s.statement_type,
                    self._format_val(s.period_start),
                    self._format_val(s.period_end),
                    s.currency or "COP",
                    str(s.data_json or {}),
                    self._format_val(s.created_at),
                )
                for s in statements
            ]
            con.executemany("INSERT INTO financial_statements VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)

        # 8. Accounting Entries
        entries = _safe_query(models.AccountingEntry)
        if entries:
            con.execute("DELETE FROM accounting_entries;")
            rows = [
                (
                    self._format_val(e.id),
                    self._format_val(e.sede_id),
                    self._format_val(e.entry_date),
                    e.reference,
                    e.description or "",
                    self._format_val(e.total_debit) or 0.0,
                    self._format_val(e.total_credit) or 0.0,
                    e.status or "posted",
                    self._format_val(e.created_at),
                )
                for e in entries
            ]
            con.executemany("INSERT INTO accounting_entries VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)

        # 9. Evangelismo Sesiones & Asistencias
        sesiones = _safe_query(models.SesionGrupo)
        if sesiones:
            con.execute("DELETE FROM sesiones_grupo;")
            rows = [
                (
                    self._format_val(sg.id),
                    self._format_val(sg.grupo_id),
                    self._format_val(sg.fecha_sesion),
                    str(sg.estado_sesion) if sg.estado_sesion else "REALIZADA",
                    self._format_val(sg.created_at),
                )
                for sg in sesiones
            ]
            con.executemany("INSERT INTO sesiones_grupo VALUES (?, ?, ?, ?, ?)", rows)

        asistencias = _safe_query(models.Asistencia)
        if asistencias:
            con.execute("DELETE FROM asistencias;")
            rows = [
                (
                    self._format_val(a.id),
                    self._format_val(a.sesion_id),
                    self._format_val(a.persona_id),
                    str(a.estado_asistencia) if a.estado_asistencia else "ASISTIO",
                    self._format_val(a.created_at),
                )
                for a in asistencias
            ]
            con.executemany("INSERT INTO asistencias VALUES (?, ?, ?, ?, ?)", rows)

    def _try_attach_postgres(self, con: duckdb.DuckDBPyConnection) -> bool:
        """Attempt to attach PostgreSQL database using DuckDB postgres_scanner."""
        db_url = settings.database_url
        if not (db_url.startswith("postgresql") or db_url.startswith("postgres://")):
            return False

        try:
            con.execute("INSTALL postgres;")
            con.execute("LOAD postgres;")
            conn_str = db_url.replace("postgresql+psycopg2://", "postgresql://").replace("postgresql+asyncpg://", "postgresql://")
            con.execute(f"ATTACH '{conn_str}' AS pg (TYPE POSTGRES, READ_ONLY);")

            tables = [
                "sedes",
                "personas",
                "crm_events",
                "event_attendances",
                "donations",
                "expense_reports",
                "expense_items",
                "financial_statements",
                "accounting_entries",
                "sesiones_grupo",
                "asistencias",
            ]
            for tbl in tables:
                con.execute(f"CREATE OR REPLACE VIEW {tbl} AS SELECT * FROM pg.{tbl};")
            logger.info("Successfully attached PostgreSQL via DuckDB postgres_scanner")
            return True
        except Exception as exc:
            logger.warning("postgres_scanner attach failed (%s), falling back to in-memory ingestion", exc)
            return False

    def _try_attach_sqlite(self, con: duckdb.DuckDBPyConnection) -> bool:
        """Attempt to attach SQLite database file using DuckDB sqlite scanner."""
        db_url = settings.database_url
        if not db_url.startswith("sqlite"):
            return False

        match = re.search(r"sqlite:///(.+)", db_url)
        if not match:
            return False

        db_path = match.group(1)
        if db_path == ":memory:" or not os.path.exists(db_path):
            return False

        try:
            con.execute("INSTALL sqlite;")
            con.execute("LOAD sqlite;")
            con.execute(f"ATTACH '{db_path}' AS sqldb (TYPE SQLITE, READ_ONLY);")
            tables = [
                "sedes",
                "personas",
                "crm_events",
                "event_attendances",
                "donations",
                "expense_reports",
                "expense_items",
                "financial_statements",
                "accounting_entries",
                "sesiones_grupo",
                "asistencias",
            ]
            for tbl in tables:
                con.execute(f"CREATE OR REPLACE VIEW {tbl} AS SELECT * FROM sqldb.{tbl};")
            logger.info("Successfully attached SQLite file via DuckDB sqlite scanner: %s", db_path)
            return True
        except Exception as exc:
            logger.warning("sqlite scanner attach failed (%s), falling back to in-memory ingestion", exc)
            return False

    def get_connection(self, db_session: Optional[Session] = None) -> duckdb.DuckDBPyConnection:
        """Build and return an isolated in-memory DuckDB connection loaded with analytics data."""
        self._ensure_duckdb()
        con = duckdb.connect(":memory:")

        # If a live SQLAlchemy session is provided, prioritize syncing the session data
        # so transactional fixtures, mock data, and recent inserts are directly queryable.
        if db_session is not None:
            self._sync_from_session(con, db_session)
            return con

        # Otherwise, attempt postgres or sqlite attachment
        attached_pg = self._try_attach_postgres(con)
        if attached_pg:
            return con

        attached_sqlite = self._try_attach_sqlite(con)
        if attached_sqlite:
            return con

        self._init_empty_tables(con)
        return con

    # ─────────────────────────────────────────────────────────────────────────────
    # ANALYTICAL QUERY 1: Church Growth Metrics Across Sedes Over Time
    # ─────────────────────────────────────────────────────────────────────────────
    def get_church_growth_metrics(
        self,
        sede_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        group_by: str = "month",
        db_session: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """Calculates church growth metrics across sedes over time with sub-50ms latency."""
        con = self.get_connection(db_session)
        t0 = time.perf_counter()
        try:
            group_by_lower = (group_by or "month").lower()
            if group_by_lower == "day":
                period_expr = "strftime(TRY_CAST(created_at AS TIMESTAMP), '%Y-%m-%d')"
            elif group_by_lower == "week":
                period_expr = "strftime(TRY_CAST(created_at AS TIMESTAMP), '%Y-W%W')"
            elif group_by_lower == "quarter":
                period_expr = "strftime(TRY_CAST(created_at AS TIMESTAMP), '%Y') || '-Q' || ((extract(month from TRY_CAST(created_at AS TIMESTAMP)) - 1) // 3 + 1)"
            elif group_by_lower == "year":
                period_expr = "strftime(TRY_CAST(created_at AS TIMESTAMP), '%Y')"
            else:  # default 'month'
                period_expr = "strftime(TRY_CAST(created_at AS TIMESTAMP), '%Y-%m')"

            where_clauses = ["created_at IS NOT NULL"]
            params: List[Any] = []

            if sede_id:
                where_clauses.append("sede_id = ?")
                params.append(str(sede_id))
            if start_date:
                where_clauses.append("TRY_CAST(created_at AS DATE) >= ?")
                params.append(str(start_date))
            if end_date:
                where_clauses.append("TRY_CAST(created_at AS DATE) <= ?")
                params.append(str(end_date))

            where_sql = " AND ".join(where_clauses)

            # Overall summary KPIs
            summary_query = f"""
            SELECT
                COUNT(*) as total_members,
                COUNT(CASE WHEN estado_vital = 'ACTIVO' THEN 1 END) as active_members,
                COUNT(CASE WHEN is_baptized = true OR is_baptized = 1 THEN 1 END) as baptized_members,
                COUNT(CASE WHEN church_role IN ('Lider', 'LIDER', 'Servidor', 'SERVIDOR', 'Pastor', 'PASTOR') THEN 1 END) as leadership_count,
                ROUND((COUNT(CASE WHEN estado_vital = 'ACTIVO' THEN 1 END)::DOUBLE / NULLIF(COUNT(*), 0)) * 100.0, 2) as retention_rate_pct
            FROM personas
            WHERE {where_sql};
            """
            summary_row = con.execute(summary_query, params).fetchone()
            total_members = summary_row[0] if summary_row else 0
            active_members = summary_row[1] if summary_row else 0
            baptized_members = summary_row[2] if summary_row else 0
            leadership_count = summary_row[3] if summary_row else 0
            retention_rate_pct = float(summary_row[4] or 0.0) if summary_row else 0.0

            # Time series trends
            trend_query = f"""
            WITH period_counts AS (
                SELECT
                    {period_expr} as period,
                    COUNT(*) as new_members,
                    COUNT(CASE WHEN estado_vital = 'ACTIVO' THEN 1 END) as active_new,
                    COUNT(CASE WHEN is_baptized = true OR is_baptized = 1 THEN 1 END) as baptized_new
                FROM personas
                WHERE {where_sql}
                GROUP BY 1
                ORDER BY 1 ASC
            ),
            cumul AS (
                SELECT
                    period,
                    new_members,
                    active_new,
                    baptized_new,
                    SUM(new_members) OVER (ORDER BY period ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) as cumulative_members,
                    LAG(new_members, 1) OVER (ORDER BY period) as prev_new
                FROM period_counts
            )
            SELECT
                period,
                new_members,
                cumulative_members,
                ROUND(CASE
                    WHEN prev_new IS NULL OR prev_new = 0 THEN 0.0
                    ELSE ((new_members - prev_new)::DOUBLE / prev_new) * 100.0
                END, 2) as growth_rate_pct,
                active_new,
                baptized_new
            FROM cumul;
            """
            trend_rows = con.execute(trend_query, params).fetchall()
            trends = [
                {
                    "period": r[0],
                    "new_members": r[1],
                    "cumulative_members": r[2],
                    "growth_rate_pct": float(r[3] or 0.0),
                    "active_new": r[4],
                    "baptized_new": r[5],
                }
                for r in trend_rows
                if r[0] is not None
            ]

            overall_growth_rate_pct = 0.0
            new_members_period = sum(t["new_members"] for t in trends)
            baseline = total_members - new_members_period
            if baseline > 0:
                overall_growth_rate_pct = round((new_members_period / baseline) * 100.0, 2)
            elif total_members > 0:
                overall_growth_rate_pct = 100.0

            # Breakdown by sede
            sede_params: List[Any] = []
            sede_where = ["p.created_at IS NOT NULL"]
            if start_date:
                sede_where.append("TRY_CAST(p.created_at AS DATE) >= ?")
                sede_params.append(str(start_date))
            if end_date:
                sede_where.append("TRY_CAST(p.created_at AS DATE) <= ?")
                sede_params.append(str(end_date))
            if sede_id:
                sede_where.append("p.sede_id = ?")
                sede_params.append(str(sede_id))

            sede_sql = " AND ".join(sede_where)

            sede_query = f"""
            SELECT
                p.sede_id,
                coalesce(s.nombre, 'Sin Sede Asignada') as sede_name,
                coalesce(s.ciudad, 'No especificada') as ciudad,
                COUNT(p.id) as total_members,
                COUNT(CASE WHEN p.estado_vital = 'ACTIVO' THEN 1 END) as active_members,
                COUNT(CASE WHEN p.is_baptized = true OR p.is_baptized = 1 THEN 1 END) as baptized_members,
                ROUND((COUNT(CASE WHEN p.estado_vital = 'ACTIVO' THEN 1 END)::DOUBLE / NULLIF(COUNT(p.id), 0)) * 100.0, 2) as active_pct
            FROM personas p
            LEFT JOIN sedes s ON p.sede_id = s.id
            WHERE {sede_sql}
            GROUP BY 1, 2, 3
            ORDER BY total_members DESC;
            """
            sede_rows = con.execute(sede_query, sede_params).fetchall()
            by_sede = [
                {
                    "sede_id": r[0],
                    "sede_name": r[1],
                    "ciudad": r[2],
                    "total_members": r[3],
                    "active_members": r[4],
                    "baptized_members": r[5],
                    "active_pct": float(r[6] or 0.0),
                }
                for r in sede_rows
            ]

            elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

            return {
                "source": "duckdb/in-memory-olap",
                "execution_time_ms": elapsed_ms,
                "filters": {
                    "sede_id": sede_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "group_by": group_by_lower,
                },
                "summary": {
                    "total_members": total_members,
                    "active_members": active_members,
                    "baptized_members": baptized_members,
                    "leadership_count": leadership_count,
                    "new_members_period": new_members_period,
                    "retention_rate_pct": retention_rate_pct,
                    "overall_growth_rate_pct": overall_growth_rate_pct,
                },
                "trends": trends,
                "by_sede": by_sede,
            }
        finally:
            con.close()

    # ─────────────────────────────────────────────────────────────────────────────
    # ANALYTICAL QUERY 2: Attendance Trends Across Services & Age Groups
    # ─────────────────────────────────────────────────────────────────────────────
    def get_attendance_trends(
        self,
        sede_id: Optional[str] = None,
        event_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        group_by: str = "month",
        db_session: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """Calculates attendance trends across services and age demographics in sub-50ms."""
        con = self.get_connection(db_session)
        t0 = time.perf_counter()
        try:
            group_by_lower = (group_by or "month").lower()
            if group_by_lower == "day":
                period_expr = "strftime(TRY_CAST(coalesce(a.session_date, TRY_CAST(e.event_date AS DATE)) AS DATE), '%Y-%m-%d')"
            elif group_by_lower == "week":
                period_expr = "strftime(TRY_CAST(coalesce(a.session_date, TRY_CAST(e.event_date AS DATE)) AS DATE), '%Y-W%W')"
            elif group_by_lower == "year":
                period_expr = "strftime(TRY_CAST(coalesce(a.session_date, TRY_CAST(e.event_date AS DATE)) AS DATE), '%Y')"
            else:  # default 'month'
                period_expr = "strftime(TRY_CAST(coalesce(a.session_date, TRY_CAST(e.event_date AS DATE)) AS DATE), '%Y-%m')"

            where_clauses = ["1=1"]
            params: List[Any] = []

            if sede_id:
                where_clauses.append("e.sede_id = ?")
                params.append(str(sede_id))
            if event_type:
                where_clauses.append("e.event_type = ?")
                params.append(str(event_type))
            if start_date:
                where_clauses.append("TRY_CAST(coalesce(a.session_date, TRY_CAST(e.event_date AS DATE)) AS DATE) >= ?")
                params.append(str(start_date))
            if end_date:
                where_clauses.append("TRY_CAST(coalesce(a.session_date, TRY_CAST(e.event_date AS DATE)) AS DATE) <= ?")
                params.append(str(end_date))

            where_sql = " AND ".join(where_clauses)

            # Summary KPIs
            summary_query = f"""
            WITH base AS (
                SELECT
                    a.id as attendance_id,
                    a.persona_id,
                    e.id as event_id,
                    e.name as event_name,
                    e.event_type
                FROM crm_events e
                LEFT JOIN event_attendances a ON e.id = a.event_id
                WHERE {where_sql}
            ),
            event_agg AS (
                SELECT
                    event_id,
                    event_name,
                    COUNT(attendance_id) as att_count
                FROM base
                GROUP BY 1, 2
            )
            SELECT
                (SELECT COUNT(attendance_id) FROM base WHERE attendance_id IS NOT NULL) as total_attendances,
                (SELECT COUNT(DISTINCT persona_id) FROM base WHERE persona_id IS NOT NULL) as unique_attendees,
                (SELECT COUNT(DISTINCT event_id) FROM base) as total_services,
                (SELECT COALESCE(MAX(att_count), 0) FROM event_agg) as peak_attendance,
                (SELECT event_name FROM event_agg ORDER BY att_count DESC LIMIT 1) as peak_event_name
            """
            summary_row = con.execute(summary_query, params).fetchone()
            total_attendances = summary_row[0] if summary_row else 0
            unique_attendees = summary_row[1] if summary_row else 0
            total_services = summary_row[2] if summary_row else 0
            peak_attendance = summary_row[3] if summary_row else 0
            peak_event_name = summary_row[4] if summary_row and summary_row[4] else "N/A"
            avg_attendance = round(total_attendances / total_services, 2) if total_services > 0 else 0.0

            # Age group distribution
            age_query = f"""
            WITH attendee_ages AS (
                SELECT
                    a.id as attendance_id,
                    p.id as persona_id,
                    p.birthday,
                    CASE
                        WHEN p.birthday IS NULL THEN 'Desconocido'
                        WHEN date_diff('year', TRY_CAST(p.birthday AS DATE), CURRENT_DATE) < 13 THEN '0-12 (Niños)'
                        WHEN date_diff('year', TRY_CAST(p.birthday AS DATE), CURRENT_DATE) < 18 THEN '13-17 (Adolescentes)'
                        WHEN date_diff('year', TRY_CAST(p.birthday AS DATE), CURRENT_DATE) < 36 THEN '18-35 (Jóvenes)'
                        WHEN date_diff('year', TRY_CAST(p.birthday AS DATE), CURRENT_DATE) < 60 THEN '36-59 (Adultos)'
                        ELSE '60+ (Adultos Mayores)'
                    END as age_group
                FROM crm_events e
                JOIN event_attendances a ON e.id = a.event_id
                LEFT JOIN personas p ON a.persona_id = p.id
                WHERE {where_sql}
            )
            SELECT
                age_group,
                COUNT(*) as count,
                ROUND((COUNT(*)::DOUBLE / NULLIF((SELECT COUNT(*) FROM attendee_ages), 0)) * 100.0, 2) as percentage
            FROM attendee_ages
            GROUP BY 1
            ORDER BY count DESC;
            """
            age_rows = con.execute(age_query, params).fetchall()
            by_age_group = [
                {"age_group": r[0], "count": r[1], "percentage": float(r[2] or 0.0)}
                for r in age_rows
            ]

            # Service type breakdown
            service_query = f"""
            SELECT
                coalesce(e.event_type, 'DOMINICAL') as event_type,
                COUNT(DISTINCT e.id) as service_count,
                COUNT(a.id) as total_attendance,
                ROUND(COUNT(a.id)::DOUBLE / NULLIF(COUNT(DISTINCT e.id), 0), 2) as avg_per_service
            FROM crm_events e
            LEFT JOIN event_attendances a ON e.id = a.event_id
            WHERE {where_sql}
            GROUP BY 1
            ORDER BY total_attendance DESC;
            """
            service_rows = con.execute(service_query, params).fetchall()
            by_service_type = [
                {
                    "event_type": r[0],
                    "service_count": r[1],
                    "total_attendance": r[2],
                    "avg_per_service": float(r[3] or 0.0),
                }
                for r in service_rows
            ]

            # Trends over time
            trend_query = f"""
            SELECT
                {period_expr} as period,
                COUNT(a.id) as total_attendance,
                COUNT(DISTINCT a.persona_id) as unique_attendees,
                COUNT(DISTINCT e.id) as services_held,
                ROUND(COUNT(a.id)::DOUBLE / NULLIF(COUNT(DISTINCT e.id), 0), 2) as avg_per_service
            FROM crm_events e
            LEFT JOIN event_attendances a ON e.id = a.event_id
            WHERE {where_sql} AND coalesce(a.session_date, TRY_CAST(e.event_date AS DATE)) IS NOT NULL
            GROUP BY 1
            ORDER BY 1 ASC;
            """
            trend_rows = con.execute(trend_query, params).fetchall()
            trends = [
                {
                    "period": r[0],
                    "total_attendance": r[1],
                    "unique_attendees": r[2],
                    "services_held": r[3],
                    "avg_per_service": float(r[4] or 0.0),
                }
                for r in trend_rows
                if r[0] is not None
            ]

            elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

            return {
                "source": "duckdb/in-memory-olap",
                "execution_time_ms": elapsed_ms,
                "filters": {
                    "sede_id": sede_id,
                    "event_type": event_type,
                    "start_date": start_date,
                    "end_date": end_date,
                    "group_by": group_by_lower,
                },
                "summary": {
                    "total_attendances": total_attendances,
                    "unique_attendees": unique_attendees,
                    "total_services": total_services,
                    "avg_attendance_per_service": avg_attendance,
                    "peak_attendance": peak_attendance,
                    "peak_event_name": peak_event_name,
                },
                "by_age_group": by_age_group,
                "by_service_type": by_service_type,
                "trends": trends,
            }
        finally:
            con.close()

    # ─────────────────────────────────────────────────────────────────────────────
    # ANALYTICAL QUERY 3: Multi-Year Financial Statements & KPI Aggregations
    # ─────────────────────────────────────────────────────────────────────────────
    def get_financial_summary(
        self,
        sede_id: Optional[str] = None,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
        group_by: str = "year",
        db_session: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """Calculates multi-year financial statements, cash flow, and KPI aggregations in sub-50ms."""
        con = self.get_connection(db_session)
        t0 = time.perf_counter()
        try:
            inc_where = ["(status IS NULL OR status = 'completed')"]
            exp_where = ["(r.status IS NULL OR r.status IN ('approved', 'reimbursed', 'submitted', 'draft'))"]
            inc_params: List[Any] = []
            exp_params: List[Any] = []

            if sede_id:
                inc_where.append("sede_id = ?")
                inc_params.append(str(sede_id))
                exp_where.append("r.sede_id = ?")
                exp_params.append(str(sede_id))

            if start_year:
                inc_where.append("extract(year from coalesce(TRY_CAST(donation_date AS DATE), TRY_CAST(created_at AS DATE))) >= ?")
                inc_params.append(int(start_year))
                exp_where.append("extract(year from coalesce(TRY_CAST(e.expense_date AS DATE), TRY_CAST(e.created_at AS DATE))) >= ?")
                exp_params.append(int(start_year))

            if end_year:
                inc_where.append("extract(year from coalesce(TRY_CAST(donation_date AS DATE), TRY_CAST(created_at AS DATE))) <= ?")
                inc_params.append(int(end_year))
                exp_where.append("extract(year from coalesce(TRY_CAST(e.expense_date AS DATE), TRY_CAST(e.created_at AS DATE))) <= ?")
                exp_params.append(int(end_year))

            inc_sql = " AND ".join(inc_where)
            exp_sql = " AND ".join(exp_where)

            # 1. Multi-Year Trends & KPIs query
            multi_year_query = f"""
            WITH inc AS (
                SELECT
                    extract(year from coalesce(TRY_CAST(donation_date AS DATE), TRY_CAST(created_at AS DATE))) as year,
                    SUM(coalesce(amount, 0.0)) as income,
                    COUNT(*) as donation_count,
                    AVG(coalesce(amount, 0.0)) as avg_donation
                FROM donations
                WHERE {inc_sql}
                GROUP BY 1
            ),
            exp AS (
                SELECT
                    extract(year from coalesce(TRY_CAST(e.expense_date AS DATE), TRY_CAST(e.created_at AS DATE))) as year,
                    SUM(coalesce(e.amount, 0.0)) as expense
                FROM expense_items e
                LEFT JOIN expense_reports r ON e.expense_report_id = r.id
                WHERE {exp_sql}
                GROUP BY 1
            ),
            all_years AS (
                SELECT year FROM inc WHERE year IS NOT NULL
                UNION
                SELECT year FROM exp WHERE year IS NOT NULL
            ),
            combined AS (
                SELECT
                    CAST(y.year AS INTEGER) as year,
                    coalesce(i.income, 0.0) as total_income,
                    coalesce(e.expense, 0.0) as total_expenses,
                    coalesce(i.income, 0.0) - coalesce(e.expense, 0.0) as net_balance,
                    coalesce(i.donation_count, 0) as donation_count,
                    coalesce(i.avg_donation, 0.0) as avg_donation
                FROM all_years y
                LEFT JOIN inc i ON y.year = i.year
                LEFT JOIN exp e ON y.year = e.year
                ORDER BY y.year ASC
            )
            SELECT
                year,
                ROUND(total_income, 2),
                ROUND(total_expenses, 2),
                ROUND(net_balance, 2),
                ROUND(CASE WHEN total_income > 0 THEN (net_balance / total_income) * 100.0 ELSE 0.0 END, 2) as operating_margin_pct,
                ROUND(CASE
                    WHEN LAG(total_income) OVER (ORDER BY year) > 0 THEN
                        ((total_income - LAG(total_income) OVER (ORDER BY year)) / LAG(total_income) OVER (ORDER BY year)) * 100.0
                    ELSE 0.0
                END, 2) as yoy_growth_pct,
                donation_count,
                ROUND(avg_donation, 2)
            FROM combined;
            """
            year_rows = con.execute(multi_year_query, inc_params + exp_params).fetchall()

            multi_year_trend = [
                {
                    "year": int(r[0]),
                    "total_income": float(r[1] or 0.0),
                    "total_expenses": float(r[2] or 0.0),
                    "net_balance": float(r[3] or 0.0),
                    "operating_margin_pct": float(r[4] or 0.0),
                    "yoy_growth_pct": float(r[5] or 0.0),
                    "donation_count": int(r[6] or 0),
                    "avg_donation": float(r[7] or 0.0),
                }
                for r in year_rows
                if r[0] is not None
            ]

            total_income = round(sum(y["total_income"] for y in multi_year_trend), 2)
            total_expenses = round(sum(y["total_expenses"] for y in multi_year_trend), 2)
            net_balance = round(total_income - total_expenses, 2)
            operating_margin_pct = (
                round((net_balance / total_income) * 100.0, 2) if total_income > 0 else 0.0
            )
            total_donations_count = sum(y["donation_count"] for y in multi_year_trend)
            avg_donation_amount = (
                round(total_income / total_donations_count, 2) if total_donations_count > 0 else 0.0
            )
            latest_yoy_growth_pct = multi_year_trend[-1]["yoy_growth_pct"] if multi_year_trend else 0.0

            # 2. Income breakdown by donation category using CTE
            income_cat_query = f"""
            WITH filtered_income AS (
                SELECT coalesce(donation_type, 'Diezmo') as donation_type, amount
                FROM donations
                WHERE {inc_sql}
            ),
            total_inc AS (
                SELECT SUM(coalesce(amount, 0.0)) as total FROM filtered_income
            )
            SELECT
                donation_type,
                ROUND(SUM(coalesce(amount, 0.0)), 2) as amount,
                ROUND((SUM(coalesce(amount, 0.0)) / NULLIF((SELECT total FROM total_inc), 0)) * 100.0, 2) as percentage
            FROM filtered_income
            GROUP BY 1
            ORDER BY amount DESC;
            """
            income_cat_rows = con.execute(income_cat_query, inc_params).fetchall()
            income_by_category = [
                {
                    "donation_type": r[0],
                    "amount": float(r[1] or 0.0),
                    "percentage": float(r[2] or 0.0),
                }
                for r in income_cat_rows
            ]

            # 3. Expense breakdown by category using CTE
            expense_cat_query = f"""
            WITH filtered_expenses AS (
                SELECT e.category, e.amount
                FROM expense_items e
                LEFT JOIN expense_reports r ON e.expense_report_id = r.id
                WHERE {exp_sql}
            ),
            total_exp AS (
                SELECT SUM(coalesce(amount, 0.0)) as total FROM filtered_expenses
            )
            SELECT
                coalesce(category, 'Operations') as category,
                ROUND(SUM(coalesce(amount, 0.0)), 2) as amount,
                ROUND((SUM(coalesce(amount, 0.0)) / NULLIF((SELECT total FROM total_exp), 0)) * 100.0, 2) as percentage
            FROM filtered_expenses
            GROUP BY 1
            ORDER BY amount DESC;
            """
            expense_cat_rows = con.execute(expense_cat_query, exp_params).fetchall()
            expenses_by_category = [
                {
                    "category": r[0],
                    "amount": float(r[1] or 0.0),
                    "percentage": float(r[2] or 0.0),
                }
                for r in expense_cat_rows
            ]

            # 4. Financial summary by sede
            sede_fin_query = f"""
            WITH sede_inc AS (
                SELECT
                    sede_id,
                    SUM(coalesce(amount, 0.0)) as inc
                FROM donations
                WHERE {inc_sql}
                GROUP BY 1
            ),
            sede_exp AS (
                SELECT
                    r.sede_id,
                    SUM(coalesce(e.amount, 0.0)) as exp
                FROM expense_items e
                LEFT JOIN expense_reports r ON e.expense_report_id = r.id
                WHERE {exp_sql}
                GROUP BY 1
            ),
            all_sedes AS (
                SELECT sede_id FROM sede_inc WHERE sede_id IS NOT NULL
                UNION
                SELECT sede_id FROM sede_exp WHERE sede_id IS NOT NULL
            )
            SELECT
                s_id.sede_id,
                coalesce(s.nombre, 'Sin Sede Asignada') as sede_name,
                ROUND(coalesce(si.inc, 0.0), 2) as total_income,
                ROUND(coalesce(se.exp, 0.0), 2) as total_expenses,
                ROUND(coalesce(si.inc, 0.0) - coalesce(se.exp, 0.0), 2) as net_balance,
                ROUND(CASE WHEN coalesce(si.inc, 0.0) > 0 THEN ((coalesce(si.inc, 0.0) - coalesce(se.exp, 0.0)) / si.inc) * 100.0 ELSE 0.0 END, 2) as operating_margin_pct
            FROM all_sedes s_id
            LEFT JOIN sedes s ON s_id.sede_id = s.id
            LEFT JOIN sede_inc si ON s_id.sede_id = si.sede_id
            LEFT JOIN sede_exp se ON s_id.sede_id = se.sede_id
            ORDER BY total_income DESC;
            """
            sede_fin_rows = con.execute(sede_fin_query, inc_params + exp_params).fetchall()
            by_sede = [
                {
                    "sede_id": r[0],
                    "sede_name": r[1],
                    "total_income": float(r[2] or 0.0),
                    "total_expenses": float(r[3] or 0.0),
                    "net_balance": float(r[4] or 0.0),
                    "operating_margin_pct": float(r[5] or 0.0),
                }
                for r in sede_fin_rows
            ]

            elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

            return {
                "source": "duckdb/in-memory-olap",
                "execution_time_ms": elapsed_ms,
                "filters": {
                    "sede_id": sede_id,
                    "start_year": start_year,
                    "end_year": end_year,
                    "group_by": (group_by or "year").lower(),
                },
                "kpis": {
                    "total_income": total_income,
                    "total_expenses": total_expenses,
                    "net_balance": net_balance,
                    "operating_margin_pct": operating_margin_pct,
                    "total_donations_count": total_donations_count,
                    "avg_donation_amount": avg_donation_amount,
                    "latest_yoy_growth_pct": latest_yoy_growth_pct,
                },
                "multi_year_trend": multi_year_trend,
                "income_by_category": income_by_category,
                "expenses_by_category": expenses_by_category,
                "by_sede": by_sede,
            }
        finally:
            con.close()


duckdb_analytics_service = DuckDBAnalyticsService()
