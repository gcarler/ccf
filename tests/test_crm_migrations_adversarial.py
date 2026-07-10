import os
import subprocess
import uuid
from pathlib import Path
import pytest
from sqlalchemy import text
from backend.models import Sede
from backend.models_crm_pipeline import PipelineCRM, EtapaPipeline, TipoPipelineEnum

ROOT = Path(__file__).resolve().parents[1]

def _run_alembic(*args: str, database_url: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["ENVIRONMENT"] = "test"
    env["DATABASE_URL"] = database_url
    return subprocess.run(
        ["alembic", *args],
        cwd=str(ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

def test_migration_baseline_failure_and_sqlite_incompatibility(tmp_path):
    """
    Empirically verify that Alembic migration fails when executing on a clean database.
    This captures two bugs:
    1. 20260702_0001_canonical_baseline runs Base.metadata.create_all, creating all tables dynamically,
       which makes subsequent migrations fail since their tables already exist.
    2. 20260710_0001_add_deleted_at_to_project_tables runs raw SQL 'ALTER TABLE ADD COLUMN IF NOT EXISTS'
       which SQLite does not support.
    """
    db_url = f"sqlite:///{tmp_path / 'temp_migration_test.db'}"
    
    # Executing migrations
    res = _run_alembic("upgrade", "head", database_url=db_url)
    
    # We expect it to FAIL (returncode != 0) with a specific table already exists error
    assert res.returncode != 0
    assert "table cms_categories already exists" in res.stderr or "table cms_categories already exists" in res.stdout

def test_sqlite_foreign_keys_not_enforced(db_session):
    """
    Empirically verify that SQLite foreign keys are NOT enforced in the current test configuration,
    permitting insertion of orphaned child records.
    """
    if db_session.bind.dialect.name == "sqlite":
        # Attempt to insert an EtapaPipeline referencing a non-existent pipeline_id
        invalid_pipeline_id = uuid.uuid4()
        etapa = EtapaPipeline(
            id=uuid.uuid4(),
            pipeline_id=invalid_pipeline_id,
            nombre="Invalid Pipeline FK Test Stage",
            orden=1
        )
        
        db_session.add(etapa)
        try:
            db_session.commit()
            fk_enforced = False
        except Exception:
            db_session.rollback()
            fk_enforced = True
            
        assert not fk_enforced, (
            "Foreign keys are enforced in SQLite, which violates our observation that "
            "no PRAGMA foreign_keys = ON is set in database.py or conftest.py."
        )

def test_unique_constraint_pipeline_sede_tipo(db_session):
    """
    Verify unique constraint on PipelineCRM (sede_id, tipo) is enforced.
    """
    # Seed a Sede
    sede_id = uuid.uuid4()
    sede = Sede(id=sede_id, nombre="Adversarial Sede", ciudad="Bogota")
    db_session.add(sede)
    db_session.commit()
    
    pipe1 = PipelineCRM(id=uuid.uuid4(), sede_id=sede.id, nombre="Pipeline 1", tipo=TipoPipelineEnum.CONSEJERIA)
    pipe2 = PipelineCRM(id=uuid.uuid4(), sede_id=sede.id, nombre="Pipeline 2", tipo=TipoPipelineEnum.CONSEJERIA)
    
    db_session.add(pipe1)
    db_session.commit()
    
    db_session.add(pipe2)
    with pytest.raises(Exception) as excinfo:
        db_session.commit()
    
    db_session.rollback()
    assert "UNIQUE constraint failed" in str(excinfo.value) or "duplicate key" in str(excinfo.value)

def test_unique_constraint_etapa_pipeline_orden(db_session):
    """
    Verify unique constraint on EtapaPipeline (pipeline_id, orden) is enforced.
    """
    sede_id = uuid.uuid4()
    sede = Sede(id=sede_id, nombre="Adversarial Sede 2", ciudad="Bogota")
    db_session.add(sede)
    db_session.commit()
    
    pipe = PipelineCRM(id=uuid.uuid4(), sede_id=sede.id, nombre="Pipeline X", tipo=TipoPipelineEnum.CONSEJERIA)
    db_session.add(pipe)
    db_session.commit()
    
    etapa1 = EtapaPipeline(id=uuid.uuid4(), pipeline_id=pipe.id, nombre="Stage 1", orden=5)
    etapa2 = EtapaPipeline(id=uuid.uuid4(), pipeline_id=pipe.id, nombre="Stage 2", orden=5)
    
    db_session.add(etapa1)
    db_session.commit()
    
    db_session.add(etapa2)
    with pytest.raises(Exception) as excinfo:
        db_session.commit()
        
    db_session.rollback()
    assert "UNIQUE constraint failed" in str(excinfo.value) or "duplicate key" in str(excinfo.value)

def test_database_limits_varchar(db_session):
    """
    Verify SQLite does not enforce VARCHAR length limits whereas PostgreSQL does.
    """
    sede_id = uuid.uuid4()
    sede = Sede(id=sede_id, nombre="Adversarial Sede 3", ciudad="Bogota")
    db_session.add(sede)
    db_session.commit()
    
    long_name = "A" * 500  # exceeds VARCHAR(100)
    pipe = PipelineCRM(id=uuid.uuid4(), sede_id=sede.id, nombre=long_name, tipo=TipoPipelineEnum.CONSEJERIA)
    db_session.add(pipe)
    
    if db_session.bind.dialect.name == "sqlite":
        db_session.commit()
        # Succeeds on SQLite because it does not enforce length constraints
        assert len(pipe.nombre) == 500
    else:
        # Fails on PostgreSQL
        with pytest.raises(Exception):
            db_session.commit()
        db_session.rollback()
