import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

from backend import models
from backend.services.task_notifications import (
    _display_name,
    _format_due_date,
    notify_task_assigned,
)


class DummyPersona:
    def __init__(self, id_val, nombre_completo=None, full_name=None, email=None):
        self.id = id_val
        self.nombre_completo = nombre_completo
        self.full_name = full_name
        self.email = email


class DummyTask:
    def __init__(
        self, id_val, assignee_id, project_id=1, title="Test Task", priority="High", due_date=None, description="Desc"
    ):
        self.id = id_val
        self.assignee_id = assignee_id
        self.project_id = project_id
        self.title = title
        self.priority = priority
        self.due_date = due_date
        self.description = description


class DummyProject:
    def __init__(self, id_val, title="Test Project"):
        self.id = id_val
        self.title = title


def test_display_name_helper():
    # 1. persona is None
    assert _display_name(None) == "Usuario"

    # 2. persona with nombre_completo
    p1 = DummyPersona(1, nombre_completo="Juan Perez")
    assert _display_name(p1) == "Juan Perez"

    # 3. persona without nombre_completo, with full_name
    p2 = DummyPersona(2, full_name="John Doe")
    assert _display_name(p2) == "John Doe"

    # 4. persona without both names
    p3 = DummyPersona(3)
    assert _display_name(p3) == "Usuario"


def test_format_due_date_helper():
    # 1. None
    assert _format_due_date(None) is None

    # 2. datetime instance
    dt = datetime(2026, 7, 29, 14, 30)
    assert _format_due_date(dt) == "29/07/2026 14:30"

    # 3. string or other type
    assert _format_due_date("2026-07-29") == "2026-07-29"


def test_notify_task_assigned_no_assignee():
    db = MagicMock()
    # Task without assignee_id
    task_no_assignee = DummyTask(id_val=100, assignee_id=None)
    assert notify_task_assigned(db, task=task_no_assignee) is False

    # Task with assignee_id but not found in DB
    task_with_assignee = DummyTask(id_val=101, assignee_id=uuid.uuid4())
    db.query.return_value.filter.return_value.first.return_value = None
    assert notify_task_assigned(db, task=task_with_assignee) is False


def test_notify_task_assigned_no_email():
    db = MagicMock()
    assignee_id = uuid.uuid4()
    task = DummyTask(id_val=102, assignee_id=assignee_id)
    assignee = DummyPersona(id_val=assignee_id, email=None)
    project = DummyProject(id_val=1, title="Project X")

    # Mock queries:
    # 1. Persona query for assignee -> assignee
    # 2. User scalar query -> user_id
    def query_side_effect(model):
        m_query = MagicMock()
        if model is models.Persona:
            m_query.filter.return_value.first.return_value = assignee
        elif model is models.User.id or str(model) == str(models.User.id):
            m_query.filter.return_value.scalar.return_value = assignee_id
        elif model is models.Project:
            m_query.filter.return_value.first.return_value = None
        return m_query

    db.query.side_effect = query_side_effect

    res = notify_task_assigned(
        db,
        task=task,
        project=project,
        assigned_by_user_id=uuid.uuid4(),
        previous_assignee_id=None,
    )

    assert res is True
    db.commit.assert_called_once()
    assert db.add.call_count == 2  # ActivityLog + CommunicationLog


@patch("backend.services.task_notifications.render_task_assignment_email")
@patch("backend.services.task_notifications.email_svc.send_email")
def test_notify_task_assigned_email_sent_new_notif(mock_send_email, mock_render_email):
    db = MagicMock()
    assignee_id = uuid.uuid4()
    user_id = uuid.uuid4()
    task = DummyTask(id_val=103, assignee_id=assignee_id)
    assignee = DummyPersona(id_val=assignee_id, email="assignee@example.com", nombre_completo="Assignee Name")
    project = DummyProject(id_val=1, title="Project Y")

    mock_render_email.return_value = ("Subject", "<p>HTML</p>", "Text")
    mock_send_email.return_value = True

    def query_side_effect(model):
        m_query = MagicMock()
        if model is models.Persona:
            m_query.filter.return_value.first.return_value = assignee
        elif model is models.User.id or str(model) == str(models.User.id):
            m_query.filter.return_value.scalar.return_value = user_id
        elif model is models.NotificacionUsuario:
            # First time: existing notification not found
            m_query.filter.return_value.first.return_value = None
        elif model is models.Project:
            m_query.filter.return_value.first.return_value = None
        return m_query

    db.query.side_effect = query_side_effect

    res = notify_task_assigned(
        db,
        task=task,
        project=project,
        assigned_by_user_id=None,
        previous_assignee_id=uuid.uuid4(),  # Reassigned
    )

    assert res is True
    db.commit.assert_called_once()
    # Staged: ProjectActivityLog, CommunicationLog, NotificacionUsuario
    assert db.add.call_count == 3


@patch("backend.services.task_notifications.render_task_assignment_email")
@patch("backend.services.task_notifications.email_svc.send_email")
def test_notify_task_assigned_email_sent_existing_notif(mock_send_email, mock_render_email):
    db = MagicMock()
    assignee_id = uuid.uuid4()
    user_id = uuid.uuid4()
    task = DummyTask(id_val=104, assignee_id=assignee_id)
    assignee = DummyPersona(id_val=assignee_id, email="assignee@example.com")
    existing_notif = MagicMock()

    mock_render_email.return_value = ("Subject", "<p>HTML</p>", "Text")
    mock_send_email.return_value = True

    def query_side_effect(model):
        m_query = MagicMock()
        if model is models.Persona:
            m_query.filter.return_value.first.return_value = assignee
        elif model is models.User.id or str(model) == str(models.User.id):
            m_query.filter.return_value.scalar.return_value = user_id
        elif model is models.NotificacionUsuario:
            # Existing notification found!
            m_query.filter.return_value.first.return_value = existing_notif
        elif model is models.Project:
            m_query.filter.return_value.first.return_value = None
        return m_query

    db.query.side_effect = query_side_effect

    res = notify_task_assigned(
        db,
        task=task,
        project=None,
        assigned_by_user_id=None,
    )

    assert res is True
    db.commit.assert_called_once()
    # Staged: ProjectActivityLog, CommunicationLog (No new NotificacionUsuario added)
    assert db.add.call_count == 2


@patch("backend.services.task_notifications.render_task_assignment_email")
@patch("backend.services.task_notifications.email_svc.send_email")
def test_notify_task_assigned_email_failed(mock_send_email, mock_render_email):
    db = MagicMock()
    assignee_id = uuid.uuid4()
    task = DummyTask(id_val=105, assignee_id=assignee_id)
    assignee = DummyPersona(id_val=assignee_id, email="assignee@example.com")

    mock_render_email.return_value = ("Subject", "<p>HTML</p>", "Text")
    mock_send_email.return_value = False  # Email failed

    def query_side_effect(model):
        m_query = MagicMock()
        if model is models.Persona:
            m_query.filter.return_value.first.return_value = assignee
        elif model is models.User.id or getattr(model, "key", None) == "id" or str(model) == str(models.User.id):
            m_query.filter.return_value.scalar.return_value = assignee_id
        elif model is models.Project:
            m_query.filter.return_value.first.return_value = None
        return m_query

    db.query.side_effect = query_side_effect

    res = notify_task_assigned(db, task=task)

    assert res is True
    db.commit.assert_called_once()
    # Staged: ProjectActivityLog, CommunicationLog (NO NotificacionUsuario because email failed)
    assert db.add.call_count == 2


def test_notify_task_assigned_exception_rollback():
    db = MagicMock()
    assignee_id = uuid.uuid4()
    task = DummyTask(id_val=106, assignee_id=assignee_id)
    assignee = DummyPersona(id_val=assignee_id, email="assignee@example.com")

    db.query.return_value.filter.return_value.first.return_value = assignee
    db.add.side_effect = Exception("Database disk error")

    res = notify_task_assigned(db, task=task)

    assert res is False
    db.rollback.assert_called_once()
