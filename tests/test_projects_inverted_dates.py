# -*- coding: utf-8 -*-
"""Regresión: GET /api/projects/{id} no debe lanzar 500 cuando el proyecto
tiene fechas invertidas (start_date > target_date).

Hallazgo en vivo (2026-10-23): el detalle de proyecto respondía 500 cuando
start_date era posterior a la fecha objetivo. El motor EVM tolera la
inconsistencia (SPI=2.0 por PV=0, ES con horizonte forzado a 30 días); el
crash provenía de la cadena de agregados del endpoint (workload /
execution-matrix / KPIs).
"""

from __future__ import annotations

import datetime
import uuid

from backend import models


def test_create_project_rejects_inverted_dates(client, db_session):
    """La API debe rechazar la creación con start_date > target_date (422)."""
    from tests.conftest import auth_headers, seed_admin

    seed_admin(db_session, email="inv-dates-422@example.com")
    headers = auth_headers(client, email="inv-dates-422@example.com")

    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "title": "Proyecto Fechas Invertidas 422",
        "start_date": (now + datetime.timedelta(days=5)).isoformat(),
        "target_date": (now - datetime.timedelta(days=10)).isoformat(),
    }
    r = client.post("/api/projects", json=payload, headers=headers)
    assert r.status_code == 422, f"debe ser 422, fue {r.status_code}: {r.text[:300]}"


def test_update_project_rejects_inverted_dates(client, db_session):
    """PATCH no debe introducir el orden invertido contra datos existentes (422)."""
    from tests.conftest import auth_headers, seed_admin

    seed_admin(db_session, email="inv-dates-patch@example.com")
    headers = auth_headers(client, email="inv-dates-patch@example.com")

    user = db_session.query(models.User).filter_by(email="inv-dates-patch@example.com").first()
    now = datetime.datetime.now(datetime.timezone.utc)
    project = models.Project(
        id=uuid.uuid4(),
        title="Proyecto Patch Fechas OK",
        sede_id=user.sede_id,
        budget_allocated=1000.0,
        start_date=now,
        target_date=now + datetime.timedelta(days=30),
    )
    db_session.add(project)
    db_session.commit()

    r = client.patch(
        f"/api/projects/{project.id}",
        json={"start_date": (now + datetime.timedelta(days=40)).isoformat()},
        headers=headers,
    )
    assert r.status_code == 422, f"debe ser 422, fue {r.status_code}: {r.text[:300]}"


def test_get_project_200_with_inverted_dates(client, db_session):
    """Project con start_date > target_date debe responder 200 en GET detalle."""
    from tests.conftest import auth_headers, seed_admin

    seed_admin(db_session, email="inv-dates@example.com")
    headers = auth_headers(client, email="inv-dates@example.com")

    # Mapear el sede_id desde el usuario sembrado
    user = db_session.query(models.User).filter_by(email="inv-dates@example.com").first()
    sede_id = user.sede_id

    now = datetime.datetime.now(datetime.timezone.utc)
    project = models.Project(
        id=uuid.uuid4(),
        title="Proyecto Fechas Invertidas",
        sede_id=sede_id,
        budget_allocated=60000.0,
        progress_mode="auto_tasks",
        start_date=now + datetime.timedelta(days=5),   # INTENCIONALMENTE FUTURA
        target_date=now - datetime.timedelta(days=10),  # ANTERIOR al inicio
    )
    db_session.add(project)
    db_session.commit()

    r = client.get(f"/api/projects/{project.id}", headers=headers)
    assert r.status_code == 200, f"500 reproducido: {r.status_code} {r.text[:500]}"
    data = r.json()
    assert data["id"] == str(project.id)
    assert data["title"] == "Proyecto Fechas Invertidas"


def test_get_project_200_with_inverted_dates_via_matrix(client, db_session):
    """La matriz de ejecución (sub-recurso del detalle) también debe ser 200."""
    from tests.conftest import auth_headers, seed_admin

    seed_admin(db_session, email="inv-dates-matrix@example.com")
    headers = auth_headers(client, email="inv-dates-matrix@example.com")

    user = db_session.query(models.User).filter_by(email="inv-dates-matrix@example.com").first()
    sede_id = user.sede_id

    now = datetime.datetime.now(datetime.timezone.utc)
    project = models.Project(
        id=uuid.uuid4(),
        title="Matriz Fechas Invertidas",
        sede_id=sede_id,
        budget_allocated=60000.0,
        progress_mode="auto_tasks",
        start_date=now + datetime.timedelta(days=5),
        target_date=now - datetime.timedelta(days=10),
    )
    db_session.add(project)
    db_session.commit()

    r = client.get(f"/api/projects/{project.id}/indicators/execution-matrix", headers=headers)
    assert r.status_code == 200, f"500 reproducido en matrix: {r.status_code} {r.text[:500]}"
