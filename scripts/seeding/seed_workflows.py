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

from backend import crud, models, schemas
from backend.core.database import SessionLocal


def seed_workflows():
    db = SessionLocal()
    try:
        # 1. Create the rule
        rule = crud.create_workflow_rule(
            db,
            name="Consolidación Automática (3 Asistencias)",
            trigger="attendance_created",
            condition={"count": 3},
            action="create_agent_task",
            payload={"title": "Intervención Pastoral: Nuevo Miembro Comprometido"},
        )
        print(f"Workflow rule created: {rule.name}")
    except Exception as e:
        print(f"Error seeding workflows: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_workflows()
