"""Tests for CrmReorderLock TTL cleanup and concurrency behavior."""

from datetime import datetime, timezone

from backend import models
from backend.models_crm_pipeline import (
    CanalOrigenEnum,
    CasoCRM,
    CrmReorderLock,
    EstadoCasoEnum,
    EtapaPipeline,
    PipelineCRM,
    TipoPipelineEnum,
)
from tests.conftest import auth_headers, seed_admin


def _setup_pipeline_and_case(db_session, sede, persona):
    pipeline = PipelineCRM(
        sede_id=sede.id,
        nombre="Lock Test Pipeline",
        tipo=TipoPipelineEnum.NUEVOS_VISITANTES,
    )
    db_session.add(pipeline)
    db_session.flush()
    stage = EtapaPipeline(
        pipeline_id=pipeline.id,
        nombre="New",
        orden=1,
    )
    db_session.add(stage)
    db_session.flush()
    case = CasoCRM(
        persona_id=persona.id,
        sede_id=sede.id,
        pipeline_id=pipeline.id,
        etapa_actual_id=stage.id,
        titulo_caso="Lock Test Case",
        origen_canal=CanalOrigenEnum.WEB_FORM,
        estado=EstadoCasoEnum.ABIERTO,
    )
    db_session.add(case)
    db_session.commit()
    return pipeline, stage, case


def test_cleanup_expired_removes_old_locks(db_session):
    # Need a real stage_id for the row to be meaningful.
    sede = models.Sede(nombre="Lock Sede", ciudad="Bogota", es_activa=True)
    db_session.add(sede)
    db_session.flush()
    pipeline = PipelineCRM(
        sede_id=sede.id,
        nombre="P",
        tipo=TipoPipelineEnum.NUEVOS_VISITANTES,
    )
    db_session.add(pipeline)
    db_session.flush()
    stage = EtapaPipeline(pipeline_id=pipeline.id, nombre="S", orden=1)
    db_session.add(stage)
    db_session.flush()
    old = CrmReorderLock(
        stage_id=stage.id,
        locked_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
    )
    db_session.add(old)
    db_session.commit()
    old_id = old.id

    CrmReorderLock.cleanup_expired(db_session, ttl_seconds=10)
    assert db_session.query(CrmReorderLock).filter(CrmReorderLock.id == old_id).first() is None


def test_cleanup_expired_keeps_recent_locks(db_session):
    sede = models.Sede(nombre="Lock Sede 2", ciudad="Bogota", es_activa=True)
    db_session.add(sede)
    db_session.flush()
    pipeline = PipelineCRM(sede_id=sede.id, nombre="P2", tipo=TipoPipelineEnum.NUEVOS_VISITANTES)
    db_session.add(pipeline)
    db_session.flush()
    stage = EtapaPipeline(pipeline_id=pipeline.id, nombre="S2", orden=1)
    db_session.add(stage)
    db_session.flush()
    recent = CrmReorderLock(stage_id=stage.id)
    db_session.add(recent)
    db_session.commit()
    recent_id = recent.id

    CrmReorderLock.cleanup_expired(db_session, ttl_seconds=10)
    assert db_session.query(CrmReorderLock).filter(CrmReorderLock.id == recent_id).first() is not None


def test_concurrent_drag_drop_blocks_while_lock_held(client, db_session):
    admin, persona, sede = seed_admin(db_session, email="lock_admin@example.com", password="testpass123")
    pipeline, stage, case = _setup_pipeline_and_case(db_session, sede, persona)

    # Simulate a first concurrent reorderer holding the lock.
    lock = CrmReorderLock(stage_id=stage.id)
    db_session.add(lock)
    db_session.commit()

    headers = auth_headers(client, email="lock_admin@example.com")
    target_stage = stage  # same stage for simplicity
    resp = client.post(
        "/api/crm/pipeline/kanban/drag-drop/concurrent",
        headers=headers,
        json={"caso_id": str(case.id), "target_stage_id": str(target_stage.id)},
    )
    assert resp.status_code == 409, f"Expected 409 due to active lock, got {resp.status_code}: {resp.text}"

    # After cleanup (lock is old enough), the request should succeed.
    lock.locked_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
    db_session.commit()
    resp2 = client.post(
        "/api/crm/pipeline/kanban/drag-drop/concurrent",
        headers=headers,
        json={"caso_id": str(case.id), "target_stage_id": str(target_stage.id)},
    )
    assert resp2.status_code == 200, f"Expected 200 after lock cleanup, got {resp2.status_code}: {resp2.text}"
