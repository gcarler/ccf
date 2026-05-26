from backend import crud, schemas


def test_agent_task_crud(db_session):
    create = schemas.AgentTaskCreate(
        title="Investigar", description="Revisar métricas", source="agent"
    )
    task = crud.create_agent_task(db_session, create)
    assert task.status == "pending"

    updated = crud.update_agent_task(
        db_session, task.id, schemas.AgentTaskUpdate(status="in_progress")
    )
    assert updated.status == "in_progress"

    tasks = crud.list_agent_tasks(db_session, status="in_progress")
    assert len(tasks) == 1


def test_agent_insight(db_session):
    insight = crud.create_agent_insight(
        db_session,
        schemas.AgentInsightCreate(title="Alert", insight_type="anomaly", payload={}),
    )
    assert insight.acknowledged is False

    ack = crud.acknowledge_insight(db_session, insight.id)
    assert ack.acknowledged is True

    insights = crud.list_agent_insights(db_session, acknowledged=True)
    assert len(insights) == 1
