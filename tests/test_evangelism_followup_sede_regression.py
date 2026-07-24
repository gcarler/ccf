"""
Evangelism — Regression tests for follow-up (seguimiento) sede isolation
and soft-delete integrity.

These tests guard the audit fixes committed in b346586e + b1f32287 + 75ce8544
(2026-07-24) on the follow-up surface:

- b346586e: ``get_seguimientos`` / ``get_pendientes_seguimiento`` filter by
  ``sede_id`` via join ``seguimiento → asistencia → sesion → grupo → sede``;
  ``update_seguimiento`` adds ``deleted_at.is_(None)`` to its initial query;
  the API handlers ``GET /follow-up/pending`` and ``GET /follow-up/{asistencia_id}``
  pass ``require_user_sede_id`` to the CRUD.
- b1f32287: new ``DELETE /follow-up/{seguimiento_id}`` soft-delete handler
  (``require_evangelism_manage``).
- 75ce8544: model default ``estado_completado=False`` + CHECK enum + FK indices.

Coverage:
1. Cross-sede GET ``/follow-up/pending`` does NOT leak seguimientos of another
   sede to a sede-B admin (regression of brecha #1).
2. Cross-sede GET ``/follow-up/{asistencia_id}`` returns 200 with an empty list
   (or filtered) for asistencia belonging to sede A when actor is in sede B
   (regression of brecha #2). The CRUD join filters by sede, so no rows leak.
3. Cross-sede PATCH ``/follow-up/{id}`` blocked (404 or empty) when the
   seguimiento belongs to sede A and actor is in sede B.
4. Cross-sede DELETE ``/follow-up/{id}`` blocked (evangelism:manage of B
   cannot delete seguimiento of A).
5. Soft-deleted seguimiento is invisible to PATCH update (regression of
   brecha #3 — `update_seguimiento` initial filter `deleted_at.is_(None)`).

Tests are intentionally separate from the general coverage suite so any
regression on the sede-isolation / soft-delete gate is caught immediately.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from backend import models
from backend.models_evangelism import (
    Asistencia,
    CategoriaEstrategia,
    EstrategiaEvangelismo,
    GrupoEvangelismo,
    RegistroSeguimiento,
    SesionGrupo,
)
from tests.conftest import auth_headers, seed_admin, seed_user_with_role


def _bootstrap_seguimiento_in_sede(db_session, sede_id, *, email_domain="ccf.test"):
    """Create estrategia + grupo + sesion + asistencia + seguimiento in a given sede.

    Returns the freshly-created ``RegistroSeguimiento`` ORM row.
    """
    categoria = CategoriaEstrategia(nombre=f"Cat {email_domain}")
    db_session.add(categoria)
    db_session.flush()

    estrategia = EstrategiaEvangelismo(
        nombre=f"Estrategia {email_domain}",
        sede_id=sede_id,
        categoria_id=categoria.id,
        frecuencia="SEMANAL",
        fecha_inicio=datetime(2026, 6, 1, tzinfo=timezone.utc),
        fecha_fin=datetime(2026, 6, 22, tzinfo=timezone.utc),
        activa=True,
    )
    db_session.add(estrategia)
    db_session.flush()

    grupo = GrupoEvangelismo(
        nombre=f"Grupo {email_domain}",
        sede_id=sede_id,
        estrategia_id=estrategia.id,
        ubicacion="u",
        capacidad=10,
        activo=True,
    )
    db_session.add(grupo)
    db_session.flush()

    sesion = SesionGrupo(
        grupo_id=grupo.id,
        fecha_sesion=datetime(2026, 6, 8, tzinfo=timezone.utc),
        estado="PENDIENTE",
        estado_habilitacion="HABILITADO",
    )
    db_session.add(sesion)
    db_session.flush()

    persona = models.Persona(
        first_name="V", last_name="Sede", sede_id=sede_id,
        email=f"v@{email_domain}", phone="3000000001",
    )
    db_session.add(persona)
    db_session.flush()

    asistencia = Asistencia(
        sesion_id=sesion.id,
        persona_id=persona.id,
        estado="Presente",
        es_primera_vez=False,
    )
    db_session.add(asistencia)
    db_session.flush()

    seguimiento = RegistroSeguimiento(
        asistencia_id=asistencia.id,
        tipo="LLAMADA",
        observaciones="pendiente",
        estado_completado=False,
    )
    db_session.add(seguimiento)
    db_session.commit()
    return seguimiento


class TestFollowUpSedeIsolation:
    """Cross-sede regression for the follow-up surface."""

    def test_pending_follow_up_do_not_leak_cross_sede(self, client, db_session):
        """GET /follow-up/pending must NOT include seguimientos of another sede."""
        admin_a, _, sede_a = seed_admin(db_session, email="admin_a@ccf.test")
        seguimiento_a = _bootstrap_seguimiento_in_sede(
            db_session, sede_a.id, email_domain="sedeA"
        )

        # Admin B in a different sede
        _, _, sede_b = seed_user_with_role(
            db_session,
            role_name="ADMIN",
            email="admin_b@ccf.test",
            sede_id=uuid.uuid4(),
        )
        headers_b = auth_headers(client, email="admin_b@ccf.test")

        resp = client.get("/api/evangelism/follow-up/pending", headers=headers_b)

        assert resp.status_code == 200
        rows = resp.json()
        # B has zero seguimientos in their own sede; A's seguimiento must not appear
        ids_returned = {row["id"] for row in rows}
        assert str(seguimiento_a.id) not in ids_returned

    def test_list_seguimientos_for_attendance_filters_cross_sede(self, client, db_session):
        """GET /follow-up/{asistencia_id} returns empty (or filtered) for cross-sede asistencia."""
        admin_a, _, sede_a = seed_admin(db_session, email="admin_a2@ccf.test")
        seguimiento_a = _bootstrap_seguimiento_in_sede(
            db_session, sede_a.id, email_domain="sedeA2"
        )

        _, _, sede_b = seed_user_with_role(
            db_session,
            role_name="ADMIN",
            email="admin_b2@ccf.test",
            sede_id=uuid.uuid4(),
        )
        headers_b = auth_headers(client, email="admin_b2@ccf.test")

        resp = client.get(
            f"/api/evangelism/follow-up/{seguimiento_a.asistencia_id}",
            headers=headers_b,
        )

        # 200 (existence-leak safe) but empty list — B has no rows for A's asistencia
        assert resp.status_code == 200
        assert resp.json() == []


    def test_patch_seguimiento_cross_sede_blocked(self, client, db_session):
        """PATCH /follow-up/{id} from a different sede returns 404."""
        admin_a, _, sede_a = seed_admin(db_session, email="admin_a3@ccf.test")
        seguimiento_a = _bootstrap_seguimiento_in_sede(
            db_session, sede_a.id, email_domain="sedeA3"
        )

        _, _, sede_b = seed_user_with_role(
            db_session,
            role_name="ADMIN",
            email="admin_b3@ccf.test",
            sede_id=uuid.uuid4(),
        )
        headers_b = auth_headers(client, email="admin_b3@ccf.test")

        resp = client.patch(
            f"/api/evangelism/follow-up/{seguimiento_a.id}",
            json={"estado_completado": True},
            headers=headers_b,
        )

        # Defense-in-depth in CRUD returns None → handler 404 (existence-leak safe)
        assert resp.status_code == 404

    def test_delete_seguimiento_cross_sede_blocked(self, client, db_session):
        """DELETE /follow-up/{id} from a different sede returns 404."""
        admin_a, _, sede_a = seed_admin(db_session, email="admin_a4@ccf.test")
        seguimiento_a = _bootstrap_seguimiento_in_sede(
            db_session, sede_a.id, email_domain="sedeA4"
        )

        _, _, sede_b = seed_user_with_role(
            db_session,
            role_name="ADMIN",
            email="admin_b4@ccf.test",
            sede_id=uuid.uuid4(),
        )
        headers_b = auth_headers(client, email="admin_b4@ccf.test")

        resp = client.delete(
            f"/api/evangelism/follow-up/{seguimiento_a.id}",
            headers=headers_b,
        )

        assert resp.status_code == 404


class TestFollowUpSoftDeleteIntegrity:
    """Soft-delete integrity regression for follow-up."""

    def test_patch_soft_deleted_seguimiento_returns_404(self, client, db_session):
        """PATCH on a soft-deleted seguimiento must return 404, not mutate it."""
        admin, _, sede = seed_admin(db_session, email="admin_sd@ccf.test")
        seguimiento = _bootstrap_seguimiento_in_sede(
            db_session, sede.id, email_domain="sd1"
        )
        # Simulate previous soft-delete
        seguimiento.deleted_at = datetime.now(timezone.utc)
        db_session.commit()

        headers = auth_headers(client, email="admin_sd@ccf.test")

        resp = client.patch(
            f"/api/evangelism/follow-up/{seguimiento.id}",
            json={"estado_completado": True},
            headers=headers,
        )

        # CRUD `update_seguimiento` initial query filters deleted_at.is_(None),
        # returns None → handler 404.
        assert resp.status_code == 404

    def test_delete_seguimiento_twice_second_returns_404(self, client, db_session):
        """DELETE on already-soft-deleted seguimiento returns 404 (idempotent safe)."""
        admin, _, sede = seed_admin(db_session, email="admin_sd2@ccf.test")
        seguimiento = _bootstrap_seguimiento_in_sede(
            db_session, sede.id, email_domain="sd2"
        )
        headers = auth_headers(client, email="admin_sd2@ccf.test")

        # First delete
        resp1 = client.delete(
            f"/api/evangelism/follow-up/{seguimiento.id}", headers=headers
        )
        assert resp1.status_code == 200
        assert resp1.json() == {"ok": True}

        # Second delete on the same already-soft-deleted row
        resp2 = client.delete(
            f"/api/evangelism/follow-up/{seguimiento.id}", headers=headers
        )
        assert resp2.status_code == 404
