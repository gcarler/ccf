"""CRM task CRUD."""
import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from backend import models, schemas
from backend.crud._utils import _utcnow
from backend.crud.crm_.shared import (
    _audit_log,
    _crud_scope_re_check_task,
    resolve_persona_id_from_identity,
)


def get_crm_tasks(
    db: Session,
    assignee_persona_id: Optional[uuid.UUID] = None,
    persona_id: Optional[uuid.UUID] = None,
) -> List[models.TareaCRM]:
    query = db.query(models.TareaCRM).filter(models.TareaCRM.deleted_at.is_(None))
    if assignee_persona_id:
        query = query.filter(models.TareaCRM.assignee_id == assignee_persona_id)
    if persona_id:
        query = query.filter(models.TareaCRM.persona_id == persona_id)
    return query.order_by(models.TareaCRM.due_date.asc()).all()


def create_crm_task(
    db: Session,
    payload: schemas.CrmTaskCreate,
    *,
    actor_user_id: str | uuid.UUID,
) -> models.TareaCRM:
    """Crea una tarea CRM y registra audit log (Axioma 1 — Auditoría Estricta).

    A partir de la refactorización, la generación del audit log vive aquí
    (defense in depth): cualquier caller — API endurecida, script de
    seeding, worker asíncrono — persiste la traza sin depender del caller
    de tener la lógica duplicada.

    Argumentos:
        db: sesión SQLAlchemy.
        payload: schema Pydantic `CrmTaskCreate`.
        actor_user_id: UUID canónico del actor que origina la mutación. Es
            obligatorio también para scripts y workers.
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
        usuario_id=str(actor_user_id),
    )
    db.commit()
    db.refresh(row)
    return row


def update_crm_task(
    db: Session,
    task_id: uuid.UUID,
    payload: schemas.CrmTaskUpdate,
    *,
    actor_user_id: str | uuid.UUID,
) -> models.TareaCRM:
    """Actualiza una tarea CRM y registra audit log sólo si hay cambios reales.

    Axioma 1 — Auditoría Estricta: minimiza el ruido en `log_auditoria`
    omitiendo updates idempotentes (mismo valor). Defense in depth: el
    audit log persiste independientemente del caller (API endurecida,
    script, worker).

    Argumentos:
        db: sesión SQLAlchemy.
        task_id: UUID de la tarea a actualizar.
        payload: contrato Pydantic `schemas.CrmTaskUpdate`.
        actor_user_id: UUID canónico del usuario que origina la mutación.

    Nota sobre scope (Axioma 3): el CRUD NO valida scope Multi-Tenant por
    sí mismo (no conoce el usuario actual fuera del `actor_user_id` que se
    le pasa explícito). Esa responsabilidad sigue siendo de la capa API.
    La separación API↔CRUD permite que el CRUD sea reutilizable desde
    callers no-API (workers, scripts) sin re-implementar la lógica de
    scope.
    """
    row = (
        db.query(models.TareaCRM)
        .filter(
            models.TareaCRM.id == task_id,
            models.TareaCRM.deleted_at.is_(None),
        )
        .first()
    )
    if not row:
        return None

    changes_in = payload.model_dump(exclude_unset=True)

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
            usuario_id=str(actor_user_id),
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
    row = (
        db.query(models.TareaCRM)
        .filter(
            models.TareaCRM.id == task_id,
            models.TareaCRM.deleted_at.is_(None),
        )
        .first()
    )
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


def _emit_mesh_event(event_type: str, case_id: str, persona_id: str | None = None, extra: dict | None = None) -> None:
    """Emite un evento asíncrono al motor Mesh vía Redis PubSub.

    No bloquea el request HTTP. El motor Mesh consume estos eventos para
    calcular SLAs, asignar alertas Overdue, y actualizar dashboards en tiempo real.
    """
    try:
        import json

        from backend.core.cache import get_redis
        from backend.core.config import get_settings

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
