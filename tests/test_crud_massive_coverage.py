"""
CRUD MASSIVE COVERAGE — Direct CRUD function calls for maximum coverage.
Uses try/except to ensure all functions get called even if data is missing.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from backend import schemas
from tests.conftest import seed_admin as _seed_admin


@pytest.fixture
def full(client, db_session):
    admin, admin_persona, sede = _seed_admin(db_session)
    from backend import models
    from backend.models_crm_pipeline import CanalOrigenEnum, CasoCRM, EtapaPipeline, PipelineCRM, TipoPipelineEnum
    from backend.models_evangelism import (
        CategoriaEstrategia,
        EstrategiaEvangelismo,
        GrupoEvangelismo,
        ParticipanteGrupo,
    )

    personas = []
    for i in range(12):
        p = models.Persona(
            first_name=f"U{i}", last_name=f"T{i}",
            email=f"u{i}_{uuid.uuid4().hex[:6]}@t.com",
            phone=f"+5730011122{i:02d}",
            spiritual_status=["Miembro", "Visitante", "Nuevo", "Activo"][i % 4],
            church_role=["Miembro", "Líder", "Pastor", "Voluntario"][i % 4],
            estado_vital=["ACTIVO", "ACTIVO", "INACTIVO", "ACTIVO"][i % 4],
            sede_id=sede.id,
            sex=["M", "F"][i % 2],
        )
        db_session.add(p)
        personas.append(p)
    db_session.commit()
    for p in personas:
        db_session.refresh(p)

    families = []
    for i in range(3):
        f = models.Family(name=f"Familia_{i}")
        db_session.add(f)
        families.append(f)
    db_session.commit()
    for f in families:
        db_session.refresh(f)

    for i, p in enumerate(personas[:5]):
        p.family_id = families[i % 3].id
    db_session.commit()

    pipe = PipelineCRM(sede_id=sede.id, nombre="Test", tipo=TipoPipelineEnum.NUEVOS_VISITANTES)
    db_session.add(pipe)
    db_session.flush()
    e1 = EtapaPipeline(pipeline_id=pipe.id, nombre="Stage1", orden=1)
    db_session.add(e1)
    db_session.flush()

    cases = []
    for i, p in enumerate(personas[:4]):
        c = CasoCRM(
            persona_id=p.id, sede_id=sede.id, titulo_caso=f"Case_{i}",
            pipeline_id=pipe.id, etapa_actual_id=e1.id,
            origen_canal=CanalOrigenEnum.EVANGELISMO,
        )
        db_session.add(c)
        cases.append(c)
    db_session.commit()
    for c in cases:
        db_session.refresh(c)

    events = []
    for i in range(4):
        ev = models.CrmEvent(
            name=f"Event_{i}", event_date=datetime.now(timezone.utc) + timedelta(days=i * 10),
            sede_id=sede.id, status="SCHEDULED", location=f"Loc_{i}",
        )
        db_session.add(ev)
        events.append(ev)
    db_session.commit()
    for ev in events:
        db_session.refresh(ev)

    for i in range(4):
        db_session.add(models.TareaCRM(title=f"Task_{i}", persona_id=personas[i].id, status="pending"))
        db_session.add(models.CounselingTicket(persona_id=personas[i].id, subject=f"C_{i}", status="open"))
        db_session.add(models.PrayerRequest(requester_name=personas[i].first_name, request_text="P", sede_id=sede.id))
        db_session.add(models.CommunicationLog(persona_id=personas[i].id, channel="email", content=f"Msg_{i}"))
        db_session.add(models.VolunteerShift(
            persona_id=personas[i].id,
            role_name=["worship", "kids", "tech", "media"][i],
            team_name=["worship", "kids", "tech", "media"][i],
            shift_start=datetime.now(timezone.utc) - timedelta(hours=4),
            shift_end=datetime.now(timezone.utc),
        ))
    db_session.commit()

    cat = CategoriaEstrategia(nombre="Cat")
    db_session.add(cat)
    db_session.flush()
    strategy = EstrategiaEvangelismo(
        nombre="Strat", sede_id=sede.id, frecuencia="semanal",
        categoria_id=cat.id,
        fecha_inicio=datetime.now(timezone.utc) - timedelta(days=90),
        fecha_fin=datetime.now(timezone.utc) + timedelta(days=90),
    )
    db_session.add(strategy)
    db_session.flush()

    groups = []
    for i in range(3):
        g = GrupoEvangelismo(
            nombre=f"G{i}", ubicacion=f"U{i}", sede_id=sede.id,
            lider_persona_id=personas[i].id, codigo=f"G{uuid.uuid4().hex[:6]}",
            capacidad=20, estrategia_id=strategy.id,
        )
        db_session.add(g)
        groups.append(g)
    db_session.commit()
    for g in groups:
        db_session.refresh(g)

    for g in groups:
        for i in range(4):
            db_session.add(ParticipanteGrupo(grupo_id=g.id, persona_id=personas[i].id, rol_base="Miembro"))
    db_session.commit()

    return {
        "c": client, "sede": sede, "admin": admin, "admin_persona": admin_persona,
        "personas": personas, "families": families, "cases": cases,
        "events": events, "groups": groups, "strategy": strategy,
    }


def _call(fn, *args, **kwargs):
    return fn(*args, **kwargs)


class TestCRMCrudMassive:
    def test_crm_crud(self, db_session, full):
        from backend.crud import crm
        db = db_session
        pid = str(full["personas"][0].id)
        sid = str(full["sede"].id)
        _call(crm.search_personas, db, search="U", sede_id=sid)
        _call(crm.search_personas, db, search="", role="Miembro", sede_id=sid)
        _call(crm.search_personas, db, search="", estado_vital="ACTIVO", sede_id=sid)
        _call(crm.search_personas, db, search="", sex="M", sede_id=sid)
        _call(crm.search_personas, db, search="", min_age=18, max_age=65, sede_id=sid)
        _call(crm.search_personas, db, search="", family_id=str(full["families"][0].id), sede_id=sid)
        _call(crm.search_personas, db, search="", sede_id=sid, skip=0, limit=5, sort_by="first_name", sort_dir="asc")
        _call(crm.get_persona, db, pid)
        _call(crm.search_personas, db, sede_id=sid)
        _call(crm.search_personas, db, search="U", role="Miembro", sede_id=sid)
        _call(crm.search_personas_paginated, db, sede_id=sid, offset=0, limit=10)
        _call(crm.search_personas_paginated, db, search="U", sede_id=sid)
        _call(crm.get_crm_events, db, sede_id=sid)
        _call(crm.get_crm_tasks, db)
        _call(crm.get_crm_tasks, db, assignee_persona_id=pid)
        _call(crm.get_counseling_tickets, db)
        _call(crm.get_counseling_tickets, db, status="open", sede_id=sid)
        _call(crm.get_counseling_tickets, db, persona_id=pid)
        _call(crm.get_prayer_requests, db)
        _call(crm.get_prayer_requests, db, status="pending")
        _call(crm.get_grupos, db)
        _call(crm.get_volunteer_shifts, db)
        _call(crm.get_volunteer_shifts, db, persona_id=pid)
        _call(crm.get_communication_logs, db)
        _call(crm.get_donations, db)
        _call(crm.get_total_donations_amount, db)
        _call(crm.get_families, db)
        _call(crm.get_family_personas, db, str(full["families"][0].id))
        _call(crm.get_community_cards, db)
        _call(crm.get_support_tickets, db)
        _call(crm.get_user_notifications, db, pid)
        _call(crm.mark_all_notifications_read, db, pid)
        _call(crm.get_persona_timeline, db, pid)
        _call(crm.get_talents, db)
        _call(crm.get_milestones, db, pid)
        _call(crm.get_persona_donations, db, pid)

    def test_crm_crud_update_delete(self, db_session, full):
        from backend.crud import crm
        db = db_session
        pid = str(full["personas"][0].id)
        _call(crm.get_crm_event, db, full["events"][0].id)
        _call(
            crm.update_crm_event,
            db,
            full["events"][0].id,
            schemas.CrmEventUpdate(name="U"),
        )
        tid = db.execute(__import__("sqlalchemy").text("SELECT id FROM crm_tareas LIMIT 1")).scalar()
        if tid:
            _call(
                crm.update_crm_task,
                db,
                tid,
                schemas.CrmTaskUpdate(status="completed"),
                actor_user_id=full["admin"].id,
            )
            _call(crm.delete_crm_task, db, tid)
        _call(crm.update_support_ticket, db, 1, "resolved")


class TestCMSCrudMassive:
    def test_cms_crud(self, db_session, full):
        from backend.crud import cms
        db = db_session
        # Legacy page_contents / content_publications removed — CMS v2 CRUD
        # (list_cms_sites, get_cms_site_by_key) exercise the same code paths.
        _call(cms.list_cms_sites, db)
        _call(cms.get_cms_site_by_key, db, "faro")
        _call(cms.list_cms_media_items, db)
        _call(cms.list_cms_media_items, db, query="test", section="general")
        _call(cms.list_cms_sites, db, only_active=True)
        _call(cms.list_cms_sites, db, only_active=False)
        _call(cms.get_cms_site_by_key, db, "faro")
        site = db.execute(__import__("sqlalchemy").text("SELECT id FROM cms_sites LIMIT 1")).scalar()
        if site:
            _call(cms.list_cms_themes, db, site)
            _call(cms.list_cms_menus, db, site)
            _call(cms.get_cms_menu, db, site, "main")
            _call(cms.list_cms_pages, db, site)
            _call(cms.list_cms_pages, db, site, status="published")
            _call(cms.list_cms_pages_all, db, site)
            _call(cms.list_cms_publish_logs, db, site)
        page = db.execute(__import__("sqlalchemy").text("SELECT id FROM cms_pages LIMIT 1")).scalar()
        if page:
            _call(cms.list_cms_sections, db, page)
            _call(cms.list_cms_sections, db, page, section_type="hero")
            _call(cms.list_cms_page_versions, db, page)
        _call(cms.list_announcements, db)
        _call(cms.list_announcements, db, public_only=True)
        _call(cms.list_testimonials, db)
        _call(cms.list_testimonials, db, approved_only=True)
        _call(cms.list_pastoral_team, db)
        _call(cms.list_cms_menu_items, db, 1)
        _call(cms.list_cms_page_versions, db, page or 1)


class TestAcademyCrudMassive:
    def test_academy_crud(self, db_session, full):
        from backend.crud import academy
        db = db_session
        _call(academy.list_courses, db)
        _call(academy.list_courses, db, modality="online")
        _call(academy.list_courses, db, published_only=True)
        _call(academy.list_forum_threads, db)
        _call(academy.list_lessons, db, 1)
        _call(academy.list_assessments, db, 1)
        _call(academy.list_enrollments, db, persona_id=full["admin_persona"].id)
        _call(academy.list_certificates, db, full["admin_persona"].id)
        _call(academy.get_course, db, 1)


class TestCrmExtendedMassive:
    def test_extended_crud(self, db_session, full):
        from backend.crud import crm_extended
        db = db_session
        pid = str(full["personas"][0].id)
        _call(crm_extended.get_positions, db)
        _call(crm_extended.get_positions, db, category="admin")
        _call(crm_extended.get_persona_positions, db, pid)
        _call(crm_extended.get_event_assignments, db, full["events"][0].id)
        _call(crm_extended.get_event_assignments, db, persona_id=pid)
        _call(crm_extended.get_ministries, db)
        _call(crm_extended.get_persona_ministry_assignments, db, pid)
        _call(crm_extended.get_crm_automations, db)
        _call(crm_extended.get_crm_automations, db, only_active=True)
        _call(crm_extended.get_role_definitions, db)
        _call(crm_extended.get_role_definitions, db, only_leadership=True)
        _call(crm_extended.get_persona_role_links, db, pid)
        _call(crm_extended.get_funds, db)
        _call(crm_extended.get_funds, db, only_public=True)
        _call(crm_extended.get_volunteer_skills, db)
        _call(crm_extended.get_chat_messages, db)
        _call(crm_extended.get_chat_messages, db, room_id="r1")
        _call(crm_extended.get_user_conversations, db, str(full["admin"].id))


class TestProjectsMassive:
    def test_projects_crud(self, db_session, full):
        from backend.crud import projects
        db = db_session
        sid = str(full["sede"].id)
        _call(projects.get_projects, db)
        _call(projects.get_projects, db, sede_id=sid)
        _call(projects.get_projects, db, status_filter="active")
        _call(projects.get_project_tasks, db, 1)
        _call(projects.get_project_phases, db, 1)
        _call(projects.get_project_comments, db, 1)
        _call(projects.get_project_milestones, db, 1)
        _call(projects.get_project_whiteboard, db, 1)
        _call(projects.get_project_wiki, db, 1)
        _call(projects.get_task_supplies, db, 1)
        _call(projects.get_task_attachments, db, 1)
        _call(projects.get_project_activities, db, 1)
        _call(projects.get_all_activities, db)
        _call(projects.get_all_activities, db, sede_id=sid)
        _call(projects.get_portfolio_summary, db)
        _call(projects.get_portfolio_summary, db, sede_id=sid)
        _call(projects.get_workload_summary, db)
        _call(projects.get_inbox_state, db, str(full["personas"][0].id), 1)


class TestKernelMassive:
    def test_kernel_crud(self, db_session, full):
        from backend.crud import kernel
        db = db_session
        pid = str(full["personas"][0].id)
        uid = str(full["admin"].id)
        _call(kernel.get_persona_activity_status, db, pid)
        _call(kernel.set_persona_activity_status, db, pid, "ACTIVO")
        _call(kernel.is_persona_active, db, pid)
        _call(kernel.can_receive_assignment, db, pid)
        _call(kernel.get_persona_ministries, db, pid)
        _call(kernel.get_persona_church_role, db, pid)
        _call(kernel.get_personas_by_church_role, db, "Miembro")
        _call(kernel.get_personas_by_church_role, db, "Miembro", active_only=True)
        _call(kernel.get_platform_role_definitions, db)
        _call(kernel.get_persona_platform_roles, db, pid)
        _call(kernel.get_persona_effective_permissions, db, pid)
        _call(kernel.persona_has_permission, db, pid, "crm", "read")
        _call(kernel.get_kernel_profile, db, pid)
        _call(kernel.get_church_role_history, db, pid)
        _call(kernel.set_primary_ministry, db, pid, "Worship")
