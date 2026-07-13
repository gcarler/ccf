from __future__ import annotations

import logging
from datetime import datetime as _datetime
from datetime import timezone as _timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from backend import models, schemas
from backend.api.evangelism_shared import (
    _get_persona_for_user,
    _is_crm_admin_or_pastor,
    _sessions_grupo_live_column_names,
    expected_group_rows,
    session_estado_habilitacion,
    session_read_only_options,
    session_read_value,
    sessions_grupo_has_estado_habilitacion,
    utc_now,
)
from backend.core.database import get_db
from backend.core.permissions import get_current_user, require_pastor_or_admin
from backend.core.tenant import require_user_sede_id
from backend.models import Asistencia, GrupoEvangelismo, SesionGrupo
from backend.models_evangelism import ParticipanteGrupo
from backend.models_evangelism import SesionGrupo as SessionModel

logger = logging.getLogger(__name__)

router = APIRouter()
static_router = APIRouter()
dynamic_router = APIRouter()

def _session_read_options(db: Session):
    return session_read_only_options(db)


# ── Sessions listing & creation ──


@static_router.get("/grupos/sessions")
@static_router.get("/groups/sessions")
def list_groups_sessions(
    season_id: Optional[UUID] = None,
    grupo_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    user_sede = require_user_sede_id(db, current_user)
    query = db.query(SesionGrupo).options(
        _session_read_options(db),
        joinedload(models.SesionGrupo.grupo),
    ).join(models.GrupoEvangelismo)
    if season_id:
        query = query.filter(models.SesionGrupo.season_id == season_id)
    if grupo_id:
        query = query.filter(models.SesionGrupo.grupo_id == grupo_id)
    query = query.filter(
        models.GrupoEvangelismo.sede_id == user_sede,
        models.GrupoEvangelismo.deleted_at.is_(None),
        models.SesionGrupo.deleted_at.is_(None),
    )
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
            .filter(
                models.Asistencia.sesion_id.in_(session_ids),
                models.Asistencia.deleted_at.is_(None),
            )
            .group_by(models.Asistencia.sesion_id)
            .all()
        )
    else:
        att_counts = {}

    return [
        {
            "id": str(session.id),
            "grupo_id": str(session.grupo_id) if session.grupo_id else None,
            "grupo_name": (session.grupo.name if session.grupo else None),
            "season_id": str(session.season_id) if session.season_id else None,
            "season_name": session.season.name if session.season else None,
            "session_date": session.session_date.isoformat(),
            "status": session.status,
            "attendance_count": att_counts.get(session.id, 0),
        }
        for session in sessions
    ]


@static_router.get("/grupos/sessions/mine/pending")
@static_router.get("/groups/sessions/mine/pending")
def list_my_pending_groups_sessions(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    house_ids: list[int]
    if _is_crm_admin_or_pastor(current_user):
        sede_id = require_user_sede_id(db, current_user)
        house_ids = [
            row[0] for row in
            db.query(models.GrupoEvangelismo.id)
            .filter(
                models.GrupoEvangelismo.sede_id == sede_id,
                models.GrupoEvangelismo.deleted_at.is_(None),
            )
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
                models.GrupoEvangelismo.deleted_at.is_(None),
                (models.GrupoEvangelismo.lider_persona_id == persona.id)
                | (models.GrupoEvangelismo.asistente_persona_id == persona.id)
            )
            .all()
        ]
    if not house_ids:
        return []

    # NOTE: ``SesionGrupo.season`` is a Python ``@property`` placeholder that
    # returns ``None`` — it is NOT a SQLAlchemy ``relationship()`` so
    # ``joinedload(SesionGrupo.season)`` raises
    # ``expected ORM mapped attribute for loader strategy argument``.
    # We omit that joinedload and batch-fetch CampaignSeason rows instead.
    sessions = (
        db.query(SesionGrupo)
        .options(_session_read_options(db))
        .options(joinedload(models.SesionGrupo.grupo))
        .filter(
            models.SesionGrupo.grupo_id.in_(house_ids),
            models.SesionGrupo.deleted_at.is_(None),
        )
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
            .filter(
                models.Asistencia.sesion_id.in_(session_ids),
                models.Asistencia.deleted_at.is_(None),
            )
            .group_by(models.Asistencia.sesion_id)
            .all()
        )

        # Batch-fetch season names referenced by these sessions (avoiding N+1).
        season_ids = list({s.season_id for s in sessions if s.season_id is not None})
        season_map: dict = {}
        if season_ids:
            season_map = {
                row.id: row.name
                for row in db.query(models.CampaignSeason)
                .filter(models.CampaignSeason.id.in_(season_ids))
                .all()
            }
    else:
        att_counts = {}
        season_map = {}

    for session in sessions:
        attendance_count = att_counts.get(session.id, 0)
        expected_count = len(expected_group_rows(db, session.grupo_id))
        needs_report = (
            session.status in {"Programada", "Pendiente", "No reportada"}
            or attendance_count == 0
            or not session_read_value(session, "reported_at")
        )
        if not needs_report:
            continue
        items.append(
            {
                "session_id": str(session.id) if session.id else None,
                "grupo_id": str(session.grupo_id) if session.grupo_id else None,
                "grupo_name": (session.grupo.name if session.grupo else None),
                "season_name": season_map.get(session.season_id),
                "session_date": (session.session_date.isoformat() if session.session_date else None),
                "status": session.status,
                "attendance_count": attendance_count,
                "expected_count": expected_count,
                "report_deadline": (
                    session_read_value(session, "report_deadline").isoformat()
                    if session_read_value(session, "report_deadline")
                    else None
                ),
            }
        )
    return items


@static_router.post("/grupos/sessions", response_model=dict)
@static_router.post("/groups/sessions", response_model=dict)
def create_groups_session(
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
    grupo_id = payload.get("grupo_id")
    topic = payload.get("topic")
    report_deadline_str = payload.get("report_deadline")

    if not season_id or not grupo_id:
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
    if str(grupo_id).lower() == "all":
        houses = db.query(GrupoEvangelismo).filter(
            models.GrupoEvangelismo.activo.is_(True),
            models.GrupoEvangelismo.sede_id == user_sede,
            models.GrupoEvangelismo.deleted_at.is_(None),
        ).all()
        houses_to_process = [h.id for h in houses]
    else:
        try:
            parsed_uuid = UUID(str(grupo_id))
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
        from sqlalchemy import func
        existing = (
            db.query(SesionGrupo)
            .options(_session_read_options(db))
            .filter(
                models.SesionGrupo.grupo_id == h_id,
                func.date(models.SesionGrupo.fecha_sesion) == session_date,
                models.SesionGrupo.deleted_at.is_(None),
            )
            .first()
        )
        if existing:
            if str(grupo_id).lower() != "all":
                raise HTTPException(
                    status_code=400,
                    detail="Ya existe una sesion registrada para ese Grupo en esa fecha",
                )
            continue  # In batch mode, we just skip existing

        session_kwargs = dict(
            grupo_id=h_id,
            season_id=season_id,
            session_date=session_date,
            status="Realizada",
            topic=topic,
            report_deadline=report_deadline,
        )
        if sessions_grupo_has_estado_habilitacion(db):
            session_kwargs["estado_habilitacion"] = HabilitacionSesionEnum.HABILITADO.value
        session = models.SesionGrupo(**session_kwargs)
        db.add(session)
        created_sessions.append(session)

    try:
        db.commit()
    except Exception:
        logger.exception("Failed to commit group sessions creation")
        db.rollback()
        raise

    return {
        "message": f"Se crearon {len(created_sessions)} sesiones.",
        "created_count": len(created_sessions),
        "session_ids": [session.id for session in created_sessions],
    }


# ── Sessions & Attendance (standalone) ──


@static_router.get("/sessions", response_model=List[dict])
def list_sessions(
    strategy_id: Optional[UUID] = None,
    house_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """List sessions, optionally filtered by strategy or house."""

    user_sede = require_user_sede_id(db, current_user)
    q = db.query(SesionGrupo).options(_session_read_options(db)).join(
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
            "grupo_id": s.grupo_id,
            "session_date": s.session_date.isoformat() if s.session_date else None,
            "status": s.status or "Realizada",
            "estado_habilitacion": session_estado_habilitacion(s),
            "topic": s.topic,
            "offering_amount": float(s.offering_amount) if s.offering_amount else None,
            "report_notes": s.report_notes,
            "novelty_type": session_read_value(s, "novelty_type"),
            "novelty_detail": session_read_value(s, "novelty_detail"),
            "reported_by_persona_id": (
                str(session_read_value(s, "reported_by_persona_id"))
                if session_read_value(s, "reported_by_persona_id")
                else None
            ),
            "report_deadline": (
                session_read_value(s, "report_deadline").isoformat()
                if session_read_value(s, "report_deadline")
                else None
            ),
        }
        for s in rows
    ]


@static_router.post("/sessions", response_model=dict)
def create_session(
    data: schemas.SesionGrupoCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Create a new session."""

    grupo_id = data.grupo_id
    if not grupo_id:
        raise HTTPException(status_code=400, detail="grupo_id es requerido")
    user_sede = require_user_sede_id(db, current_user)
    group = (
        db.query(GrupoEvangelismo)
        .filter(
            GrupoEvangelismo.id == grupo_id,
            GrupoEvangelismo.sede_id == user_sede,
            GrupoEvangelismo.deleted_at.is_(None),
        )
        .first()
    )
    if not group:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    live_columns = _sessions_grupo_live_column_names(db)
    session_kwargs = dict(
        grupo_id=grupo_id,
        season_id=data.season_id,
        session_date=data.session_date,
        topic=data.topic,
        offering_amount=data.offering_amount,
        report_notes=data.report_notes,
        cancellation_reason=data.cancellation_reason,
        status=data.status,
    )
    if "novelty_type" in live_columns:
        session_kwargs["novelty_type"] = data.novelty_type
    if "novelty_detail" in live_columns:
        session_kwargs["novelty_detail"] = data.novelty_detail
    if "reported_by_persona_id" in live_columns:
        session_kwargs["reported_by_persona_id"] = data.reported_by_persona_id
    if "reported_at" in live_columns:
        session_kwargs["reported_at"] = _datetime.now(_timezone.utc)
    db_session = SessionModel(
        **session_kwargs,
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


@dynamic_router.get("/sessions/{session_id}", response_model=dict)
def get_session_detail(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Get session with attendance records including persona names."""
    from backend.models_crm import Persona

    session = (
        db.query(SesionGrupo)
        .options(_session_read_options(db))
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

    # Build persona name lookup for this session's grupo
    persona_map: dict[str, str] = {}
    house_personas = db.query(ParticipanteGrupo).filter(models.ParticipanteGrupo.grupo_id == session.grupo_id).all()
    for hm in house_personas:
        p = db.query(Persona).filter(Persona.id == hm.persona_id).first()
        if p:
            persona_map[hm.persona_id] = p.nombre_completo

    attendance_list = []
    for a in attendance_rows:
        status = a.status if a.status else ("present" if a.attended else "absent")
        attendance_list.append(
            {
                "id": a.id,
                "session_id": str(a.sesion_id),
                "persona_id": a.persona_id,
                "persona_name": persona_map.get(a.persona_id, f"Persona {a.persona_id}"),
                "status": status,
                "notes": a.notes,
                "attended": a.attended,
            }
        )

    gh = session.grupo
    return {
        "session": {
            "id": session.id,
            "grupo_id": session.grupo_id,
            "session_date": session.session_date.isoformat() if session.session_date else None,
            "topic": session.topic,
            "offering_amount": float(session.offering_amount) if session.offering_amount else None,
            "status": session.status,
            "report_notes": session.report_notes,
            "novelty_type": session_read_value(session, "novelty_type"),
            "novelty_detail": session_read_value(session, "novelty_detail"),
            "reported_by_persona_id": (
                str(session_read_value(session, "reported_by_persona_id"))
                if session_read_value(session, "reported_by_persona_id")
                else None
            ),
            "report_deadline": (
                session_read_value(session, "report_deadline").isoformat()
                if session_read_value(session, "report_deadline")
                else None
            ),
        },
        "attendance": attendance_list,
        "grupo": {
            "id": gh.id,
            "name": gh.name,
            "leader_name": gh.leader_name,
        }
        if gh
        else None,
    }


@dynamic_router.put("/sessions/{session_id}", response_model=schemas.SesionGrupoResponse)
def update_session(
    session_id: UUID,
    update: schemas.SesionGrupoUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Update session."""

    db_session = (
        db.query(SessionModel)
        .options(_session_read_options(db))
        .join(models.GrupoEvangelismo, models.GrupoEvangelismo.id == SessionModel.grupo_id)
        .filter(SessionModel.id == session_id)
        .filter(models.GrupoEvangelismo.sede_id == require_user_sede_id(db, current_user))
        .filter(SessionModel.deleted_at.is_(None))
        .first()
    )
    if not db_session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    update_data = update.model_dump(exclude_unset=True)
    live_columns = _sessions_grupo_live_column_names(db)
    for key, value in update_data.items():
        if key not in live_columns:
            continue
        setattr(db_session, key, value)

    if "reported_at" in live_columns:
        db_session.reported_at = _datetime.now(_timezone.utc)
    db.commit()
    # Serializar via SesionGrupoResponse (antes dict manual). El validador
    # ``_coerce_uuid_to_str`` garantiza que ``id`` y ``grupo_id`` se
    # expongan como string en el JSON — preserva el contrato con el
    # frontend (que espera ``session_id`` y ``grupo_id`` como string).
    return schemas.SesionGrupoResponse.model_validate(db_session)


@dynamic_router.delete("/sessions/{session_id}")
def delete_session(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Cancela una sesion (soft-delete: marca como CANCELADA)."""

    db_session = (
        db.query(SesionGrupo)
        .options(_session_read_options(db))
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


@dynamic_router.patch("/sessions/{session_id}/habilitacion", response_model=dict)
def toggle_session_habilitacion(
    session_id: UUID,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Admin: habilita o deshabilita manualmente una sesion para recibir reportes."""
    from backend.models_evangelism import HabilitacionSesionEnum

    session = (
        db.query(SesionGrupo)
        .options(_session_read_options(db))
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
    habilitado_en = utc_now()

    if sessions_grupo_has_estado_habilitacion(db):
        session.estado_habilitacion = nuevo_estado
        session.habilitado_por = persona.id if persona else None
        session.habilitado_en = habilitado_en
        db.commit()

    return {
        "session_id": session_id,
        "estado_habilitacion": nuevo_estado,
        "habilitado_en": habilitado_en.isoformat(),
    }


@dynamic_router.post("/strategies/{strategy_id}/habilitar-todas", response_model=dict)
def habilitar_todas_sesiones(
    strategy_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Admin: habilita todas las sesiones de una estrategia de un golpe."""
    from backend.models_evangelism import GrupoEvangelismo, HabilitacionSesionEnum

    grupos = db.query(GrupoEvangelismo).filter(
        GrupoEvangelismo.estrategia_id == strategy_id,
        GrupoEvangelismo.sede_id == require_user_sede_id(db, current_user),
        GrupoEvangelismo.deleted_at.is_(None),
    ).all()
    grupo_ids = [g.id for g in grupos]
    if not grupo_ids:
        raise HTTPException(status_code=404, detail="Estrategia sin grupos")

    persona = _get_persona_for_user(db, current_user.id)

    if not sessions_grupo_has_estado_habilitacion(db):
        return {"strategy_id": strategy_id, "sesiones_habilitadas": 0}

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


@dynamic_router.post("/strategies/{strategy_id}/deshabilitar-todas", response_model=dict)
def deshabilitar_todas_sesiones(
    strategy_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Admin: bloquea todas las sesiones de una estrategia."""
    from backend.models_evangelism import GrupoEvangelismo, HabilitacionSesionEnum

    grupos = db.query(GrupoEvangelismo).filter(
        GrupoEvangelismo.estrategia_id == strategy_id,
        GrupoEvangelismo.sede_id == require_user_sede_id(db, current_user),
        GrupoEvangelismo.deleted_at.is_(None),
    ).all()
    grupo_ids = [g.id for g in grupos]
    if not grupo_ids:
        raise HTTPException(status_code=404, detail="Estrategia sin grupos")

    if not sessions_grupo_has_estado_habilitacion(db):
        return {"strategy_id": strategy_id, "sesiones_deshabilitadas": 0}

    updated = db.query(SesionGrupo).filter(
        SesionGrupo.grupo_id.in_(grupo_ids),
        SesionGrupo.deleted_at.is_(None),
    ).update({
        "estado_habilitacion": HabilitacionSesionEnum.DESHABILITADO.value,
    }, synchronize_session=False)
    db.commit()

    return {"strategy_id": strategy_id, "sesiones_deshabilitadas": updated}


# Strategy D: el include_router(static_router/dynamic_router) está
# al FINAL del archivo (después de R2 /personas/search) para que
# TODAS las rutas estáticas —incluyendo las definidas luego— sean
# registradas antes del mount. Moverlo aquí antes causa 404 en
# FastAPI para las rutas posteriores.


# ─────────────────────────────────────────────────────
# R2 — Riesgo residual audit: búsqueda remota de personas
# ─────────────────────────────────────────────────────
# El formulario de registrar asistencia de un Grupo en Casa pre-carga
# los participantes del grupo (esperados) pero NO permite buscar
# visitantes/contactos fuera del grupo. Para volumen alto, conviene
# una búsqueda remota con debounce desde el campo de texto del frontend.
# Este endpoint es consumido por ``groups/[id]/page.tsx`` vía
# ``apiFetch('/evangelism/personas/search', { params })`` con AbortController.


@static_router.get("/personas/search", response_model=dict)
def search_personas_for_attendance(
    q: str = "",
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Búsqueda remota con debounce de personas para el formulario de asistencia.

    Args:
        q: texto de búsqueda (mínimo 3 caracteres para evitar storm).
        limit: tope razonable (default 10).

    Returns:
        ``{"results": [{id, nombre_completo, church_role, phone, email}, ...]}``
        filtrado por la sede del usuario actual y por el texto.
    """
    lowered_query = (q or "").strip().lower()
    if len(lowered_query) < 3:
        return {"results": []}

    # Limit defensivo para no pegar a la DB completa.
    bounded_limit = max(1, min(int(limit or 10), 25))
    user_sede = require_user_sede_id(db, current_user)

    # ``Persona`` no tiene columna ``deleted_at`` (su borrado se gestiona
    # vía ``soft_delete`` con otro mecanismo), así que filtramos solo
    # por sede. Si en el futuro se agrega ``deleted_at`` a ``Persona``
    # este filtro debe re-introducirse.
    rows = (
        db.query(models.Persona)
        .filter(models.Persona.sede_id == user_sede)
        .order_by(models.Persona.nombre_completo.asc())
        .all()
    )

    def _matches(persona) -> bool:
        haystack = " ".join(
            [
                str(getattr(persona, "nombre_completo", "") or ""),
                str(getattr(persona, "first_name", "") or ""),
                str(getattr(persona, "last_name", "") or ""),
                str(getattr(persona, "email", "") or ""),
                str(getattr(persona, "phone", "") or ""),
                str(getattr(persona, "documento", "") or ""),
                str(getattr(persona, "church_role", "") or ""),
            ]
        ).lower()
        return lowered_query in haystack

    return {
        "results": [
            {
                "id": str(p.id),
                "nombre_completo": p.nombre_completo,
                "church_role": getattr(p, "church_role_effective", "") or getattr(p, "church_role", "") or "Miembro",
                "phone": getattr(p, "phone", "") or "",
                "email": getattr(p, "email", "") or "",
            }
            for p in rows
            if _matches(p)
        ][:bounded_limit]
    }


# Strategy D: static routes BEFORE dynamic ones (avoid FastAPI shadow matching).
# CRÍTICO: este include_router debe estar al FINAL del archivo para que
# las rutas definidas luego (ej. R2 /personas/search) sean registradas.
# FastAPI ``include_router`` solo monta las rutas que existen en el
# sub-router en el momento de la llamada.
router.include_router(static_router)
router.include_router(dynamic_router)
