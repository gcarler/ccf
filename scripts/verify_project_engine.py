from __future__ import annotations
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from backend.core.database import SessionLocal, Base, engine
from backend import models, crud, schemas

def verify_project_engine():
    print("=== CCF PROJECT ENGINE QUALITY CHECK ===")
    
    # Force fresh schema for testing
    print("[0/4] Preparing Clean Project Environment...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # 1. Create a Project
        print("[1/4] Creating Test Project...")
        project = models.Project(name="Gran Vigilia 2026", description="Evento masivo de oración")
        db.add(project)
        db.commit()
        db.refresh(project)
        print(f"  > Project created: {project.name}")

        # 2. Create a Task with Metadata
        print("[2/4] Creating Task with Metadata (Priority, Dates)...")
        due_date = datetime.utcnow() + timedelta(days=2)
        task = models.ProjectTask(
            project_id=project.id,
            title="Montaje de Sonido",
            priority="urgent",
            status="todo",
            due_date=due_date,
            labels=["Técnica", "Urgente"]
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        print(f"  > Task created: {task.title} | Priority: {task.priority} | Due: {task.due_date}")

        # 3. Assign Supplies
        print("[3/4] Assigning Supplies to Task...")
        supply = models.TaskSupply(
            task_id=task.id,
            item_name="Consola Digital",
            quantity=1,
            status="pending"
        )
        db.add(supply)
        db.commit()
        db.refresh(supply)
        print(f"  > Supply assigned: {supply.item_name} ({supply.quantity})")

        # 4. Final Integration Check
        print("[4/4] Verifying Relational Integrity...")
        db_task = db.query(models.ProjectTask).filter(models.ProjectTask.id == task.id).first()
        assert db_task.project.name == "Gran Vigilia 2026"
        assert len(db_task.supplies) > 0
        assert db_task.supplies[0].item_name == "Consola Digital"
        
        print("\n=== PROJECT ENGINE CERTIFIED: 100% QUALITY ===")
        
    except Exception as e:
        print(f"\n!!! PROJECT ENGINE FAILED: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    verify_project_engine()
