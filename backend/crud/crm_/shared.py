"""Shared CRM helpers used across multiple subdomains."""
import logging
import threading
import uuid

from sqlalchemy import inspect
from sqlalchemy.orm import Session, load_only, selectinload
from sqlalchemy.sql import literal_column

from backend import models
from backend.schemas.crm.base import PersonaResponse

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
        _logger.warning(
            "resolve_persona_id_for_user: user_id con formato UUID inválido, devolviendo None: %r",
            user_id,
        )
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


def get_user_sede_id(db: Session, user_id: "str | uuid.UUID | Any") -> uuid.UUID | None:
    """Obtiene el sede_id de la Persona vinculada al usuario actual.

    Retorna ``uuid.UUID`` (no ``str``) para que los callers CRUD puedan
    comparar directamente con ``Persona.sede_id`` (que es ``UUID(as_uuid=True)``
    en el modelo). La fuente canónica en ``backend.core.tenant.get_user_sede_id``
    delegada aquí retorna ``str | None`` — esta envoltura CRM hace la coerción
    a ``UUID`` una sola vez en el límite de la capa CRUD, donde es tipicamente
    consistente con el ORM.

    Retorna ``None`` si el usuario no tiene persona asociada o la persona no
    tiene sede. Usado para imponer filtro Multi-Tenant (Axioma 3) en todas las
    queries.
    """
    from backend.core.tenant import get_user_sede_id as resolve_user_sede_id

    raw = resolve_user_sede_id(db, user_id)
    if raw is None:
        return None
    try:
        return uuid.UUID(str(raw))
    except (TypeError, ValueError, AttributeError):
        # Valor histórico no-UUID: preferimos None (scope desactivado para el
        # actor) en vez de propagate el str y romper comparaciones ORM.
        _logger.warning("get_user_sede_id: valor no-UUID descartado: %r", raw)
        return None


# ── Axioma 3 — Multi-Tenant: Defense-in-Depth scope re-check (CRUD layer) ───


def _actor_sede_or_none(
    db: Session, actor_user_id: str | uuid.UUID
) -> uuid.UUID | None:
    """Resolve la sede de un actor canónico autenticado.

    Retorna ``uuid.UUID`` (no ``str``) para que los callers CRUD puedan
    comparar directamente con columnas ``sede_id`` modeladas como
    ``UUID(as_uuid=True)``. ``None`` sólo significa que una persona válida no
    tiene sede asignada (superadministración). Un actor ausente, malformado o
    inexistente se rechaza y nunca desactiva silenciosamente los controles de
    scope.
    """
    from fastapi import HTTPException as _HTTPException

    try:
        actor_uuid = uuid.UUID(str(actor_user_id))
    except (TypeError, ValueError, AttributeError):
        raise _HTTPException(status_code=401, detail="Authenticated actor required")
    if resolve_persona_id_for_user(db, actor_uuid) is None:
        raise _HTTPException(status_code=401, detail="Authenticated actor required")
    return get_user_sede_id(db, actor_uuid)


def _resolve_anchor_sede(
    db: Session, anchor_name: str, anchor_value
) -> uuid.UUID | None:
    """Resuelve la sede_id del target de un anchor FK. Retorna ``uuid.UUID``
    (no ``str``) para que los callers puedan comparar directamente con
    ``user_sede`` (también ``UUID``) en el re-check de scope Axioma 3.
    Retorna ``None`` si el target no existe o no tiene sede asignada.

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
    raw = row[0]
    if isinstance(raw, uuid.UUID):
        return raw
    try:
        return uuid.UUID(str(raw))
    except (TypeError, ValueError, AttributeError):
        return None


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
        if anchor_sede is None or anchor_sede != user_sede:
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
    import uuid as _uuid

    from backend.models_evangelism import LogAuditoria

    db.add(
        LogAuditoria(
            tabla_afectada=tabla,
            registro_id=str(registro_id),
            accion=accion,
            detalles_cambio=detalles or {},
            usuario_id=_uuid.UUID(usuario_id) if usuario_id else None,
        )
    )


# ── Dynamic schema introspection helpers (moved from api/crm/_shared.py)
# Cache simple para nombres de columnas vivas. El schema no cambia en runtime,
# por lo que cachear indefinidamente es seguro y evita introspection en cada request.
_SCHEMA_COLUMN_CACHE: dict[str, set[str]] = {}
_SCHEMA_COLUMN_LOCK = threading.Lock()

_logger_schema = logging.getLogger(__name__)


def _get_live_column_names(db: Session, table_name: str) -> set[str]:
    """Devuelve los nombres de columnas de una tabla, cacheados por nombre."""
    with _SCHEMA_COLUMN_LOCK:
        cached = _SCHEMA_COLUMN_CACHE.get(table_name)
        if cached is not None:
            return cached
    bind = db.get_bind()
    if bind is None:
        return set()
    try:
        columns = inspect(bind).get_columns(table_name)
    except Exception as exc:
        _logger_schema.debug("Failed to inspect %s columns: %s", table_name, exc)
        return set()
    result = {str(column.get("name")) for column in columns if column.get("name")}
    with _SCHEMA_COLUMN_LOCK:
        _SCHEMA_COLUMN_CACHE[table_name] = result
    return result


def _persona_live_column_names(db: Session) -> set[str]:
    return _get_live_column_names(db, "personas")


def _case_live_column_names(db: Session) -> set[str]:
    return _get_live_column_names(db, "crm_casos")


def _case_created_column(db: Session):
    live_cols = _case_live_column_names(db)
    if "fecha_creacion" in live_cols and hasattr(models.CasoCRM, "fecha_creacion"):
        return models.CasoCRM.fecha_creacion
    if "created_at" in live_cols:
        return literal_column("crm_casos.created_at")
    if "fecha_creacion" in live_cols:
        return literal_column("crm_casos.fecha_creacion")
    if hasattr(models.CasoCRM, "fecha_creacion"):
        return models.CasoCRM.fecha_creacion
    return None


def _stage_live_column_names(db: Session) -> set[str]:
    return _get_live_column_names(db, "crm_etapas_pipeline")


def persona_query(db: Session):
    live_cols = _persona_live_column_names(db)
    live_attrs = [
        getattr(models.Persona, name)
        for name in live_cols
        if hasattr(models.Persona, name)
    ]
    query = db.query(models.Persona)
    if live_attrs:
        query = query.options(load_only(*live_attrs))
    return query


def case_query(db: Session):
    live_cols = _case_live_column_names(db)
    live_attrs = [
        getattr(models.CasoCRM, name)
        for name in live_cols
        if hasattr(models.CasoCRM, name)
    ]
    query = db.query(models.CasoCRM)
    if live_attrs:
        query = query.options(load_only(*live_attrs))

    persona_live_cols = _persona_live_column_names(db)
    persona_live_attrs = [
        getattr(models.Persona, name)
        for name in persona_live_cols
        if hasattr(models.Persona, name)
    ]
    stage_live_cols = _stage_live_column_names(db)
    stage_live_attrs = [
        getattr(models.EtapaPipeline, name)
        for name in stage_live_cols
        if hasattr(models.EtapaPipeline, name)
    ]

    if persona_live_attrs:
        query = query.options(
            selectinload(models.CasoCRM.persona).load_only(*persona_live_attrs),
            selectinload(models.CasoCRM.asignado_a).load_only(*persona_live_attrs),
        )
    if stage_live_attrs:
        query = query.options(
            selectinload(models.CasoCRM.etapa_actual).load_only(*stage_live_attrs)
        )
    return query


def prepare_persona_for_output(db: Session, persona: models.Persona):
    """Populate missing ORM-backed attributes with None to avoid lazy-loading
    fields that are absent in the live table.
    """
    live_cols = _persona_live_column_names(db)
    for field_name in PersonaResponse.model_fields:
        if field_name == "nombre_completo" or field_name in live_cols:
            continue
        if hasattr(models.Persona, field_name):
            try:
                setattr(persona, field_name, None)
            except Exception as exc:
                _logger_schema.debug("Failed to set persona field %s to None: %s", field_name, exc)
                persona.__dict__[field_name] = None
    return persona


def prepare_case_for_output(db: Session, case: models.CasoCRM):
    live_cols = _case_live_column_names(db)
    for field_name in models.CasoCRM.__table__.columns.keys():
        if field_name in live_cols:
            continue
        if hasattr(models.CasoCRM, field_name):
            try:
                setattr(case, field_name, None)
            except Exception as exc:
                _logger_schema.debug("Failed to set case field %s to None: %s", field_name, exc)
                case.__dict__[field_name] = None
    persona = getattr(case, "persona", None)
    if persona is not None:
        prepare_persona_for_output(db, persona)
    assigned = getattr(case, "asignado_a", None)
    if assigned is not None:
        prepare_persona_for_output(db, assigned)
    return case
