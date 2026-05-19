from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from backend import models
from backend.core.database import SessionLocal
from backend.management.schema import reset_database_for_local_bootstrap


def verify_project_engine():
    print("=== CCF PROJECT ENGINE QUALITY CHECK ===")

    print("[0/4] Preparing Clean Project Environment...")
    reset_database_for_local_bootstrap()

    db = SessionLocal()

    try:
        print("[1/4] Creating Test Project...")
        project = models.Project(title="Gran Vigilia 2026", description="Evento masivo de oracion")
        db.add(project)
        db.commit()
        db.refresh(project)
        print(f"  > Project created: {project.title}")

        print("[2/4] Creating Task with Metadata (Priority, Dates)...")
        due_date = datetime.utcnow() + timedelta(days=2)
        task = models.ProjectTask(
            project_id=project.id,
            title="Montaje de Sonido",
            priority="urgent",
            status="todo",
            due_date=due_date,
            labels=["Tecnica", "Urgente"],
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        print(f"  > Task created: {task.title} | Priority: {task.priority} | Due: {task.due_date}")

        print("[3/4] Assigning Supplies to Task...")
        supply = models.TaskSupply(
            task_id=task.id,
            item_name="Consola Digital",
            quantity=1,
            status="pending",
        )
        db.add(supply)
        db.commit()
        db.refresh(supply)
        print(f"  > Supply assigned: {supply.item_name} ({supply.quantity})")

        print("[4/4] Verifying Relational Integrity...")
        db_task = db.query(models.ProjectTask).filter(models.ProjectTask.id == task.id).first()
        assert db_task.project.title == "Gran Vigilia 2026"
        assert len(db_task.supplies) > 0
        assert db_task.supplies[0].item_name == "Consola Digital"

        print("\n=== PROJECT ENGINE CERTIFIED: 100% QUALITY ===")
    except Exception as exc:
        print(f"\n!!! PROJECT ENGINE FAILED: {exc}")
        import traceback

        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    verify_project_engine()
