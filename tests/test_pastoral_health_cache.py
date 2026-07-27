import uuid
from datetime import date, datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import update

from backend import models
from backend.core.cache import get_redis
from backend.crud.crm_.health import (
    _cache_key,
    calculate_health_score,
    calculate_pastoral_health,
    calculate_pastoral_health_score,
    recalculate_and_persist_pastoral_health,
    update_pastoral_health,
)
from tests.conftest import seed_admin


def _clear_health_cache():
    redis = get_redis()
    try:
        if hasattr(redis, "scan_iter"):
            for k in redis.scan_iter(match="health_cache:*"):
                redis.delete(k)
            return
        # MemoryRedis fallback: limpiar claves con prefijo desde el store interno
        store = getattr(redis, "_store", {})
        for k in list(store.keys()):
            if k.startswith("health_cache:"):
                redis.delete(k)
    except Exception as exc:  # pragma: no cover - safety net
        raise RuntimeError(f"Failed to clear health cache: {exc}") from exc


@pytest.fixture(autouse=True)
def clear_health_cache_before_each_test():
    """Cada test empieza con el caché de salud vacío."""
    _clear_health_cache()


def _create_persona(db_session, sede, is_baptized=False, email_suffix="test"):
    persona = models.Persona(
        id=uuid.uuid4(),
        first_name="Cache",
        last_name="Test",
        email=f"cache_{email_suffix}@example.com",
        sede_id=sede.id,
        is_baptized=is_baptized,
    )
    db_session.add(persona)
    db_session.commit()
    return persona


def test_update_pastoral_health_uses_cache_on_second_call(db_session):
    """La segunda llamada a update_pastoral_health debe usar el caché."""
    _, _, sede = seed_admin(db_session)
    persona = _create_persona(db_session, sede, is_baptized=True)

    with patch("backend.crud.crm_.health._compute_pastoral_health_score") as mock_compute:
        mock_compute.return_value = (10, "EN_RIESGO", False)
        result = update_pastoral_health(db_session, persona.id)
        assert result is not None
        assert result.health_score == 10
        assert mock_compute.call_count == 1

    with patch("backend.crud.crm_.health._compute_pastoral_health_score") as mock_compute:
        mock_compute.return_value = (10, "EN_RIESGO", False)
        result = update_pastoral_health(db_session, persona.id)
        assert result is not None
        assert result.health_score == 10
        assert mock_compute.call_count == 0


def test_cache_invalidated_on_asistencia_insert_and_soft_delete(db_session):
    """Insertar y soft-deletear una Asistencia invalida el caché."""
    _, _, sede = seed_admin(db_session)
    persona = _create_persona(db_session, sede)

    update_pastoral_health(db_session, persona.id)

    # Agregar asistencia presente -> score 50 (ESTABLE)
    asist = models.Asistencia(
        id=uuid.uuid4(),
        persona_id=persona.id,
        sesion_id=uuid.uuid4(),
        estado="presente",
    )
    db_session.add(asist)
    db_session.commit()

    with patch("backend.crud.crm_.health._compute_pastoral_health_score") as mock_compute:
        mock_compute.return_value = (50, "ESTABLE", False)
        result = update_pastoral_health(db_session, persona.id)
        assert result is not None
        assert result.health_score == 50
        assert mock_compute.call_count == 1

    # Soft-delete de la asistencia -> vuelve a 0
    asist.deleted_at = datetime.now(timezone.utc)
    db_session.commit()

    with patch("backend.crud.crm_.health._compute_pastoral_health_score") as mock_compute:
        mock_compute.return_value = (0, "EN_RIESGO", False)
        result = update_pastoral_health(db_session, persona.id)
        assert result is not None
        assert result.health_score == 0
        assert mock_compute.call_count == 1


def test_cache_invalidated_on_communication_log_insert(db_session):
    """Insertar un CommunicationLog invalida el caché."""
    _, _, sede = seed_admin(db_session)
    persona = _create_persona(db_session, sede)

    update_pastoral_health(db_session, persona.id)

    log = models.CommunicationLog(
        id=uuid.uuid4(),
        persona_id=persona.id,
        channel="WhatsApp",
        content="Hola",
        outcome="sent",
    )
    db_session.add(log)
    db_session.commit()

    with patch("backend.crud.crm_.health._compute_pastoral_health_score") as mock_compute:
        mock_compute.return_value = (5, "EN_RIESGO", False)
        result = update_pastoral_health(db_session, persona.id)
        assert result is not None
        assert result.health_score == 5
        assert mock_compute.call_count == 1


def test_cache_invalidated_on_spiritual_milestone_insert(db_session):
    """Insertar un SpiritualMilestone invalida el caché."""
    _, _, sede = seed_admin(db_session)
    persona = _create_persona(db_session, sede, is_baptized=False)

    update_pastoral_health(db_session, persona.id)

    milestone = models.SpiritualMilestone(
        id=uuid.uuid4(),
        persona_id=persona.id,
        sede_id=sede.id,
        type="Bautismo",
        event_date=date.today(),
    )
    db_session.add(milestone)
    db_session.commit()

    with patch("backend.crud.crm_.health._compute_pastoral_health_score") as mock_compute:
        mock_compute.return_value = (10, "EN_RIESGO", True)
        result = update_pastoral_health(db_session, persona.id)
        assert result is not None
        assert result.health_score == 10
        assert mock_compute.call_count == 1


def test_cache_invalidated_on_persona_baptized_change(db_session):
    """Cambiar Persona.is_baptized invalida el caché."""
    _, _, sede = seed_admin(db_session)
    persona = _create_persona(db_session, sede, is_baptized=False)

    update_pastoral_health(db_session, persona.id)

    persona.is_baptized = True
    db_session.commit()

    with patch("backend.crud.crm_.health._compute_pastoral_health_score") as mock_compute:
        mock_compute.return_value = (10, "EN_RIESGO", False)
        result = update_pastoral_health(db_session, persona.id)
        assert result is not None
        assert result.health_score == 10
        assert mock_compute.call_count == 1


def test_cache_invalidated_on_interaccion_crm_insert(db_session):
    """Insertar una InteraccionCRM invalida el caché."""
    _, admin_persona, sede = seed_admin(db_session)
    persona = _create_persona(db_session, sede)

    pipeline = models.PipelineCRM(
        id=uuid.uuid4(), sede_id=sede.id, nombre="P", tipo="NUEVOS_VISITANTES"
    )
    etapa = models.EtapaPipeline(id=uuid.uuid4(), pipeline_id=pipeline.id, nombre="E", orden=1)
    db_session.add_all([pipeline, etapa])
    db_session.commit()

    caso = models.CasoCRM(
        id=uuid.uuid4(),
        persona_id=persona.id,
        sede_id=sede.id,
        pipeline_id=pipeline.id,
        etapa_actual_id=etapa.id,
        titulo_caso="Caso",
        origen_canal="WEB_FORM",
    )
    db_session.add(caso)
    db_session.commit()

    update_pastoral_health(db_session, persona.id)

    interaccion = models.InteraccionCRM(
        id=uuid.uuid4(),
        caso_id=caso.id,
        realizado_por_id=admin_persona.id,
        tipo="LLAMADA_OUTBOUND",
        resumen="Llamada",
    )
    db_session.add(interaccion)
    db_session.commit()

    with patch("backend.crud.crm_.health._compute_pastoral_health_score") as mock_compute:
        mock_compute.return_value = (5, "EN_RIESGO", False)
        result = update_pastoral_health(db_session, persona.id)
        assert result is not None
        assert result.health_score == 5
        assert mock_compute.call_count == 1


def test_cache_invalidated_on_course_attendance_insert(db_session):
    """Insertar un CourseAttendance invalida el caché."""
    _, _, sede = seed_admin(db_session)
    persona = _create_persona(db_session, sede)

    enrollment = models.Enrollment(
        id=uuid.uuid4(),
        persona_id=persona.id,
        course_id=uuid.uuid4(),
        status="active",
    )
    db_session.add(enrollment)
    db_session.commit()

    update_pastoral_health(db_session, persona.id)

    attendance = models.CourseAttendance(
        id=uuid.uuid4(),
        enrollment_id=enrollment.id,
        session_date=datetime.now(timezone.utc),
        status="present",
    )
    db_session.add(attendance)
    db_session.commit()

    with patch("backend.crud.crm_.health._compute_pastoral_health_score") as mock_compute:
        mock_compute.return_value = (50, "ESTABLE", False)
        result = update_pastoral_health(db_session, persona.id)
        assert result is not None
        assert result.health_score == 50
        assert mock_compute.call_count == 1


def test_update_pastoral_health_returns_db_values_on_cache_hit(db_session):
    """En cache hit se devuelve la persona con los valores frescos de DB."""
    _, _, sede = seed_admin(db_session)
    persona = _create_persona(db_session, sede, is_baptized=True)

    update_pastoral_health(db_session, persona.id)

    # Simular que otra operación actualiz la DB por fuera del caché.
    db_session.execute(
        update(models.Persona)
        .where(models.Persona.id == persona.id)
        .values(health_score=99, health_status="COMPROMETIDO")
    )
    db_session.commit()

    result = update_pastoral_health(db_session, persona.id)
    assert result.health_score == 99
    assert result.health_status == "COMPROMETIDO"


def test_recalculate_and_persist_direct_does_not_use_or_set_cache(db_session):
    """recalculate_and_persist_pastoral_health directo recalcula siempre y no toca caché."""
    _, _, sede = seed_admin(db_session)
    persona = _create_persona(db_session, sede, is_baptized=True)

    with patch("backend.crud.crm_.health._compute_pastoral_health_score") as mock_compute:
        mock_compute.return_value = (10, "EN_RIESGO", False)
        score, status = recalculate_and_persist_pastoral_health(db_session, persona.id)
        assert score == 10
        assert status == "EN_RIESGO"
        assert mock_compute.call_count == 1

    cached = get_redis().get(_cache_key(persona.id))
    assert cached is None


def test_update_pastoral_health_cache_hit_does_not_commit(db_session):
    """update_pastoral_health no debe hacer commit cuando usa el caché."""
    _, _, sede = seed_admin(db_session)
    persona = _create_persona(db_session, sede, is_baptized=True)

    # Establecer el caché
    update_pastoral_health(db_session, persona.id)

    # Agregar una asistencia pendiente sin commitear
    pending_asist = models.Asistencia(
        id=uuid.uuid4(),
        persona_id=persona.id,
        sesion_id=uuid.uuid4(),
        estado="presente",
    )
    db_session.add(pending_asist)

    # Llamar a update_pastoral_health en cache hit no debe commitear
    update_pastoral_health(db_session, persona.id)

    # Hacer rollback de la asistencia pendiente
    db_session.rollback()

    # Si se hubiera hecho commit, la asistencia existiría en DB
    asist_count = (
        db_session.query(models.Asistencia)
        .filter(models.Asistencia.id == pending_asist.id)
        .count()
    )
    assert asist_count == 0


@pytest.mark.parametrize(
    "deprecated_fn",
    [
        calculate_pastoral_health,
        calculate_pastoral_health_score,
        calculate_health_score,
    ],
)
def test_deprecated_wrapper_emits_deprecation_warning(db_session, deprecated_fn):
    """Cada wrapper deprecado debe emitir DeprecationWarning al usarse."""
    _, _, sede = seed_admin(db_session)
    persona = _create_persona(db_session, sede, is_baptized=True)
    with pytest.warns(DeprecationWarning, match="recalculate_and_persist_pastoral_health"):
        deprecated_fn(db_session, persona.id)
