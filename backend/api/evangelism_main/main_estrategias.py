from __future__ import annotations

import logging
from datetime import timezone as _tz
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend import crud, models
from backend.core.database import get_db
from backend.core.permissions import require_pastor_or_admin
from backend.crud.evangelism import (
    create_estrategia as create_evangelism_strategy,
)
from backend.crud.evangelism import (
    delete_estrategia as delete_evangelism_strategy,
)
from backend.crud.evangelism import (
    update_estrategia as update_evangelism_strategy,
)
from backend.api.evangelism_shared import sessions_grupo_has_estado_habilitacion
from backend.schemas.crm.base import (
    EvangelismStrategy,
    EvangelismStrategyCreate,
    EvangelismStrategyUpdate,
)

estrategias_router = APIRouter(tags=["Evangelismo - Estrategias"])

logger = logging.getLogger(__name__)


# --- EVANGELISM STRATEGIES ---


def _hydrate_strategy_synonyms(obj: EvangelismStrategy, source) -> EvangelismStrategy:
    """Asegura synonyms de SQLAlchemy que Pydantic v2 puede omitir."""
    if obj.recurrence is None and source.frecuencia is not None:
        obj.recurrence = source.frecuencia
    if obj.day_of_week is None and source.dia_reunion is not None:
        obj.day_of_week = source.dia_reunion
    if obj.start_time is None and source.hora_reunion is not None:
        obj.start_time = source.hora_reunion
    if obj.start_date is None and source.fecha_inicio is not None:
        obj.start_date = source.fecha_inicio
    if obj.end_date is None and source.fecha_fin is not None:
        obj.end_date = source.fecha_fin
    return obj


def _count_strategy_groups(db: Session, strategy_id: UUID) -> int:
    from backend.models_evangelism import GrupoEvangelismo
    return db.query(GrupoEvangelismo).filter(
        GrupoEvangelismo.estrategia_id == strategy_id,
        GrupoEvangelismo.deleted_at.is_(None),
    ).count()


def read_evangelism_strategies(
    skip: int = 0,
    limit: int = 100,
    activa: Optional[bool] = None,
    clase_raiz: Optional[str] = None,
    sede_id: Optional[str] = None,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_pastor_or_admin),
):
    from backend.crud.evangelism import get_estrategias
    from backend.models_evangelism import GrupoEvangelismo

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
        obj = _hydrate_strategy_synonyms(obj, s)
        obj.group_count = _count_strategy_groups(db, s.id)
        result.append(obj)
    return result


@estrategias_router.get("/strategies", response_model=List[EvangelismStrategy])
def read_evangelism_strategies_route(
    skip: int = 0,
    limit: int = 100,
    activa: Optional[bool] = None,
    clase_raiz: Optional[str] = None,
    sede_id: Optional[str] = None,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_pastor_or_admin),
):
    return read_evangelism_strategies(
        skip=skip,
        limit=limit,
        activa=activa,
        clase_raiz=clase_raiz,
        sede_id=sede_id,
        db=db,
        _user=_user,
    )


@estrategias_router.get("/strategies/{strategy_id}", response_model=EvangelismStrategy)
def read_strategy(
    strategy_id: UUID,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_pastor_or_admin),
):
    from backend.models_evangelism import EstrategiaEvangelismo as StrategyModel
    from backend.models_evangelism import GrupoEvangelismo

    db_obj = db.query(StrategyModel).filter(StrategyModel.id == strategy_id).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="Evangelism strategy not found")
    result = EvangelismStrategy.model_validate(db_obj)
    result = _hydrate_strategy_synonyms(result, db_obj)
    result.group_count = _count_strategy_groups(db, strategy_id)
    return result


@estrategias_router.post("/strategies", response_model=EvangelismStrategy)
def create_strategy(
    strategy: EvangelismStrategyCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    try:
        from backend.models import Sede as _Sede
        from backend.models_evangelism import CategoriaEstrategia
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
        result = create_evangelism_strategy(db=db, data=strategy, sede_id=sede_id, categoria_id=primera_categoria.id, actor_user_id=str(current_user.id))
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
            logger.warning(
                "Phase task generation failed for evangelism strategy=%s; keeping strategy saved",
                result.id,
            )
    return result


@estrategias_router.put("/strategies/{strategy_id}", response_model=EvangelismStrategy)
def update_strategy(
    strategy_id: UUID,
    strategy: EvangelismStrategyUpdate,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_pastor_or_admin),
):
    try:
        if strategy.default_role_id is not None:
            from backend.models_evangelism import RolPersonalizadoEstrategia

            default_role = (
                db.query(RolPersonalizadoEstrategia)
                .filter(
                    RolPersonalizadoEstrategia.id == strategy.default_role_id,
                    RolPersonalizadoEstrategia.estrategia_id == strategy_id,
                    RolPersonalizadoEstrategia.deleted_at.is_(None),
                )
                .first()
            )
            if not default_role:
                raise HTTPException(
                    status_code=400,
                    detail="El rol por defecto debe pertenecer a esta estrategia",
                )
        db_obj = update_evangelism_strategy(db=db, strategy_id=strategy_id, data=strategy, actor_user_id=str(_user.id))
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
            logger.warning(
                "Phase task regeneration failed for evangelism strategy=%s; keeping update saved",
                strategy_id,
            )
    return result


@estrategias_router.post("/strategies/{strategy_id}/generate-sessions", response_model=dict)
def generate_strategy_sessions(
    strategy_id: UUID,
    habilitar_inmediatamente: bool = True,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_pastor_or_admin),
):
    """Genera sesiones automáticas para todos los grupos de una estrategia según su recurrencia.

    Si la estrategia tiene ``dia_reunion`` configurado, la fecha de inicio se ajusta
    automáticamente al primer día de reunión — así las sesiones siempre caen en el
    día correcto de la semana aunque la fecha_inicio esté en otro día.

    Quality fix (R3 — riesgo residual audit): por defecto
    ``habilitar_inmediatamente=True`` para eliminar la fricción "generar → habilitar
    manualmente → recién entonces reportar". Las sesiones recién creadas ya nacen
    en ``HABILITADO`` para que los líderes puedan reportar asistencia sin paso
    intermedio. Tests de regresión sensibles a la regla histórica "nacen
    DESHABILITADO" pueden pasar ``habilitar_inmediatamente=False`` y conservar el
    bloqueo como flujo canónico de seguridad (ver
    ``test_evangelism_triple7_flow.py``).
    """
    from datetime import timedelta

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

    if not groups:
        return {
            "strategy": strat.nombre,
            "recurrence": strat.frecuencia,
            "start": str(strat.fecha_inicio),
            "end": str(strat.fecha_fin),
            "sessions_per_group": 0,
            "groups": 0,
            "total_sessions_created": 0,
            "message": "No hay grupos en esta estrategia. Crea grupos primero."
        }

    # ── Ajustar fecha_inicio al primer día de reunión ──
    fecha_inicio = strat.fecha_inicio
    if strat.dia_reunion:
        DAY_MAP = {
            "domingo": 6, "lunes": 0, "martes": 1, "miércoles": 2,
            "miercoles": 2, "jueves": 3, "viernes": 4, "sábado": 5, "sabado": 5,
            "Domingo": 6, "Lunes": 0, "Martes": 1, "Miércoles": 2,
            "Jueves": 3, "Viernes": 4, "Sábado": 5,
        }
        target = DAY_MAP.get(strat.dia_reunion)
        if target is not None:
            current_weekday = fecha_inicio.weekday()
            diff = (target - current_weekday) % 7
            if diff > 0:
                fecha_inicio = fecha_inicio + timedelta(days=diff)
                logger.info(
                    "Ajustando fecha_inicio de %s a %s (día=%s)",
                    strat.fecha_inicio, fecha_inicio, strat.dia_reunion,
                )

    # Capturar timestamp ANTES de calcular_sesiones. Sirve como umbral
    # para que el update posterior habilite SOLO las sesiones recién
    # creadas (``created_at > _before_call``). Sin este desplazamiento
    # el filtro no encuentra nada porque ``calcular_sesiones`` ya hizo
    # su propio ``db.commit()`` con ``created_at = now()`` previo.
    from datetime import datetime as _dt_now
    _before_call = _dt_now.utcnow()

    created = 0
    sesiones_habilitadas = 0
    try:
        created = calcular_sesiones(
            db=db,
            estrategia_id=strategy_id,
            sede_id=strat.sede_id,
            fecha_inicio=fecha_inicio,
            fecha_fin=strat.fecha_fin,
            frecuencia=strat.frecuencia,
            grupos_ids=[g.id for g in groups],
        )
    except ValueError as e:
        logger.warning("No se pudieron validar sesiones para strategy=%s: %s", strategy_id, e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.warning("Failed to generate evangelism sessions for strategy=%s", strategy_id)
        return {
            "strategy": strat.nombre,
            "recurrence": strat.frecuencia,
            "start": str(fecha_inicio),
            "end": str(strat.fecha_fin),
            "sessions_per_group": 0,
            "groups": len(groups),
            "total_sessions_created": 0,
            "sesiones_habilitadas": 0,
            "habilitar_inmediatamente": habilitar_inmediatamente,
            "warning": "No se pudieron generar sesiones en esta sede",
        }

    sessions_per_group = created // len(groups) if groups else 0

    if habilitar_inmediatamente and created > 0:
        from backend.models_evangelism import HabilitacionSesionEnum, SesionGrupo

        if not sessions_grupo_has_estado_habilitacion(db):
            return {
                "strategy": strat.nombre,
                "recurrence": strat.frecuencia,
                "start": str(fecha_inicio),
                "end": str(strat.fecha_fin),
                "sessions_per_group": sessions_per_group,
                "groups": len(groups),
                "total_sessions_created": created,
                "sesiones_habilitadas": 0,
                "habilitar_inmediatamente": habilitar_inmediatamente,
            }

        # Auto-habilitar SOLO las sesiones creadas en este call.
        # ``_before_call`` se tomó arriba antes de ``calcular_sesiones``
        # para usar ``created_at > _before_call`` como filtro preciso.
        # Esto evita pisar cualquier sesión que el admin haya
        # deshabilitado manualmente en el mismo rango de fechas
        # (escenario pastoral común: líder solicita bloqueo temporal
        # por duelo, etc.).
        sesiones_habilitadas = (
            db.query(SesionGrupo)
            .filter(
                SesionGrupo.grupo_id.in_([g.id for g in groups]),
                SesionGrupo.fecha_sesion >= fecha_inicio,
                SesionGrupo.fecha_sesion <= strat.fecha_fin,
                SesionGrupo.deleted_at.is_(None),
                SesionGrupo.created_at > _before_call,
            )
            .update(
                {SesionGrupo.estado_habilitacion: HabilitacionSesionEnum.HABILITADO.value},
                synchronize_session=False,
            )
        )
        db.commit()

    return {
        "strategy": strat.nombre,
        "recurrence": strat.frecuencia,
        "start": str(fecha_inicio),
        "end": str(strat.fecha_fin),
        "sessions_per_group": sessions_per_group,
        "groups": len(groups),
        "total_sessions_created": created,
        "sesiones_habilitadas": sesiones_habilitadas,
        "habilitar_inmediatamente": habilitar_inmediatamente,
    }


@estrategias_router.delete("/strategies/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_strategy(
    strategy_id: UUID,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_pastor_or_admin),
):
    if not delete_evangelism_strategy(db=db, strategy_id=strategy_id, actor_user_id=str(_user.id)):
        raise HTTPException(status_code=404, detail="Evangelism strategy not found")


def _project_phases_as_tasks(db, strategy_id: UUID, strategy_name: str, phases: list[dict], start_date=None):
    """Create N1 tasks in Projects module for each phase of a mass event."""
    from datetime import datetime as dt

    from backend.models_projects import Project, ProjectTask

    # Create a project linked to the strategy
    project = Project(
        title=f"[MASIVO] {strategy_name}",
        description=f"Evento masivo generado desde estrategia de evangelismo #{strategy_id}",
        status="active",
        created_at=dt.now(_tz.utc),
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
            sd = dt.fromisoformat(phase_start.replace("Z", "+00:00")) if phase_start else None
        except Exception:
            sd = None
        try:
            dd = dt.fromisoformat(phase_end.replace("Z", "+00:00")) if phase_end else None
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
            created_at=dt.now(_tz.utc),
        )
        db.add(task)

    db.commit()
    return project
