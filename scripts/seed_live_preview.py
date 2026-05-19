from __future__ import annotations
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from backend.core.database import SessionLocal
from backend.management.schema import reset_database_for_local_bootstrap
from backend import models, crud, schemas

def seed_live_preview():
    print("=== CCF LIVE PREVIEW SEEDING (CALIDAD) ===")
    
    # Force fresh schema for testing and preview
    print("[0/4] Re-syncing Database Schema...")
    reset_database_for_local_bootstrap()
    
    db = SessionLocal()
    
    try:
        # 1. Seed Courses
        print("[1/4] Seeding Active Courses...")
        c1 = models.Course(code="PAST-01", title="Liderazgo Pastoral I", modality="formal", xp_per_lesson=50)
        c2 = models.Course(code="BIBL-02", title="Hermenéutica Avanzada", modality="no_formal", xp_per_lesson=30)
        db.add_all([c1, c2])
        db.commit()

        # 2. Seed Candidates (Users with high progress)
        print("[2/4] Seeding Academic Candidates...")
        u1 = models.User(username="juan_pro", email="juan@ccf.la", password_hash="hash", role="estudiante", xp=450)
        db.add(u1)
        db.commit()
        db.refresh(u1)
        
        enr = models.Enrollment(user_id=u1.id, course_id=c1.id, progress_percent=95, status="active")
        db.add(enr)
        db.commit()

        # 3. Seed Announcements
        print("[3/4] Seeding Institutional Announcements...")
        crud.create_announcement(db, {
            "title": "Gran Vigilia de Oración 2026",
            "content": "Hermanos, los invitamos este viernes a las 7:00 PM a nuestro auditorio principal."
        })
        crud.create_announcement(db, {
            "title": "Nuevas Becas de Formación",
            "content": "Ya están abiertos los cupos para el diplomado en Misiones Transculturales."
        })

        # 4. Seed Forum Activity
        print("[4/4] Seeding Forum Debates...")
        t1 = models.ForumThread(title="Duda sobre Romanos 8:28", category="Teología", author_id=u1.id)
        db.add(t1)
        db.commit()

        print("\n=== SEEDING COMPLETE: PLATFORM IS NOW ALIVE ===")
        
    except Exception as e:
        print(f"\n!!! SEEDING FAILED: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_live_preview()
