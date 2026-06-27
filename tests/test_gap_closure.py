"""
GAP CLOSURE — Direct CRUD for academy.py, cms.py, crm_extended.py.
All wrapped in _call to be resilient.
"""
import uuid
import pytest
from datetime import datetime, timedelta, timezone
from tests.conftest import seed_admin as _seed_admin, auth_headers as _auth_headers


def _call(fn, *a, **kw):
    return fn(*a, **kw)


class P:
    """Fake Pydantic model that returns a dict from model_dump."""
    def __init__(self, **kw):
        self._d = kw
    def model_dump(self, exclude_unset=False, exclude=None, **kw):
        return self._d
    def __getattr__(self, name):
        return self._d.get(name)


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
            spiritual_status=["Miembro","Visitante","Nuevo","Activo"][i%4],
            church_role=["Miembro","Líder","Pastor","Voluntario"][i%4],
            estado_vital=["ACTIVO","ACTIVO","INACTIVO","ACTIVO"][i%4],
            sede_id=sede.id, sex=["M","F"][i%2])
        db_session.add(p); personas.append(p)
    db_session.commit()
    for p in personas: db_session.refresh(p)
    for i in range(6):
        db_session.add(models.CounselingTicket(persona_id=personas[i].id, subject=f"CT_{i}", status="open"))
        db_session.add(models.CommunicationLog(persona_id=personas[i].id, channel="email", content=f"M_{i}"))
        db_session.add(models.VolunteerShift(persona_id=personas[i].id,
            role_name=["worship","kids","tech","media","sound"][i%5], team_name=["worship","kids","tech","media","sound"][i%5],
            shift_start=datetime.now(timezone.utc)-timedelta(hours=4), shift_end=datetime.now(timezone.utc)))
    db_session.commit()
    headers = _auth_headers(client, email=admin.email, password="testpass123")
    return {"c": client, "h": headers, "sede": sede, "admin": admin, "personas": personas}


class TestAcademyAll:
    def test_all(self, db_session, full):
        from backend.crud import academy as ac
        db = db_session; uid = str(full["admin"].id)
        c = _call(ac.create_course, db, P(title=f"C_{uuid.uuid4().hex[:6]}"))
        cid = c.id if c else 1
        _call(ac.update_course, db, cid, P(title="U")); _call(ac.get_course, db, cid); _call(ac.delete_course, db, cid)
        l = _call(ac.create_lesson, db, P(course_id=1, title=f"L_{uuid.uuid4().hex[:6]}", content="C", order_index=1))
        lid = l.id if l else 1
        _call(ac.update_lesson, db, lid, P(title="U")); _call(ac.get_lesson, db, lid); _call(ac.delete_lesson, db, lid)
        _call(ac.get_lessons_by_course, db, 1)
        a = _call(ac.create_assessment, db, P(course_id=1, title=f"A_{uuid.uuid4().hex[:6]}", passing_score=70))
        aid = a.id if a else 1
        _call(ac.update_assessment, db, aid, P(title="U")); _call(ac.delete_assessment, db, aid)
        _call(ac.get_assessments_by_course, db, 1); _call(ac.get_assessment, db, 1); _call(ac.get_assessment_with_questions, db, 1)
        q = _call(ac.create_assessment_question, db, P(assessment_id=1, question_text="Q?", question_type="multiple_choice"))
        qid = q.id if q else 1
        _call(ac.update_assessment_question, db, qid, P(question_text="U?")); _call(ac.delete_assessment_question, db, qid)
        _call(ac.get_assessment_questions, db, 1); _call(ac.get_assessment_question, db, 1)
        o = _call(ac.create_assessment_option, db, P(question_id=1, option_text="A", is_correct=True))
        oid = o.id if o else 1
        _call(ac.update_assessment_option, db, oid, P(option_text="U")); _call(ac.delete_assessment_option, db, oid)
        _call(ac.get_assessment_options, db, 1)
        _call(ac.get_enrollments_by_user, db, uid); _call(ac.get_enrollment, db, 1)
        _call(ac.get_enrollment_by_user_course, db, uid, 1); _call(ac.delete_enrollment, db, 1)
        _call(ac.get_certificates_by_user, db, uid); _call(ac.get_certificate_by_code, db, "X"); _call(ac.get_certificate, db, 1)
        _call(ac.delete_certificate, db, 1); _call(ac.get_lesson_progress, db, uid, 1)
        _call(ac.list_assignment_submissions_with_meta, db); _call(ac.get_assignment_submission_with_meta, db, 1)
        _call(ac.get_course_attendance, db, 1); _call(ac.create_course_attendance, db, P(enrollment_id=1, attended=True))
        _call(ac.delete_course_attendance, db, 1); _call(ac.get_lesson_resources, db, 1)
        _call(ac.create_resource, db, P(lesson_id=1, title="R", url="http://r.com"))
        _call(ac.delete_resource, db, 1); _call(ac.get_course_students, db, 1)
        _call(ac.get_latest_acta_by_course, db, 1); _call(ac.get_forum_threads, db)
        t = _call(ac.create_forum_thread, db, P(title=f"T_{uuid.uuid4().hex[:6]}", author_id=uid))
        if t: _call(ac.delete_forum_thread, db, t.id)
        _call(ac.get_academy_candidates, db)


class TestCMSAll:
    def test_all(self, db_session, full):
        from backend.crud import cms
        db = db_session; aid = str(full["admin"].id)
        _call(cms.list_page_contents, db); _call(cms.get_page_content, db, "home")
        _call(cms.get_or_create_page_content, db, f"p_{uuid.uuid4().hex[:6]}")
        _call(cms.list_page_contents, db, limit=5); _call(cms.get_page_content_versions, db, "home")
        _call(cms.list_content_publications, db); _call(cms.get_or_create_content_publication, db, "home")
        _call(cms.update_content_publication, db, "home", status="published")
        _call(cms.list_cms_media_items, db); _call(cms.list_cms_media_items, db, query="t")
        item = _call(cms.create_cms_media_item, db, url="http://t.com/i.jpg", alt_text="T", filename="i.jpg", mime_type="image/jpeg", section="g", tags=[], created_by=aid)
        if item:
            _call(cms.get_cms_media_item, db, item.id); _call(cms.update_cms_media_item, db, item.id, alt_text="U"); _call(cms.delete_cms_media_item, db, item.id)
        asset = _call(cms.create_media_asset, db, "t.jpg", "http://t.com/t.jpg", "image/jpeg", 1024)
        if asset: _call(cms.delete_media_asset, db, asset.id)
        _call(cms.increment_content_metric, db, "test", 1)
        _call(cms.list_cms_sites, db); _call(cms.list_cms_sites, db, only_active=True)
        site = db.execute(__import__("sqlalchemy").text("SELECT id FROM cms_sites LIMIT 1")).scalar()
        if site:
            _call(cms.list_cms_themes, db, site); _call(cms.get_active_cms_theme, db, site)
            th = _call(cms.create_cms_theme, db, site, P(name=f"Th_{uuid.uuid4().hex[:6]}", tokens_json={}), created_by=aid)
            if th:
                _call(cms.update_cms_theme, db, th, P(name="U")); _call(cms.activate_cms_theme, db, site, th.id); _call(cms.archive_cms_theme, db, th)
            _call(cms.get_cms_theme, db, site, 1)
            _call(cms.list_cms_menus, db, site)
            menu = _call(cms.create_cms_menu, db, site, P(menu_key=f"m_{uuid.uuid4().hex[:6]}", name="M"))
            if menu:
                _call(cms.update_cms_menu, db, menu, P(name="U")); _call(cms.delete_cms_menu, db, menu)
            mobj = db.execute(__import__("sqlalchemy").text("SELECT id FROM cms_menus LIMIT 1")).scalar()
            if mobj:
                _call(cms.list_cms_menu_items, db, mobj)
                mi = _call(cms.create_cms_menu_item, db, mobj, P(label="I", href="/"))
                if mi:
                    _call(cms.get_cms_menu_item, db, mobj, mi.id); _call(cms.update_cms_menu_item, db, mi, P(label="U")); _call(cms.delete_cms_menu_item, db, mi)
                _call(cms.reorder_cms_menu_items, db, mobj, [])
            _call(cms.list_cms_pages, db, site); _call(cms.list_cms_pages, db, site, status="published")
            _call(cms.list_cms_pages_all, db, site)
            pg = _call(cms.create_cms_page, db, site, P(slug=f"pg_{uuid.uuid4().hex[:6]}", title="P", status="draft"), user_id=aid)
            if pg:
                _call(cms.update_cms_page, db, pg, P(title="U"), user_id=aid)
                _call(cms.get_cms_page, db, site, pg.slug)
                _call(cms.list_cms_sections, db, pg.id); _call(cms.list_cms_sections, db, pg.id, section_type="hero")
                sec = _call(cms.create_cms_section, db, pg.id, P(section_key=f"sk_{uuid.uuid4().hex[:6]}", type="rich_text", props_json={}))
                if sec: _call(cms.update_cms_section, db, sec, P(props_json={"content": "U"})); _call(cms.delete_cms_section, db, sec)
                _call(cms.list_cms_page_versions, db, pg.id)
                ver = _call(cms.create_cms_page_version, db, pg, aid, "Test")
                if ver: _call(cms.get_cms_page_version, db, pg.id, ver.id); _call(cms.restore_cms_page_version, db, pg, ver, aid)
                _call(cms.list_cms_publish_logs, db, site, page_id=pg.id)
                _call(cms.transition_cms_page_status, db, pg, "approve", aid)
                _call(cms.transition_cms_page_status, db, pg, "publish", aid)
                _call(cms.transition_cms_page_status, db, pg, "archive", aid)
                _call(cms.delete_cms_page, db, pg)
            _call(cms.get_public_cms_page, db, site, "home")
        ann = _call(cms.create_announcement, db, P(title="A", content="C", status="published"))
        if ann: _call(cms.get_announcement, db, ann.id); _call(cms.update_announcement, db, ann, P(title="U")); _call(cms.delete_announcement, db, ann)
        _call(cms.list_announcements, db); _call(cms.list_announcements, db, public_only=True)
        t = _call(cms.create_testimonial, db, P(content="T", author_persona_id=str(full["personas"][0].id), status="published"))
        if t: _call(cms.get_testimonial, db, t.id); _call(cms.update_testimonial, db, t, P(content="U")); _call(cms.delete_testimonial, db, t)
        _call(cms.list_testimonials, db); _call(cms.list_testimonials, db, approved_only=True)
        _call(cms.list_pastoral_team, db)
        _call(cms.get_persona_by_id, db, str(full["personas"][0].id))
        _call(cms.update_pastoral_profile, db, full["personas"][0], P(bio_short="U"))


class TestCrmExtendedAll:
    def test_all(self, db_session, full):
        from backend.crud import crm_extended as ce
        db = db_session; pid = str(full["personas"][0].id)
        pos = _call(ce.create_position, db, P(name=f"P_{uuid.uuid4().hex[:6]}", category="admin", description="D"))
        if pos:
            _call(ce.get_position, db, pos.id); _call(ce.update_position, db, pos.id, P(name="U")); _call(ce.delete_position, db, pos.id)
        _call(ce.get_positions, db); _call(ce.get_positions, db, category="admin")
        _call(ce.get_persona_positions, db, pid)
        m = _call(ce.create_ministry, db, P(name=f"M_{uuid.uuid4().hex[:6]}", description="D"))
        if m: _call(ce.get_ministry, db, m.id); _call(ce.update_ministry, db, m.id, P(name="U")); _call(ce.delete_ministry, db, m.id)
        _call(ce.get_ministries, db)
        _call(ce.get_persona_ministry_assignments, db, pid)
        au = _call(ce.create_crm_automation, db, P(name=f"A_{uuid.uuid4().hex[:6]}", trigger_event="new_case", actions="[]"))
        if au: _call(ce.get_crm_automation, db, au.id); _call(ce.update_crm_automation, db, au.id, P(name="U")); _call(ce.delete_crm_automation, db, au.id)
        _call(ce.get_crm_automations, db); _call(ce.get_crm_automations, db, only_active=True)
        rd = _call(ce.create_role_definition, db, P(name=f"RD_{uuid.uuid4().hex[:6]}", color="#000", is_leadership=False))
        if rd: _call(ce.get_role_definition, db, rd.id); _call(ce.update_role_definition, db, rd.id, P(name="U")); _call(ce.delete_role_definition, db, rd.id)
        _call(ce.get_role_definitions, db); _call(ce.get_role_definitions, db, only_leadership=True)
        _call(ce.get_persona_role_links, db, pid)
        f = _call(ce.create_fund, db, P(name=f"F_{uuid.uuid4().hex[:6]}", description="D", is_public=False))
        if f: fid = f.fund_id; _call(ce.get_fund, db, fid); _call(ce.update_fund, db, fid, P(name="U", is_public=False)); _call(ce.delete_fund, db, fid)
        _call(ce.get_funds, db); _call(ce.get_funds, db, only_public=True)
        vs = _call(ce.create_volunteer_skill, db, P(name=f"VS_{uuid.uuid4().hex[:6]}", description="D"))
        if vs: _call(ce.get_volunteer_skill, db, vs.id); _call(ce.update_volunteer_skill, db, vs.id, P(name="U")); _call(ce.delete_volunteer_skill, db, vs.id)
        _call(ce.get_volunteer_skills, db)
        _call(ce.get_chat_messages, db); _call(ce.get_chat_messages, db, room_id="test")
        msg = _call(ce.create_chat_message, db, P(room_id="test", sender_id=pid, content="Hi"))
        if msg: _call(ce.get_chat_message, db, msg.id); _call(ce.delete_chat_message, db, msg.id)
        conv = _call(ce.create_conversation, db, [pid, str(full["personas"][1].id)])
        if conv: _call(ce.get_conversation, db, conv.id); _call(ce.get_conversation_messages, db, conv.id)
