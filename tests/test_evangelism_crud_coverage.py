"""
Tests for crud/evangelism.py — covers missing CRUD operations.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from backend import crud
from backend.models_evangelism import (
    Asistencia,
    CategoriaEstrategia,
    EstrategiaEvangelismo,
    GrupoEvangelismo,
    SesionGrupo,
)
from backend.schemas.evangelism import RegistroSeguimientoCreate, RegistroSeguimientoUpdate
from tests.conftest import seed_admin as _seed_admin


def _make_strategy(db, sede_id):
    cat = CategoriaEstrategia(id=uuid.uuid4(), nombre="Cat CRUD")
    db.add(cat)
    db.flush()
    s = EstrategiaEvangelismo(
        id=uuid.uuid4(),
        nombre="Estrategia CRUD",
        sede_id=sede_id,
        categoria_id=cat.id,
        fecha_inicio=datetime.now(timezone.utc),
        fecha_fin=datetime.now(timezone.utc) + timedelta(days=90),
    )
    db.add(s)
    db.flush()
    return s


@pytest.fixture
def full(client, db_session):
    admin, persona, sede = _seed_admin(db_session)
    return {"db": db_session, "admin": admin, "persona": persona, "sede": sede}


class TestExcusasCRUD:
    def test_create_motivo_excusa(self, full):
        excusa = crud.evangelism.create_motivo_excusa(
            full["db"], descripcion="Enfermedad", actor_user_id=full["admin"].id
        )
        full["db"].commit()
        assert excusa.id is not None

    def test_get_motivos_excusa(self, full):
        crud.evangelism.create_motivo_excusa(full["db"], descripcion="Test", actor_user_id=full["admin"].id)
        full["db"].commit()
        result = crud.evangelism.get_motivos_excusa(full["db"])
        assert len(result) >= 1

    def test_update_motivo_excusa(self, full):
        excusa = crud.evangelism.create_motivo_excusa(
            full["db"], descripcion="Original", actor_user_id=full["admin"].id
        )
        full["db"].commit()
        updated = crud.evangelism.update_motivo_excusa(
            full["db"], excusa.id, descripcion="Actualizado", actor_user_id=full["admin"].id
        )
        full["db"].commit()
        assert updated is not None

    def test_delete_motivo_excusa(self, full):
        excusa = crud.evangelism.create_motivo_excusa(full["db"], descripcion="Borrar", actor_user_id=full["admin"].id)
        full["db"].commit()
        result = crud.evangelism.delete_motivo_excusa(full["db"], excusa.id, actor_user_id=full["admin"].id)
        full["db"].commit()
        assert result is True

    def test_delete_motivo_excusa_not_found(self, full):
        result = crud.evangelism.delete_motivo_excusa(full["db"], uuid.uuid4(), actor_user_id=full["admin"].id)
        assert result is False

    def test_seed_motivos_excusa(self, full):
        result = crud.evangelism.seed_motivos_excusa(full["db"], actor_user_id=full["admin"].id)
        full["db"].commit()
        assert result is not None


class TestSeguimientoCRUD:
    def _make_asistencia_with_session(self, full):
        strategy = _make_strategy(full["db"], full["sede"].id)
        g = GrupoEvangelismo(
            id=uuid.uuid4(),
            nombre=f"G_{uuid.uuid4().hex[:6]}",
            estrategia_id=strategy.id,
            sede_id=full["sede"].id,
            activo=True,
            capacidad=20,
        )
        full["db"].add(g)
        full["db"].flush()
        s = SesionGrupo(
            id=uuid.uuid4(),
            grupo_id=g.id,
            fecha_sesion=datetime.now(timezone.utc).date(),
            estado="REALIZADA",
            estado_habilitacion="HABILITADO",
        )
        full["db"].add(s)
        full["db"].flush()
        a = Asistencia(
            id=uuid.uuid4(),
            sesion_id=s.id,
            persona_id=full["persona"].id,
            estado="ASISTIO",
        )
        full["db"].add(a)
        full["db"].flush()
        return a

    def test_create_seguimiento(self, full):
        asistencia = self._make_asistencia_with_session(full)
        full["db"].commit()
        data = RegistroSeguimientoCreate(
            tipo="LLAMADA",
            observaciones="Llamada de seguimiento",
            asistencia_id=asistencia.id,
        )
        seg = crud.evangelism.create_seguimiento(full["db"], data=data, actor_user_id=full["admin"].id)
        full["db"].commit()
        assert seg.id is not None

    def test_get_seguimientos(self, full):
        asistencia = self._make_asistencia_with_session(full)
        full["db"].commit()
        data = RegistroSeguimientoCreate(
            tipo="MENSAJE_WHATSAPP",
            observaciones="Mensaje",
            asistencia_id=asistencia.id,
        )
        crud.evangelism.create_seguimiento(full["db"], data=data, actor_user_id=full["admin"].id)
        full["db"].commit()
        result = crud.evangelism.get_seguimientos(full["db"], asistencia.id)
        assert len(result) >= 1

    def test_update_seguimiento(self, full):
        asistencia = self._make_asistencia_with_session(full)
        full["db"].commit()
        data = RegistroSeguimientoCreate(
            tipo="LLAMADA",
            observaciones="Original",
            asistencia_id=asistencia.id,
        )
        seg = crud.evangelism.create_seguimiento(full["db"], data=data, actor_user_id=full["admin"].id)
        full["db"].commit()
        update_data = RegistroSeguimientoUpdate(observaciones="Actualizado")
        updated = crud.evangelism.update_seguimiento(full["db"], seg.id, update_data, actor_user_id=full["admin"].id)
        full["db"].commit()
        assert updated is not None

    def test_delete_seguimiento(self, full):
        asistencia = self._make_asistencia_with_session(full)
        full["db"].commit()
        data = RegistroSeguimientoCreate(
            tipo="ORACION",
            observaciones="Borrar",
            asistencia_id=asistencia.id,
        )
        seg = crud.evangelism.create_seguimiento(full["db"], data=data, actor_user_id=full["admin"].id)
        full["db"].commit()
        result = crud.evangelism.delete_seguimiento(full["db"], seg.id, actor_user_id=full["admin"].id)
        full["db"].commit()
        assert result is True

    def test_get_pendientes_seguimiento(self, full):
        self._make_asistencia_with_session(full)
        full["db"].commit()
        result = crud.evangelism.get_pendientes_seguimiento(full["db"], sede_id=str(full["sede"].id))
        assert isinstance(result, list)


class TestEstrategiaCRUDExtended:
    def test_get_estrategias(self, full):
        _make_strategy(full["db"], full["sede"].id)
        full["db"].commit()
        result = crud.evangelism.get_estrategias(full["db"], sede_id=str(full["sede"].id))
        assert len(result) >= 1

    def test_get_estrategia(self, full):
        s = _make_strategy(full["db"], full["sede"].id)
        full["db"].commit()
        result = crud.evangelism.get_estrategia(full["db"], s.id)
        assert result is not None

    def test_get_estrategia_not_found(self, full):
        result = crud.evangelism.get_estrategia(full["db"], uuid.uuid4())
        assert result is None

    def test_delete_estrategia(self, full):
        s = _make_strategy(full["db"], full["sede"].id)
        full["db"].commit()
        result = crud.evangelism.delete_estrategia(full["db"], s.id, actor_user_id=full["admin"].id)
        full["db"].commit()
        assert result is True
