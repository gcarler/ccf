"""Tests unitarios del motor de indicadores: CREMA (C,R,E,M,A), records y sync reactivo.

Cubre las brechas G1–G6 documentadas en
docs/AUDITORIA_MOTOR_CALCULO_INDICADORES_PROYECTOS_20261021.md
(TKT-PROJECTS-AUDIT-INDICATOR-ENGINE-CREMA-SYNC-PRO-01):
- G1: validate_crema_indicator (criterios, bandas de estado, determinismo).
- G4: SPI con 4 decimales en mediciones manuales.
- G5: SPI None con meta inválida (<= 0) + bandera target_value_valid.
- G3: el upsert del sync preserva los records manuales del mismo período.
- G6: indicadores huérfanos de componentes eliminados quedan marcados.
- G2: hook reactivo notify_project_execution_change_safe refresca sin sembrar.
"""

import datetime
import uuid
from datetime import timedelta, timezone

import pytest

from backend import models, schemas
from backend.crud import projects as crud
from tests.conftest import seed_admin


# ──────────────────────────────────────────────────────────────────────
# G1 — validate_crema_indicator
# ──────────────────────────────────────────────────────────────────────


def _crema_payload(**overrides):
    base = {
        "name": "Porcentaje de Avance Físico del Componente EDT",
        "description": "Dato metodológico de prueba unitaria",
        "level": "FINANCIERO_EVM",
        "calculation_type": "COSTO_EFICIENCIA",
        "unit_of_measure": "%",
        "target_value": 100.0,
        "frequency": "mensual",
    }
    base.update(overrides)
    return base


def test_validate_crema_indicator_indicator_perfecto_puntua_100():
    res = crud.validate_crema_indicator(_crema_payload())
    assert res["score"] == 100.0
    assert res["status"] == "EXCELENTE"
    for key in ("C", "R", "E", "M", "A"):
        assert res["criteria"][key]["score"] == 20.0
        assert res["criteria"][key]["passed"] is True
    assert res["summary"]


def test_validate_crema_indicator_criterio_c_nombre_breve_se_recomienda():
    res = crud.validate_crema_indicator(_crema_payload(name="Cuadros"))
    c = res["criteria"]["C"]
    assert c["score"] == 10.0  # 6 por longitud 4-7 + 4 sin palabra-métrica
    assert c["passed"] is False
    assert c["recommendations"]


def test_validate_crema_indicator_nivel_no_canonico_solo_media_puntos():
    res = crud.validate_crema_indicator(_crema_payload(level="NIVEL_IMPROBABLE"))
    r = res["criteria"]["R"]
    assert r["score"] == 10.0
    assert r["passed"] is False
    assert "NIVEL_IMPROBABLE" in r["recommendations"][0]


def test_validate_crema_indicator_calculo_no_canonico_pierde_puntos():
    res = crud.validate_crema_indicator(_crema_payload(calculation_type="PROMEDIO_MAGICO"))
    a = res["criteria"]["A"]
    assert a["score"] == 8.0
    assert a["passed"] is False


def test_validate_crema_indicator_banda_bueno():
    # 10 (C breve) + 20 (R) + 15 (E anual) + 15 (M meta=0) + 20 (A) = 80 → BUENO
    res = crud.validate_crema_indicator(
        _crema_payload(
            name="Cuadros",
            level="GESTION_PROCESO",
            calculation_type="PORCENTAJE_PROPORCION",
            frequency="anual",
            unit_of_measure="unidades",
            target_value=0.0,
        )
    )
    assert res["score"] == 80.0
    assert res["status"] == "BUENO"


def test_validate_crema_indicator_banda_regular():
    # 10 (C) + 10 (R inválido) + 15 (E anual) + 15 (M) + 8 (A) = 58 → REGULAR
    res = crud.validate_crema_indicator(
        _crema_payload(
            name="Cuadros",
            level="NIVEL_IMPROBABLE",
            calculation_type="PROMEDIO_MAGICO",
            frequency="anual",
            unit_of_measure="unidades",
            target_value=0.0,
        )
    )
    assert res["score"] == 58.0
    assert res["status"] == "REGULAR"


def test_validate_crema_indicator_banda_deficiente():
    # 7 (C nominal) + 10 (R) + 12 (E) + 0 (M) + 8 (A) = 37 → DEFICIENTE
    res = crud.validate_crema_indicator(
        _crema_payload(
            name="",
            level="NIVEL_IMPROBABLE",
            calculation_type="PROMEDIO_MAGICO",
            frequency="diario",
            unit_of_measure=None,
            target_value=None,
        )
    )
    assert res["score"] == 37.0
    assert res["status"] == "DEFICIENTE"


def test_validate_crema_indicator_determinista_sin_efectos():
    primero = crud.validate_crema_indicator(_crema_payload())
    segundo = crud.validate_crema_indicator(_crema_payload())
    assert primero == segundo


# ──────────────────────────────────────────────────────────────────────
# Helpers de DB
# ──────────────────────────────────────────────────────────────────────


def _seed_project_with_task(db_session, email, progress_pct=50.0, with_component=True):
    user, persona, sede = seed_admin(db_session, email=email)
    now = datetime.datetime.now(timezone.utc)
    project = models.Project(
        id=uuid.uuid4(),
        title="Proyecto Motor Indicadores",
        sede_id=sede.id,
        budget_allocated=10000.0,
        progress_mode="auto_tasks",
    )
    db_session.add(project)
    db_session.flush()
    comp = None
    if with_component:
        comp = models.ProjectComponent(
            id=uuid.uuid4(),
            project_id=project.id,
            code="EDT-A",
            name="Módulo A",
            budget_allocated=10000.0,
            order_index=1,
        )
        db_session.add(comp)
        db_session.flush()
    task = models.ProjectTask(
        id=uuid.uuid4(),
        project_id=project.id,
        component_id=comp.id if comp else None,
        title="Actividad A",
        status="in_progress",
        estimated_hours=40.0,
        physical_progress_pct=progress_pct,
    )
    db_session.add(task)
    db_session.commit()
    return user, persona, sede, project, comp, task


def _create_auto_indicator(db_session, project, persona, source_type, component_id=None, target=100.0):
    return crud.create_project_indicator(
        db_session,
        project.id,
        schemas.ProjectIndicatorCreate(
            code="PRO-X",
            name="Indicador de prueba de ejecución real",
            description="Tributación automática",
            level="COMPONENTE_EDT" if component_id else "PRODUCTO_PRINCIPAL",
            calculation_type="PORCENTAJE_PROPORCION",
            unit_of_measure="%",
            target_value=target,
            source_type=source_type,
            component_id=component_id,
        ),
        created_by=persona.id,
        sede_id=project.sede_id,
    )


# ──────────────────────────────────────────────────────────────────────
# create_project_indicator_record — SPI (G4, G5) y Axioma 3
# ──────────────────────────────────────────────────────────────────────


def test_record_spi_se_deriva_del_registro_con_precision_4_decimales(db_session):
    _, persona, sede, project, _, _ = _seed_project_with_task(db_session, "record-spi@example.com")
    ind = _create_auto_indicator(db_session, project, persona, "pro_edt_progress")

    rec = crud.create_project_indicator_record(
        db_session,
        ind.id,
        schemas.ProjectIndicatorRecordCreate(period="2026-10", target_value=3.0, actual_value=1.0),
        reported_by=persona.id,
        sede_id=sede.id,
        project_id=project.id,
    )
    assert rec.spi == 0.3333  # 4 decimales (G4), no 0.33


def test_record_spi_none_con_meta_invalida(db_session):
    _, persona, sede, project, _, _ = _seed_project_with_task(db_session, "record-target@example.com")
    ind = _create_auto_indicator(db_session, project, persona, "pro_edt_progress")

    rec = crud.create_project_indicator_record(
        db_session,
        ind.id,
        schemas.ProjectIndicatorRecordCreate(period="2026-10", target_value=0.0, actual_value=42.0),
        reported_by=persona.id,
        sede_id=sede.id,
        project_id=project.id,
    )
    assert rec.spi is None  # G5: no se fabrica SPI ficticio con meta <= 0


def test_record_actualiza_current_value_del_indicador(db_session):
    _, persona, sede, project, _, _ = _seed_project_with_task(db_session, "record-current@example.com")
    ind = _create_auto_indicator(db_session, project, persona, "pro_edt_progress")

    rec = crud.create_project_indicator_record(
        db_session,
        ind.id,
        schemas.ProjectIndicatorRecordCreate(period="2026-10", target_value=100.0, actual_value=75.0),
        reported_by=persona.id,
        sede_id=sede.id,
        project_id=project.id,
    )
    assert rec.spi == 0.75
    db_session.refresh(ind)
    assert float(ind.current_value) == 75.0


def test_record_normaliza_reported_at_naive_a_utc(db_session):
    _, persona, sede, project, _, _ = _seed_project_with_task(db_session, "record-tz@example.com")
    ind = _create_auto_indicator(db_session, project, persona, "pro_edt_progress")

    naive = datetime.datetime(2026, 10, 20, 12, 0, 0)  # sin tzinfo
    rec = crud.create_project_indicator_record(
        db_session,
        ind.id,
        schemas.ProjectIndicatorRecordCreate(
            period="2026-10", target_value=100.0, actual_value=10.0, reported_at=naive
        ),
        reported_by=persona.id,
        sede_id=sede.id,
        project_id=project.id,
    )
    stored = rec.reported_at
    if stored.tzinfo is not None:
        stored = stored.astimezone(timezone.utc)
    # El instante persistido es el mismo (naive interpretado como UTC, sin shift
    # de horas ni conversión erronea). En SQLite DateTime(timezone=True) devuelve
    # naive; en PostgreSQL conserva tzinfo UTC.
    assert stored.replace(tzinfo=None) == naive


def test_record_rechaza_indicador_de_otro_proyecto_axioma_3(db_session):
    _, persona, sede, project, _, _ = _seed_project_with_task(db_session, "record-scope@example.com")
    ind = _create_auto_indicator(db_session, project, persona, "pro_edt_progress")

    otro_project = models.Project(
        id=uuid.uuid4(),
        title="Proyecto ajeno",
        sede_id=sede.id,
        budget_allocated=1000.0,
        progress_mode="auto_tasks",
    )
    db_session.add(otro_project)
    db_session.commit()

    with pytest.raises(ValueError, match="Axioma 3"):
        crud.create_project_indicator_record(
            db_session,
            ind.id,
            schemas.ProjectIndicatorRecordCreate(period="2026-10", target_value=100.0, actual_value=10.0),
            reported_by=persona.id,
            sede_id=sede.id,
            project_id=otro_project.id,
        )


# ──────────────────────────────────────────────────────────────────────
# G3 — el sync no pisa records manuales del mismo período
# ──────────────────────────────────────────────────────────────────────


def test_sync_preserva_record_manual_del_mismo_periodo(db_session):
    _, persona, sede, project, comp, _ = _seed_project_with_task(
        db_session, "sync-manual@example.com", progress_pct=50.0, with_component=True
    )
    ind = _create_auto_indicator(db_session, project, persona, "pro_edt_progress", component_id=comp.id)

    # 1) sync con actor: genera el record automático del período
    crud.sync_project_indicators_and_kpis(
        db_session,
        project.id,
        actor_id=persona.id,
        sede_id=sede.id,
        record_period="2026-10",
    )
    # 2) el usuario reporta una medición manual en el mismo período
    manual = crud.create_project_indicator_record(
        db_session,
        ind.id,
        schemas.ProjectIndicatorRecordCreate(
            period="2026-10", target_value=100.0, actual_value=99.0, notes="Medición manual del líder"
        ),
        reported_by=persona.id,
        sede_id=sede.id,
        project_id=project.id,
    )
    # 3) re-sync: el manual debe quedar intacto y coexistir un auto
    crud.sync_project_indicators_and_kpis(
        db_session,
        project.id,
        actor_id=persona.id,
        sede_id=sede.id,
        record_period="2026-10",
    )

    records = crud.get_project_indicator_records(db_session, ind.id, sede_id=sede.id, project_id=project.id)
    del_periodo = [r for r in records if r.period == "2026-10"]
    auto_recs = [r for r in del_periodo if (r.notes or "").startswith(crud.AUTO_SYNC_NOTE_PREFIX)]
    assert len(auto_recs) >= 1
    assert len(del_periodo) >= 2  # manual + auto coexisten

    manual_after = next(r for r in records if r.id == manual.id)
    assert manual_after.actual_value == 99.0  # intocado por el motor
    assert manual_after.notes == "Medición manual del líder"


def test_sync_sin_actor_no_persiste_records_axioma_autoria(db_session):
    _, persona, sede, project, comp, _ = _seed_project_with_task(
        db_session, "sync-sin-actor@example.com", progress_pct=60.0, with_component=True
    )
    ind = _create_auto_indicator(db_session, project, persona, "pro_edt_progress", component_id=comp.id)

    result = crud.sync_project_indicators_and_kpis(
        db_session,
        project.id,
        actor_id=None,
        sede_id=sede.id,
        record_period="2026-10",
    )
    assert result["synced_indicators"] >= 1  # current_value refrescado
    records = crud.get_project_indicator_records(db_session, ind.id, sede_id=sede.id, project_id=project.id)
    assert records == []  # historial solo con actor canónico


# ──────────────────────────────────────────────────────────────────────
# G6 — indicadores huérfanos (componente eliminado)
# ──────────────────────────────────────────────────────────────────────


def test_indicador_de_componente_eliminado_queda_marcado_como_huerfano(db_session):
    _, persona, sede, project, comp, _ = _seed_project_with_task(
        db_session, "orphan@example.com", progress_pct=60.0, with_component=True
    )
    ind = _create_auto_indicator(db_session, project, persona, "pro_edt_progress", component_id=comp.id)

    # Valor fresco antes de eliminar el componente
    crud.sync_project_indicators_and_kpis(
        db_session, project.id, actor_id=persona.id, sede_id=sede.id, record_period="2026-10"
    )
    db_session.refresh(ind)
    assert float(ind.current_value) == 60.0

    # Soft-delete del componente EDT
    comp.deleted_at = datetime.datetime.now(timezone.utc)
    db_session.commit()

    listed = {i.id: i for i in crud.get_project_indicators(db_session, project.id, sede_id=sede.id)}
    assert listed[ind.id].__dict__["is_orphaned"] is True  # G6: marcado, no sustituido por el global
    assert float(listed[ind.id].current_value) == 60.0  # el valor previo no se machaca con el global


# ──────────────────────────────────────────────────────────────────────
# G2 — hook reactivo notify_project_execution_change_safe
# ──────────────────────────────────────────────────────────────────────


def test_hook_reactivo_refresca_indicador_sin_sembrar_nada(db_session):
    _, persona, sede, project, comp, task = _seed_project_with_task(
        db_session, "hook-reactivo@example.com", progress_pct=40.0, with_component=True
    )
    _create_auto_indicator(db_session, project, persona, "pro_edt_progress", component_id=comp.id)

    total_antes = len(
        crud.get_project_indicators(db_session, project.id, sede_id=sede.id)
    )

    # Mutación de ejecución → el CRUD dispara el hook reactivo sin sembrar
    task.physical_progress_pct = 80.0
    db_session.commit()
    res = crud.notify_project_execution_change_safe(
        db_session, project.id, actor_id=persona.id, sede_id=sede.id
    )

    listed = {i.id: i for i in crud.get_project_indicators(db_session, project.id, sede_id=sede.id)}
    auto_vals = [float(i.current_value) for i in listed.values() if i.current_value == 80.0]
    assert res is not None
    assert auto_vals  # algún auto tomó el nuevo avance
    total_despues = len(crud.get_project_indicators(db_session, project.id, sede_id=sede.id))
    assert total_despues == total_antes  # no siembra nuevas Familias Pro


def test_hook_reactivo_noop_en_proyecto_sin_indicadores_auto(db_session):
    _, persona, sede, project, _, task = _seed_project_with_task(
        db_session, "hook-noop@example.com", progress_pct=40.0, with_component=False
    )
    res = crud.notify_project_execution_change_safe(
        db_session, project.id, actor_id=persona.id, sede_id=sede.id
    )
    assert res is None  # sin indicadores/KPIs vinculados no hay trabajo


def test_hook_reactivo_responde_con_sede_invalida_retornando_none(db_session):
    _, persona, sede, project, _, _ = _seed_project_with_task(
        db_session, "hook-sede@example.com", progress_pct=40.0, with_component=False
    )
    # sede_id ajena al proyecto → get_project falla por Axioma 3 y el wrapper lo traga
    otra_sede_id = uuid.uuid4()
    res = crud.notify_project_execution_change_safe(
        db_session, project.id, actor_id=persona.id, sede_id=otra_sede_id
    )
    assert res is None
