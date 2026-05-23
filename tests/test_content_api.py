from backend import models
from backend.core.security import get_password_hash


def seed_admin(db_session, email="admin@example.com", password="secret123"):
    user = models.User(
        username="admin",
        email=email,
        password_hash=get_password_hash(password),
        role="admin",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def auth_headers(client, email="admin@example.com", password="secret123"):
    response = client.post(
        "/api/auth/login",
        data={"username": email, "password": password, "grant_type": "password"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_wiki_content_accepts_plain_text(client, db_session):
    seed_admin(db_session)
    headers = auth_headers(client)

    create_response = client.post(
        "/api/content/wiki_support",
        json={"title": "Wiki soporte", "content": "<h1>Guia</h1><p>Texto libre</p>"},
        headers=headers,
    )
    assert create_response.status_code == 200
    assert create_response.json()["content"] == "<h1>Guia</h1><p>Texto libre</p>"

    update_response = client.patch(
        "/api/content/wiki_support",
        json={"content": "<p>Actualizado</p>"},
        headers=headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["content"] == "<p>Actualizado</p>"


def test_non_wiki_content_still_requires_json(client, db_session):
    seed_admin(db_session)
    headers = auth_headers(client)

    response = client.post(
        "/api/content/faro_home_hero",
        json={"title": "Hero", "content": "texto libre"},
        headers=headers,
    )

    assert response.status_code == 422


def test_rich_text_content_keys_accept_html_without_json(client, db_session):
    seed_admin(db_session)
    headers = auth_headers(client)

    response = client.post(
        "/api/content/faro_about_body_html",
        json={
            "title": "Cuerpo nosotros",
            "content": "<h2>Somos FARO</h2><p>Texto enriquecido.</p>",
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["content"] == "<h2>Somos FARO</h2><p>Texto enriquecido.</p>"
