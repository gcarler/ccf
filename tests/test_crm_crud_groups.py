"""Coverage tests for backend/crud/crm_/groups.py — target 90%+."""
from __future__ import annotations

import uuid as _uuid

from sqlalchemy.orm import Session

from backend import models, schemas
from backend.crud.crm_ import groups as crud_groups
from backend.crud._utils import _utcnow
from backend.schemas.evangelism import GrupoEvangelismoCreate, GrupoEvangelismoUpdate, ParticipanteGrupoConRol


def _seed_sede(db: Session, name: str = "Sede Test") -> models.Sede:
    s = models.Sede(id=_uuid.uuid4(), nombre=name, ciudad="Bogota", es_activa=True)
    db.add(s)
    db.flush()
    return s


def _seed_persona(db: Session, sede_id, first="Persona") -> models.Persona:
    p = models.Persona(id=_uuid.uuid4(), first_name=first, last_name="Test", sede_id=sede_id)
    db.add(p)
    db.flush()
    return p


def _seed_categoria(db):
    from backend.models_evangelism import CategoriaEstrategia
    c = CategoriaEstrategia(id=_uuid.uuid4(), nombre="Cat")
    db.add(c)
    db.flush()
    return c


def _seed_strategy(db, sede_id):
    from backend.models_evangelism import EstrategiaEvangelismo
    s = EstrategiaEvangelismo(
        id=_uuid.uuid4(), nombre="Estrategia",
        sede_id=sede_id, categoria_id=_seed_categoria(db).id,
    )
    db.add(s)
    db.flush()
    return s


def _seed_grupo(db, sede_id, estrategia_id=None, deleted_at=None, nombre="Grupo Test"):
    g = models.GrupoEvangelismo(
        id=_uuid.uuid4(), nombre=nombre,
        sede_id=sede_id, deleted_at=deleted_at,
        estrategia_id=estrategia_id,
    )
    db.add(g)
    db.flush()
    return g


def _seed_custom_role(db, estrategia_id):
    from backend.models_evangelism import RolPersonalizadoEstrategia
    r = RolPersonalizadoEstrategia(
        id=_uuid.uuid4(), nombre_rol="Líder",
        estrategia_id=estrategia_id,
    )
    db.add(r)
    db.flush()
    return r


def _commit(db):
    db.commit()


class TestGroupParticipantRoleValues:

    def test_plain_role(self):
        item = type("Item", (), {"role": "miembro", "rol_personalizado_id": None})()
        role, custom_id = crud_groups._group_participant_role_values(item)
        assert role == "miembro"
        assert custom_id is None

    def test_custom_role_from_prefix(self):
        rid = _uuid.uuid4()
        item = type("Item", (), {"role": f"custom:{rid}", "rol_personalizado_id": None})()
        role, custom_id = crud_groups._group_participant_role_values(item)
        assert role == "personalizado"
        assert str(custom_id) == str(rid)

    def test_custom_role_explicit_preferred(self):
        rid = _uuid.uuid4()
        other = _uuid.uuid4()
        item = type("Item", (), {"role": f"custom:{rid}", "rol_personalizado_id": other})()
        role, custom_id = crud_groups._group_participant_role_values(item)
        assert role == "personalizado"
        assert str(custom_id) == str(other)

    def test_custom_role_explicit_str_uuid(self):
        rid = _uuid.uuid4()
        other = _uuid.uuid4()
        item = type("Item", (), {"role": f"custom:{rid}", "rol_personalizado_id": str(other)})()
        role, custom_id = crud_groups._group_participant_role_values(item)
        assert role == "personalizado"
        assert str(custom_id) == str(other)

    def test_custom_role_explicit_invalid(self):
        rid = _uuid.uuid4()
        item = type("Item", (), {"role": f"custom:{rid}", "rol_personalizado_id": "not-a-uuid"})()
        role, custom_id = crud_groups._group_participant_role_values(item)
        assert role == "personalizado"
        assert str(custom_id) == str(rid)

    def test_personalizado_old_explicit(self):
        rid = _uuid.uuid4()
        item = type("Item", (), {"role": "personalizado", "rol_personalizado_id": rid})()
        role, custom_id = crud_groups._group_participant_role_values(item)
        assert role == "personalizado"
        assert str(custom_id) == str(rid)

    def test_personalizado_old_str_uuid(self):
        rid = _uuid.uuid4()
        item = type("Item", (), {"role": "personalizado", "rol_personalizado_id": str(rid)})()
        role, custom_id = crud_groups._group_participant_role_values(item)
        assert role == "personalizado"
        assert str(custom_id) == str(rid)

    def test_personalizado_old_invalid(self):
        item = type("Item", (), {"role": "personalizado", "rol_personalizado_id": "invalid"})()
        role, custom_id = crud_groups._group_participant_role_values(item)
        assert role == "personalizado"
        assert custom_id is None

    def test_role_none_defaults(self):
        item = type("Item", (), {"role": None, "rol_personalizado_id": None})()
        role, custom_id = crud_groups._group_participant_role_values(item)
        assert role == "participante"
        assert custom_id is None

    def test_custom_prefix_invalid_uuid(self):
        item = type("Item", (), {"role": "custom:not-a-uuid", "rol_personalizado_id": None})()
        role, custom_id = crud_groups._group_participant_role_values(item)
        assert role == "personalizado"
        assert custom_id is None


class TestCrudGrupos:

    def test_get_grupos_empty(self, db_session):
        result = crud_groups.get_grupos(db_session)
        assert result == []

    def test_get_grupos_excludes_soft_deleted(self, db_session):
        sede = _seed_sede(db_session)
        _seed_grupo(db_session, sede.id, deleted_at=_utcnow())
        _commit(db_session)
        result = crud_groups.get_grupos(db_session)
        assert len(result) == 0

    def test_get_grupos_filter_sede(self, db_session):
        s1 = _seed_sede(db_session, "S1")
        s2 = _seed_sede(db_session, "S2")
        _seed_grupo(db_session, s1.id, nombre="G1")
        _seed_grupo(db_session, s2.id, nombre="G2")
        _commit(db_session)
        result = crud_groups.get_grupos(db_session, sede_id=s2.id)
        assert len(result) == 1
        assert result[0].nombre == "G2"

    def test_get_grupos_pagination(self, db_session):
        sede = _seed_sede(db_session)
        for i in range(5):
            _seed_grupo(db_session, sede.id, nombre=f"G{i}")
        _commit(db_session)
        result = crud_groups.get_grupos(db_session, skip=1, limit=2)
        assert len(result) == 2

    def test_get_grupo_found(self, db_session):
        sede = _seed_sede(db_session)
        g = _seed_grupo(db_session, sede.id)
        _commit(db_session)
        result = crud_groups.get_grupo(db_session, g.id)
        assert result is not None
        assert result.id == g.id

    def test_get_grupo_not_found(self, db_session):
        result = crud_groups.get_grupo(db_session, _uuid.uuid4())
        assert result is None

    def test_get_grupo_excludes_soft_deleted(self, db_session):
        sede = _seed_sede(db_session)
        g = _seed_grupo(db_session, sede.id, deleted_at=_utcnow())
        _commit(db_session)
        assert crud_groups.get_grupo(db_session, g.id) is None

    def test_create_grupo_minimal(self, db_session):
        sede = _seed_sede(db_session)
        payload = GrupoEvangelismoCreate(name="Mi Grupo")
        g = crud_groups.create_grupo(db_session, payload, sede_id=sede.id)
        assert g.nombre == "Mi Grupo"
        assert g.sede_id == sede.id
        assert g.codigo is not None

    def test_create_grupo_with_estrategia_id(self, db_session):
        sede = _seed_sede(db_session)
        s = _seed_strategy(db_session, sede.id)
        payload = GrupoEvangelismoCreate(
            name="Grupo Estrat",
            evangelism_strategy_id=s.id,
        )
        g = crud_groups.create_grupo(db_session, payload, sede_id=sede.id)
        assert g.estrategia_id == s.id

    def test_create_grupo_with_code(self, db_session):
        sede = _seed_sede(db_session)
        payload = GrupoEvangelismoCreate(name="Codigo Test", code="MI-CODE-001")
        g = crud_groups.create_grupo(db_session, payload, sede_id=sede.id)
        assert g.codigo == "MI-CODE-001"

    def test_create_grupo_fallback_name(self, db_session):
        sede = _seed_sede(db_session)
        payload = GrupoEvangelismoCreate(name="", address="Cra 10 #20-30")
        g = crud_groups.create_grupo(db_session, payload, sede_id=sede.id)
        assert "Cra" in g.nombre

    def test_create_grupo_with_base_attendee_ids(self, db_session):
        sede = _seed_sede(db_session)
        p = _seed_persona(db_session, sede.id)
        payload = GrupoEvangelismoCreate(
            name="Grupo Attendees",
            base_attendee_ids=[p.id],
        )
        g = crud_groups.create_grupo(db_session, payload, sede_id=sede.id)
        assert g.nombre == "Grupo Attendees"
        pgs = db_session.query(models.ParticipanteGrupo).filter(
            models.ParticipanteGrupo.grupo_id == g.id
        ).all()
        assert len(pgs) >= 1

    def test_create_grupo_with_base_attendees_with_roles(self, db_session):
        sede = _seed_sede(db_session)
        p = _seed_persona(db_session, sede.id)
        payload = GrupoEvangelismoCreate(
            name="Grupo Roles",
            base_attendees_with_roles=[
                ParticipanteGrupoConRol(persona_id=p.id, role="miembro"),
            ],
        )
        g = crud_groups.create_grupo(db_session, payload, sede_id=sede.id)
        pgs = db_session.query(models.ParticipanteGrupo).filter(
            models.ParticipanteGrupo.grupo_id == g.id
        ).all()
        assert len(pgs) >= 1

    def test_create_grupo_with_custom_role(self, db_session):
        sede = _seed_sede(db_session)
        s = _seed_strategy(db_session, sede.id)
        cr = _seed_custom_role(db_session, s.id)
        p = _seed_persona(db_session, sede.id)
        payload = GrupoEvangelismoCreate(
            name="Grupo Custom",
            evangelism_strategy_id=s.id,
            base_attendees_with_roles=[
                ParticipanteGrupoConRol(
                    persona_id=p.id, role=f"custom:{cr.id}",
                    rol_personalizado_id=cr.id,
                ),
            ],
        )
        g = crud_groups.create_grupo(db_session, payload, sede_id=sede.id)
        pgs = db_session.query(models.ParticipanteGrupo).filter(
            models.ParticipanteGrupo.grupo_id == g.id
        ).all()
        assert len(pgs) >= 1
        assert pgs[0].rol_personalizado_id == cr.id

    def test_delete_grupo_happy(self, db_session):
        sede = _seed_sede(db_session)
        g = _seed_grupo(db_session, sede.id)
        _commit(db_session)
        assert crud_groups.delete_grupo(db_session, g.id) is True
        db_session.expire_all()
        assert crud_groups.get_grupo(db_session, g.id) is None

    def test_delete_grupo_not_found(self, db_session):
        assert crud_groups.delete_grupo(db_session, _uuid.uuid4()) is False

    def test_update_grupo_not_found(self, db_session):
        payload = GrupoEvangelismoUpdate(name="Nope")
        result = crud_groups.update_grupo(db_session, _uuid.uuid4(), payload)
        assert result is None

    def test_update_grupo_basic(self, db_session):
        sede = _seed_sede(db_session)
        g = _seed_grupo(db_session, sede.id, nombre="Viejo")
        _commit(db_session)
        payload = GrupoEvangelismoUpdate(name="Nuevo")
        result = crud_groups.update_grupo(db_session, g.id, payload)
        assert result.nombre == "Nuevo"

    def test_update_grupo_code_empty_fallback(self, db_session):
        sede = _seed_sede(db_session)
        g = _seed_grupo(db_session, sede.id, nombre="CodeTest")
        _commit(db_session)
        payload = GrupoEvangelismoUpdate(code="")
        result = crud_groups.update_grupo(db_session, g.id, payload)
        assert result.codigo is not None

    def test_update_grupo_soft_deleted_returns_none(self, db_session):
        sede = _seed_sede(db_session)
        g = _seed_grupo(db_session, sede.id, deleted_at=_utcnow())
        _commit(db_session)
        payload = GrupoEvangelismoUpdate(name="Ghost")
        result = crud_groups.update_grupo(db_session, g.id, payload)
        assert result is None


class TestUpdateGrupoAttendees:

    def test_update_with_base_attendees_with_roles_miembro(self, db_session):
        sede = _seed_sede(db_session)
        g = _seed_grupo(db_session, sede.id)
        p = _seed_persona(db_session, sede.id)
        _commit(db_session)
        payload = GrupoEvangelismoUpdate(
            base_attendees_with_roles=[
                ParticipanteGrupoConRol(persona_id=p.id, role="miembro"),
            ],
        )
        result = crud_groups.update_grupo(db_session, g.id, payload)
        pgs = db_session.query(models.ParticipanteGrupo).filter(
            models.ParticipanteGrupo.grupo_id == g.id,
            models.ParticipanteGrupo.deleted_at.is_(None),
        ).all()
        assert len(pgs) >= 1

    def test_update_with_base_attendees_reassign(self, db_session):
        sede = _seed_sede(db_session)
        g = _seed_grupo(db_session, sede.id)
        p = _seed_persona(db_session, sede.id)
        _commit(db_session)
        payload1 = GrupoEvangelismoUpdate(
            base_attendees_with_roles=[
                ParticipanteGrupoConRol(persona_id=p.id, role="miembro"),
            ],
        )
        crud_groups.update_grupo(db_session, g.id, payload1)
        payload2 = GrupoEvangelismoUpdate(
            base_attendees_with_roles=[
                ParticipanteGrupoConRol(persona_id=p.id, role="asistente"),
            ],
        )
        result = crud_groups.update_grupo(db_session, g.id, payload2)
        pgs = db_session.query(models.ParticipanteGrupo).filter(
            models.ParticipanteGrupo.grupo_id == g.id,
            models.ParticipanteGrupo.deleted_at.is_(None),
        ).all()
        assert len(pgs) == 1
        assert pgs[0].role == "asistente"

    def test_update_with_base_attendees_leader_detection(self, db_session):
        sede = _seed_sede(db_session)
        s = _seed_strategy(db_session, sede.id)
        cr = _seed_custom_role(db_session, s.id)
        g = _seed_grupo(db_session, sede.id, estrategia_id=s.id)
        p = _seed_persona(db_session, sede.id)
        _commit(db_session)
        payload = GrupoEvangelismoUpdate(
            base_attendees_with_roles=[
                ParticipanteGrupoConRol(
                    persona_id=p.id, role=f"custom:{cr.id}",
                    rol_personalizado_id=cr.id,
                ),
            ],
        )
        result = crud_groups.update_grupo(db_session, g.id, payload)
        assert result.lider_persona_id == p.id

    def test_update_with_base_attendee_ids(self, db_session):
        sede = _seed_sede(db_session)
        g = _seed_grupo(db_session, sede.id)
        p = _seed_persona(db_session, sede.id)
        _commit(db_session)
        payload = GrupoEvangelismoUpdate(
            base_attendee_ids=[p.id],
        )
        result = crud_groups.update_grupo(db_session, g.id, payload)
        pgs = db_session.query(models.ParticipanteGrupo).filter(
            models.ParticipanteGrupo.grupo_id == g.id,
            models.ParticipanteGrupo.deleted_at.is_(None),
        ).all()
        assert len(pgs) == 1
        assert pgs[0].role == "miembro"

    def test_update_with_base_attendee_ids_reassign(self, db_session):
        sede = _seed_sede(db_session)
        g = _seed_grupo(db_session, sede.id)
        p = _seed_persona(db_session, sede.id)
        _commit(db_session)
        payload1 = GrupoEvangelismoUpdate(base_attendee_ids=[p.id])
        crud_groups.update_grupo(db_session, g.id, payload1)
        payload2 = GrupoEvangelismoUpdate(base_attendee_ids=[p.id])
        result = crud_groups.update_grupo(db_session, g.id, payload2)
        pgs = db_session.query(models.ParticipanteGrupo).filter(
            models.ParticipanteGrupo.grupo_id == g.id,
            models.ParticipanteGrupo.deleted_at.is_(None),
        ).all()
        assert len(pgs) == 1

    def test_update_with_personalizado_rehidratacion(self, db_session):
        sede = _seed_sede(db_session)
        s = _seed_strategy(db_session, sede.id)
        cr = _seed_custom_role(db_session, s.id)
        g = _seed_grupo(db_session, sede.id, estrategia_id=s.id)
        p = _seed_persona(db_session, sede.id)
        _commit(db_session)
        payload1 = GrupoEvangelismoUpdate(
            base_attendees_with_roles=[
                ParticipanteGrupoConRol(
                    persona_id=p.id, role=f"custom:{cr.id}",
                    rol_personalizado_id=cr.id,
                ),
            ],
        )
        crud_groups.update_grupo(db_session, g.id, payload1)
        payload2 = GrupoEvangelismoUpdate(
            base_attendees_with_roles=[
                ParticipanteGrupoConRol(
                    persona_id=p.id, role="personalizado",
                    rol_personalizado_id=None,
                ),
            ],
        )
        result = crud_groups.update_grupo(db_session, g.id, payload2)
        pgs = db_session.query(models.ParticipanteGrupo).filter(
            models.ParticipanteGrupo.grupo_id == g.id,
            models.ParticipanteGrupo.deleted_at.is_(None),
        ).all()
        assert len(pgs) == 1
        assert pgs[0].rol_personalizado_id == cr.id

    def test_update_with_host_detection(self, db_session):
        sede = _seed_sede(db_session)
        g = _seed_grupo(db_session, sede.id)
        p = _seed_persona(db_session, sede.id)
        _commit(db_session)
        payload = GrupoEvangelismoUpdate(
            base_attendees_with_roles=[
                ParticipanteGrupoConRol(persona_id=p.id, role="anfitrion"),
            ],
        )
        result = crud_groups.update_grupo(db_session, g.id, payload)
        assert result.anfitrion_persona_id == p.id

    def test_update_with_colider_detection(self, db_session):
        sede = _seed_sede(db_session)
        g = _seed_grupo(db_session, sede.id)
        p = _seed_persona(db_session, sede.id)
        _commit(db_session)
        payload = GrupoEvangelismoUpdate(
            base_attendees_with_roles=[
                ParticipanteGrupoConRol(persona_id=p.id, role="colider"),
            ],
        )
        result = crud_groups.update_grupo(db_session, g.id, payload)
        assert result.asistente_persona_id == p.id

    def test_update_with_co_lider_detection(self, db_session):
        sede = _seed_sede(db_session)
        g = _seed_grupo(db_session, sede.id)
        p = _seed_persona(db_session, sede.id)
        _commit(db_session)
        payload = GrupoEvangelismoUpdate(
            base_attendees_with_roles=[
                ParticipanteGrupoConRol(persona_id=p.id, role="co líder"),
            ],
        )
        result = crud_groups.update_grupo(db_session, g.id, payload)
        assert result.asistente_persona_id == p.id

    def test_update_with_host_not_overwritten(self, db_session):
        sede = _seed_sede(db_session)
        g = _seed_grupo(db_session, sede.id)
        p1 = _seed_persona(db_session, sede.id, "Host")
        p2 = _seed_persona(db_session, sede.id, "Other")
        _commit(db_session)
        payload = GrupoEvangelismoUpdate(
            base_attendees_with_roles=[
                ParticipanteGrupoConRol(persona_id=p1.id, role="anfitrion"),
                ParticipanteGrupoConRol(persona_id=p2.id, role="anfitrion"),
            ],
        )
        result = crud_groups.update_grupo(db_session, g.id, payload)
        assert result.anfitrion_persona_id == p1.id


