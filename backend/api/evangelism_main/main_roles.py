from __future__ import annotations

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend import models, schemas
from backend import crud
from backend.api.evangelism_shared import get_visible_strategy
from backend.core.database import get_db
from backend.core.permissions import require_evangelism_manage
from backend.core.tenant import require_user_sede_id

roles_router = APIRouter(tags=["Evangelismo - Roles y Excusas"])

logger = logging.getLogger(__name__)


def _require_visible_strategy(db: Session, strategy_id: UUID, user) -> models.EstrategiaEvangelismo:
    strategy = get_visible_strategy(db, strategy_id, require_user_sede_id(db, user))
    if not strategy:
        raise HTTPException(status_code=404, detail="Estrategia no encontrada")
    return strategy


# ──────────────────────────────────────────────
# EVANGELISM STRATEGIES - ROLES
# ──────────────────────────────────────────────


@roles_router.get(
    "/strategies/{strategy_id}/roles",
    response_model=List[schemas.RolPersonalizadoEstrategiaResponse],
)
def list_strategy_roles(
    strategy_id: UUID,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_evangelism_manage),
):
    """Lista los roles personalizados de una estrategia."""
    from backend.crud.evangelism import get_roles_personalizados

    _require_visible_strategy(db, strategy_id, _user)
    rows = get_roles_personalizados(db, estrategia_id=strategy_id)
    # Serializa cada ORM a dict (UUID→str) para ResponseValidation strict.
    return [
        schemas.RolPersonalizadoEstrategiaResponse.model_validate(r).model_dump(mode="json")
        for r in rows
    ]


def _serialize_rol_personalizado(obj) -> dict:
    """Serializa un ORM ``RolPersonalizadoEstrategia`` a dict (UUID→str)."""
    return schemas.RolPersonalizadoEstrategiaResponse.model_validate(obj).model_dump(mode="json")


@roles_router.post(
    "/strategies/{strategy_id}/roles",
    response_model=schemas.RolPersonalizadoEstrategiaResponse,
)
def create_strategy_role(
    strategy_id: UUID,
    payload: schemas.RolPersonalizadoEstrategiaCreate,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_evangelism_manage),
):
    """Crea un rol personalizado para una estrategia."""
    from backend.crud.evangelism import create_rol_personalizado

    _require_visible_strategy(db, strategy_id, _user)
    payload.estrategia_id = strategy_id
    return _serialize_rol_personalizado(create_rol_personalizado(db, payload, actor_user_id=str(_user.id)))


@roles_router.delete("/strategies/{strategy_id}/roles/{role_id}")
def delete_strategy_role(
    strategy_id: UUID,
    role_id: UUID,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_evangelism_manage),
):
    """Elimina un rol personalizado de una estrategia."""
    from backend.crud.evangelism import delete_rol_personalizado

    strategy = _require_visible_strategy(db, strategy_id, _user)
    if strategy.default_role_id == role_id:
        strategy.default_role_id = None
    if not delete_rol_personalizado(db, role_id, actor_user_id=str(_user.id)):
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    return {"ok": True}


# ──────────────────────────────────────────────
# MOTIVOS DE EXCUSA
# ──────────────────────────────────────────────


@roles_router.get("/excuses", response_model=List[schemas.MotivoExcusaResponse])
def list_motivos_excusa(
    solo_activos: bool = True,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_evangelism_manage),
):
    """Lista el catálogo de motivos de excusa."""
    from backend.crud.evangelism import get_motivos_excusa

    return get_motivos_excusa(db, solo_activos=solo_activos)


@roles_router.post("/excuses", response_model=schemas.MotivoExcusaResponse)
def create_motivo_excusa(
    payload: schemas.MotivoExcusaCreate,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_evangelism_manage),
):
    """Crea un nuevo motivo de excusa."""
    from backend.crud.evangelism import create_motivo_excusa

    return create_motivo_excusa(db, payload.descripcion, actor_user_id=str(_user.id))


@roles_router.patch("/excuses/{excusa_id}", response_model=schemas.MotivoExcusaResponse)
def update_motivo_excusa(
    excusa_id: UUID,
    payload: schemas.MotivoExcusaUpdate,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_evangelism_manage),
):
    """Actualiza un motivo de excusa (no permite modificar los del sistema)."""
    from backend.crud.evangelism import update_motivo_excusa

    result = update_motivo_excusa(db, excusa_id, descripcion=payload.descripcion, activo=payload.activo, actor_user_id=str(_user.id))
    if not result:
        raise HTTPException(status_code=404, detail="Excusa no encontrada o es del sistema")
    return result


@roles_router.delete("/excuses/{excusa_id}")
def delete_motivo_excusa(
    excusa_id: UUID,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_evangelism_manage),
):
    """Elimina un motivo de excusa (no permite eliminar los del sistema)."""
    from backend.crud.evangelism import delete_motivo_excusa

    if not delete_motivo_excusa(db, excusa_id, actor_user_id=str(_user.id)):
        raise HTTPException(status_code=404, detail="Excusa no encontrada o es del sistema")
    return {"ok": True}


@roles_router.post("/excuses/seed")
def seed_motivos_excusa(
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_evangelism_manage),
):
    """Inserta las excusas base del sistema (SALUD, TRABAJO, FAMILIA, OTRA)."""
    from backend.crud.evangelism import seed_motivos_excusa

    created = seed_motivos_excusa(db, actor_user_id=str(_user.id))
    return {"created": len(created), "excusas": [e.descripcion for e in created]}
