"""Direct unit tests for `backend.crud.crm_.resources` (QC-18 módulo A).

QC-18 closure (errorescrm.md): 14/19 CRM CRUD modules had 0 *direct* unit
tests — covered only transitively via API integration tests. This file
closes the `resources.py` gap (18 public functions): categorías, plantillas
(+filtros canal/categoria/q/soft-delete), adjuntos, bitácora de envíos.

Posture mirrors `tests/test_crm_crud_personas.py`: SQLite in-memory via the
`db_session` fixture, direct row inserts, no HTTP layer. We exercise:
  * Soft-delete semantics (activo=False hides from list/get).
  * Sede-scope filter on `list_plantillas` / `list_envios_sede`
    (Axioma 3 — cross-tenant must not leak).
  * `_coerce_uuid_or_404` raises 404 on malformed UUID input (existence-leak
    safe contract).
  * Enum coercion `CanalEnvio` / `EstadoEnvioPlantilla` on write paths.
  * `count_envios` returns 0 on empty / plantilla inexistente (defensive).
"""
from __future__ import annotations

import uuid as _uuid
from typing import Optional

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend import models
from backend.crud import crm_ as crud_crm  # noqa: F401 — ensure registry
from backend.crud.crm_ import resources
from backend.models_crm import (
    BitacoraEnvioPlantilla,
    CanalEnvio,
    CategoriaRecurso,
    EstadoEnvioPlantilla,
    PlantillaMensaje,
    RecursoAdjunto,
)
from backend.schemas.crm.resources import (
    CategoriaRecursoCreate,
    CategoriaRecursoUpdate,
    PlantillaMensajeCreate,
    PlantillaMensajeUpdate,
)


# ─── Fixtures local ────────────────────────────────────────────────────────────

def _seed_sede(db: Session, name: str = "Sede QC-18.A") -> models.Sede:
    sede = models.Sede(id=_uuid.uuid4(), nombre=name, ciudad="QC18 City", es_activa=True)
    db.add(sede)
    db.flush()
    return sede


def _seed_categoria(db: Session, *, nombre: str = "Cat QC18", color: str = "#6B7280") -> CategoriaRecurso:
    cat = CategoriaRecurso(id=_uuid.uuid4(), nombre=nombre, color_ui_hex=color, activo=True)
    db.add(cat)
    db.flush()
    return cat


def _seed_plantilla(
    db: Session,
    *,
    sede_id: _uuid.UUID,
    categoria: CategoriaRecurso,
    titulo: str = "Plantilla QC18",
    canal: CanalEnvio = CanalEnvio.WHATSAPP,
    contenido: str = "Hola {{nombre}}",
    activo: bool = True,
) -> PlantillaMensaje:
    p = PlantillaMensaje(
        id=_uuid.uuid4(),
        sede_id=sede_id,
        categoria_id=categoria.id,
        titulo=titulo,
        canal=canal,
        contenido_texto=contenido,
        variables_requeridas=["nombre"],
        activo=activo,
    )
    db.add(p)
    db.flush()
    return p


def _seed_adjunto(
    db: Session,
    *,
    sede_id: _uuid.UUID,
    plantilla: Optional[PlantillaMensaje] = None,
    nombre: str = "adjunto.pdf",
    activo: bool = True,
) -> RecursoAdjunto:
    a = RecursoAdjunto(
        id=_uuid.uuid4(),
        sede_id=sede_id,
        plantilla_id=plantilla.id if plantilla else None,
        nombre_recurso=nombre,
        url_acceso="https://example.com/adjunto",
        nombre_archivo=nombre,
        tipo_mime="application/pdf",
        peso_bytes=1024,
        activo=activo,
    )
    db.add(a)
    db.flush()
    return a


def _seed_envio(
    db: Session,
    *,
    sede_id: _uuid.UUID,
    plantilla: Optional[PlantillaMensaje] = None,
    destinatario_id: Optional[_uuid.UUID] = None,
    estado: EstadoEnvioPlantilla = EstadoEnvioPlantilla.PROCESANDO,
    payload: Optional[dict] = None,
) -> BitacoraEnvioPlantilla:
    e = BitacoraEnvioPlantilla(
        id=_uuid.uuid4(),
        sede_id=sede_id,
        plantilla_id=plantilla.id if plantilla else None,
        destinatario_id=str(destinatario_id or _uuid.uuid4()),
        estado=estado,
        payload_hidratado=payload or {},
    )
    db.add(e)
    db.flush()
    return e


def _commit(db: Session) -> None:
    db.commit()


# ─── Categorías ───────────────────────────────────────────────────────────────


def test_list_categorias_only_returns_activos(db_session):
    """Soft-delete contract: `list_categorias` filters `activo=True`."""
    cat_activo = _seed_categoria(db_session, nombre="Activa")
    cat_inactivo = _seed_categoria(db_session, nombre="Inactiva")
    cat_inactivo.activo = False
    _commit(db_session)

    out = resources.list_categorias(db_session)
    ids = {c.id for c in out}
    assert cat_activo.id in ids
    assert cat_inactivo.id not in ids, "list_categorias leaked a soft-deleted category"


def test_list_categorias_ordered_by_nombre(db_session):
    """Sort contract: results come back ordered by `nombre` asc."""
    _seed_categoria(db_session, nombre="Zeta")
    _seed_categoria(db_session, nombre="Alfa")
    _seed_categoria(db_session, nombre="Beta")
    _commit(db_session)

    nombres = [c.nombre for c in resources.list_categorias(db_session)]
    assert nombres == sorted(nombres), f"list_categorias not sorted: {nombres}"


def test_get_categoria_returns_none_when_missing(db_session):
    """Missing-but-wellformed UUID → None (not 404)."""
    out = resources.get_categoria(db_session, str(_uuid.uuid4()))
    assert out is None


def test_get_categoria_raises_404_on_malformed_uuid(db_session):
    """`_coerce_uuid_or_404` existence-leak contract: malformed → 404, never 500."""
    with pytest.raises(HTTPException) as exc:
        resources.get_categoria(db_session, "not-a-uuid")
    assert exc.value.status_code == 404


def test_create_categoria_persists_fields(db_session):
    """`create_categoria` writes the schema fields verbatim."""
    payload = CategoriaRecursoCreate(
        nombre="Nueva Cat",
        descripcion="desc",
        color_ui_hex="#FF0000",
    )
    obj = resources.create_categoria(db_session, payload)
    assert obj.id is not None
    assert obj.nombre == "Nueva Cat"
    assert obj.descripcion == "desc"
    assert obj.color_ui_hex == "#FF0000"
    assert obj.activo is True


def test_update_categoria_updates_provided_fields_only(db_session):
    """`exclude_unset=True` contract: unmentioned fields unchanged."""
    cat = _seed_categoria(db_session, nombre="Original", color="#000000")
    _commit(db_session)

    out = resources.update_categoria(
        db_session, str(cat.id),
        CategoriaRecursoUpdate(nombre="Renombrado"),
    )
    assert out.nombre == "Renombrado"
    assert out.color_ui_hex == "#000000", "neighboring field was clobbered by exclude_unset"


def test_update_categoria_returns_none_for_missing(db_session):
    out = resources.update_categoria(db_session, str(_uuid.uuid4()), CategoriaRecursoUpdate(nombre="x"))
    assert out is None


def test_delete_categoria_soft_deletes_and_returns_true(db_session):
    """Soft-delete: `delete_categoria` flips `activo=False` (no hard delete)."""
    cat = _seed_categoria(db_session, nombre="ToDelete")
    _commit(db_session)

    ok = resources.delete_categoria(db_session, str(cat.id))
    assert ok is True
    db_session.expire_all()
    assert resources.get_categoria(db_session, str(cat.id)) is None, "delete_categoria did not soft-delete"
    # Row still present in the table (hard delete would have removed it)
    row = db_session.query(CategoriaRecurso).filter(CategoriaRecurso.id == cat.id).first()
    assert row is not None and row.activo is False


def test_delete_categoria_returns_false_for_missing(db_session):
    assert resources.delete_categoria(db_session, str(_uuid.uuid4())) is False


# ─── Plantillas ───────────────────────────────────────────────────────────────


def test_list_plantillas_scoped_by_sede(db_session):
    """Axioma 3: `list_plantillas` must NOT return plantillas of another sede."""
    sede_a = _seed_sede(db_session, name="A")
    sede_b = _seed_sede(db_session, name="B")
    cat = _seed_categoria(db_session)
    p_a = _seed_plantilla(db_session, sede_id=sede_a.id, categoria=cat, titulo="A-Tmpl")
    p_b = _seed_plantilla(db_session, sede_id=sede_b.id, categoria=cat, titulo="B-Tmpl")
    _commit(db_session)

    out_a = resources.list_plantillas(db_session, sede_id=str(sede_a.id))
    ids = {p.id for p in out_a}
    assert p_a.id in ids
    assert p_b.id not in ids, "list_plantillas leaked cross-tenant plantilla"


def test_list_plantillas_excludes_soft_deleted(db_session):
    sede = _seed_sede(db_session)
    cat = _seed_categoria(db_session)
    p_live = _seed_plantilla(db_session, sede_id=sede.id, categoria=cat, titulo="Live")
    p_dead = _seed_plantilla(db_session, sede_id=sede.id, categoria=cat, titulo="Dead", activo=False)
    _commit(db_session)

    ids = {p.id for p in resources.list_plantillas(db_session, sede_id=str(sede.id))}
    assert p_live.id in ids
    assert p_dead.id not in ids


def test_list_plantillas_filters_by_canal_and_categoria(db_session):
    sede = _seed_sede(db_session)
    cat1 = _seed_categoria(db_session, nombre="C1")
    cat2 = _seed_categoria(db_session, nombre="C2")
    p_wa = _seed_plantilla(db_session, sede_id=sede.id, categoria=cat1, canal=CanalEnvio.WHATSAPP, titulo="WA")
    p_em = _seed_plantilla(db_session, sede_id=sede.id, categoria=cat1, canal=CanalEnvio.EMAIL, titulo="EM")
    p_em2 = _seed_plantilla(db_session, sede_id=sede.id, categoria=cat2, canal=CanalEnvio.EMAIL, titulo="EM2")
    _commit(db_session)

    wa_only = resources.list_plantillas(db_session, sede_id=str(sede.id), canal="WHATSAPP")
    assert {p.id for p in wa_only} == {p_wa.id}

    em_cat2 = resources.list_plantillas(db_session, sede_id=str(sede.id), canal="EMAIL", categoria_id=str(cat2.id))
    assert {p.id for p in em_cat2} == {p_em2.id}


def test_list_plantillas_search_q_matches_titulo_or_contenido(db_session):
    sede = _seed_sede(db_session)
    cat = _seed_categoria(db_session)
    p_t = _seed_plantilla(db_session, sede_id=sede.id, categoria=cat, titulo="Bienvenida Especial", contenido="x")
    p_c = _seed_plantilla(db_session, sede_id=sede.id, categoria=cat, titulo="Otro", contenido="codigo SECRETO xyz")
    _commit(db_session)

    hit_t = resources.list_plantillas(db_session, sede_id=str(sede.id), q="Especial")
    hit_c = resources.list_plantillas(db_session, sede_id=str(sede.id), q="SECRETO")
    assert {p.id for p in hit_t} == {p_t.id}
    assert {p.id for p in hit_c} == {p_c.id}


def test_get_plantilla_returns_none_for_missing(db_session):
    assert resources.get_plantilla(db_session, str(_uuid.uuid4())) is None


def test_get_plantilla_raises_404_on_malformed_uuid(db_session):
    with pytest.raises(HTTPException) as exc:
        resources.get_plantilla(db_session, "garbage")
    assert exc.value.status_code == 404


def test_create_plantilla_coerces_canal_enum_and_persists(db_session):
    sede = _seed_sede(db_session)
    cat = _seed_categoria(db_session)
    _commit(db_session)

    payload = PlantillaMensajeCreate(
        categoria_id=cat.id,
        titulo="FromPayload",
        canal="EMAIL",
        contenido_texto="Body {{x}}",
        variables_requeridas=["x"],
    )
    obj = resources.create_plantilla(db_session, payload, sede_id=str(sede.id))
    assert obj.canal == CanalEnvio.EMAIL, "create_plantilla did not coerce canal to enum"
    assert obj.sede_id == sede.id
    assert obj.activo is True


def test_update_plantilla_returns_none_for_missing(db_session):
    out = resources.update_plantilla(db_session, str(_uuid.uuid4()), PlantillaMensajeUpdate(titulo="x"))
    assert out is None


def test_update_plantilla_coerces_canal_and_categoria_on_update(db_session):
    sede = _seed_sede(db_session)
    cat1 = _seed_categoria(db_session, nombre="C1")
    cat2 = _seed_categoria(db_session, nombre="C2")
    p = _seed_plantilla(db_session, sede_id=sede.id, categoria=cat1, canal=CanalEnvio.WHATSAPP)
    _commit(db_session)

    out = resources.update_plantilla(
        db_session, str(p.id),
        PlantillaMensajeUpdate(canal="SMS", categoria_id=cat2.id, contenido_texto="new body"),
    )
    assert out.canal == CanalEnvio.SMS
    assert out.categoria_id == cat2.id
    assert out.contenido_texto == "new body"


def test_delete_plantilla_soft_deletes_and_returns_true(db_session):
    sede = _seed_sede(db_session)
    cat = _seed_categoria(db_session)
    p = _seed_plantilla(db_session, sede_id=sede.id, categoria=cat)
    _commit(db_session)

    assert resources.delete_plantilla(db_session, str(p.id)) is True
    db_session.expire_all()
    assert resources.get_plantilla(db_session, str(p.id)) is None


def test_delete_plantilla_returns_false_for_missing(db_session):
    assert resources.delete_plantilla(db_session, str(_uuid.uuid4())) is False


def test_count_envios_zero_for_plantilla_with_no_envios(db_session):
    sede = _seed_sede(db_session)
    cat = _seed_categoria(db_session)
    p = _seed_plantilla(db_session, sede_id=sede.id, categoria=cat)
    _commit(db_session)

    assert resources.count_envios(db_session, str(p.id)) == 0


def test_count_envios_counts_only_for_that_plantilla(db_session):
    sede = _seed_sede(db_session)
    cat = _seed_categoria(db_session)
    p1 = _seed_plantilla(db_session, sede_id=sede.id, categoria=cat, titulo="P1")
    p2 = _seed_plantilla(db_session, sede_id=sede.id, categoria=cat, titulo="P2")
    _seed_envio(db_session, sede_id=sede.id, plantilla=p1)
    _seed_envio(db_session, sede_id=sede.id, plantilla=p1)
    _seed_envio(db_session, sede_id=sede.id, plantilla=p2)
    _commit(db_session)

    assert resources.count_envios(db_session, str(p1.id)) == 2
    assert resources.count_envios(db_session, str(p2.id)) == 1


def test_count_envios_raises_404_on_malformed_uuid(db_session):
    with pytest.raises(HTTPException) as exc:
        resources.count_envios(db_session, "bad")
    assert exc.value.status_code == 404


# ─── Adjuntos ─────────────────────────────────────────────────────────────────


def test_list_adjuntos_only_returns_actives_for_plantilla(db_session):
    sede = _seed_sede(db_session)
    cat = _seed_categoria(db_session)
    p = _seed_plantilla(db_session, sede_id=sede.id, categoria=cat)
    a_live = _seed_adjunto(db_session, sede_id=sede.id, plantilla=p, nombre="live.pdf")
    a_dead = _seed_adjunto(db_session, sede_id=sede.id, plantilla=p, nombre="dead.pdf", activo=False)
    a_orphan = _seed_adjunto(db_session, sede_id=sede.id, plantilla=None, nombre="orphan.pdf")
    _commit(db_session)

    ids = {a.id for a in resources.list_adjuntos(db_session, plantilla_id=str(p.id))}
    assert a_live.id in ids
    assert a_dead.id not in ids, "list_adjuntos leaked a soft-deleted adjunto"
    assert a_orphan.id not in ids, "list_adjuntos returned an adjunto belonging to no plantilla"


def test_create_adjunto_persists_with_optional_seaweed_fid(db_session):
    sede = _seed_sede(db_session)
    a = resources.create_adjunto(
        db_session,
        sede_id=str(sede.id),
        plantilla_id=None,
        nombre_recurso="r",
        url_acceso="https://x",
        nombre_archivo="r.pdf",
        tipo_mime="application/pdf",
        peso_bytes=10,
        seaweed_fid="fid-123",
    )
    assert a.id is not None
    assert a.seaweed_fid == "fid-123"
    assert a.activo is True


def test_delete_adjunto_soft_deletes_and_returns_true(db_session):
    sede = _seed_sede(db_session)
    a = _seed_adjunto(db_session, sede_id=sede.id)
    _commit(db_session)

    assert resources.delete_adjunto(db_session, str(a.id)) is True
    db_session.expire_all()
    # After soft-delete it's filtered out of list_adjuntos (any plantilla) —
    # but since it had no plantilla we just verify the flag flip directly.
    row = db_session.query(RecursoAdjunto).filter(RecursoAdjunto.id == a.id).first()
    assert row is not None and row.activo is False


def test_delete_adjunto_returns_false_for_missing(db_session):
    assert resources.delete_adjunto(db_session, str(_uuid.uuid4())) is False


def test_delete_adjunto_raises_404_on_malformed_uuid(db_session):
    with pytest.raises(HTTPException) as exc:
        resources.delete_adjunto(db_session, "not-uuid")
    assert exc.value.status_code == 404


# ─── Bitácora de envíos ───────────────────────────────────────────────────────


def test_create_envio_defaults_to_procesando(db_session):
    sede = _seed_sede(db_session)
    _commit(db_session)
    e = resources.create_envio(
        db_session,
        sede_id=str(sede.id),
        plantilla_id=None,
        caso_id=None,
        enviado_por_id=None,
        destinatario_id=str(_uuid.uuid4()),
        payload_hidratado={"k": "v"},
    )
    assert e.estado == EstadoEnvioPlantilla.PROCESANDO, "create_envio must default estado to PROCESANDO"


def test_update_estado_envio_coerces_enum_and_persists_log_error(db_session):
    sede = _seed_sede(db_session)
    e = _seed_envio(db_session, sede_id=sede.id)
    _commit(db_session)

    out = resources.update_estado_envio(db_session, str(e.id), "ENVIADO", log_error=None)
    assert out.estado == EstadoEnvioPlantilla.ENVIADO

    out2 = resources.update_estado_envio(db_session, str(e.id), "FALLIDO", log_error="smtp 5xx")
    assert out2.estado == EstadoEnvioPlantilla.FALLIDO
    assert out2.log_error == "smtp 5xx"


def test_update_estado_envio_returns_none_for_missing(db_session):
    assert resources.update_estado_envio(db_session, str(_uuid.uuid4()), "ENVIADO") is None


def test_update_estado_envio_raises_404_on_malformed_uuid(db_session):
    with pytest.raises(HTTPException) as exc:
        resources.update_estado_envio(db_session, "x", "ENVIADO")
    assert exc.value.status_code == 404


def test_list_envios_plantilla_filters_by_plantilla_and_orders_desc(db_session):
    """Order contract: bitácora ordered by `fecha_envio` desc."""
    sede = _seed_sede(db_session)
    cat = _seed_categoria(db_session)
    p = _seed_plantilla(db_session, sede_id=sede.id, categoria=cat)
    # Seed two envíos but ensure distinct timestamps so the DESC order is observable.
    import datetime as dt
    e1 = _seed_envio(db_session, sede_id=sede.id, plantilla=p)
    e1.fecha_envio = dt.datetime(2026, 7, 1, 10, 0, tzinfo=dt.timezone.utc)
    e2 = _seed_envio(db_session, sede_id=sede.id, plantilla=p)
    e2.fecha_envio = dt.datetime(2026, 7, 2, 10, 0, tzinfo=dt.timezone.utc)
    _commit(db_session)

    out = resources.list_envios_plantilla(db_session, plantilla_id=str(p.id))
    assert len(out) == 2
    assert out[0].fecha_envio >= out[1].fecha_envio, "list_envios_plantilla not ordered by fecha_envio desc"


def test_list_envios_sede_scoped_by_sede(db_session):
    """Axioma 3: `list_envios_sede` must NOT return envíos of another sede."""
    sede_a = _seed_sede(db_session, name="A")
    sede_b = _seed_sede(db_session, name="B")
    e_a = _seed_envio(db_session, sede_id=sede_a.id)
    e_b = _seed_envio(db_session, sede_id=sede_b.id)
    _commit(db_session)

    out_a = resources.list_envios_sede(db_session, sede_id=str(sede_a.id))
    ids = {e.id for e in out_a}
    assert e_a.id in ids
    assert e_b.id not in ids, "list_envios_sede leaked cross-tenant envío"


def test_list_envios_sede_raises_404_on_malformed_uuid(db_session):
    with pytest.raises(HTTPException) as exc:
        resources.list_envios_sede(db_session, sede_id="bad")
    assert exc.value.status_code == 404
