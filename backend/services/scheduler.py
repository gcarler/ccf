from __future__ import annotations
import threading
import time
import logging
from backend.core.database import SessionLocal
from backend.analytics.proactive_ia import run_proactive_analysis
import asyncio

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

def start_background_scheduler():
    """Initializes and starts the background task loop using native threads."""
    log.info("Starting Native Background Scheduler...")
    
    def run_loop():
        # Wait a bit for the system to stabilize
        time.sleep(10)
        while True:
            try:
                run_ai_analysis()
            except Exception as e:
                log.error(f"Scheduler loop error: {e}")
            
            # Run every hour (3600 seconds)
            time.sleep(3600)

    thread = threading.Thread(target=run_loop, daemon=True)
    thread.start()
    log.info("Background Scheduler is running in a native daemon thread (No external dependencies).")
