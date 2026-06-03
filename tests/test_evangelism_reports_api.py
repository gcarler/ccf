import uuid
from datetime import datetime, date, timezone

import pytest
from backend import models
from tests.conftest import seed_admin_v2, auth_headers_v2


def _seed_sede(db_session):
    sede = models.Sede(
        id=uuid.uuid4(), nombre="Test Sede", ciudad="Bogota", es_activa=True
    )
    db_session.add(sede)
    db_session.commit()
    db_session.refresh(sede)
    return sede


def _seed_categoria(db_session):
    cat = models.CategoriaEstrategia(nombre="Test Cat", descripcion="Desc")
    db_session.add(cat)
    db_session.commit()
    db_session.refresh(cat)
    return cat


@pytest.mark.xfail(reason="reportlab not installed in test env", strict=False)
def test_attendance_pdf_for_group(client, db_session):
    admin, persona, sede = seed_admin_v2(db_session)
    headers = auth_headers_v2(client)
    cat = _seed_categoria(db_session)

    import uuid
    estrategia = models.EstrategiaEvangelismo(
        id=uuid.uuid4(),
        nombre="Estrategia Test",
        categoria_id=cat.id,
        sede_id=sede.id,
        frecuencia="SEMANAL",
        activa=True,
    )
    db_session.add(estrategia)
    db_session.commit()

    grupo = models.GrupoEvangelismo(
        estrategia_id=estrategia.id,
        sede_id=sede.id,
        codigo="GRP-001",
        nombre="Grupo Test",
        lider_persona_id=persona.id,
        activo=True,
    )
    db_session.add(grupo)
    db_session.commit()
    db_session.refresh(grupo)

    resp = client.get(
        f"/api/evangelism/reports/group/{grupo.id}/attendance-pdf",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"


def test_attendance_excel_for_group(client, db_session):
    admin, persona, sede = seed_admin_v2(db_session)
    headers = auth_headers_v2(client)
    cat = _seed_categoria(db_session)

    estrategia = models.EstrategiaEvangelismo(
        id=uuid.uuid4(),
        nombre="Estrategia Test 2",
        categoria_id=cat.id,
        sede_id=sede.id,
        frecuencia="SEMANAL",
        activa=True,
    )
    db_session.add(estrategia)
    db_session.commit()

    grupo = models.GrupoEvangelismo(
        estrategia_id=estrategia.id,
        sede_id=sede.id,
        codigo="GRP-002",
        nombre="Grupo Test 2",
        lider_persona_id=persona.id,
        activo=True,
    )
    db_session.add(grupo)
    db_session.commit()
    db_session.refresh(grupo)

    resp = client.get(
        f"/api/evangelism/reports/group/{grupo.id}/attendance-excel",
        headers=headers,
    )
    assert resp.status_code == 200
    assert (
        resp.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


def test_strategy_summary(client, db_session):
    admin, persona, sede = seed_admin_v2(db_session)
    headers = auth_headers_v2(client)
    cat = _seed_categoria(db_session)

    estrategia = models.EstrategiaEvangelismo(
        id=uuid.uuid4(),
        nombre="Estrategia Resumen",
        categoria_id=cat.id,
        sede_id=sede.id,
        frecuencia="MENSUAL",
        activa=True,
    )
    db_session.add(estrategia)
    db_session.commit()

    grupo = models.GrupoEvangelismo(
        estrategia_id=estrategia.id,
        sede_id=sede.id,
        codigo="GRP-003",
        nombre="Grupo Resumen",
        lider_persona_id=persona.id,
        activo=True,
    )
    db_session.add(grupo)
    db_session.commit()

    resp = client.get(
        f"/api/evangelism/reports/strategy/{estrategia.id}/summary",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["estrategia_id"] == estrategia.id
    assert data["nombre"] == "Estrategia Resumen"
    assert "grupos" in data


def test_strategy_summary_404_for_missing_strategy(client, db_session):
    seed_admin_v2(db_session)
    headers = auth_headers_v2(client)
    resp = client.get(
        "/api/evangelism/reports/strategy/NONEXISTENT/summary", headers=headers
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Estrategia no encontrada"
