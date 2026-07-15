from __future__ import annotations

import os
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

# Locate the project root by walking up until we find the `backend/`
# package. This keeps the script runnable from scripts/, tests/, or CI.
_HERE = Path(__file__).resolve()
_PROJECT_ROOT = next((p for p in _HERE.parents if (p / "backend" / "__init__.py").is_file()), None)
if _PROJECT_ROOT is None:
    raise RuntimeError(f"backend package not found above {_HERE}")
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend import models
from backend.core.database import SessionLocal
from backend.core.security import get_password_hash
from backend.models_auth import RolPlataforma, Usuario
from backend.models_crm import Persona
from backend.models_projects import Project, ProjectActivityLog, ProjectPhase, ProjectTask

DEMO_PROJECTS = (
    {
        "title": "Demo Proyecto 1",
        "description": "Semilla estructural de evangelismo para validar proyectos, tareas y actividades.",
        "status": "active",
        "color": "#2563eb",
    },
    {
        "title": "Demo Proyecto 2",
        "description": "Segundo proyecto demo con fechas distintas para probar calendarios y tablas.",
        "status": "planning",
        "color": "#0f766e",
    },
    {
        "title": "Demo Proyecto 3",
        "description": "Tercer proyecto demo con el mismo contrato de datos en otra línea temporal.",
        "status": "on_hold",
        "color": "#b45309",
    },
)

ACTIVITY_TYPES = ("project_created", "task_created", "status_changed", "comment_added", "review_requested")


@dataclass(frozen=True)
class DemoActor:
    user: Usuario
    persona: Persona
    sede: models.Sede


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_role(db) -> RolPlataforma:
    role = db.query(RolPlataforma).filter(RolPlataforma.nombre == "ADMIN").first()
    if role:
        return role
    role = RolPlataforma(id=uuid.uuid4(), nombre="ADMIN", permisos={"*": "allow"})
    db.add(role)
    db.flush()
    return role


def _ensure_actor(db, email: str | None = None) -> DemoActor:
    candidate = None
    if email:
        candidate = db.query(Usuario).filter(Usuario.email == email).first()
    if candidate is None:
        candidate = db.query(Usuario).join(RolPlataforma, Usuario.rol_plataforma_id == RolPlataforma.id).filter(
            RolPlataforma.nombre == "ADMIN"
        ).order_by(Usuario.created_at.asc()).first()
    if candidate is None:
        candidate = db.query(Usuario).order_by(Usuario.created_at.asc()).first()

    if candidate is None:
        persona = Persona(
            id=uuid.uuid4(),
            first_name="Demo",
            last_name="Admin",
            email=email or "demo-admin@example.com",
        )
        db.add(persona)
        db.flush()
        sede = models.Sede(id=uuid.uuid4(), nombre="Sede Demo", ciudad="Bogota", es_activa=True)
        db.add(sede)
        db.flush()
        persona.sede_id = sede.id
        user = Usuario(
            id=persona.id,
            sede_id=sede.id,
            username=(email or "demo-admin@example.com").split("@")[0],
            email=email or "demo-admin@example.com",
            password_hash=get_password_hash("demo12345"),
            rol_plataforma_id=_ensure_role(db).id,
            is_active=True,
            is_email_verified=True,
        )
        db.add(user)
        db.flush()
        return DemoActor(user=user, persona=persona, sede=sede)

    persona = db.query(Persona).filter(Persona.id == candidate.id).first()
    if persona is None:
        persona = Persona(
            id=candidate.id,
            first_name="Demo",
            last_name="Admin",
            email=candidate.email,
        )
        db.add(persona)
        db.flush()
    sede = db.query(models.Sede).filter(models.Sede.id == candidate.sede_id).first()
    if sede is None:
        sede = db.query(models.Sede).first()
        if sede is None:
            sede = models.Sede(id=uuid.uuid4(), nombre="Sede Demo", ciudad="Bogota", es_activa=True)
            db.add(sede)
            db.flush()
    persona.sede_id = sede.id
    candidate.sede_id = sede.id
    db.flush()
    return DemoActor(user=candidate, persona=persona, sede=sede)


def _purge_existing_demo_projects(db) -> None:
    demo_titles = {item["title"] for item in DEMO_PROJECTS}
    existing = db.query(Project).filter(Project.title.in_(demo_titles)).all()
    for project in existing:
        db.query(models.ProjectComment).filter(models.ProjectComment.project_id == project.id).delete(
            synchronize_session=False
        )
        db.query(models.ProjectDocument).filter(models.ProjectDocument.project_id == project.id).delete(
            synchronize_session=False
        )
        db.delete(project)
    db.commit()


def _seed_project_bundle(db, actor: DemoActor, index: int, payload: dict, base_date: datetime) -> Project:
    project = Project(
        id=uuid.uuid4(),
        sede_id=actor.sede.id,
        owner_id=actor.persona.id,
        title=payload["title"],
        description=payload["description"],
        status=payload["status"],
        color=payload["color"],
        created_at=base_date,
        updated_at=base_date + timedelta(days=6),
    )
    db.add(project)
    db.flush()

    phases = [
        ("Por Hacer", "todo", "#94a3b8", 0),
        ("En Curso", "in_progress", "#3b82f6", 1),
        ("Revisión", "review", "#f59e0b", 2),
        ("Completado", "completed", "#10b981", 3),
    ]
    for name, slug, color, order_index in phases:
        db.add(
            ProjectPhase(
                id=uuid.uuid4(),
                project_id=project.id,
                name=name,
                slug=slug,
                color=color,
                order_index=order_index,
            )
        )

    task_templates = (
        ("Levantamiento", "todo", 0),
        ("Diseño", "in_progress", 1),
        ("Ejecución", "review", 2),
        ("Validación", "completed", 3),
        ("Cierre", "in_progress", 4),
    )
    tasks: list[ProjectTask] = []
    for offset, (label, status, order_index) in enumerate(task_templates, start=1):
        start_date = base_date + timedelta(days=offset * 2 + index)
        due_date = start_date + timedelta(days=1 + offset)
        task = ProjectTask(
            id=uuid.uuid4(),
            project_id=project.id,
            assignee_id=actor.persona.id,
            title=f"{payload['title']} - Tarea {offset}: {label}",
            description=f"{payload['title']} · actividad {offset} para validar fechas y navegación.",
            status=status,
            priority="medium" if offset < 4 else "high",
            order_index=order_index,
            start_date=start_date,
            due_date=due_date,
            labels=["demo", f"fase-{offset}"],
            created_at=start_date - timedelta(hours=3),
            updated_at=due_date,
        )
        db.add(task)
        tasks.append(task)

    for activity_offset, action_type in enumerate(ACTIVITY_TYPES, start=0):
        db.add(
            ProjectActivityLog(
                id=uuid.uuid4(),
                project_id=project.id,
                persona_id=actor.persona.id,
                action_type=action_type,
                description=(
                    f"{payload['title']} · registro demo {activity_offset + 1} "
                    f"({action_type.replace('_', ' ')})"
                ),
                created_at=base_date + timedelta(days=activity_offset * 2 + index),
            )
        )

    db.commit()
    return project


def seed_projects_demo(db=None, *, actor_email: str | None = None, reset: bool = True):
    session = db or SessionLocal()
    owns_session = db is None
    try:
        actor = _ensure_actor(session, actor_email or os.getenv("PROJECTS_DEMO_EMAIL") or os.getenv("E2E_EMAIL"))
        if reset:
            _purge_existing_demo_projects(session)
        created = []
        base_anchor = _utcnow() - timedelta(days=21)
        for index, payload in enumerate(DEMO_PROJECTS):
            created.append(_seed_project_bundle(session, actor, index, payload, base_anchor + timedelta(days=index * 7)))
        return created
    finally:
        if owns_session:
            session.close()


def main() -> None:
    created = seed_projects_demo()
    print(f"seeded-projects-demo {len(created)} projects")


if __name__ == "__main__":
    main()
