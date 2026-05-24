import datetime as dt

from backend import models
from backend.core.database import SessionLocal


def create_anomalies():
    db = SessionLocal()
    try:
        # 1. Leads estancados (hace 10 días)
        old_date = dt.datetime.now() - dt.timedelta(days=10)
        lead = models.ConsolidationPipeline(
            first_name="Anomalía",
            last_name="Test",
            phone="123456789",
            stage="new",
            updated_at=old_date,
            created_at=old_date,
        )
        db.add(lead)

        # 2. Tarea vencida
        project = db.query(models.Project).first()
        if project:
            task = models.ProjectTask(
                project_id=project.id,
                title="Tarea Crítica Vencida",
                status="todo",
                priority="urgent",
                due_date=dt.datetime.now() - dt.timedelta(days=2),
            )
            db.add(task)

        db.commit()
        print("🚩 Anomalías insertadas para activar IA.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    create_anomalies()
