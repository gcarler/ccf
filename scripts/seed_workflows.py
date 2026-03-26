from backend.core.database import SessionLocal
from backend import crud, schemas, models

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
            payload={"title": "Intervención Pastoral: Nuevo Miembro Comprometido"}
        )
        print(f"Workflow rule created: {rule.name}")
    except Exception as e:
        print(f"Error seeding workflows: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_workflows()
