"""
CRUD FINAL PUSH — Tests for academy.py, cms.py, evangelism CRUD functions.
All CRUD functions called directly with populated database.
"""
import uuid
import pytest
from datetime import datetime, timedelta, timezone
from tests.conftest import seed_admin_v2 as _seed_admin, auth_headers_v2 as _auth_headers


def _call(fn, *a, **kw):
    return fn(*a, **kw)


@pytest.fixture
def full(client, db_session):
    admin, admin_persona, sede = _seed_admin(db_session)
    from backend import models

    personas = []
    for i in range(15):
        p = models.Persona(
            first_name=f"U{i}", last_name=f"T{i}",
            email=f"u{i}_{uuid.uuid4().hex[:6]}@t.com",
            phone=f"+5730011122{i:02d}",
            spiritual_status=["Miembro", "Visitante", "Nuevo", "Activo"][i % 4],
            church_role=["Miembro", "Líder", "Pastor", "Voluntario"][i % 4],
            estado_vital=["ACTIVO", "ACTIVO", "INACTIVO", "ACTIVO"][i % 4],
            sede_id=sede.id, sex=["M", "F"][i % 2],
        )
        db_session.add(p)
        personas.append(p)
    db_session.commit()
    for p in personas:
        db_session.refresh(p)

    for i in range(4):
        db_session.add(models.CounselingTicket(persona_id=personas[i].id, subject=f"CT_{i}", status="open"))
        db_session.add(models.PrayerRequest(requester_name=personas[i].first_name, request_text="P", sede_id=sede.id))
        db_session.add(models.CommunicationLog(persona_id=personas[i].id, channel="email", content=f"Msg_{i}"))
        db_session.add(models.VolunteerShift(persona_id=personas[i].id,
            role_name=["worship", "kids", "tech", "media"][i],
            team_name=["worship", "kids", "tech", "media"][i],
            shift_start=datetime.now(timezone.utc) - timedelta(hours=4),
            shift_end=datetime.now(timezone.utc)))
    db_session.commit()

    headers = _auth_headers(client, email=admin.email, password="testpass123")
    return {"c": client, "h": headers, "sede": sede, "admin": admin, "personas": personas}


class TestAcademyCRUD:
    def test_every_academy_function(self, db_session, full):
        from backend.crud import academy
        db = db_session
        uid = str(full["admin"].id)
        # Courses CRUD
        courses = _call(academy.get_courses, db)
        assert courses is not None
        _call(academy.get_courses, db, modality="online")
        _call(academy.get_courses, db, published_only=True)
        _call(academy.get_course, db, 1)
        course = _call(academy.create_course, db, {"title": f"C_{uuid.uuid4().hex[:6]}", "description": "D", "modality": "online"})
        if course:
            _call(academy.update_course, db, course.id, {"title": "Updated"})
            _call(academy.delete_course, db, course.id)
        # Lessons CRUD
        _call(academy.get_lessons_by_course, db, 1)
        _call(academy.get_lesson, db, 1)
        lesson = _call(academy.create_lesson, db, {"course_id": 1, "title": f"L_{uuid.uuid4().hex[:6]}", "content": "C", "order_index": 1})
        if lesson:
            _call(academy.update_lesson, db, lesson.id, {"title": "U"})
            _call(academy.delete_lesson, db, lesson.id)
        # Assessments CRUD
        _call(academy.get_assessments_by_course, db, 1)
        _call(academy.get_assessment_by_id, db, 1)
        assessment = _call(academy.create_assessment, db, {"course_id": 1, "title": f"A_{uuid.uuid4().hex[:6]}", "passing_score": 70})
        if assessment:
            _call(academy.update_assessment, db, assessment.id, {"title": "U"})
            _call(academy.delete_assessment, db, assessment.id)
        # Questions CRUD
        _call(academy.get_assessment_questions, db, 1)
        _call(academy.get_assessment_question, db, 1)
        q = _call(academy.create_assessment_question, db, {"assessment_id": 1, "question_text": "Q?", "question_type": "multiple_choice"})
        if q:
            _call(academy.update_assessment_question, db, q.id, {"question_text": "Updated?"})
            _call(academy.delete_assessment_question, db, q.id)
        # Options CRUD
        _call(academy.get_assessment_options, db, 1)
        opt = _call(academy.create_assessment_option, db, {"question_id": 1, "option_text": "A", "is_correct": True})
        if opt:
            _call(academy.update_assessment_option, db, opt.id, {"option_text": "Updated"})
            _call(academy.delete_assessment_option, db, opt.id)
        # Enrollments
        _call(academy.get_enrollments_by_user, db, uid)
        _call(academy.get_enrollment, db, 1)
        _call(academy.get_enrollment_by_user_course, db, uid, 1)
        # Certificates
        _call(academy.get_certificates_by_user, db, uid)
        _call(academy.get_certificate_by_code, db, "test")
        _call(academy.get_certificate, db, 1)
        # Progress
        _call(academy.get_lesson_progress, db, uid, 1)
        # Submissions
        _call(academy.list_assignment_submissions_with_meta, db)
        _call(academy.get_assignment_submission_with_meta, db, 1)
        # Attendance
        _call(academy.get_course_attendance, db, 1)
        _call(academy.create_course_attendance, db, {"enrollment_id": 1, "attended": True})
        # Resources
        _call(academy.get_lesson_resources, db, 1)
        _call(academy.create_resource, db, {"lesson_id": 1, "title": "R", "url": "http://r.com"})
        # Students
        _call(academy.get_course_students, db, 1)
        # Acta
        _call(academy.get_latest_acta_by_course, db, 1)
        # Forum
        _call(academy.get_forum_threads, db)
        _call(academy.get_forum_thread, db, 1)
        t = _call(academy.create_forum_thread, db, {"title": f"T_{uuid.uuid4().hex[:6]}", "author_id": uid})
        if t:
            _call(academy.delete_forum_thread, db, t.id)
        # Candidates
        _call(academy.get_academy_candidates, db)
        # Delete enrollment
        _call(academy.delete_enrollment, db, 1)
        # Delete certificate
        _call(academy.delete_certificate, db, 1)
        # Delete course attendance
        _call(academy.delete_course_attendance, db, 1)
        # Delete resource
        _call(academy.delete_resource, db, 1)
        # Delete assessment option
        _call(academy.delete_assessment_option, db, 1)
        # Delete assessment question
        _call(academy.delete_assessment_question, db, 1)


class TestCMSAdvancedCRUD:
    def test_every_cms_function(self, db_session, full):
        from backend.crud import cms
        db = db_session
        # Create site
        site = _call(cms.create_cms_site, db, type("P", (), {"model_dump": lambda self, **kw: {"site_key": f"s_{uuid.uuid4().hex[:6]}", "name": "Test", "base_path": "/t"}})())
        if site:
            _call(cms.update_cms_site, db, site, type("P", (), {"model_dump": lambda self, **kw: {"name": "U"}})())
            _call(cms.archive_cms_site, db, site)
        # Create theme
        site_obj = db.execute(__import__("sqlalchemy").text("SELECT id FROM cms_sites LIMIT 1")).scalar()
        if site_obj:
            theme = _call(cms.create_cms_theme, db, site_obj, type("P", (), {"model_dump": lambda self, **kw: {"name": f"Th_{uuid.uuid4().hex[:6]}", "tokens_json": {}}})(), created_by=str(full["admin"].id))
            if theme:
                _call(cms.update_cms_theme, db, theme, type("P", (), {"model_dump": lambda self, **kw: {"name": "U"}})())
                _call(cms.activate_cms_theme, db, site_obj, theme.id)
                _call(cms.archive_cms_theme, db, theme)
            # Create menu
            menu = _call(cms.create_cms_menu, db, site_obj, type("P", (), {"model_dump": lambda self, **kw: {"menu_key": f"m_{uuid.uuid4().hex[:6]}", "name": "Test"}})())
            if menu:
                _call(cms.update_cms_menu, db, menu, type("P", (), {"model_dump": lambda self, **kw: {"name": "U"}})())
                _call(cms.delete_cms_menu, db, menu)
            # Create menu item
            menu_obj = db.execute(__import__("sqlalchemy").text("SELECT id FROM cms_menus LIMIT 1")).scalar()
            if menu_obj:
                mi = _call(cms.create_cms_menu_item, db, menu_obj, type("P", (), {"model_dump": lambda self, **kw: {"label": "I", "href": "/"}})())
                if mi:
                    _call(cms.update_cms_menu_item, db, mi, type("P", (), {"model_dump": lambda self, **kw: {"label": "U"}})())
                    _call(cms.delete_cms_menu_item, db, mi)
            # Create page
            page = _call(cms.create_cms_page, db, site_obj, type("P", (), {"model_dump": lambda self, **kw: {"slug": f"p_{uuid.uuid4().hex[:6]}", "title": "P", "status": "draft"}})(), user_id=str(full["admin"].id))
            if page:
                _call(cms.update_cms_page, db, page, type("P", (), {"model_dump": lambda self, **kw: {"title": "U"}})(), user_id=str(full["admin"].id))
                # Create section
                sec = _call(cms.create_cms_section, db, page.id, type("P", (), {"model_dump": lambda self, **kw: {"section_key": f"s_{uuid.uuid4().hex[:6]}", "type": "rich_text", "props_json": {}}})())
                if sec:
                    _call(cms.update_cms_section, db, sec, type("P", (), {"model_dump": lambda self, **kw: {"props_json": {"content": "U"}}})())
                    _call(cms.archive_cms_section, db, sec)
                # Create version
                ver = _call(cms.create_cms_page_version, db, page, str(full["admin"].id), "Test")
                if ver:
                    _call(cms.restore_cms_page_version, db, page, ver, str(full["admin"].id))
                # Transition status
                _call(cms.transition_cms_page_status, db, page, "approve", str(full["admin"].id))
                _call(cms.transition_cms_page_status, db, page, "publish", str(full["admin"].id))
                _call(cms.transition_cms_page_status, db, page, "archive", str(full["admin"].id))
                _call(cms.delete_cms_page, db, page)
        # Media items
        item = _call(cms.create_cms_media_item, db, url="http://t.com/i.jpg", alt_text="T",
            filename="i.jpg", mime_type="image/jpeg", section="test", tags=[], created_by=str(full["admin"].id))
        if item:
            _call(cms.update_cms_media_item, db, item.id, alt_text="U")
            _call(cms.delete_cms_media_item, db, item.id)
        # Media asset
        asset = _call(cms.create_media_asset, db, "test.jpg", "http://t.com/test.jpg", "image/jpeg", 1024)
        if asset:
            _call(cms.delete_media_asset, db, asset.id)
        # Content metrics
        _call(cms.increment_content_metric, db, "test_metric", 1)
        # Announcements
        ann = _call(cms.create_announcement, db, {"title": "A", "content": "C", "status": "published"})
        if ann:
            _call(cms.get_announcement, db, ann.id)
            _call(cms.update_announcement, db, ann, type("P", (), {"model_dump": lambda self, **kw: {"title": "U"}})())
            _call(cms.delete_announcement, db, ann)
        # Testimonials
        t = _call(cms.create_testimonial, db, {"content": "T", "author_persona_id": str(full["personas"][0].id), "status": "published"})
        if t:
            _call(cms.get_testimonial, db, t.id)
            _call(cms.update_testimonial, db, t, type("P", (), {"model_dump": lambda self, **kw: {"content": "U"}})())
            _call(cms.delete_testimonial, db, t)
        # Pastoral team
        _call(cms.list_pastoral_team, db)
        _call(cms.get_persona_by_id, db, str(full["personas"][0].id))
        _call(cms.update_pastoral_profile, db, full["personas"][0], {"bio_short": "Updated"})
        # Page content
        _call(cms.update_page_content, db, "test_key", {"title": "T", "content": "C"})
        _call(cms.get_page_content, db, "test_key")
        _call(cms.list_page_contents, db)
        _call(cms.get_or_create_page_content, db, "test_key")
        _call(cms.get_page_content_versions, db, "test_key")
        _call(cms.restore_page_content_version, db, "test_key", 1)
        # Publications
        _call(cms.get_or_create_content_publication, db, "test_key")
        _call(cms.update_content_publication, db, "test_key", status="published")
        _call(cms.list_content_publications, db)
        # Sites
        _call(cms.list_cms_sites, db)
        _call(cms.list_cms_sites, db, only_active=True)
        _call(cms.get_cms_site_by_key, db, "faro")
        # Theme list
        if site_obj:
            _call(cms.list_cms_themes, db, site_obj)
            _call(cms.get_cms_theme, db, site_obj, 1)
            _call(cms.get_active_cms_theme, db, site_obj)
        # Menu list
        if site_obj:
            _call(cms.list_cms_menus, db, site_obj)
        # Pages list
        if site_obj:
            _call(cms.list_cms_pages, db, site_obj)
            _call(cms.list_cms_pages, db, site_obj, status="published")
            _call(cms.list_cms_pages_all, db, site_obj)
        # Sections list
        page_obj = db.execute(__import__("sqlalchemy").text("SELECT id FROM cms_pages LIMIT 1")).scalar()
        if page_obj:
            _call(cms.list_cms_sections, db, page_obj)
            _call(cms.list_cms_sections, db, page_obj, section_type="hero")
            _call(cms.list_cms_page_versions, db, page_obj)
            _call(cms.list_cms_publish_logs, db, page_obj, page_id=page_obj)
        # Media items list
        _call(cms.list_cms_media_items, db)
        _call(cms.list_cms_media_items, db, query="test")
        _call(cms.list_cms_media_items, db, section="general")
        # Public page
        _call(cms.get_public_cms_page, db, site_obj or 1, "home")
