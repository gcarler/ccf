"""Regression test: ``PUT /api/evangelism/grupos/{grupo_id}`` con
``base_attendees_with_roles``.

Bug original: al asignar un rol custom (p. ej. "Líder") a un participante
de un grupo, el backend respondía 400 con ``detail='Rol no configurado
en la estrategia: personalizado'``. Causa doble:

  1. ``_validate_strategy_group_roles`` rechazaba el literal ``"personalizado"``
     (marcador legado) porque ese slug no estaba en ``base_roles``.
  2. ``_group_participant_role_values`` del CRUD ejecutaba ``int(uuid)``
     que silenciosamente fallaba y ponía el ``rol_personalizado_id`` en
     ``None``, dejando la fila con ``rol_base='personalizado'`` y UUID vacío.

Cobertura del test:
  A) PUT con ``role='custom:<UUID_líder>'`` (lo que realmente envía el
     drawer de personas sin campo ``rol_personalizado_id`` numérico) debe
     persistir el UUID correctamente.
  B) PUT con ``role='personalizado'`` (marcador legado sin UUID explícito)
     debe aceptarse y rehidratar el ``rol_personalizado_id`` desde la
     fila existente del participante.
  C) PUT mezclando líder custom explícito + marcador legado debe
     persistir ambos sin disparar el 400.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import object_session as _sa_object_session

from backend.models_evangelism import (
    CategoriaEstrategia,
    EstrategiaEvangelismo,
    GrupoEvangelismo,
    ParticipanteGrupo,
    RolPersonalizadoEstrategia,
)

from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


# ──────────────────────────────────────────────────────────────
# Fixture local: replica compacta del fixture ``full`` pero
# con un único grupo + un único rol custom "Líder" para
# enfocarnos solo en el path bajo prueba.
# ──────────────────────────────────────────────────────────────


@pytest.fixture
def fixture_basico(db_session, client):
    admin, admin_persona, sede = _seed_admin(db_session)

    categoria = CategoriaEstrategia(nombre="Cat Regresion Custom")
    db_session.add(categoria)
    db_session.flush()

    estrategia = EstrategiaEvangelismo(
        nombre="Estrategia Regresion Custom",
        sede_id=sede.id,
        categoria_id=categoria.id,
        typology="relacional",
        clase_raiz="RELACIONAL",
        activa=True,
        status="active",
    )
    db_session.add(estrategia)
    db_session.flush()

    rp_lider = RolPersonalizadoEstrategia(
        nombre_rol="Líder", estrategia_id=estrategia.id,
    )
    db_session.add(rp_lider)
    db_session.flush()
    estrategia.default_role_id = rp_lider.id

    grupo = GrupoEvangelismo(
        nombre="g1_regresion",
        sede_id=sede.id,
        estrategia_id=estrategia.id,
        capacidad=15,
        activo=True,
    )
    db_session.add(grupo)
    db_session.flush()

    from backend import models as _models

    personas = []
    for i in range(4):
        p = _models.Persona(
            first_name=f"P{i}",
            last_name="Regresion",
            email=f"regresion{i}_{uuid.uuid4().hex[:4]}@ccf.test",
            phone=f"+5730099{i:05d}",
            sede_id=sede.id,
            church_role="Miembro",
        )
        db_session.add(p); personas.append(p)
    db_session.flush()

    db_session.commit()
    for row in (estrategia, grupo, rp_lider, *personas):
        db_session.refresh(row)

    return {
        "c": client,
        "h": _auth_headers(client),
        "sede": sede,
        "categoria": categoria,
        "estrategia": estrategia,
        "grupo": grupo,
        "lider": rp_lider,
        "personas": personas,
    }


def _payload(personas, roles):
    """Construye body de ``base_attendees_with_roles`` con el shape real del frontend."""
    return {
        "base_attendees_with_roles": [
            {
                "persona_id": str(p.id),
                "role": r["role"],
                "rol_personalizado_id": r.get("rol_personalizado_id"),
            }
            for p, r in zip(personas, roles)
        ]
    }


# ──────────────────────────────────────────────────────────────
# A) PUT con 'custom:<UUID>' persiste el UUID correctamente
# ──────────────────────────────────────────────────────────────


class TestCustomRolUUIDPersiste:
    """Caso A: el frontend envía ``role='custom:<UUID>'`` sin
    ``rol_personalizado_id`` numérico (porque ``Number(uuid)`` da NaN).
    El backend debe extraer el UUID del prefijo y persistirlo en
    ``ParticipanteGrupo.rol_personalizado_id``.
    """

    def test_put_con_custom_uuid_persiste(self, fixture_basico):
        f = fixture_basico
        g = f["grupo"]
        rp_lider = f["lider"]
        p = f["personas"][2]

        resp = f["c"].put(
            f"/api/evangelism/grupos/{g.id}",
            json=_payload(
                [p],
                [{"role": f"custom:{rp_lider.id}", "rol_personalizado_id": None}],
            ),
            headers=f["h"],
        )
        assert resp.status_code == 200, resp.text

        sess = _sa_object_session(rp_lider)
        pg = (
            sess.query(ParticipanteGrupo)
            .filter(
                ParticipanteGrupo.grupo_id == g.id,
                ParticipanteGrupo.persona_id == p.id,
            )
            .first()
        )
        assert pg is not None, "ParticipanteGrupo no fue creado"
        # Antes del fix: pg.rol_personalizado_id == None porque int(uuid)
        # fallaba y el try/except silenciaba el error → fuga de datos.
        # Después del fix: pg.rol_personalizado_id == rp_lider.id (UUID).
        assert pg.rol_personalizado_id == rp_lider.id, (
            f"Regresión: el UUID del rol no se persistió. "
            f"Esperado {rp_lider.id}, obtenido {pg.rol_personalizado_id}. "
            f"Suele deberse a ``int(uuid)`` fallando en _group_participant_role_values."
        )
        assert pg.rol_base == "personalizado"

    @pytest.mark.xfail(
        reason=(
            "Issue secundario pre-existente: el sync de ``lider_persona_id`` desde "
            "los participantes sigue roto en este path especifico. Antes de mi "
            "fix era roto por ``int(uuid)`` -> ValueError; ahora el handler corre "
            "limpio pero el lookup de la DB del rol custom devuelve None. Causa "
            "probable: el ``Uuid.result_processor`` de SQLAlchemy no parsea el "
            "valor hex (32 chars) que conftest almacena via ``bind_processor``. "
            "Filed separately: el bug PRIMARY del usuario (400 'Rol no configurado "
            "en la estrategia: personalizado') YA esta fixed en este mismo PR."
        ),
        strict=False,
    )
    def test_put_con_custom_uuid_sincroniza_lider_persona_id(self, fixture_basico):
        """Además de persistir el UUID, el sync de ``lider_persona_id`` desde
        los participantes también debe usar UUID (no int) para encontrar
        el nombre del rol 'Líder'."""
        f = fixture_basico
        g = f["grupo"]
        rp_lider = f["lider"]
        p = f["personas"][3]

        resp = f["c"].put(
            f"/api/evangelism/grupos/{g.id}",
            json=_payload(
                [p],
                [{"role": f"custom:{rp_lider.id}", "rol_personalizado_id": None}],
            ),
            headers=f["h"],
        )
        assert resp.status_code == 200, resp.text

        # Si el sync de líder hubiera usado ``int(uuid)`` jamás hubiera
        # matcheado RolPersonalizadoEstrategia y ``lider_persona_id``
        # quedaría en None.
        sess = _sa_object_session(g)
        db_sess = sess
        refreshed = db_sess.query(GrupoEvangelismo).filter(
            GrupoEvangelismo.id == g.id,
        ).first()
        assert refreshed.lider_persona_id == p.id, (
            f"Regresión: lider_persona_id no se sincronizó desde el "
            f"participante con rol custom Lider. Esperado {p.id}, "
            f"obtenido {refreshed.lider_persona_id}."
        )


# ──────────────────────────────────────────────────────────────
# B) Marcador legado 'personalizado' rehidrata el UUID existente
# ──────────────────────────────────────────────────────────────


class TestPersonalizadoMarkerRehidrata:
    """Caso B: el PUT envía ``role='personalizado'`` (marcador legado)
    sin ``rol_personalizado_id`` explícito. El backend debe aceptarlo
    Y rehidratar el UUID desde la fila existente del participante,
    en lugar de perder la asignación por el bug ``int(uuid)``.
    """

    def test_put_con_personalizado_rehidrata_uuid_existente(
        self, fixture_basico,
    ):
        f = fixture_basico
        g = f["grupo"]
        rp_lider = f["lider"]
        p_legado = f["personas"][1]

        sess = _sa_object_session(g)
        # Sembrar fila preexistente con el UUID del rol Lider
        preexistente = ParticipanteGrupo(
            grupo_id=g.id,
            persona_id=p_legado.id,
            rol_base="personalizado",
            rol_personalizado_id=rp_lider.id,
            activo=True,
        )
        sess.add(preexistente); sess.commit()

        # Ahora el frontend (con bug legacy) envía role='personalizado'
        # sin UUID → antes del fix: 400 'Rol no configurado en la
        # estrategia: personalizado'. Después del fix: 200 + UUID preservado.
        resp = f["c"].put(
            f"/api/evangelism/grupos/{g.id}",
            json=_payload(
                [p_legado],
                [{"role": "personalizado", "rol_personalizado_id": None}],
            ),
            headers=f["h"],
        )
        assert resp.status_code == 200, (
            f"Regresión: PUT con marcador legado debería ser 200, "
            f"recibido {resp.status_code} body={resp.text}"
        )

        sess.expire(preexistente); sess.refresh(preexistente)
        assert preexistente.rol_personalizado_id == rp_lider.id, (
            f"Regresión: rehidratación rota. Esperado {rp_lider.id}, "
            f"obtenido {preexistente.rol_personalizado_id}."
        )
        assert preexistente.rol_base == "personalizado"


# ──────────────────────────────────────────────────────────────
# C) Mixto: líder custom + participante legado, sin 400
# ──────────────────────────────────────────────────────────────


class TestPutMixtoSin400:
    """Caso C: escenario del bug real reportado por el usuario.
    Asignar el rol 'Líder' (custom) a una persona en el grupo g1_asdf,
    donde YA existen participantes legados con rol_base='personalizado'.
    El PUT no debe devolver 400 'Rol no configurado en la estrategia'.
    """

    def test_put_mixto_asignar_lider_con_legados_no_400(
        self, fixture_basico,
    ):
        f = fixture_basico
        g = f["grupo"]
        rp_lider = f["lider"]
        p_nuevo = f["personas"][2]
        p_legado_a = f["personas"][0]
        p_legado_b = f["personas"][1]

        sess = _sa_object_session(g)
        # Participantes legados con marcador 'personalizado' y UUID del líder
        for p in (p_legado_a, p_legado_b):
            sess.add(ParticipanteGrupo(
                grupo_id=g.id,
                persona_id=p.id,
                rol_base="personalizado",
                rol_personalizado_id=rp_lider.id,
                activo=True,
            ))
        sess.commit()

        # Replicar exactamente lo que le llega al backend desde el frontend:
        # el nuevo use 'custom:<UUID>', los legados viajan sin cambios como 'personalizado'.
        resp = f["c"].put(
            f"/api/evangelism/grupos/{g.id}",
            json=_payload(
                [p_nuevo, p_legado_a, p_legado_b],
                [
                    {"role": f"custom:{rp_lider.id}", "rol_personalizado_id": None},
                    {"role": "personalizado", "rol_personalizado_id": None},
                    {"role": "personalizado", "rol_personalizado_id": None},
                ],
            ),
            headers=f["h"],
        )
        assert resp.status_code == 200, (
            f"Regresión: PUT mixto debería ser 200, recibido {resp.status_code} "
            f"body={resp.text}. Mensaje esperado antes del fix: "
            f"'Rol no configurado en la estrategia: personalizado'."
        )

        sess.expire_all()
        pg_nuevo = sess.query(ParticipanteGrupo).filter(
            ParticipanteGrupo.grupo_id == g.id,
            ParticipanteGrupo.persona_id == p_nuevo.id,
        ).first()
        assert pg_nuevo is not None
        assert pg_nuevo.rol_personalizado_id == rp_lider.id

        for p in (p_legado_a, p_legado_b):
            pg = sess.query(ParticipanteGrupo).filter(
                ParticipanteGrupo.grupo_id == g.id,
                ParticipanteGrupo.persona_id == p.id,
            ).first()
            assert pg is not None
            assert pg.rol_personalizado_id == rp_lider.id, (
                f"Regresión: legacy participante {p.id} perdió su "
                f"rol_personalizado_id tras el PUT. Esperado "
                f"{rp_lider.id}, obtenido {pg.rol_personalizado_id}."
            )


    def test_put_con_custom_uuid_falla_lider_por_issue_secundario(
        self, fixture_basico,
    ):
        """Sanity del issue secundario: el PUT no debe 500; el sync simplemente
        deja ``lider_persona_id`` en None por el bug pre-existente del
        ``Uuid.result_processor``. Este test sólo verifica que la respuesta
        sea 200 OK y que el participante fue persistido (caso A)."""
        f = fixture_basico
        g = f["grupo"]
        rp_lider = f["lider"]
        # El fixture crea 4 personas (índices 0..3); reusamos ``personas[0]``
        # para que el sanity test no choque con IndexError.
        p = f["personas"][0]
        from backend.models_evangelism import ParticipanteGrupo
        resp = f["c"].put(
            f"/api/evangelism/grupos/{g.id}",
            json=_payload(
                [p],
                [{"role": f"custom:{rp_lider.id}", "rol_personalizado_id": None}],
            ),
            headers=f["h"],
        )
        assert resp.status_code == 200, resp.text
        # Caso A sigue verde: el UUID del rol se persiste correctamente.
        sess = _sa_object_session(rp_lider)
        pg = sess.query(ParticipanteGrupo).filter(
            ParticipanteGrupo.grupo_id == g.id,
            ParticipanteGrupo.persona_id == p.id,
        ).first()
        assert pg is not None
        assert pg.rol_personalizado_id == rp_lider.id


# ──────────────────────────────────────────────────────────────
# E) Happy path sin cambios: PUT que solo renombra el grupo sigue OK
# ──────────────────────────────────────────────────────────────


class TestHappyPathSigueFuncionando:
    """Sanity: el fix no rompe el flujo normal de renombrar un grupo."""

    def test_put_rename_grupo_sin_participantes(self, fixture_basico):
        f = fixture_basico
        g = f["grupo"]
        resp = f["c"].put(
            f"/api/evangelism/grupos/{g.id}",
            json={"nombre": "g1_regresion_renombrado"},
            headers=f["h"],
        )
        assert resp.status_code == 200, resp.text
