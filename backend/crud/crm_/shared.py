"""Shared CRM helpers used across multiple subdomains."""
import logging
import uuid

from sqlalchemy.orm import Session

from backend import models

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


def _actor_sede_or_none(
    db: Session, actor_user_id: str | uuid.UUID
) -> str | None:
    """Resolve la sede de un actor canónico autenticado.

    ``None`` sólo significa que una persona válida no tiene sede asignada
    (superadministración). Un actor ausente, malformado o inexistente se
    rechaza y nunca desactiva silenciosamente los controles de scope.
    """
    from fastapi import HTTPException as _HTTPException

    try:
        actor_uuid = uuid.UUID(str(actor_user_id))
    except (TypeError, ValueError, AttributeError):
        raise _HTTPException(status_code=401, detail="Authenticated actor required")
    if resolve_persona_id_for_user(db, actor_uuid) is None:
        raise _HTTPException(status_code=401, detail="Authenticated actor required")
    return get_user_sede_id(db, str(actor_uuid))


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

    El actor es obligatorio. Un superadministrador canónico sin sede conserva
    el alcance global de administración.

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
    # None como valor de slot → "no se setea este anchor", válido.
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
