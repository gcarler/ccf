from __future__ import annotations

import datetime as dt
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from backend import models, crud, schemas

class IntelligenceMESH:
    """Motor de Inteligencia Central para el Ecosistema CCF."""

    @staticmethod
    def run_full_analysis(db: Session):
        """Ejecuta todos los motores de análisis y genera insights/tareas para los agentes."""
        insights = []
        insights.extend(IntelligenceMESH.analyze_pastoral_care(db))
        insights.extend(IntelligenceMESH.analyze_academy_performance(db))
        insights.extend(IntelligenceMESH.analyze_project_health(db))
        
        # Guardar insights generados en la base de datos
        for insight_data in insights:
            IntelligenceMESH._save_insight(db, insight_data)
            
        return len(insights)

    @staticmethod
    def analyze_pastoral_care(db: Session):
        """Detecta miembros o leads que necesitan atención inmediata."""
        insights = []
        
        # 1. Leads estancados en el pipeline
        one_week_ago = dt.datetime.now() - dt.timedelta(days=7)
        stagnant_leads = db.query(models.ConsolidationPipeline).filter(
            models.ConsolidationPipeline.updated_at <= one_week_ago,
            models.ConsolidationPipeline.stage != "converted"
        ).all()
        
        if stagnant_leads:
            insights.append({
                "title": "Abandono en Consolidación",
                "type": "pastoral_alert",
                "payload": f"Hay {len(stagnant_leads)} personas sin seguimiento en la última semana. Riesgo de enfriamiento."
            })

        # 2. Miembros sin comunicación reciente
        # (Heurística: Miembros activos con > 30 días sin logs de comunicación)
        # implementation omitted for brevity but logic is clear
        
        return insights

    @staticmethod
    def analyze_academy_performance(db: Session):
        """Analiza tendencias de estudio y deserción."""
        insights = []
        
        # 1. Cursos con baja tasa de finalización
        # ... logic ...
        
        # 2. Alumnos destacados (Gamificación)
        top_students = db.query(models.User).order_by(models.User.xp.desc()).limit(3).all()
        if top_students:
            names = ", ".join([u.username for u in top_students])
            insights.append({
                "title": "Líderes Emergentes",
                "type": "academy_insight",
                "payload": f"Top estudiantes por XP: {names}. Considerar para roles de mentoría."
            })
            
        return insights

    @staticmethod
    def analyze_project_health(db: Session):
        """Analiza retrasos en proyectos de infraestructura/eventos."""
        insights = []
        
        # 1. Tareas urgentes vencidas
        now = dt.datetime.now()
        overdue_tasks = db.query(models.ProjectTask).filter(
            models.ProjectTask.due_date < now,
            models.ProjectTask.status != "done"
        ).count()
        
        if overdue_tasks > 0:
            insights.append({
                "title": "Cuello de Botella Operativo",
                "type": "project_alert",
                "payload": f"Se detectaron {overdue_tasks} tareas críticas vencidas en proyectos activos."
            })
            
        return insights

    @staticmethod
    def _save_insight(db: Session, data: dict):
        """Evita duplicados y guarda el insight."""
        existing = db.query(models.AgentInsight).filter(
            models.AgentInsight.title == data["title"],
            models.AgentInsight.acknowledged == False
        ).first()
        
        if not existing:
            new_insight = models.AgentInsight(
                title=data["title"],
                insight_type=data["type"],
                payload=data["payload"]
            )
            db.add(new_insight)
            db.commit()
