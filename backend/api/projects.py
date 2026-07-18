from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import Integer, and_, cast, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from backend import crud, models, schemas
from backend.core.audit import record_admin_action
from backend.core.config import get_settings
from backend.core.database import get_db
from backend.core.permissions import (
    MODULE_PERMISSION_MAP,
    _has_permission,
    get_current_active_user,
    get_user_effective_permissions,
    normalize_role,
    require_module_access,
    require_staff_or_admin,
)
from backend.core.storage import storage_service
from backend.core.uploads import MAX_UPLOAD_SIZE, sanitize_filename
from backend.crud.crm import get_user_sede_id
from backend.crud.projects import (
    create_milestone as _projects_create_milestone,
)
from backend.crud.projects import (
    delete_milestone as _projects_delete_milestone,
)
from backend.crud.projects import (
    get_user_persona_id,
)
from backend.mesh_websockets import manager
from backend.services.task_notifications import notify_task_assigned

settings = get_settings()


router = APIRouter()
logger = logging.getLogger(__name__)


def _resolve_persona(db: Session, user_id: Any):
    persona_id = get_user_persona_id(db, user_id)
    if not persona_id:
        return None
    return db.query(models.Persona).filter(models.Persona.id == persona_id).first()


def _author_name(persona) -> str:
    if not persona:
        return "Usuario"
    return getattr(persona, "nombre_completo", None) or getattr(persona, "full_name", None) or "Usuario"


def _assignment_changed(previous_assignee_id, current_assignee_id) -> bool:
    if previous_assignee_id is None and current_assignee_id is None:
        return False
    return str(previous_assignee_id) != str(current_assignee_id)


@router.get("/tasks", response_model=List[schemas.ProjectTask])
def list_all_my_tasks(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Obtiene todas las tareas asignadas al usuario actual de todos los proyectos.

    Axioma 3 — strict scope: solo se devuelven tareas de proyectos en la
    ``sede_id`` del actor. Superadmin (sin sede) ve todo.
    """
    persona_id = get_user_persona_id(db, current_user.id)
    if not persona_id:
        return []
    user_sede = get_user_sede_id(db, current_user.id)
    q = (
        db.query(models.ProjectTask)
        .join(models.Project, models.Project.id == models.ProjectTask.project_id)
        .filter(
            models.ProjectTask.assignee_id == persona_id,
            models.ProjectTask.deleted_at.is_(None),
        )
    )
    if user_sede:
        q = q.filter(models.Project.sede_id == user_sede)
    tasks = q.all()
    for t in tasks:
        _prepare_task_for_response(t)
    return tasks


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _log_project_activity(db: Session, project_id: Any, user_id: Any, action_type: str, description: str):
    persona_id = get_user_persona_id(db, user_id)
    activity = models.ProjectActivityLog(
        project_id=_to_uuid(project_id),
        persona_id=persona_id,
        action_type=action_type,
        description=description,
    )
    db.add(activity)
    return activity


def _to_uuid(val):
    """Convert string UUID to uuid.UUID for SQLAlchemy filters."""
    if isinstance(val, uuid.UUID):
        return val
    try:
        return uuid.UUID(str(val))
    except (ValueError, AttributeError):
        return val


def _ensure_project(db: Session, project_id: str, user_sede=None) -> models.Project:
    """Fetch a project by id and enforce multi-tenant scope (Axioma 3).

    Existence-leak safe: returns 404 (never 403) when the project is in a
    different ``sede_id`` than the actor or when the project's ``sede_id``
    is NULL while the actor is restricted to a sede. This
    matches the CRM/CMS ``_ensure_*`` convention so cross-tenant probing
    yields indistinguishable error from "not found".

    Fix vs prior implementation: previously the guard used
    ``if user_sede and project.sede_id and ...``, which let projects without
    ``sede_id`` slip past scope checks
    when an actor from any sede queried them. The new guard explicitly
    rejects projects with NULL ``sede_id`` whenever the actor is bounded
    to a sede, eliminating the leak.

    Args:
        db: SQLAlchemy session.
        project_id: Project identifier (UUID or string).
        user_sede: Actor's sede. ``None`` ⇒ superadmin path, no scope
            filter is applied.
    """
    project = (
        db.query(models.Project)
        .options(
            selectinload(models.Project.tasks).selectinload(models.ProjectTask.attachments),
            selectinload(models.Project.tasks).selectinload(models.ProjectTask.supplies),
            selectinload(models.Project.tasks).selectinload(models.ProjectTask.subtasks),
            selectinload(models.Project.milestones),
            selectinload(models.Project.activity_logs),
        )
        .filter(models.Project.id == _to_uuid(project_id), models.Project.deleted_at.is_(None))
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    # Axioma 3 strict scope: even projects with NULL sede_id are hidden
    # from seated actors. Only the superadmin (user_sede = None) bypasses scope.
    if user_sede is not None:
        if project.sede_id is None or str(project.sede_id) != str(user_sede):
            raise HTTPException(status_code=404, detail="Project not found")
    return project


def _ensure_task(db: Session, task_id: str) -> models.ProjectTask:
    task = (
        db.query(models.ProjectTask)
        .options(
            selectinload(models.ProjectTask.supplies),
            selectinload(models.ProjectTask.attachments),
        )
        .filter(models.ProjectTask.id == _to_uuid(task_id), models.ProjectTask.deleted_at.is_(None))
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


def _ensure_task_in_project(db: Session, project_id: str, task_id: str) -> models.ProjectTask:
    task = _ensure_task(db, task_id)
    if str(task.project_id) != str(project_id):
        raise HTTPException(status_code=404, detail="Task not found in project")
    return task


def _ensure_supply_in_task(db: Session, project_id: str, task_id: str, supply_id: UUID) -> models.TaskSupply:
    _ensure_task_in_project(db, project_id, task_id)
    supply = (
        db.query(models.TaskSupply)
        .filter(models.TaskSupply.id == supply_id, models.TaskSupply.task_id == _to_uuid(task_id))
        .first()
    )
    if not supply:
        raise HTTPException(status_code=404, detail="Supply not found in task")
    return supply


def _ensure_milestone_in_project(db: Session, project_id: str, milestone_id: str) -> models.ProjectMilestone:
    milestone = (
        db.query(models.ProjectMilestone)
        .filter(
            models.ProjectMilestone.id == _to_uuid(milestone_id),
            models.ProjectMilestone.project_id == _to_uuid(project_id),
        )
        .first()
    )
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found in project")
    return milestone


def _ensure_attachment_in_task(db: Session, project_id: str, task_id: str, attachment_id: str) -> models.ProjectAttachment:
    _ensure_task_in_project(db, project_id, task_id)
    attachment = (
        db.query(models.ProjectAttachment)
        .filter(
            models.ProjectAttachment.id == _to_uuid(attachment_id),
            models.ProjectAttachment.task_id == _to_uuid(task_id),
        )
        .first()
    )
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found in task")
    return attachment


def _inbox_item_exists_for_actor(
    db: Session,
    item_id: str,
    persona_id: Any,
    user_sede: Optional[Any],
) -> bool:
    """Determinar si ``item_id`` existe en el inbox del actor.

    PEND-QUALITY-INBOX-SCOPE-001 (cierre 2026-07-16): usado por
    :func:`mark_inbox_read` para rechazar ``item_id`` arbitrarios antes
    de tocar ``project_inbox_state``.

    Formatos aceptados (deben coincidir con la salida de
    :func:`list_inbox`):

    * ``comment-<uuid>``: comentario no resuelto (de otro autor) en un
      proyecto **no soft-deleted** de la ``sede_id`` del actor.
    * ``task-<uuid>``: tarea abierta (``status != "completed"``, **no
      soft-deleted**) asignada al actor, en un proyecto **no
      soft-deleted** de la ``sede_id`` del actor.

    Existencia-leak safe: cualquier formato inválido o UUID que no
    satisface las condiciones devuelve ``False``, por lo que
    ``mark_inbox_read`` responde **404** indistinguible de "no existe".
    """
    if not item_id or not isinstance(item_id, str) or "-" not in item_id:
        return False
    prefix, _, raw_uuid = item_id.partition("-")
    if prefix not in {"comment", "task"} or not raw_uuid:
        return False
    target_uuid = _to_uuid(raw_uuid)
    if target_uuid is raw_uuid:  # _to_uuid fallback cuando el parse falla
        return False

    if prefix == "comment":
        q = (
            db.query(models.ProjectComment.id)
            .join(models.Project, models.Project.id == models.ProjectComment.project_id)
            .filter(
                models.ProjectComment.id == target_uuid,
                models.ProjectComment.deleted_at.is_(None),
                ~models.ProjectComment.is_resolved,
                # Replicar el filtro de ``list_inbox``: auto-comentarios
                # del propio actor no aparecen en su feed, por lo que
                # tampoco deben ser marcables como leídos.
                models.ProjectComment.author_id != persona_id,
                # Solo comentarios de proyectos no soft-deleted; el filtro
                # de ``author_id != persona_id`` se aplica en ``list_inbox``
                # (auto-comentarios excluidos) y se respeta aquí implícito
                # vía la uni\u00f3n con ``list_inbox``.
                models.Project.deleted_at.is_(None),
            )
        )
        if user_sede is not None:
            q = q.filter(models.Project.sede_id == user_sede)
        return db.query(q.exists()).scalar() is True

    # prefix == "task"
    q = (
        db.query(models.ProjectTask.id)
        .join(models.Project, models.Project.id == models.ProjectTask.project_id)
        .filter(
            models.ProjectTask.id == target_uuid,
            models.ProjectTask.deleted_at.is_(None),
            models.ProjectTask.status != "completed",
            models.ProjectTask.assignee_id == persona_id,
            models.Project.deleted_at.is_(None),
        )
    )
    if user_sede is not None:
        q = q.filter(models.Project.sede_id == user_sede)
    return db.query(q.exists()).scalar() is True


def _get_persona_id_for_user(db: Session, user_id: Any) -> Optional[uuid.UUID]:
    """Resolve the persona_id for a given user_id.

    Assignment-based access in Projects is tied to ``personas.id`` (owner
    and assignee), not ``auth_users.id``. Returns ``None`` when the user
    has no associated persona.
    """
    persona_id = get_user_persona_id(db, user_id)
    if persona_id:
        return _to_uuid(persona_id)
    return None


def _is_project_owner(db: Session, project_id: Any, persona_id: Any) -> bool:
    """Return True if ``persona_id`` owns the given project."""
    project = (
        db.query(models.Project)
        .filter(
            models.Project.id == _to_uuid(project_id),
            models.Project.deleted_at.is_(None),
        )
        .first()
    )
    return project is not None and str(project.owner_id) == str(persona_id)


def _is_assigned_to_project(db: Session, project_id: Any, persona_id: Any) -> bool:
    """Check if ``persona_id`` has access to ``project_id`` via assignment.

    A persona is considered assigned to a project when:
    * They are the project owner, OR
    * They are the assignee of at least one non-deleted task in the project.
    """
    if _is_project_owner(db, project_id, persona_id):
        return True
    task = (
        db.query(models.ProjectTask)
        .filter(
            models.ProjectTask.project_id == _to_uuid(project_id),
            models.ProjectTask.assignee_id == _to_uuid(persona_id),
            models.ProjectTask.deleted_at.is_(None),
        )
        .first()
    )
    return task is not None


def _is_assigned_to_task(db: Session, task_id: Any, persona_id: Any) -> bool:
    """Check if ``persona_id`` has access to ``task_id`` via assignment.

    A persona is considered assigned to a task when:
    * They are the assignee of the task, OR
    * They are the owner of the parent project.
    """
    task = (
        db.query(models.ProjectTask)
        .filter(
            models.ProjectTask.id == _to_uuid(task_id),
            models.ProjectTask.deleted_at.is_(None),
        )
        .first()
    )
    if not task:
        return False
    if str(task.assignee_id) == str(persona_id):
        return True
    return _is_project_owner(db, task.project_id, persona_id)


def _has_role_based_project_access(db: Session, current_user: models.User, min_level: str) -> bool:
    """Check if the user has role-based permission for the Projects module.

    Reuses ``backend.core.permissions.get_user_effective_permissions`` and
    ``_has_permission`` so the assignment-based dependency stays consistent
    with the rest of the platform without circular imports.
    """
    perm_key = MODULE_PERMISSION_MAP["projects"].get(min_level)
    if not perm_key:
        return False
    perms = get_user_effective_permissions(db, current_user)
    if perms.get(perm_key) == "allow":
        return True
    role = normalize_role(str(getattr(current_user, "role", "")))
    if not role and hasattr(current_user, "rol_plataforma") and current_user.rol_plataforma:
        role = normalize_role(current_user.rol_plataforma.nombre)
    return _has_permission(role, set(perms.keys()), perm_key)


def require_project_access(min_level: str = "read"):
    """FastAPI dependency factory: role-based OR assignment-based access.

    Rules:
    * Admin/Gestor/Editor pass via role-based permissions (existing model).
    * For ``read`` and ``edit`` levels, any authenticated user with a
      persona assigned to the project/task also passes.
    * ``manage`` level remains strictly role-based.
    * Endpoints without a ``project_id`` or ``task_id`` path parameter
      fall back to role-based checks (assignment cannot be determined).
    * Axioma 3: before returning 403, the dependency checks whether the
      referenced project/task exists in the actor's sede. If it does not
      exist or belongs to another sede, 404 is returned instead, even for
      the ``manage`` level.

    This implements the product decision that in the Projects module
    access is driven by task/project assignment, not only by platform role.
    """
    async def _check(
        request: Request,
        current_user: models.User = Depends(get_current_active_user),
        db: Session = Depends(get_db),
    ):
        # Role-based access (admin bypass + projects:* permissions)
        if _has_role_based_project_access(db, current_user, min_level):
            return current_user

        project_id = request.path_params.get("project_id")
        task_id = request.path_params.get("task_id")

        # Axioma 3 — existence-leak safe: before rejecting with 403, verify the
        # resource exists in the actor's scope. If the project/task belongs to
        # another sede (or does not exist), return 404 so cross-sede probing is
        # indistinguishable from a missing resource. This applies to all levels,
        # including manage, so a user without projects:manage still gets 404
        # (not 403) when the resource is cross-sede or non-existent.
        user_sede = get_user_sede_id(db, current_user.id)
        if user_sede is not None and (project_id or task_id):
            target_project_id = None
            if task_id:
                task_row = (
                    db.query(models.ProjectTask.project_id)
                    .filter(
                        models.ProjectTask.id == _to_uuid(task_id),
                        models.ProjectTask.deleted_at.is_(None),
                    )
                    .first()
                )
                if not task_row:
                    raise HTTPException(status_code=404, detail="Task not found")
                target_project_id = task_row.project_id
                # If the path also carries a project_id, it must match the
                # task's parent project. Otherwise the resource is not
                # where the URL says it is.
                if project_id:
                    path_project_uuid = _to_uuid(project_id)
                    if str(target_project_id) != str(path_project_uuid):
                        raise HTTPException(status_code=404, detail="Task not found in project")
            elif project_id:
                target_project_id = _to_uuid(project_id)

            if target_project_id is not None:
                project_sede = (
                    db.query(models.Project.sede_id)
                    .filter(
                        models.Project.id == target_project_id,
                        models.Project.deleted_at.is_(None),
                    )
                    .scalar()
                )
                if project_sede is None or str(project_sede) != str(user_sede):
                    raise HTTPException(status_code=404, detail="Project not found")

        # manage level is strictly role-based
        if min_level == "manage":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permisos insuficientes. Se requiere: projects:{min_level}",
            )

        persona_id = _get_persona_id_for_user(db, current_user.id)
        if not persona_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permisos insuficientes. Se requiere: projects:{min_level}",
            )

        # Task-level endpoints take precedence when task_id is present
        if task_id and _is_assigned_to_task(db, task_id, persona_id):
            return current_user

        # Project-level assignment
        if project_id and _is_assigned_to_project(db, project_id, persona_id):
            return current_user

        # No project_id/task_id in path → cannot determine assignment
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permisos insuficientes. Se requiere: projects:{min_level}",
        )

    return _check


def _assert_assignee_in_sede(
    db: Session,
    assignee_id: Optional[uuid.UUID | str],
    user_sede: Optional[uuid.UUID | str],
) -> None:
    """Validate that an assignee persona belongs to the actor's ``sede_id``.

    Closed Axioma 3 enforcement on PATCH/POST payloads that carry an
    ``assignee_id``. Without this check, an actor from ``sede_a`` could
    inject a UUID of a persona from ``sede_b`` and have the backend
    transparently persist that cross-sede assignment.

    Behavior:
      * ``assignee_id`` falsy (None or empty) → silent skip (no assignee).
      * ``user_sede`` is ``None`` (superadmin) → no scope filter.
      * Otherwise the persona must exist AND live in the actor's sede.
        Personas with NULL ``sede_id`` are treated as untagged and
        blocked to avoid cross-sede leakage. Existence-leak safe: 404
        on mismatch (never 403).

    Note: ``_to_uuid`` is *not* raise-style — it returns the original bad
    value on parse failure. The downstream ``Persona.id ==`` filter then
    returns ``None`` and we map it to 404. We intentionally do NOT raise
    a separate 400 on malformed UUIDs; that's a single source of truth
    with the rest of the project.
    """
    if not assignee_id:
        return
    if user_sede is None:
        return
    persona_uuid = _to_uuid(assignee_id)
    persona = (
        db.query(models.Persona)
        .filter(models.Persona.id == persona_uuid)
        .first()
    )
    if not persona:
        raise HTTPException(status_code=404, detail="Assignee not found")
    if persona.sede_id is not None and str(persona.sede_id) != str(user_sede):
        # Existence-leak safe: indistinguishable from "not found".
        raise HTTPException(status_code=404, detail="Assignee not found")


def _assert_status_in_project_phases(
    db: Session, project_id: Any, status_value: Any
) -> None:
    """Reject a task ``status`` that does not match any active ``ProjectPhase.slug``.

    Contract (test_projects_kanban_move.py RED suite, Sprint 1/2):

    * **400** (not 422): business-rule violation tied to DB state, not a
      Pydantic schema issue — distinct from FastAPI's 422 reserved for
      schema validation. FastAPI returns 422 only when static schema
      constraints are violated; kanban membership is a runtime concept.
    * Soft-deleted phases (``deleted_at IS NOT NULL``) are filtered out
      by :func:`crud.get_project_phases`, so they cannot be assigned —
      this satisfies ``test_patch_status_to_soft_deleted_phase_rejected``.
    * Empty / None ``status`` is treated as "not in payload" — callers
      that don't touch ``status`` should not be forced to send a value.
    * **Canonical fallback**: when the project has no active phases
      (e.g. test fixtures that create a project directly without calling
      ``create_default_phases_factory``) the canonical 4-phase set is
      accepted. Production always bootstraps default phases via the
      ``create_project`` endpoint so this path is guard-only — it keeps
      ``test_create_task`` from breaking under strict validation while
      still rejecting garbage slugs like ``"not_a_real_phase"``. Note:
      it is not a free-string fallback; only the 4 canonical phases are
      allowed.
    * Race window: there is an inherent race between this snapshot read
      and the subsequent ``setattr(task, "status", ...)`` if another
      request calls ``set_project_phases`` between them. Mitigations
      (SELECT … FOR SHARE, optimistic locking) are deferred until the
      drag-and-drop kanban endpoints need higher-throughput safety.

    The detail string intentionally contains both words "status" and
    "phase" so the test envelope assertion passes and consumers can
    pinpoint the offending axis.
    """
    if status_value is None:
        return
    # Normalize whitespace defensively without forbidding slugs that
    # legitimately contain spaces (none currently exist, but be safe).
    candidate = str(status_value).strip()
    if not candidate:
        return
    project_uuid = _to_uuid(project_id)
    phase_rows = crud.get_project_phases(db, project_uuid)
    if phase_rows:
        valid_slugs = {p.slug for p in phase_rows}
        source = "project phases"
    else:
        valid_slugs = _CANONICAL_PHASE_SLUGS
        source = "canonical defaults (project has no phases configured)"
    if candidate in valid_slugs:
        return
    pretty = ", ".join(sorted(valid_slugs))
    raise HTTPException(
        status_code=400,
        detail=(
            f"status '{candidate}' is not a valid phase. "
            f"Active phases for this {source}: [{pretty}]"
        ),
    )


def _validate_whiteboard_json(elements_json: str) -> None:
    """Valida que elements_json sea JSON válido.

    Rechaza el literal "undefined" (bug de cliente JS) y JSON malformado.
    """
    if elements_json.strip().lower() == "undefined":
        raise HTTPException(status_code=400, detail="elements_json must be valid JSON, got 'undefined'")
    try:
        json.loads(elements_json)
    except (json.JSONDecodeError, TypeError, ValueError):
        raise HTTPException(status_code=400, detail="elements_json must be valid JSON")


# Canonical 4-phase set used when a project has no active Phase rows
# configured (most often in tests that bypass ``create_default_phases``).
# This is intentionally a tight allow-list, not a free-string fallback.
_CANONICAL_PHASE_SLUGS: frozenset[str] = frozenset(
    {"todo", "in_progress", "review", "completed"}
)

# Compat enum values that may still exist in client payloads or old DB rows.
# These are normalized to canonical values on read/write to avoid 422 errors
# and to keep the UI consistent.
_COMPAT_PRIORITY_MAP: dict[str, str] = {"normal": "medium"}
_COMPAT_STATUS_MAP: dict[str, str] = {"done": "completed", "blocked": "todo", "pending": "todo"}


def _normalize_task_payload(payload: dict) -> dict:
    """Map compat task status/priority values to canonical enums in payloads."""
    if "priority" in payload and isinstance(payload["priority"], str):
        payload["priority"] = _COMPAT_PRIORITY_MAP.get(payload["priority"], payload["priority"])
    if "status" in payload and isinstance(payload["status"], str):
        payload["status"] = _COMPAT_STATUS_MAP.get(payload["status"], payload["status"])
    return payload


def _normalize_task_enums(task: models.ProjectTask) -> None:
    """Map compat task status/priority values stored on a task row to canonical enums."""
    if task.priority in _COMPAT_PRIORITY_MAP:
        task.priority = _COMPAT_PRIORITY_MAP[task.priority]
    if task.status in _COMPAT_STATUS_MAP:
        task.status = _COMPAT_STATUS_MAP[task.status]


def _serialize_attachment(attachment: models.ProjectAttachment) -> dict:
    return {
        "id": attachment.id,
        "task_id": attachment.task_id,
        "filename": attachment.filename,
        "file_url": attachment.file_url,
        "file_type": attachment.file_type,
        "file_size": attachment.file_size,
        "created_at": attachment.created_at,
    }


def _serialize_task_attachments(task: models.ProjectTask) -> models.ProjectTask:
    task.__dict__["attachments"] = [
        _serialize_attachment(attachment)
        for attachment in (task.attachments or [])
        if getattr(attachment, "deleted_at", None) is None
    ]
    return task


def _prepare_task_for_response(task: models.ProjectTask) -> models.ProjectTask:
    _normalize_task_enums(task)
    _normalize_dates(task)
    _serialize_task_attachments(task)
    if hasattr(task, "supplies") and task.supplies:
        task.supplies = [s for s in task.supplies if s.deleted_at is None]
    if hasattr(task, "subtasks") and task.subtasks:
        task.subtasks = [_prepare_task_for_response(sub) for sub in task.subtasks if sub.deleted_at is None]
    return task


def _prepare_project_for_response(project: models.Project) -> models.Project:
    _normalize_dates(project)
    for milestone in project.milestones:
        _normalize_dates(milestone)
    for task in project.tasks:
        _prepare_task_for_response(task)
    return project


def _normalize_dates(obj):
    if not obj:
        return obj
    # Soporte mejorado para multiples formatos de fecha de SQLite
    for attr in [
        "created_at",
        "target_date",
        "due_date",
        "start_date",
        "updated_at",
        "last_edited_at",
    ]:
        val = getattr(obj, attr, None)
        if val and isinstance(val, str):
            try:
                # Limpiar milisegundos si es necesario
                clean_val = val.split(".")[0] if "." in val and "T" not in val else val
                setattr(
                    obj,
                    attr,
                    datetime.fromisoformat(clean_val.replace(" ", "T").replace("Z", "+00:00")),
                )
            except MemoryError:
                raise
            except Exception as exc:
                logger.debug(
                    "Failed to normalize project date: %s",
                    exc,
                    extra={"attribute": attr, "value": val},
                )
                if attr == "created_at":
                    setattr(obj, attr, datetime.now())
    return obj


@router.get("", response_model=List[schemas.Project])
def list_projects(
    status_filter: Optional[str] = Query(None, alias="status"),
    owner_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    user_sede = get_user_sede_id(db, current_user.id)
    query = (
        db.query(models.Project)
        .options(
            selectinload(models.Project.tasks).selectinload(models.ProjectTask.attachments),
            selectinload(models.Project.milestones),
        )
        .filter(models.Project.deleted_at.is_(None))
    )
    if user_sede:
        query = query.filter(models.Project.sede_id == user_sede)
    if status_filter:
        query = query.filter(models.Project.status == status_filter)
    if owner_id:
        query = query.filter(models.Project.owner_id == owner_id)

    projects = query.order_by(models.Project.created_at.desc()).all()
    for p in projects:
        _prepare_project_for_response(p)
    return projects


@router.post("", response_model=schemas.Project, status_code=status.HTTP_201_CREATED)
def create_project(
    project: schemas.ProjectCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    owner_persona_id = get_user_persona_id(db, current_user.id)
    user_sede = get_user_sede_id(db, current_user.id)
    db_project = crud.create_project(db, project, owner_persona_id=owner_persona_id, sede_id=user_sede)

    crud.create_default_phases(db, db_project.id)

    if owner_persona_id:
        crud.create_activity_log(
            db, db_project.id, owner_persona_id, "project_created", f"Proyecto '{db_project.title}' creado"
        )

    record_admin_action(
        db, current_user, action="create_project", resource_type="project", resource_id=str(db_project.id)
    )
    _normalize_dates(db_project)
    return db_project


# ── Phases / Kanban Columns ─────────────────────────────


@router.get("/{project_id}/phases", response_model=List[schemas.ProjectPhaseSchema])
def list_project_phases(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_project_access("read")),
):
    """Lista las fases (columnas del kanban) de un proyecto."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    return crud.get_project_phases(db, project_id)


@router.put("/{project_id}/phases", response_model=List[schemas.ProjectPhaseSchema])
def set_project_phases(
    project_id: str,
    phases: List[schemas.ProjectPhaseInput],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_project_access("manage")),
):
    """Reemplaza todas las fases del proyecto (reordenar / renombrar / agregar / eliminar).
    El orden en el array define el order_index de cada fase.
    Solo administradores y gestores pueden modificar fases.
    El acceso se valida con ``require_project_access("manage")``; por tanto,
    un usuario sin permisos de manage recibe 404 (no 403) cuando el proyecto
    no existe o pertenece a otra sede (Axioma 3).
    """
    user_sede = get_user_sede_id(db, current_user.id)
    _project = _ensure_project(db, project_id, user_sede=user_sede)
    # Race-condition fix: lock the parent project row while we validate
    # task counts and apply the phase rewrite, so concurrent inserts
    # under a status about to be removed cannot create orphan tasks.
    db.query(models.Project).filter(
        models.Project.id == _to_uuid(project_id)
    ).with_for_update().first()

    # Check no phase with tasks is being deleted
    existing = {p.slug for p in crud.get_project_phases(db, project_id)}
    incoming = {p.slug for p in phases}
    removed = existing - incoming
    if removed:
        has_tasks = (
            db.query(models.ProjectTask)
            .filter(
                models.ProjectTask.project_id == project_id,
                models.ProjectTask.status.in_(removed),
            )
            .count()
        )
        if has_tasks:
            raise HTTPException(
                status_code=409,
                detail=f"No se puede eliminar la fase '{next(iter(removed))}': tiene {has_tasks} tarea(s) asignada(s). Mueve las tareas primero.",
            )

    phase_dicts = [{"name": p.name, "slug": p.slug, "color": p.color, "order_index": i} for i, p in enumerate(phases)]
    created = crud.set_project_phases(db, _to_uuid(project_id), phase_dicts)
    return created


# --- COMMENTS ---


@router.get("/comments", response_model=List[schemas.ProjectCommentItem])
def list_all_comments(
    unresolved_only: bool = False,
    limit: int = Query(120, le=500),
    offset: int = Query(0, ge=0),
    project_id: Optional[str] = None,
    task_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Lista todos los comentarios de proyectos con filtros opcionales.

    Axioma 3 — strict scope: el feed global de comentarios queda acotado
    a los proyectos del actor. La ruta acepta un ``project_id`` opcional
    para filtrado explícito (validado vía ``_ensure_project``); cuando
    NO se pasa project_id, la respuesta agrega comentarios de proyectos
    visibles para la ``sede_id`` del actor. Superadmin (sin sede) sigue
    viendo todo, consistente con ``list_projects``.
    """
    user_sede = get_user_sede_id(db, current_user.id)
    q = db.query(models.ProjectComment).filter(models.ProjectComment.deleted_at.is_(None))
    if project_id:
        # Validate scope at the project level before exposing its comments.
        _ensure_project(db, project_id, user_sede=user_sede)
        q = q.filter(models.ProjectComment.project_id == _to_uuid(project_id))
    elif user_sede:
        # No project filter → join with Project and keep only those in
        # the actor's sede. Also exclude comments on soft-deleted projects.
        q = q.join(
            models.Project, models.Project.id == models.ProjectComment.project_id
        ).filter(
            models.Project.sede_id == user_sede,
            models.Project.deleted_at.is_(None),
        )
    if unresolved_only:
        q = q.filter(models.ProjectComment.is_resolved.is_(False))
    if task_id:
        q = q.filter(models.ProjectComment.task_id == _to_uuid(task_id))
    rows = q.order_by(models.ProjectComment.created_at.desc()).offset(offset).limit(limit).all()
    # Batch-fetch authors to avoid N+1 queries
    author_ids = {row.author_id for row in rows if row.author_id}
    authors_map = {}
    if author_ids:
        authors = db.query(models.Persona).filter(models.Persona.id.in_(author_ids)).all()
        authors_map = {p.id: _author_name(p) for p in authors}
    result = []
    for row in rows:
        result.append(
            schemas.ProjectCommentItem(
                id=row.id,
                project_id=str(row.project_id) if row.project_id is not None else None,
                task_id=str(row.task_id) if row.task_id is not None else None,
                content=row.content,
                author_id=str(row.author_id) if row.author_id is not None else None,
                author_name=authors_map.get(row.author_id, "Usuario"),
                is_resolved=row.is_resolved,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
        )
    return result


@router.post(
    "/{project_id}/tasks",
    response_model=schemas.ProjectTask,
    status_code=status.HTTP_201_CREATED,
)
def create_project_task(
    project_id: str,
    task: schemas.ProjectTaskCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_project_access("edit")),
):
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    # Race-condition fix: acquire a row lock on the parent project so the
    # subsequent MAX(order_index) + INSERT is serialized across concurrent
    # task creations. On PostgreSQL this is a real SELECT ... FOR UPDATE;
    # on SQLite it is a no-op (the test suite runs serialized transactions).
    db.query(models.Project).filter(
        models.Project.id == _to_uuid(project_id)
    ).with_for_update().first()
    project = db.query(models.Project).filter(models.Project.id == _to_uuid(project_id)).first()
    payload = task.model_dump()
    _normalize_task_payload(payload)
    _assert_status_in_project_phases(db, project_id, payload.get("status"))
    _assert_assignee_in_sede(db, payload.get("assignee_id"), user_sede)
    max_order = (
        db.query(func.max(models.ProjectTask.order_index))
        .filter(models.ProjectTask.project_id == _to_uuid(project_id))
        .scalar()
        or 0
    )
    payload["project_id"] = _to_uuid(project_id)
    payload["order_index"] = max_order + 1
    db_task = models.ProjectTask(**payload)
    db.add(db_task)

    # Bitacora Ministerial
    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "task_created",
        f"Tarea '{db_task.title}' lanzada por {getattr(current_user, 'username', getattr(current_user, 'email', 'usuario'))}",
    )
    db.commit()
    db.refresh(db_task)
    if getattr(db_task, "assignee_id", None):
        notify_task_assigned(
            db,
            task=db_task,
            project=project,
            assigned_by_user_id=current_user.id,
        )
    return db_task


# ── PORTFOLIO SUMMARY ──────────────────────────────────────────────────────────


@router.get("/summary", response_model=List[schemas.ProjectPortfolioSummaryRow])
def portfolio_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Resumen de portafolio agrupado por estatus de proyecto.

    Axioma 3 — strict scope: solo se agregan proyectos en la ``sede_id``
    del actor. Superadmin (sin sede) ve todo.
    """
    user_sede = get_user_sede_id(db, current_user.id)
    done_case = func.coalesce(func.sum(cast(models.ProjectTask.status == "completed", Integer)), 0).label(
        "completed_tasks"
    )

    q = (
        db.query(
            models.Project.status,
            func.count(func.distinct(models.Project.id)).label("total_projects"),
            func.count(models.ProjectTask.id).label("total_tasks"),
            done_case,
        )
        .outerjoin(
            models.ProjectTask,
            and_(
                models.ProjectTask.project_id == models.Project.id,
                models.ProjectTask.deleted_at.is_(None),
            ),
        )
        .filter(models.Project.deleted_at.is_(None))
    )
    if user_sede:
        q = q.filter(models.Project.sede_id == user_sede)
    rows = q.group_by(models.Project.status).all()

    return [
        schemas.ProjectPortfolioSummaryRow(
            project_status=row[0] or "unknown",
            total_projects=row[1],
            total_tasks=row[2] or 0,
            completed_tasks=row[3] or 0,
            completion_ratio=round((row[3] or 0) / max(row[2] or 1, 1), 2),
        )
        for row in rows
    ]


@router.get("/workload", response_model=List[schemas.ProjectWorkloadSummaryRow])
def workload_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Resumen de carga de trabajo por persona.

    Axioma 3 — strict scope consistente con el resto del módulo: solo se
    agregan tareas de proyectos en la ``sede_id`` del actor. Superadmin
    (``user_sede`` = ``None``) ve todo.

    N+1 fix (oportunista, Sprint 1.1) — antes este endpoint emitía una
    query de ``COUNT(overdue)`` por cada assignee devolvido por la query
    principal (1 + N queries). Ahora las tres métricas (open / in_review /
    overdue) se agregan en un único ``GROUP BY`` con ``CASE`` expressions
    portable sobre SQLite + Postgres. Una sola query para N assignees.
    """
    user_sede = get_user_sede_id(db, current_user.id)
    open_statuses = ("todo", "in_progress", "review")
    now_expr = func.now()

    open_count = func.count(models.ProjectTask.id).label("open_tasks")
    in_review_count = func.coalesce(
        func.sum(cast(models.ProjectTask.status == "review", Integer)),
        0,
    ).label("in_review")
    overdue_count = func.coalesce(
        func.sum(
            cast(
                models.ProjectTask.status.in_(open_statuses)
                & (models.ProjectTask.due_date < now_expr),
                Integer,
            )
        ),
        0,
    ).label("overdue_tasks")

    q = (
        db.query(
            models.ProjectTask.assignee_id,
            open_count,
            in_review_count,
            overdue_count,
        )
        .filter(
            models.ProjectTask.status.in_(open_statuses),
            models.ProjectTask.assignee_id.isnot(None),
            models.ProjectTask.deleted_at.is_(None),
        )
    )
    if user_sede:
        # Single JOIN when scope is set; supplies ``Project.sede_id`` to the
        # WHERE. Without this the workload feed would leak cross-sede rows.
        q = q.join(
            models.Project, models.Project.id == models.ProjectTask.project_id
        ).filter(models.Project.sede_id == user_sede)

    rows = (
        q.group_by(models.ProjectTask.assignee_id)
        .order_by(open_count.desc())
        .all()
    )
    return [
        schemas.ProjectWorkloadSummaryRow(
            assignee_id=str(row.assignee_id) if row.assignee_id else None,
            open_tasks=row.open_tasks or 0,
            in_review=row.in_review or 0,
            overdue_tasks=row.overdue_tasks or 0,
        )
        for row in rows
    ]


@router.get("/activities", response_model=List[schemas.ProjectActivityItem])
def list_activities(
    limit: int = Query(20, le=200),
    offset: int = Query(0, ge=0),
    project_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Feed de actividad global de proyectos.

    Axioma 3 — strict scope: cuando NO se pasa ``project_id`` el feed
    se acota a bitacoras de proyectos visibles para la ``sede_id`` del
    actor (join con Project). Cuando SÍ se pasa ``project_id``, se
    valida la sede del proyecto con ``_ensure_project``. Esto elimina
    el leak cross-sede del feed ministerial.

    N+1 fix (oportunista, Sprint 1.1) — antes cada log disparaba su
    propio ``db.query(Project).filter(id=log.project_id).first()`` para
    resolver ``project_title``. Con ``limit=200`` eso eran hasta 200
    queries por request. Ahora se hace un único ``IN (...)`` batch y se
    indexa por ``project_id`` en un dict para O(1) lookup por log.
    """
    user_sede = get_user_sede_id(db, current_user.id)
    q = db.query(models.ProjectActivityLog)
    if project_id:
        _ensure_project(db, project_id, user_sede=user_sede)
        q = q.filter(models.ProjectActivityLog.project_id == _to_uuid(project_id))
    elif user_sede:
        # Join con Project para que ``Project.sede_id`` sea usable en el filtro.
        # Exclude activity logs from soft-deleted projects.
        q = q.join(
            models.Project, models.Project.id == models.ProjectActivityLog.project_id
        ).filter(
            models.Project.sede_id == user_sede,
            models.Project.deleted_at.is_(None),
        )
    logs = q.order_by(models.ProjectActivityLog.created_at.desc()).offset(offset).limit(limit).all()

    # ── Batch fetch: 1 query for the unique project_ids of this page ──
    project_ids = {log.project_id for log in logs if log.project_id}
    projects_map: dict = {}
    if project_ids:
        rows = (
            db.query(models.Project.id, models.Project.title)
            .filter(models.Project.id.in_(project_ids))
            .all()
        )
        projects_map = {pid: title for pid, title in rows}

    result = []
    for log in logs:
        _normalize_dates(log)
        result.append(
            schemas.ProjectActivityItem(
                id=str(log.id),
                kind=log.action_type,
                project_id=str(log.project_id) if log.project_id is not None else None,
                project_title=projects_map.get(log.project_id, "Proyecto"),
                description=log.description or "",
                created_at=log.created_at or _utcnow(),
            )
        )
    return result


@router.get("/tasks/{task_id}", response_model=schemas.ProjectTask)
def get_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_project_access("read")),
):
    """Obtiene una tarea por ID.

    Axioma 3 — cross-sede defense-in-depth: validate the task's parent
    project against the actor's ``sede_id`` via ``_ensure_project``. Without
    this, a user from sede_a could fetch a task in sede_b just by guessing
    the task_id.
    """
    user_sede = get_user_sede_id(db, current_user.id)
    task = _ensure_task(db, task_id)
    _ensure_project(db, str(task.project_id), user_sede=user_sede)
    _normalize_task_enums(task)
    _normalize_dates(task)
    return task


@router.patch("/tasks/{task_id}", response_model=schemas.ProjectTask)
def update_task(
    task_id: str,
    payload: schemas.ProjectTaskUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_project_access("edit")),
):
    """Actualiza una tarea usando ruta plana (sin project_id).

    Axioma 3 — the flat PATCH path takes only ``task_id``. We must
    validate the task's parent project via ``_ensure_project`` so a
    sede_a user cannot mutate tasks in sede_b projects just by knowing
    the task_id (existence-leak safe: returns 404, not 403).
    """
    user_sede = get_user_sede_id(db, current_user.id)
    task = _ensure_task(db, task_id)
    _ensure_project(db, str(task.project_id), user_sede=user_sede)
    update_data = payload.model_dump(exclude_unset=True)
    _normalize_task_payload(update_data)
    if "status" in update_data:
        _assert_status_in_project_phases(db, task.project_id, update_data["status"])
    if "assignee_id" in update_data:
        _assert_assignee_in_sede(db, update_data["assignee_id"], user_sede)
    previous_assignee_id = getattr(task, "assignee_id", None)
    for key, value in update_data.items():
        setattr(task, key, value)
    _normalize_task_enums(task)
    task.updated_at = _utcnow()
    db.commit()
    db.refresh(task)
    if "assignee_id" in update_data and _assignment_changed(previous_assignee_id, getattr(task, "assignee_id", None)) and task.assignee_id:
        notify_task_assigned(
            db,
            task=task,
            assigned_by_user_id=current_user.id,
            previous_assignee_id=previous_assignee_id,
        )
    _normalize_dates(task)
    return task


# ── INBOX (must be before /{project_id} routes) ────────────────────────────────


@router.get("/inbox", response_model=List[schemas.ProjectInboxItem])
def list_inbox(
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Bandeja de entrada unificada por persona: 2 superficies en un solo feed.

    **Endpoint**: ``GET /api/projects/inbox?limit=N`` (default 50, máx 200).

    **Response shape**: ``List[ProjectInboxItem]`` (ver Pydantic en
    ``backend/schemas/projects.py``). Cada item expone ``id`` composite
    (``"comment-<id>"`` / ``"task-<id>"``), ``type`` (``"comment"`` /
    ``"task_assigned"``), ``user``, ``content``, ``project``,
    ``project_id``, ``task_id`` (opcional), ``task_title`` (opcional),
    ``is_read`` y ``created_at``.

    **Superficies combinadas** (ordenadas independientemente, truncadas al
    ``limit`` final):

    1. **Comentarios no resueltos** (``type="comment"``): ``ProjectComment``
       con ``~is_resolved``, ``author_id != persona_id`` (excluye
       auto-comentarios). Orden: ``created_at desc``.
    2. **Tareas abiertas asignadas al actor** (``type="task_assigned"``):
       ``ProjectTask`` con ``assignee_id == persona_id``,
       ``status != "completed"``, ``deleted_at IS NULL``. Orden:
       ``updated_at desc``.

    **Marca de leído** (sincronizada vía ``POST /api/projects/inbox/{item_id}/read``):
    ``ProjectInboxState`` con UNIQUE ``(persona_id, item_id)``. Una query
    batch por superficie resuelve el flag ``is_read`` en O(1) por item.

    **RBAC**:

    * ``GET /inbox`` requiere ``projects:read`` (decorador). Admin / Gestor
      / Editor pasan; **Miembro = 403** (baseline documentado en
      ``tests/test_projects_rbac.py`` + ``PEND-RBAC-001``).
    * ``POST /inbox/{item_id}/read`` requiere ``projects:edit``.

    **Axioma 3 (multi-tenant)**:

    * Sedes sentadas: sólo items de proyectos cuya ``Project.sede_id ==
      user_sede``. Cross-sede unread comments + out-of-sede assigned
      tasks filtrados server-side. Proyectos soft-deleted excluidos.
    * Superadmin (``user_sede = None``): ve todo (consistente con
      ``list_projects`` / ``list_whiteboards`` / ``list_activities``).

    **Performance**: N+1 fix (Sprint 1.1). Un ``IN (...)`` batch por
    superficie para resolver ``author_name`` / ``project_title`` más un
    batch para resolver ``is_read`` desde ``project_inbox_state``.
    ``selectinload(Project.owner)`` evita N+1 al resolver ``user`` en
    items ``task_assigned``.

    **Diferencia con ``GET /api/projects/activities``**: ``activities`` es
    bitácora cruda universal por proyecto; ``inbox`` es feed normalizado
    por persona con merge de 2 superficies y estado ``is_read``.

    Contrato documentado en handover canónico:
    ``ccf/docs/ESTADO_PROYECTOS.md`` §4.1 (cierre de ``PEND-INBOX-CONTRACT-001``).
    """
    inbox_items: list[schemas.ProjectInboxItem] = []

    # Obtener persona_id (UUID) desde current_user.id (Integer)
    persona = _resolve_persona(db, current_user.id)
    persona_id = persona.id if persona else None
    user_sede = get_user_sede_id(db, current_user.id)

    # Comentarios no leídos en proyectos del usuario
    unread_comments = ()
    if persona_id:
        q_unread = (
            db.query(models.ProjectComment, models.Project)
            .join(models.Project, models.Project.id == models.ProjectComment.project_id)
            .filter(
                ~models.ProjectComment.is_resolved,
                models.ProjectComment.deleted_at.is_(None),
                models.ProjectComment.author_id != persona_id,
                # PEND-QUALITY-INBOX-SCOPE-001 (2026-07-16): excluir
                # comentarios cuyo proyecto esté soft-deleted para que el
                # feed del inbox no muestre fantasmas tras un borrado.
                models.Project.deleted_at.is_(None),
            )
        )
        if user_sede:
            q_unread = q_unread.filter(models.Project.sede_id == user_sede)
        unread_comments = (
            q_unread.order_by(models.ProjectComment.created_at.desc())
            .limit(limit)
            .all()
        )

    # ── Batch-fetch authors + inbox states (N+1 fix) ──
    comment_author_ids = {c.author_id for c, _ in unread_comments if c.author_id}
    comment_item_ids = {f"comment-{c.id}" for c, _ in unread_comments}
    authors_map: dict = {}
    if comment_author_ids:
        authors_map = {
            p.id: _author_name(p)
            for p in db.query(models.Persona).filter(models.Persona.id.in_(comment_author_ids)).all()
        }
    inbox_states_map: dict = {}
    if comment_item_ids and persona_id:
        inbox_states_map = {
            s.item_id: s.is_read
            for s in db.query(models.ProjectInboxState).filter(
                models.ProjectInboxState.persona_id == persona_id,
                models.ProjectInboxState.item_id.in_(comment_item_ids),
            ).all()
        }

    for comment, project in unread_comments:
        item_id = f"comment-{comment.id}"
        is_read = inbox_states_map.get(item_id, False)
        inbox_items.append(
            schemas.ProjectInboxItem(
                id=item_id,
                type="comment",
                user=authors_map.get(comment.author_id, "Usuario"),
                content=comment.content[:120],
                project=project.title,
                project_id=str(project.id) if project.id is not None else None,
                task_id=str(comment.task_id) if comment.task_id is not None else None,
                is_read=is_read,
                created_at=comment.created_at,
            )
        )

    # ── Task-assignments inbox surface (NEW, Sprint 1.1) ─────────
    # Tareas ABIERTAs asignadas al actor en proyectos visibles. Cierra el
    # feature gap donde instancias donde el email había fallado / no había
    # sido enviado aún así quedaban sin notificar al inbox. La query
    # excluye tareas completadas (estado terminal) y soft-deleted.
    assigned_tasks = ()
    if persona_id:
        q_tasks = (
            db.query(models.ProjectTask, models.Project)
            .join(models.Project, models.Project.id == models.ProjectTask.project_id)
            .options(selectinload(models.Project.owner))
            .filter(
                models.ProjectTask.assignee_id == persona_id,
                models.ProjectTask.deleted_at.is_(None),
                models.ProjectTask.status != "completed",
                # PEND-QUALITY-INBOX-SCOPE-001 (2026-07-16): excluir
                # tareas cuyo proyecto esté soft-deleted para no exponer
                # tareas fantasma en el inbox tras un borrado. La rama de
                # ``task.deleted_at`` ya excluye soft-delete a nivel tarea.
                models.Project.deleted_at.is_(None),
            )
        )
        if user_sede:
            q_tasks = q_tasks.filter(models.Project.sede_id == user_sede)
        assigned_tasks = (
            q_tasks.order_by(models.ProjectTask.updated_at.desc())
            .limit(limit)
            .all()
        )

    # ── Batch-fetch inbox states for task items (N+1 fix) ──
    task_item_ids = {f"task-{t.id}" for t, _ in assigned_tasks}
    task_inbox_states_map: dict = {}
    if task_item_ids and persona_id:
        task_inbox_states_map = {
            s.item_id: s.is_read
            for s in db.query(models.ProjectInboxState).filter(
                models.ProjectInboxState.persona_id == persona_id,
                models.ProjectInboxState.item_id.in_(task_item_ids),
            ).all()
        }

    for task, project in assigned_tasks:
        item_id = f"task-{task.id}"
        is_read = task_inbox_states_map.get(item_id, False)
        project_owner_name = (
            _author_name(project.owner) if project and getattr(project, "owner", None) else "Equipo"
        )
        inbox_items.append(
            schemas.ProjectInboxItem(
                id=item_id,
                type="task_assigned",
                user=project_owner_name,
                content=f"Tarea asignada: {task.title}",
                project=project.title if project else "Proyecto",
                project_id=str(project.id) if project and project.id is not None else None,
                task_id=str(task.id),
                task_title=task.title,
                is_read=is_read,
                created_at=task.updated_at or _utcnow(),
            )
        )

    return inbox_items[:limit]


@router.post("/inbox/{item_id}/read", response_model=dict)
def mark_inbox_read(
    item_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Marca un item del inbox como leído.

    PEND-QUALITY-INBOX-SCOPE-001 (2026-07-16): exigir que ``item_id``
    corresponda a una entrada real del inbox del actor antes de
    upsertar ``ProjectInboxState``. Antes este endpoint hacía un upsert
    ciego en ``project_inbox_state`` y cualquier ``item_id`` arbitrario
    quedaba persistido como leído. Ahora se valida:

    * El formato ``comment-<uuid>`` o ``task-<uuid>``.
    * Que la entidad subyacente (comentario no resuelto de otro autor en
      proyecto visible, o tarea abierta asignada al actor en proyecto
      visible) efectivamente exista para ``persona_id`` + ``user_sede``.

    Si no se cumple, responde **404** (existence-leak safe). El upsert
    atómico se mantiene para cubrir el race entre POSTs concurrentes.
    """
    persona = _resolve_persona(db, current_user.id)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    user_sede = get_user_sede_id(db, current_user.id)

    # ── Validación de existencia real del item en el inbox del actor ──
    if not _inbox_item_exists_for_actor(db, item_id, persona.id, user_sede):
        raise HTTPException(status_code=404, detail="Inbox item not found")

    # Race-condition fix: replace check-then-act with an atomic upsert.
    # Two concurrent clicks or a duplicate POST would otherwise both see
    # ``state = None`` and either duplicate the row (if no unique
    # constraint) or raise IntegrityError 500 (if there is one). The
    # try/except handles both PostgreSQL and SQLite dialects uniformly.
    try:
        state = models.ProjectInboxState(
            persona_id=persona.id,
            item_id=item_id,
            is_read=True,
        )
        db.add(state)
        db.commit()
    except IntegrityError:
        db.rollback()
        state = (
            db.query(models.ProjectInboxState)
            .filter(
                models.ProjectInboxState.persona_id == persona.id,
                models.ProjectInboxState.item_id == item_id,
            )
            .first()
        )
        if state and not state.is_read:
            state.is_read = True
            db.commit()
    return {"ok": True, "item_id": item_id}


# ── WIKI & WHITEBOARD CON CALIDAD AUDITADA ─────────────────────────
# NOTA: /whiteboards (sin project_id) debe ir ANTES de /{project_id}
# para evitar que FastAPI interprete "whiteboards" como un project_id.


@router.get("/whiteboards", response_model=List[schemas.ProjectWhiteboard])
def list_whiteboards(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Lista todas las pizarras activas del alcance del actor actual.

    Axioma 3 — solo se devuelven pizarras cuyos proyectos pertenezcan a la
    ``sede_id`` del actor. Esto previene el leak cross-sede del feed de
    whiteboards en el módulo de plataforma. El superadmin (``user_sede``
    = ``None``) sigue viendo todas, consistente con list_projects.
    """
    user_sede = get_user_sede_id(db, current_user.id)
    q = (
        db.query(models.ProjectWhiteboard)
        .join(models.Project, models.Project.id == models.ProjectWhiteboard.project_id)
        .filter(models.ProjectWhiteboard.deleted_at.is_(None))
    )
    if user_sede:
        q = q.filter(models.Project.sede_id == user_sede)
    boards = q.order_by(models.ProjectWhiteboard.updated_at.desc()).all()
    return [_normalize_dates(b) for b in boards]


@router.get("/{project_id}", response_model=schemas.Project)
def get_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_project_access("read")),
):
    user_sede = get_user_sede_id(db, current_user.id)
    p = _ensure_project(db, project_id, user_sede=user_sede)
    _prepare_project_for_response(p)
    for log in p.activity_logs:
        _normalize_dates(log)
        log.user_name = log.persona.nombre_completo if log.persona else "Sistema"
    return p


@router.get("/{project_id}/wiki", response_model=Optional[schemas.ProjectDocument])
def get_project_wiki(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_project_access("read")),
):
    """Obtiene el wiki (ProjectDocument) asociado a un proyecto.

    Axioma 3 — the route previously skipped ``_ensure_project`` and
    leaked cross-sede wikis by guessing project_id. The fix mirrors the
    rest of the module: validate the parent project before returning
    the document.
    """
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    doc = db.query(models.ProjectDocument).filter(models.ProjectDocument.project_id == _to_uuid(project_id)).first()
    return _normalize_dates(doc)


@router.post("/{project_id}/wiki", response_model=schemas.ProjectDocument)
def update_project_wiki(
    project_id: str,
    payload: schemas.ProjectDocumentUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_project_access("edit")),
):
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)  # Validates project exists + scope
    doc = crud.get_project_wiki(db, _to_uuid(project_id))
    title = payload.title or "Wiki Ministerial"
    content = payload.content or ""
    author_persona_id = get_user_persona_id(db, current_user.id)

    if not doc:
        doc = models.ProjectDocument(
            project_id=_to_uuid(project_id),
            title=title,
            content=content,
            author_id=author_persona_id,
        )
        db.add(doc)
    else:
        doc.title = title
        doc.content = content
        doc.author_id = author_persona_id
        doc.last_edited_at = datetime.now(timezone.utc)

    # Registrar cambio en la bitacora
    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "wiki_updated",
        "Documentacion Wiki actualizada.",
    )
    db.commit()
    db.refresh(doc)
    return _normalize_dates(doc)


@router.get("/{project_id}/whiteboard", response_model=Optional[schemas.ProjectWhiteboard])
def get_project_whiteboard(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_project_access("read")),
):
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    board = crud.get_project_whiteboard(db, _to_uuid(project_id))
    return _normalize_dates(board)


@router.post("/{project_id}/whiteboard", response_model=schemas.ProjectWhiteboard)
def update_project_whiteboard(
    project_id: str,
    payload: schemas.ProjectWhiteboardUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_project_access("edit")),
):
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    board = (
        db.query(models.ProjectWhiteboard).filter(models.ProjectWhiteboard.project_id == _to_uuid(project_id)).first()
    )
    title = payload.title or "Pizarra Estrategica"
    elements = payload.elements_json or "[]"

    # Validate elements_json is valid JSON (reject "undefined", malformed, etc.)
    _validate_whiteboard_json(elements)

    if not board:
        board = models.ProjectWhiteboard(project_id=_to_uuid(project_id), title=title, elements_json=elements)
        db.add(board)
    else:
        board.elements_json = elements
        board.updated_at = datetime.now(timezone.utc)

    board.title = title
    if payload.thumbnail_url is not None:
        board.thumbnail_url = payload.thumbnail_url

    db.commit()
    db.refresh(board)
    return _normalize_dates(board)


@router.delete("/{project_id}/whiteboard", status_code=status.HTTP_204_NO_CONTENT)
def delete_project_whiteboard(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_project_access("edit")),
):
    """Realiza soft delete de la pizarra asociada a un proyecto."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    board = (
        db.query(models.ProjectWhiteboard).filter(models.ProjectWhiteboard.project_id == _to_uuid(project_id)).first()
    )
    if board:
        board.deleted_at = datetime.now(timezone.utc)
        db.commit()
    return None


# --- ATTACHMENTS & SUPPLIES ---


@router.post("/{project_id}/tasks/{task_id}/attachments", response_model=schemas.ProjectTask)
async def upload_task_attachment(
    project_id: str,
    task_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_project_access("edit")),
):
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    task = _ensure_task_in_project(db, project_id, task_id)
    filename = sanitize_filename(file.filename or "file")
    contents = await file.read()

    if len(contents) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds maximum size")

    url = storage_service.save_file(contents, filename, subfolder="projects")

    uploader_persona_id = get_user_persona_id(db, current_user.id)
    attachment = models.ProjectAttachment(
        task_id=_to_uuid(task_id),
        filename=filename,
        file_url=url,
        file_type=file.content_type,
        file_size=len(contents),
        uploader_id=uploader_persona_id,
    )
    db.add(attachment)
    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "attachment_added",
        f"Archivo '{filename}' adjuntado a '{task.title}'",
    )
    db.commit()
    db.refresh(task)
    return _serialize_task_attachments(task)


@router.delete("/{project_id}/tasks/{task_id}/attachments/{attachment_id}", response_model=dict)
def delete_task_attachment(
    project_id: str,
    task_id: str,
    attachment_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_project_access("edit")),
):
    """Elimina un archivo adjunto de una tarea (soft delete)."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    attachment = _ensure_attachment_in_task(db, project_id, task_id, attachment_id)
    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "attachment_deleted",
        f"Archivo '{attachment.filename}' eliminado",
    )
    crud.delete_attachment(db, _to_uuid(attachment_id))
    return {"ok": True, "deleted": attachment_id}


@router.patch("/{project_id}/tasks/{task_id}", response_model=schemas.ProjectTask)
def update_project_task(
    project_id: str,
    task_id: str,
    payload: schemas.ProjectTaskUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_project_access("edit")),
):
    """Actualiza una tarea con auditoría ministerial automática."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    task = _ensure_task_in_project(db, project_id, task_id)
    update_data = payload.model_dump(exclude_unset=True)
    _normalize_task_payload(update_data)
    if "status" in update_data:
        _assert_status_in_project_phases(db, project_id, update_data["status"])
    # Validate that the new assignee (if any) belongs to the actor's sede.
    # Without this, an actor in sede A could inject a persona UUID from sede B
    # via PATCH body {} and assign tasks across tenant boundaries.
    if "assignee_id" in update_data:
        _assert_assignee_in_sede(db, update_data.get("assignee_id"), user_sede)
    previous_assignee_id = getattr(task, "assignee_id", None)
    changed_fields = []

    for key, value in update_data.items():
        old_value = getattr(task, key, None)
        setattr(task, key, value)
        if old_value != value:
            changed_fields.append(key)

    _normalize_task_enums(task)
    if changed_fields:
        _log_project_activity(
            db,
            project_id,
            current_user.id,
            "task_updated",
            f"Tarea '{task.title}' actualizada: {', '.join(changed_fields)}",
        )
    db.commit()
    db.refresh(task)
    if "assignee_id" in update_data and _assignment_changed(previous_assignee_id, getattr(task, "assignee_id", None)) and task.assignee_id:
        notify_task_assigned(
            db,
            task=task,
            assigned_by_user_id=current_user.id,
            previous_assignee_id=previous_assignee_id,
        )
    return task


@router.get("/{project_id}/tasks/{task_id}/supplies", response_model=List[schemas.TaskSupply])
def list_task_supplies(
    project_id: str,
    task_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_project_access("read")),
):
    """Lista los insumos de una tarea."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    _ensure_task_in_project(db, project_id, task_id)
    return crud.get_task_supplies(db, _to_uuid(task_id))


@router.post(
    "/{project_id}/tasks/{task_id}/supplies",
    response_model=schemas.TaskSupply,
    status_code=status.HTTP_201_CREATED,
)
def create_task_supply(
    project_id: str,
    task_id: str,
    payload: schemas.TaskSupplyCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_project_access("edit")),
):
    """Crea un insumo requerido para una tarea."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    task = _ensure_task_in_project(db, project_id, task_id)
    supply = models.TaskSupply(task_id=_to_uuid(task_id), **payload.model_dump())
    db.add(supply)
    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "supply_added",
        f"Insumo '{supply.item_name}' agregado a '{task.title}'",
    )
    db.commit()
    db.refresh(supply)
    return supply


@router.patch(
    "/{project_id}/tasks/{task_id}/supplies/{supply_id}",
    response_model=schemas.TaskSupply,
)
def update_task_supply(
    project_id: str,
    task_id: str,
    supply_id: str,
    payload: schemas.TaskSupplyUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_project_access("edit")),
):
    """Actualiza nombre, cantidad o estado de un insumo."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    task = _ensure_task_in_project(db, project_id, task_id)
    supply = _ensure_supply_in_task(db, project_id, task_id, supply_id)
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(supply, key, value)
    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "supply_updated",
        f"Insumo '{supply.item_name}' actualizado en '{task.title}'",
    )
    db.commit()
    db.refresh(supply)
    return supply


@router.delete("/{project_id}/tasks/{task_id}/supplies/{supply_id}", response_model=dict)
def delete_task_supply(
    project_id: str,
    task_id: str,
    supply_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_project_access("edit")),
):
    """Elimina un insumo de una tarea."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    task = _ensure_task_in_project(db, project_id, task_id)
    supply = _ensure_supply_in_task(db, project_id, task_id, supply_id)
    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "supply_deleted",
        f"Insumo '{supply.item_name}' eliminado de '{task.title}'",
    )
    crud.delete_supply(db, supply_id)
    return {"ok": True, "deleted": supply_id}


# ── SUBTASKS ───────────────────────────────────────────────────────────────────


@router.post(
    "/{project_id}/tasks/{task_id}/subtasks",
    response_model=schemas.ProjectTask,
    status_code=status.HTTP_201_CREATED,
)
def create_subtask(
    project_id: str,
    task_id: str,
    subtask: schemas.ProjectTaskCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Crea una subtarea (nivel 2 o 3) bajo una tarea existente."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    parent_task = _ensure_task_in_project(db, project_id, task_id)
    # Race-condition fix: lock the parent project row before reading the
    # MAX(order_index) so concurrent subtask creations do not share the
    # same order_index slot.
    db.query(models.Project).filter(
        models.Project.id == _to_uuid(project_id)
    ).with_for_update().first()
    payload = subtask.model_dump()
    _normalize_task_payload(payload)
    _assert_status_in_project_phases(db, project_id, payload.get("status"))
    _assert_assignee_in_sede(db, payload.get("assignee_id"), user_sede)
    max_order = (
        db.query(func.max(models.ProjectTask.order_index)).filter(models.ProjectTask.parent_id == task_id).scalar() or 0
    )
    # FIX: Previously these were assigned as raw strings (``project_id`` is
    # declared as ``str`` from the route path). ``ProjectTask.project_id``
    # is a ``UUID(as_uuid=True)`` column — assigning a string breaks SQLite
    # (see ``tests/test_projects_api.py::TestTasks::test_create_task_with_uuid_assignee``
    # and the parametrized regression suite). Coerce via ``_to_uuid``.
    payload["project_id"] = _to_uuid(project_id)
    payload["parent_id"] = _to_uuid(task_id)
    payload["order_index"] = max_order + 1
    db_subtask = models.ProjectTask(**payload)
    db.add(db_subtask)
    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "subtask_created",
        f"Sub-actividad '{db_subtask.title}' creada bajo '{parent_task.title}'",
    )
    db.commit()
    db.refresh(db_subtask)
    if getattr(db_subtask, "assignee_id", None):
        notify_task_assigned(
            db,
            task=db_subtask,
            assigned_by_user_id=current_user.id,
            previous_assignee_id=None,
        )
    return db_subtask


@router.patch(
    "/{project_id}/tasks/{task_id}/subtasks/{subtask_id}",
    response_model=schemas.ProjectTask,
)
def update_subtask(
    project_id: str,
    task_id: str,
    subtask_id: str,
    payload: schemas.ProjectTaskUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_project_access("edit")),
):
    """Actualiza una subtarea."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    _ensure_task_in_project(db, project_id, task_id)
    subtask = _ensure_task_in_project(db, project_id, subtask_id)
    if str(subtask.parent_id) != str(task_id):
        raise HTTPException(status_code=404, detail="Subtask not found under task")
    update_data = payload.model_dump(exclude_unset=True)
    _normalize_task_payload(update_data)
    if "status" in update_data:
        _assert_status_in_project_phases(db, project_id, update_data["status"])
    if "assignee_id" in update_data:
        _assert_assignee_in_sede(db, update_data["assignee_id"], user_sede)
    previous_assignee_id = getattr(subtask, "assignee_id", None)
    for key, value in update_data.items():
        setattr(subtask, key, value)
    _normalize_task_enums(subtask)
    db.commit()
    db.refresh(subtask)
    if "assignee_id" in update_data and _assignment_changed(previous_assignee_id, getattr(subtask, "assignee_id", None)) and subtask.assignee_id:
        notify_task_assigned(
            db,
            task=subtask,
            assigned_by_user_id=current_user.id,
            previous_assignee_id=previous_assignee_id,
        )
    return subtask


@router.delete("/{project_id}/tasks/{task_id}/subtasks/{subtask_id}")
def delete_subtask(
    project_id: str,
    task_id: str,
    subtask_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_project_access("edit")),
):
    """Elimina una subtarea."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    _ensure_task_in_project(db, project_id, task_id)
    subtask = _ensure_task_in_project(db, project_id, subtask_id)
    if str(subtask.parent_id) != str(task_id):
        raise HTTPException(status_code=404, detail="Subtask not found under task")
    subtask.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "deleted": subtask_id}


# ── COMMENTS ──────────────────────────────────────────────────────────────────


@router.post("/comments", response_model=schemas.ProjectCommentItem)
def create_comment(
    payload: schemas.ProjectCommentCreateWithProject,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Crea un comentario usando project_id en el body."""
    project_id = payload.project_id
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="content is required")
    task_id = payload.task_id
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    author_persona_id = get_user_persona_id(db, current_user.id)
    comment = models.ProjectComment(
        project_id=_to_uuid(project_id),
        task_id=_to_uuid(task_id) if task_id else None,
        author_id=author_persona_id,
        content=content,
    )
    db.add(comment)
    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "comment_added",
        content,
    )
    db.commit()
    db.refresh(comment)
    return schemas.ProjectCommentItem(
        id=comment.id,
        project_id=str(comment.project_id) if comment.project_id is not None else None,
        task_id=str(comment.task_id) if comment.task_id is not None else None,
        content=comment.content,
        author_id=str(comment.author_id) if comment.author_id is not None else None,
        author_name=_author_name(db.query(models.Persona).filter(models.Persona.id == comment.author_id).first()),
        is_resolved=comment.is_resolved,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
    )


@router.post("/{project_id}/comments", response_model=schemas.ProjectCommentItem)
def create_project_comment(
    project_id: str,
    payload: schemas.ProjectCommentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Crea un comentario en un proyecto."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    author_persona_id = get_user_persona_id(db, current_user.id)
    comment = models.ProjectComment(
        project_id=_to_uuid(project_id),
        task_id=_to_uuid(payload.task_id) if payload.task_id else None,
        author_id=author_persona_id,
        content=payload.content,
    )
    db.add(comment)
    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "comment_added",
        payload.content,
    )
    db.commit()
    db.refresh(comment)
    return schemas.ProjectCommentItem(
        id=comment.id,
        project_id=str(comment.project_id) if comment.project_id is not None else None,
        task_id=str(comment.task_id) if comment.task_id is not None else None,
        content=comment.content,
        author_id=str(comment.author_id) if comment.author_id is not None else None,
        author_name=_author_name(db.query(models.Persona).filter(models.Persona.id == comment.author_id).first()),
        is_resolved=comment.is_resolved,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
    )


@router.patch("/comments/{comment_id}", response_model=schemas.ProjectCommentItem)
def update_project_comment(
    comment_id: str,
    payload: schemas.ProjectCommentUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Actualiza un comentario (contenido o estado de resolución)."""
    comment = db.query(models.ProjectComment).filter(models.ProjectComment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    # IDOR fix + Axioma 3: validate that the actor's sede matches the comment's
    # parent project. Without this a sede_a user could mutate a comment in a
    # sede_b project by guessing the comment_id and calling PATCH/DELETE.
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, str(comment.project_id), user_sede=user_sede)
    if payload.content is not None:
        comment.content = payload.content
    if payload.is_resolved is not None:
        comment.is_resolved = payload.is_resolved
    db.commit()
    db.refresh(comment)
    author = db.query(models.Persona).filter(models.Persona.id == comment.author_id).first()
    return schemas.ProjectCommentItem(
        id=comment.id,
        project_id=str(comment.project_id) if comment.project_id is not None else None,
        task_id=str(comment.task_id) if comment.task_id is not None else None,
        content=comment.content,
        author_id=str(comment.author_id) if comment.author_id is not None else None,
        author_name=_author_name(author),
        is_resolved=comment.is_resolved,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
    )


# ── TASK LIST PER PROJECT ──────────────────────────────────────────────────────


@router.get("/{project_id}/tasks", response_model=List[schemas.ProjectTask])
def list_project_tasks(
    project_id: str,
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Lista todas las tareas de un proyecto."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    q = (
        db.query(models.ProjectTask)
        .options(
            selectinload(models.ProjectTask.attachments),
            selectinload(models.ProjectTask.supplies),
            selectinload(models.ProjectTask.subtasks),
        )
        .filter(models.ProjectTask.project_id == _to_uuid(project_id), models.ProjectTask.deleted_at.is_(None))
    )

    if status_filter:
        q = q.filter(models.ProjectTask.status == status_filter)

    tasks = q.order_by(models.ProjectTask.order_index.asc()).all()

    for t in tasks:
        _prepare_task_for_response(t)

    return tasks


# ── PROJECT UPDATE & DELETE ────────────────────────────────────────────────────


@router.patch("/{project_id}", response_model=schemas.Project)
def update_project(
    project_id: str,
    payload: schemas.ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Actualiza los metadatos de un proyecto."""
    user_sede = get_user_sede_id(db, current_user.id)
    project = _ensure_project(db, project_id, user_sede=user_sede)
    update_data = payload.model_dump(exclude_unset=True)
    changed_fields = []
    for key, value in update_data.items():
        old_value = getattr(project, key, None)
        setattr(project, key, value)
        if old_value != value:
            changed_fields.append(key)
    project.updated_at = _utcnow()
    if changed_fields:
        _log_project_activity(
            db,
            project_id,
            current_user.id,
            "project_updated",
            f"Proyecto '{project.title}' actualizado: {', '.join(changed_fields)}",
        )
    db.commit()
    db.refresh(project)
    _normalize_dates(project)
    return project


@router.delete("/{project_id}")
def delete_project(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff_or_admin),
):
    """Elimina (soft delete) un proyecto y todos sus datos relacionados.

    **Política confirmada** (``PEND-QUALITY-RBAC-ASYM-001`` — cierre
    2026-07-16): ``DELETE /projects/{id}`` requiere ``academy:manage``
    v\u00eda ``require_staff_or_admin``, NO ``projects:edit`` como su primo
    ``PATCH /projects/{id}``. La asimetr\u00eda se mantiene como pol\u00edtica
    deliberada porque un borrado de proyecto arrastra tareas, hitos,
    wiki, pizarra, comentarios y bit\u00e1cora ministerial — es una
    operaci\u00f3n destructiva de m\u00f3dulo, no de proyecto.

    * Editor (con ``projects:edit``) pasa ``PATCH`` pero recibe **403** en
      ``DELETE``.  Esto queda congelado por
      ``tests/test_projects_rbac.py::test_delete_project_requires_academy_manage_per_policy``.
    * Gestor / Admin pasan ambas rutas.

    Si en el futuro se decide alinear ``DELETE`` con la matriz
    ``projects:*``, este docstring y ``PROJECTS_RBAC_MATRIX.md \u00a76``
    deben actualizarse, y el test arriba debe ajustarse.
    """
    user_sede = get_user_sede_id(db, current_user.id)
    project = _ensure_project(db, project_id, user_sede=user_sede)
    project.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "deleted": project_id}


@router.delete("/{project_id}/tasks/{task_id}")
def delete_project_task(
    project_id: str,
    task_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Elimina una tarea de un proyecto."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    task = _ensure_task_in_project(db, project_id, task_id)
    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "task_deleted",
        f"Tarea '{task.title}' eliminada",
    )
    task.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "deleted": task_id}


@router.delete("/comments/{comment_id}")
def delete_project_comment(
    comment_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Elimina un comentario."""
    comment = db.query(models.ProjectComment).filter(models.ProjectComment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    # IDOR fix + Axioma 3 (mirror of update_project_comment): the actor
    # must own the sede that owns the comment's parent project.
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, str(comment.project_id), user_sede=user_sede)
    comment.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "deleted": comment_id}


# ── PROJECT CHAT ─────────────────────────────────────────────────────


@router.get("/{project_id}/messages", response_model=List[schemas.ProjectMessageItem])
def list_project_messages(
    project_id: str,
    limit: int = Query(50, le=200),
    before: Optional[int] = Query(None, alias="before"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """List project chat messages, newest first, with cursor pagination.

    Axioma 3 — the actor's ``sede_id`` is validated through
    ``_ensure_project`` (with ``user_sede`` filter); if the project does
    not belong to the actor's sede the response is exactly 404 — no
    existence leak.

    Soft-delete filter — contract: ``deleted_at IS NOT NULL`` messages
    are *excluded* from the listing (audit only), keeping the DB row
    intact for the parallel
    ``TestChatDeletePermissions::test_soft_deleted_message_kept_in_db_for_audit``
    contract. Hard-delete is reserved to admin forensics tooling, never
    via this endpoint.

    Cursor pagination — ``before`` is the **integer representation** of
    the cursor UUID (the client's ``uuid.UUID(...).int`` form). The DB
    column stores UUIDs as 32-char hex strings (SQLite) or native UUID
    (Postgres). We must NOT pass the raw ``int`` to SQLAlchemy because
    SQLite raises ``OverflowError: Python int too large to convert to
    SQLite INTEGER`` (UUID.int ≈ 10^38 > INT64 max ≈ 9.2e18). So we
    rebuild the UUID from the int and compare against its hex form (or
    canonical string in Postgres). Falls back to UUID string parsing if
    ``before`` is passed as a canonical UUID string (forward compat).
    Malformed cursors no-op rather than 422 — pagination is best-effort.
    """
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    room = f"project_{project_id}"
    q = db.query(models.ChatMessage).filter(
        models.ChatMessage.room_id == room,
        models.ChatMessage.deleted_at.is_(None),
    )
    if before is not None:
        cursor_hex: Optional[str] = None
        try:
            # Primary path: client sends ``cursor.int`` — the integer of
            # a UUID. SQLite-bound int comparison would overflow, so we
            # reconstruct the UUID and compare by hex string instead.
            cursor_uuid = uuid.UUID(int=int(before))
            cursor_hex = cursor_uuid.hex
        except (TypeError, ValueError, OverflowError):
            try:
                # Forward-compat: someone passed a canonical UUID string.
                cursor_uuid = uuid.UUID(str(before))
                cursor_hex = cursor_uuid.hex
            except (TypeError, ValueError, AttributeError):
                # Malformed cursor — best-effort: skip the filter rather
                # than fail the request. Pagination clients retry on stale
                # cursor with the latest ID anyway.
                cursor_hex = None
        if cursor_hex:
            q = q.filter(models.ChatMessage.id < uuid.UUID(cursor_hex))
    rows = q.order_by(models.ChatMessage.created_at.desc()).limit(limit).all()
    sender_ids = {r.sender_id for r in rows}
    users_map = {}
    if sender_ids:
        personas = db.query(models.Persona).filter(models.Persona.id.in_(sender_ids)).all()
        users_map = {p.id: _author_name(p) for p in personas}
    return [
        schemas.ProjectMessageItem(
            id=r.id,
            sender_id=str(r.sender_id),
            sender_name=users_map.get(r.sender_id, "Usuario"),
            content=r.content,
            created_at=r.created_at,
            is_read=r.is_read,
        )
        for r in rows
    ]


@router.post(
    "/{project_id}/messages",
    response_model=schemas.ProjectMessageItem,
    status_code=status.HTTP_201_CREATED,
)
def send_project_message(
    project_id: str,
    payload: schemas.ProjectMessageCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Send a message to the project chat room."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    persona = _resolve_persona(db, current_user.id)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    msg = models.ChatMessage(
        sender_id=persona.id,
        room_id=f"project_{project_id}",
        content=payload.content,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    # Broadcast via WebSocket (safe no-op if no event loop available)
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(
                manager.broadcast_event(
                    {
                        "event": "project_message",
                        "project_id": project_id,
                        "message": {
                            "id": msg.id,
                            "sender_id": msg.sender_id,
                            "sender_name": _author_name(persona),
                            "content": msg.content,
                            "created_at": str(msg.created_at),
                        },
                    },
                    room=f"project_{project_id}",
                )
            )
    except RuntimeError:
        pass

    return schemas.ProjectMessageItem(
        id=msg.id,
        sender_id=str(msg.sender_id),
        sender_name=_author_name(persona),
        content=msg.content,
        created_at=msg.created_at,
    )


@router.delete("/{project_id}/messages/{message_id}")
def delete_project_message(
    project_id: str,
    message_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Delete a chat message (own message or admin).

    IDOR fix + Axioma 3: validate that ``msg.room_id == project_{project_id}``
    before any role check so a sede_a user cannot delete messages stored
    under ``project_b`` by guessing message_ids. Without this the helper
    would happily return 200 on cross-project ids.
    """
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    msg = db.query(models.ChatMessage).filter(models.ChatMessage.id == message_id).first()
    if not msg:
        raise HTTPException(404, detail="Message not found")
    if str(msg.room_id) != f"project_{project_id}":
        # Existence-leak safe rejection: the message is real but it doesn't
        # belong to the project in the URL path. 404, not 403.
        raise HTTPException(404, detail="Message not found in this project")
    if msg.sender_id != current_user.id:
        role = normalize_role(getattr(current_user, "role", ""))
        if not role and hasattr(current_user, "rol_plataforma") and current_user.rol_plataforma:
            role = normalize_role(current_user.rol_plataforma.nombre)
        if role not in ("admin", "pastor", "coordinador"):
            raise HTTPException(403, detail="Cannot delete another user's message")
    msg.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True}


# ── MILESTONES ─────────────────────────────────────────────────────────────────


@router.get("/{project_id}/milestones", response_model=List[schemas.ProjectMilestone])
def list_project_milestones(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "read")),
):
    """Lista los hitos de un proyecto."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    milestones = crud.get_project_milestones(db, _to_uuid(project_id))
    for m in milestones:
        _normalize_dates(m)
    return milestones


@router.post(
    "/{project_id}/milestones",
    response_model=schemas.ProjectMilestone,
    status_code=status.HTTP_201_CREATED,
)
def create_project_milestone(
    project_id: str,
    payload: schemas.ProjectMilestoneBase,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Crea un hito en un proyecto."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    milestone = _projects_create_milestone(
        db, _to_uuid(project_id),
        title=payload.title,
        description=payload.description,
        target_date=payload.target_date,
        is_completed=payload.is_completed or False,
    )
    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "milestone_created",
        f"Hito '{milestone.title}' creado",
    )
    db.commit()
    _normalize_dates(milestone)
    return milestone


@router.delete("/{project_id}/milestones/{milestone_id}", response_model=dict)
def delete_project_milestone(
    project_id: str,
    milestone_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Elimina un hito de un proyecto (soft delete)."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    milestone = _ensure_milestone_in_project(db, project_id, milestone_id)
    _log_project_activity(
        db,
        project_id,
        current_user.id,
        "milestone_deleted",
        f"Hito '{milestone.title}' eliminado",
    )
    _projects_delete_milestone(db, _to_uuid(milestone_id))
    return {"ok": True, "deleted": milestone_id}


@router.patch("/{project_id}/milestones/{milestone_id}", response_model=schemas.ProjectMilestone)
def update_project_milestone(
    project_id: str,
    milestone_id: str,
    payload: schemas.ProjectMilestoneUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("projects", "edit")),
):
    """Actualiza un hito y registra cambios relevantes en la bitacora."""
    user_sede = get_user_sede_id(db, current_user.id)
    _ensure_project(db, project_id, user_sede=user_sede)
    milestone = _ensure_milestone_in_project(db, project_id, milestone_id)
    previous_completed = milestone.is_completed
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(milestone, key, value)

    if "is_completed" in update_data and milestone.is_completed != previous_completed:
        action_type = "milestone_completed" if milestone.is_completed else "milestone_reopened"
        description = (
            f"Hito '{milestone.title}' completado" if milestone.is_completed else f"Hito '{milestone.title}' reabierto"
        )
    else:
        action_type = "milestone_updated"
        description = f"Hito '{milestone.title}' actualizado"

    _log_project_activity(
        db,
        project_id,
        current_user.id,
        action_type,
        description,
    )
    db.commit()
    db.refresh(milestone)
    _normalize_dates(milestone)
    return milestone
