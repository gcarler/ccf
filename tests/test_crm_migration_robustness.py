import os
import uuid
import pytest
import subprocess
from pathlib import Path
from sqlalchemy import create_engine, text
from alembic.config import Config
from alembic import command

ROOT = Path(__file__).resolve().parents[1]

def _run_alembic(*args: str, database_url: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["ENVIRONMENT"] = "test"
    env["DATABASE_URL"] = database_url
    
    # Ensure we use the venv's alembic binary if available
    alembic_bin = str(ROOT / "venv" / "bin" / "alembic")
    if not os.path.exists(alembic_bin):
        alembic_bin = "alembic"
        
    return subprocess.run(
        [alembic_bin, *args],
        cwd=str(ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

def test_sqlite_baseline_migration_failure(tmp_path):
    """
    Verify that running the baseline upgrade from scratch on SQLite fails.
    This demonstrates the design flaw where 20260702_0001_canonical_baseline runs 
    Base.metadata.create_all which creates everything, making subsequent steps fail.
    """
    db_url = f"sqlite:///{tmp_path / 'baseline_test.db'}"
    res = _run_alembic("upgrade", "head", database_url=db_url)
    assert res.returncode != 0
    # The migration should fail because Base.metadata.create_all pre-creates tables.
    assert "already exists" in res.stderr or "already exists" in res.stdout

def test_postgresql_baseline_migration_failure():
    """
    Verify that running the baseline upgrade from scratch on PostgreSQL also fails.
    It can fail due to "type citext does not exist" (lack of CITEXT extension) or
    "already exists" if the schema was not completely fresh.
    """
    pg_url = "postgresql://ccf_admin:ccf_password_secret_123@localhost:5432/ccf_db?options=-csearch_path=baseline_fail_schema"
    
    # Recreate the schema clean
    engine = create_engine("postgresql://ccf_admin:ccf_password_secret_123@localhost:5432/ccf_db")
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS baseline_fail_schema CASCADE"))
        conn.execute(text("CREATE SCHEMA baseline_fail_schema"))
        conn.commit()

    res = _run_alembic("upgrade", "head", database_url=pg_url)
    assert res.returncode != 0
    err_msg = res.stderr or res.stdout
    assert "already exists" in err_msg or "type \"citext\" does not exist" in err_msg, (
        f"Expected table already exists or citext error, got: {err_msg}"
    )

def test_crm_automation_graph_migration_logic_sqlite(tmp_path):
    """
    Simulate the pre-migration state on SQLite and test the upgrade/downgrade logic 
    for 20260710_0002_crm_automation_graph.
    We expect the downgrade to fail on SQLite because of the unnamed foreign key constraint.
    """
    db_url = f"sqlite:///{tmp_path / 'graph_test.db'}"
    engine = create_engine(db_url)
    
    # 1. Setup pre-migration schema for 20260710_0002
    with engine.connect() as conn:
        conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) PRIMARY KEY)"))
        conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('20260710_0001')"))
        
        conn.execute(text("CREATE TABLE crm_casos (id VARCHAR(36) PRIMARY KEY, nombre VARCHAR(100))"))
        conn.execute(text(
            "CREATE TABLE crm_automations ("
            "id VARCHAR(36) PRIMARY KEY, "
            "name VARCHAR(100), "
            "trigger_event VARCHAR(50), "
            "action_type VARCHAR(50), "
            "is_active BOOLEAN, "
            "next_automation_id VARCHAR(36) REFERENCES crm_automations(id)"
            ")"
        ))
        
        # Insert in topological order (C, B, A) to satisfy any foreign keys if they are enabled later
        conn.execute(text("INSERT INTO crm_automations (id, name, trigger_event, action_type, is_active, next_automation_id) VALUES ('C', 'Auto C', 'event', 'action', 1, NULL)"))
        conn.execute(text("INSERT INTO crm_automations (id, name, trigger_event, action_type, is_active, next_automation_id) VALUES ('B', 'Auto B', 'event', 'action', 1, 'C')"))
        conn.execute(text("INSERT INTO crm_automations (id, name, trigger_event, action_type, is_active, next_automation_id) VALUES ('A', 'Auto A', 'event', 'action', 1, 'B')"))
        conn.commit()

    # 2. Upgrade to head (runs 20260710_0002)
    res = _run_alembic("upgrade", "head", database_url=db_url)
    assert res.returncode == 0, res.stderr

    # 3. Verify upgraded structure and data migration
    with engine.connect() as conn:
        edges = conn.execute(text("SELECT source_id, target_id FROM crm_automation_edges")).all()
        assert len(edges) == 2
        assert ('A', 'B') in edges
        assert ('B', 'C') in edges
        
        # next_automation_id column must be dropped
        try:
            conn.execute(text("SELECT next_automation_id FROM crm_automations"))
            col_exists = True
        except Exception:
            col_exists = False
        assert not col_exists, "next_automation_id was not dropped from crm_automations"
        
        # Add a branching relationship in upgraded state: A -> D
        conn.execute(text("INSERT INTO crm_automations (id, name, trigger_event, action_type, is_active) VALUES ('D', 'Auto D', 'event', 'action', 1)"))
        conn.execute(text(f"INSERT INTO crm_automation_edges (id, source_id, target_id) VALUES ('{uuid.uuid4()}', 'A', 'D')"))
        conn.commit()

    # 4. Downgrade to 20260710_0001 (restores next_automation_id)
    # We expect this to fail on SQLite because of the unnamed foreign key constraint in batch_alter_table.
    res = _run_alembic("downgrade", "20260710_0001", database_url=db_url)
    assert res.returncode != 0
    assert "Constraint must have a name" in res.stderr

def test_crm_automation_graph_migration_logic_postgresql():
    """
    Verify the upgrade/downgrade logic on PostgreSQL, including the lossy downgrade behavior.
    """
    pg_url = "postgresql://ccf_admin:ccf_password_secret_123@localhost:5432/ccf_db?options=-csearch_path=graph_migration_test"
    engine = create_engine("postgresql://ccf_admin:ccf_password_secret_123@localhost:5432/ccf_db")
    
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS graph_migration_test CASCADE"))
        conn.execute(text("CREATE SCHEMA graph_migration_test"))
        conn.commit()
        
    with engine.connect() as conn:
        conn.execute(text("SET search_path TO graph_migration_test"))
        conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) PRIMARY KEY)"))
        conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('20260710_0001')"))
        
        conn.execute(text("CREATE TABLE crm_casos (id UUID PRIMARY KEY, nombre VARCHAR(100))"))
        conn.execute(text(
            "CREATE TABLE crm_automations ("
            "id UUID PRIMARY KEY, "
            "name VARCHAR(100), "
            "trigger_event VARCHAR(50), "
            "action_type VARCHAR(50), "
            "is_active BOOLEAN, "
            "next_automation_id UUID REFERENCES crm_automations(id)"
            ")"
        ))
        
        # Insert in topological order (C, B, A) to satisfy FK constraints
        a_id, b_id, c_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        conn.execute(
            text("INSERT INTO crm_automations (id, name, trigger_event, action_type, is_active, next_automation_id) VALUES (:id, 'Auto C', 'event', 'action', true, NULL)"),
            {"id": c_id}
        )
        conn.execute(
            text("INSERT INTO crm_automations (id, name, trigger_event, action_type, is_active, next_automation_id) VALUES (:id, 'Auto B', 'event', 'action', true, :next)"),
            {"id": b_id, "next": c_id}
        )
        conn.execute(
            text("INSERT INTO crm_automations (id, name, trigger_event, action_type, is_active, next_automation_id) VALUES (:id, 'Auto A', 'event', 'action', true, :next)"),
            {"id": a_id, "next": b_id}
        )
        conn.commit()

    # Upgrade to head
    res = _run_alembic("upgrade", "head", database_url=pg_url)
    assert res.returncode == 0, res.stderr

    # Verify upgrade
    with engine.connect() as conn:
        conn.execute(text("SET search_path TO graph_migration_test"))
        edges = conn.execute(text("SELECT source_id, target_id FROM crm_automation_edges")).all()
        assert len(edges) == 2
        assert (a_id, b_id) in edges
        assert (b_id, c_id) in edges

        # Add branching relationship: A -> D
        d_id = uuid.uuid4()
        conn.execute(
            text("INSERT INTO crm_automations (id, name, trigger_event, action_type, is_active) VALUES (:id, 'Auto D', 'event', 'action', true)"),
            {"id": d_id}
        )
        conn.execute(
            text("INSERT INTO crm_automation_edges (id, source_id, target_id) VALUES (:id, :source, :target)"),
            {"id": uuid.uuid4(), "source": a_id, "target": d_id}
        )
        conn.commit()

    # Downgrade on PostgreSQL (this succeeds unlike SQLite since PG supports transactional DDL changes)
    res = _run_alembic("downgrade", "20260710_0001", database_url=pg_url)
    assert res.returncode == 0, res.stderr

    # Verify downgrade is lossy (A is restricted back to a single target_id)
    with engine.connect() as conn:
        conn.execute(text("SET search_path TO graph_migration_test"))
        res_autos = conn.execute(
            text("SELECT id, next_automation_id FROM crm_automations WHERE id = :id"),
            {"id": a_id}
        ).fetchone()
        assert res_autos is not None
        assert res_autos[1] in (b_id, d_id)
