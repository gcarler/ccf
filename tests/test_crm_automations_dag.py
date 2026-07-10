import uuid
from datetime import timedelta

from backend.models import Persona
from backend.models_crm import CrmAutomation, CrmAutomationEdge, PendingCrmAction
from backend.models_shared import _utcnow
from backend.services.automation_engine import engine


def test_crm_automations_dag(db_session):
    # 1. Create a target persona UUID
    persona_id = uuid.uuid4()
    persona = Persona(
        id=persona_id,
        first_name="Test",
        last_name="Persona",
        email="test_persona@example.com",
    )
    db_session.add(persona)
    db_session.commit()

    # 2. Create automations
    root_auto = CrmAutomation(
        name="Root Automation", trigger_event="test_event", action_type="send_email", delay_minutes=0, is_active=True
    )
    left_auto = CrmAutomation(
        name="Left Branch", trigger_event="next_event", action_type="send_email", delay_minutes=10, is_active=True
    )
    right_auto = CrmAutomation(
        name="Right Branch", trigger_event="next_event", action_type="create_task", delay_minutes=20, is_active=True
    )
    db_session.add_all([root_auto, left_auto, right_auto])
    db_session.commit()

    # 3. Create edges for DAG branching: root -> left, root -> right
    edge_left = CrmAutomationEdge(source_id=root_auto.id, target_id=left_auto.id)
    edge_right = CrmAutomationEdge(source_id=root_auto.id, target_id=right_auto.id)
    db_session.add_all([edge_left, edge_right])
    db_session.commit()

    # 4. Create initial pending action for root
    pending_root = PendingCrmAction(
        automation_id=root_auto.id,
        target_persona_id=persona_id,
        execute_at=_utcnow() - timedelta(minutes=1),
        status="pending",
    )
    db_session.add(pending_root)
    db_session.commit()

    # 5. Process pending actions
    engine._process_crm_pending_actions(db_session)
    db_session.commit()

    # 6. Verify assertions
    # Root action should be executed
    db_session.refresh(pending_root)
    assert pending_root.status == "executed"

    # Subsequent actions for left and right branches should be queued
    next_actions = (
        db_session.query(PendingCrmAction)
        .filter(PendingCrmAction.target_persona_id == persona_id, PendingCrmAction.status == "pending")
        .all()
    )

    assert len(next_actions) == 2
    auto_ids = {action.automation_id for action in next_actions}
    assert auto_ids == {left_auto.id, right_auto.id}

    # Verify execution times
    left_action = [a for a in next_actions if a.automation_id == left_auto.id][0]
    right_action = [a for a in next_actions if a.automation_id == right_auto.id][0]

    left_execute_at = left_action.execute_at
    if left_execute_at.tzinfo is not None:
        left_execute_at = left_execute_at.replace(tzinfo=None)

    right_execute_at = right_action.execute_at
    if right_execute_at.tzinfo is not None:
        right_execute_at = right_execute_at.replace(tzinfo=None)

    now = _utcnow()
    if now.tzinfo is not None:
        now = now.replace(tzinfo=None)

    assert abs((left_execute_at - now).total_seconds() - 600) < 30
    assert abs((right_execute_at - now).total_seconds() - 1200) < 30
