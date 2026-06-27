import sys
from pathlib import Path

# Locate the project root by walking up until we find the `backend/`
# package. This works whether the script lives in scripts/, scripts/seeding/
# scripts/migrations/, scripts/auditing/ or any other nested folder.
_HERE = Path(__file__).resolve()
_PROJECT_ROOT = next(
    (p for p in _HERE.parents if (p / "backend" / "__init__.py").is_file()),
    None,
)
if _PROJECT_ROOT is None:
    raise RuntimeError(f"backend package not found above {_HERE}")
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import asyncio
from datetime import datetime, timedelta

from backend.crud import create_project, create_project_task
from backend.database import SessionLocal
from backend.schemas import ProjectCreate, ProjectTaskCreate


def seed_projects():
    db = SessionLocal()
    try:
        # Create a default project
        project_data = ProjectCreate(
            title="Proyecto CCF Fase 1",
            description="Implementación del nuevo ecosistema web.",
            owner_id=1,
        )
        project = create_project(db, project_data)

        # Create tasks
        tasks = [
            ProjectTaskCreate(
                project_id=project.id,
                title="Diseño de UI/UX Proyectos",
                status="EN CURSO",
                priority="Alta",
                due_date=datetime.utcnow() + timedelta(days=5),
                description="Finalizar la interfaz de usuario con estilo ClickUp.",
            ),
            ProjectTaskCreate(
                project_id=project.id,
                title="Implementación Base de Datos",
                status="PENDIENTE",
                priority="Media",
                due_date=datetime.utcnow() + timedelta(days=7),
                description="Migraciones de Alembic para el módulo de proyectos.",
            ),
            ProjectTaskCreate(
                project_id=project.id,
                title="Componentes Frontend (React)",
                status="EN CURSO",
                priority="Media",
                due_date=datetime.utcnow() + timedelta(days=10),
                description="Crear Toolbar y Drawer unificados.",
            ),
        ]
        for task in tasks:
            create_project_task(db, task)

        print("Project and tasks seeded successfully!")
    except Exception as e:
        print(f"Error seeding projects: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_projects()
