"""Communication log CRUD."""
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from backend import models, schemas
from backend.crud._utils import _utcnow
from backend.crud.crm_.shared import (
    _actor_sede_or_none,
    _logger,
    _resolve_anchor_sede,
    resolve_persona_id_from_identity,
)
from backend.schemas.notifications import CommunicationLogUpdate


def _crud_scope_re_check_communication_log_create(
    db: Session,
    actor_user_id,
    persona_id,
) -> None:
    """Axioma 3 — defense in depth para ``create_communication_log``.

    Re-valida el anchor ``persona_id`` (única FK de CommunicationLog)
    contra la sede del actor. Cierra el TOCTOU gap donde un caller que
    NO es la API endurecida (worker async, script de seeding, llamada
    directa al CRUD) podría crear un log sobre una persona de otra sede,
    bypaseando ``_get_scoped_persona`` en el router.

    Política (consistente con ``_crud_scope_re_check_task``):
      - Actor sin sede (``_actor_sede_or_none`` retorna ``None``):
        superadmin / anterior path — bypass sin check.
      - Actor con sede y ``persona_id`` None: REJECT (orphan log para un
        editor en sede viola el axioma — invisible para sí mismo,
        visible sólo a ``get_communication_logs(sede_id=None)``).
      - Actor con sede y ``persona_id`` en OTRA sede o irresoluble: REJECT.
      - Match exacto de sede: OK.

    Raises ``HTTPException(404)`` con mensaje neutro (sin leak del anchor)
    para que el caller lo trate como existence-leak safe. La anomalía se
    registra vía ``logging.warning(...)`` para triage operacional.
    """
    user_sede = _actor_sede_or_none(db, actor_user_id)
    if not user_sede:
        return  # superadmin / anterior path

    from fastapi import HTTPException as _HTTPException

    if persona_id is None:
        _logger.warning(
            "Axioma 3 scope violation: create_communication_log sin persona_id "
            "(actor_sede=%s actor_user_id=%s)",
            user_sede,
            actor_user_id,
        )
        raise _HTTPException(
            status_code=404, detail="CommunicationLog creation blocked"
        )

    target_sede = _resolve_anchor_sede(db, "persona_id", persona_id)
    if target_sede is None or target_sede != str(user_sede):
        _logger.warning(
            "Axioma 3 scope violation: create_communication_log cross-sede "
            "(actor_sede=%s actor_user_id=%s persona_id=%s target_sede=%s)",
            user_sede,
            actor_user_id,
            persona_id,
            target_sede,
        )
        # Mensaje genérico para no leakear info de la violation.
        raise _HTTPException(
            status_code=404, detail="CommunicationLog creation blocked"
        )


def create_communication_log(
    db: Session,
    payload: schemas.CommunicationLogCreate,
    *,
    actor_user_id: str | uuid.UUID,
) -> models.CommunicationLog:
    """Crea un CommunicationLog con defense-in-depth (Axioma 3 — CRUD layer).

    Parámetros:
        db: sesión SQLAlchemy.
        payload: schema Pydantic ``CommunicationLogCreate``. Incluye
            ``persona_id`` (target, ∀-required?) y opcional ``leader_id``
            (staff que origina el log).
        actor_user_id: identidad (UUID o string) del usuario que origina
            la mutación. Si es ``None`` (bulk import desde script /
            worker async anterior), se salta el scope re-check. Si tiene
            sede asignada, se valida que ``persona_id`` pertenezca a esa
            sede antes del ``db.add``.

    Defense-in-depth: el CRUD vuelve a verificar el anchor incluso si el
    caller es la API endurecida. Esto cierra el TOCTOU gap donde otro
    admin podría mover la ``Persona`` a otra sede entre el fetch del API
    (``_get_scoped_persona``) y el commit (``create_communication_log``).
    """
    data = payload.model_dump()
    leader_identity = data.pop("leader_id", None)
    data["leader_id"] = resolve_persona_id_from_identity(db, leader_identity)

    # Defense in depth — Axioma 3 (Multi-Tenant) scope re-check (CREATE).
    # Cierra el TOCTOU gap donde un caller no-API (worker, script, seed)
    # podría crear un log con persona cross-sede. Si el actor está en
    # sede_a e intenta loguear persona de sede_b → 404 pre-add.
    _crud_scope_re_check_communication_log_create(
        db, actor_user_id, data.get("persona_id")
    )

    row = models.CommunicationLog(**{k: v for k, v in data.items()
                                     if hasattr(models.CommunicationLog, k)})
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_communication_logs(
    db: Session, limit: int = 50, sede_id: str | None = None
):
    """Lista los CommunicationLog más recientes, opcionalmente acotados a la sede indicada.

    Axioma 3 — Multi-Tenant: si ``sede_id`` está presente, agrega un JOIN con
    ``models.Persona`` y filtra ``Persona.sede_id == sede_id``. CommunicationLog
    NO tiene columna ``sede_id`` propia; el scope se obtiene vía la FK
    ``persona_id → personas.id``. Si ``sede_id`` es ``None`` (superadmin /
    caller sin scope), retorna el log global sin filtrar.

    Política READ-only: para hardening defensivo adicional, callers sensibles
    (API) deben pasar explícitamente su ``user_sede`` recibido desde JWT vía
    ``get_user_sede_id``.
    """
    query = db.query(models.CommunicationLog)
    if sede_id:
        query = query.join(
            models.Persona,
            models.CommunicationLog.persona_id == models.Persona.id,
        ).filter(models.Persona.sede_id == sede_id)
    return query.order_by(models.CommunicationLog.created_at.desc()).limit(limit).all()


def get_communication_log(db: Session, log_id: str) -> Optional[models.CommunicationLog]:
    return db.query(models.CommunicationLog).filter(models.CommunicationLog.id == log_id).first()


def update_communication_log(
    db: Session, log_id: str, payload: CommunicationLogUpdate
) -> Optional[models.CommunicationLog]:
    row = db.query(models.CommunicationLog).filter(models.CommunicationLog.id == log_id).first()
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def delete_communication_log(db: Session, log_id: str) -> bool:
    row = db.query(models.CommunicationLog).filter(models.CommunicationLog.id == log_id).first()
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True
