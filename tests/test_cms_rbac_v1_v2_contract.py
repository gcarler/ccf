"""RBAC parity regressions for the CMS v1 compatibility surface and v2."""

from __future__ import annotations

import uuid

from tests.conftest import auth_headers, seed_user_with_role


def test_editor_role_can_mutate_v1_media(client, db_session):
    seed_user_with_role(
        db_session,
        role_name="EDITOR",
        email="cms-rbac-editor@example.com",
        password="testpass123",
        permisos={
            "cms:read": "allow",
            "cms:edit": "allow",
            "profile:manage": "allow",
        },
    )
    headers = auth_headers(client, email="cms-rbac-editor@example.com")

    response = client.post(
        "/api/cms/media",
        headers=headers,
        json={
            "url": "/uploads/editor.png",
            "alt_text": "editorial asset",
            "section": "hero",
            "tags": [],
        },
    )
    assert response.status_code == 201, response.text


def test_editor_cannot_run_destructive_media_operations(client, db_session):
    """Editors may mutate editorial media, but not cleanup or hard-delete."""
    seed_user_with_role(
        db_session,
        role_name="EDITOR",
        email="cms-rbac-editor-destructive@example.com",
        password="testpass123",
        permisos={
            "cms:read": "allow",
            "cms:edit": "allow",
            "profile:manage": "allow",
        },
    )
    headers = auth_headers(client, email="cms-rbac-editor-destructive@example.com")

    cleanup_response = client.post("/api/cms/media/cleanup?dry_run=true", headers=headers)
    assert cleanup_response.status_code == 403, cleanup_response.text

    media_response = client.post(
        "/api/cms/media",
        headers=headers,
        json={
            "url": "/uploads/editor-destructive.png",
            "alt_text": "editorial asset",
            "section": "hero",
            "tags": [],
        },
    )
    assert media_response.status_code == 201, media_response.text
    media_id = media_response.json()["id"]

    hard_delete_response = client.delete(f"/api/cms/media/{media_id}?permanent=true", headers=headers)
    assert hard_delete_response.status_code == 403, hard_delete_response.text


def test_publisher_role_can_run_media_cleanup_and_hard_delete(client, db_session):
    """Publishers retain access to operational cleanup and hard-delete."""
    seed_user_with_role(
        db_session,
        role_name="COORDINADOR",
        email="cms-rbac-publisher@example.com",
        password="testpass123",
        permisos={
            "cms:read": "allow",
            "cms:edit": "allow",
            "profile:manage": "allow",
        },
    )
    headers = auth_headers(client, email="cms-rbac-publisher@example.com")

    response = client.post("/api/cms/media/cleanup?dry_run=true", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["dry_run"] is True

    media_response = client.post(
        "/api/cms/media",
        headers=headers,
        json={
            "url": "/uploads/publisher-hard-delete.png",
            "alt_text": "publisher asset",
            "section": "hero",
            "tags": [],
        },
    )
    assert media_response.status_code == 201, media_response.text
    media_id = media_response.json()["id"]
    hard_delete_response = client.delete(f"/api/cms/media/{media_id}?permanent=true", headers=headers)
    assert hard_delete_response.status_code == 204, hard_delete_response.text


def test_lector_with_manual_cms_edit_grant_cannot_mutate_v1_or_v2(client, db_session):
    """A granular grant must not bypass the nominal CMS editor role gate.

    CMS v1 historically relied only on ``cms:edit`` while v2 also checked
    ``CMS_EDITOR_ROLES``. Keep the compatibility router, but make both
    surfaces reject the same nominal LECTOR role consistently.
    """
    seed_user_with_role(
        db_session,
        role_name="LECTOR",
        email="cms-rbac-lector@example.com",
        password="testpass123",
        permisos={
            "cms:read": "allow",
            "cms:edit": "allow",
            "profile:manage": "allow",
        },
    )
    headers = auth_headers(client, email="cms-rbac-lector@example.com")

    v1_response = client.post(
        "/api/cms/media",
        headers=headers,
        json={
            "url": "/uploads/lector.png",
            "alt_text": "should be blocked",
            "section": "hero",
            "tags": [],
        },
    )
    assert v1_response.status_code == 403, v1_response.text

    v2_response = client.post(
        f"/api/cms/v2/images/optimize?media_id={uuid.uuid4()}",
        headers=headers,
    )
    assert v2_response.status_code == 403, v2_response.text
