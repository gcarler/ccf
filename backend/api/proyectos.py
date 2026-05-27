"""Nuevo módulo de proyectos (/api/proyectos).

Convivve paralelamente con /api/projects (viejo).
Tablas: proyectos, equipo_proyecto, tareas_proyecto, dependencias_tareas,
        comentarios_tarea, documentos_proyecto.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.permissions import require_module_access
from backend.models_proyectos import (ComentarioTarea, DependenciaTarea,
                                       DocumentoProyecto, EquipoProyecto,
                                       Proyecto, TareaProyecto)
from backend.schemas.proyectos import (
    ComentarioTareaCreate, ComentarioTareaSchema, DependenciaTareaCreate,
    DependenciaTareaSchema, DocumentoCreate, DocumentoSchema,
    EquipoProyectoCreate, EquipoProyectoSchema, ProyectoCreate, ProyectoSchema,
    ProyectoUpdate, TareaProyectoCreate, TareaProyectoSchema,
    TareaProyectoUpdate)

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Helpers ─────────────────────────────────────────────────────────────────

def _get_proyecto_o_404(proyecto_id: str, db: Session) -> Proyecto:
    try:
        pid = uuid.UUID(proyecto_id)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="ID de proyecto inválido")
    proy = db.query(Proyecto).filter(Proyecto.id == pid).first()
    if not proy:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Proyecto no encontrado")
    return proy


def _get_tarea_o_404(tarea_id: str, db: Session) -> TareaProyecto:
    try:
        tid = uuid.UUID(tarea_id)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="ID de tarea inválido")
    tarea = db.query(TareaProyecto).filter(TareaProyecto.id == tid).first()
    if not tarea:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada")
    return tarea


# ── Proyectos CRUD ─────────────────────────────────────────────────────────

@router.get("/", response_model=list[ProyectoSchema])
def listar_proyectos(
    db: Session = Depends(get_db),
    _=Depends(require_module_access("projects", "read")),
):
    return db.query(Proyecto).order_by(Proyecto.fecha_creacion.desc()).all()


@router.post("/", response_model=ProyectoSchema, status_code=status.HTTP_201_CREATED)
def crear_proyecto(
    payload: ProyectoCreate,
    db: Session = Depends(get_db),
    _=Depends(require_module_access("projects", "edit")),
):
    proy = Proyecto(**payload.model_dump())
    db.add(proy)
    db.commit()
    db.refresh(proy)
    return proy


@router.get("/{proyecto_id}", response_model=ProyectoSchema)
def obtener_proyecto(
    proyecto_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_module_access("projects", "read")),
):
    proy = _get_proyecto_o_404(proyecto_id, db)
    return proy


@router.patch("/{proyecto_id}", response_model=ProyectoSchema)
def actualizar_proyecto(
    proyecto_id: str,
    payload: ProyectoUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_module_access("projects", "edit")),
):
    proy = _get_proyecto_o_404(proyecto_id, db)
    for key, val in payload.model_dump(exclude_unset=True).items():
        setattr(proy, key, val)
    db.commit()
    db.refresh(proy)
    return proy


@router.delete("/{proyecto_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_proyecto(
    proyecto_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_module_access("projects", "admin")),
):
    proy = _get_proyecto_o_404(proyecto_id, db)
    db.delete(proy)
    db.commit()


# ── Equipo ─────────────────────────────────────────────────────────────────

@router.get("/{proyecto_id}/equipo", response_model=list[EquipoProyectoSchema])
def listar_equipo(
    proyecto_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_module_access("projects", "read")),
):
    _get_proyecto_o_404(proyecto_id, db)  # validate exists
    return db.query(EquipoProyecto).filter(
        EquipoProyecto.proyecto_id == uuid.UUID(proyecto_id),
        EquipoProyecto.es_historico == False,
    ).all()


@router.post("/{proyecto_id}/equipo", response_model=EquipoProyectoSchema, status_code=status.HTTP_201_CREATED)
def agregar_miembro(
    proyecto_id: str,
    payload: EquipoProyectoCreate,
    db: Session = Depends(get_db),
    _=Depends(require_module_access("projects", "edit")),
):
    _get_proyecto_o_404(proyecto_id, db)
    miembro = EquipoProyecto(proyecto_id=uuid.UUID(proyecto_id), **payload.model_dump())
    db.add(miembro)
    db.commit()
    db.refresh(miembro)
    return miembro


@router.delete("/{proyecto_id}/equipo/{persona_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_miembro(
    proyecto_id: str,
    persona_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_module_access("projects", "admin")),
):
    _get_proyecto_o_404(proyecto_id, db)
    miembro = db.query(EquipoProyecto).filter(
        EquipoProyecto.proyecto_id == uuid.UUID(proyecto_id),
        EquipoProyecto.persona_id == persona_id,
        EquipoProyecto.es_historico == False,
    ).first()
    if not miembro:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Miembro no encontrado en el equipo")
    db.delete(miembro)
    db.commit()


# ── Tareas ─────────────────────────────────────────────────────────────────

@router.get("/{proyecto_id}/tareas", response_model=list[TareaProyectoSchema])
def listar_tareas(
    proyecto_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_module_access("projects", "read")),
):
    _get_proyecto_o_404(proyecto_id, db)
    return db.query(TareaProyecto).filter(
        TareaProyecto.proyecto_id == uuid.UUID(proyecto_id),
    ).order_by(TareaProyecto.fecha_vencimiento).all()


@router.post("/{proyecto_id}/tareas", response_model=TareaProyectoSchema, status_code=status.HTTP_201_CREATED)
def crear_tarea(
    proyecto_id: str,
    payload: TareaProyectoCreate,
    db: Session = Depends(get_db),
    _=Depends(require_module_access("projects", "edit")),
):
    _get_proyecto_o_404(proyecto_id, db)
    tarea = TareaProyecto(proyecto_id=uuid.UUID(proyecto_id), **payload.model_dump())
    db.add(tarea)
    db.commit()
    db.refresh(tarea)
    return tarea


@router.patch("/{proyecto_id}/tareas/{tarea_id}", response_model=TareaProyectoSchema)
def actualizar_tarea(
    proyecto_id: str,
    tarea_id: str,
    payload: TareaProyectoUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_module_access("projects", "edit")),
):
    _get_proyecto_o_404(proyecto_id, db)
    tarea = _get_tarea_o_404(tarea_id, db)
    if str(tarea.proyecto_id) != proyecto_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="La tarea no pertenece a este proyecto")
    for key, val in payload.model_dump(exclude_unset=True).items():
        setattr(tarea, key, val)
    db.commit()
    db.refresh(tarea)
    return tarea


@router.delete("/{proyecto_id}/tareas/{tarea_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_tarea(
    proyecto_id: str,
    tarea_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_module_access("projects", "admin")),
):
    _get_proyecto_o_404(proyecto_id, db)
    tarea = _get_tarea_o_404(tarea_id, db)
    if str(tarea.proyecto_id) != proyecto_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="La tarea no pertenece a este proyecto")
    db.delete(tarea)
    db.commit()


# ── Comentarios ────────────────────────────────────────────────────────────

@router.post("/{proyecto_id}/tareas/{tarea_id}/comentarios", response_model=ComentarioTareaSchema, status_code=status.HTTP_201_CREATED)
def crear_comentario(
    proyecto_id: str,
    tarea_id: str,
    payload: ComentarioTareaCreate,
    db: Session = Depends(get_db),
    _=Depends(require_module_access("projects", "read")),
):
    _get_proyecto_o_404(proyecto_id, db)
    tarea = _get_tarea_o_404(tarea_id, db)
    if str(tarea.proyecto_id) != proyecto_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="La tarea no pertenece a este proyecto")
    comentario = ComentarioTarea(
        tarea_id=uuid.UUID(tarea_id),
        persona_id=1,  # TODO: sacar de auth.current_user
        comentario=payload.comentario,
    )
    db.add(comentario)
    db.commit()
    db.refresh(comentario)
    return comentario


# ── Dependencias ───────────────────────────────────────────────────────────

@router.post("/{proyecto_id}/tareas/{tarea_id}/dependencias", response_model=DependenciaTareaSchema, status_code=status.HTTP_201_CREATED)
def crear_dependencia(
    proyecto_id: str,
    tarea_id: str,
    payload: DependenciaTareaCreate,
    db: Session = Depends(get_db),
    _=Depends(require_module_access("projects", "edit")),
):
    _get_proyecto_o_404(proyecto_id, db)
    tarea = _get_tarea_o_404(tarea_id, db)
    if str(tarea.proyecto_id) != proyecto_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="La tarea no pertenece a este proyecto")
    dep = DependenciaTarea(
        tarea_bloqueante_id=payload.tarea_bloqueante_id,
        tarea_bloqueada_id=uuid.UUID(tarea_id),
        tipo_dependencia=payload.tipo_dependencia,
    )
    db.add(dep)
    db.commit()
    db.refresh(dep)
    return dep
