"""
CRUD Module Coverage Tests — Imports and basic function calls.

Goal: Cover module-level code by importing and calling functions with minimal data.
"""
import uuid

import pytest

from tests.conftest import auth_headers, seed_admin


@pytest.fixture(scope="function")
def authed_client(client, db_session):
    user, persona, sede = seed_admin(db_session)
    headers = auth_headers(client)
    return client, headers, sede, persona, db_session


# ═══════════════════════════════════════════════════════════════════════════════
# 1. CRM CRUD — Direct DB Operations
# ═══════════════════════════════════════════════════════════════════════════════

class TestCrmCrudDirect:
    def test_create_and_get_persona(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.models_crm import Persona
        p = Persona(id=uuid.uuid4(), first_name="CRUD", last_name="Test", email="crud@test.com")
        db.add(p)
        db.flush()
        result = db.query(Persona).filter(Persona.id == p.id).first()
        assert result is not None
        assert result.first_name == "CRUD"

    def test_update_persona(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.models_crm import Persona
        p = Persona(id=uuid.uuid4(), first_name="Old", last_name="Name", email="upd@test.com")
        db.add(p)
        db.flush()
        p.first_name = "New"
        db.flush()
        assert p.first_name == "New"

    def test_delete_persona(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.models_crm import Persona
        p = Persona(id=uuid.uuid4(), first_name="Del", last_name="Test", email="del@test.com")
        db.add(p)
        db.flush()
        db.delete(p)
        db.flush()
        result = db.query(Persona).filter(Persona.id == p.id).first()
        assert result is None

    def test_list_personas(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.models_crm import Persona
        result = db.query(Persona).limit(10).all()
        assert isinstance(result, list)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. CMS CRUD — Direct DB Operations
# ═══════════════════════════════════════════════════════════════════════════════

class TestCmsCrudDirect:
    def test_create_and_get_site(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.models_cms import CmsSite
        site = CmsSite(id=uuid.uuid4(), site_key="crud-test", name="CRUD Test", base_path="/", is_active=True)
        db.add(site)
        db.flush()
        result = db.query(CmsSite).filter(CmsSite.id == site.id).first()
        assert result is not None

    def test_create_page(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.models_cms import CmsPage, CmsSite
        site = CmsSite(id=uuid.uuid4(), site_key="page-test", name="Page Test", base_path="/", is_active=True)
        db.add(site)
        db.flush()
        page = CmsPage(id=uuid.uuid4(), site_id=site.id, slug="test-page", title="Test Page", status="draft")
        db.add(page)
        db.flush()
        assert page.id is not None

    def test_create_section(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.models_cms import CmsPage, CmsSection, CmsSite
        site = CmsSite(id=uuid.uuid4(), site_key="section-test", name="Section Test", base_path="/", is_active=True)
        db.add(site)
        db.flush()
        page = CmsPage(id=uuid.uuid4(), site_id=site.id, slug="section-page", title="Section Page", status="draft")
        db.add(page)
        db.flush()
        section = CmsSection(id=uuid.uuid4(), page_id=page.id, section_key="hero-1", type="hero", props_json={"title": "Test"}, sort_order=0, is_visible=True)
        db.add(section)
        db.flush()
        assert section.id is not None

    def test_create_theme(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.models_cms import CmsSite, CmsTheme
        site = CmsSite(id=uuid.uuid4(), site_key="theme-test", name="Theme Test", base_path="/", is_active=True)
        db.add(site)
        db.flush()
        theme = CmsTheme(id=uuid.uuid4(), site_id=site.id, name="Test Theme", tokens_json={"--primary": "#000"}, is_active=True)
        db.add(theme)
        db.flush()
        assert theme.id is not None

    def test_create_menu(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.models_cms import CmsMenu, CmsSite
        site = CmsSite(id=uuid.uuid4(), site_key="menu-test", name="Menu Test", base_path="/", is_active=True)
        db.add(site)
        db.flush()
        menu = CmsMenu(id=uuid.uuid4(), site_id=site.id, menu_key="test-menu", name="Test Menu", is_active=True)
        db.add(menu)
        db.flush()
        assert menu.id is not None

    def test_create_menu_item(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.models_cms import CmsMenu, CmsMenuItem, CmsSite
        site = CmsSite(id=uuid.uuid4(), site_key="menu-item-test", name="Menu Item Test", base_path="/", is_active=True)
        db.add(site)
        db.flush()
        menu = CmsMenu(id=uuid.uuid4(), site_id=site.id, menu_key="item-test", name="Item Test", is_active=True)
        db.add(menu)
        db.flush()
        item = CmsMenuItem(id=uuid.uuid4(), menu_id=menu.id, label="Home", href="/", sort_order=0)
        db.add(item)
        db.flush()
        assert item.id is not None


# ═══════════════════════════════════════════════════════════════════════════════
# 3. PROJECTS CRUD — Direct DB Operations
# ═══════════════════════════════════════════════════════════════════════════════

class TestProjectsCrudDirect:
    def test_create_project(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.models_projects import Project
        project = Project(id=uuid.uuid4(), title="Test Project", sede_id=sede.id, owner_id=persona.id)
        db.add(project)
        db.flush()
        assert project.id is not None

    def test_list_projects(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.models_projects import Project
        result = db.query(Project).limit(10).all()
        assert isinstance(result, list)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. ACADEMY CRUD — Direct DB Operations
# ═══════════════════════════════════════════════════════════════════════════════

class TestAcademyCrudDirect:
    def test_create_course(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.models_academy_core import Course
        course = Course(code="TEST01", title="Test Course", description="A test course", modality="online")
        db.add(course)
        db.flush()
        assert course.id is not None

    def test_list_courses(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.models_academy_core import Course
        result = db.query(Course).limit(10).all()
        assert isinstance(result, list)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. AUTH CRUD — Direct DB Operations
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuthCrudDirect:
    def test_get_user(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.models_auth import Usuario
        user = db.query(Usuario).filter(Usuario.email == "admin@example.com").first()
        assert user is not None

    def test_list_users(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.models_auth import Usuario
        users = db.query(Usuario).all()
        assert isinstance(users, list)

    def test_get_role(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.models_auth import RolPlataforma
        role = db.query(RolPlataforma).first()
        assert role is not None


# ═══════════════════════════════════════════════════════════════════════════════
# 6. EVANGELISM CRUD — Direct DB Operations
# ═══════════════════════════════════════════════════════════════════════════════

class TestEvangelismCrudDirect:
    def test_create_grupo(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.models_evangelism import GrupoEvangelismo
        grupo = GrupoEvangelismo(id=uuid.uuid4(), nombre="Test Grupo", sede_id=sede.id, lider_persona_id=persona.id)
        db.add(grupo)
        db.flush()
        assert grupo.id is not None

    def test_list_grupos(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.models_evangelism import GrupoEvangelismo
        result = db.query(GrupoEvangelismo).limit(10).all()
        assert isinstance(result, list)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. ENTERPRISE CMS CRUD — Direct DB Operations
# ═══════════════════════════════════════════════════════════════════════════════

class TestEnterpriseCrudDirect:
    def test_create_audit_log(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.models_enterprise import AuditLog
        log = AuditLog(id=uuid.uuid4(), actor_persona_id=persona.id, action="test.create", entity_type="test", entity_id="123")
        db.add(log)
        db.flush()
        assert log.id is not None

    def test_create_notification(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.models_enterprise import CmsNotification
        notif = CmsNotification(id=uuid.uuid4(), recipient_persona_id=persona.id, notification_type="test", title="Test Notif")
        db.add(notif)
        db.flush()
        assert notif.id is not None

    def test_create_webhook(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.models_enterprise import Webhook
        hook = Webhook(id=uuid.uuid4(), site_key="faro", name="Test Hook", url="https://example.com/hook")
        db.add(hook)
        db.flush()
        assert hook.id is not None

    def test_create_custom_type(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.models_enterprise import CmsCustomType
        ct = CmsCustomType(id=uuid.uuid4(), site_key="faro", type_key="policy", label="Policy")
        db.add(ct)
        db.flush()
        assert ct.id is not None

    def test_create_custom_entry(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.models_enterprise import CmsCustomEntry
        entry = CmsCustomEntry(id=uuid.uuid4(), site_key="faro", type_key="wiki", slug="test-article", title="Test Article")
        db.add(entry)
        db.flush()
        assert entry.id is not None

    def test_create_glossary_term(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.models_enterprise import CmsGlossaryTerm
        term = CmsGlossaryTerm(id=uuid.uuid4(), site_key="faro", term="CRM", definition="Customer Relationship Management")
        db.add(term)
        db.flush()
        assert term.id is not None

    def test_create_search_index(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.models_enterprise import SearchIndex
        idx = SearchIndex(id=uuid.uuid4(), site_key="faro", entity_type="cms_page", entity_id="test", title="Test Page")
        db.add(idx)
        db.flush()
        assert idx.id is not None

    def test_create_user_session(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from datetime import datetime, timedelta

        from backend.models_enterprise import UserSession
        session = UserSession(id=uuid.uuid4(), persona_id=persona.id, session_token="test-token", expires_at=datetime.utcnow() + timedelta(hours=1))
        db.add(session)
        db.flush()
        assert session.id is not None

    def test_create_media_folder(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.models_enterprise import MediaFolder
        folder = MediaFolder(id=uuid.uuid4(), site_key="faro", name="Test Folder", slug="test-folder", path="/test-folder/")
        db.add(folder)
        db.flush()
        assert folder.id is not None

    def test_create_redirect(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.models_enterprise import CmsRedirect
        redir = CmsRedirect(id=uuid.uuid4(), site_key="faro", from_path="/old", to_path="/new", status_code=301)
        db.add(redir)
        db.flush()
        assert redir.id is not None
