from __future__ import annotations
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.auth import require_pastor_or_admin
from backend.core.database import get_db

roles_router = APIRouter(tags=["Evangelismo - Roles y Excusas"])

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# EVANGELISM STRATEGIES - ROLES
# ──────────────────────────────────────────────


@roles_router.get(
    "/strategies/{strategy_id}/roles",
    response_model=List[schemas.RolPersonalizadoEstrategiaResponse],
)
def list_strategy_roles(
    strategy_id: str,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_pastor_or_admin),
):
    """Lista los roles personalizados de una estrategia."""
    from backend.crud.evangelism import get_roles_personalizados

    strategy = db.query(models.EstrategiaEvangelismo).filter(models.EstrategiaEvangelismo.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="Estrategia no encontrada")
    return get_roles_personalizados(db, estrategia_id=strategy_id)


@roles_router.post(
    "/strategies/{strategy_id}/roles",
    response_model=schemas.RolPersonalizadoEstrategiaResponse,
)
def create_strategy_role(
    strategy_id: str,
    payload: schemas.RolPersonalizadoEstrategiaCreate,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_pastor_or_admin),
):
    """Crea un rol personalizado para una estrategia."""
    from backend.crud.evangelism import create_rol_personalizado

    strategy = db.query(models.EstrategiaEvangelismo).filter(models.EstrategiaEvangelismo.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="Estrategia no encontrada")
    payload.estrategia_id = strategy_id
    return create_rol_personalizado(db, payload)


@roles_router.delete("/strategies/{strategy_id}/roles/{role_id}")
def delete_strategy_role(
    strategy_id: str,
    role_id: int,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_pastor_or_admin),
):
    """Elimina un rol personalizado de una estrategia."""
    from backend.crud.evangelism import delete_rol_personalizado

    strategy = db.query(models.EstrategiaEvangelismo).filter(models.EstrategiaEvangelismo.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="Estrategia no encontrada")
    if not delete_rol_personalizado(db, role_id):
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    return {"ok": True}


# ──────────────────────────────────────────────
# MOTIVOS DE EXCUSA
# ──────────────────────────────────────────────


@roles_router.get("/excuses", response_model=List[schemas.MotivoExcusaResponse])
def list_motivos_excusa(
    solo_activos: bool = True,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_pastor_or_admin),
):
    """Lista el catálogo de motivos de excusa."""
    from backend.crud.evangelism import get_motivos_excusa

    return get_motivos_excusa(db, solo_activos=solo_activos)


@roles_router.post("/excuses", response_model=schemas.MotivoExcusaResponse)
def create_motivo_excusa(
    payload: schemas.MotivoExcusaCreate,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_pastor_or_admin),
):
    """Crea un nuevo motivo de excusa."""
    from backend.crud.evangelism import create_motivo_excusa

    return create_motivo_excusa(db, payload.descripcion)


@roles_router.patch("/excuses/{excusa_id}", response_model=schemas.MotivoExcusaResponse)
def update_motivo_excusa(
    excusa_id: int,
    payload: schemas.MotivoExcusaUpdate,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_pastor_or_admin),
):
    """Actualiza un motivo de excusa (no permite modificar los del sistema)."""
    from backend.crud.evangelism import update_motivo_excusa

    result = update_motivo_excusa(db, excusa_id, descripcion=payload.descripcion, activo=payload.activo)
    if not result:
        raise HTTPException(status_code=404, detail="Excusa no encontrada o es del sistema")
    return result


@roles_router.delete("/excuses/{excusa_id}")
def delete_motivo_excusa(
    excusa_id: int,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_pastor_or_admin),
):
    """Elimina un motivo de excusa (no permite eliminar los del sistema)."""
    from backend.crud.evangelism import delete_motivo_excusa

    if not delete_motivo_excusa(db, excusa_id):
        raise HTTPException(status_code=404, detail="Excusa no encontrada o es del sistema")
    return {"ok": True}


@roles_router.post("/excuses/seed")
def seed_motivos_excusa(
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_pastor_or_admin),
):
    """Inserta las excusas base del sistema (SALUD, TRABAJO, FAMILIA, OTRA)."""
    from backend.crud.evangelism import seed_motivos_excusa

    created = seed_motivos_excusa(db)
    return {"created": len(created), "excusas": [e.descripcion for e in created]}
