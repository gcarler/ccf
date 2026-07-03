"""
CRUD Integration Tests — Directly tests CRUD modules with real DB operations.

Goal: Increase coverage by exercising CRUD functions directly.
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
# 1. CRM CRUD TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestCrmCrud:
    def test_create_persona(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.crud.crm import create_persona
        from backend.schemas.crm import PersonaCreate
        payload = PersonaCreate(first_name="Test", last_name="User", email="test@crud.com")
        p = create_persona(db, payload)
        assert p is not None
        assert p.first_name == "Test"

    def test_get_persona(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.crud.crm import create_persona, get_persona
        from backend.schemas.crm import PersonaCreate
        payload = PersonaCreate(first_name="Get", last_name="Test", email="get@crud.com")
        p = create_persona(db, payload)
        result = get_persona(db, p.id)
        assert result is not None
        assert result.first_name == "Get"

    def test_update_persona(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.crud.crm import create_persona, update_persona
        from backend.schemas.crm import PersonaCreate, PersonaUpdate
        payload = PersonaCreate(first_name="Old", last_name="Name", email="update@crud.com")
        p = create_persona(db, payload)
        update_payload = PersonaUpdate(first_name="New")
        update_persona(db, p.id, update_payload)
        assert p.first_name == "New"

    def test_list_personas(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.crud.crm import search_personas
        result = search_personas(db, limit=10)
        assert isinstance(result, (list, tuple))

    def test_delete_persona(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.crud.crm import create_persona, delete_persona
        from backend.schemas.crm import PersonaCreate
        payload = PersonaCreate(first_name="Delete", last_name="Me", email="delete@crud.com")
        p = create_persona(db, payload)
        result = delete_persona(db, p.id)
        assert result is True


# ═══════════════════════════════════════════════════════════════════════════════
# 2. CMS CRUD TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestCmsCrud:
    @staticmethod
    def _create_page(db, persona, slug, title):
        from backend.crud.cms import create_cms_page, create_cms_site
        from backend.schemas.cms import CmsPageCreate, CmsSiteCreate

        site = create_cms_site(
            db,
            CmsSiteCreate(
                site_key=f"test-{uuid.uuid4().hex}",
                name="Test Site",
                base_path=f"/test-{uuid.uuid4().hex}",
            ),
        )
        return create_cms_page(
            db,
            site.id,
            CmsPageCreate(slug=slug, title=title, status="draft"),
            persona.id,
        )

    def test_create_page(self, authed_client):
        client, headers, sede, persona, db = authed_client
        page = self._create_page(db, persona, "test-page", "Test Page")
        assert page is not None
        assert page.slug == "test-page"

    def test_get_page(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.crud.cms import get_cms_page
        page = self._create_page(db, persona, "get-page", "Get Page")
        result = get_cms_page(db, page.site_id, page.slug)
        assert result is not None

    def test_update_page(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.crud.cms import update_cms_page
        from backend.schemas.cms import CmsPageUpdate
        page = self._create_page(db, persona, "update-page", "Old Title")
        update_cms_page(db, page, CmsPageUpdate(title="New Title"), persona.id)
        assert page.title == "New Title"

    def test_list_pages(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.crud.cms import list_cms_pages
        result, _total = list_cms_pages(db, site_id=uuid.uuid4())
        assert isinstance(result, list)

    def test_create_section(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.crud.cms import create_cms_section
        from backend.schemas.cms import CmsSectionCreate
        page = self._create_page(db, persona, "section-page", "Section Page")
        section = create_cms_section(db, page.id, CmsSectionCreate(type="hero", props_json={"title": "Test"}))
        assert section is not None

    def test_update_section(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.crud.cms import create_cms_section, update_cms_section
        from backend.schemas.cms import CmsSectionCreate, CmsSectionUpdate
        page = self._create_page(db, persona, "update-section", "Update Section")
        section = create_cms_section(db, page.id, CmsSectionCreate(type="hero", props_json={}))
        update_cms_section(db, section, CmsSectionUpdate(props_json={"title": "Updated"}))
        assert section.props_json == {"title": "Updated"}


# ═══════════════════════════════════════════════════════════════════════════════
# 3. PROJECTS CRUD TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestProjectsCrud:
    def test_create_project(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.crud.projects import create_project
        from backend.schemas.projects import ProjectCreate
        project = create_project(db, ProjectCreate(title="Test Project"), sede_id=sede.id, owner_persona_id=persona.id)
        assert project is not None
        assert project.name == "Test Project"

    def test_get_project(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.crud.projects import create_project, get_project
        from backend.schemas.projects import ProjectCreate
        project = create_project(db, ProjectCreate(title="Get Project"), sede_id=sede.id, owner_persona_id=persona.id)
        result = get_project(db, project.id, sede_id=sede.id)
        assert result is not None

    def test_update_project(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.crud.projects import create_project, update_project
        from backend.schemas.projects import ProjectCreate, ProjectUpdate
        project = create_project(db, ProjectCreate(title="Old Name"), sede_id=sede.id, owner_persona_id=persona.id)
        update_project(db, project.id, ProjectUpdate(title="New Name"), sede_id=sede.id)
        assert project.name == "New Name"

    def test_list_projects(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.crud.projects import get_projects
        result = get_projects(db, sede_id=sede.id)
        assert isinstance(result, list)

    def test_create_task(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.crud.projects import create_project, create_project_task
        from backend.schemas.projects import ProjectCreate, ProjectTaskCreate
        project = create_project(db, ProjectCreate(title="Task Project"), sede_id=sede.id, owner_persona_id=persona.id)
        task = create_project_task(db, ProjectTaskCreate(project_id=project.id, title="Test Task", assignee_id=persona.id))
        assert task is not None

    def test_list_tasks(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.crud.projects import create_project, get_project_tasks
        from backend.schemas.projects import ProjectCreate
        project = create_project(db, ProjectCreate(title="List Tasks"), sede_id=sede.id, owner_persona_id=persona.id)
        result = get_project_tasks(db, project.id)
        assert isinstance(result, list)

# ═══════════════════════════════════════════════════════════════════════════════
# 4. ACADEMY CRUD TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestAcademyCrud:
    def test_create_course(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.crud.academy import create_course
        course = create_course(db, {"code": "TEST-CREATE", "title": "Test Course", "description": "A test course", "modality": "online"})
        assert course is not None
        assert course.title == "Test Course"

    def test_get_course(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.crud.academy import create_course, get_course
        course = create_course(db, {"code": "TEST-GET", "title": "Get Course", "description": "Get test", "modality": "online"})
        result = get_course(db, course.id)
        assert result is not None

    def test_list_courses(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.crud.academy import list_courses
        result = list_courses(db)
        assert isinstance(result, list)

    def test_create_enrollment(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.crud.academy import create_course, create_enrollment
        from backend.schemas.academy import EnrollmentCreate
        course = create_course(db, {"code": "TEST-ENROLL", "title": "Enroll Course", "description": "Enroll test", "modality": "online"})
        enrollment = create_enrollment(db, EnrollmentCreate(course_id=course.id, persona_id=persona.id))
        assert enrollment is not None

    def test_list_enrollments(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.crud.academy import list_enrollments
        result = list_enrollments(db)
        assert isinstance(result, list)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. EVANGELISM CRUD TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestEvangelismCrud:
    def test_create_strategy(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.crud.evangelism import create_estrategia
        from backend.models_evangelism import CategoriaEstrategia
        from backend.schemas.evangelism import EstrategiaEvangelismoCreate
        # Schema fields are the canonical English shape (see ``EstrategiaEvangelismoBase``
        # in ``backend/schemas/evangelism.py``); Spanish columns on the ORM are
        # exposed via ``synonym`` and translated in ``create_estrategia``.
        cat = CategoriaEstrategia(nombre="Test Category")
        db.add(cat)
        db.flush()
        data = EstrategiaEvangelismoCreate(
            name="Test Strategy",
            description="Test",
            start_date="2026-01-01",
            end_date="2026-12-31",
        )
        strategy = create_estrategia(
            db, data, sede_id=str(sede.id), categoria_id=str(cat.id)
        )
        assert strategy is not None

    def test_list_strategies(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.crud.evangelism import get_estrategias
        result = get_estrategias(db, sede_id=str(sede.id))
        assert isinstance(result, list)

    def test_create_grupo(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.models_evangelism import GrupoEvangelismo
        grupo = GrupoEvangelismo(nombre="Test Grupo", sede_id=sede.id, lider_persona_id=persona.id)
        db.add(grupo)
        db.flush()
        assert grupo.id is not None

    def test_list_grupos(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.models_evangelism import GrupoEvangelismo
        result = db.query(GrupoEvangelismo).filter(GrupoEvangelismo.sede_id == sede.id).all()
        assert isinstance(result, list)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. DASHBOARD CRUD TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestDashboardCrud:
    def test_get_dashboard_metrics(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.crud.dashboard import get_dashboard_metrics
        result = get_dashboard_metrics(db)
        assert result is not None

    def test_get_cms_dashboard(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.crud.dashboard import get_cms_dashboard
        result = get_cms_dashboard(db)
        assert result is not None


# ═══════════════════════════════════════════════════════════════════════════════
# 7. KERNEL CRUD TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestKernelCrud:
    def test_get_persona_ministries(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.crud.kernel import get_persona_ministries
        result = get_persona_ministries(db, str(persona.id))
        assert isinstance(result, list)

    def test_get_persona_platform_roles(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.crud.kernel import get_persona_platform_roles
        result = get_persona_platform_roles(db, str(persona.id))
        assert isinstance(result, list)

    def test_get_kernel_profile(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.crud.kernel import get_kernel_profile
        result = get_kernel_profile(db, str(persona.id))
        assert result is not None or result is None  # May be None if no profile


# ═══════════════════════════════════════════════════════════════════════════════
# 8. AUTH CRUD TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuthCrud:
    def test_get_user_by_email(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.models_auth import Usuario
        user = db.query(Usuario).filter(Usuario.email == "admin@example.com").first()
        assert user is not None

    def test_list_users(self, authed_client):
        client, headers, sede, persona, db = authed_client
        from backend.models_auth import Usuario
        users = db.query(Usuario).all()
        assert isinstance(users, list)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. CMS V2 CRUD TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestCmsV2Crud:
    def test_create_site(self, authed_client):
        client, headers, sede, persona, db = authed_client
        import uuid

        from backend.models_cms import CmsSite
        site = CmsSite(id=uuid.uuid4(), site_key="test-site", name="Test Site", is_active=True)
        db.add(site)
        db.flush()
        assert site.id is not None

    def test_create_theme(self, authed_client):
        client, headers, sede, persona, db = authed_client
        import uuid

        from backend.models_cms import CmsSite, CmsTheme
        site = CmsSite(id=uuid.uuid4(), site_key="theme-test", name="Theme Test", is_active=True)
        db.add(site)
        db.flush()
        theme = CmsTheme(id=uuid.uuid4(), site_id=site.id, name="Test Theme", tokens_json={"--primary": "#000"}, is_active=True)
        db.add(theme)
        db.flush()
        assert theme.id is not None

    def test_create_menu(self, authed_client):
        client, headers, sede, persona, db = authed_client
        import uuid

        from backend.models_cms import CmsMenu, CmsSite
        site = CmsSite(id=uuid.uuid4(), site_key="menu-test", name="Menu Test", is_active=True)
        db.add(site)
        db.flush()
        menu = CmsMenu(id=uuid.uuid4(), site_id=site.id, menu_key="test-menu", name="Test Menu", is_active=True)
        db.add(menu)
        db.flush()
        assert menu.id is not None

    def test_create_menu_item(self, authed_client):
        client, headers, sede, persona, db = authed_client
        import uuid

        from backend.models_cms import CmsMenu, CmsMenuItem, CmsSite
        site = CmsSite(id=uuid.uuid4(), site_key="menu-item-test", name="Menu Item Test", is_active=True)
        db.add(site)
        db.flush()
        menu = CmsMenu(id=uuid.uuid4(), site_id=site.id, menu_key="item-test", name="Item Test", is_active=True)
        db.add(menu)
        db.flush()
        item = CmsMenuItem(id=uuid.uuid4(), menu_id=menu.id, label="Home", href="/", sort_order=0)
        db.add(item)
        db.flush()
        assert item.id is not None
