"""Direct unit tests for `backend.crud.crm_.pipeline` (QC-18 módulo B).

QC-18 closure (errorescrm.md): `pipeline.py` had 0 direct tests — covered
only transitively via API integration tests. This file covers the 10
public functions: PipelineCRM + EtapaPipeline CRUD with `deleted_at`
soft-delete (timestamp-based, NOT the `activo` bool used elsewhere).

Posture mirrors `tests/test_crm_crud_personas.py`: SQLite in-memory via the
`db_session` fixture, direct row inserts, no HTTP layer. We exercise:
  * Soft-delete by `deleted_at` (list/get must filter `deleted_at IS NULL`).
  * `list_pipelines` sede-scope (Axioma 3 — cross-tenant must not leak).
  * `archive_*` sets `deleted_at` (no hard delete).
  * `update_*` sets `updated_at` via `_utcnow`.
  * `list_stages` filter by pipeline + order by `orden`.
"""
from __future__ import annotations

import uuid as _uuid

from sqlalchemy.orm import Session

from backend import models
from backend.crud.crm_ import pipeline as crud_pipeline
from backend.models_crm_pipeline import EtapaPipeline, PipelineCRM
from backend.models_shared import _utcnow

# ─── Fixtures local ────────────────────────────────────────────────────────────

def _seed_sede(db: Session, name: str = "Sede QC-18.B") -> models.Sede:
    sede = models.Sede(id=_uuid.uuid4(), nombre=name, ciudad="QC18 City", es_activa=True)
    db.add(sede)
    db.flush()
    return sede


def _seed_pipeline(
    db: Session,
    *,
    sede_id: _uuid.UUID,
    nombre: str = "Pipeline QC18",
    tipo: str = "CONSEJERIA",  # TipoPipelineEnum: NUEVOS_VISITANTES | CONSEJERIA | RETENCION | VOLUNTARIADO
    activo: bool = True,
    deleted_at=None,
) -> PipelineCRM:
    p = PipelineCRM(
        id=_uuid.uuid4(),
        sede_id=sede_id,
        nombre=nombre,
        tipo=tipo,
        activo=activo,
        deleted_at=deleted_at,
    )
    db.add(p)
    db.flush()
    return p


def _seed_stage(
    db: Session,
    *,
    pipeline: PipelineCRM,
    nombre: str = "Etapa",
    orden: int = 1,
    deleted_at=None,
) -> EtapaPipeline:
    s = EtapaPipeline(
        id=_uuid.uuid4(),
        pipeline_id=pipeline.id,
        nombre=nombre,
        orden=orden,
        requiere_accion=False,
        deleted_at=deleted_at,
    )
    db.add(s)
    db.flush()
    return s


def _commit(db: Session) -> None:
    db.commit()


# ─── Pipelines ─────────────────────────────────────────────────────────────────


def test_list_pipelines_scoped_by_sede(db_session):
    """Axioma 3: list_pipelines must NOT return pipelines from another sede."""
    sede_a = _seed_sede(db_session, name="A")
    sede_b = _seed_sede(db_session, name="B")
    p_a = _seed_pipeline(db_session, sede_id=sede_a.id, nombre="PA")
    p_b = _seed_pipeline(db_session, sede_id=sede_b.id, nombre="PB")
    _commit(db_session)

    out_a = crud_pipeline.list_pipelines(db_session, sede_id=sede_a.id)
    ids = {p.id for p in out_a}
    assert p_a.id in ids
    assert p_b.id not in ids, "list_pipelines leaked cross-tenant pipeline"


def test_list_pipelines_excludes_soft_deleted(db_session):
    """Soft-delete by deleted_at: list_pipelines filters `deleted_at IS NULL`."""
    sede = _seed_sede(db_session)
    p_live = _seed_pipeline(db_session, sede_id=sede.id, nombre="Live", tipo="CONSEJERIA")
    p_dead = _seed_pipeline(db_session, sede_id=sede.id, nombre="Dead", tipo="RETENCION", deleted_at=_utcnow())
    _commit(db_session)

    ids = {p.id for p in crud_pipeline.list_pipelines(db_session, sede_id=sede.id)}
    assert p_live.id in ids
    assert p_dead.id not in ids, "list_pipelines leaked a deleted_at-soft-deleted pipeline"


def test_list_pipelines_ordered_by_nombre(db_session):
    sede = _seed_sede(db_session)
    _seed_pipeline(db_session, sede_id=sede.id, nombre="Zeta", tipo="CONSEJERIA")
    _seed_pipeline(db_session, sede_id=sede.id, nombre="Alfa", tipo="RETENCION")
    _seed_pipeline(db_session, sede_id=sede.id, nombre="Beta", tipo="VOLUNTARIADO")
    _commit(db_session)

    nombres = [p.nombre for p in crud_pipeline.list_pipelines(db_session, sede_id=sede.id)]
    assert nombres == sorted(nombres), f"list_pipelines not sorted: {nombres}"


def test_get_pipeline_returns_none_for_missing(db_session):
    assert crud_pipeline.get_pipeline(db_session, _uuid.uuid4()) is None


def test_get_pipeline_excludes_soft_deleted(db_session):
    sede = _seed_sede(db_session)
    p = _seed_pipeline(db_session, sede_id=sede.id, deleted_at=_utcnow())
    _commit(db_session)

    assert crud_pipeline.get_pipeline(db_session, p.id) is None, "get_pipeline returned a deleted_at-soft-deleted row"


def test_create_pipeline_persists_fields(db_session):
    sede = _seed_sede(db_session)
    _commit(db_session)
    row = crud_pipeline.create_pipeline(
        db_session,
        {"id": _uuid.uuid4(), "sede_id": sede.id, "nombre": "Nuevo", "tipo": "CONSEJERIA", "activo": True},
    )
    assert row.id is not None
    assert row.nombre == "Nuevo"
    assert row.deleted_at is None


def test_update_pipeline_sets_updated_at(db_session):
    """`update_pipeline` injects `updated_at = _utcnow()` regardless of input.

    SQLite stores timezone-aware `DateTime(timezone=True)` columns as NAIVE
    (CCF MEMORY invariant). On read-back the comparison against the
    tz-aware `_utcnow()` value raises TypeError — apply the platform's
    `_as_aware_utc` defense pattern before comparing.
    """
    import datetime as dt

    def _as_aware_utc(value):
        if value is None:
            return None
        return value if value.tzinfo is not None else value.replace(tzinfo=dt.timezone.utc)

    sede = _seed_sede(db_session)
    p = _seed_pipeline(db_session, sede_id=sede.id, nombre="Orig")
    original_updated = _as_aware_utc(p.updated_at)
    _commit(db_session)

    out = crud_pipeline.update_pipeline(db_session, p, {"nombre": "Renombrado"})
    assert out.nombre == "Renombrado"
    new_updated = _as_aware_utc(out.updated_at)
    assert new_updated is not None
    # updated_at was either None-original (now set) or advanced — both acceptable.
    if original_updated is not None:
        assert new_updated >= original_updated


def test_archive_pipeline_sets_deleted_at(db_session):
    """archive_pipeline is the soft-delete primitive — must set deleted_at, not row-DELETE."""
    sede = _seed_sede(db_session)
    p = _seed_pipeline(db_session, sede_id=sede.id)
    assert p.deleted_at is None
    _commit(db_session)

    crud_pipeline.archive_pipeline(db_session, p)
    db_session.expire_all()
    # Row still in the table (hard delete would have removed it)
    row = db_session.query(PipelineCRM).filter(PipelineCRM.id == p.id).first()
    assert row is not None and row.deleted_at is not None, "archive_pipeline did not soft-delete (deleted_at still None)"
    # And now invisible to list/get
    assert crud_pipeline.get_pipeline(db_session, p.id) is None


# ─── Etapas ────────────────────────────────────────────────────────────────────


def test_list_stages_filtered_by_pipeline_and_ordered_by_orden(db_session):
    sede = _seed_sede(db_session)
    p = _seed_pipeline(db_session, sede_id=sede.id, tipo="CONSEJERIA")
    p_other = _seed_pipeline(db_session, sede_id=sede.id, nombre="Other", tipo="RETENCION")
    s1 = _seed_stage(db_session, pipeline=p, nombre="S1", orden=2)
    s2 = _seed_stage(db_session, pipeline=p, nombre="S2", orden=1)
    s_other = _seed_stage(db_session, pipeline=p_other, nombre="SO", orden=1)
    _commit(db_session)

    out = crud_pipeline.list_stages(db_session, pipeline_id=p.id)
    ids = [s.id for s in out]
    assert s_other.id not in ids, "list_stages returned a stage from a different pipeline"
    # ordered by orden asc → S2 (orden=1) before S1 (orden=2)
    assert out[0].id == s2.id
    assert out[1].id == s1.id


def test_list_stages_excludes_soft_deleted(db_session):
    sede = _seed_sede(db_session)
    p = _seed_pipeline(db_session, sede_id=sede.id)
    s_live = _seed_stage(db_session, pipeline=p, nombre="Live", orden=1)
    s_dead = _seed_stage(db_session, pipeline=p, nombre="Dead", orden=2, deleted_at=_utcnow())
    _commit(db_session)

    ids = {s.id for s in crud_pipeline.list_stages(db_session, pipeline_id=p.id)}
    assert s_live.id in ids
    assert s_dead.id not in ids


def test_get_stage_returns_none_for_missing(db_session):
    assert crud_pipeline.get_stage(db_session, _uuid.uuid4()) is None


def test_get_stage_excludes_soft_deleted(db_session):
    sede = _seed_sede(db_session)
    p = _seed_pipeline(db_session, sede_id=sede.id)
    s = _seed_stage(db_session, pipeline=p, deleted_at=_utcnow())
    _commit(db_session)
    assert crud_pipeline.get_stage(db_session, s.id) is None


def test_create_stage_persists_fields(db_session):
    sede = _seed_sede(db_session)
    p = _seed_pipeline(db_session, sede_id=sede.id)
    _commit(db_session)

    row = crud_pipeline.create_stage(
        db_session,
        {"id": _uuid.uuid4(), "pipeline_id": p.id, "nombre": "E", "orden": 1, "requiere_accion": True, "visual_color": "#000"},
    )
    assert row.nombre == "E"
    assert row.orden == 1
    assert row.requiere_accion is True
    assert row.deleted_at is None


def test_update_stage_sets_attributes(db_session):
    sede = _seed_sede(db_session)
    p = _seed_pipeline(db_session, sede_id=sede.id)
    s = _seed_stage(db_session, pipeline=p, nombre="Orig", orden=1)
    _commit(db_session)

    out = crud_pipeline.update_stage(db_session, s, {"nombre": "Renom", "orden": 5})
    assert out.nombre == "Renom"
    assert out.orden == 5


def test_archive_stage_sets_deleted_at(db_session):
    sede = _seed_sede(db_session)
    p = _seed_pipeline(db_session, sede_id=sede.id)
    s = _seed_stage(db_session, pipeline=p)
    _commit(db_session)

    crud_pipeline.archive_stage(db_session, s)
    db_session.expire_all()
    row = db_session.query(EtapaPipeline).filter(EtapaPipeline.id == s.id).first()
    assert row is not None and row.deleted_at is not None
    assert crud_pipeline.get_stage(db_session, s.id) is None
