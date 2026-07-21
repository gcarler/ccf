from backend import models
from tests.conftest import auth_headers, seed_admin, seed_user_with_role


def test_admin_milestones_uuid_award_uses_auth_users(client, db_session):
    admin, _, _ = seed_admin(db_session)
    target_user, target_persona, _ = seed_user_with_role(
        db_session,
        role_name="persona",
        email="milestone-target@test.com",
        password="secret123",
    )

    badge = models.Medalla(
        name="Hito Admin",
        description="Hito de prueba",
        icon_key="star",
        xp_reward=25,
    )
    db_session.add(badge)
    db_session.commit()
    db_session.refresh(badge)

    headers = auth_headers(client, email=admin.email, password="testpass123")

    resp = client.post(
        "/api/admin/milestones/award",
        headers=headers,
        json={"badge_id": str(badge.id), "persona_id": str(target_persona.id)},
    )
    assert resp.status_code == 200
    assert resp.json()["awarded"] == 1

    rows = db_session.query(models.MedallaUsuario).filter(
        models.MedallaUsuario.user_id == target_user.id,
        models.MedallaUsuario.badge_id == badge.id,
    ).all()
    assert len(rows) == 1
