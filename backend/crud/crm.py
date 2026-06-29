"""CRM: Personas, pipeline, events, tasks, counseling, prayer, grupos, etc."""

import datetime as dt
import logging
import uuid
from typing import List, Optional
from uuid import UUID

from backend.crud._utils import _to_uuid

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, selectinload

from backend import models, schemas
from backend.core.security import decrypt_data, encrypt_data
from backend.crud._utils import _utcnow
from backend.schemas.crm import CrmEventUpdate
from backend.schemas.notifications import CommunicationLogUpdate
from backend.schemas.operational import CommunityBoardCardUpdate


_logger = logging.getLogger(__name__)


def _is_uuid_like(value) -> bool:
    try:
        uuid.UUID(str(value))
        return True
    except (TypeError, ValueError):
        return False


def resolve_persona_id_for_user(db: Session, user_id: uuid.UUID | str | None):
    if user_id is None:
        return None
    try:
        persona_uuid = uuid.UUID(str(user_id))
    except (TypeError, ValueError, AttributeError):
        return None
    persona = (
        db.query(models.Persona.id)
        .filter(models.Persona.id == persona_uuid)
        .first()
    )
    return persona[0] if persona else None


def resolve_persona_id_from_identity(db: Session, identity: uuid.UUID | str | None):
    if identity is None:
        return None
    return resolve_persona_id_for_user(db, identity)


def get_user_sede_id(db: Session, user_id: str) -> str | None:
    """Obtiene el sede_id de la Persona vinculada al usuario actual.

    Retorna None si el usuario no tiene persona asociada o la persona no tiene sede.
    Usado para imponer filtro Multi-Tenant (Axioma 3) en todas las queries.
    """
    from backend.core.tenant import get_user_sede_id as resolve_user_sede_id

    return resolve_user_sede_id(db, user_id)


# ── Axioma 3 — Multi-Tenant: Defense-in-Depth scope re-check (CRUD layer) ───


def _actor_sede_or_none(db: Session, actor_user_id) -> str | None:
    """Resolve la sede del actor o None si es superadmin / actor ausente / anterior.

    Disparadores de None (no se aplica scope-check):
      - `actor_user_id is None`: callers anterior o scripts (workers async,
        migraciones, seeds) que operan sin contexto de usuario.
      - `get_user_sede_id` retorna None: usuario sin persona vinculada o
        con persona sin sede asignada (típicamente superadmin).

    En cualquier otro caso devuelve la sede del actor como string.

    Manejo de excepciones: se capturan sólo errores de tipo/valor/atributo
    (propios de inputs malformados). Errores de DB/programación no se
    enmascaran — propagan para no bypassear el scope-check por bug oculto.
    """
    if actor_user_id is None:
        return None
    try:
        return get_user_sede_id(db, str(actor_user_id))
    except (TypeError, ValueError, AttributeError):
        return None


def _resolve_anchor_sede(
    db: Session, anchor_name: str, anchor_value
) -> str | None:
    """Resuelve la sede_id del target de un anchor FK. Retorna None si el
    target no existe o no tiene sede asignada.

    Anchors soportados (multi-tenant TareaCRM):
      - `caso_id`: FK a CasoCRM (sede_id propia).
      - `persona_id`: FK a Persona (sede_id propia).
      - `asignado_a_id`: alias semántico de TareaCRM.assignee_id (FK a Persona).

    Función pura de resolución. NO decide si hay violation.
    """
    from backend.models_crm_pipeline import CasoCRM

    if anchor_value is None:
        return None

    if anchor_name == "caso_id":
        row = (
            db.query(CasoCRM.sede_id)
            .filter(CasoCRM.id == anchor_value)
            .first()
        )
    elif anchor_name in ("persona_id", "asignado_a_id"):
        row = (
            db.query(models.Persona.sede_id)
            .filter(models.Persona.id == anchor_value)
            .first()
        )
    else:
        return None

    if not row or not row[0]:
        return None
    return str(row[0])


def _crud_scope_re_check_task(
    db: Session,
    actor_user_id,
    *,
    incoming_anchors: dict | None = None,
    current_row_anchors: dict | None = None,
    operation: str = "WRITE",
) -> None:
    """Defense in depth — Multi-Tenant (Axioma 3) re-check al nivel del CRUD.

    Cierra el TOCTOU gap donde otro admin puede mover una fila cross-sede
    entre el API fetch (p.ej. `_get_scoped_task`) y el commit del CRUD.

    Política: STRICT sobre el estado final combinado de anclas.
    Combinamos incoming_anchors (FKs entrantes en CREATE/UPDATE) con
    current_row_anchors (FKs ya persistidas en UPDATE) — los incoming
    sobrescriben los current_row correspondientes. Para el estado final
    resultante exigimos: TODAS las anclas con valor distinto de None deben
    pertenecer a `user_sede`. Si alguna está en OTRA sede o es
    irresoluble, raise `HTTPException(404, "Task not found")`.

    Esta política es ESTRICTA vs la API (que es OR-based para lectura en
    `_get_scoped_task`). La asimetría es deliberada:

      - READ (API `_get_scoped_task` OR-based): si UNA ancla está en
        scope, la tarea es legible. Esto permite "tropical cases" donde
        un caso de sede_A se asigna temporalmente a un pastor de sede_B.
      - WRITE (CRUD defense-in-depth STRICT): no se permite INTRODUCIR o
        DEJAR anclas cross-sede en la fila mutada. Esto cierra el TOCTOU
        y blinda la creación de filas con anclas mixtas (potencial leak).

    Disparadores (skip cuando):
      - `actor_user_id is None`: callers anterior o scripts que no tienen
        contexto de usuario. NO rompe workers async, migraciones, seeds.
      - Actor sin sede (superadmin): ve TODO, igual que en API layer.

    Casos especiales:
      - Orphan (todas las anclas None): se REJECT para editores en sede.
        Consistente con API que rechaza orphans para no-superadmins.
      - FK target Inexistente: la query retorna None → tratado como
        violation (no podemos garantizar scope). REJECT por safe-default.

    Pre-flush en CREATE: se ejecuta antes de `db.add(row)` para no
    ensuciar la Identity Map de SQLAlchemy con objetos inválidos.
    Pre-mutation en UPDATE: se ejecuta después del SELECT inicial pero
    antes de cualquier `setattr`.

    NOTA sobre DB-audit: NO se persiste un `LogAuditoria` pre-commit.
    SQLAlchemy rollback descartaría cualquier entrada pendiente, y el
    audit trail debe registrar mutaciones cristalizadas (no intentos
    bloqueados). La anomalía se registra vía `logging.warning(...)` en
    la capa de aplicación para triage operacional.

    Args:
        incoming_anchors: anclas FK que se quieren escribir.
        current_row_anchors: anclas FK ya persistidas (UPDATE only).
        operation: 'CREATE' o 'UPDATE' (sólo logging clarity).
    """
    user_sede = _actor_sede_or_none(db, actor_user_id)
    if not user_sede:
        return

    # Combinar incoming sobre current_row (incoming gana → refleja el
    # estado FINAL de la fila post-mutación).
    combined: dict = {}
    if current_row_anchors:
        combined.update(current_row_anchors)
    if incoming_anchors:
        combined.update(incoming_anchors)

    if not combined:
        return  # defensivo: caller debe pasar al menos un slot

    # Orphan guard: TODAS las anclas son None → fila huérfana. Para un
    # editor en sede, esto viola el axioma (orphan visible sólo a
    # superadmin en API). REJECT por consistencia.
    if all(value is None for value in combined.values()):
        _logger.warning(
            "Axioma 3 scope violation blocked at CRUD layer "
            "(op=%s actor_sede=%s actor_user_id=%s reason=orphan_all_anchors_none)",
            operation,
            user_sede,
            actor_user_id,
        )
        from fastapi import HTTPException as _HTTPException
        raise _HTTPException(status_code=404, detail="Task not found")

    # STRICT: TODAS las anclas con valor deben estar en user_sede.
    # None como valor de slot → "no se setea este anchor", v\u00e1lido.
    # (Una ancla no escrita/no persistida NO se valida; sólo lo presente
    # en el estado final combinado.)
    for anchor_name, anchor_value in combined.items():
        if anchor_value is None:
            # Slot no seteado → nada que validar. Skip silenciosamente.
            continue
        anchor_sede = _resolve_anchor_sede(db, anchor_name, anchor_value)
        if anchor_sede is None or anchor_sede != str(user_sede):
            # Cross-sede o target inexistente → violation.
            _logger.warning(
                "Axioma 3 scope violation blocked at CRUD layer "
                "(op=%s actor_sede=%s actor_user_id=%s anchor=%s "
                "anchor_sede=%s reason=cross_sede_or_unresolvable)",
                operation,
                user_sede,
                actor_user_id,
                anchor_name,
                anchor_sede,
            )
            from fastapi import HTTPException as _HTTPException
            # Mensaje genérico (sin nombre del anchor) para no leakear
            # información sobre qué vector fue cross-sede. El detalle
            # diagnóstico queda en `logging.warning(...)`.
            raise _HTTPException(status_code=404, detail="Task not found")


def _audit_log(
    db: Session, tabla: str, registro_id: str, accion: str, detalles: dict | None = None, usuario_id: str | None = None
) -> None:
    """Registra una entrada en logs_auditoria (JSONB) para trazabilidad.

    Axioma 1 — Auditoría Estricta: toda mutación sensible debe dejar traza.
    """
    from backend.models_evangelism import LogAuditoria
    import uuid as _uuid

    db.add(
        LogAuditoria(
            tabla_afectada=tabla,
            registro_id=str(registro_id),
            accion=accion,
            detalles_cambio=detalles or {},
            usuario_id=_uuid.UUID(usuario_id) if usuario_id else None,
        )
    )


# ── Personas ────────────────────────────────────────────


def create_persona(db: Session, payload: schemas.PersonaCreate) -> models.Persona:
    # Axioma 1 — Validación de Identidad Previa: buscar persona existente
    # por teléfono o documento antes de crear un duplicado.
    existing = _find_existing_persona(db, payload)
    if existing:
        # Si existe, devolver el registro existente (no crear duplicado)
        return existing

    import uuid as _uuid

    data = payload.model_dump(exclude_unset=True)
    if "baptism_date" in data:
        data["fecha_bautismo"] = data.pop("baptism_date")
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
    old_fecha_bautismo = row.fecha_bautismo

    updates = payload.model_dump(exclude_unset=True)
    if "baptism_date" in updates:
        updates["fecha_bautismo"] = updates.pop("baptism_date")
    for key, value in updates.items():
        setattr(row, key, value)

    # Axioma 1 — Integridad de Embudo: registrar cambios en historial_embudo
    _track_funnel_changes(db, row, old_church_role, old_estado_vital, old_fecha_bautismo)

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


def _track_funnel_changes(db: Session, persona, old_church_role, old_estado_vital, old_fecha_bautismo):
    """Registra en HistorialEmbudo los cambios en church_role, estado_vital, o fecha_bautismo."""
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

    # fecha_bautismo (nuevo bautismo)
    if old_fecha_bautismo is None and persona.fecha_bautismo is not None:
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


# ── Personas ────────────────────────────────────────────


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


# ── CRM Events ─────────────────────────────────────────


def get_crm_events(db: Session, sede_id: str | None = None, skip: int = 0, limit: int = 100) -> List[models.CrmEvent]:
    q = db.query(models.CrmEvent)
    if sede_id:
        q = q.filter(models.CrmEvent.sede_id == sede_id)
    return q.order_by(models.CrmEvent.event_date.desc()).offset(skip).limit(limit).all()


def create_crm_event(db: Session, payload: schemas.CrmEventCreate) -> models.CrmEvent:
    try:
        payload_data = payload.model_dump()
        role_ids = payload_data.get("target_role_ids") or []
        payload_data["target_role_ids"] = [str(role_id) for role_id in role_ids] or None
        if payload_data.get("target_audience") == "ROLE":
            payload_data["target_role_id"] = role_ids[0] if role_ids else payload_data.get("target_role_id")
        else:
            payload_data["target_role_id"] = None
            payload_data["target_role_ids"] = None
        row = models.CrmEvent(**payload_data)
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
    except Exception as e:
        db.rollback()
        raise ValueError(f"Error al crear evento: {str(e)}")


# ── CRM Tasks ──────────────────────────────────────────


def get_crm_tasks(
    db: Session,
    assignee_persona_id: Optional[uuid.UUID] = None,
    persona_id: Optional[uuid.UUID] = None,
) -> List[models.TareaCRM]:
    query = db.query(models.TareaCRM)
    if assignee_persona_id:
        query = query.filter(models.TareaCRM.assignee_id == assignee_persona_id)
    if persona_id:
        query = query.filter(models.TareaCRM.persona_id == persona_id)
    return query.order_by(models.TareaCRM.due_date.asc()).all()


def create_crm_task(
    db: Session,
    payload: schemas.CrmTaskCreate,
    *,
    actor_user_id: str | uuid.UUID | None = None,
) -> models.TareaCRM:
    """Crea una tarea CRM y registra audit log (Axioma 1 — Auditoría Estricta).

    A partir de la refactorización, la generación del audit log vive aquí
    (defense in depth): cualquier caller — API endurecida, script de
    seeding, worker asíncrono — persiste la traza sin depender del caller
    de tener la lógica duplicada.

    Argumentos:
        db: sesión SQLAlchemy.
        payload: schema Pydantic `CrmTaskCreate`.
        actor_user_id: identidad (UUID o string) del usuario que origina la
            mutación. Si es `None` (e.g., bulk import desde script), la fila
            de auditoría se persiste con `usuario_id=NULL`. Si tiene sede
            asignada, se aplica defense-in-depth scope re-check (OR-based)
            sobre las anclas entrantes.
    """
    data = payload.model_dump()
    assignee_identity = data.pop("assignee_id", None)
    data["assignee_id"] = resolve_persona_id_from_identity(db, assignee_identity)

    # Defense in depth — Axioma 3 (Multi-Tenant) scope re-check (CREATE, pre-flush).
    # Cierra el TOCTOU gap donde un caller que no es la API endurecida (worker,
    # script, seed) podría crear una tarea con anclas cross-sede. Si el actor
    # está en sede y ALGUNA FK entrante está en OTRA sede → 404 pre-add.
    _crud_scope_re_check_task(
        db,
        actor_user_id,
        incoming_anchors={
            "caso_id": data.get("caso_id"),
            "persona_id": data.get("persona_id"),
            "asignado_a_id": data.get("assignee_id"),
        },
        operation="CREATE",
    )

    row = models.TareaCRM(**data)
    db.add(row)
    db.flush()  # poblar row.id antes del audit log
    _audit_log(
        db,
        "crm_tareas",
        str(row.id),
        "CREATE",
        detalles={
            "title": row.titulo,
            "category": row.categoria,
            "persona_id": str(row.persona_id) if row.persona_id else None,
            "asignado_a_id": str(row.asignado_a_id) if row.asignado_a_id else None,
            "priority": row.prioridad,
            "status": row.estado,
        },
        usuario_id=str(actor_user_id) if actor_user_id else None,
    )
    db.commit()
    db.refresh(row)
    return row


def update_crm_task(
    db: Session,
    task_id: uuid.UUID,
    payload,
    *,
    actor_user_id: str | uuid.UUID | None = None,
) -> models.TareaCRM:
    """Actualiza una tarea CRM y registra audit log sólo si hay cambios reales.

    Axioma 1 — Auditoría Estricta: minimiza el ruido en `log_auditoria`
    omitiendo updates idempotentes (mismo valor). Defense in depth: el
    audit log persiste independientemente del caller (API endurecida,
    script, worker).

    Argumentos:
        db: sesión SQLAlchemy.
        task_id: UUID de la tarea a actualizar.
        payload: `schemas.CrmTaskUpdate` (preferido) o un `dict` compatible
            para callers anterior (algunos tests directos al CRUD usan dict).
            El CRUD acepta ambos via duck typing sobre `model_dump`.
        actor_user_id: identidad del usuario que origina la mutación; `None`
            produce una fila con `usuario_id=NULL`.

    Nota sobre scope (Axioma 3): el CRUD NO valida scope Multi-Tenant por
    sí mismo (no conoce el usuario actual fuera del `actor_user_id` que se
    le pasa explícito). Esa responsabilidad sigue siendo de la capa API.
    La separación API↔CRUD permite que el CRUD sea reutilizable desde
    callers no-API (workers, scripts) sin re-implementar la lógica de
    scope.
    """
    row = db.query(models.TareaCRM).filter(models.TareaCRM.id == task_id).first()
    if not row:
        return None

    # Duck typing: schema Pydantic (preferred) o dict (anterior callers).
    changes_in = (
        payload.model_dump(exclude_unset=True)
        if hasattr(payload, "model_dump")
        else dict(payload)
    )

    # Defense in depth — Axioma 3 (Multi-Tenant) scope re-check (UPDATE).
    # Detecta DOS vectores:
    #   1. TOCTOU: ancla actualmente persistida se movió cross-sede
    #      entre el fetch inicial del API y este re-fetch del CRUD.
    #   2. NEW_FK: el body del PATCH intenta escribir una FK nueva
    #      (caso_id/persona_id/assignee_id) que pertenece a otra sede.
    # Pre-mutation: se ejecuta antes de cualquier `setattr` para no
    # dejar la Identity Map de SQLAlchemy en estado parcial.
    _current_anchors = {
        "caso_id": row.caso_id,
        "persona_id": row.persona_id,
        "asignado_a_id": row.assignee_id,
    }
    _incoming_anchors: dict = {}
    _ANCHOR_PAYLOAD_KEYS = (
        ("caso_id", "caso_id"),
        ("persona_id", "persona_id"),
        ("assignee_id", "asignado_a_id"),  # schema usa assignee_id, helper usa asignado_a_id
    )
    for payload_key, anchor_key in _ANCHOR_PAYLOAD_KEYS:
        if payload_key in changes_in:
            _incoming_anchors[anchor_key] = changes_in[payload_key]
    _crud_scope_re_check_task(
        db,
        actor_user_id,
        incoming_anchors=_incoming_anchors or None,
        current_row_anchors=_current_anchors,
        operation="UPDATE",
    )

    changes: dict = {}
    for key, value in changes_in.items():
        # SQLAlchemy resuelve los synonyms (title↔titulo, etc.) tanto en
        # getattr como en setattr, así que podemos usar la key cruda.
        old_val = getattr(row, key, None)
        if _values_equivalent(old_val, value):
            continue
        changes[key] = {
            "from": _value_for_audit(old_val),
            "to": _value_for_audit(value),
        }
        setattr(row, key, value)

    if changes:
        _audit_log(
            db,
            "crm_tareas",
            str(row.id),
            "UPDATE",
            detalles=changes,
            usuario_id=str(actor_user_id) if actor_user_id else None,
        )
    db.commit()
    db.refresh(row)
    return row


def _values_equivalent(a, b) -> bool:
    """Compara valores manejando None en ambos lados y tipos datetime."""
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    if hasattr(a, "isoformat") and hasattr(b, "isoformat"):
        return a.isoformat() == b.isoformat()
    return a == b


def _value_for_audit(value):
    """Serializa un valor para el campo `detalles_cambio` JSON de la tabla
    `logs_auditoria` (columna JSONB).

    Reglas de serialización (todas JSONB-safe):
      - `None` → `None`
      - `datetime` / `date` → ISO 8601 string (`isoformat()`)
      - `uuid.UUID` → `str(uuid)` (Postgres JSONB no acepta objetos UUID
        nativos; necesitamos string para reconstruir el valor en queries
        posteriores).
      - resto → tal cual.
    """
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def delete_crm_task(db: Session, task_id: uuid.UUID) -> bool:
    row = db.query(models.TareaCRM).filter(models.TareaCRM.id == task_id).first()
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ── Volunteers ─────────────────────────────────────────


def get_volunteer_shifts(db: Session, persona_id: Optional[str] = None) -> List[models.VolunteerShift]:
    query = db.query(models.VolunteerShift)
    if persona_id:
        query = query.filter(models.VolunteerShift.persona_id == persona_id)
    return query.order_by(models.VolunteerShift.shift_start.asc()).all()


def create_volunteer_shift(db: Session, payload: schemas.VolunteerShiftCreate) -> models.VolunteerShift:
    row = models.VolunteerShift(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


# ── Event Attendance ───────────────────────────────────


def create_event_attendance(db: Session, payload: schemas.EventAttendanceCreate) -> models.EventAttendance:
    try:
        row = models.EventAttendance(**payload.model_dump())
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
    except Exception as e:
        db.rollback()
        raise ValueError(f"Error al registrar asistencia: {str(e)}")


# ── Counseling ─────────────────────────────────────────


def get_counseling_tickets(
    db: Session,
    status: str | None = None,
    persona_id: str | None = None,
    sede_id: UUID | None = None,
    skip: int = 0,
    limit: int = 100,
) -> List[models.CounselingTicket]:
    query = db.query(models.CounselingTicket).filter(models.CounselingTicket.deleted_at.is_(None))
    if sede_id is not None:
        query = query.join(models.Persona, models.CounselingTicket.persona_id == models.Persona.id).filter(
            models.Persona.sede_id == sede_id
        )
    if status:
        query = query.filter(models.CounselingTicket.status == status)
    if persona_id:
        query = query.filter(models.CounselingTicket.persona_id == persona_id)
    tickets = query.order_by(models.CounselingTicket.created_at.desc()).offset(skip).limit(limit).all()

    for t in tickets:
        if t.notes:
            t.notes = decrypt_data(t.notes)

    return tickets


def create_counseling_ticket(db: Session, payload: schemas.CounselingTicketCreate) -> models.CounselingTicket:
    from backend.crud._utils import analyze_pastoral_priority, analyze_pastoral_sentiment

    try:
        data = payload.model_dump()
        pastor_identity = data.pop("pastor_id", None)
        data["pastor_id"] = resolve_persona_id_from_identity(db, pastor_identity)
        raw_notes = data.get("notes", "")

        data["priority_level"] = analyze_pastoral_priority(raw_notes)
        score, label = analyze_pastoral_sentiment(raw_notes)
        data["sentiment_score"] = score
        data["sentiment_label"] = label

        if raw_notes:
            data["notes"] = encrypt_data(raw_notes)

        row = models.CounselingTicket(**data)
        db.add(row)
        db.commit()
        db.refresh(row)

        row.notes = decrypt_data(row.notes)
        return row
    except Exception as e:
        db.rollback()
        raise ValueError(f"Error al crear ticket de consejería: {str(e)}")


# ── Prayer ─────────────────────────────────────────────


def get_prayer_requests(
    db: Session, status: str | None = None, skip: int = 0, limit: int = 100
) -> List[models.PrayerRequest]:
    query = db.query(models.PrayerRequest)
    if status:
        query = query.filter(models.PrayerRequest.status == status)
    return query.order_by(models.PrayerRequest.created_at.desc()).offset(skip).limit(limit).all()


def create_prayer_request(db: Session, payload: schemas.PrayerRequestCreate) -> models.PrayerRequest:
    try:
        row = models.PrayerRequest(**payload.model_dump())
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
    except Exception as e:
        db.rollback()
        raise ValueError(f"Error al registrar petición de oración: {str(e)}")


# ── Grupos ───────────────────────────────────────


def get_grupos(db: Session, skip: int = 0, limit: int = 100, sede_id: str | None = None):
    query = db.query(models.GrupoEvangelismo)
    if sede_id:
        query = query.filter(models.GrupoEvangelismo.sede_id == sede_id)
    return query.offset(skip).limit(limit).all()


def _group_participant_role_values(item):
    role = str(getattr(item, "role", "") or "participante").strip()
    custom_role_id = getattr(item, "rol_personalizado_id", None)
    if role.startswith("custom:"):
        try:
            custom_role_id = int(role.split(":", 1)[1])
        except (TypeError, ValueError):
            custom_role_id = None
        role = "personalizado"
    return role or "participante", custom_role_id


def create_grupo(db: Session, payload: schemas.GrupoEvangelismoCreate, sede_id: str | None = None):
    data = payload.model_dump(exclude={"base_attendee_ids", "base_attendees_with_roles"})
    # Map evangelism_strategy_id -> estrategia_id.
    if data.get("evangelism_strategy_id") and not data.get("estrategia_id"):
        data["estrategia_id"] = data.pop("evangelism_strategy_id")
    # Infer sede_id from user if not provided in payload
    if sede_id and not data.get("sede_id"):
        data["sede_id"] = sede_id
    if not str(data.get("code") or "").strip():
        base = (str(data.get("name") or data.get("address") or "FARO").strip().upper().replace(" ", "-"))[
            :12
        ]  # truncate to leave room for suffix
        suffix = _utcnow().strftime("%m%d%H%M")  # 8 chars
        data["code"] = f"{base}-{suffix}"[:30]
    if not str(data.get("name") or "").strip():
        fallback_name = str(data.get("address") or data["code"]).strip()
        data["name"] = f"Faro pendiente - {fallback_name}"
    db_obj = models.GrupoEvangelismo(**data)
    db.add(db_obj)

    base_attendees_with_roles = getattr(payload, "base_attendees_with_roles", None)
    if base_attendees_with_roles is not None:
        db.flush()  # Get the ID without committing
        for item in base_attendees_with_roles:
            role, custom_role_id = _group_participant_role_values(item)
            attendee = models.ParticipanteGrupo(
                grupo_id=db_obj.id,
                persona_id=uuid.UUID(str(item.persona_id)) if isinstance(item.persona_id, str) else item.persona_id,
                role=role,
                rol_personalizado_id=custom_role_id,
            )
            db.add(attendee)
    elif payload.base_attendee_ids:
        db.flush()  # Get the ID without committing
        for persona_id in payload.base_attendee_ids:
            attendee = models.ParticipanteGrupo(grupo_id=db_obj.id, persona_id=persona_id, role="asistente")
            db.add(attendee)

    db.commit()
    db.refresh(db_obj)
    return db_obj


def update_grupo(db: Session, house_id: uuid.UUID, payload: schemas.GrupoEvangelismoUpdate):
    house = db.query(models.GrupoEvangelismo).filter(models.GrupoEvangelismo.id == house_id).first()
    if not house:
        return None

    update_data = payload.model_dump(
        exclude_unset=True,
        exclude={"base_attendee_ids", "base_attendees_with_roles"},
    )
    if "code" in update_data and not str(update_data["code"] or "").strip():
        update_data["code"] = house.code or f"FARO-{house.id}"
    for key, value in update_data.items():
        setattr(house, key, value)

    if payload.base_attendees_with_roles is not None:
        db.query(models.ParticipanteGrupo).filter(models.ParticipanteGrupo.grupo_id == house_id).update(
            {models.ParticipanteGrupo.deleted_at: _utcnow(), models.ParticipanteGrupo.activo: False},
            synchronize_session=False,
        )
        for item in payload.base_attendees_with_roles:
            role, custom_role_id = _group_participant_role_values(item)
            p_id = uuid.UUID(str(item.persona_id)) if isinstance(item.persona_id, str) else item.persona_id
            existing = db.query(models.ParticipanteGrupo).filter(
                models.ParticipanteGrupo.grupo_id == house_id,
                models.ParticipanteGrupo.persona_id == p_id
            ).first()
            if existing:
                existing.deleted_at = None
                existing.activo = True
                existing.role = role
                existing.rol_personalizado_id = custom_role_id
            else:
                db.add(
                    models.ParticipanteGrupo(
                        grupo_id=house_id,
                        persona_id=p_id,
                        role=role,
                        rol_personalizado_id=custom_role_id,
                    )
                )
        # Sincronizar lider_persona_id, asistente_persona_id y anfitrion_persona_id desde los participantes.
        _SUBORDINATE_TOKENS = {"co", "colider", "colíder", "asistente", "del"}
        db.flush()
        
        new_leader_id = None
        new_assistant_id = None
        new_host_id = None

        for item in payload.base_attendees_with_roles:
            role_str = str(getattr(item, "role", "") or "").lower().strip()
            custom_id = getattr(item, "rol_personalizado_id", None)
            if role_str.startswith("custom:") and not custom_id:
                try:
                    custom_id = int(role_str.split(":", 1)[1])
                except (ValueError, TypeError):
                    pass
            if custom_id:
                custom_rol = db.query(models.RolPersonalizadoEstrategia).filter(
                    models.RolPersonalizadoEstrategia.id == custom_id
                ).first()
                role_str = (custom_rol.nombre_rol if custom_rol else role_str).lower().strip()
            
            # Normalizar para comparación
            role_norm = role_str.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
            tokens = set(role_norm.replace("-", " ").replace("_", " ").split())
            
            is_leader = ("lider" in tokens or "leader" in tokens) and not (tokens & _SUBORDINATE_TOKENS)
            is_assistant = ("asistente" in tokens or "colider" in tokens or ("co" in tokens and ("lider" in tokens or "leader" in tokens)))
            is_host = "anfitrion" in tokens or "host" in tokens

            p_uuid = uuid.UUID(str(item.persona_id)) if isinstance(item.persona_id, str) else item.persona_id

            if is_leader and not new_leader_id:
                new_leader_id = p_uuid
            if is_assistant and not new_assistant_id:
                new_assistant_id = p_uuid
            if is_host and not new_host_id:
                new_host_id = p_uuid

        house.lider_persona_id = new_leader_id
        house.asistente_persona_id = new_assistant_id
        house.anfitrion_persona_id = new_host_id
    elif payload.base_attendee_ids is not None:
        db.query(models.ParticipanteGrupo).filter(models.ParticipanteGrupo.grupo_id == house_id).update(
            {models.ParticipanteGrupo.deleted_at: _utcnow(), models.ParticipanteGrupo.activo: False},
            synchronize_session=False,
        )
        for persona_id in payload.base_attendee_ids:
            p_id = uuid.UUID(str(persona_id)) if isinstance(persona_id, str) else persona_id
            existing = db.query(models.ParticipanteGrupo).filter(
                models.ParticipanteGrupo.grupo_id == house_id,
                models.ParticipanteGrupo.persona_id == p_id
            ).first()
            if existing:
                existing.deleted_at = None
                existing.activo = True
                existing.role = "miembro"
            else:
                db.add(
                    models.ParticipanteGrupo(
                        grupo_id=house_id,
                        persona_id=p_id,
                        role="miembro",
                    )
                )

    db.flush()
    house.personas_count = (
        db.query(models.ParticipanteGrupo)
        .filter(
            models.ParticipanteGrupo.grupo_id == house_id,
            models.ParticipanteGrupo.deleted_at.is_(None),
        )
        .count()
    )

    db.commit()
    db.refresh(house)
    return house


# ── Talents & Families ─────────────────────────────────


def get_talents(db: Session, search: str | None = None):
    return search_personas(db, search=search)


def get_families(db: Session, skip: int = 0, limit: int = 100):
    families = db.query(models.Family).offset(skip).limit(limit).all()
    for f in families:
        f.personas_count = db.query(models.Persona).filter(models.Persona.family_id == f.id).count()
    return families


def create_family(db: Session, name: str):
    fam = models.Family(name=name)
    db.add(fam)
    db.commit()
    db.refresh(fam)
    return fam


# ── Persona Timeline ────────────────────────────────────


def get_persona_timeline(db: Session, persona_id: str):
    persona = db.query(models.Persona).filter(models.Persona.id == _to_uuid(persona_id)).first()
    if not persona:
        return []

    timeline = []

    timeline.append(
        {
            "type": "participation",
            "title": "Ingreso a la Familia CCF",
            "description": f"Registro formal como {persona.church_role}.",
            "date": persona.created_at.isoformat(),
            "icon": "Sparkles",
            "color": "bg-purple-500",
        }
    )

    enrollments = db.query(models.Enrollment).filter(models.Enrollment.persona_id == persona.id).all()
    for en in enrollments:
        timeline.append(
            {
                "type": "academy",
                "title": "Inscripción Academia",
                "description": f"Inició el curso {en.course.title if en.course else 'de formación'}.",
                "date": en.created_at.isoformat(),
                "icon": "GraduationCap",
                "color": "bg-emerald-500",
            }
        )
        if en.certificate_issued:
            timeline.append(
                {
                    "type": "certificate",
                    "title": "Certificación Obtenida",
                    "description": f"Completó con éxito el curso: {en.course.title if en.course else 'de formación'}.",
                    "date": (en.created_at + dt.timedelta(days=30)).isoformat(),
                    "icon": "Award",
                    "color": "bg-amber-500",
                }
            )

    ministries = db.query(models.PersonaMinistryAssignment).filter(models.PersonaMinistryAssignment.persona_id == persona_id).all()
    for mm in ministries:
        timeline.append(
            {
                "type": "ministry",
                "title": "Vinculación Ministerial",
                "description": f"Se integró al ministerio de {mm.name}.",
                "date": (mm.created_at.isoformat() if mm.created_at else persona.created_at.isoformat()),
                "icon": "ShieldCheck",
                "color": "bg-indigo-600",
            }
        )

    sessions = db.query(models.CounselingTicket).filter(models.CounselingTicket.persona_id == persona_id).all()
    for s in sessions:
        timeline.append(
            {
                "type": "counseling",
                "title": "Sesión Pastoral",
                "description": f"Atención espiritual: {s.subject}.",
                "date": s.created_at.isoformat(),
                "icon": "Heart",
                "color": "bg-rose-500",
            }
        )

    calls = db.query(models.CommunicationLog).filter(models.CommunicationLog.persona_id == persona_id).all()
    for c in calls:
        timeline.append(
            {
                "type": "communication",
                "title": "Seguimiento Pastoral",
                "description": f"Contacto vía {c.channel}: {c.content[:50]}...",
                "date": c.created_at.isoformat(),
                "icon": "Phone",
                "color": "bg-blue-500",
            }
        )

    timeline.sort(key=lambda x: x["date"], reverse=True)
    return timeline


# ── Communication Logs ─────────────────────────────────


def _crud_scope_re_check_communication_log_create(
    db: Session,
    actor_user_id,
    persona_id,
) -> None:
    """Axioma 3 — defense in depth para ``create_communication_log``.

    Re-valida el anchor ``persona_id`` (única FK de CommunicationLog)
    contra la sede del actor. Cierra el TOCTOU gap donde un caller que
    NO es la API endurecida (worker async, script de seeding, llamada
    directa al CRUD) podría crear un log sobre una persona de otra sede,
    bypaseando ``_get_scoped_persona`` en el router.

    Política (consistente con ``_crud_scope_re_check_task``):
      - Actor sin sede (``_actor_sede_or_none`` retorna ``None``):
        superadmin / anterior path — bypass sin check.
      - Actor con sede y ``persona_id`` None: REJECT (orphan log para un
        editor en sede viola el axioma — invisible para sí mismo,
        visible sólo a ``get_communication_logs(sede_id=None)``).
      - Actor con sede y ``persona_id`` en OTRA sede o irresoluble: REJECT.
      - Match exacto de sede: OK.

    Raises ``HTTPException(404)`` con mensaje neutro (sin leak del anchor)
    para que el caller lo trate como existence-leak safe. La anomalía se
    registra vía ``logging.warning(...)`` para triage operacional.
    """
    user_sede = _actor_sede_or_none(db, actor_user_id)
    if not user_sede:
        return  # superadmin / anterior path

    from fastapi import HTTPException as _HTTPException

    if persona_id is None:
        _logger.warning(
            "Axioma 3 scope violation: create_communication_log sin persona_id "
            "(actor_sede=%s actor_user_id=%s)",
            user_sede,
            actor_user_id,
        )
        raise _HTTPException(
            status_code=404, detail="CommunicationLog creation blocked"
        )

    target_sede = _resolve_anchor_sede(db, "persona_id", persona_id)
    if target_sede is None or target_sede != str(user_sede):
        _logger.warning(
            "Axioma 3 scope violation: create_communication_log cross-sede "
            "(actor_sede=%s actor_user_id=%s persona_id=%s target_sede=%s)",
            user_sede,
            actor_user_id,
            persona_id,
            target_sede,
        )
        # Mensaje genérico para no leakear info de la violation.
        raise _HTTPException(
            status_code=404, detail="CommunicationLog creation blocked"
        )


def create_communication_log(
    db: Session,
    payload: schemas.CommunicationLogCreate,
    *,
    actor_user_id: str | uuid.UUID | None = None,
) -> models.CommunicationLog:
    """Crea un CommunicationLog con defense-in-depth (Axioma 3 — CRUD layer).

    Parámetros:
        db: sesión SQLAlchemy.
        payload: schema Pydantic ``CommunicationLogCreate``. Incluye
            ``persona_id`` (target, ∀-required?) y opcional ``leader_id``
            (staff que origina el log).
        actor_user_id: identidad (UUID o string) del usuario que origina
            la mutación. Si es ``None`` (bulk import desde script /
            worker async anterior), se salta el scope re-check. Si tiene
            sede asignada, se valida que ``persona_id`` pertenezca a esa
            sede antes del ``db.add``.

    Defense-in-depth: el CRUD vuelve a verificar el anchor incluso si el
    caller es la API endurecida. Esto cierra el TOCTOU gap donde otro
    admin podría mover la ``Persona`` a otra sede entre el fetch del API
    (``_get_scoped_persona``) y el commit (``create_communication_log``).
    """
    data = payload.model_dump()
    leader_identity = data.pop("leader_id", None)
    data["leader_id"] = resolve_persona_id_from_identity(db, leader_identity)

    # Defense in depth — Axioma 3 (Multi-Tenant) scope re-check (CREATE).
    # Cierra el TOCTOU gap donde un caller no-API (worker, script, seed)
    # podría crear un log con persona cross-sede. Si el actor está en
    # sede_a e intenta loguear persona de sede_b → 404 pre-add.
    _crud_scope_re_check_communication_log_create(
        db, actor_user_id, data.get("persona_id")
    )

    row = models.CommunicationLog(**{k: v for k, v in data.items()
                                     if hasattr(models.CommunicationLog, k)})
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_communication_logs(
    db: Session, limit: int = 50, sede_id: str | None = None
):
    """Lista los CommunicationLog más recientes, opcionalmente acotados a la sede indicada.

    Axioma 3 — Multi-Tenant: si ``sede_id`` está presente, agrega un JOIN con
    ``models.Persona`` y filtra ``Persona.sede_id == sede_id``. CommunicationLog
    NO tiene columna ``sede_id`` propia; el scope se obtiene vía la FK
    ``persona_id → personas.id``. Si ``sede_id`` es ``None`` (superadmin /
    caller sin scope), retorna el log global sin filtrar.

    Política READ-only: para hardening defensivo adicional, callers sensibles
    (API) deben pasar explícitamente su ``user_sede`` recibido desde JWT vía
    ``get_user_sede_id``.
    """
    query = db.query(models.CommunicationLog)
    if sede_id:
        query = query.join(
            models.Persona,
            models.CommunicationLog.persona_id == models.Persona.id,
        ).filter(models.Persona.sede_id == sede_id)
    return query.order_by(models.CommunicationLog.created_at.desc()).limit(limit).all()


# ── Notifications ────────────────────────────────────────


def get_user_notifications(db: Session, user_id: uuid.UUID | str, limit: int = 20) -> List[models.Notification]:
    notification_user_id = resolve_persona_id_for_user(db, user_id)
    if notification_user_id is None:
        return []
    return (
        db.query(models.Notification)
        .filter(models.Notification.user_id == notification_user_id)
        .order_by(models.Notification.created_at.desc())
        .limit(limit)
        .all()
    )


def mark_notification_as_read(
    db: Session,
    notification_id: uuid.UUID,
    *,
    owner_persona_id: uuid.UUID | str | None = None,
):
    """Marca una Notification como le\u00edda con ownership check (Axioma 3).

    Parámetros:
        db: sesi\u00f3n SQLAlchemy.
        notification_id: UUID de la Notification a marcar.
        owner_persona_id: persona_id del caller. Si est\u00e1 presente y
            difiere de ``Notification.user_id`` (recipient), la Notification
            se considera fuera de scope y el CRUD retorna ``None`` (el
            API layer lo traduce a 404 / existence-leak safe). Si es
            ``None`` (superadmin / caller sin contexto de persona), se
            omite el ownership check — comportamiento anterior preservado
            para scripts y bulk imports.

    Axioma 3 — ownership: cada usuario ve y modifica SÓLO sus propias
    notifications (BOLA-style leak prevention). Pattern consistente con
    ``_get_scoped_persona`` del CRM: 404 (no 403) para evitar existence
    leaks.

    Returns:
        La ``Notification`` actualizada (is_read=True) o ``None`` si no
        existe o no pertenece al ``owner_persona_id`` (existence-leak
        safe el caller no distingue entre ambos casos).
    """
    notification = db.query(models.Notification).filter(models.Notification.id == notification_id).first()
    if not notification:
        return None
    # Ownership guard: notification.user_id == owner_persona_id
    if owner_persona_id is not None and str(notification.user_id) != str(owner_persona_id):
        # Existence-leak safe: NO se persiste mutaci\u00f3n y se retorna None
        # para que el API layer responda 404 sin filtrar IDs existentes.
        return None
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification


def mark_all_notifications_read(db: Session, user_id: uuid.UUID | str):
    notification_user_id = resolve_persona_id_for_user(db, user_id)
    if notification_user_id is None:
        return
    db.query(models.Notification).filter(
        models.Notification.user_id == notification_user_id,
        models.Notification.is_read.is_(False),
    ).update({models.Notification.is_read: True})
    db.commit()


# ── Donations ────────────────────────────────────────────


def create_donation(db: Session, payload: schemas.DonationCreate) -> models.Donation:
    row = models.Donation(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_donations(db: Session, skip: int = 0, limit: int = 100) -> List[models.Donation]:
    return (
        db.query(models.Donation)
        .filter(models.Donation.deleted_at.is_(None))
        .order_by(models.Donation.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_total_donations_amount(db: Session) -> float:
    return db.query(func.sum(models.Donation.amount)).scalar() or 0


# ── Spiritual Milestones ─────────────────────────────────


def get_milestones(db: Session, persona_id) -> List[models.SpiritualMilestone]:
    persona_uuid = uuid.UUID(str(persona_id))
    return (
        db.query(models.SpiritualMilestone)
        .filter(
            models.SpiritualMilestone.persona_id == persona_uuid,
            models.SpiritualMilestone.deleted_at.is_(None),
        )
        .order_by(models.SpiritualMilestone.event_date.desc())
        .all()
    )


def create_milestone(
    db: Session,
    persona_id,
    type: str,
    event_date,
    minister_id: Optional[str] = None,
) -> models.SpiritualMilestone:
    persona_uuid = uuid.UUID(str(persona_id))
    minister_uuid = uuid.UUID(str(minister_id)) if minister_id else None
    row = models.SpiritualMilestone(
        persona_id=persona_uuid,
        type=type,
        event_date=event_date,
        minister_id=minister_uuid,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


# ── Family Personas ──────────────────────────────────────


def get_family_personas(db: Session, family_id: UUID):
    return (
        db.query(models.Persona)
        .filter(models.Persona.family_id == family_id)
        .order_by(models.Persona.nombre_completo.asc())
        .all()
    )


# ── Support Tickets ─────────────────────────────────────


def create_support_ticket(db: Session, ticket: schemas.SupportTicketCreate) -> models.SupportTicket:
    row = models.SupportTicket(**ticket.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_support_tickets(
    db: Session, user_id: Optional[uuid.UUID] = None, skip: int = 0, limit: int = 100
) -> List[models.SupportTicket]:
    q = db.query(models.SupportTicket).order_by(models.SupportTicket.created_at.desc())
    if user_id is not None:
        q = q.filter(models.SupportTicket.user_id == user_id)
    return q.offset(skip).limit(limit).all()


def update_support_ticket(db: Session, ticket_id: str, new_status: str):
    ticket = db.query(models.SupportTicket).filter(models.SupportTicket.id == ticket_id).first()
    if not ticket:
        return None
    ticket.status = new_status
    db.commit()
    db.refresh(ticket)
    return ticket


# ── Community Board ─────────────────────────────────────


def get_community_cards(db: Session, column_id: Optional[str] = None) -> List[models.CommunityBoardCard]:
    q = db.query(models.CommunityBoardCard).order_by(models.CommunityBoardCard.position.asc())
    if column_id:
        q = q.filter(models.CommunityBoardCard.column_id == column_id)
    return q.all()


def create_community_card(db: Session, card: schemas.CommunityBoardCardCreate) -> models.CommunityBoardCard:
    max_pos = db.query(func.max(models.CommunityBoardCard.position)).scalar() or 0
    row = models.CommunityBoardCard(**card.model_dump(), position=max_pos + 1)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


# --- Evangelism Strategies ---
# MOVED to crud/evangelism.py (EstrategiaEvangelismo with UUID PK)


# ── Missing CRUDs ──────────────────────────────────────

# ── Personas ─────────────────────────────────────────────


# ── CRM Events ─────────────────────────────────────────


# ── Test-compatible alias ─────────────────────────────────────────────
def list_personas(db: Session, **kwargs) -> List[models.Persona]:
    """Alias consumed by ````tests/test_crud_integration.py::TestCrmCrud.test_list_personas````.

    Delegates to ````search_personas```` which already accepts ````limit````, ````sede_id````
    and the full filter set; this thin wrapper just normalizes the public name.
    """
    return search_personas(db, **kwargs)


def get_crm_event(db: Session, event_id: UUID) -> Optional[models.CrmEvent]:
    return db.query(models.CrmEvent).filter(models.CrmEvent.id == event_id).first()


def update_crm_event(db: Session, event_id: UUID, payload) -> Optional[models.CrmEvent]:
    """Update a CRM event. Accepts Pydantic schema or plain dict.

    The ````dict```` branch is for ````tests/test_remaining_gaps.py::test_events_crud```` which
    passes a raw ````dict```` (callers from the API always pass a schema). Detect
    via duck-typing so both shapes work without breaking the type contract.
    """
    row = db.query(models.CrmEvent).filter(models.CrmEvent.id == event_id).first()
    if not row:
        return None
    changes = (
        payload.model_dump(exclude_unset=True)
        if hasattr(payload, "model_dump")
        else dict(payload)
    )
    for key, value in changes.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def delete_crm_event(db: Session, event_id: UUID) -> bool:
    row = db.query(models.CrmEvent).filter(models.CrmEvent.id == event_id).first()
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


def get_event_attendance(db: Session, event_id: UUID) -> List[models.EventAttendance]:
    return db.query(models.EventAttendance).filter(models.EventAttendance.event_id == event_id).all()


def delete_event_attendance(db: Session, attendance_id: UUID) -> bool:
    row = db.query(models.EventAttendance).filter(models.EventAttendance.id == attendance_id).first()
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ── Volunteers ─────────────────────────────────────────


def get_volunteer_shift(db: Session, shift_id: UUID) -> Optional[models.VolunteerShift]:
    return db.query(models.VolunteerShift).filter(models.VolunteerShift.id == shift_id).first()


def update_volunteer_shift(
    db: Session, shift_id: UUID, payload: schemas.VolunteerShiftUpdate
) -> Optional[models.VolunteerShift]:
    row = db.query(models.VolunteerShift).filter(models.VolunteerShift.id == shift_id).first()
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def delete_volunteer_shift(db: Session, shift_id: UUID) -> bool:
    row = db.query(models.VolunteerShift).filter(models.VolunteerShift.id == shift_id).first()
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ── Counseling ─────────────────────────────────────────


def get_counseling_ticket(db: Session, ticket_id: UUID) -> Optional[models.CounselingTicket]:
    row = (
        db.query(models.CounselingTicket)
        .filter(
            models.CounselingTicket.id == ticket_id,
            models.CounselingTicket.deleted_at.is_(None),
        )
        .first()
    )
    if row and row.notes:
        row.notes = decrypt_data(row.notes)
    return row


def update_counseling_ticket(
    db: Session, ticket_id: UUID, payload: schemas.CounselingTicketUpdate
) -> Optional[models.CounselingTicket]:
    row = db.query(models.CounselingTicket).filter(models.CounselingTicket.id == ticket_id).first()
    if not row:
        return None
    data = payload.model_dump(exclude_unset=True)
    if "pastor_id" in data:
        pastor_identity = data.pop("pastor_id")
        row.pastor_id = resolve_persona_id_from_identity(db, pastor_identity)
    for key, value in data.items():
        if key == "notes" and value:
            setattr(row, key, encrypt_data(value))
        else:
            setattr(row, key, value)
    db.commit()
    db.refresh(row)
    if row.notes:
        row.notes = decrypt_data(row.notes)
    return row


def delete_counseling_ticket(db: Session, ticket_id: UUID) -> bool:
    row = (
        db.query(models.CounselingTicket)
        .filter(
            models.CounselingTicket.id == ticket_id,
            models.CounselingTicket.deleted_at.is_(None),
        )
        .first()
    )
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ── Prayer ─────────────────────────────────────────────


def get_prayer_request(db: Session, request_id: UUID) -> Optional[models.PrayerRequest]:
    return db.query(models.PrayerRequest).filter(models.PrayerRequest.id == request_id).first()


def update_prayer_request(
    db: Session, request_id: UUID, payload: schemas.PrayerRequestUpdate
) -> Optional[models.PrayerRequest]:
    row = db.query(models.PrayerRequest).filter(models.PrayerRequest.id == request_id).first()
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def delete_prayer_request(db: Session, request_id: UUID) -> bool:
    row = db.query(models.PrayerRequest).filter(models.PrayerRequest.id == request_id).first()
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ── Grupos ───────────────────────────────────────


def get_grupo(db: Session, house_id: uuid.UUID) -> Optional[models.GrupoEvangelismo]:
    return db.query(models.GrupoEvangelismo).filter(models.GrupoEvangelismo.id == house_id).first()


def delete_grupo(db: Session, house_id: uuid.UUID) -> bool:
    row = db.query(models.GrupoEvangelismo).filter(models.GrupoEvangelismo.id == house_id).first()
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ── Families ───────────────────────────────────────────


def get_family(db: Session, family_id: UUID) -> Optional[models.Family]:
    return db.query(models.Family).filter(models.Family.id == family_id).first()


def update_family(db: Session, family_id: UUID, name: str) -> Optional[models.Family]:
    row = db.query(models.Family).filter(models.Family.id == family_id).first()
    if not row:
        return None
    row.name = name
    db.commit()
    db.refresh(row)
    return row


def delete_family(db: Session, family_id: UUID) -> bool:
    row = db.query(models.Family).filter(models.Family.id == family_id).first()
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ── Consolidation ──────────────────────────────────────


def _emit_mesh_event(event_type: str, case_id: str, persona_id: str | None = None, extra: dict | None = None) -> None:
    """Emite un evento asíncrono al motor Mesh vía Redis PubSub.

    No bloquea el request HTTP. El motor Mesh consume estos eventos para
    calcular SLAs, asignar alertas Overdue, y actualizar dashboards en tiempo real.
    """
    try:
        from backend.core.cache import get_redis
        from backend.core.config import get_settings
        import json

        redis_client = get_redis()
        if redis_client is None:
            return

        settings = get_settings()
        channel = f"{settings.environment}:ws"
        payload = {
            "event": event_type,
            "case_id": case_id,
            "persona_id": persona_id,
            "timestamp": _utcnow().isoformat(),
            **(extra or {}),
        }
        redis_client.publish(channel, json.dumps(payload, default=str))
    except Exception:
        pass  # Fire-and-forget: no bloquear el request si Redis no está disponible


# ── Communication Logs ─────────────────────────────────


def get_communication_log(db: Session, log_id: str) -> Optional[models.CommunicationLog]:
    return db.query(models.CommunicationLog).filter(models.CommunicationLog.id == log_id).first()


def update_communication_log(
    db: Session, log_id: str, payload: CommunicationLogUpdate
) -> Optional[models.CommunicationLog]:
    row = db.query(models.CommunicationLog).filter(models.CommunicationLog.id == log_id).first()
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def delete_communication_log(db: Session, log_id: str) -> bool:
    row = db.query(models.CommunicationLog).filter(models.CommunicationLog.id == log_id).first()
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ── Donations ───────────────────────────────────────────


def get_donation(db: Session, donation_id: UUID) -> Optional[models.Donation]:
    return (
        db.query(models.Donation)
        .filter(
            models.Donation.id == donation_id,
            models.Donation.deleted_at.is_(None),
        )
        .first()
    )


def update_donation(db: Session, donation_id: UUID, payload: schemas.DonationUpdate) -> Optional[models.Donation]:
    row = db.query(models.Donation).filter(models.Donation.id == donation_id).first()
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def delete_donation(db: Session, donation_id: UUID) -> bool:
    row = (
        db.query(models.Donation)
        .filter(
            models.Donation.id == donation_id,
            models.Donation.deleted_at.is_(None),
        )
        .first()
    )
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ── Spiritual Milestones ─────────────────────────────────


def update_milestone(db: Session, milestone_id: UUID, **kwargs) -> Optional[models.SpiritualMilestone]:
    row = db.query(models.SpiritualMilestone).filter(models.SpiritualMilestone.id == milestone_id).first()
    if not row:
        return None
    for key, value in kwargs.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def delete_milestone(db: Session, milestone_id: UUID) -> bool:
    row = (
        db.query(models.SpiritualMilestone)
        .filter(
            models.SpiritualMilestone.id == milestone_id,
            models.SpiritualMilestone.deleted_at.is_(None),
        )
        .first()
    )
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ── Support Tickets ─────────────────────────────────────


def get_support_ticket(db: Session, ticket_id: str) -> Optional[models.SupportTicket]:
    return db.query(models.SupportTicket).filter(models.SupportTicket.id == ticket_id).first()


def delete_support_ticket(db: Session, ticket_id: str) -> bool:
    row = db.query(models.SupportTicket).filter(models.SupportTicket.id == ticket_id).first()
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ── Community Board ─────────────────────────────────────


def get_community_card(db: Session, card_id: UUID) -> Optional[models.CommunityBoardCard]:
    return db.query(models.CommunityBoardCard).filter(models.CommunityBoardCard.id == card_id).first()


def update_community_card(
    db: Session, card_id: UUID, payload: CommunityBoardCardUpdate
) -> Optional[models.CommunityBoardCard]:
    row = db.query(models.CommunityBoardCard).filter(models.CommunityBoardCard.id == card_id).first()
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def delete_community_card(db: Session, card_id: UUID) -> bool:
    row = db.query(models.CommunityBoardCard).filter(models.CommunityBoardCard.id == card_id).first()
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


# ── Evangelism Strategies ──────────────────────────────────────────────
# MOVED to crud/evangelism.py (EstrategiaEvangelismo with UUID PK)
