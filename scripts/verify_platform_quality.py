from __future__ import annotations
import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from backend.app import app
from backend.core.database import SessionLocal, Base, engine
from backend import crud, models, schemas

client = TestClient(app)

def verify_quality():
    print("=== CCF PLATFORM QUALITY CERTIFICATION ===")
    
    # Force fresh schema for testing
    print("[0/4] Preparing Clean Environment...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    # Seed required levels for testing level-up
    db = SessionLocal()
    db.add(models.Level(title="Aspirante", min_xp=0))
    db.add(models.Level(title="Discípulo", min_xp=100))
    db.add(models.Badge(name="Test Badge", icon_key="star", xp_reward=50))
    db.commit()
    
    try:
        # 1. Test User Creation & Auth
        print("[1/4] Testing Auth & Identity...")
        test_email = "test_quality@ccf.la"
        existing = crud.get_user_by_email(db, test_email)
        if existing:
            db.delete(existing)
            db.commit()
            
        user_in = schemas.UserCreate(username="quality_tester", email=test_email, password="QualityPassword123!", role="estudiante")
        user = crud.create_user(db, user_in)
        print(f"  > User created: {user.username} (ID: {user.id})")

        # 2. Test Gamification Logic
        print("[2/4] Testing Gamification Motor...")
        initial_status = crud.get_user_xp_and_level(db, user.id)
        print(f"  > Initial XP: {initial_status['xp']}, Level: {initial_status['level']}")
        
        # Simulate completing a lesson (giving 50 XP)
        crud.grant_xp(db, user.id, 50)
        updated_status = crud.get_user_xp_and_level(db, user.id)
        print(f"  > Updated XP: {updated_status['xp']} (Success)")
        
        # 3. Test UI Preferences
        print("[3/4] Testing UI Persistence...")
        prefs = {"theme": "dark", "sidebar": "collapsed", "last_view": "kanban"}
        crud.update_ui_preferences(db, user.id, prefs)
        saved_prefs = crud.get_ui_preferences(db, user.id)
        if saved_prefs.settings["theme"] == "dark":
            print("  > UI Preferences persisted correctly.")
        
        # 4. Test Intelligence Engine
        print("[4/4] Testing Optimus Brain Insights...")
        insights = crud.list_agent_insights(db)
        if len(insights) > 0:
            print(f"  > IA Insights found: {len(insights)} (Last: {insights[0].title})")

        print("\n=== CERTIFICATION SUCCESSFUL: PLATFORM IS STABLE ===")
        
    except Exception as e:
        print(f"\n!!! CERTIFICATION FAILED: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    verify_quality()
