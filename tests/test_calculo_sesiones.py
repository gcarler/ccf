from datetime import datetime, timezone
import uuid

from backend import models
from backend.services.calculo_sesiones import calcular_sesiones


def _seed_sede(db_session, nombre="Sede Sesiones"):
    sede = models.Sede(id=uuid.uuid4(), nombre=nombre, ciudad="Bogota", es_activa=True)
    db_session.add(sede)
    db_session.commit()
    db_session.refresh(sede)
    return sede


def _seed_categoria(db_session):
    categoria = models.CategoriaEstrategia(nombre=f"Categoria {uuid.uuid4().hex[:8]}")
    db_session.add(categoria)
    db_session.commit()
    db_session.refresh(categoria)
    return categoria


def _seed_estrategia(db_session, sede, categoria, nombre="Estrategia Sesiones"):
    estrategia = models.EstrategiaEvangelismo(
        id=str(uuid.uuid4()),
        nombre=nombre,
        categoria_id=categoria.id,
        sede_id=sede.id,
        frecuencia="SEMANAL",
        activa=True,
    )
    db_session.add(estrategia)
    db_session.commit()
    db_session.refresh(estrategia)
    return estrategia


def _seed_grupo(db_session, estrategia, sede, nombre="Grupo Sesiones"):
    grupo = models.GrupoEvangelismo(
        estrategia_id=estrategia.id,
        sede_id=sede.id,
        nombre=nombre,
        activo=True,
    )
    db_session.add(grupo)
    db_session.commit()
    db_session.refresh(grupo)
    return grupo


def _session_dates(db_session, grupo_id):
    rows = (
        db_session.query(models.SesionGrupo)
        .filter(models.SesionGrupo.grupo_id == grupo_id)
        .order_by(models.SesionGrupo.fecha_sesion.asc())
        .all()
    )
    return [row.fecha_sesion.date().isoformat() for row in rows]


def test_calcular_sesiones_normaliza_frecuencia_e_idempotente(db_session):
    sede = _seed_sede(db_session)
    categoria = _seed_categoria(db_session)
    estrategia = _seed_estrategia(db_session, sede, categoria)
    grupo = _seed_grupo(db_session, estrategia, sede)

    created = calcular_sesiones(
        db=db_session,
        estrategia_id=estrategia.id,
        sede_id=sede.id,
        fecha_inicio=datetime(2026, 6, 1, 19, 0, tzinfo=timezone.utc),
        fecha_fin=datetime(2026, 6, 22, 19, 0, tzinfo=timezone.utc),
        frecuencia="semanal",
        grupos_ids=[grupo.id],
    )
    assert created == 4

    created_again = calcular_sesiones(
        db=db_session,
        estrategia_id=estrategia.id,
        sede_id=sede.id,
        fecha_inicio=datetime(2026, 6, 1, 19, 0, tzinfo=timezone.utc),
        fecha_fin=datetime(2026, 6, 22, 19, 0, tzinfo=timezone.utc),
        frecuencia="SEMANAL",
        grupos_ids=[grupo.id],
    )
    assert created_again == 0
    assert _session_dates(db_session, grupo.id) == ["2026-06-01", "2026-06-08", "2026-06-15", "2026-06-22"]


def test_calcular_sesiones_mensual_preserva_dia_original(db_session):
    sede = _seed_sede(db_session)
    categoria = _seed_categoria(db_session)
    estrategia = _seed_estrategia(db_session, sede, categoria)
    grupo = _seed_grupo(db_session, estrategia, sede)

    created = calcular_sesiones(
        db=db_session,
        estrategia_id=estrategia.id,
        sede_id=sede.id,
        fecha_inicio=datetime(2026, 1, 31, 10, 0, tzinfo=timezone.utc),
        fecha_fin=datetime(2026, 4, 30, 10, 0, tzinfo=timezone.utc),
        frecuencia="MENSUAL",
        grupos_ids=[grupo.id],
    )
    assert created == 4
    assert _session_dates(db_session, grupo.id) == ["2026-01-31", "2026-02-28", "2026-03-31", "2026-04-30"]


def test_calcular_sesiones_evento_unico_crea_solo_fecha_inicio(db_session):
    sede = _seed_sede(db_session)
    categoria = _seed_categoria(db_session)
    estrategia = _seed_estrategia(db_session, sede, categoria)
    grupo = _seed_grupo(db_session, estrategia, sede)

    created = calcular_sesiones(
        db=db_session,
        estrategia_id=estrategia.id,
        sede_id=sede.id,
        fecha_inicio=datetime(2026, 7, 5, 18, 0, tzinfo=timezone.utc),
        fecha_fin=datetime(2026, 8, 5, 18, 0, tzinfo=timezone.utc),
        frecuencia="evento único",
        grupos_ids=[grupo.id],
    )
    assert created == 1
    assert _session_dates(db_session, grupo.id) == ["2026-07-05"]


def test_calcular_sesiones_ignora_grupos_fuera_de_estrategia_o_sede(db_session):
    sede = _seed_sede(db_session)
    otra_sede = _seed_sede(db_session, nombre="Otra Sede")
    categoria = _seed_categoria(db_session)
    estrategia = _seed_estrategia(db_session, sede, categoria)
    otra_estrategia = _seed_estrategia(db_session, sede, categoria, nombre="Otra Estrategia")
    grupo_valido = _seed_grupo(db_session, estrategia, sede, nombre="Grupo Valido")
    grupo_otra_estrategia = _seed_grupo(db_session, otra_estrategia, sede, nombre="Grupo Otra Estrategia")
    grupo_otra_sede = _seed_grupo(db_session, estrategia, otra_sede, nombre="Grupo Otra Sede")

    created = calcular_sesiones(
        db=db_session,
        estrategia_id=estrategia.id,
        sede_id=sede.id,
        fecha_inicio=datetime(2026, 6, 1, 19, 0, tzinfo=timezone.utc),
        fecha_fin=datetime(2026, 6, 8, 19, 0, tzinfo=timezone.utc),
        frecuencia="Semanal",
        grupos_ids=[grupo_valido.id, grupo_otra_estrategia.id, grupo_otra_sede.id],
    )
    assert created == 2
    assert _session_dates(db_session, grupo_valido.id) == ["2026-06-01", "2026-06-08"]
    assert _session_dates(db_session, grupo_otra_estrategia.id) == []
    assert _session_dates(db_session, grupo_otra_sede.id) == []
