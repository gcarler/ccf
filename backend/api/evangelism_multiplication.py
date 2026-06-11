"""Sistema de Multiplicación de Grupos de Evangelismo.

Endpoints:
  - GET  /api/evangelism/multiplication/check   — grupos que superan el umbral
  - POST /api/evangelism/multiplication/split   — divide un grupo en dos
  - GET  /api/evangelism/multiplication/history — historial de multiplicaciones
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session, joinedload

from backend import models
from backend.auth import require_pastor_or_admin
from backend.core.database import get_db
from backend.core.tenant import require_user_sede_id

router = APIRouter()
logger = logging.getLogger(__name__)


# ── Pydantic schemas ─────────────────────────────────────────────────────────

class SplitRequest(BaseModel):
    grupo_id: UUID
    nuevo_nombre: str = Field(..., min_length=2, max_length=150)
    nuevo_lider_id: str  # UUID de la Persona que será líder del nuevo grupo


class SplitResponse(BaseModel):
    ok: bool
    mensaje: str
    grupo_original: dict
    nuevo_grupo: dict
    miembros_transferidos: int


class MultiplicationHistoryItem(BaseModel):
    grupo_id: UUID
    grupo_nombre: str
    parent_group_id: Optional[UUID] = None
    parent_group_nombre: Optional[str] = None
    notes_historial: Optional[str] = None
    created_at: Optional[str] = None
    miembros_actuales: int = 0
    lider_nombre: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class MultiplicationCheckItem(BaseModel):
    grupo_id: UUID
    grupo_nombre: str
    lider_nombre: Optional[str] = None
    total_miembros: int
    excede_umbral: bool
    sugerencia: str

    model_config = ConfigDict(from_attributes=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _count_members(db: Session, grupo_id: UUID) -> int:
    return (
        db.query(models.ParticipanteGrupo)
        .filter(
            models.ParticipanteGrupo.grupo_id == grupo_id,
            models.ParticipanteGrupo.activo,
        )
        .count()
    )


def _serialize_grupo(grupo: models.GrupoEvangelismo, db: Session) -> dict:
    miembros_total = _count_members(db, grupo.id)
    return {
        "id": grupo.id,
        "codigo": grupo.codigo,
        "nombre": grupo.nombre,
        "lider_persona_id": str(grupo.lider_persona_id) if grupo.lider_persona_id else None,
        "lider_nombre": f"{grupo.lider.first_name} {grupo.lider.last_name}" if grupo.lider else None,
        "sede_id": grupo.sede_id,
        "activo": grupo.activo,
        "total_miembros": miembros_total,
        "parent_group_id": grupo.parent_group_id,
        "parent_group_nombre": grupo.parent_group.nombre if grupo.parent_group else None,
        "notes_historial": grupo.notes_historial,
        "created_at": grupo.created_at.isoformat() if grupo.created_at else None,
    }


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/multiplication/check", response_model=List[MultiplicationCheckItem])
def check_multiplication(
    umbral: int = Query(15, description="Umbral de miembros para sugerir división"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Analiza todos los grupos y devuelve los que superan el umbral de miembros,
    sugiriendo división."""
    user_sede = require_user_sede_id(db, current_user)
    q = db.query(models.GrupoEvangelismo).filter(
        models.GrupoEvangelismo.activo,
        models.GrupoEvangelismo.sede_id == user_sede,
    )
    grupos = q.options(joinedload(models.GrupoEvangelismo.lider)).order_by(models.GrupoEvangelismo.nombre.asc()).all()

    resultados: list[dict] = []
    for grupo in grupos:
        total = _count_members(db, grupo.id)
        excede = total > umbral
        lider_nombre = (
            f"{grupo.lider.first_name} {grupo.lider.last_name}"
            if grupo.lider
            else "Sin líder"
        )

        if excede:
            mitad = total // 2
            sugerencia = (
                f"Dividir en dos grupos de aproximadamente {mitad} miembros cada uno. "
                f"Seleccione un nuevo líder para el grupo derivado."
            )
        else:
            sugerencia = "Aún no alcanza el umbral mínimo para división."

        resultados.append({
            "grupo_id": grupo.id,
            "grupo_nombre": grupo.nombre,
            "lider_nombre": lider_nombre,
            "total_miembros": total,
            "excede_umbral": excede,
            "sugerencia": sugerencia,
        })

    return resultados


@router.post("/multiplication/split", response_model=SplitResponse)
def split_group(
    payload: SplitRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Divide un grupo existente en dos, transfiriendo la mitad de los miembros
    al nuevo grupo. Registra el historial de multiplicación."""
    import uuid as _uuid

    # ── Validar grupo original ──
    grupo_original = (
        db.query(models.GrupoEvangelismo)
        .filter(models.GrupoEvangelismo.id == payload.grupo_id)
        .first()
    )
    if not grupo_original:
        raise HTTPException(status_code=404, detail="Grupo original no encontrado.")

    if not grupo_original.activo:
        raise HTTPException(
            status_code=400, detail="No se puede dividir un grupo inactivo."
        )

    # ── Validar nuevo líder ──
    try:
        nuevo_lider_uuid = _uuid.UUID(payload.nuevo_lider_id)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=400, detail="nuevo_lider_id debe ser un UUID válido."
        )

    nuevo_lider = (
        db.query(models.Persona)
        .filter(models.Persona.id == nuevo_lider_uuid)
        .first()
    )
    if not nuevo_lider:
        raise HTTPException(status_code=404, detail="Persona del nuevo líder no encontrada.")

    # ── Obtener miembros activos ──
    participantes = (
        db.query(models.ParticipanteGrupo)
        .filter(
            models.ParticipanteGrupo.grupo_id == payload.grupo_id,
            models.ParticipanteGrupo.activo,
        )
        .order_by(models.ParticipanteGrupo.id.asc())
        .all()
    )

    if len(participantes) < 2:
        raise HTTPException(
            status_code=400,
            detail="El grupo necesita al menos 2 miembros para dividirse.",
        )

    # Dividir a la mitad
    mitad = len(participantes) // 2
    transferir = participantes[mitad:]  # segunda mitad se va al nuevo grupo

    # ── Crear nuevo grupo ──
    nuevo_grupo = models.GrupoEvangelismo(
        nombre=payload.nuevo_nombre,
        estrategia_id=grupo_original.estrategia_id,
        sede_id=grupo_original.sede_id,
        dia_reunion=grupo_original.dia_reunion,
        hora_reunion=grupo_original.hora_reunion,
        ubicacion=grupo_original.ubicacion,
        capacidad=grupo_original.capacidad,
        activo=True,
        lider_persona_id=nuevo_lider_uuid,
        parent_group_id=grupo_original.id,
        notes_historial=f"Nacido del grupo '{grupo_original.nombre}' (ID {grupo_original.id}) el {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC",
    )
    db.add(nuevo_grupo)
    db.flush()  # obtener nuevo_grupo.id

    # ── Transferir miembros ──
    transferidos = 0
    for part in transferir:
        part.grupo_id = nuevo_grupo.id
        transferidos += 1

    # ── Actualizar grupo original: registrar como padre ──
    grupo_original.notes_historial = (
        f"Grupo padre del grupo '{payload.nuevo_nombre}' (ID {nuevo_grupo.id}) "
        f"— división realizada el {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC"
    )

    db.commit()
    db.refresh(nuevo_grupo)
    db.refresh(grupo_original)

    logger.info(
        "Grupo dividido: original=%d (%s) → nuevo=%d (%s), %d miembros transferidos por %s",
        grupo_original.id,
        grupo_original.nombre,
        nuevo_grupo.id,
        nuevo_grupo.nombre,
        transferidos,
        current_user.email if hasattr(current_user, "email") else "desconocido",
    )

    return SplitResponse(
        ok=True,
        mensaje=f"Grupo '{grupo_original.nombre}' dividido exitosamente. "
        f"{transferidos} miembros transferidos al nuevo grupo '{nuevo_grupo.nombre}'.",
        grupo_original=_serialize_grupo(grupo_original, db),
        nuevo_grupo=_serialize_grupo(nuevo_grupo, db),
        miembros_transferidos=transferidos,
    )


@router.get("/multiplication/history", response_model=List[MultiplicationHistoryItem])
def multiplication_history(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Devuelve el historial de multiplicaciones: todos los grupos que tienen
    un parent_group_id (es decir, que nacieron de una división)."""
    hijos = (
        db.query(models.GrupoEvangelismo)
        .filter(models.GrupoEvangelismo.parent_group_id.isnot(None))
        .options(
            joinedload(models.GrupoEvangelismo.parent_group),
            joinedload(models.GrupoEvangelismo.lider),
        )
        .order_by(models.GrupoEvangelismo.created_at.desc())
        .all()
    )

    resultados: list[dict] = []
    for grupo in hijos:
        resultados.append({
            "grupo_id": grupo.id,
            "grupo_nombre": grupo.nombre,
            "parent_group_id": grupo.parent_group_id,
            "parent_group_nombre": grupo.parent_group.nombre if grupo.parent_group else None,
            "notes_historial": grupo.notes_historial,
            "created_at": grupo.created_at.isoformat() if grupo.created_at else None,
            "miembros_actuales": _count_members(db, grupo.id),
            "lider_nombre": (
                f"{grupo.lider.first_name} {grupo.lider.last_name}"
                if grupo.lider
                else None
            ),
        })

    return resultados
