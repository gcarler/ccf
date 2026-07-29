"""
Comprehensive tests for CRM CRUD submodules to increase code coverage across all submodules.
Submodules targeted:
- backend/crud/crm_/health.py
- backend/crud/crm_/personas.py
- backend/crud/crm_/groups.py
- backend/crud/crm_/tasks.py
- backend/crud/crm_/timeline.py
- backend/crud/crm_/resources.py
- backend/crud/crm_/families.py
- backend/crud/crm_/milestones.py
- backend/crud/crm_/pipeline.py
- backend/crud/crm_/shared.py
- backend/crud/crm_/support.py
- backend/crud/crm_/volunteers.py
"""
import uuid
import pytest
from datetime import datetime, date, timezone
from backend import models, models_crm_pipeline, schemas
from backend.schemas.crm.base import CrmTaskCreate, CrmTaskUpdate, VolunteerShiftCreate
from backend.schemas.operational import SupportTicketCreate
from backend.crud import crm as crm_crud
from backend.crud.crm_ import (
    health as health_crud,
    personas as personas_crud,
    groups as groups_crud,
    tasks as tasks_crud,
    timeline as timeline_crud,
    resources as resources_crud,
    families as families_crud,
    milestones as milestones_crud,
    pipeline as pipeline_crud,
    shared as shared_crud,
    support as support_crud,
    volunteers as volunteers_crud,
)

# -------------------------------------------------------------------
# Fixtures
# -------------------------------------------------------------------
@pytest.fixture
def sample_sede(db_session):
    sede = models.Sede(
        id=uuid.uuid4(),
        nombre=f"Sede Test {uuid.uuid4().hex[:6]}",
        ciudad="Bogota",
        es_activa=True
    )
    db_session.add(sede)
    db_session.commit()
    db_session.refresh(sede)
    return sede

@pytest.fixture
def sample_persona(db_session, sample_sede):
    persona = models.Persona(
        id=uuid.uuid4(),
        first_name="Test",
        last_name="User",
        email=f"test_{uuid.uuid4().hex[:6]}@example.com",
        phone=f"+57300{uuid.uuid4().hex[:6][:7]}",
        id_number=f"DOC{uuid.uuid4().hex[:8]}",
        sede_id=sample_sede.id,
        estado_vital="ACTIVO",
        church_role="Miembro"
    )
    db_session.add(persona)
    db_session.commit()
    db_session.refresh(persona)
    return persona


# -------------------------------------------------------------------
# 1. Tests for health.py
# -------------------------------------------------------------------
def test_health_crud_functions(db_session, sample_persona):
    # Test _normalize_persona_id
    pid_uuid = sample_persona.id
    pid_str = str(pid_uuid)
    pid_hex = pid_uuid.hex
    assert health_crud._normalize_persona_id(pid_uuid) == pid_uuid
    assert health_crud._normalize_persona_id(pid_str) == pid_uuid
    assert health_crud._normalize_persona_id(pid_hex) == pid_uuid

    # Test cache functions
    health_crud._set_cached_health(pid_uuid, 85, "Excelente")
    cached = health_crud._get_cached_health(pid_uuid)
    assert cached == (85, "Excelente")

    health_crud._invalidate_health_cache(pid_uuid)
    assert health_crud._get_cached_health(pid_uuid) is None

    # Test recalculate_and_persist_pastoral_health & update_pastoral_health
    score, status = health_crud.recalculate_and_persist_pastoral_health(db_session, pid_uuid)
    assert isinstance(score, int)
    assert isinstance(status, str)

    updated_p = health_crud.update_pastoral_health(db_session, pid_uuid)
    assert updated_p is not None

    # Test listeners / helpers
    class DummyCourseAttendance:
        pass
    dummy = DummyCourseAttendance()
    assert health_crud._persona_id_from_course_attendance(dummy) is None

    # Test _suppress_health_invalidation context manager
    with health_crud._suppress_health_invalidation():
        health_crud._invalidate_health_cache(pid_uuid)


# -------------------------------------------------------------------
# 2. Tests for personas.py
# -------------------------------------------------------------------
def test_personas_crud_functions(db_session, sample_sede, sample_persona):
    # Test search & query
    q = personas_crud.persona_query(db_session)
    assert q is not None

    prepared = personas_crud.prepare_persona_for_output(db_session, sample_persona)
    assert prepared is not None

    # Test get_persona
    p = personas_crud.get_persona(db_session, str(sample_persona.id))
    assert p is not None and p.id == sample_persona.id

    # Test search_personas & search_personas_page & paginated
    res = personas_crud.search_personas(db_session, search="Test", sede_id=sample_sede.id)
    assert len(res) >= 1

    p_page_res = personas_crud.search_personas_page(db_session, search="Test", skip=0, limit=10, sede_id=sample_sede.id)
    assert p_page_res["total"] >= 1

    p_paginated = personas_crud.search_personas_paginated(db_session, search="Test", limit=10, offset=0, sede_id=sample_sede.id)
    assert len(p_paginated["items"]) >= 1

    p_list = personas_crud.get_personas(db_session, search="Test")
    assert len(p_list) >= 1

    # Test mentor operations
    candidates = personas_crud.list_mentor_candidates(db_session, str(sample_persona.id), sede_id=sample_sede.id)
    assert isinstance(candidates, list)

    mentor_persona = models.Persona(
        id=uuid.uuid4(),
        first_name="Mentor",
        last_name="User",
        email=f"mentor_{uuid.uuid4().hex[:6]}@example.com",
        sede_id=sample_sede.id
    )
    db_session.add(mentor_persona)
    db_session.commit()

    mentorship = personas_crud.assign_persona_mentor(db_session, sample_persona.id, mentor_persona.id, notes="Testing mentor")
    assert mentorship is not None

    # Test update_persona
    update_payload = schemas.PersonaUpdate(first_name="TestUpdated")
    updated = personas_crud.update_persona(db_session, str(sample_persona.id), update_payload)
    assert updated.first_name == "TestUpdated"

    # Test get_talents & donations
    talents = personas_crud.get_talents(db_session, search="Test")
    assert isinstance(talents, list)

    donations = personas_crud.get_persona_donations(db_session, str(sample_persona.id))
    assert isinstance(donations, list)

    # Test delete_persona
    deleted = personas_crud.delete_persona(db_session, str(sample_persona.id))
    assert deleted is True


# -------------------------------------------------------------------
# 3. Tests for groups.py
# -------------------------------------------------------------------
def test_groups_crud_functions(db_session, sample_sede, sample_persona):
    # Create group
    group_payload = schemas.GrupoEvangelismoCreate(
        name=f"Grupo {uuid.uuid4().hex[:6]}",
        address="Calle 123",
        leader_id=sample_persona.id
    )
    group = groups_crud.create_grupo(db_session, group_payload, sede_id=sample_sede.id)
    assert group is not None and group.nombre == group_payload.name

    # Get group
    fetched = groups_crud.get_grupo(db_session, group.id)
    assert fetched is not None and fetched.id == group.id

    # List groups
    groups_list = groups_crud.get_grupos(db_session, sede_id=sample_sede.id)
    assert len(groups_list) >= 1

    # Update group
    update_payload = schemas.GrupoEvangelismoUpdate(name="Grupo Updated")
    updated = groups_crud.update_grupo(db_session, group.id, update_payload)
    assert updated.nombre == "Grupo Updated"

    # Delete group
    deleted = groups_crud.delete_grupo(db_session, group.id)
    assert deleted is True


# -------------------------------------------------------------------
# 4. Tests for tasks.py
# -------------------------------------------------------------------
def test_tasks_crud_functions(db_session, sample_persona):
    # Create task
    task_payload = CrmTaskCreate(
        title="Test CRM Task",
        description="Testing task crud",
        persona_id=sample_persona.id,
        assignee_id=sample_persona.id,
        due_date=date.today()
    )
    task = tasks_crud.create_crm_task(
        db_session,
        payload=task_payload,
        actor_user_id=sample_persona.id
    )
    assert task is not None and task.title == "Test CRM Task"

    # List tasks
    tasks = tasks_crud.get_crm_tasks(db_session, persona_id=sample_persona.id)
    assert len(tasks) >= 1

    # Update task
    task_update = CrmTaskUpdate(title="Test CRM Task Updated", status="completed")
    updated = tasks_crud.update_crm_task(db_session, task.id, payload=task_update, actor_user_id=sample_persona.id)
    assert updated.title == "Test CRM Task Updated"

    # Helper tests
    assert tasks_crud._values_equivalent("a", "a") is True
    assert tasks_crud._values_equivalent("a", "b") is False
    assert tasks_crud._value_for_audit(date.today()) == date.today().isoformat()

    # Delete task
    deleted = tasks_crud.delete_crm_task(db_session, task.id)
    assert deleted is True


# -------------------------------------------------------------------
# 5. Tests for timeline.py
# -------------------------------------------------------------------
def test_timeline_crud_functions(db_session, sample_persona):
    timeline = timeline_crud.get_persona_timeline(db_session, str(sample_persona.id))
    assert isinstance(timeline, list)


# -------------------------------------------------------------------
# 6. Tests for resources.py
# -------------------------------------------------------------------
def test_resources_crud_functions(db_session, sample_sede):
    # Categories
    cat_payload = schemas.CategoriaRecursoCreate(nombre=f"Cat {uuid.uuid4().hex[:6]}", descripcion="Test cat")
    cat = resources_crud.create_categoria(db_session, cat_payload)
    assert cat is not None

    cat_fetched = resources_crud.get_categoria(db_session, str(cat.id))
    assert cat_fetched is not None

    cats = resources_crud.list_categorias(db_session)
    assert len(cats) >= 1

    cat_updated = resources_crud.update_categoria(db_session, str(cat.id), schemas.CategoriaRecursoUpdate(nombre="Cat Updated"))
    assert cat_updated.nombre == "Cat Updated"

    # Plantillas
    plantilla_payload = schemas.PlantillaMensajeCreate(
        titulo=f"Plantilla {uuid.uuid4().hex[:6]}",
        contenido_texto="Hola {{nombre}}",
        canal="WHATSAPP",
        categoria_id=cat.id
    )
    plantilla = resources_crud.create_plantilla(db_session, plantilla_payload, sede_id=sample_sede.id)
    assert plantilla is not None

    p_fetched = resources_crud.get_plantilla(db_session, str(plantilla.id))
    assert p_fetched is not None

    plantillas = resources_crud.list_plantillas(db_session, sede_id=sample_sede.id)
    assert len(plantillas) >= 1

    p_updated = resources_crud.update_plantilla(db_session, str(plantilla.id), schemas.PlantillaMensajeUpdate(titulo="Plantilla Updated"))
    assert p_updated.titulo == "Plantilla Updated"

    # Envios & Counts & Adjuntos
    envios_cnt = resources_crud.count_envios(db_session, str(plantilla.id))
    assert envios_cnt == 0

    adjunto = resources_crud.create_adjunto(
        db_session,
        sede_id=str(sample_sede.id),
        plantilla_id=str(plantilla.id),
        nombre_recurso="Doc",
        url_acceso="http://example.com/doc.pdf",
        nombre_archivo="doc.pdf",
        tipo_mime="application/pdf",
        peso_bytes=1024
    )
    assert adjunto is not None

    adjuntos = resources_crud.list_adjuntos(db_session, plantilla_id=str(plantilla.id))
    assert len(adjuntos) == 1

    resources_crud.delete_adjunto(db_session, str(adjunto.id))
    resources_crud.delete_plantilla(db_session, str(plantilla.id))
    resources_crud.delete_categoria(db_session, str(cat.id))


# -------------------------------------------------------------------
# 7. Tests for families.py, milestones.py, support.py, volunteers.py
# -------------------------------------------------------------------
def test_families_crud_functions(db_session, sample_persona):
    fam = families_crud.create_family(db_session, name=f"Familia {uuid.uuid4().hex[:6]}")
    assert fam is not None

    f_fetched = families_crud.get_family(db_session, str(fam.id))
    assert f_fetched is not None

    f_list = families_crud.get_families(db_session)
    assert len(f_list) >= 1

    f_updated = families_crud.update_family(db_session, str(fam.id), name="Familia Updated")
    assert f_updated.name == "Familia Updated"

    families_crud.delete_family(db_session, str(fam.id))


def test_milestones_crud_functions(db_session, sample_persona, sample_sede):
    ms = milestones_crud.create_milestone(
        db_session,
        persona_id=sample_persona.id,
        type="bautismo",
        event_date=date.today(),
        sede_id=sample_sede.id
    )
    assert ms is not None

    ms_list = milestones_crud.list_milestones(db_session, sede_id=sample_sede.id)
    assert len(ms_list) >= 1

    milestones_crud.delete_milestone(db_session, str(ms.id))


def test_support_crud_functions(db_session, sample_persona):
    st_payload = SupportTicketCreate(
        subject="Ayuda",
        description="Testing support",
        user_id=sample_persona.id
    )
    ticket = support_crud.create_support_ticket(db_session, ticket=st_payload)
    assert ticket is not None

    t_fetched = support_crud.get_support_ticket(db_session, str(ticket.id))
    assert t_fetched is not None

    tickets = support_crud.get_support_tickets(db_session, user_id=str(sample_persona.id))
    assert len(tickets) >= 1

    t_updated = support_crud.update_support_ticket(db_session, str(ticket.id), new_status="resolved")
    assert t_updated.status == "resolved"


def test_volunteers_crud_functions(db_session, sample_persona):
    shifts = volunteers_crud.get_volunteer_shifts(db_session)
    assert isinstance(shifts, list)

    shift_payload = VolunteerShiftCreate(
        persona_id=sample_persona.id,
        role_name="Acomodador",
        team_name="Bienvenida",
        shift_start=datetime.now(timezone.utc),
        shift_end=datetime.now(timezone.utc)
    )
    shift = volunteers_crud.create_volunteer_shift(db_session, payload=shift_payload)
    assert shift is not None

    s_fetched = volunteers_crud.get_volunteer_shift(db_session, str(shift.id))
    assert s_fetched is not None

    volunteers_crud.delete_volunteer_shift(db_session, str(shift.id))

# -------------------------------------------------------------------
# 8. Extra Edge Case Tests for 100% Coverage (health, groups, tasks, personas)
# -------------------------------------------------------------------
def test_health_listeners_edge_cases(db_session, sample_persona, sample_sede):
    pipe = models.PipelineCRM(id=uuid.uuid4(), sede_id=sample_sede.id, nombre="Pipeline Test", tipo=models_crm_pipeline.TipoPipelineEnum.RETENCION)
    stage = models.EtapaPipeline(id=uuid.uuid4(), pipeline_id=pipe.id, nombre="Etapa 1", orden=1)
    db_session.add_all([pipe, stage])
    db_session.commit()

    case = models.CasoCRM(
        id=uuid.uuid4(),
        persona_id=sample_persona.id,
        sede_id=sample_sede.id,
        pipeline_id=pipe.id,
        etapa_actual_id=stage.id,
        titulo_caso="Test Case",
        origen_canal=models_crm_pipeline.CanalOrigenEnum.WEB_FORM,
        estado=models_crm_pipeline.EstadoCasoEnum.ABIERTO
    )
    db_session.add(case)
    db_session.commit()

    inter = models.InteraccionCRM(
        id=uuid.uuid4(),
        caso_id=case.id,
        realizado_por_id=sample_persona.id,
        tipo=models_crm_pipeline.TipoInteraccionEnum.WHATSAPP,
        resumen="Test note"
    )
    db_session.add(inter)
    db_session.commit()

    assert health_crud._persona_id_from_interaccion(inter) == sample_persona.id

    # Invoke listeners directly
    health_crud._after_insert_direct(None, None, inter)
    health_crud._after_update_direct(None, None, inter)
    health_crud._after_delete_direct(None, None, inter)
    health_crud._after_course_attendance_change(None, None, None)

def test_tasks_emit_mesh_event(db_session, sample_persona):
    # Test _emit_mesh_event exception handling when redis is dummy/none
    tasks_crud._emit_mesh_event("test_event", str(uuid.uuid4()), str(sample_persona.id), {"extra": 123})

def test_groups_edge_cases(db_session, sample_sede, sample_persona):
    # Test group custom role resolution and subordinate tokens logic
    group_payload = schemas.GrupoEvangelismoCreate(
        name=f"Grupo Custom {uuid.uuid4().hex[:6]}",
        address="Calle 456",
        leader_id=sample_persona.id
    )
    group = groups_crud.create_grupo(db_session, group_payload, sede_id=sample_sede.id)

    # Test update_grupo with custom roles & subordinate tokens
    update_payload = schemas.GrupoEvangelismoUpdate(
        name="Grupo Custom Updated",
        base_attendees_with_roles=[
            {"persona_id": str(sample_persona.id), "role": "co-lider"}
        ]
    )
    updated = groups_crud.update_grupo(db_session, group.id, update_payload)
    assert updated is not None

def test_personas_additional_queries(db_session, sample_persona):
    # Test edge case helpers in personas
    days = personas_crud._compute_days_in_state(db_session, sample_persona.id, "activo")
    assert days is None or isinstance(days, int)

    token = personas_crud._normalize_token(" Test  ")
    assert token.strip().lower() == "test"

    rate_map = personas_crud._attendance_rate_map(db_session, [sample_persona.id])
    assert isinstance(rate_map, dict)

    vol_map = personas_crud._volunteer_commitment_map(db_session, [sample_persona.id])
    assert isinstance(vol_map, dict)
