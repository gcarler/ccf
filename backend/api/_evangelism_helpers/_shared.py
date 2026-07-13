"""Axioma 3 — Multi-Tenant scope helpers for Evangelismo routes.

Facilitadores de scope para entidades del módulo Evangelismo:

  - ``EstrategiaEvangelismo``     → ``sede_id`` directo (columna real).
  - ``GrupoEvangelismo``           → ``sede_id`` directo (columna real).
  - ``SesionGrupo``                → sede vía JOIN ``GrupoEvangelismo``.
  - ``ParticipanteGrupo``          → sede vía JOIN ``GrupoEvangelismo``.
  - ``RegistroSeguimiento``        → sede vía JOIN ``Asistencia → SesionGrupo
                                     → GrupoEvangelismo`` (3 niveles).

Patrón consistente con ``backend/api/_cms_helpers/_shared.py``:

  - El helper SIEMPRE devuelve 404 (no 403) ante cross-sede o target
    inexistente. Esto evita existencia-leaks: el caller no puede distinguir
    "no existe" de "existe pero es de otra sede".
  - Si el staff actual no tiene sede (``_actor_sede_or_none_evangelismo``
    retorna ``None`` → superadmin / anterior path), se omite el scope
    filter y el actor ve TODO lo no-borrado, consistente con la API
    endurecida de CRM/messaging/CMS.

Caso especial:

  - ``MotivoExcusa`` es lookup-table global cross-sede por naturaleza
    y NO recibe scope. La gate ``seed_motivos_excusa`` exige ``actor_sede
    is None`` (``crud/evangelism.py``) — defense-in-depth complementaria
    en la capa CRUD.

DRY multi-module:

  - ``_coerce_uuid_or_404`` vive en ``backend.crud._utils`` y se reusa
    desde CRM, CMS y Evangelismo. Una sola política de 404
    existence-leak safe ante input malformado.

Cierre de IDORs multi-tenant en evangelismo:

  - Reemplaza hand-rolled fetches (``db.query(SesionGrupo).filter(...).first()``)
    por ``_get_scoped_sesion(db, current_user, session_id)`` garantizando
    que el recurso pertenece a la sede del actor (o 404 si está en otra).
  - Idem para estrategia / grupo / participante / seguimiento.
"""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Query, Session

from backend import models
from backend.core.database import get_db
from backend.core.permissions import require_pastor_or_admin
from backend.crud._utils import _coerce_uuid_or_404
from backend.crud.crm import get_user_sede_id
from backend.models_evangelism import (
    Asistencia,
    EstrategiaEvangelismo,
    GrupoEvangelismo,
    ParticipanteGrupo,
    RegistroSeguimiento,
    SesionGrupo,
)

# ────────────────────────────────────────────────────────────────
# 1) Actor → sede resolution
# ────────────────────────────────────────────────────────────────


def _actor_sede_or_none_evangelismo(
    db: Session, current_user: models.User
) -> Optional[str]:
    """Retorna la sede del actor o ``None`` para superadministración.

    Política idéntica al canon ``backend/api/_cms_helpers/_shared._actor_sede_or_none``
    y ``backend/api/crm/_shared._actor_sede_or_none``: si el ``Usuario`` no
    tiene sede asignada (admin, superadmin, usuario "global" Auth v3),
    retorna ``None`` y el caller aplica bypass.

    No se envuelve ``get_user_sede_id`` con try/except porque su contrato
    documentado es: retorna ``None`` para "no sede" silenciosamente y
    deja propagar errores operativos (DB caído, etc.). Un narrow except
    no atrapa el modo de falla real y podría enmascarar un bypass
    silencioso si upstream mutara a retorno ``None`` no intencional.

    Actor sin ``id`` → ``HTTPException(401)``.
    """
    user_id = getattr(current_user, "id", None)
    if user_id is None:
        raise HTTPException(
            status_code=401, detail="Authenticated actor required"
        )
    return get_user_sede_id(db, user_id)


# ────────────────────────────────────────────────────────────────
# 2) Dependency wrapper — require_pastor_or_admin + sede pre-resuelta
# ────────────────────────────────────────────────────────────────


async def require_pastor_or_admin_with_sede(
    request: Request,
    current_user: models.User = Depends(require_pastor_or_admin),
    db: Session = Depends(get_db),
) -> models.User:
    """Wrapper de ``require_pastor_or_admin`` con sede pre-resuelta.

    Comportamiento:

    1. Hereda la validación rol de ``require_pastor_or_admin`` (403 si el
       actor no es pastor ni admin). Garantiza el primer filtro de seguridad.
    2. Resuelve la sede del actor una sola vez (``_actor_sede_or_none_evangelismo``)
       y la cachea en ``request.state.evangelismo_actor_sede`` — slot
       dedicado al scope del módulo evangelismo, no mutamos el ORM
       ``Usuario`` (lo que podría tener efectos colaterales con la sesión
       de SQLAlchemy / serialización Pydantic).
    3. Para superadmin / actor sin sede → ``request.state.evangelismo_actor_sede = None``,
       bypass consistente con el resto del axioma 3.

    Handlers pueden leer la sede cacheada con un cheap ``getattr``::

        @router.get("/sessions/{sid}")
        def get_session(
            sid: UUID,
            request: Request,
            current_user: models.User = Depends(
                require_pastor_or_admin_with_sede
            ),
            db: Session = Depends(get_db),
        ):
            actor_sede = getattr(
                request.state, "evangelismo_actor_sede", None
            )
            return _get_scoped_sesion(db, current_user, sid)

    o llamar inline::

        actor_sede = _actor_sede_or_none_evangelismo(db, current_user)

    Mientras ``_actor_sede_or_none_evangelismo`` es determinista y barato
    (índice por ``user_id``), la cache evita N+1 cuando un handler invoca
    varios ``_get_scoped_*`` por request.
    """
    actor_sede = _actor_sede_or_none_evangelismo(db, current_user)
    request.state.evangelismo_actor_sede = actor_sede
    return current_user


# ────────────────────────────────────────────────────────────────
# 3) Scope filters (Query builders)
# ────────────────────────────────────────────────────────────────


def _scope_evangelism_strategies_by_user_sede(
    db: Session, current_user: models.User, query: Query
) -> Query:
    """Filtra un query de ``EstrategiaEvangelismo`` por ``sede_id == user_sede``.

    Estrategia tiene ``sede_id`` propio: filter directo, eficiente.
    Superadmin bypass (sin scope) si el actor no tiene sede.
    """
    user_sede = _actor_sede_or_none_evangelismo(db, current_user)
    if user_sede:
        query = query.filter(EstrategiaEvangelismo.sede_id == user_sede)
    return query


def _scope_evangelism_grupos_by_user_sede(
    db: Session, current_user: models.User, query: Query
) -> Query:
    """Filtra un query de ``GrupoEvangelismo`` por ``sede_id == user_sede``.

    Grupo tiene ``sede_id`` propio: filter directo, eficiente.
    """
    user_sede = _actor_sede_or_none_evangelismo(db, current_user)
    if user_sede:
        query = query.filter(GrupoEvangelismo.sede_id == user_sede)
    return query


def _scope_evangelismo_through_grupo(
    db: Session,
    current_user: models.User,
    query: Query,
    *,
    from_model,
) -> Query:
    """Sede heredada vía JOIN a ``GrupoEvangelismo``.

    Aplica JOIN ``GrupoEvangelismo.id == from_model.grupo_id`` y filter
    ``GrupoEvangelismo.sede_id == user_sede``. Centraliza el patrón
    repetido en ``_get_scoped_sesion`` y ``_get_scoped_participante``
    (también ``_get_scoped_seguimiento`` con JOIN extra a ``Asistencia``).

    ``from_model``: la entidad ORM externa (e.g. ``SesionGrupo``,
    ``ParticipanteGrupo``) que tiene FK a ``GrupoEvangelismo.grupo_id``.

    Superadmin bypass (sin filter) si el actor no tiene sede.
    """
    user_sede = _actor_sede_or_none_evangelismo(db, current_user)
    query = query.join(
        GrupoEvangelismo, GrupoEvangelismo.id == from_model.grupo_id
    )
    if user_sede:
        query = query.filter(GrupoEvangelismo.sede_id == user_sede)
    return query


# ────────────────────────────────────────────────────────────────
# 4) Getters con existence-leak safe 404
# ────────────────────────────────────────────────────────────────


def _get_scoped_strategy(
    db: Session, current_user: models.User, strategy_id
) -> EstrategiaEvangelismo:
    """Devuelve la ``EstrategiaEvangelismo`` o raise ``HTTPException(404)``.

    Existence-leak safe: 404 tanto si la estrategia no existe como si
    pertenece a otra sede. Filtro por ``sede_id`` directo (columna real).
    """
    sid = _coerce_uuid_or_404(strategy_id, "Estrategia no encontrada")
    query = db.query(EstrategiaEvangelismo).filter(
        EstrategiaEvangelismo.id == sid
    )
    query = _scope_evangelism_strategies_by_user_sede(db, current_user, query)
    row = query.first()
    if not row:
        raise HTTPException(status_code=404, detail="Estrategia no encontrada")
    return row


def _get_scoped_grupo(
    db: Session, current_user: models.User, grupo_id
) -> GrupoEvangelismo:
    """Devuelve el ``GrupoEvangelismo`` o raise ``HTTPException(404)``.

    Existence-leak safe. ``grupo_id`` malformado también devuelve 404.
    """
    gid = _coerce_uuid_or_404(grupo_id, "Grupo no encontrado")
    query = db.query(GrupoEvangelismo).filter(GrupoEvangelismo.id == gid)
    query = _scope_evangelism_grupos_by_user_sede(db, current_user, query)
    row = query.first()
    if not row:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    return row


def _get_scoped_sesion(
    db: Session, current_user: models.User, session_id
) -> SesionGrupo:
    """Devuelve la ``SesionGrupo`` o raise ``HTTPException(404)``.

    SesionGrupo no tiene ``sede_id`` directo: hereda la sede del
    ``GrupoEvangelismo`` padre vía JOIN. Reutiliza
    ``_scope_evangelismo_through_grupo`` para DRY.

    Existence-leak safe: si la sesión existe pero el grupo está en
    otra sede, la query retorna 0 filas y devolvemos 404 sin revelar
    la existencia cross-sede.
    """
    sid = _coerce_uuid_or_404(session_id, "Sesión no encontrada")
    query = db.query(SesionGrupo).filter(SesionGrupo.id == sid)
    query = _scope_evangelismo_through_grupo(
        db, current_user, query, from_model=SesionGrupo
    )
    row = query.first()
    if not row:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    return row


def _get_scoped_participante(
    db: Session, current_user: models.User, participante_id
) -> ParticipanteGrupo:
    """Devuelve el ``ParticipanteGrupo`` o raise ``HTTPException(404)``.

    Hereda sede del grupo padre vía JOIN. Reutiliza el helper DRY.
    """
    pid = _coerce_uuid_or_404(
        participante_id, "Participante no encontrado"
    )
    query = db.query(ParticipanteGrupo).filter(
        ParticipanteGrupo.id == pid
    )
    query = _scope_evangelismo_through_grupo(
        db, current_user, query, from_model=ParticipanteGrupo
    )
    row = query.first()
    if not row:
        raise HTTPException(
            status_code=404, detail="Participante no encontrado"
        )
    return row


def _get_scoped_seguimiento(
    db: Session, current_user: models.User, seguimiento_id
) -> RegistroSeguimiento:
    """Devuelve el ``RegistroSeguimiento`` o raise ``HTTPException(404)``.

    Encadena JOIN ``Asistencia`` → ``SesionGrupo`` → ``GrupoEvangelismo``.
    La sede final es la del grupo de la sesión a la que pertenece la
    asistencia del seguimiento.

    Existence-leak safe en toda la cadena: si cualquier nivel está en
    otra sede, la query retorna 0 filas y devolvemos 404.

    El filtro por ID se aplica primero (sobre la entidad target) y el
    scope por sede después — mismo plan de ejecución porque PostgreSQL
    usa el índice PK de RegistroSeguimiento, pero la intención es más
    legible: "el seguimiento ``X`` si pertenece a mi sede".
    """
    seg_id = _coerce_uuid_or_404(
        seguimiento_id, "Seguimiento no encontrado"
    )
    query = (
        db.query(RegistroSeguimiento)
        .join(Asistencia, Asistencia.id == RegistroSeguimiento.asistencia_id)
        .join(SesionGrupo, SesionGrupo.id == Asistencia.sesion_id)
        .filter(RegistroSeguimiento.id == seg_id)
    )
    # Scope a través del grupo padre (helper agrega JOIN + filter sede).
    query = _scope_evangelismo_through_grupo(
        db, current_user, query, from_model=SesionGrupo
    )
    row = query.first()
    if not row:
        raise HTTPException(
            status_code=404, detail="Seguimiento no encontrado"
        )
    return row


# ────────────────────────────────────────────────────────────────
# Re-exports
# ────────────────────────────────────────────────────────────────


__all__ = (
    # Actor → sede
    "_actor_sede_or_none_evangelismo",
    # Wrapper dependency
    "require_pastor_or_admin_with_sede",
    # Scope filters
    "_scope_evangelism_grupos_by_user_sede",
    "_scope_evangelism_strategies_by_user_sede",
    "_scope_evangelismo_through_grupo",
    # Existence-leak safe getters
    "_get_scoped_grupo",
    "_get_scoped_participante",
    "_get_scoped_seguimiento",
    "_get_scoped_sesion",
    "_get_scoped_strategy",
)
