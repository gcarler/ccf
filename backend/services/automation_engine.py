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

            # 3. Flujos de Automatización de CRM
            self._process_crm_pending_actions(db)

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

    def _process_crm_pending_actions(self, db: Session):
        import uuid as _uuid

        from backend.models_crm import CrmAutomation, CrmAutomationEdge, PendingCrmAction
        from backend.models_crm_pipeline import CasoCRM
        from backend.models_shared import _utcnow

        pending_actions = (
            db.query(PendingCrmAction)
            .filter(
                PendingCrmAction.status == "pending",
                PendingCrmAction.execute_at <= _utcnow()
            )
            .all()
        )

        def detect_cycle_dfs(start_id, db_session) -> bool:
            visited = set()
            rec_stack = set()
            
            def dfs(curr_id) -> bool:
                if len(rec_stack) > 900:  # Safety recursion depth limit
                    return True
                visited.add(curr_id)
                rec_stack.add(curr_id)
                
                edges_list = db_session.query(CrmAutomationEdge).filter(CrmAutomationEdge.source_id == curr_id).all()
                for edge in edges_list:
                    target_id = edge.target_id
                    if target_id not in visited:
                        if dfs(target_id):
                            return True
                    elif target_id in rec_stack:
                        return True
                        
                rec_stack.remove(curr_id)
                return False
                
            return dfs(start_id)

        def evaluate_condition(cond_type, actual_val, expected_val_str) -> bool:
            if not cond_type or not isinstance(cond_type, str):
                cond_type = "equals"
            
            cond_type = cond_type.lower().strip()
            
            if cond_type == "always":
                return True
                
            if cond_type == "ne":
                return not evaluate_condition("equals", actual_val, expected_val_str)
                
            if cond_type == "equals":
                if actual_val is None:
                    return expected_val_str in (None, "", "None", "null")
                if expected_val_str is None:
                    return False
                try:
                    if isinstance(actual_val, bool):
                        return actual_val == (expected_val_str.lower() in ("true", "1", "yes"))
                    elif isinstance(actual_val, int):
                        return actual_val == int(expected_val_str)
                    elif isinstance(actual_val, float):
                        return actual_val == float(expected_val_str)
                    elif isinstance(actual_val, _uuid.UUID):
                        return actual_val == _uuid.UUID(expected_val_str)
                    elif hasattr(actual_val, "value"):  # Enum comparison
                        return str(actual_val.value) == expected_val_str or str(actual_val) == expected_val_str
                    else:
                        return str(actual_val) == str(expected_val_str)
                except Exception:
                    return str(actual_val) == str(expected_val_str)
            
            if cond_type == "contains":
                if actual_val is None or expected_val_str is None:
                    return False
                return str(expected_val_str).lower() in str(actual_val).lower()
                
            if cond_type == "starts_with":
                if actual_val is None or expected_val_str is None:
                    return False
                return str(actual_val).lower().startswith(str(expected_val_str).lower())
                
            if cond_type == "in":
                if actual_val is None or expected_val_str is None:
                    return False
                import json
                try:
                    items = json.loads(expected_val_str)
                    if not isinstance(items, list):
                        items = [items]
                except Exception:
                    items = [x.strip() for x in expected_val_str.split(",")]
                act_str = str(actual_val).lower()
                return any(str(item).lower() == act_str for item in items)
                
            if cond_type == "gt":
                if actual_val is None or expected_val_str is None:
                    return False
                try:
                    return float(actual_val) > float(expected_val_str)
                except Exception:
                    return str(actual_val) > str(expected_val_str)
                    
            if cond_type == "lt":
                if actual_val is None or expected_val_str is None:
                    return False
                try:
                    return float(actual_val) < float(expected_val_str)
                except Exception:
                    return str(actual_val) < str(expected_val_str)
            
            return False

        for action in pending_actions:
            automation = db.query(CrmAutomation).filter(CrmAutomation.id == action.automation_id).first()
            if not automation:
                action.status = "failed"
                continue
            
            # DFS Loop Cycle Detection
            if detect_cycle_dfs(automation.id, db):
                logger.warning(f"Cycle detected in CRM automation flow starting at {automation.id}. Action failed.")
                action.status = "failed"
                continue
            
            try:
                logger.info(f"Executing CRM automation {automation.id} for persona {action.target_persona_id}")
                
                # Fetch target CasoCRM case and linked Persona
                case = db.query(CasoCRM).filter(CasoCRM.persona_id == action.target_persona_id).first()
                persona = None
                if hasattr(models, "Persona"):
                    persona = db.query(models.Persona).filter(models.Persona.id == action.target_persona_id).first()
                
                # Execution of current action (simulated)
                action.status = "executed"
                
                # Retrieve outgoing edges from active automation
                edges = db.query(CrmAutomationEdge).filter(CrmAutomationEdge.source_id == automation.id).all()
                for edge in edges:
                    # Evaluate conditions
                    cond_type_str = edge.condition_type.lower().strip() if (edge.condition_type and isinstance(edge.condition_type, str)) else ""
                    if cond_type_str == "always":
                        # Always matches regardless of key/value
                        pass
                    elif edge.condition_key:
                        val = None
                        found = False
                        
                        # 1. CasoCRM attributes
                        if case is not None and hasattr(case, edge.condition_key):
                            val = getattr(case, edge.condition_key)
                            found = True
                        # 2. CasoCRM payload_web json keys
                        elif case is not None and case.payload_web and isinstance(case.payload_web, dict) and edge.condition_key in case.payload_web:
                            val = case.payload_web[edge.condition_key]
                            found = True
                        # 3. Linked Persona attributes
                        elif persona is not None and hasattr(persona, edge.condition_key):
                            val = getattr(persona, edge.condition_key)
                            found = True
                        
                        if not found or not evaluate_condition(edge.condition_type, val, edge.condition_value):
                            # Skip this edge since condition evaluates to False
                            logger.info(f"Skipping edge {edge.id} due to condition mismatch: {edge.condition_key}")
                            continue

                    next_auto = db.query(CrmAutomation).filter(CrmAutomation.id == edge.target_id).first()
                    if next_auto:
                        next_execute_at = _utcnow() + timedelta(minutes=next_auto.delay_minutes)
                        next_action = PendingCrmAction(
                            automation_id=next_auto.id,
                            target_persona_id=action.target_persona_id,
                            execute_at=next_execute_at,
                            status="pending"
                        )
                        db.add(next_action)
                        logger.info(f"Queued next automation {next_auto.id} for execution at {next_execute_at}")

            except Exception as e:
                logger.error(f"Failed to execute CRM automation {automation.id}: {e}")
                action.status = "failed"

    def trigger_crm_automation(self, db: Session, automation_id: str, target_persona_id: str):
        from backend.models_crm import CrmAutomation, PendingCrmAction
        from backend.models_shared import _utcnow
        
        automation = db.query(CrmAutomation).filter(CrmAutomation.id == automation_id).first()
        if not automation:
            return
            
        execute_at = _utcnow() + timedelta(minutes=automation.delay_minutes)
        action = PendingCrmAction(
            automation_id=automation.id,
            target_persona_id=target_persona_id,
            execute_at=execute_at,
            status="pending"
        )
        db.add(action)
        db.commit()


# Inicializar motor globalmente
engine = AutomationEngine()
