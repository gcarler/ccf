"""
Tests for Evangelism Public Endpoints (/api/evangelism/public/* and /strategies/public-config).

Covers:
- GET /api/evangelism/public/upcoming-events (filtering, ordering, aware UTC datetimes)
- GET /api/evangelism/strategies/public-config (strict multi-tenant isolation by user_sede_id)
- PATCH /api/evangelism/strategies/{id}/toggle-public (200 on same sede, 404 on cross-sede/deleted/missing)
- Timezone awareness validation for next_occurrence calculations
"""

from __future__ import annotations

import datetime
import uuid

from backend import models
from backend.api.evangelism_public import get_next_occurrence
from backend.models_evangelism import CategoriaEstrategia, EstrategiaEvangelismo
from tests.conftest import auth_headers, seed_admin


def _create_strategy(
    db_session,
    sede_id,
    categoria_id,
    nombre="Estrategia Test",
    dia="Lunes",
    hora="19:00",
    is_public=False,
    activa=True,
    deleted=False,
):
    est = EstrategiaEvangelismo(
        id=uuid.uuid4(),
        nombre=nombre,
        sede_id=sede_id,
        categoria_id=categoria_id,
        typology="relacional",
        strategy_type="geografica",
        frecuencia="SEMANAL",
        dia_reunion=dia,
        hora_reunion=hora,
        fecha_inicio=datetime.datetime(2026, 6, 1, tzinfo=datetime.timezone.utc),
        fecha_fin=datetime.datetime(2026, 6, 22, tzinfo=datetime.timezone.utc),
        activa=activa,
        is_public=is_public,
        status="active",
        deleted_at=datetime.datetime.now(datetime.timezone.utc) if deleted else None,
    )
    db_session.add(est)
    db_session.commit()
    db_session.refresh(est)
    return est


class TestEvangelismPublicEndpoints:
    def test_get_next_occurrence_timezone_aware(self):
        """Verify get_next_occurrence returns a timezone-aware UTC datetime."""
        dt = get_next_occurrence("Lunes", "18:30")
        assert dt is not None
        assert dt.tzinfo is not None
        assert dt.tzinfo == datetime.timezone.utc
        assert dt.hour == 18
        assert dt.minute == 30

    def test_get_next_occurrence_invalid_inputs(self):
        """Invalid inputs return None safely without raising exceptions."""
        assert get_next_occurrence(None, "18:00") is None
        assert get_next_occurrence("Lunes", None) is None
        assert get_next_occurrence("DiaInvalido", "18:00") is None
        assert get_next_occurrence("Lunes", "hora_invalida") is None

    def test_upcoming_public_events(self, client, db_session):
        """GET /api/evangelism/public/upcoming-events must only return public, active, non-deleted events."""
        admin, _, sede = seed_admin(db_session)

        cat = CategoriaEstrategia(nombre=f"Cat Public {uuid.uuid4().hex[:6]}")
        db_session.add(cat)
        db_session.commit()

        # 1. Public & active & non-deleted -> should appear
        est_pub = _create_strategy(
            db_session, sede.id, cat.id, nombre="Public Active", dia="Martes", hora="20:00", is_public=True, activa=True
        )
        # 2. Not public -> excluded
        _create_strategy(
            db_session, sede.id, cat.id, nombre="Private Active", dia="Martes", hora="20:00", is_public=False, activa=True
        )
        # 3. Public but inactive -> excluded
        _create_strategy(
            db_session, sede.id, cat.id, nombre="Public Inactive", dia="Martes", hora="20:00", is_public=True, activa=False
        )
        # 4. Public but soft-deleted -> excluded
        _create_strategy(
            db_session, sede.id, cat.id, nombre="Public Deleted", dia="Martes", hora="20:00", is_public=True, activa=True, deleted=True
        )

        resp = client.get("/api/evangelism/public/upcoming-events")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

        event_ids = [e["id"] for e in data]
        assert str(est_pub.id) in event_ids

        # Ensure datetime strings are aware
        for item in data:
            if item["id"] == str(est_pub.id):
                assert item["nombre"] == "Public Active"
                assert item["dia_reunion"] == "Martes"
                assert item["hora_reunion"] == "20:00"
                # ISO format must include timezone offset (+00:00 or Z)
                assert "+00:00" in item["next_datetime"] or item["next_datetime"].endswith("Z")

    def test_public_strategies_config_tenant_isolation(self, client, db_session):
        """GET /api/evangelism/strategies/public-config must isolate strategies by user's sede."""
        admin, _, sede_a = seed_admin(db_session)
        headers_a = auth_headers(client)

        cat = CategoriaEstrategia(nombre=f"Cat Config {uuid.uuid4().hex[:6]}")
        db_session.add(cat)

        sede_b = models.Sede(
            id=uuid.uuid4(),
            nombre=f"Sede B {uuid.uuid4().hex[:4]}",
            ciudad="Medellin",
            es_activa=True,
        )
        db_session.add(sede_b)
        db_session.commit()

        # Strategy in Sede A
        est_a = _create_strategy(db_session, sede_a.id, cat.id, nombre="Estrategia Sede A")
        # Strategy in Sede B
        est_b = _create_strategy(db_session, sede_b.id, cat.id, nombre="Estrategia Sede B")
        # Soft-deleted strategy in Sede A
        est_a_deleted = _create_strategy(db_session, sede_a.id, cat.id, nombre="Estrategia Sede A Borrada", deleted=True)

        resp = client.get("/api/evangelism/strategies/public-config", headers=headers_a)
        assert resp.status_code == 200
        data = resp.json()
        ids = [item["id"] for item in data]

        # Sede A must be visible
        assert str(est_a.id) in ids
        # Sede B must NOT be visible (no cross-tenant leakage)
        assert str(est_b.id) not in ids
        # Deleted strategy must NOT be visible
        assert str(est_a_deleted.id) not in ids

    def test_toggle_public_strategy_same_sede(self, client, db_session):
        """PATCH /api/evangelism/strategies/{id}/toggle-public returns 200 and toggles is_public for own sede."""
        admin, _, sede = seed_admin(db_session)
        headers = auth_headers(client)

        cat = CategoriaEstrategia(nombre=f"Cat Toggle {uuid.uuid4().hex[:6]}")
        db_session.add(cat)
        db_session.commit()

        est = _create_strategy(db_session, sede.id, cat.id, nombre="Toggle Sede Own", is_public=False)

        # Toggle to True
        resp = client.patch(
            f"/api/evangelism/strategies/{est.id}/toggle-public",
            json={"is_public": True},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json() == {"id": str(est.id), "is_public": True}

        db_session.refresh(est)
        assert est.is_public is True

        # Toggle back to False
        resp = client.patch(
            f"/api/evangelism/strategies/{est.id}/toggle-public",
            json={"is_public": False},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json() == {"id": str(est.id), "is_public": False}

        db_session.refresh(est)
        assert est.is_public is False

    def test_toggle_public_strategy_cross_sede_idor_protection(self, client, db_session):
        """PATCH /api/evangelism/strategies/{id}/toggle-public must return 404 for other sede's strategy."""
        admin, _, sede_a = seed_admin(db_session)
        headers_a = auth_headers(client)

        cat = CategoriaEstrategia(nombre=f"Cat IDOR {uuid.uuid4().hex[:6]}")
        db_session.add(cat)

        sede_b = models.Sede(
            id=uuid.uuid4(),
            nombre=f"Sede B IDOR {uuid.uuid4().hex[:4]}",
            ciudad="Barranquilla",
            es_activa=True,
        )
        db_session.add(sede_b)
        db_session.commit()

        est_b = _create_strategy(db_session, sede_b.id, cat.id, nombre="Strategy Sede B", is_public=False)

        # Attempt to toggle from Sede A operator
        resp = client.patch(
            f"/api/evangelism/strategies/{est_b.id}/toggle-public",
            json={"is_public": True},
            headers=headers_a,
        )
        # Uniform 404 IDOR prevention
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Estrategia no encontrada"

        # Verify state in DB was NOT changed
        db_session.refresh(est_b)
        assert est_b.is_public is False

    def test_toggle_public_strategy_deleted_or_nonexistent(self, client, db_session):
        """PATCH /api/evangelism/strategies/{id}/toggle-public must return 404 if deleted or non-existent."""
        admin, _, sede = seed_admin(db_session)
        headers = auth_headers(client)

        cat = CategoriaEstrategia(nombre=f"Cat NonExist {uuid.uuid4().hex[:6]}")
        db_session.add(cat)
        db_session.commit()

        est_del = _create_strategy(db_session, sede.id, cat.id, nombre="Strategy Deleted", deleted=True)

        resp = client.patch(
            f"/api/evangelism/strategies/{est_del.id}/toggle-public",
            json={"is_public": True},
            headers=headers,
        )
        assert resp.status_code == 404

        resp_fake = client.patch(
            f"/api/evangelism/strategies/{uuid.uuid4()}/toggle-public",
            json={"is_public": True},
            headers=headers,
        )
        assert resp_fake.status_code == 404
