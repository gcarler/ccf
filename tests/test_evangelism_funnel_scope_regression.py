"""Regression tests for strategy funnel tenant/strategy scoping."""
from __future__ import annotations

import uuid

from backend import models
from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def test_funnel_ignores_history_for_unrelated_person(client, db_session):
    """Velocity in one funnel must not include another person's history."""
    _admin, _admin_persona, sede = _seed_admin(db_session, email="funnel-scope@test.com")
    headers = _auth_headers(client, email="funnel-scope@test.com", password="testpass123")

    target_persona = models.Persona(
        id=uuid.uuid4(),
        first_name="Target",
        last_name="Person",
        sede_id=sede.id,
    )
    unrelated_persona = models.Persona(
        id=uuid.uuid4(),
        first_name="Unrelated",
        last_name="Person",
        sede_id=sede.id,
    )
    db_session.add_all([target_persona, unrelated_persona])
    db_session.flush()

    strategy = client.post(
        "/api/evangelism/strategies",
        json={"name": f"Scope-{uuid.uuid4().hex[:8]}"},
        headers=headers,
    )
    assert strategy.status_code == 200, strategy.text
    strategy_id = uuid.UUID(strategy.json()["id"])

    group = models.GrupoEvangelismo(
        id=uuid.uuid4(),
        nombre="Scoped funnel",
        sede_id=sede.id,
        estrategia_id=strategy_id,
        lider_persona_id=target_persona.id,
    )
    role = models.RolPersonalizadoEstrategia(
        id=uuid.uuid4(),
        estrategia_id=strategy_id,
        nombre_rol="colider",
    )
    db_session.add_all([group, role])
    db_session.flush()
    db_session.add(
        models.ParticipanteGrupo(
            id=uuid.uuid4(),
            grupo_id=group.id,
            persona_id=target_persona.id,
            rol_base="personalizado",
            rol_personalizado_id=role.id,
            activo=True,
        )
    )
    db_session.add_all(
        [
            models.HistorialEmbudo(
                id=uuid.uuid4(),
                persona_id=target_persona.id,
                rol_anterior="invitado",
                rol_nuevo="colider",
                dias_en_estado_anterior=15,
            ),
            models.HistorialEmbudo(
                id=uuid.uuid4(),
                persona_id=unrelated_persona.id,
                rol_anterior="invitado",
                rol_nuevo="colider",
                dias_en_estado_anterior=999,
            ),
        ]
    )
    db_session.commit()

    response = client.get(
        f"/api/evangelism/analytics/strategy/{strategy_id}/funnel",
        headers=headers,
    )
    assert response.status_code == 200, response.text
    colider = next(stage for stage in response.json()["stages"] if stage["key"] == "colider")
    assert colider["avg_days_before"] == 15
