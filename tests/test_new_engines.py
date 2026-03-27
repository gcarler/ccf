from __future__ import annotations
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from backend import models, crud, schemas

def test_gamification_xp_and_levelup(db_session: Session):
    # 1. Setup levels
    lvl1 = models.Level(title="Novato", min_xp=0)
    lvl2 = models.Level(title="Experto", min_xp=100)
    db_session.add_all([lvl1, lvl2])
    db_session.commit()

    # 2. Create user
    user = models.User(username="gametest", email="game@test.com", password_hash="hash", role="estudiante")
    db_session.add(user)
    db_session.commit()

    # 3. Grant XP
    crud.grant_xp(db_session, user.id, 150)
    
    # 4. Verify level up
    db_session.refresh(user)
    assert user.xp == 150
    assert user.current_level_id == lvl2.id

def test_ui_preferences_persistence(db_session: Session):
    # 1. Create user
    user = models.User(username="preftest", email="pref@test.com", password_hash="hash", role="estudiante")
    db_session.add(user)
    db_session.commit()

    # 2. Save prefs
    prefs = {"theme": "dark", "layout": "compact"}
    crud.update_ui_preferences(db_session, user.id, prefs)

    # 3. Retrieve and verify
    saved = crud.get_ui_preferences(db_session, user.id)
    assert saved.settings["theme"] == "dark"
    assert saved.settings["layout"] == "compact"

def test_badge_awarding_uniqueness(db_session: Session):
    # 1. Setup
    user = models.User(username="badgetest", email="badge@test.com", password_hash="hash", role="estudiante")
    badge = models.Badge(name="Medalla Pro", icon_key="star", xp_reward=10)
    db_session.add_all([user, badge])
    db_session.commit()

    # 2. Award twice
    crud.award_badge(db_session, user.id, "Medalla Pro")
    crud.award_badge(db_session, user.id, "Medalla Pro")

    # 3. Verify uniqueness
    count = db_session.query(models.UserBadge).filter(models.UserBadge.user_id == user.id).count()
    assert count == 1
