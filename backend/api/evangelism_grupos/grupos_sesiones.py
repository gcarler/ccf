from __future__ import annotations

import logging
from datetime import datetime as _datetime, timezone as _timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from backend import models, schemas
from backend.models import SesionGrupo, GrupoEvangelismo, Asistencia
from backend.models_evangelism import ParticipanteGrupo, SesionGrupo as SessionModel
from backend.api.evangelism_shared import (
    expected_group_rows,
    utc_now,
    _is_crm_admin_or_pastor,
    _get_persona_for_user,
)
from backend.core.permissions import get_current_user, require_pastor_or_admin
from backend.core.database import get_db
from backend.core.tenant import require_user_sede_id

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Sessions listing & creation ──


@router.get("/grupos/sessions")
@router.get("/faro/sessions")
def list_faro_sessions(
    season_id: Optional[int] = None,
    cell_group_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    user_sede = require_user_sede_id(db, current_user)
    query = db.query(SesionGrupo).options(
        joinedload(models.SesionGrupo.grupo),
    ).join(models.GrupoEvangelismo)
    if season_id:
        query = query.filter(models.SesionGrupo.season_id == season_id)
    if cell_group_id:
        query = query.filter(models.SesionGrupo.grupo_id == cell_group_id)
    query = query.filter(models.GrupoEvangelismo.sede_id == user_sede)
    sessions = query.order_by(models.SesionGrupo.fecha_sesion.desc()).all()

    # Single query: get attendance counts for all sessions at once
    if sessions:
        session_ids = [s.id for s in sessions]
        from sqlalchemy import func

        att_counts = dict(
            db.query(
                models.Asistencia.sesion_id,
                func.count(models.Asistencia.id),
            )
            .filter(models.Asistencia.sesion_id.in_(session_ids))
            .group_by(models.Asistencia.sesion_id)
            .all()
        )
    else:
        att_counts = {}

    return [
        {
            "id": session.id,
            "cell_group_id": session.grupo_id,
            "cell_group_name": (session.cell_group.name if session.cell_group else None),
            "season_id": session.season_id,
            "season_name": session.season.name if session.season else None,
            "session_date": session.session_date.isoformat(),
            "status": session.status,
            "attendance_count": att_counts.get(session.id, 0),
        }
        for session in sessions
    ]


@router.get("/grupos/sessions/mine/pending")
@router.get("/faro/sessions/mine/pending")
def list_my_pending_faro_sessions(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    house_ids: list[int]
    if _is_crm_admin_or_pastor(current_user):
        sede_id = require_user_sede_id(db, current_user)
        house_ids = [
            row[0] for row in
            db.query(models.GrupoEvangelismo.id)
            .filter(models.GrupoEvangelismo.sede_id == sede_id)
            .all()
        ]
    else:
        persona = _get_persona_for_user(db, current_user.id)
        if not persona:
            return []
        house_ids = [
            row[0]
            for row in db.query(models.GrupoEvangelismo.id)
            .filter(
                (models.GrupoEvangelismo.lider_persona_id == persona.id)
                | (models.GrupoEvangelismo.asistente_persona_id == persona.id)
            )
            .all()
        ]
    if not house_ids:
        return []

    sessions = (
        db.query(SesionGrupo)
        .options(
            joinedload(models.SesionGrupo.grupo),
            joinedload(models.SesionGrupo.season),
        )
        .filter(models.SesionGrupo.grupo_id.in_(house_ids))
        .order_by(models.SesionGrupo.fecha_sesion.desc())
        .limit(40)
        .all()
    )

    items = []

    # Single query: get attendance counts for all sessions at once
    if sessions:
        session_ids = [s.id for s in sessions]
        from sqlalchemy import func

        att_counts = dict(
            db.query(
                models.Asistencia.sesion_id,
                func.count(models.Asistencia.id),
            )
            .filter(models.Asistencia.sesion_id.in_(session_ids))
            .group_by(models.Asistencia.sesion_id)
            .all()
        )
    else:
        att_counts = {}

    for session in sessions:
        attendance_count = att_counts.get(session.id, 0)
        expected_count = len(expected_group_rows(db, session.grupo_id))
        needs_report = (
            session.status in {"Programada", "Pendiente", "No reportada"}
            or attendance_count == 0
            or not session.reported_at
        )
        if not needs_report:
            continue
        items.append(
            {
                "session_id": session.id,
                "cell_group_id": session.grupo_id,
                "cell_group_name": (session.cell_group.name if session.cell_group else None),
                "season_name": session.season.name if session.season else None,
                "session_date": (session.session_date.isoformat() if session.session_date else None),
                "status": session.status,
                "attendance_count": attendance_count,
                "expected_count": expected_count,
                "report_deadline": (session.report_deadline.isoformat() if session.report_deadline else None),
            }
        )
    return items


@router.post("/grupos/sessions", response_model=dict)
@router.post("/faro/sessions", response_model=dict)
def create_faro_session(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    try:
        from datetime import date as date_type

        session_date = date_type.fromisoformat(payload["session_date"])
    except (KeyError, ValueError):
        raise HTTPException(status_code=400, detail="Fecha de sesión requerida en formato YYYY-MM-DD")

    season_id = payload.get("season_id")
    cell_group_id = payload.get("cell_group_id") or payload.get("grupo_id")
    topic = payload.get("topic")
    report_deadline_str = payload.get("report_deadline")

    if not season_id or not cell_group_id:
        raise HTTPException(status_code=400, detail="Faltan datos: temporada y grupo son requeridos")
    user_sede = require_user_sede_id(db, current_user)

    season = db.query(models.CampaignSeason).filter(models.CampaignSeason.id == season_id).first()
    if not season:
        raise HTTPException(status_code=404, detail="Season not found")
    if season.start_date > session_date or season.end_date < session_date:
        raise HTTPException(
            status_code=400,
            detail=f"La fecha debe estar dentro de la temporada ({season.start_date} - {season.end_date})",
        )

    # Parse deadline if present
    report_deadline = None
    if report_deadline_str:
        from datetime import datetime

        try:
            report_deadline = datetime.fromisoformat(report_deadline_str.replace("Z", "+00:00"))
        except ValueError:
            logger.warning("report_deadline inválido: %s", report_deadline_str)
            pass

    # Gather houses
    houses_to_process = []
    if str(cell_group_id).lower() == "all":
        houses = db.query(GrupoEvangelismo).filter(
            models.GrupoEvangelismo.activo.is_(True),
            models.GrupoEvangelismo.sede_id == user_sede,
            models.GrupoEvangelismo.deleted_at.is_(None),
        ).all()
        houses_to_process = [h.id for h in houses]
    else:
        try:
            parsed_uuid = UUID(str(cell_group_id))
        except ValueError:
            raise HTTPException(status_code=400, detail="Identificador de grupo inválido")
        house = db.query(GrupoEvangelismo).filter(
            models.GrupoEvangelismo.id == parsed_uuid,
            models.GrupoEvangelismo.sede_id == user_sede,
            models.GrupoEvangelismo.deleted_at.is_(None),
        ).first()
        if not house:
            raise HTTPException(status_code=404, detail="Grupo no encontrado")
        houses_to_process = [house.id]

    from backend.models_evangelism import HabilitacionSesionEnum

    created_sessions = []
    for h_id in houses_to_process:
        existing = (
            db.query(SesionGrupo)
            .filter(
                models.SesionGrupo.grupo_id == h_id,
                models.SesionGrupo.fecha_sesion == session_date,
                models.SesionGrupo.deleted_at.is_(None),
            )
            .first()
        )
        if existing:
            if str(cell_group_id).lower() != "all":
                raise HTTPException(
                    status_code=400,
                    detail="Ya existe una sesion registrada para ese Faro en esa fecha",
                )
            continue  # In batch mode, we just skip existing

        session = models.SesionGrupo(
            cell_group_id=h_id,
            season_id=season_id,
            session_date=session_date,
            status="Realizada",
            estado_habilitacion=HabilitacionSesionEnum.HABILITADO.value,
            topic=topic,
            report_deadline=report_deadline,
        )
        db.add(session)
        created_sessions.append(session)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    for s in created_sessions:
        db.refresh(s)

    return {
        "message": f"Se crearon {len(created_sessions)} sesiones.",
        "created_count": len(created_sessions),
        "session_ids": [session.id for session in created_sessions],
    }


# ── Sessions & Attendance (standalone) ──


@router.get("/sessions", response_model=List[dict])
def list_sessions(
    strategy_id: Optional[str] = None,
    house_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """List sessions, optionally filtered by strategy or house."""

    user_sede = require_user_sede_id(db, current_user)
    q = db.query(SesionGrupo).join(
        models.GrupoEvangelismo,
        models.GrupoEvangelismo.id == models.SesionGrupo.grupo_id,
    ).filter(
        models.GrupoEvangelismo.sede_id == user_sede,
        models.GrupoEvangelismo.deleted_at.is_(None),
        models.SesionGrupo.deleted_at.is_(None),
    )
    if strategy_id:
        q = q.filter(GrupoEvangelismo.estrategia_id == strategy_id)
    if house_id:
        q = q.filter(models.SesionGrupo.grupo_id == house_id)
    rows = q.order_by(models.SesionGrupo.fecha_sesion.desc()).all()
    return [
        {
            "id": s.id,
            "grupo_id": s.cell_group_id,
            "session_date": s.session_date.isoformat() if s.session_date else None,
            "status": s.status or "Realizada",
            "estado_habilitacion": getattr(s, "estado_habilitacion", "DESHABILITADO"),
            "topic": s.topic,
            "offering_amount": float(s.offering_amount) if s.offering_amount else None,
            "report_notes": s.report_notes,
        }
        for s in rows
    ]


@router.post("/sessions", response_model=dict)
def create_session(
    data: schemas.SesionGrupoCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Create a new session."""

    cell_group_id = data.grupo_id
    if not cell_group_id:
        raise HTTPException(status_code=400, detail="grupo_id es requerido")
    user_sede = require_user_sede_id(db, current_user)
    group = (
        db.query(GrupoEvangelismo)
        .filter(
            GrupoEvangelismo.id == cell_group_id,
            GrupoEvangelismo.sede_id == user_sede,
            GrupoEvangelismo.deleted_at.is_(None),
        )
        .first()
    )
    if not group:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    db_session = SessionModel(
        cell_group_id=cell_group_id,
        season_id=data.season_id,
        session_date=data.session_date,
        topic=data.topic,
        offering_amount=data.offering_amount,
        report_notes=data.report_notes,
        novelty_type=data.novelty_type,
        novelty_detail=data.novelty_detail,
        cancellation_reason=data.cancellation_reason,
        reported_by_persona_id=data.reported_by_persona_id,
        reported_at=_datetime.now(_timezone.utc),
        status=data.status,
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return {
        "id": db_session.id,
        "grupo_id": db_session.grupo_id,
        "session_date": db_session.session_date.isoformat() if db_session.session_date else None,
        "status": db_session.status or "Realizada",
        "topic": db_session.topic,
        "offering_amount": float(db_session.offering_amount) if db_session.offering_amount else None,
        "report_notes": db_session.report_notes,
    }


@router.get("/sessions/{session_id}", response_model=dict)
def get_session_detail(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Get session with attendance records including member names."""
    from backend.models_crm import Persona

    session = (
        db.query(SesionGrupo)
        .options(joinedload(models.SesionGrupo.grupo))
        .join(models.GrupoEvangelismo, models.GrupoEvangelismo.id == models.SesionGrupo.grupo_id)
        .filter(models.SesionGrupo.id == session_id)
        .filter(models.GrupoEvangelismo.sede_id == require_user_sede_id(db, current_user))
        .filter(models.SesionGrupo.deleted_at.is_(None))
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    attendance_rows = db.query(Asistencia).filter(models.Asistencia.sesion_id == session_id).all()

    # Build persona name lookup for this session's cell_group
    persona_map: dict[str, str] = {}
    house_members = db.query(ParticipanteGrupo).filter(models.ParticipanteGrupo.grupo_id == session.grupo_id).all()
    for hm in house_members:
        p = db.query(Persona).filter(Persona.id == hm.persona_id).first()
        if p:
            persona_map[hm.persona_id] = p.nombre_completo

    attendance_list = []
    for a in attendance_rows:
        status = a.status if a.status else ("present" if a.attended else "absent")
        attendance_list.append(
            {
                "id": a.id,
                "session_id": a.session_id,
                "persona_id": a.persona_id,
                "persona_name": persona_map.get(a.persona_id, f"Persona {a.persona_id}"),
                "status": status,
                "notes": a.notes,
                "attended": a.attended,
            }
        )

    gh = session.cell_group
    return {
        "session": {
            "id": session.id,
            "cell_group_id": session.grupo_id,
            "session_date": session.session_date.isoformat() if session.session_date else None,
            "topic": session.topic,
            "offering_amount": float(session.offering_amount) if session.offering_amount else None,
            "status": session.status,
            "report_notes": session.report_notes,
        },
        "attendance": attendance_list,
        "cell_group": {
            "id": gh.id,
            "name": gh.name,
            "leader_name": gh.leader_name,
        }
        if gh
        else None,
    }


@router.put("/sessions/{session_id}", response_model=dict)
def update_session(
    session_id: int,
    update: schemas.SesionGrupoUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Update session."""

    db_session = (
        db.query(SessionModel)
        .join(models.GrupoEvangelismo, models.GrupoEvangelismo.id == SessionModel.grupo_id)
        .filter(SessionModel.id == session_id)
        .filter(models.GrupoEvangelismo.sede_id == require_user_sede_id(db, current_user))
        .filter(SessionModel.deleted_at.is_(None))
        .first()
    )
    if not db_session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_session, key, value)

    db_session.reported_at = _datetime.now(_timezone.utc)
    db.commit()
    db.refresh(db_session)
    return db_session


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Cancela una sesion (soft-delete: marca como CANCELADA)."""

    db_session = (
        db.query(SesionGrupo)
        .join(models.GrupoEvangelismo, models.GrupoEvangelismo.id == models.SesionGrupo.grupo_id)
        .filter(models.SesionGrupo.id == session_id)
        .filter(models.GrupoEvangelismo.sede_id == require_user_sede_id(db, current_user))
        .filter(models.SesionGrupo.deleted_at.is_(None))
        .first()
    )
    if not db_session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    # Soft-delete: marcar como cancelada en lugar de borrar
    from backend.models_evangelism import EstadoSesionEnum
    db_session.status = EstadoSesionEnum.CANCELADA.value
    db_session.deleted_at = utc_now()
    db.commit()
    return {"ok": True, "status": "cancelada"}


# ── GOBERNANZA DE SESIONES (Habilitacion / Bloqueo) ─────────────────────────


@router.patch("/sessions/{session_id}/habilitacion", response_model=dict)
def toggle_session_habilitacion(
    session_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Admin: habilita o deshabilita manualmente una sesion para recibir reportes."""
    from backend.models_evangelism import HabilitacionSesionEnum

    session = (
        db.query(SesionGrupo)
        .join(models.GrupoEvangelismo, models.GrupoEvangelismo.id == SesionGrupo.grupo_id)
        .filter(SesionGrupo.id == session_id)
        .filter(models.GrupoEvangelismo.sede_id == require_user_sede_id(db, current_user))
        .filter(SesionGrupo.deleted_at.is_(None))
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada o no pertenece a tu sede")

    accion = payload.get("accion", "").upper()
    if accion not in ("HABILITAR", "DESHABILITAR", "CERRAR"):
        raise HTTPException(status_code=400, detail="accion debe ser HABILITAR, DESHABILITAR o CERRAR")

    nuevo_estado = {
        "HABILITAR": HabilitacionSesionEnum.HABILITADO.value,
        "DESHABILITAR": HabilitacionSesionEnum.DESHABILITADO.value,
        "CERRAR": HabilitacionSesionEnum.CERRADO.value,
    }[accion]

    # Resolver persona del usuario actual
    persona = _get_persona_for_user(db, current_user.id)

    session.estado_habilitacion = nuevo_estado
    session.habilitado_por = persona.id if persona else None
    session.habilitado_en = utc_now()
    db.commit()
    db.refresh(session)

    return {
        "session_id": session_id,
        "estado_habilitacion": session.estado_habilitacion,
        "habilitado_en": session.habilitado_en.isoformat() if session.habilitado_en else None,
    }


@router.post("/strategies/{strategy_id}/habilitar-todas", response_model=dict)
def habilitar_todas_sesiones(
    strategy_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Admin: habilita todas las sesiones de una estrategia de un golpe."""
    from backend.models_evangelism import HabilitacionSesionEnum, GrupoEvangelismo

    grupos = db.query(GrupoEvangelismo).filter(
        GrupoEvangelismo.estrategia_id == strategy_id,
        GrupoEvangelismo.sede_id == require_user_sede_id(db, current_user),
        GrupoEvangelismo.deleted_at.is_(None),
    ).all()
    grupo_ids = [g.id for g in grupos]
    if not grupo_ids:
        raise HTTPException(status_code=404, detail="Estrategia sin grupos")

    persona = _get_persona_for_user(db, current_user.id)

    updated = db.query(SesionGrupo).filter(
        SesionGrupo.grupo_id.in_(grupo_ids),
        SesionGrupo.deleted_at.is_(None),
    ).update({
        "estado_habilitacion": HabilitacionSesionEnum.HABILITADO.value,
        "habilitado_por": persona.id if persona else None,
        "habilitado_en": utc_now(),
    }, synchronize_session=False)
    db.commit()

    return {"strategy_id": strategy_id, "sesiones_habilitadas": updated}


@router.post("/strategies/{strategy_id}/deshabilitar-todas", response_model=dict)
def deshabilitar_todas_sesiones(
    strategy_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Admin: bloquea todas las sesiones de una estrategia."""
    from backend.models_evangelism import HabilitacionSesionEnum, GrupoEvangelismo

    grupos = db.query(GrupoEvangelismo).filter(
        GrupoEvangelismo.estrategia_id == strategy_id,
        GrupoEvangelismo.sede_id == require_user_sede_id(db, current_user),
        GrupoEvangelismo.deleted_at.is_(None),
    ).all()
    grupo_ids = [g.id for g in grupos]
    if not grupo_ids:
        raise HTTPException(status_code=404, detail="Estrategia sin grupos")

    updated = db.query(SesionGrupo).filter(
        SesionGrupo.grupo_id.in_(grupo_ids),
        SesionGrupo.deleted_at.is_(None),
    ).update({
        "estado_habilitacion": HabilitacionSesionEnum.DESHABILITADO.value,
    }, synchronize_session=False)
    db.commit()

    return {"strategy_id": strategy_id, "sesiones_deshabilitadas": updated}
