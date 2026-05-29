from backend import models
from backend.core.security import get_password_hash


def seed_admin(db_session, email="admin@example.com", password="secret123"):
    user = models.User(
        username="admin",
        email=email,
        password_hash=get_password_hash(password),
        role="admin",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def auth_headers(client, email="admin@example.com", password="secret123"):
    response = client.post(
        "/api/auth/login",
        data={"username": email, "password": password, "grant_type": "password"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_project_whiteboard_roundtrip(client, db_session):
    seed_admin(db_session)
    headers = auth_headers(client)

    create_response = client.post(
        "/api/projects/",
        json={"title": "Proyecto Faro", "description": "Prueba de whiteboard"},
        headers=headers,
    )
    assert create_response.status_code == 201
    project_id = create_response.json()["id"]

    whiteboard_response = client.post(
        f"/api/projects/{project_id}/whiteboard",
        json={
            "title": "Pizarra Estrategica",
            "elements_json": '[{"id":1}]',
            "thumbnail_url": "/static/thumb.png",
        },
        headers=headers,
    )
    assert whiteboard_response.status_code == 200
    whiteboard = whiteboard_response.json()
    assert whiteboard["project_id"] == project_id
    assert whiteboard["title"] == "Pizarra Estrategica"
    assert whiteboard["elements_json"] == '[{"id":1}]'
    assert whiteboard["thumbnail_url"] == "/static/thumb.png"

    fetch_response = client.get(
        f"/api/projects/{project_id}/whiteboard", headers=headers
    )
    assert fetch_response.status_code == 200
    fetched = fetch_response.json()
    assert fetched["title"] == "Pizarra Estrategica"
    assert fetched["thumbnail_url"] == "/static/thumb.png"


def test_project_comments_and_task_filter(client, db_session):
    seed_admin(db_session)
    headers = auth_headers(client)

    create_project = client.post(
        "/api/projects/",
        json={"title": "Proyecto Comentarios", "description": "Prueba"},
        headers=headers,
    )
    assert create_project.status_code == 201
    project_id = create_project.json()["id"]

    task_response = client.post(
        f"/api/projects/{project_id}/tasks",
        json={
            "title": "Tarea 1",
            "status": "todo",
            "priority": "normal",
            "category": "General",
        },
        headers=headers,
    )
    assert task_response.status_code == 201
    task_id = task_response.json()["id"]

    comment_response = client.post(
        "/api/projects/comments",
        json={
            "project_id": project_id,
            "task_id": task_id,
            "content": "Comentario desde proyecto",
        },
        headers=headers,
    )
    assert comment_response.status_code == 200
    comment = comment_response.json()
    assert comment["project_id"] == project_id
    assert comment["task_id"] == task_id
    assert comment["content"] == "Comentario desde proyecto"

    list_response = client.get(
        f"/api/projects/comments?project_id={project_id}&task_id={task_id}",
        headers=headers,
    )
    assert list_response.status_code == 200
    rows = list_response.json()
    assert len(rows) == 1
    assert rows[0]["id"] == comment["id"]

    activities_response = client.get(
        f"/api/projects/activities?project_id={project_id}",
        headers=headers,
    )
    assert activities_response.status_code == 200
    activities = activities_response.json()
    assert any(
        row["kind"] == "comment_added"
        and row["description"] == "Comentario desde proyecto"
        for row in activities
    )


def test_projects_list_coerces_legacy_string_labels(client, db_session):
    seed_admin(db_session)
    headers = auth_headers(client)

    project_response = client.post(
        "/api/projects/",
        json={"title": "Proyecto Legacy Labels", "description": "Prueba"},
        headers=headers,
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    # Insert legacy-like task payload where labels is stored as scalar text.
    legacy_task = models.ProjectTask(
        project_id=project_id,
        title="Tarea Legacy",
        status="todo",
        priority="normal",
    )
    legacy_task.labels = "Fase"
    db_session.add(legacy_task)
    db_session.commit()

    list_response = client.get("/api/projects/", headers=headers)
    assert list_response.status_code == 200
    projects = list_response.json()
    target = next((p for p in projects if p["id"] == project_id), None)
    assert target is not None
    labels = [
        t.get("labels")
        for t in target.get("tasks", [])
        if t.get("title") == "Tarea Legacy"
    ]
    assert labels
    assert labels[0] == ["Fase"]


def test_project_attachment_upload_adds_activity(client, db_session):
    seed_admin(db_session)
    headers = auth_headers(client)

    project_response = client.post(
        "/api/projects/",
        json={"title": "Proyecto Archivos", "description": "Prueba"},
        headers=headers,
    )
    project_id = project_response.json()["id"]

    task_response = client.post(
        f"/api/projects/{project_id}/tasks",
        json={"title": "Tarea con archivo", "status": "todo", "priority": "normal"},
        headers=headers,
    )
    task_id = task_response.json()["id"]

    upload_response = client.post(
        f"/api/projects/{project_id}/tasks/{task_id}/attachments",
        headers=headers,
        files={"file": ("brief.pdf", b"contenido", "application/pdf")},
    )
    assert upload_response.status_code == 200
    uploaded_task = upload_response.json()
    assert uploaded_task["attachments"][0]["filename"] == "brief.pdf"

    activities_response = client.get(
        f"/api/projects/activities?project_id={project_id}",
        headers=headers,
    )
    assert activities_response.status_code == 200
    activities = activities_response.json()
    assert any(
        row["kind"] == "attachment_added" and "brief.pdf" in row["description"]
        for row in activities
    )


def test_project_milestone_creation_adds_activity(client, db_session):
    seed_admin(db_session)
    headers = auth_headers(client)

    project_response = client.post(
        "/api/projects/",
        json={"title": "Proyecto Hitos", "description": "Prueba"},
        headers=headers,
    )
    project_id = project_response.json()["id"]

    milestone_response = client.post(
        f"/api/projects/{project_id}/milestones",
        json={"title": "Primer hito"},
        headers=headers,
    )
    print("MILESTONE RESPONSE:", milestone_response.text)
    assert milestone_response.status_code == 201

    activities_response = client.get(
        f"/api/projects/activities?project_id={project_id}",
        headers=headers,
    )
    assert activities_response.status_code == 200
    activities = activities_response.json()
    assert any(
        row["kind"] == "milestone_created" and "Primer hito" in row["description"]
        for row in activities
    )


def test_project_supplies_can_be_created_and_updated(client, db_session):
    seed_admin(db_session)
    headers = auth_headers(client)

    project_response = client.post(
        "/api/projects/",
        json={"title": "Proyecto Insumos", "description": "Prueba"},
        headers=headers,
    )
    project_id = project_response.json()["id"]

    task_response = client.post(
        f"/api/projects/{project_id}/tasks",
        json={"title": "Preparar culto", "status": "todo", "priority": "normal"},
        headers=headers,
    )
    task_id = task_response.json()["id"]

    create_response = client.post(
        f"/api/projects/{project_id}/tasks/{task_id}/supplies",
        json={"item_name": "Microfonos", "quantity": 2, "status": "pending"},
        headers=headers,
    )
    assert create_response.status_code == 201
    supply = create_response.json()
    assert supply["item_name"] == "Microfonos"
    assert supply["quantity"] == 2

    patch_response = client.patch(
        f"/api/projects/{project_id}/tasks/{task_id}/supplies/{supply['id']}",
        json={"quantity": 3, "status": "ready"},
        headers=headers,
    )
    assert patch_response.status_code == 200
    updated = patch_response.json()
    assert updated["quantity"] == 3
    assert updated["status"] == "ready"

    list_response = client.get(
        f"/api/projects/{project_id}/tasks/{task_id}/supplies",
        headers=headers,
    )
    assert list_response.status_code == 200
    assert list_response.json()[0]["id"] == supply["id"]

    activities_response = client.get(
        f"/api/projects/activities?project_id={project_id}",
        headers=headers,
    )
    activities = activities_response.json()
    assert any(row["kind"] == "supply_added" for row in activities)
    assert any(row["kind"] == "supply_updated" for row in activities)


def test_project_milestone_can_be_completed_and_edited(client, db_session):
    seed_admin(db_session)
    headers = auth_headers(client)

    project_response = client.post(
        "/api/projects/",
        json={"title": "Proyecto Seguimiento", "description": "Prueba"},
        headers=headers,
    )
    project_id = project_response.json()["id"]

    milestone_response = client.post(
        f"/api/projects/{project_id}/milestones",
        json={"title": "Visita inicial"},
        headers=headers,
    )
    milestone_id = milestone_response.json()["id"]

    completed_response = client.patch(
        f"/api/projects/{project_id}/milestones/{milestone_id}",
        json={"is_completed": True},
        headers=headers,
    )
    assert completed_response.status_code == 200
    assert completed_response.json()["is_completed"] is True

    edited_response = client.patch(
        f"/api/projects/{project_id}/milestones/{milestone_id}",
        json={"title": "Visita inicial confirmada"},
        headers=headers,
    )
    assert edited_response.status_code == 200
    assert edited_response.json()["title"] == "Visita inicial confirmada"

    activities_response = client.get(
        f"/api/projects/activities?project_id={project_id}",
        headers=headers,
    )
    activities = activities_response.json()
    assert any(row["kind"] == "milestone_completed" for row in activities)
    assert any(row["kind"] == "milestone_updated" for row in activities)
