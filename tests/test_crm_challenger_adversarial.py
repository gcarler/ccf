import uuid
import pytest
from backend import models
from backend.models_crm import CrmAutomation, CrmAutomationEdge, PendingCrmAction
from backend.models_crm_pipeline import CasoCRM, EtapaPipeline, PipelineCRM
from backend.services.automation_engine import engine
from backend.models_shared import _utcnow as models_shared_utcnow
from tests.conftest import seed_admin

def test_atomic_sort_reorder_empty_payload(db_session):
    admin_a, persona_a, sede_a = seed_admin(db_session, email="chal_admin_a@example.com")
    CasoCRM.atomic_sort_reorder(db_session, [], sede_a.id)  # Should not raise exception

def test_atomic_sort_reorder_duplicate_ids(db_session):
    admin_a, persona_a, sede_a = seed_admin(db_session, email="chal_admin_a@example.com")
    case_id = uuid.uuid4()
    payload = [
        {"id": str(case_id), "sort_order": 1},
        {"id": str(case_id), "sort_order": 2}
    ]
    with pytest.raises(ValueError) as excinfo:
        CasoCRM.atomic_sort_reorder(db_session, payload, sede_a.id)
    assert "Duplicate IDs in reorder payload." in str(excinfo.value)

def test_atomic_sort_reorder_non_existent_case(db_session):
    admin_a, persona_a, sede_a = seed_admin(db_session, email="chal_admin_a@example.com")
    case_id = uuid.uuid4()
    payload = [{"id": str(case_id), "sort_order": 1}]
    with pytest.raises(ValueError) as excinfo:
        CasoCRM.atomic_sort_reorder(db_session, payload, sede_a.id)
    assert "Case not found" in str(excinfo.value)

def test_atomic_sort_reorder_cross_sede_case(db_session):
    admin_a, persona_a, sede_a = seed_admin(db_session, email="chal_admin_a@example.com")
    admin_b, persona_b, sede_b = seed_admin(db_session, email="chal_admin_b@example.com")

    pipeline_b = PipelineCRM(sede_id=sede_b.id, nombre="Pipeline B", tipo="CONSEJERIA")
    db_session.add(pipeline_b)
    db_session.flush()

    stage_b = EtapaPipeline(pipeline_id=pipeline_b.id, nombre="Stage B", orden=1)
    db_session.add(stage_b)
    db_session.flush()

    case_b = CasoCRM(
        persona_id=persona_b.id,
        sede_id=sede_b.id,
        pipeline_id=pipeline_b.id,
        etapa_actual_id=stage_b.id,
        titulo_caso="Caso B",
        origen_canal="WEB_FORM",
    )
    db_session.add(case_b)
    db_session.flush()

    # Admin A tries to reorder Case B (belonging to Sede B)
    payload = [{"id": str(case_b.id), "sort_order": 1}]
    with pytest.raises(ValueError) as excinfo:
        CasoCRM.atomic_sort_reorder(db_session, payload, sede_a.id)
    assert "Sede isolation violation" in str(excinfo.value)
    assert "some cases do not belong to user's Sede" in str(excinfo.value)

def test_atomic_sort_reorder_cross_sede_target_stage(db_session):
    admin_a, persona_a, sede_a = seed_admin(db_session, email="chal_admin_a@example.com")
    admin_b, persona_b, sede_b = seed_admin(db_session, email="chal_admin_b@example.com")

    pipeline_a = PipelineCRM(sede_id=sede_a.id, nombre="Pipeline A", tipo="NUEVOS_VISITANTES")
    pipeline_b = PipelineCRM(sede_id=sede_b.id, nombre="Pipeline B", tipo="CONSEJERIA")
    db_session.add_all([pipeline_a, pipeline_b])
    db_session.flush()

    stage_a = EtapaPipeline(pipeline_id=pipeline_a.id, nombre="Stage A", orden=1)
    stage_b = EtapaPipeline(pipeline_id=pipeline_b.id, nombre="Stage B", orden=1)
    db_session.add_all([stage_a, stage_b])
    db_session.flush()

    case_a = CasoCRM(
        persona_id=persona_a.id,
        sede_id=sede_a.id,
        pipeline_id=pipeline_a.id,
        etapa_actual_id=stage_a.id,
        titulo_caso="Caso A",
        origen_canal="WEB_FORM",
    )
    db_session.add(case_a)
    db_session.flush()

    # Admin A tries to move Case A to Stage B (belonging to Sede B) using various stage keys
    for key in ("stage_id", "etapa_actual_id", "etapa_id", "target_stage_id", "drag_target_etapa_id"):
        payload = [{"id": str(case_a.id), key: str(stage_b.id)}]
        with pytest.raises(ValueError) as excinfo:
            CasoCRM.atomic_sort_reorder(db_session, payload, sede_a.id)
        assert "Sede isolation violation" in str(excinfo.value)
        assert "some target stages do not belong to user's Sede" in str(excinfo.value)

def test_automation_engine_operators_adversarial(db_session):
    persona_id = uuid.uuid4()
    persona = models.Persona(
        id=persona_id, first_name="Chal", last_name="Tester", email="chal_tester@example.com", estado_vital="ACTIVO"
    )
    db_session.add(persona)
    db_session.commit()

    admin, admin_p, sede = seed_admin(db_session, email="chal_auto_admin@example.com")
    pipeline = PipelineCRM(sede_id=sede.id, nombre="Chal Pipeline", tipo="NUEVOS_VISITANTES")
    db_session.add(pipeline)
    db_session.flush()

    stage = EtapaPipeline(pipeline_id=pipeline.id, nombre="Stage 1", orden=1)
    db_session.add(stage)
    db_session.flush()

    case = CasoCRM(
        persona_id=persona_id,
        sede_id=sede.id,
        pipeline_id=pipeline.id,
        etapa_actual_id=stage.id,
        titulo_caso="Adversarial Test Case",
        origen_canal="WEB_FORM",
        payload_web={
            "null_key": None,
            "text_key": "Hello World",
            "number_key": 100,
            "list_key": "apple,banana,cherry",
        },
    )
    db_session.add(case)
    db_session.commit()

    def check_condition(cond_type, cond_key, cond_val, should_match):
        root = CrmAutomation(
            name="Root", trigger_event="trigger", action_type="send_email", delay_minutes=0, is_active=True
        )
        target = CrmAutomation(
            name="Target", trigger_event="trigger", action_type="send_email", delay_minutes=10, is_active=True
        )
        db_session.add_all([root, target])
        db_session.flush()

        edge = CrmAutomationEdge(
            source_id=root.id,
            target_id=target.id,
            condition_type=cond_type,
            condition_key=cond_key,
            condition_value=cond_val,
        )
        db_session.add(edge)
        db_session.commit()

        action = PendingCrmAction(
            automation_id=root.id, target_persona_id=persona_id, execute_at=models_shared_utcnow(), status="pending"
        )
        db_session.add(action)
        db_session.commit()

        engine._process_crm_pending_actions(db_session)
        db_session.commit()

        queued = (
            db_session.query(PendingCrmAction)
            .filter(PendingCrmAction.automation_id == target.id, PendingCrmAction.target_persona_id == persona_id)
            .first()
        )

        is_matched = queued is not None

        # Cleanup
        db_session.delete(action)
        db_session.delete(edge)
        db_session.delete(root)
        db_session.delete(target)
        if queued:
            db_session.delete(queued)
        db_session.commit()

        assert is_matched == should_match, f"Expected {should_match}, got {is_matched}"
        return is_matched

    # 1. Test invalid/empty operator default behavior (defaults to equals)
    check_condition(None, "text_key", "Hello World", should_match=True)
    check_condition("", "text_key", "Hello World", should_match=True)
    # "   " is stripped to "" which does not match any operator and falls back to False
    check_condition("   ", "text_key", "Hello World", should_match=False)

    # 2. Test operator casing and whitespace trimming
    check_condition("  EQUALS  ", "text_key", "Hello World", should_match=True)
    check_condition("CONTAINS", "text_key", "Hello", should_match=True)
    check_condition("  starts_with  ", "text_key", "Hello", should_match=True)

    # 3. Test IN operator formatting & edge cases
    # comma separated list with spaces
    check_condition("in", "text_key", " hello world , other_value ", should_match=True)
    # JSON list
    check_condition("in", "text_key", '["hello world", "other"]', should_match=True)
    # Non-list JSON (e.g. string/int)
    check_condition("in", "text_key", '"hello world"', should_match=True)
    check_condition("in", "number_key", '100', should_match=True)
    # invalid JSON string with brackets fallback to splitting (brackets remain, so it shouldn't match)
    check_condition("in", "text_key", '[hello world, other]', should_match=False)


    # 4. Test numeric comparison fallback
    # non-numeric gt comparison should do string comparison
    check_condition("gt", "text_key", "G", should_match=True)
    check_condition("gt", "text_key", "Z", should_match=False)
    # non-numeric lt comparison
    check_condition("lt", "text_key", "Z", should_match=True)
    check_condition("lt", "text_key", "G", should_match=False)

    # 5. Test None values
    check_condition("equals", "null_key", "None", should_match=True)
    check_condition("equals", "null_key", "null", should_match=True)
    check_condition("equals", "null_key", "", should_match=True)
    check_condition("equals", "null_key", None, should_match=True)
    check_condition("equals", "null_key", "something", should_match=False)

    # 6. Test float comparison
    check_condition("gt", "number_key", "99.9", should_match=True)
    check_condition("lt", "number_key", "100.1", should_match=True)

