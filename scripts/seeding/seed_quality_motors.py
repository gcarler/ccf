from __future__ import annotations

import sys
from pathlib import Path

# Locate the project root by walking up until we find the `backend/`
# package. This works whether the script lives in scripts/, scripts/seeding/
# scripts/migrations/, scripts/auditing/ or any other nested folder.
_HERE = Path(__file__).resolve()
_PROJECT_ROOT = next(
    (p for p in _HERE.parents if (p / "backend" / "__init__.py").is_file()),
    None,
)
if _PROJECT_ROOT is None:
    raise RuntimeError(f"backend package not found above {_HERE}")
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.core.database import SessionLocal
from backend.management.schema import upgrade_with_optional_bootstrap


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
            if (
                not db.query(models.Level)
                .filter(models.Level.title == l["title"])
                .first()
            ):
                db.add(models.Level(**l))

        print("--- Seeding Initial Badges ---")
        badges = [
            {
                "name": "Primer Paso",
                "description": "Completaste tu primera lección.",
                "icon_key": "zap",
                "xp_reward": 50,
            },
            {
                "name": "Estudiante Estrella",
                "description": "Obtuviste 100% en un examen.",
                "icon_key": "award",
                "xp_reward": 100,
            },
            {
                "name": "Corazón Generoso",
                "description": "Realizaste tu primera donación.",
                "icon_key": "heart",
                "xp_reward": 200,
            },
        ]
        for b in badges:
            if (
                not db.query(models.Badge)
                .filter(models.Badge.name == b["name"])
                .first()
            ):
                db.add(models.Badge(**b))

        print("--- Seeding AI Initial Insights ---")
        insights = [
            {
                "title": "Bienvenida al Sistema",
                "insight_type": "info",
                "payload": "Optimus Brain está listo para analizar tu crecimiento espiritual.",
            },
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
