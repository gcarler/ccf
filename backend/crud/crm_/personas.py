"""Persona CRUD and search helpers."""
import datetime as dt
from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, selectinload

from backend import models, schemas
from backend.crud._utils import _to_uuid, _utcnow
from backend.crud.crm_.shared import _audit_log


def create_persona(db: Session, payload: schemas.PersonaCreate) -> models.Persona:
    # Axioma 1 — Validación de Identidad Previa: buscar persona existente
    # por teléfono o documento antes de crear un duplicado.
    existing = _find_existing_persona(db, payload)
    if existing:
        # Si existe, devolver el registro existente (no crear duplicado)
        return existing

    import uuid as _uuid

    data = payload.model_dump(exclude_unset=True)
    data.setdefault("qr_token", _uuid.uuid4().hex[:16].upper())
    row = models.Persona(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    _audit_log(
        db,
        "personas",
        str(row.id),
        "CREATE",
        detalles={
            "first_name": row.first_name,
            "last_name": row.last_name,
            "phone": row.phone,
            "church_role": row.church_role,
        },
    )

    # Inter-módulos: notificar registro de nuevo miembro/persona
    try:
        from backend.services.event_consumers import dispatch_event
        dispatch_event("persona_registered", {
            "persona_id": str(row.id),
            "name": f"{row.first_name} {row.last_name or ''}".strip(),
            "church_role": str(row.church_role) if row.church_role else "Visitante",
            "email": row.email,
        })
    except Exception:
        pass

    return row


def _find_existing_persona(db: Session, payload: schemas.PersonaCreate) -> Optional[models.Persona]:
    """Busca una persona existente por teléfono o número de documento.

    Axioma 1 — Person-Centric Kernel: anexar al UUID existente, no duplicar.
    """
    phones = [p for p in (payload.phone, payload.mobile_phone) if p]
    if phones:
        match = (
            db.query(models.Persona)
            .filter(
                or_(
                    models.Persona.phone.in_(phones),
                    models.Persona.mobile_phone.in_(phones),
                )
            )
            .first()
        )
        if match:
            return match

    if payload.id_number:
        match = db.query(models.Persona).filter(models.Persona.id_number == payload.id_number).first()
        if match:
            return match

    return None


def search_personas(
    db: Session,
    search: str | None = None,
    role: str | None = None,
    estado_vital: str | None = None,
    spiritual_status: str | None = None,
    sex: str | None = None,
    group_name: str | None = None,
    participation_type: str | None = None,
    id_type: str | None = None,
    min_age: int | None = None,
    max_age: int | None = None,
    family_id: UUID | None = None,
    sede_id: str | None = None,
    skip: int = 0,
    limit: int = 1000,
    sort_by: str | None = None,
    sort_dir: str = "asc",
):
    query = db.query(models.Persona).options(
        selectinload(models.Persona.family),
        selectinload(models.Persona.positions),
    )
    # Axioma 3 — Multi-Tenant: filtrar por sede obligatoriamente
    if sede_id is not None:
        query = query.filter(models.Persona.sede_id == sede_id)
    if search:
        like = f"%{search}%"
        # NOTA: nombre_completo es @hybrid_property con expresión SQL, funciona en filter
        query = query.filter(
            or_(
                models.Persona.first_name.ilike(like),
                models.Persona.last_name.ilike(like),
                models.Persona.nombre_completo.ilike(like),
                models.Persona.email.ilike(like),
                models.Persona.id_number.ilike(like),
                models.Persona.phone.ilike(like),
                models.Persona.mobile_phone.ilike(like),
            )
        )
    if role:
        query = query.filter(models.Persona.church_role == role)
    if estado_vital:
        query = query.filter(models.Persona.estado_vital == estado_vital)
    if spiritual_status:
        query = query.filter(models.Persona.spiritual_status == spiritual_status)
    if sex:
        query = query.filter(models.Persona.sex == sex)
    if id_type:
        query = query.filter(models.Persona.id_type == id_type)
    if group_name:
        query = query.filter(models.Persona.group_name == group_name)
    if participation_type:
        query = query.filter(models.Persona.participation_type == participation_type)
    if min_age is not None:
        cutoff = dt.date.today() - dt.timedelta(days=min_age * 365)
        query = query.filter(models.Persona.birthday <= cutoff)
    if max_age is not None:
        cutoff = dt.date.today() - dt.timedelta(days=max_age * 365 + 1)
        query = query.filter(models.Persona.birthday >= cutoff)
    if family_id:
        query = query.filter(models.Persona.family_id == family_id)

    sort_col = getattr(models.Persona, sort_by or "nombre_completo", models.Persona.nombre_completo)
    query = query.order_by(sort_col.desc() if sort_dir == "desc" else sort_col.asc())

    personas = query.offset(skip).limit(limit).all()
    return _enrich_personas_with_progress(db, personas)


def get_persona(db: Session, persona_id: str) -> Optional[models.Persona]:
    return db.query(models.Persona).filter(models.Persona.id == _to_uuid(persona_id)).first()


def update_persona(db: Session, persona_id: str, payload: schemas.PersonaUpdate) -> Optional[models.Persona]:
    row = db.query(models.Persona).filter(models.Persona.id == _to_uuid(persona_id)).first()
    if not row:
        return None

    # Capturar valores anteriores para el trigger de embudo
    old_church_role = row.church_role
    old_estado_vital = row.estado_vital
    old_baptism_date = row.baptism_date

    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(row, key, value)

    # Axioma 1 — Integridad de Embudo: registrar cambios en historial_embudo
    _track_funnel_changes(db, row, old_church_role, old_estado_vital, old_baptism_date)

    db.commit()
    db.refresh(row)
    _audit_log(
        db,
        "personas",
        str(row.id),
        "UPDATE",
        detalles={"church_role": row.church_role, "estado_vital": row.estado_vital},
    )

    # Inter-módulos: disparar eventos cuando cambia estado espiritual o rol
    try:
        from backend.services.event_consumers import dispatch_event
        if old_church_role != row.church_role:
            dispatch_event("persona_status_changed", {
                "persona_id": str(row.id),
                "from_role": str(old_church_role) if old_church_role else None,
                "to_role": str(row.church_role) if row.church_role else None,
            })
        if old_estado_vital != row.estado_vital:
            dispatch_event("spiritual_stage_transition", {
                "persona_id": str(row.id),
                "from_stage": old_estado_vital,
                "to_stage": row.estado_vital,
                "agent_id": str(row.id),
            })
    except Exception:
        pass  # eventos son best-effort, nunca bloquean la transacción

    return row


def _track_funnel_changes(db: Session, persona, old_church_role, old_estado_vital, old_baptism_date):
    """Registra cambios de rol, estado vital o fecha de bautismo."""
    from backend.models_evangelism import HistorialEmbudo

    now = _utcnow()
    pid = persona.id if hasattr(persona, "id") else persona.id

    # church_role
    if old_church_role and old_church_role != persona.church_role:
        days = _compute_days_in_state(db, pid, old_church_role)
        db.add(
            HistorialEmbudo(
                persona_id=pid,
                rol_anterior=str(old_church_role),
                rol_nuevo=str(persona.church_role),
                fecha_cambio=now,
                dias_en_estado_anterior=days,
            )
        )

    # estado_vital
    if old_estado_vital and old_estado_vital != persona.estado_vital:
        days = _compute_days_in_state(db, pid, old_estado_vital)
        db.add(
            HistorialEmbudo(
                persona_id=pid,
                rol_anterior=str(old_estado_vital),
                rol_nuevo=str(persona.estado_vital),
                fecha_cambio=now,
                dias_en_estado_anterior=days,
            )
        )

    # baptism_date (nuevo bautismo)
    if old_baptism_date is None and persona.baptism_date is not None:
        db.add(
            HistorialEmbudo(
                persona_id=pid,
                rol_anterior="NO_BAUTIZADO",
                rol_nuevo="BAUTIZADO",
                fecha_cambio=now,
                dias_en_estado_anterior=None,
            )
        )


def _compute_days_in_state(db: Session, persona_id, state_name: str) -> int | None:
    """Calcula cuántos días pasó la persona en el estado anterior."""
    from backend.models_evangelism import HistorialEmbudo

    last_entry = (
        db.query(HistorialEmbudo)
        .filter(HistorialEmbudo.persona_id == persona_id)
        .order_by(HistorialEmbudo.fecha_cambio.desc())
        .first()
    )
    if last_entry and last_entry.fecha_cambio:
        delta = _utcnow() - last_entry.fecha_cambio
        return delta.days
    return None


def delete_persona(db: Session, persona_id: str) -> bool:
    row = db.query(models.Persona).filter(models.Persona.id == _to_uuid(persona_id)).first()
    if not row:
        return False
    # Soft-delete: nunca eliminar físicamente una Persona.
    # Axioma 1 — Person-Centric Kernel: solo se cambia estado_vital a INACTIVO.
    row.estado_vital = "INACTIVO"
    row.unregistration_date = _utcnow().date()
    db.commit()
    _audit_log(
        db,
        "personas",
        str(row.id),
        "SOFT_DELETE",
        detalles={"estado_vital": "INACTIVO", "unregistration_date": str(row.unregistration_date)},
    )
    return True


def get_persona_donations(db: Session, persona_id: str):
    return (
        db.query(models.Donation)
        .filter(models.Donation.persona_id == persona_id)
        .order_by(models.Donation.created_at.desc())
        .all()
    )


_MEMBER_SORT_FIELDS = {
    "first_name": models.Persona.first_name,
    "last_name": models.Persona.last_name,
    "email": models.Persona.email,
    "church_role": models.Persona.church_role,
    "spiritual_status": models.Persona.spiritual_status,
    "created_at": models.Persona.created_at,
}


def _enrich_personas_with_progress(
    db: Session,
    personas: List[models.Persona],
) -> List[models.Persona]:
    """Adjunta academy_progress (avg de Enrollment) a cada persona in-place.

    spiritual_health se deja al default del schema (0.8) porque el valor
    hash-based anterior era mock/placeholder, no dato real.
    """
    if not personas:
        return personas
    persona_ids = [p.id for p in personas]
    progress_data = (
        db.query(
            models.Enrollment.persona_id,
            func.avg(models.Enrollment.progress_percent),
        )
        .filter(models.Enrollment.persona_id.in_(persona_ids))
        .group_by(models.Enrollment.persona_id)
        .all()
    )
    progress_map = {pid: float(avg or 0.0) for pid, avg in progress_data}
    for p in personas:
        p.academy_progress = progress_map.get(p.id, 0.0)
    return personas


def search_personas_paginated(
    db: Session,
    search: str | None = None,
    role: str | None = None,
    spiritual_status: str | None = None,
    sede_id: UUID | None = None,
    offset: int = 0,
    limit: int = 100,
    sort_by: str | None = None,
    sort_dir: str = "asc",
) -> dict:
    """Returns { items: [...], total: N } for server-side AG Grid pagination."""
    query = db.query(models.Persona).options(
        selectinload(models.Persona.family),
        selectinload(models.Persona.positions),
    )
    # Axioma 3 — Multi-Tenant: filtrar por sede obligatoriamente
    if sede_id is not None:
        query = query.filter(models.Persona.sede_id == sede_id)
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                models.Persona.first_name.ilike(like),
                models.Persona.last_name.ilike(like),
                models.Persona.email.ilike(like),
                models.Persona.church_role.ilike(like),
            )
        )
    if role:
        query = query.filter(models.Persona.church_role == role)
    if spiritual_status:
        query = query.filter(models.Persona.spiritual_status == spiritual_status)

    total = query.count()

    sort_col = _MEMBER_SORT_FIELDS.get(sort_by or "last_name", models.Persona.last_name)
    query = query.order_by(sort_col.desc() if sort_dir == "desc" else sort_col.asc())

    personas = query.offset(offset).limit(limit).all()
    return {"items": _enrich_personas_with_progress(db, personas), "total": total}


def get_personas(db: Session, search: str | None = None, role: str | None = None):
    return search_personas(db, search=search, role=role)


def get_talents(db: Session, search: str | None = None):
    return search_personas(db, search=search)
