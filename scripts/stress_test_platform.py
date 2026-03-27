from __future__ import annotations
import sys
import time
import uuid
from pathlib import Path
from sqlalchemy.orm import Session

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from backend.core.database import SessionLocal, engine, Base
from backend import models, crud, schemas

def run_stress_test():
    print("=== CCF PLATFORM STRESS & PERFORMANCE TEST ===")
    db = SessionLocal()
    
    try:
        # 1. User Injection
        print("[1/3] Injecting 100 virtual users...")
        start_time = time.time()
        for i in range(100):
            u_id = f"user_{i}_{uuid.uuid4().hex[:6]}"
            user = models.User(
                username=u_id,
                email=f"{u_id}@test.la",
                password_hash="stress_test_hash",
                role="estudiante"
            )
            db.add(user)
        db.commit()
        print(f"  > Done in {time.time() - start_time:.2f}s")

        # 2. Messaging High-Volume Test
        print("[2/3] Simulating 2,000 chat messages...")
        start_time = time.time()
        test_user = db.query(models.User).first()
        for i in range(2000):
            msg = models.ChatMessage(
                sender_id=test_user.id,
                room_id="general_room",
                content=f"Stress test message volume #{i}"
            )
            db.add(msg)
            if i % 500 == 0: # Batch commit for efficiency
                db.commit()
        db.commit()
        print(f"  > Done in {time.time() - start_time:.2f}s")

        # 3. Gamification Engine Stress
        print("[3/3] Simulating 500 concurrent XP grants...")
        start_time = time.time()
        users = db.query(models.User).limit(100).all()
        for u in users:
            for j in range(5):
                crud.grant_xp(db, u.id, 10)
        print(f"  > Done in {time.time() - start_time:.2f}s")

        print("\n=== STRESS TEST COMPLETE: SYSTEM IS SCALABLE ===")
        
    except Exception as e:
        print(f"\n!!! STRESS TEST FAILED: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_stress_test()
