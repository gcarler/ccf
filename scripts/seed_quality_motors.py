from __future__ import annotations
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from backend.core.database import SessionLocal
from backend.management.schema import upgrade_with_optional_bootstrap
from backend import models, crud, schemas

def seed_quality_motors():
    db = SessionLocal()
    try:
        print("--- Applying migrations ---")
        upgrade_with_optional_bootstrap()
        
        print("--- Seeding Gamification Levels ---")
        levels = [
            {"title": "Aspirante", "min_xp": 0, "icon_key": "user"},
            {"title": "Discípulo", "min_xp": 500, "icon_key": "shield"},
            {"title": "Líder", "min_xp": 2000, "icon_key": "star"},
            {"title": "Pastor", "min_xp": 5000, "icon_key": "award"},
        ]
        for l in levels:
            if not db.query(models.Level).filter(models.Level.title == l["title"]).first():
                db.add(models.Level(**l))
        
        print("--- Seeding Initial Badges ---")
        badges = [
            {"name": "Primer Paso", "description": "Completaste tu primera lección.", "icon_key": "zap", "xp_reward": 50},
            {"name": "Estudiante Estrella", "description": "Obtuviste 100% en un examen.", "icon_key": "award", "xp_reward": 100},
            {"name": "Corazón Generoso", "description": "Realizaste tu primera donación.", "icon_key": "heart", "xp_reward": 200},
        ]
        for b in badges:
            if not db.query(models.Badge).filter(models.Badge.name == b["name"]).first():
                db.add(models.Badge(**b))

        print("--- Seeding AI Initial Insights ---")
        insights = [
            {"title": "Bienvenida al Sistema", "insight_type": "info", "payload": "Optimus Brain está listo para analizar tu crecimiento espiritual."},
        ]
        for i in insights:
            crud.create_agent_insight(db, schemas.AgentInsightCreate(**i))

        db.commit()
        print("--- Quality Seeding Complete! ---")
    except Exception as e:
        print(f"Error during seeding: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_quality_motors()
