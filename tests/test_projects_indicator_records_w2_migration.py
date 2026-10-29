"""W2 — verificación de la migración de unicidad parcial de records.

Ejecuta la migración real
`20261028_0001_project_indicator_records_live_unique` en modo standalone
(Alembic Operations sobre una conexión SQLite de archivo temporario) para
probar:
- upgrade(): soft-delete dedupe (conserva la medición más reciente por
  `reported_at DESC, created_at DESC`; Axioma 2, sin hard delete) y creación
  del índice único parcial sobre filas vivas.
- Enforzamiento: duplicado vivo viola `IntegrityError`; tras soft delete el
  período vuelve a estar disponible.
- downgrade(): elimina el índice (historia marcada no se restaura, REGLAS §9).

La cadena completa `alembic upgrade head` desde cero falla de forma
preexistente en `a89b968a23b0_add_donation_date` (`duplicate column
donation_date`, ramificación histórica de heads) — hallazgo separado, ajeno a
esta migración; aquí se verifica la migración W2 de forma aislada.
"""

import datetime
import importlib.util
import uuid
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

from alembic import op as _alembic_op  # noqa: F401  (referencia del módulo migración)

REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = (
    REPO_ROOT / "alembic" / "canonical_versions" / "20261028_0001_project_indicator_records_live_unique.py"
)
INDEX_NAME = "uq_project_indicator_records_indicator_period_live"

_DDL = """
CREATE TABLE project_indicator_records (
    id VARCHAR(32) PRIMARY KEY,
    indicator_id VARCHAR(32) NOT NULL,
    period VARCHAR(50) NOT NULL,
    target_value FLOAT NOT NULL DEFAULT 0,
    actual_value FLOAT NOT NULL DEFAULT 0,
    spi FLOAT,
    notes TEXT,
    evidence_url VARCHAR(500),
    reported_by VARCHAR(32),
    reported_at VARCHAR(32) NOT NULL,
    created_at VARCHAR(32) NOT NULL,
    updated_at VARCHAR(32) NOT NULL,
    deleted_at VARCHAR(32)
)
"""


def _load_migration_module():
    spec = importlib.util.spec_from_file_location("w2_migration", str(MIGRATION_PATH))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _iso(dt: datetime.datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S.%f")


@pytest.fixture()
def standalone_records_db(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path}/w2_records.db")
    with engine.connect() as conn:
        conn.exec_driver_sql(_DDL)
        conn.commit()
    yield engine
    engine.dispose()


def _insert_row(conn, *, indicator_id, period, reported_at, actual=10.0, row_id=None):
    row_id = row_id or uuid.uuid4().hex
    now_iso = _iso(datetime.datetime.now())
    conn.exec_driver_sql(
        "INSERT INTO project_indicator_records "
        "(id, indicator_id, period, target_value, actual_value, reported_at, created_at, updated_at) "
        "VALUES (?, ?, ?, 100.0, ?, ?, ?, ?)",
        (row_id, indicator_id, period, actual, _iso(reported_at), now_iso, now_iso),
    )
    return row_id


def _index_exists(conn) -> bool:
    row = conn.exec_driver_sql(
        "SELECT sql FROM sqlite_master WHERE type='index' AND name=?", (INDEX_NAME,)
    ).fetchone()
    return row is not None and row[0] is not None


def _rows(conn, indicator_id, period):
    return conn.exec_driver_sql(
        "SELECT id, deleted_at FROM project_indicator_records "
        "WHERE indicator_id=? AND period=? ORDER BY reported_at DESC, created_at DESC, id DESC",
        (indicator_id, period),
    ).fetchall()


def test_w2_migracion_dedupe_soft_delete_y_indice_parcial(standalone_records_db):
    engine = standalone_records_db
    mod = _load_migration_module()
    base = datetime.datetime(2026, 10, 15, 12, 0, tzinfo=datetime.timezone.utc)

    with engine.connect() as conn:
        older_id = _insert_row(conn, indicator_id="IND-A", period="2026-10", reported_at=base)
        newest_id = _insert_row(
            conn, indicator_id="IND-A", period="2026-10", reported_at=base + datetime.timedelta(days=5)
        )
        other_id = _insert_row(
            conn, indicator_id="IND-A", period="2026-11", reported_at=base + datetime.timedelta(days=1)
        )
        # Duplicado ya soft-deleted antes de la migración: no participa.
        gone_id = _insert_row(
            conn, indicator_id="IND-A", period="2026-10", reported_at=base + datetime.timedelta(days=9)
        )
        conn.exec_driver_sql(
            "UPDATE project_indicator_records SET deleted_at=? WHERE id=?",
            (_iso(datetime.datetime.now()), gone_id),
        )
        conn.commit()

        ops = Operations(MigrationContext.configure(conn))
        mod.op = ops  # el módulo vincula `op` a las operaciones de esta conexión
        mod.upgrade()
        # Alembic CI ejecuta cada migración en su propia transacción; aquí el
        # commit explícito materializa dedupe + índice antes del enforcement.
        conn.commit()

        assert _index_exists(conn)
        filas = _rows(conn, "IND-A", "2026-10")
        ids = {rid for rid, _ in filas}
        assert ids == {older_id, newest_id, gone_id}  # sin hard deletes
        vivos = {rid for rid, deleted in filas if deleted is None}
        assert vivos == {newest_id}  # W2: la más reciente por reported_at sobrevive
        # El auto superado y el ya hist\u00f3rico quedan marcados (Axioma 2)
        marcados = {rid for rid, deleted in filas if deleted is not None}
        assert marcados == {older_id, gone_id}
        # Otra cuenta con período distinto queda viva (unicidad por período)
        vivos_otro = {rid for rid, deleted in _rows(conn, "IND-A", "2026-11") if deleted is None}
        assert vivos_otro == {other_id}

        # Enforzamiento: segundo vivo del mismo período viola el índice parcial
        with pytest.raises(sa.exc.IntegrityError):
            _insert_row(conn, indicator_id="IND-A", period="2026-10", reported_at=base)
            conn.commit()
        conn.rollback()

        # Soft delete del vivo: el período vuelve a estar disponible
        conn.exec_driver_sql(
            "UPDATE project_indicator_records SET deleted_at=? WHERE id=?",
            (_iso(datetime.datetime.now()), newest_id),
        )
        conn.commit()
        reusado = _insert_row(conn, indicator_id="IND-A", period="2026-10", reported_at=base)
        conn.commit()
        assert reusado

        # downgrade() elimina el índice (historia marcada no se restaura)
        mod.downgrade()
        assert not _index_exists(conn)
        # Sin el índice, un duplicado vivo vuelve a permitirse (reversibilidad)
        dup = _insert_row(conn, indicator_id="IND-A", period="2026-10", reported_at=base)
        conn.commit()
        assert dup
