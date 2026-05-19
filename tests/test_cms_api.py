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


def test_public_testimonials_only_returns_approved_items(client, db_session):
    seed_admin(db_session)
    headers = auth_headers(client)

    approved = client.post(
        "/api/cms/testimonials",
        json={
            "content": "Historia aprobada",
            "emotion": "Fe",
            "media_type": "video",
            "video_url": "https://cdn.example.org/testimonio.mp4",
            "is_approved": True,
        },
        headers=headers,
    )
    pending = client.post(
        "/api/cms/testimonials",
        json={"content": "Historia pendiente", "emotion": "Fe", "is_approved": False},
        headers=headers,
    )
    assert approved.status_code == 201
    assert pending.status_code == 201

    public_rows = client.get("/api/cms/testimonials")
    assert public_rows.status_code == 200
    contents = [row["content"] for row in public_rows.json()]
    assert "Historia aprobada" in contents
    assert "Historia pendiente" not in contents
    public_approved = next(row for row in public_rows.json() if row["content"] == "Historia aprobada")
    assert public_approved["media_type"] == "video"
    assert public_approved["video_url"] == "https://cdn.example.org/testimonio.mp4"

    pending_public = client.get(f"/api/cms/testimonials/{pending.json()['id']}")
    assert pending_public.status_code == 404

    pending_admin = client.get(
        f"/api/admin/testimonials/{pending.json()['id']}",
        headers=headers,
    )
    assert pending_admin.status_code == 200
    assert pending_admin.json()["content"] == "Historia pendiente"

    updated = client.patch(
        f"/api/admin/testimonials/{approved.json()['id']}",
        json={
            "media_type": "podcast",
            "podcast_url": "https://cdn.example.org/testimonio.mp3",
            "show_on_home": True,
        },
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["media_type"] == "podcast"
    assert updated.json()["podcast_url"] == "https://cdn.example.org/testimonio.mp3"
    assert updated.json()["show_on_home"] is True


def test_public_announcements_only_returns_published_items(client, db_session):
    seed_admin(db_session)
    headers = auth_headers(client)

    published = client.post(
        "/api/cms/announcements",
        json={"title": "Aviso publicado", "content": "Visible", "category": "General", "status": "published"},
        headers=headers,
    )
    draft = client.post(
        "/api/cms/announcements",
        json={"title": "Aviso borrador", "content": "Oculto", "category": "General", "status": "draft"},
        headers=headers,
    )
    archived = client.post(
        "/api/cms/announcements",
        json={"title": "Aviso archivado", "content": "Oculto", "category": "General", "status": "archived"},
        headers=headers,
    )
    assert published.status_code == 201
    assert draft.status_code == 201
    assert archived.status_code == 201

    public_rows = client.get("/api/cms/announcements")
    assert public_rows.status_code == 200
    titles = [row["title"] for row in public_rows.json()]
    assert titles == ["Aviso publicado"]

    assert client.get(f"/api/cms/announcements/{draft.json()['id']}").status_code == 404

    admin_rows = client.get("/api/admin/announcements", headers=headers)
    assert admin_rows.status_code == 200
    assert {row["status"] for row in admin_rows.json()} == {"published", "draft", "archived"}

    metrics = client.get("/api/cms/metrics", headers=headers)
    assert metrics.status_code == 200
    assert metrics.json()["announcements_total"] == 3
    assert metrics.json()["announcements_active"] == 1


def test_cms_media_metadata_can_be_created_searched_and_updated(client, db_session):
    seed_admin(db_session)
    headers = auth_headers(client)

    created = client.post(
        "/api/cms/media",
        json={
            "url": "/api/static/hero-faro.webp",
            "alt_text": "Hero inicial",
            "section": "builder",
            "tags": ["hero"],
            "filename": "hero-faro.webp",
            "mime_type": "image/webp",
            "file_size": 2048,
        },
        headers=headers,
    )
    assert created.status_code == 201
    media_id = created.json()["id"]
    assert created.json()["filename"] == "hero-faro.webp"
    assert created.json()["mime_type"] == "image/webp"

    searched = client.get("/api/cms/media?query=hero-faro", headers=headers)
    assert searched.status_code == 200
    assert [row["id"] for row in searched.json()] == [media_id]

    updated = client.patch(
        f"/api/cms/media/{media_id}",
        json={"alt_text": "Hero actualizado", "section": "landing", "tags": ["hero", "landing"]},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["alt_text"] == "Hero actualizado"
    assert updated.json()["section"] == "landing"
    assert updated.json()["tags"] == ["hero", "landing"]

    archived = client.delete(f"/api/cms/media/{media_id}", headers=headers)
    assert archived.status_code == 204
    assert client.get("/api/cms/media?query=hero-faro", headers=headers).json() == []

    with_archived = client.get("/api/cms/media?query=hero-faro&include_archived=true", headers=headers)
    assert with_archived.status_code == 200
    assert with_archived.json()[0]["status"] == "archived"

    restored = client.patch(f"/api/cms/media/{media_id}", json={"status": "active"}, headers=headers)
    assert restored.status_code == 200
    assert restored.json()["status"] == "active"


def test_public_cms_page_uses_published_snapshot_not_live_draft(client, db_session):
    seed_admin(db_session)
    headers = auth_headers(client)

    site = client.post(
        "/api/cms/v2/sites",
        json={"site_key": "snapshot", "name": "Snapshot", "base_path": "/snapshot", "is_active": True},
        headers=headers,
    )
    assert site.status_code == 201

    page = client.post(
        "/api/cms/v2/sites/snapshot/pages",
        json={
            "slug": "inicio",
            "title": "Inicio publicado",
            "seo_json": {
                "meta_title": "SEO publicado",
                "meta_description": "Descripcion publicada",
                "meta_image": "/publicada.jpg",
            },
        },
        headers=headers,
    )
    assert page.status_code == 201

    visible_section = client.post(
        "/api/cms/v2/sites/snapshot/pages/inicio/sections",
        json={
            "type": "hero",
            "props_json": {"title": "Titulo publicado"},
            "sort_order": 0,
            "is_visible": True,
        },
        headers=headers,
    )
    hidden_section = client.post(
        "/api/cms/v2/sites/snapshot/pages/inicio/sections",
        json={
            "type": "rich_text",
            "props_json": {"title": "No publico"},
            "sort_order": 1,
            "is_visible": False,
        },
        headers=headers,
    )
    assert visible_section.status_code == 201
    assert hidden_section.status_code == 201

    published = client.post(
        "/api/cms/v2/sites/snapshot/pages/inicio/workflow",
        json={"action": "publish", "notes": "Publicacion inicial"},
        headers=headers,
    )
    assert published.status_code == 200
    assert published.json()["published_version_id"] is not None

    publish_log = client.get("/api/cms/v2/sites/snapshot/pages/inicio/publish-log", headers=headers)
    assert publish_log.status_code == 200
    assert publish_log.json()[0]["action"] == "publish"
    assert publish_log.json()[0]["metadata_json"]["notes"] == "Publicacion inicial"

    draft_page = client.patch(
        "/api/cms/v2/sites/snapshot/pages/inicio",
        json={
            "title": "Inicio borrador",
            "seo_json": {
                "meta_title": "SEO borrador",
                "meta_description": "Descripcion borrador",
                "meta_image": "/borrador.jpg",
            },
        },
        headers=headers,
    )
    assert draft_page.status_code == 200

    edited = client.patch(
        f"/api/cms/v2/sites/snapshot/pages/inicio/sections/{visible_section.json()['id']}",
        json={"props_json": {"title": "Borrador sin publicar"}},
        headers=headers,
    )
    assert edited.status_code == 200

    preview_page = client.get("/api/cms/v2/sites/snapshot/pages/inicio/preview", headers=headers)
    assert preview_page.status_code == 200
    assert preview_page.json()["title"] == "Inicio borrador"
    assert preview_page.json()["seo_json"]["meta_title"] == "SEO borrador"
    preview_titles = [row["props_json"].get("title") for row in preview_page.json()["sections"]]
    assert preview_titles == ["Borrador sin publicar"]

    public_page = client.get("/api/cms/v2/public/sites/snapshot/pages/inicio")
    assert public_page.status_code == 200
    assert public_page.json()["title"] == "Inicio publicado"
    assert public_page.json()["seo_json"]["meta_title"] == "SEO publicado"
    section_titles = [row["props_json"].get("title") for row in public_page.json()["sections"]]
    assert section_titles == ["Titulo publicado"]

    archived_page = client.post(
        "/api/cms/v2/sites/snapshot/pages/inicio/workflow",
        json={"action": "archive", "notes": "Archivar sin eliminar"},
        headers=headers,
    )
    assert archived_page.status_code == 200
    assert archived_page.json()["status"] == "archived"
    assert client.get("/api/cms/v2/public/sites/snapshot/pages/inicio").status_code == 404

    restored_page = client.post(
        "/api/cms/v2/sites/snapshot/pages/inicio/workflow",
        json={"action": "revert_draft", "notes": "Restaurar a borrador"},
        headers=headers,
    )
    assert restored_page.status_code == 200
    assert restored_page.json()["status"] == "draft"
    restored_preview = client.get("/api/cms/v2/sites/snapshot/pages/inicio/preview", headers=headers)
    assert restored_preview.status_code == 200
    assert restored_preview.json()["title"] == "Inicio borrador"


def test_public_cms_menu_filters_non_public_items(client, db_session):
    seed_admin(db_session)
    headers = auth_headers(client)

    site_response = client.post(
        "/api/cms/v2/sites",
        json={"site_key": "web", "name": "Web", "base_path": "/web", "is_active": True},
        headers=headers,
    )
    assert site_response.status_code == 201

    menu_response = client.post(
        "/api/cms/v2/sites/web/menus",
        json={"menu_key": "main", "name": "Principal", "is_active": True},
        headers=headers,
    )
    assert menu_response.status_code == 201

    visible = client.post(
        "/api/cms/v2/sites/web/menus/main/items",
        json={"label": "Inicio", "href": "/web", "visibility": "public"},
        headers=headers,
    )
    hidden = client.post(
        "/api/cms/v2/sites/web/menus/main/items",
        json={"label": "Privado", "href": "/web/privado", "visibility": "hidden"},
        headers=headers,
    )
    assert visible.status_code == 201
    assert hidden.status_code == 201

    public_menu = client.get("/api/cms/v2/public/sites/web/menus/main")
    assert public_menu.status_code == 200
    labels = [item["label"] for item in public_menu.json()["items"]]
    assert labels == ["Inicio"]

    inactive_menu = client.patch(
        "/api/cms/v2/sites/web/menus/main",
        json={"is_active": False},
        headers=headers,
    )
    assert inactive_menu.status_code == 200
    assert client.get("/api/cms/v2/public/sites/web/menus/main").status_code == 404


def test_cms_section_delete_archives_and_can_restore(client, db_session):
    seed_admin(db_session)
    headers = auth_headers(client)

    site = client.post(
        "/api/cms/v2/sites",
        json={"site_key": "sections", "name": "Sections", "base_path": "/sections", "is_active": True},
        headers=headers,
    )
    assert site.status_code == 201
    page = client.post(
        "/api/cms/v2/sites/sections/pages",
        json={"slug": "inicio", "title": "Inicio"},
        headers=headers,
    )
    assert page.status_code == 201
    section = client.post(
        "/api/cms/v2/sites/sections/pages/inicio/sections",
        json={"type": "hero", "props_json": {"title": "Recuperable"}, "sort_order": 0},
        headers=headers,
    )
    assert section.status_code == 201

    archived = client.delete(
        f"/api/cms/v2/sites/sections/pages/inicio/sections/{section.json()['id']}",
        headers=headers,
    )
    assert archived.status_code == 204

    section_list = client.get("/api/cms/v2/sites/sections/pages/inicio/sections", headers=headers)
    assert section_list.status_code == 200
    assert section_list.json()[0]["status"] == "archived"

    preview = client.get("/api/cms/v2/sites/sections/pages/inicio/preview", headers=headers)
    assert preview.status_code == 200
    assert preview.json()["sections"] == []

    restored = client.patch(
        f"/api/cms/v2/sites/sections/pages/inicio/sections/{section.json()['id']}",
        json={"status": "active"},
        headers=headers,
    )
    assert restored.status_code == 200
    assert restored.json()["status"] == "active"

    restored_preview = client.get("/api/cms/v2/sites/sections/pages/inicio/preview", headers=headers)
    assert restored_preview.status_code == 200
    assert restored_preview.json()["sections"][0]["props_json"]["title"] == "Recuperable"
