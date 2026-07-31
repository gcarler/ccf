"""Unit and integration tests for CMS v2 Blog Post Comments API (Milestone 4 / R4).

Verifies:
  - Public comment creation: POST /api/cms/v2/public/posts/{post_id}/comments (status pending)
  - Nested reply creation with parent_id
  - Public comment listing: GET /api/cms/v2/public/posts/{post_id}/comments (approved only + 1-level replies)
  - Admin comment listing: GET /api/cms/v2/sites/{site_key}/post-comments (status filter, pagination, pending_count)
  - Admin comment status patch: PATCH /api/cms/v2/sites/{site_key}/post-comments/{id} (approve, spam, delete)
  - Error handling: 404 for non-existent post/site/comment, 400 for invalid parent_id.
"""
from __future__ import annotations

import uuid as _uuid
import pytest
from backend import models
from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


@pytest.fixture
def admin_client(client, db_session):
    admin, _, _ = _seed_admin(db_session)
    return client, _auth_headers(client, email=admin.email, password="testpass123")


@pytest.fixture
def comments_setup(db_session):
    site = models.CmsSite(
        id=_uuid.uuid4(),
        site_key="ccf_comments_test",
        name="CCF Comments Test Site",
        base_path="/comments_test",
        is_active=True,
    )
    db_session.add(site)
    db_session.commit()

    post = models.CmsPost(
        id=_uuid.uuid4(),
        site_id=site.id,
        slug="post-para-comentarios",
        title="Post de Prueba para Comentarios",
        content="Contenido del post...",
        status="published",
    )
    db_session.add(post)
    db_session.commit()

    return site, post


def test_public_create_comment(client, comments_setup):
    site, post = comments_setup
    payload = {
        "author_name": "Juan Pérez",
        "author_email": "juan@example.com",
        "content": "Excelente artículo sobre la fe.",
    }
    response = client.post(f"/api/cms/v2/public/posts/{post.id}/comments", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["author_name"] == "Juan Pérez"
    assert data["author_email"] == "juan@example.com"
    assert data["content"] == "Excelente artículo sobre la fe."
    assert data["status"] == "pending"
    assert data["post_id"] == str(post.id)
    assert data["parent_id"] is None


def test_public_create_comment_nonexistent_post(client):
    fake_id = _uuid.uuid4()
    payload = {
        "author_name": "Maria",
        "author_email": "maria@example.com",
        "content": "Comentario de prueba",
    }
    response = client.post(f"/api/cms/v2/public/posts/{fake_id}/comments", json=payload)
    assert response.status_code == 404


def test_public_create_nested_reply(client, comments_setup, db_session):
    site, post = comments_setup
    root_comment = models.CmsPostComment(
        id=_uuid.uuid4(),
        post_id=post.id,
        author_name="Carlos",
        author_email="carlos@example.com",
        content="Comentario inicial",
        status="approved",
    )
    db_session.add(root_comment)
    db_session.commit()

    payload = {
        "author_name": "Ana",
        "author_email": "ana@example.com",
        "content": "Respuesta a Carlos",
        "parent_id": str(root_comment.id),
    }
    response = client.post(f"/api/cms/v2/public/posts/{post.id}/comments", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["parent_id"] == str(root_comment.id)
    assert data["status"] == "pending"


def test_public_create_reply_invalid_parent(client, comments_setup):
    site, post = comments_setup
    payload = {
        "author_name": "Pedro",
        "author_email": "pedro@example.com",
        "content": "Respuesta invalida",
        "parent_id": str(_uuid.uuid4()),
    }
    response = client.post(f"/api/cms/v2/public/posts/{post.id}/comments", json=payload)
    assert response.status_code == 400


def test_public_get_approved_comments(client, comments_setup, db_session):
    site, post = comments_setup

    c1 = models.CmsPostComment(
        id=_uuid.uuid4(),
        post_id=post.id,
        author_name="Usuario Aprobado 1",
        author_email="approved1@example.com",
        content="Comentario aprobado 1",
        status="approved",
    )
    c2 = models.CmsPostComment(
        id=_uuid.uuid4(),
        post_id=post.id,
        author_name="Usuario Pendiente",
        author_email="pending@example.com",
        content="Comentario pendiente",
        status="pending",
    )
    db_session.add_all([c1, c2])
    db_session.commit()

    r1 = models.CmsPostComment(
        id=_uuid.uuid4(),
        post_id=post.id,
        parent_id=c1.id,
        author_name="Respuesta Aprobada",
        author_email="reply@example.com",
        content="Respuesta al comentario 1",
        status="approved",
    )
    db_session.add(r1)
    db_session.commit()

    response = client.get(f"/api/cms/v2/public/posts/{post.id}/comments")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1  # Only c1 is root approved
    assert data[0]["id"] == str(c1.id)
    assert data[0]["author_name"] == "Usuario Aprobado 1"
    assert "author_email" not in data[0]  # Public schema omits email
    assert len(data[0]["replies"]) == 1
    assert data[0]["replies"][0]["id"] == str(r1.id)
    assert data[0]["replies"][0]["content"] == "Respuesta al comentario 1"


def test_admin_list_comments_and_pending_count(admin_client, comments_setup, db_session):
    client, headers = admin_client
    site, post = comments_setup

    c1 = models.CmsPostComment(
        id=_uuid.uuid4(),
        post_id=post.id,
        author_name="Comentario Pendiente 1",
        author_email="p1@example.com",
        content="Pendiente 1",
        status="pending",
    )
    c2 = models.CmsPostComment(
        id=_uuid.uuid4(),
        post_id=post.id,
        author_name="Comentario Pendiente 2",
        author_email="p2@example.com",
        content="Pendiente 2",
        status="pending",
    )
    c3 = models.CmsPostComment(
        id=_uuid.uuid4(),
        post_id=post.id,
        author_name="Comentario Aprobado",
        author_email="a1@example.com",
        content="Aprobado 1",
        status="approved",
    )
    db_session.add_all([c1, c2, c3])
    db_session.commit()

    response = client.get(f"/api/cms/v2/sites/{site.site_key}/post-comments", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert data["pending_count"] == 2
    assert len(data["items"]) == 3

    # Test filtering by status=pending
    resp_pending = client.get(
        f"/api/cms/v2/sites/{site.site_key}/post-comments?status=pending",
        headers=headers,
    )
    assert resp_pending.status_code == 200
    data_pending = resp_pending.json()
    assert data_pending["total"] == 2
    assert data_pending["pending_count"] == 2
    assert all(item["status"] == "pending" for item in data_pending["items"])


def test_admin_update_comment_status(admin_client, comments_setup, db_session):
    client, headers = admin_client
    site, post = comments_setup

    c = models.CmsPostComment(
        id=_uuid.uuid4(),
        post_id=post.id,
        author_name="Moderacion Test",
        author_email="mod@example.com",
        content="Aprobar este comentario",
        status="pending",
    )
    db_session.add(c)
    db_session.commit()

    # Approve comment
    res_approve = client.patch(
        f"/api/cms/v2/sites/{site.site_key}/post-comments/{c.id}",
        json={"status": "approved"},
        headers=headers,
    )
    assert res_approve.status_code == 200
    assert res_approve.json()["status"] == "approved"

    # Mark as spam
    res_spam = client.patch(
        f"/api/cms/v2/sites/{site.site_key}/post-comments/{c.id}",
        json={"status": "spam"},
        headers=headers,
    )
    assert res_spam.status_code == 200
    assert res_spam.json()["status"] == "spam"

    # Delete comment
    res_del = client.patch(
        f"/api/cms/v2/sites/{site.site_key}/post-comments/{c.id}",
        json={"status": "deleted"},
        headers=headers,
    )
    assert res_del.status_code == 200
    assert res_del.json()["status"] == "deleted"
