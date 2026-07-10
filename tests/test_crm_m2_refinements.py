import uuid

import pytest

from backend import models
from backend.models_crm import CrmAutomation, CrmAutomationEdge, PendingCrmAction
from backend.models_crm_pipeline import CasoCRM, EtapaPipeline, PipelineCRM
from backend.services.automation_engine import engine
from tests.conftest import seed_admin


def test_atomic_sort_reorder_target_stage_sede_isolation(db_session):
    # Setup two sedes
    admin_a, persona_a, sede_a = seed_admin(db_session, email="ref_admin_a@example.com")
    admin_b, persona_b, sede_b = seed_admin(db_session, email="ref_admin_b@example.com")

    # Create pipelines for each sede
    pipeline_a = PipelineCRM(sede_id=sede_a.id, nombre="Pipeline Sede A", tipo="NUEVOS_VISITANTES")
    pipeline_b = PipelineCRM(sede_id=sede_b.id, nombre="Pipeline Sede B", tipo="CONSEJERIA")
    db_session.add_all([pipeline_a, pipeline_b])
    db_session.flush()

    # Create stages
    stage_a = EtapaPipeline(pipeline_id=pipeline_a.id, nombre="Stage A", orden=1)
    stage_b = EtapaPipeline(pipeline_id=pipeline_b.id, nombre="Stage B", orden=1)
    db_session.add_all([stage_a, stage_b])
    db_session.flush()

    # Create case belonging to Sede A
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

    # Try to reorder case_a into stage_b (which is Sede B) from user_sede_id=sede_a.id
    # This should trigger ValueError due to target stage Sede isolation violation.
    payload = [{"id": str(case_a.id), "target_stage_id": str(stage_b.id)}]

    with pytest.raises(ValueError) as excinfo:
        CasoCRM.atomic_sort_reorder(db_session, payload, sede_a.id)

    assert "Sede isolation violation" in str(excinfo.value)
    assert "some target stages do not belong to user's Sede" in str(excinfo.value)


def test_automation_engine_operators(db_session):
    persona_id = uuid.uuid4()

    # Setup test person
    persona = models.Persona(
        id=persona_id, first_name="Testy", last_name="Automation", email="testy_auto@example.com", estado_vital="ACTIVO"
    )
    db_session.add(persona)
    db_session.commit()

    # Setup case with payload_web containing various fields for test operators
    # Let's mock a case belonging to a default Sede and Pipeline
    admin, admin_p, sede = seed_admin(db_session, email="auto_admin@example.com")
    pipeline = PipelineCRM(sede_id=sede.id, nombre="Auto Pipeline", tipo="NUEVOS_VISITANTES")
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
        titulo_caso="Test Case for Automation",
        origen_canal="WEB_FORM",
        payload_web={"my_key": "my_foo_value", "my_number": 42, "another_key": "some_value"},
    )
    db_session.add(case)
    db_session.commit()

    # Define a helper function to test a condition
    def check_condition(cond_type, cond_key, cond_val, should_match):
        # Create root and target automations
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

        # Add pending action
        action = PendingCrmAction(
            automation_id=root.id, target_persona_id=persona_id, execute_at=models_shared_utcnow(), status="pending"
        )
        db_session.add(action)
        db_session.commit()

        # Run engine processing
        engine._process_crm_pending_actions(db_session)
        db_session.commit()

        # Verify if target action was queued
        queued = (
            db_session.query(PendingCrmAction)
            .filter(PendingCrmAction.automation_id == target.id, PendingCrmAction.target_persona_id == persona_id)
            .first()
        )

        is_matched = queued is not None
        assert is_matched == should_match, (
            f"Condition type '{cond_type}' with key '{cond_key}' and val '{cond_val}' expected match: {should_match}, got: {is_matched}"
        )

        # Cleanup for next check
        db_session.delete(action)
        db_session.delete(edge)
        db_session.delete(root)
        db_session.delete(target)
        if queued:
            db_session.delete(queued)
        db_session.commit()

    # Import the utcnow helper from backend.models_shared
    from backend.models_shared import _utcnow as models_shared_utcnow

    # 1. Test "equals"
    check_condition("equals", "my_key", "my_foo_value", should_match=True)
    check_condition("equals", "my_key", "different_value", should_match=False)
    # Test case-insensitivity of equals operator
    check_condition("EQUALS", "my_key", "my_foo_value", should_match=True)

    # 2. Test "contains"
    check_condition("contains", "my_key", "foo", should_match=True)
    check_condition("contains", "my_key", "bar", should_match=False)

    # 3. Test "starts_with"
    check_condition("starts_with", "my_key", "my_f", should_match=True)
    check_condition("starts_with", "my_key", "foo", should_match=False)

    # 4. Test "always"
    # regardless of key/value
    check_condition("always", None, None, should_match=True)
    check_condition("always", "non_existing_key", "any_value", should_match=True)

    # 5. Test "IN"
    check_condition("IN", "my_key", "my_foo_value,other_val", should_match=True)
    check_condition("in", "my_key", "other_val_1,other_val_2", should_match=False)
    # Test JSON array style for IN
    check_condition("IN", "my_key", '["my_foo_value", "other_val"]', should_match=True)

    # 6. Test "gt"
    check_condition("gt", "my_number", "40", should_match=True)
    check_condition("gt", "my_number", "45", should_match=False)

    # 7. Test "lt"
    check_condition("lt", "my_number", "50", should_match=True)
    check_condition("lt", "my_number", "30", should_match=False)

    # 8. Test "ne"
    check_condition("ne", "my_key", "not_my_foo_value", should_match=True)
    check_condition("ne", "my_key", "my_foo_value", should_match=False)
