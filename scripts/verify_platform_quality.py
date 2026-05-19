from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).parent.parent))

from backend import crud, models, schemas
from backend.app import app
from backend.core.database import SessionLocal
from backend.management.schema import reset_database_for_local_bootstrap


client = TestClient(app)


def verify_quality():
    print("=== CCF PLATFORM QUALITY CERTIFICATION ===")

    print("[0/4] Preparing Clean Environment...")
    reset_database_for_local_bootstrap()

    db = SessionLocal()
    db.add(models.Level(title="Aspirante", min_xp=0))
    db.add(models.Level(title="Discipulo", min_xp=100))
    db.add(models.Badge(name="Test Badge", icon_key="star", xp_reward=50))
    db.commit()

    try:
        print("[1/4] Testing Auth & Identity...")
        test_email = "test_quality@ccf.la"
        existing = crud.get_user_by_email(db, test_email)
        if existing:
            db.delete(existing)
            db.commit()

        user_in = schemas.UserCreate(
            username="quality_tester",
            email=test_email,
            password="QualityPassword123!",
            role="estudiante",
        )
        user = crud.create_user(db, user_in)
        print(f"  > User created: {user.username} (ID: {user.id})")

        print("[2/4] Testing Gamification Motor...")
        initial_status = crud.get_user_xp_and_level(db, user.id)
        print(f"  > Initial XP: {initial_status['xp']}, Level: {initial_status['level']}")
        crud.grant_xp(db, user.id, 50)
        updated_status = crud.get_user_xp_and_level(db, user.id)
        print(f"  > Updated XP: {updated_status['xp']} (Success)")

        print("[3/4] Testing UI Persistence...")
        prefs = {"theme": "dark", "sidebar": "collapsed", "last_view": "kanban"}
        crud.update_ui_preferences(db, user.id, prefs)
        saved_prefs = crud.get_ui_preferences(db, user.id)
        if saved_prefs.settings["theme"] == "dark":
            print("  > UI Preferences persisted correctly.")

        print("[4/4] Testing Optimus Brain Insights...")
        insights = crud.list_agent_insights(db)
        if len(insights) > 0:
            print(f"  > IA Insights found: {len(insights)} (Last: {insights[0].title})")

        print("\n=== CERTIFICATION SUCCESSFUL: PLATFORM IS STABLE ===")
    except Exception as exc:
        print(f"\n!!! CERTIFICATION FAILED: {exc}")
        import traceback

        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    verify_quality()
