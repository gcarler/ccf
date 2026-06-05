from __future__ import annotations
import datetime
from datetime import timezone as _tz
import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.api.evangelism_shared import utc_now
from backend.auth import require_active_user, require_admin, require_module_access, require_pastor_or_admin
from backend.core.database import get_db
from backend.core.tenant import require_user_sede_id
from backend.crud.evangelism import (
    create_estrategia as create_evangelism_strategy,
    update_estrategia as update_evangelism_strategy,
    delete_estrategia as delete_evangelism_strategy,
)
from backend.schemas.crm import (
    EvangelismStrategy,
    EvangelismStrategyCreate,
    EvangelismStrategyUpdate,
)
from backend.mesh_websockets import manager

estrategias_router = APIRouter(tags=["Evangelismo - Estrategias"])

logger = logging.getLogger(__name__)


# --- EVANGELISM STRATEGIES ---


@estrategias_router.get("/strategies", response_model=List[EvangelismStrategy])
def read_evangelism_strategies(
    skip: int = 0,
    limit: int = 100,
    activa: Optional[bool] = None,
    clase_raiz: Optional[str] = None,
    sede_id: Optional[str] = None,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_pastor_or_admin),
):
    from backend.models_evangelism import GrupoEvangelismo
    from backend.crud.evangelism import get_estrategias

    strategies = get_estrategias(
        db,
        skip=skip,
        limit=limit,
        activa=activa,
        clase_raiz=clase_raiz,
        sede_id=sede_id,
    )
    result = []
    for s in strategies:
        obj = EvangelismStrategy.model_validate(s)
        obj.group_count = db.query(GrupoEvangelismo).filter(
            GrupoEvangelismo.estrategia_id == str(s.id),
            GrupoEvangelismo.deleted_at.is_(None),
        ).count()
        result.append(obj)
    return result


@estrategias_router.get("/strategies/{strategy_id}", response_model=EvangelismStrategy)
def read_strategy(
    strategy_id: str,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_pastor_or_admin),
):
    from backend.models_evangelism import EstrategiaEvangelismo as StrategyModel
    from backend.models_evangelism import GrupoEvangelismo

    db_obj = db.query(StrategyModel).filter(StrategyModel.id == strategy_id).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="Evangelism strategy not found")
    result = EvangelismStrategy.model_validate(db_obj)
    result.group_count = db.query(GrupoEvangelismo).filter(
        GrupoEvangelismo.estrategia_id == strategy_id,
        GrupoEvangelismo.deleted_at.is_(None),
    ).count()
    return result


@estrategias_router.post("/strategies", response_model=EvangelismStrategy)
def create_strategy(
    strategy: EvangelismStrategyCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    try:
        from backend.models_evangelism import CategoriaEstrategia
        from backend.models import Sede as _Sede
        # Asignar sede_id desde el usuario autenticado
        sede_id = crud.get_user_sede_id(db, current_user.id)
        if not sede_id:
            # Fallback: usar la primera sede disponible
            primera_sede = db.query(_Sede).order_by("nombre").first()
            if not primera_sede:
                raise HTTPException(400, detail="No hay sedes configuradas en el sistema.")
            sede_id = str(primera_sede.id)
        # Asignar categoria_id por defecto (tomar la primera disponible, o crear una genérica)
        primera_categoria = db.query(CategoriaEstrategia).order_by("id").first()
        if not primera_categoria:
            # Crear categoría por defecto si no existe ninguna
            primera_categoria = CategoriaEstrategia(nombre="General")
            db.add(primera_categoria)
            db.flush()
        result = create_evangelism_strategy(db=db, data=strategy, sede_id=sede_id, categoria_id=primera_categoria.id)
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise
    # ── Phase scheduling trigger ──
    if strategy.typology == "evento_masivo" and strategy.phases:
        try:
            _project_phases_as_tasks(db, result.id, result.name, strategy.phases, strategy.start_date)
        except Exception:
            db.rollback()
            if not delete_evangelism_strategy(db=db, strategy_id=result.id):
                logger.error(
                    "Failed to clean up strategy after phase generation error",
                    extra={"strategy_id": str(result.id)},
                )
            raise HTTPException(
                status_code=500,
                detail="No se pudieron generar las tareas del evento masivo",
            )
    return result


@estrategias_router.put("/strategies/{strategy_id}", response_model=EvangelismStrategy)
def update_strategy(
    strategy_id: str,
    strategy: EvangelismStrategyUpdate,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_pastor_or_admin),
):
    try:
        db_obj = update_evangelism_strategy(db=db, strategy_id=strategy_id, data=strategy)
    except Exception:
        db.rollback()
        raise
    if not db_obj:
        raise HTTPException(status_code=404, detail="Evangelism strategy not found")
    result = EvangelismStrategy.model_validate(db_obj)
    # ── Phase scheduling trigger ──
    if strategy.typology == "evento_masivo" and strategy.phases:
        try:
            _project_phases_as_tasks(db, strategy_id, result.name, strategy.phases, strategy.start_date)
        except Exception:
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail="No se pudieron generar las tareas del evento masivo",
            )
    return result


@estrategias_router.post("/strategies/{strategy_id}/generate-sessions", response_model=dict)
def generate_strategy_sessions(
    strategy_id: str,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_pastor_or_admin),
):
    """Genera sesiones automáticas para todos los grupos de una estrategia según su recurrencia."""
    from backend.models_evangelism import EstrategiaEvangelismo as StratModel
    from backend.models_evangelism import GrupoEvangelismo
    from backend.services.calculo_sesiones import calcular_sesiones

    strat = db.query(StratModel).filter(StratModel.id == strategy_id).first()
    if not strat:
        raise HTTPException(status_code=404, detail="Estrategia no encontrada")
    if not strat.frecuencia or not strat.fecha_inicio or not strat.fecha_fin:
        raise HTTPException(
            status_code=400,
            detail="La estrategia necesita: frecuencia, fecha_inicio, fecha_fin",
        )

    groups = db.query(GrupoEvangelismo).filter(
        GrupoEvangelismo.estrategia_id == strategy_id,
        GrupoEvangelismo.deleted_at.is_(None),
    ).all()

    try:
        created = calcular_sesiones(
            db=db,
            estrategia_id=strategy_id,
            sede_id=strat.sede_id,
            fecha_inicio=strat.fecha_inicio,
            fecha_fin=strat.fecha_fin,
            frecuencia=strat.frecuencia,
            grupos_ids=[g.id for g in groups],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    sessions_per_group = created // len(groups) if groups else 0
    return {
        "strategy": strat.nombre,
        "recurrence": strat.frecuencia,
        "start": str(strat.fecha_inicio),
        "end": str(strat.fecha_fin),
        "sessions_per_group": sessions_per_group,
        "groups": len(groups),
        "total_sessions_created": created,
    }


@estrategias_router.delete("/strategies/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_strategy(
    strategy_id: str,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_pastor_or_admin),
):
    if not delete_evangelism_strategy(db=db, strategy_id=strategy_id):
        raise HTTPException(status_code=404, detail="Evangelism strategy not found")


def _project_phases_as_tasks(db, strategy_id: str, strategy_name: str, phases: list[dict], start_date=None):
    """Create N1 tasks in Projects module for each phase of a mass event."""
    from backend.models_projects import Project, ProjectTask
    from datetime import datetime

    # Create a project linked to the strategy
    project = Project(
        title=f"[MASIVO] {strategy_name}",
        description=f"Evento masivo generado desde estrategia de evangelismo #{strategy_id}",
        status="active",
        created_at=datetime.now(_tz.utc),
    )
    # Store strategy link in description
    db.add(project)
    db.flush()

    for i, phase in enumerate(phases):
        phase_name = phase.get("name", f"Fase {i + 1}")
        phase_type = phase.get("type", "general")
        phase_start = phase.get("start_date")
        phase_end = phase.get("end_date")

        try:
            sd = datetime.fromisoformat(phase_start.replace("Z", "+00:00")) if phase_start else None
        except Exception:
            sd = None
        try:
            dd = datetime.fromisoformat(phase_end.replace("Z", "+00:00")) if phase_end else None
        except Exception:
            dd = None

        task = ProjectTask(
            project_id=project.id,
            title=f"[N1] {phase_name}",
            description=f"Fase '{phase_type}' del evento masivo '{strategy_name}'. Generada automáticamente.",
            priority="urgent",  # N1 = highest priority
            status="todo",
            start_date=sd,
            due_date=dd,
            order_index=i,
            labels=["N1", "Evangelismo", phase_type] if phase_type else ["N1", "Evangelismo"],
            created_at=datetime.now(_tz.utc),
        )
        db.add(task)

    db.commit()
    return project
