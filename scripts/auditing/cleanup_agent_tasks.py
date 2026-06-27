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

import os
import sys

# Añadir el directorio raíz al path para poder importar backend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.orm import Session

from backend import models
from backend.core.database import SessionLocal


def cleanup_agent_tasks():
    db = SessionLocal()
    try:
        print("--- Iniciando limpieza de AgentTasks ---")

        # 1. Eliminar tareas sin source válido (None o vacío)
        deleted_no_source = (
            db.query(models.AgentTask)
            .filter(
                (models.AgentTask.source.is_(None)) | (models.AgentTask.source == "")
            )
            .delete(synchronize_session=False)
        )
        print(f"Eliminadas {deleted_no_source} tareas sin source válido.")

        # 2. Eliminar duplicados (mismo título y descripción)
        # Agrupamos por título y descripción y nos quedamos con el ID más reciente
        all_tasks = (
            db.query(models.AgentTask)
            .order_by(models.AgentTask.created_at.desc())
            .all()
        )
        seen = set()
        duplicates_ids = []

        for task in all_tasks:
            key = (task.title, task.description)
            if key in seen:
                duplicates_ids.append(task.id)
            else:
                seen.add(key)

        if duplicates_ids:
            deleted_duplicates = (
                db.query(models.AgentTask)
                .filter(models.AgentTask.id.in_(duplicates_ids))
                .delete(synchronize_session=False)
            )
            print(f"Eliminadas {deleted_duplicates} tareas duplicadas.")
        else:
            print("No se encontraron tareas duplicadas.")

        db.commit()
        print("--- Limpieza completada con éxito ---")

    except Exception as e:
        db.rollback()
        print(f"Error durante la limpieza: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    cleanup_agent_tasks()
