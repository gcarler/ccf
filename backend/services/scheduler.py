from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timedelta, timezone

from backend.analytics.proactive_ia import run_proactive_analysis
from backend.core.database import SessionLocal
from backend.api.evangelism_shared import sessions_grupo_has_estado_habilitacion

log = logging.getLogger(__name__)


def run_ai_analysis():
    """Wrapper to run AI analysis with its own DB session."""
    log.info("Automatic Task: Running Proactive AI Analysis...")
    db = SessionLocal()
    try:
        insights_count = run_proactive_analysis(db)
        if insights_count > 0:
            log.info(f"AI generated {insights_count} new insights.")
    except Exception as e:
        log.error(f"Error in automatic AI task: {e}")
    finally:
        db.close()


def run_session_governance():
    """Habilita las sesiones de la semana en curso y cierra las de semanas pasadas."""
    from backend.models_evangelism import HabilitacionSesionEnum, SesionGrupo

    db = SessionLocal()
    try:
        if not sessions_grupo_has_estado_habilitacion(db):
            return
        now = datetime.now(timezone.utc)
        # Semana en curso: lunes 00:00 → domingo 23:59
        days_since_monday = now.weekday()
        week_start = (now - timedelta(days=days_since_monday)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        week_end = week_start + timedelta(days=7)

        # Habilitar sesiones dentro de la semana actual que aún no fueron habilitadas
        habilitadas = db.query(SesionGrupo).filter(
            SesionGrupo.fecha_sesion >= week_start,
            SesionGrupo.fecha_sesion < week_end,
            SesionGrupo.estado_habilitacion == HabilitacionSesionEnum.DESHABILITADO.value,
            SesionGrupo.deleted_at.is_(None),
        ).update(
            {"estado_habilitacion": HabilitacionSesionEnum.HABILITADO.value},
            synchronize_session=False,
        )

        # Cerrar sesiones HABILITADAS de semanas anteriores
        cerradas = db.query(SesionGrupo).filter(
            SesionGrupo.fecha_sesion < week_start,
            SesionGrupo.estado_habilitacion == HabilitacionSesionEnum.HABILITADO.value,
            SesionGrupo.deleted_at.is_(None),
        ).update(
            {"estado_habilitacion": HabilitacionSesionEnum.CERRADO.value},
            synchronize_session=False,
        )

        db.commit()
        if habilitadas or cerradas:
            log.info(
                f"Session governance: {habilitadas} habilitadas, {cerradas} cerradas "
                f"(semana {week_start.date()} – {week_end.date()})"
            )
    except Exception as e:
        log.error(f"Error in session governance task: {e}")
        db.rollback()
    finally:
        db.close()


def start_background_scheduler():
    """Initializes and starts the background task loop using native threads."""
    log.info("Starting Native Background Scheduler...")

    def run_loop():
        time.sleep(10)
        last_governance_day = -1

        while True:
            try:
                run_ai_analysis()
            except Exception as e:
                log.error(f"Scheduler loop error (AI): {e}")

            # Gobernanza de sesiones: una vez al día
            try:
                today = datetime.now(timezone.utc).day
                if today != last_governance_day:
                    run_session_governance()
                    last_governance_day = today
            except Exception as e:
                log.error(f"Scheduler loop error (governance): {e}")

            time.sleep(3600)

    thread = threading.Thread(target=run_loop, daemon=True)
    thread.start()
    log.info(
        "Background Scheduler is running in a native daemon thread (No external dependencies)."
    )
