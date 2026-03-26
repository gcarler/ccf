from __future__ import annotations
import logging
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend import models, crud, schemas
from datetime import datetime, timedelta

log = logging.getLogger(__name__)

def run_proactive_analysis(db: Session):
    """
    Main engine for Optimus Brain proactive insights.
    Scans DB for patterns and creates AgentInsight records.
    """
    log.info("Starting Proactive AI Analysis...")
    insights_created = 0

    # 1. Analyze Academy Attrition Risk
    stale_enrollments = db.query(models.Enrollment).filter(
        models.Enrollment.status == "active",
        models.Enrollment.progress_percent < 50,
        models.Enrollment.created_at < (datetime.utcnow() - timedelta(days=30))
    ).all()

    if len(stale_enrollments) > 0:
        crud.create_agent_insight(db, schemas.AgentInsightCreate(
            title="Riesgo de Deserción Académica",
            insight_type="predictive",
            payload=f"Se detectaron {len(stale_enrollments)} estudiantes con progreso estancado hace más de 30 días. Se recomienda campaña de re-engagement."
        ))
        insights_created += 1

    # 2. Analyze CRM Pipeline Velocity
    new_leads = db.query(models.ConsolidationPipeline).filter(
        models.ConsolidationPipeline.stage == "new",
        models.ConsolidationPipeline.created_at < (datetime.utcnow() - timedelta(days=3))
    ).all()

    if len(new_leads) > 0:
        crud.create_agent_insight(db, schemas.AgentInsightCreate(
            title="Cuello de Botella en Consolidación",
            insight_type="operational",
            payload=f"Hay {len(new_leads)} nuevos prospectos esperando llamada inicial por más de 72 horas."
        ))
        insights_created += 1

    # 3. High Performance Recognition
    top_performers = db.query(models.User).filter(models.User.xp > 1000).limit(5).all()
    if top_performers:
        crud.create_agent_insight(db, schemas.AgentInsightCreate(
            title="Potencial de Liderazgo Detectado",
            insight_type="growth",
            payload=f"Identificados {len(top_performers)} usuarios con XP superior a 1000. Candidatos ideales para el próximo nivel de Liderazgo."
        ))
        insights_created += 1

    db.commit()
    return insights_created
