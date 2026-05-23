import logging
import threading
import time
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from backend import models
from backend.core.database import SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AutomationEngine")


class AutomationEngine:
    _instance = None
    _thread = None
    _stop_event = threading.Event()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AutomationEngine, cls).__new__(cls)
        return cls._instance

    def start(self):
        if self._thread is None:
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()
            logger.info("🚀 Automation Engine started.")

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join()
            self._thread = None
            logger.info("🛑 Automation Engine stopped.")

    def _run_loop(self):
        while not self._stop_event.is_set():
            try:
                self._check_all_rules()
            except Exception as e:
                logger.error(f"Error in automation loop: {e}")

            # Dormir por 1 minuto antes de la siguiente revisión
            time.sleep(60)

    def _check_all_rules(self):
        db = SessionLocal()
        try:
            # 1. Alerta de Sobrecarga
            self._process_overload_rule(db)

            # 2. Recordatorio de Deadline (24h antes)
            self._process_deadline_rule(db)

            db.commit()
        finally:
            db.close()

    def _process_overload_rule(self, db: Session):
        # Usar la vista que creamos en el paso anterior
        from sqlalchemy import text

        query = text(
            "SELECT user_id, full_name, open_tasks FROM view_user_workload WHERE open_tasks > 8"
        )
        overloaded = db.execute(query).fetchall()

        for row in overloaded:
            # Crear notificación si no existe una reciente (evitar spam)
            # Por simplicidad, creamos una de sistema
            exists = (
                db.query(models.Notification)
                .filter(
                    models.Notification.user_id == row.user_id,
                    models.Notification.title == "Alerta de Capacidad",
                )
                .first()
            )

            if not exists:
                notif = models.Notification(
                    user_id=row.user_id,
                    title="Alerta de Capacidad",
                    content=f"Hola {row.full_name}, tienes {row.open_tasks} tareas activas. Considera delegar o priorizar con tu líder.",
                )
                db.add(notif)
                logger.info(f"Notification sent to user {row.user_id} for overload.")

    def _process_deadline_rule(self, db: Session):
        tomorrow = datetime.now() + timedelta(days=1)
        tasks = (
            db.query(models.ProjectTask)
            .filter(
                models.ProjectTask.status != "done",
                models.ProjectTask.due_date <= tomorrow,
                models.ProjectTask.assignee_id.isnot(None),
            )
            .all()
        )

        for task in tasks:
            # Crear un recordatorio en la tabla Cronos
            exists = (
                db.query(models.UserReminder)
                .filter(
                    models.UserReminder.related_id == task.id,
                    models.UserReminder.related_type == "task",
                )
                .first()
            )

            if not exists:
                reminder = models.UserReminder(
                    user_id=task.assignee_id,
                    title=f"⚠️ Entrega Mañana: {task.title}",
                    description=f"La tarea del proyecto {task.project_id} vence pronto.",
                    remind_at=datetime.now(),
                    priority="high",
                    related_type="task",
                    related_id=task.id,
                )
                db.add(reminder)
                logger.info(f"Reminder created for task {task.id}.")


# Inicializar motor globalmente
engine = AutomationEngine()
