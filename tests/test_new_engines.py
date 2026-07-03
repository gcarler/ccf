from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from backend import crud, models


def _create_test_user(db: Session, username: str, email: str) -> models.User:
    """Create a User (auth) with required Persona and Sede."""
    sede = models.Sede(
        id=uuid.uuid4(),
        nombre=f"Sede {username}",
        ciudad="Bogota",
        es_activa=True,
    )
    db.add(sede)
    db.flush()

    persona = models.Persona(
        id=uuid.uuid4(),
        sede_id=sede.id,
        first_name=username,
        last_name="Test",
        email=email,
    )
    db.add(persona)
    db.flush()

    user = models.User(
        id=persona.id,
        sede_id=sede.id,
        username=username,
        email=email,
        password_hash="hash",
        is_active=True,
    )
    db.add(user)
    db.commit()
    return user


def test_gamification_xp_and_levelup(db_session: Session):
    # 1. Setup levels
    lvl1 = models.Level(title="Novato", min_xp=0)
    lvl2 = models.Level(title="Experto", min_xp=100)
    db_session.add_all([lvl1, lvl2])
    db_session.commit()

    # 2. Create user
    user = _create_test_user(db_session, "gametest", "game@test.com")

    # 3. Grant XP
    crud.grant_xp(db_session, user.id, 150)

    # 4. Verify level up
    db_session.refresh(user)
    assert user.xp == 150
    assert user.current_level_id == lvl2.id


def test_ui_preferences_persistence(db_session: Session):
    # 1. Create user
    user = _create_test_user(db_session, "preftest", "pref@test.com")

    # 2. Save prefs
    prefs = {"theme": "dark", "layout": "compact"}
    crud.update_ui_preferences(db_session, user.id, prefs)

    # 3. Retrieve and verify
    saved = crud.get_ui_preferences(db_session, user.id)
    assert saved.settings["theme"] == "dark"
    assert saved.settings["layout"] == "compact"


def test_badge_awarding_uniqueness(db_session: Session):
    # 1. Setup
    user = _create_test_user(db_session, "badgetest", "badge@test.com")
    badge = models.Badge(name="Medalla Pro", icon_key="star", xp_reward=10)
    db_session.add(badge)
    db_session.commit()

    # 2. Award twice
    crud.award_badge(db_session, user.id, "Medalla Pro")
    crud.award_badge(db_session, user.id, "Medalla Pro")

    # 3. Verify uniqueness
    count = (
        db_session.query(models.UserBadge)
        .filter(models.UserBadge.user_id == user.id)
        .count()
    )
    assert count == 1
