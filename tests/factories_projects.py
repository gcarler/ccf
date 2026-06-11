"""Data factories for the Projects module (pytest).

Each factory creates a single model instance and calls db.flush() so that the
caller can build relational graphs without committing until ready.

Pattern: plain functions, no factory_boy, following conftest.py:seed_admin_v2().
"""

from __future__ import annotations

import uuid as _uuid
from datetime import datetime, timezone
from typing import Any, Optional


def _utcnow():
    return datetime.now(timezone.utc)


def _short_id() -> str:
    return _uuid.uuid4().hex[:8]


# ── Persona & Sede helpers (thin wrappers so factories are self-contained) ──


def _ensure_persona(db, persona_id: Optional[_uuid.UUID] = None):
    """Create a bare Persona (no auth) if persona_id is not given."""
    from backend.models_crm import Persona

    if persona_id:
        p = db.query(Persona).filter(Persona.id == persona_id).first()
        if p:
            return p
    p = Persona(
        id=persona_id or _uuid.uuid4(),
        first_name="Factory",
        last_name=f"User_{_short_id()}",
        email=f"factory_{_short_id()}@example.com",
    )
    db.add(p)
    db.flush()
    return p


def _ensure_sede(db, sede_id: Optional[_uuid.UUID] = None):
    """Create a bare Sede if sede_id is not given."""
    from backend import models as _models

    if sede_id:
        s = db.query(_models.Sede).filter(_models.Sede.id == sede_id).first()
        if s:
            return s
    s = _models.Sede(
        id=sede_id or _uuid.uuid4(),
        nombre=f"Sede Factory {_short_id()}",
        ciudad="Bogota",
        es_activa=True,
    )
    db.add(s)
    db.flush()
    return s


# ── 1. Project ────────────────────────────────────────────────────────────


def create_project_factory(db, **overrides) -> "Project":
    """Create a Project with sensible defaults.

    If owner_id or sede_id are omitted a bare Persona / Sede is created.
    """
    from backend.models_projects import Project

    owner_id = overrides.pop("owner_id", None)
    sede_id = overrides.pop("sede_id", None)

    # Resolve / create FK targets
    if owner_id is not None:
        _ensure_persona(db, owner_id)
    if sede_id is not None:
        _ensure_sede(db, sede_id)

    title = overrides.pop("title", None) or f"Proyecto Test {_short_id()}"
    defaults = dict(
        id=_uuid.uuid4(),
        title=title,
        description="Descripcion de prueba",
        status="planning",
        owner_id=owner_id or _ensure_persona(db).id,
        sede_id=sede_id or _ensure_sede(db).id,
        color="#3b82f6",
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )
    defaults.update(overrides)
    obj = Project(**defaults)
    db.add(obj)
    db.flush()
    return obj


# ── 2. Task ────────────────────────────────────────────────────────────────


def create_task_factory(db, project_id: _uuid.UUID, **overrides) -> "ProjectTask":
    """Create a task linked to *project_id*.

    If assignee_id is omitted a bare Persona is created.
    """
    from backend.models_projects import ProjectTask

    assignee_id = overrides.pop("assignee_id", None)
    if assignee_id is not None:
        _ensure_persona(db, assignee_id)

    title = overrides.pop("title", None) or f"Tarea Test {_short_id()}"
    defaults = dict(
        id=_uuid.uuid4(),
        project_id=project_id,
        title=title,
        description="Descripcion de tarea de prueba",
        status="todo",
        priority="medium",
        order_index=0,
        assignee_id=assignee_id or _ensure_persona(db).id,
        labels=[],
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )
    defaults.update(overrides)
    obj = ProjectTask(**defaults)
    db.add(obj)
    db.flush()
    return obj


# ── 3. Subtask ──────────────────────────────────────────────────────────────


def create_subtask_factory(db, parent_id: _uuid.UUID, project_id: _uuid.UUID, **overrides) -> "ProjectTask":
    """Create a subtask under *parent_id*."""
    from backend.models_projects import ProjectTask

    title = overrides.pop("title", None) or f"Sub: Tarea Test {_short_id()}"
    defaults = dict(
        id=_uuid.uuid4(),
        project_id=project_id,
        parent_id=parent_id,
        title=title,
        description="Sub-tarea de prueba",
        status="todo",
        priority="medium",
        order_index=0,
        labels=[],
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )
    defaults.update(overrides)
    obj = ProjectTask(**defaults)
    db.add(obj)
    db.flush()
    return obj


# ── 4. Milestone ──────────────────────────────────────────────────────────


def create_milestone_factory(db, project_id: _uuid.UUID, **overrides) -> "ProjectMilestone":
    """Create a milestone with target_date = +7 days by default."""
    from backend.models_projects import ProjectMilestone

    title = overrides.pop("title", None) or f"Hito Test {_short_id()}"
    defaults = dict(
        id=_uuid.uuid4(),
        project_id=project_id,
        title=title,
        description="Hito de prueba",
        target_date=_utcnow(),
        is_completed=False,
        created_at=_utcnow(),
    )
    defaults.update(overrides)
    obj = ProjectMilestone(**defaults)
    db.add(obj)
    db.flush()
    return obj


# ── 5. Comment ────────────────────────────────────────────────────────────


def create_comment_factory(db, project_id: _uuid.UUID, author_id: _uuid.UUID, **overrides) -> "ProjectComment":
    """Create a comment.

    *author_id* is required (the Persona who wrote it).
    """
    from backend.models_projects import ProjectComment

    content = overrides.pop("content", None) or f"Comentario de prueba {_short_id()}"
    defaults = dict(
        project_id=project_id,
        task_id=None,
        author_id=author_id,
        content=content,
        is_resolved=False,
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )
    defaults.update(overrides)
    obj = ProjectComment(**defaults)
    db.add(obj)
    db.flush()
    return obj


# ── 6. Supply ─────────────────────────────────────────────────────────────


def create_supply_factory(db, task_id: _uuid.UUID, **overrides) -> "TaskSupply":
    """Create a task supply."""
    from backend.models_projects import TaskSupply

    item_name = overrides.pop("item_name", None) or f"Insumo {_short_id()}"
    defaults = dict(
        task_id=task_id,
        item_name=item_name,
        quantity=1,
        status="pending",
    )
    defaults.update(overrides)
    obj = TaskSupply(**defaults)
    db.add(obj)
    db.flush()
    return obj


# ── 7. Default Phases (the 4 Kanban columns) ─────────────────────────────


def create_default_phases_factory(db, project_id: _uuid.UUID) -> list["ProjectPhase"]:
    """Create the standard 4 Kanban phases for a project.

    Returns the list of created phase objects.
    """
    from backend.models_projects import ProjectPhase

    phases_data = [
        ("Por hacer", "todo", "#94a3b8", 0),
        ("En progreso", "in_progress", "#3b82f6", 1),
        ("Revision", "review", "#f59e0b", 2),
        ("Completada", "completed", "#22c55e", 3),
    ]
    phases = []
    for name, slug, color, idx in phases_data:
        p = ProjectPhase(
            id=_uuid.uuid4(),
            project_id=project_id,
            name=name,
            slug=slug,
            color=color,
            order_index=idx,
        )
        db.add(p)
        phases.append(p)
    db.flush()
    return phases


# ── 8. Activity Log ────────────────────────────────────────────────────────


def create_activity_log_factory(db, project_id: _uuid.UUID, action_type: str = "task_created", **overrides) -> "ProjectActivityLog":
    """Create an activity log entry."""
    from backend.models_projects import ProjectActivityLog

    persona_id = overrides.pop("persona_id", None)
    if persona_id is not None:
        _ensure_persona(db, persona_id)

    description = overrides.pop("description", None) or f"Actividad: {action_type}"
    defaults = dict(
        project_id=project_id,
        persona_id=persona_id or _ensure_persona(db).id,
        action_type=action_type,
        description=description,
        created_at=_utcnow(),
    )
    defaults.update(overrides)
    obj = ProjectActivityLog(**defaults)
    db.add(obj)
    db.flush()
    return obj


# ── 9. Wiki (ProjectDocument) ──────────────────────────────────────────────


def create_wiki_factory(db, project_id: _uuid.UUID, **overrides) -> "ProjectDocument":
    """Create a project wiki document."""
    from backend.models_projects import ProjectDocument

    author_id = overrides.pop("author_id", None)
    if author_id is not None:
        _ensure_persona(db, author_id)

    defaults = dict(
        project_id=project_id,
        title="Wiki Ministerial",
        content="# Wiki\n\nDocumentacion de prueba.",
        author_id=author_id or _ensure_persona(db).id,
        created_at=_utcnow(),
    )
    defaults.update(overrides)
    obj = ProjectDocument(**defaults)
    db.add(obj)
    db.flush()
    return obj


# ── 10. Whiteboard ─────────────────────────────────────────────────────────


def create_whiteboard_factory(db, project_id: _uuid.UUID, **overrides) -> "ProjectWhiteboard":
    """Create a project whiteboard."""
    from backend.models_projects import ProjectWhiteboard

    defaults = dict(
        project_id=project_id,
        title="Pizarra Estrategica",
        elements_json="[]",
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )
    defaults.update(overrides)
    obj = ProjectWhiteboard(**defaults)
    db.add(obj)
    db.flush()
    return obj


# ── 11. ChatMessage (models_crm) ───────────────────────────────────────────


def create_message_factory(db, project_id: _uuid.UUID, sender_id: _uuid.UUID, **overrides) -> "ChatMessage":
    """Create a project chat message.

    *sender_id* is required (the Persona UUID who sent the message).
    """
    from backend.models_crm import ChatMessage

    _ensure_persona(db, sender_id)
    content = overrides.pop("content", None) or f"Mensaje de prueba {_short_id()}"
    defaults = dict(
        sender_id=sender_id,
        room_id=f"project_{project_id}",
        content=content,
        is_read=False,
        created_at=_utcnow(),
    )
    defaults.update(overrides)
    obj = ChatMessage(**defaults)
    db.add(obj)
    db.flush()
    return obj


# ── 12. Attachment ──────────────────────────────────────────────────────────


def create_attachment_factory(db, task_id: _uuid.UUID, **overrides) -> "ProjectAttachment":
    """Create a task attachment."""
    from backend.models_projects import ProjectAttachment

    uploader_id = overrides.pop("uploader_id", None)
    if uploader_id is not None:
        _ensure_persona(db, uploader_id)

    defaults = dict(
        task_id=task_id,
        filename=f"archivo_{_short_id()}.pdf",
        file_url=f"/api/static/test_{_short_id()}.pdf",
        file_type="application/pdf",
        file_size=1024,
        uploader_id=uploader_id or _ensure_persona(db).id,
        created_at=_utcnow(),
    )
    defaults.update(overrides)
    obj = ProjectAttachment(**defaults)
    db.add(obj)
    db.flush()
    return obj


# ── 13. Inbox State ─────────────────────────────────────────────────────


def create_inbox_state_factory(db, persona_id: _uuid.UUID, item_id: str, **overrides) -> "ProjectInboxState":
    """Create an inbox state entry."""
    from backend.models_projects import ProjectInboxState

    _ensure_persona(db, persona_id)
    defaults = dict(
        persona_id=persona_id,
        item_id=item_id or f"comment_{_short_id()}",
        is_read=False,
    )
    defaults.update(overrides)
    obj = ProjectInboxState(**defaults)
    db.add(obj)
    db.flush()
    return obj


# ── Composite setup helpers ──────────────────────────────────────────────


def setup_project_with_all_relations(db) -> dict:
    """Create a complete project with tasks, phases, milestones, wiki, etc.

    Returns a dict with every created object accessible by key, e.g.:
        result["project"], result["tasks"][0], result["milestones"], …
    """
    project = create_project_factory(db)
    phases = create_default_phases_factory(db, project.id)

    t1 = create_task_factory(db, project.id, status="todo", title="Tarea 1 - Diseno")
    t2 = create_task_factory(db, project.id, status="in_progress", title="Tarea 2 - Desarrollo")
    t3 = create_task_factory(db, project.id, status="completed", title="Tarea 3 - QA")

    sub = create_subtask_factory(db, t1.id, project.id, title="Sub: Mockups")

    m1 = create_milestone_factory(db, project.id, title="MVP v1.0")
    m2 = create_milestone_factory(db, project.id, title="Lanzamiento", is_completed=True)

    persona = _ensure_persona(db)
    c1 = create_comment_factory(db, project.id, persona.id, content="Comentario de prueba 1")
    c2 = create_comment_factory(db, project.id, persona.id, content="Comentario de prueba 2")

    s1 = create_supply_factory(db, t1.id, item_name="Hosting")
    s2 = create_supply_factory(db, t1.id, item_name="Dominio")

    al1 = create_activity_log_factory(db, project.id, "project_created", persona_id=persona.id)
    al2 = create_activity_log_factory(db, project.id, "task_created", persona_id=persona.id)

    wiki = create_wiki_factory(db, project.id, author_id=persona.id)
    whiteboard = create_whiteboard_factory(db, project.id)
    msg = create_message_factory(db, project.id, persona.id)

    return {
        "project": project,
        "phases": phases,
        "tasks": [t1, t2, t3],
        "subtasks": [sub],
        "milestones": [m1, m2],
        "comments": [c1, c2],
        "supplies": [s1, s2],
        "activity_logs": [al1, al2],
        "wiki": wiki,
        "whiteboard": whiteboard,
        "message": msg,
        "persona": persona,
    }
