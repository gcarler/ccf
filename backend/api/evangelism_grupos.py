from __future__ import annotations

import collections
from datetime import datetime as _datetime, timezone as _timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from backend import crud, models, schemas
from backend.models import SesionGrupo, GrupoEvangelismo, Asistencia
from backend.models_evangelism import ParticipanteGrupo, SesionGrupo as SessionModel
from backend.api.evangelism_shared import expected_group_rows, member_payload, utc_now
from backend.auth import get_current_user, normalize_role, require_active_user, require_pastor_or_admin
from backend.core.database import get_db

router = APIRouter()


def _is_crm_admin_or_pastor(user: models.User) -> bool:
    role = normalize_role(str(getattr(user, "role", "")))
    if not role and hasattr(user, "rol_plataforma") and user.rol_plataforma:
        role = normalize_role(user.rol_plataforma.nombre)
    return role in {"admin", "administrador", "pastor"}


def _get_persona_for_user(db: Session, user_id) -> Optional[models.Persona]:
    import uuid as _uuid

    # UUID-based user (v3): persona.id == user.id
    if isinstance(user_id, _uuid.UUID) or (isinstance(user_id, str) and "-" in str(user_id)):
        try:
            uid = _uuid.UUID(str(user_id))
            return db.query(models.Persona).filter(models.Persona.id == uid).first()
        except (ValueError, AttributeError):
            pass
    # Integer user (legacy): persona.user_id == user.id
    return db.query(models.Persona).filter(models.Persona.user_id == user_id).first()


def _can_manage_grupo(db: Session, user: models.User, house) -> bool:
    if _is_crm_admin_or_pastor(user):
        return True
    persona = _get_persona_for_user(db, user.id)
    if not persona:
        return False
    return persona.id in {house.leader_persona_id, house.assistant_persona_id}


@router.get("/grupos", response_model=List[dict])
@router.get("/faro", response_model=List[dict])
def list_cell_groups(
    estrategia_id: Optional[str] = None,
    sede_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    q = db.query(GrupoEvangelismo)
    if estrategia_id:
        q = q.filter(GrupoEvangelismo.estrategia_id == estrategia_id)
    if sede_id is not None:
        q = q.filter(GrupoEvangelismo.sede_id == sede_id)
    groups = q.order_by(GrupoEvangelismo.nombre.asc()).all()
    return [
        {
            "id": g.id,
            "name": g.nombre,
            "zone": g.ubicacion,
            "address": g.direccion,
            "leader_name": g.lider.nombre_completo if g.lider else "",
            "leader_id": str(g.lider_persona_id) if g.lider_persona_id else None,
            "assistant_id": str(g.asistente_persona_id) if g.asistente_persona_id else None,
            "host_id": str(g.anfitrion_persona_id) if g.anfitrion_persona_id else None,
            "members_count": len(g.participantes) if g.participantes else 0,
            "capacity": g.capacidad,
            "day_of_week": g.dia_reunion,
            "start_time": g.hora_reunion,
            "status": "Activo" if g.activo else "Inactivo",
            "evangelism_strategy_id": str(g.estrategia_id) if g.estrategia_id else None,
        }
        for g in groups
    ]


@router.get("/grupos/mine", response_model=List[dict])
@router.get("/faro/mine", response_model=List[dict])
def list_my_cell_groups(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if _is_crm_admin_or_pastor(current_user):
        return crud.get_cell_groups(db)
    persona = _get_persona_for_user(db, current_user.id)
    if not persona:
        return []
    return (
        db.query(GrupoEvangelismo)
        .filter(
            (models.GrupoEvangelismo.lider_persona_id == persona.id)
            | (models.GrupoEvangelismo.asistente_persona_id == persona.id)
        )
        .order_by(models.GrupoEvangelismo.nombre.asc())
        .all()
    )


@router.get("/grupos/assignment-summary", response_model=dict)
@router.get("/faro/assignment-summary", response_model=dict)
def get_faro_assignment_summary(
    sede_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    q = db.query(GrupoEvangelismo).order_by(models.GrupoEvangelismo.nombre.asc())
    if sede_id is not None:
        q = q.filter(models.GrupoEvangelismo.sede_id == sede_id)
    houses = q.all()
    personas = db.query(models.Persona).all()
    assigned_persona_ids = {
        row[0] for row in db.query(models.ParticipanteGrupo.persona_id).distinct().all() if row and row[0] is not None
    }
    for house in houses:
        for pid in [house.leader_persona_id, house.assistant_persona_id, house.host_persona_id]:
            if pid:
                assigned_persona_ids.add(pid)

    houses_with_leader = [house for house in houses if house.leader_persona_id]
    houses_without_leader = [house for house in houses if not house.leader_persona_id]
    houses_with_assistant = [house for house in houses if house.assistant_persona_id]
    houses_without_assistant = [house for house in houses if not house.assistant_persona_id]
    houses_with_host = [house for house in houses if house.host_persona_id]
    houses_without_host = [house for house in houses if not house.host_persona_id]
    houses_with_members = [house for house in houses if (house.members_count or 0) > 0]
    houses_without_members = [house for house in houses if (house.members_count or 0) == 0]

    unassigned_personas = [
        {
            "id": p.id,
            "name": p.nombre_completo,
            "church_role": p.church_role,
        }
        for p in personas
        if p.id not in assigned_persona_ids
    ]

    return {
        "houses_total": len(houses),
        "houses_with_leader": len(houses_with_leader),
        "houses_without_leader": len(houses_without_leader),
        "houses_with_assistant": len(houses_with_assistant),
        "houses_without_assistant": len(houses_without_assistant),
        "houses_with_host": len(houses_with_host),
        "houses_without_host": len(houses_without_host),
        "houses_with_members": len(houses_with_members),
        "houses_without_members": len(houses_without_members),
        "personas_total": len(personas),
        "personas_unassigned": len(unassigned_personas),
        "houses_needing_leader": [
            {
                "id": house.id,
                "name": house.name,
                "code": house.code,
                "zone": house.zone,
                "address": house.address,
            }
            for house in houses_without_leader
        ],
        "houses_needing_assistant": [
            {
                "id": house.id,
                "name": house.name,
                "code": house.code,
                "zone": house.zone,
                "address": house.address,
            }
            for house in houses_without_assistant
        ],
        "houses_needing_host": [
            {
                "id": house.id,
                "name": house.name,
                "code": house.code,
                "zone": house.zone,
                "address": house.address,
            }
            for house in houses_without_host
        ],
        "unassigned_personas": unassigned_personas[:100],
    }


@router.get("/grupos/{grupo_id}", response_model=dict)
@router.get("/faro/{grupo_id}", response_model=dict)
@router.get("/micro/{grupo_id}", response_model=dict)
def get_cell_group(
    grupo_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    from backend.models_evangelism import GrupoEvangelismo, SesionGrupo, Asistencia

    house = db.query(GrupoEvangelismo).filter(GrupoEvangelismo.id == grupo_id).first()
    if not house:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    if not _can_manage_grupo(db, current_user, house):
        raise HTTPException(status_code=403, detail="No autorizado para este grupo")

    base_rows = (
        db.query(models.ParticipanteGrupo, models.Persona)
        .join(models.Persona, models.Persona.id == models.ParticipanteGrupo.persona_id)
        .filter(models.ParticipanteGrupo.grupo_id == grupo_id)
        .order_by(models.Persona.nombre_completo.asc())
        .all()
    )
    base_attendees = [
        {
            "persona_id": str(persona.id),
            "name": persona.nombre_completo,
            "role": row.role or "miembro",
            "church_role": persona.church_role,
            "phone": persona.telefono,
        }
        for row, persona in base_rows
    ]
    base_attendee_ids = [item["persona_id"] for item in base_attendees]

    sessions = (
        db.query(SesionGrupo)
        .filter(models.SesionGrupo.grupo_id == grupo_id)
        .order_by(models.SesionGrupo.fecha_sesion.desc())
        .limit(20)
        .all()
    )

    expected_count = len(base_attendees)
    absence_counter = collections.Counter()
    absence_details: dict[int, list[dict]] = collections.defaultdict(list)
    attendance_by_session = collections.defaultdict(list)

    if sessions:
        from sqlalchemy import func as sqlfunc

        session_ids = [session.id for session in sessions]
        attendance_rows = db.query(Asistencia).filter(models.Asistencia.sesion_id.in_(session_ids)).all()
        for row in attendance_rows:
            attendance_by_session[row.session_id].append(row)
            if not row.attended and row.persona_id:
                absence_counter[row.persona_id] += 1
                absence_details[row.persona_id].append(
                    {
                        "session_id": row.session_id,
                        "session_date": None,
                        "reason": row.absence_reason,
                        "reason_detail": row.absence_reason_detail,
                    }
                )
        attendance_counts = (
            db.query(
                models.Asistencia.sesion_id,
                sqlfunc.count(models.Asistencia.id).label("cnt"),
            )
            .filter(models.Asistencia.sesion_id.in_(session_ids))
            .group_by(models.Asistencia.sesion_id)
            .all()
        )
        attendance_map = {row.session_id: row.cnt for row in attendance_counts}
    else:
        attendance_map = {}

    sessions_data = [
        {
            "id": session.id,
            "grupo_id": session.grupo_id,
            "session_date": session.session_date.isoformat(),
            "status": session.status,
            "attendance_count": attendance_map.get(session.id, 0),
            "present_count": sum(1 for row in attendance_by_session.get(session.id, []) if row.attended),
            "absent_count": sum(1 for row in attendance_by_session.get(session.id, []) if not row.attended),
            "attendance_rate": (
                round(
                    (
                        sum(1 for row in attendance_by_session.get(session.id, []) if row.attended)
                        / max(expected_count, 1)
                    )
                    * 100,
                    1,
                )
                if expected_count
                else 0
            ),
            "topic": session.topic,
            "report_deadline": None,
            "offering_amount": (float(session.offering_amount) if session.offering_amount is not None else None),
            "novelty_type": session.novelty_type,
            "novelty_detail": session.novelty_detail,
            "cancellation_reason": session.cancellation_reason,
        }
        for session in sessions
    ]

    monitoring_sessions = sessions_data[:8]
    monitoring_rates = [
        session["attendance_rate"] for session in monitoring_sessions if session["attendance_rate"] is not None
    ]
    monitoring_average_rate = round(sum(monitoring_rates) / len(monitoring_rates), 1) if monitoring_rates else 0
    monitoring_average_presence = (
        round(sum(session["present_count"] for session in monitoring_sessions) / len(monitoring_sessions))
        if monitoring_sessions
        else 0
    )
    attendance_trend = [
        {
            "session_id": session["id"],
            "session_date": session["session_date"],
            "status": session["status"],
            "attendance_rate": session["attendance_rate"],
            "present_count": session["present_count"],
            "absent_count": session["absent_count"],
        }
        for session in monitoring_sessions
    ]

    repeat_absentees = []
    for persona_id, count in absence_counter.items():
        if count >= 2:
            p = db.query(models.Persona).filter(models.Persona.id == persona_id).first()
            repeat_absentees.append(
                {
                    "persona_id": persona_id,
                    "name": p.nombre_completo if p else "Persona",
                    "absences": count,
                    "details": absence_details.get(persona_id, []),
                }
            )

    alerts = []
    if sessions_data:
        last_session = sessions_data[0]
        if last_session["status"] in {"Cancelada", "No realizada"}:
            alerts.append(
                {
                    "type": "session_status",
                    "message": f"La última sesión está marcada como {last_session['status'].lower()}.",
                    "session_id": last_session["id"],
                }
            )
    if repeat_absentees:
        alerts.append(
            {
                "type": "repeat_absence",
                "message": f"{len(repeat_absentees)} persona(s) acumulan ausencias recurrentes.",
            }
        )

    return {
        "id": house.id,
        "code": house.code,
        "name": house.name,
        "zone": house.zone,
        "address": house.address,
        "latitude": float(house.latitude) if house.latitude else None,
        "longitude": float(house.longitude) if house.longitude else None,
        "leader_name": house.leader_name,
        "leader_id": house.leader_persona_id,
        "assistant_id": house.assistant_persona_id,
        "host_id": house.host_persona_id,
        "base_attendee_ids": base_attendee_ids,
        "base_attendees": base_attendees,
        "members_count": house.members_count,
        "capacity": house.capacity,
        "day_of_week": house.day_of_week,
        "start_time": house.start_time,
        "end_time": house.end_time,
        "status": house.status,
        "created_at": house.created_at.isoformat() if house.created_at else None,
        "sessions": sessions_data,
        "total_sessions": len(sessions_data),
        "total_attendance": sum(session["attendance_count"] for session in sessions_data),
        "monitoring": {
            "expected_members": expected_count,
            "average_attendance": monitoring_average_presence,
            "average_attendance_rate": monitoring_average_rate,
            "attendance_trend": attendance_trend,
            "recent_sessions": [
                {
                    "session_id": session["id"],
                    "session_date": session["session_date"],
                    "status": session["status"],
                    "present_count": session["present_count"],
                    "absent_count": session["absent_count"],
                    "attendance_rate": session["attendance_rate"],
                    "topic": session["topic"],
                    "offering_amount": session["offering_amount"],
                    "novelty_type": session["novelty_type"],
                }
                for session in monitoring_sessions
            ],
            "repeat_absentees": repeat_absentees,
            "alerts": alerts,
        },
    }


@router.post("/grupos", response_model=dict)
@router.post("/faro", response_model=dict)
def create_cell_group(
    payload: schemas.GrupoEvangelismoCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    obj = crud.create_cell_group(db, payload)
    return {
        "id": obj.id,
        "code": obj.codigo,
        "name": obj.nombre,
        "zone": obj.ubicacion,
        "address": obj.direccion,
        "capacity": obj.capacidad,
        "day_of_week": obj.dia_reunion,
        "start_time": obj.hora_reunion,
        "leader_id": str(obj.lider_persona_id) if obj.lider_persona_id else None,
        "assistant_id": str(obj.asistente_persona_id) if obj.asistente_persona_id else None,
        "host_id": str(obj.anfitrion_persona_id) if obj.anfitrion_persona_id else None,
        "status": "Activo" if obj.activo else "Inactivo",
        "members_count": len(obj.participantes) if obj.participantes else 0,
        "evangelism_strategy_id": str(obj.estrategia_id) if obj.estrategia_id else None,
    }


@router.put("/grupos/{grupo_id}", response_model=dict)
@router.put("/faro/{grupo_id}", response_model=dict)
def update_cell_group(
    grupo_id: int,
    payload: schemas.GrupoEvangelismoUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    house_db = db.query(GrupoEvangelismo).filter(models.GrupoEvangelismo.id == grupo_id).first()
    if not house_db:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    if not _can_manage_grupo(db, current_user, house_db):
        raise HTTPException(status_code=403, detail="No autorizado para este grupo")
    if not _is_crm_admin_or_pastor(current_user):
        allowed_fields = {"base_attendee_ids", "base_attendees_with_roles"}
        incoming_fields = set(payload.model_dump(exclude_unset=True).keys())
        if not incoming_fields:
            raise HTTPException(status_code=400, detail="No hay campos para actualizar")
        if not incoming_fields.issubset(allowed_fields):
            raise HTTPException(
                status_code=403,
                detail="Lideres y colideres solo pueden gestionar asistentes del grupo",
            )
    house = crud.update_cell_group(db, grupo_id, payload)
    if not house:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    return {"id": house.id, "name": house.name, "members_count": house.members_count}


@router.delete("/grupos/{grupo_id}", status_code=204)
@router.delete("/faro/{grupo_id}", status_code=204)
def delete_cell_group(
    grupo_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Desactiva un grupo de evangelismo (soft-delete)."""
    house = db.query(GrupoEvangelismo).filter(GrupoEvangelismo.id == grupo_id).first()
    if not house:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    house.activo = False
    db.commit()
    return None


@router.get("/grupos/seasons")
@router.get("/faro/seasons")
def list_campaign_seasons(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    seasons = db.query(models.CampaignSeason).order_by(models.CampaignSeason.start_date.desc()).all()
    return [
        {
            "id": season.id,
            "name": season.name,
            "start_date": season.start_date.isoformat(),
            "end_date": season.end_date.isoformat(),
            "periodicity": season.periodicity,
            "status": season.status,
            "created_at": season.created_at.isoformat() if season.created_at else None,
        }
        for season in seasons
    ]


@router.post("/grupos/seasons", response_model=dict)
@router.post("/faro/seasons", response_model=dict)
def create_campaign_season(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    name = str(payload.get("name", "")).strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    try:
        from datetime import date as date_type

        start = date_type.fromisoformat(payload["start_date"])
        end = date_type.fromisoformat(payload["end_date"])
    except (KeyError, ValueError):
        raise HTTPException(
            status_code=400,
            detail="start_date and end_date required in YYYY-MM-DD format",
        )
    if end <= start:
        raise HTTPException(status_code=400, detail="end_date must be after start_date")

    season = models.CampaignSeason(
        name=name,
        start_date=start,
        end_date=end,
        periodicity=payload.get("periodicity", "SEMANAL"),
        status="Activa",
    )
    db.add(season)
    db.commit()
    db.refresh(season)
    return {"id": season.id, "name": season.name, "status": season.status}


@router.patch("/grupos/seasons/{season_id}", response_model=dict)
@router.patch("/faro/seasons/{season_id}", response_model=dict)
def update_campaign_season(
    season_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    season = db.query(models.CampaignSeason).filter(models.CampaignSeason.id == season_id).first()
    if not season:
        raise HTTPException(status_code=404, detail="Season not found")
    for field in ["name", "status", "periodicity"]:
        if field in payload:
            setattr(season, field, payload[field])
    db.commit()
    return {"id": season.id, "name": season.name, "status": season.status}


@router.get("/grupos/sessions")
@router.get("/faro/sessions")
def list_faro_sessions(
    season_id: Optional[int] = None,
    cell_group_id: Optional[int] = None,
    sede_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    query = db.query(SesionGrupo).options(
        joinedload(models.SesionGrupo.grupo),
    )
    if season_id:
        query = query.filter(models.SesionGrupo.season_id == season_id)
    if cell_group_id:
        query = query.filter(models.SesionGrupo.grupo_id == cell_group_id)
    if sede_id is not None:
        query = query.join(models.GrupoEvangelismo).filter(models.GrupoEvangelismo.sede_id == sede_id)
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
        house_ids = [row[0] for row in db.query(models.GrupoEvangelismo.id).all()]
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
        raise HTTPException(status_code=400, detail="session_date required in YYYY-MM-DD format")

    season_id = payload.get("season_id")
    cell_group_id = payload.get("cell_group_id")
    topic = payload.get("topic")
    report_deadline_str = payload.get("report_deadline")

    if not season_id or not cell_group_id:
        raise HTTPException(status_code=400, detail="season_id and cell_group_id required")

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
            pass

    # Gather houses
    houses_to_process = []
    if str(cell_group_id).lower() == "all":
        houses = db.query(GrupoEvangelismo).filter(models.GrupoEvangelismo.activo.is_(True)).all()
        houses_to_process = [h.id for h in houses]
    else:
        houses_to_process = [int(cell_group_id)]

    created_sessions = []
    for h_id in houses_to_process:
        existing = (
            db.query(SesionGrupo)
            .filter(
                models.SesionGrupo.grupo_id == h_id,
                models.SesionGrupo.season_id == season_id,
                models.SesionGrupo.fecha_sesion == session_date,
            )
            .first()
        )
        if existing:
            if str(cell_group_id).lower() != "all":
                raise HTTPException(
                    status_code=400,
                    detail="Ya existe una sesión registrada para ese Faro en esa fecha",
                )
            continue  # In batch mode, we just skip existing

        session = models.SesionGrupo(
            cell_group_id=h_id,
            season_id=season_id,
            session_date=session_date,
            status="Realizada",
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
    }


@router.get("/grupos/sessions/{session_id}/attendance")
@router.get("/faro/sessions/{session_id}/attendance")
def get_faro_session_attendance(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    session = db.query(SesionGrupo).filter(models.SesionGrupo.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    house = db.query(GrupoEvangelismo).filter(models.GrupoEvangelismo.id == session.grupo_id).first()
    if not house:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    if not _can_manage_grupo(db, current_user, house):
        raise HTTPException(status_code=403, detail="No autorizado para este grupo")

    attendances = (
        db.query(Asistencia)
        .filter(models.Asistencia.sesion_id == session_id)
        .options(joinedload(models.Asistencia.persona))
        .all()
    )

    expected_rows = expected_group_rows(db, session.grupo_id)
    attendance_map = {attendance.persona_id: attendance for attendance in attendances}
    present = []
    absent = []
    expected_members = []
    for _, member in expected_rows:
        attendance = attendance_map.get(member.id)
        attended = (
            bool(
                attendance.attended
                if hasattr(attendance, "attended")
                else (attendance.estado == "ASISTIO" if attendance else False)
            )
            if attendance
            else False
        )
        payload = member_payload(
            member,
            attended=attended,
            scanned_at=getattr(attendance, "scanned_at", None) if attendance else None,
            absence_reason=getattr(attendance, "absence_reason", None) if attendance else None,
            absence_reason_detail=(
                getattr(attendance, "absence_reason_detail", None) or getattr(attendance, "detalle_excusa", None)
            )
            if attendance
            else None,
            estado=attendance.estado if attendance else None,
            es_primera_vez=attendance.es_primera_vez if attendance else False,
        )
        expected_members.append(payload)
        if attended:
            present.append(payload)
        else:
            absent.append(payload)

    return {
        "session_id": session_id,
        "session_date": session.session_date.isoformat(),
        "cell_group_id": session.grupo_id,
        "status": session.status,
        "topic": session.topic,
        "offering_amount": (float(session.offering_amount) if session.offering_amount is not None else None),
        "report_notes": session.report_notes,
        "novelty_type": session.novelty_type,
        "novelty_detail": session.novelty_detail,
        "cancellation_reason": session.cancellation_reason,
        "reported_by_persona_id": session.reported_by_persona_id,
        "total": len(present),
        "present_count": len(present),
        "absent_count": len(absent),
        "attendees": present,
        "absentees": absent,
        "expected_members": expected_members,
    }


@router.post("/grupos/sessions/{session_id}/attendance", response_model=dict)
@router.post("/faro/sessions/{session_id}/attendance", response_model=dict)
def add_faro_attendance(
    session_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    member_ids = payload.get("persona_ids") or payload.get("member_ids", [])
    attendees = payload.get("attendees")

    session = db.query(SesionGrupo).filter(models.SesionGrupo.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    house = db.query(GrupoEvangelismo).filter(models.GrupoEvangelismo.id == session.grupo_id).first()
    if not house:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    if not _can_manage_grupo(db, current_user, house):
        raise HTTPException(status_code=403, detail="No autorizado para este grupo")

    from datetime import datetime, timezone

    if session.report_deadline:
        current_time = datetime.now(timezone.utc)
        deadline = session.report_deadline
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        if current_time > deadline:
            raise HTTPException(
                status_code=403,
                detail="El plazo para reportar asistencia en esta sesión ha vencido.",
            )

    import uuid

    if attendees and not isinstance(attendees, list):
        raise HTTPException(status_code=400, detail="attendees must be a list")

    if attendees:
        processed = 0
        for item in attendees:
            member_id = item.get("persona_id") or item.get("member_id")
            if not member_id:
                continue
            if isinstance(member_id, str):
                try:
                    member_id = uuid.UUID(member_id)
                except ValueError:
                    raise HTTPException(status_code=400, detail=f"ID de miembro inválido: {member_id}")
            attended = bool(item.get("attended", True))
            absence_reason = item.get("absence_reason")
            absence_reason_detail = item.get("absence_reason_detail")

            if not attended and not absence_reason:
                raise HTTPException(
                    status_code=400,
                    detail=f"Razón de ausencia requerida para el miembro {member_id}.",
                )

            row = (
                db.query(Asistencia)
                .filter(
                    models.Asistencia.sesion_id == session_id,
                    models.Asistencia.persona_id == member_id,
                )
                .first()
            )
            if row:
                row.attended = attended
                row.absence_reason = absence_reason
                row.absence_reason_detail = absence_reason_detail
                row.scanned_at = utc_now() if attended else row.scanned_at
            else:
                db.add(
                    Asistencia(
                        session_id=session_id,
                        persona_id=member_id,
                        attended=attended,
                        absence_reason=absence_reason,
                        absence_reason_detail=absence_reason_detail,
                    )
                )
            processed += 1
    else:
        if not member_ids:
            raise HTTPException(status_code=400, detail="member_ids or attendees is required")
        processed = 0
        for member_id in member_ids:
            if isinstance(member_id, str):
                try:
                    member_id = uuid.UUID(member_id)
                except ValueError:
                    raise HTTPException(status_code=400, detail=f"ID de miembro inválido: {member_id}")
            exists = (
                db.query(Asistencia)
                .filter(
                    models.Asistencia.sesion_id == session_id,
                    models.Asistencia.persona_id == member_id,
                )
                .first()
            )
            if not exists:
                db.add(Asistencia(session_id=session_id, persona_id=member_id, attended=True))
                processed += 1

    new_status = payload.get("status", session.status)
    new_cancellation_reason = payload.get("cancellation_reason", session.cancellation_reason)

    if new_status in ["Cancelada", "No realizada"] and not new_cancellation_reason:
        raise HTTPException(
            status_code=400,
            detail=f"Motivo de cancelación es requerido cuando el estado es {new_status}.",
        )

    new_offering_amount = payload.get("offering_amount", session.offering_amount)
    if new_offering_amount is not None and float(new_offering_amount) < 0:
        raise HTTPException(status_code=400, detail="La ofrenda no puede ser un valor negativo.")

    session.topic = payload.get("topic", session.topic)
    session.offering_amount = new_offering_amount
    session.report_notes = payload.get("report_notes", session.report_notes)
    session.novelty_type = payload.get("novelty_type", session.novelty_type)
    session.novelty_detail = payload.get("novelty_detail", session.novelty_detail)
    session.cancellation_reason = new_cancellation_reason
    session.status = new_status
    session.reported_by_persona_id = payload.get("reported_by_persona_id", session.reported_by_persona_id)
    session.reported_at = utc_now()

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"status": "success", "processed": processed, "session_id": session_id}


@router.get("/grupos/analytics")
@router.get("/faro/analytics")
def get_faro_analytics(
    season_id: Optional[int] = None,
    sede_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    from sqlalchemy import func

    query = db.query(
        models.SesionGrupo.grupo_id,
        models.SesionGrupo.season_id,
        func.count(models.Asistencia.id).label("total_attendance"),
        func.count(models.SesionGrupo.id.distinct()).label("total_sessions"),
    ).join(
        models.Asistencia,
        models.Asistencia.sesion_id == models.SesionGrupo.id,
        isouter=True,
    )
    if season_id:
        query = query.filter(models.SesionGrupo.season_id == season_id)
    if sede_id is not None:
        query = query.join(models.GrupoEvangelismo).filter(models.GrupoEvangelismo.sede_id == sede_id)

    rows = query.group_by(models.SesionGrupo.grupo_id, models.SesionGrupo.season_id).all()
    total_attendance = sum(row.total_attendance or 0 for row in rows)
    total_sessions = sum(row.total_sessions or 0 for row in rows)
    active_faros = len({row.grupo_id for row in rows})

    return {
        "total_attendance": total_attendance,
        "total_sessions": total_sessions,
        "active_faros": active_faros,
        "avg_per_session": (round(total_attendance / total_sessions) if total_sessions > 0 else 0),
        "per_faro": [
            {
                "cell_group_id": row.grupo_id,
                "total_attendance": row.total_attendance or 0,
                "total_sessions": row.total_sessions or 0,
                "avg": (round((row.total_attendance or 0) / row.total_sessions) if row.total_sessions else 0),
            }
            for row in rows
        ],
    }


@router.get("/macro/despliegue", response_model=dict)
def get_macro_despliegue(
    season_id: Optional[int] = None,
    sede_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    from sqlalchemy import func

    # 1. Determine active season if not provided
    if not season_id:
        active_season = (
            db.query(models.CampaignSeason)
            .filter(models.CampaignSeason.status == "Activa")
            .order_by(models.CampaignSeason.id.desc())
            .first()
        )
        if active_season:
            season_id = active_season.id
            season_name = active_season.name
        else:
            return {
                "season": "No hay temporada activa",
                "total_houses": 0,
                "despliegue": [],
            }
    else:
        season = db.query(models.CampaignSeason).filter(models.CampaignSeason.id == season_id).first()
        season_name = season.name if season else f"Temporada {season_id}"

    # 2. Get all active houses
    q = db.query(GrupoEvangelismo).filter(models.GrupoEvangelismo.activo.is_(True))
    if sede_id is not None:
        q = q.filter(models.GrupoEvangelismo.sede_id == sede_id)
    houses = q.order_by(models.GrupoEvangelismo.nombre.asc()).all()

    # 3. Get all sessions for the season
    sessions = db.query(SesionGrupo).filter(models.SesionGrupo.season_id == season_id).all()

    # Group sessions by house
    sessions_by_house = collections.defaultdict(list)
    for s in sessions:
        sessions_by_house[s.cell_group_id].append(s)

    # Get attendance counts per session
    attendance_counts = (
        db.query(
            models.Asistencia.sesion_id,
            func.count(models.Asistencia.id).label("cnt"),
        )
        .group_by(models.Asistencia.sesion_id)
        .all()
    )
    att_map = {row.session_id: row.cnt for row in attendance_counts}

    # 4. Build the dense JSON
    despliegue = []
    for house in houses:
        house_sessions = sorted(sessions_by_house.get(house.id, []), key=lambda x: x.session_date)
        matrix = []
        for idx, s in enumerate(house_sessions):
            matrix.append(
                {
                    "week": idx + 1,
                    "status": s.status,
                    "date": s.session_date.isoformat(),
                    "attendance": att_map.get(s.id, 0),
                    "reason": s.cancellation_reason,
                }
            )

        realizadas = sum(1 for m in matrix if m["status"] == "Realizada")
        total = len(matrix)
        compliance_rate = round((realizadas / total) * 100, 1) if total > 0 else 0

        despliegue.append(
            {
                "house_id": house.id,
                "code": house.code,
                "name": house.name,
                "expected_day": house.day_of_week,
                "leader_name": house.leader_name,
                "compliance_matrix": matrix,
                "compliance_rate": compliance_rate,
            }
        )

    return {
        "season": season_name,
        "total_houses": len(houses),
        "despliegue": despliegue,
    }


# ── FARO Visitor Registration (new guests from session reports) ──


class FaroVisitorCreate(BaseModel):
    first_name: str
    last_name: str
    phone: Optional[str] = None
    cell_group_id: int
    session_id: Optional[int] = None


@router.post("/grupos/visitors", response_model=dict)
@router.post("/faro/visitors", response_model=dict)
def register_faro_visitor(
    visitor: FaroVisitorCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    """Register a new guest from a Faro session report as a Persona + CRM lead."""
    # Verificar que usuario es líder/asistente del grupo
    house = db.query(GrupoEvangelismo).filter(models.GrupoEvangelismo.id == visitor.cell_group_id).first()
    if not house:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")

    persona = _get_persona_for_user(db, current_user.id)
    if persona and persona.id not in {house.leader_persona_id, house.assistant_persona_id, house.host_persona_id}:
        raise HTTPException(status_code=403, detail="Solo el líder o asistente puede registrar visitantes")

    # Find existing persona by phone
    existing = None
    if visitor.phone:
        existing = db.query(models.Persona).filter(models.Persona.telefono == visitor.phone).first()

    if existing:
        return {"status": "duplicate", "persona_id": existing.id}

    # Create new persona
    new_persona = models.Persona(
        nombre_completo=f"{visitor.first_name} {visitor.last_name}".strip(),
        telefono=visitor.phone,
        church_role="Visitante Faro",
    )
    db.add(new_persona)
    db.commit()
    db.refresh(new_persona)

    # Vincular al grupo
    db.add(
        models.ParticipanteGrupo(
            cell_group_id=visitor.cell_group_id,
            persona_id=new_persona.id,
            role="visitante",
        )
    )

    # CRM follow-up (v2 — CasoCRM replaces ConsolidationCase)
    case = models.CasoCRM(
        persona_id=new_persona.id,
        sede_id=new_persona.sede_id,
        pipeline_id=1,  # default pipeline
        etapa_actual_id=1,  # default first stage
        titulo_caso=f"Seguimiento: {new_persona.first_name} {new_persona.last_name}",
        origen_canal="evangelismo",
        estado="ABIERTO",
    )
    db.add(case)

    db.commit()

    return {"status": "created", "persona_id": new_persona.id}


# ── Sessions & Attendance ──


@router.get("/sessions", response_model=List[dict])
def list_sessions(
    strategy_id: Optional[str] = None,
    house_id: Optional[int] = None,
    sede_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """List sessions, optionally filtered by strategy, house or sede."""

    q = db.query(SesionGrupo)
    if strategy_id:
        q = q.join(models.GrupoEvangelismo, models.GrupoEvangelismo.id == models.SesionGrupo.grupo_id).filter(
            GrupoEvangelismo.estrategia_id == strategy_id
        )
    if house_id:
        q = q.filter(models.SesionGrupo.grupo_id == house_id)
    if sede_id is not None:
        q = q.join(models.GrupoEvangelismo, models.GrupoEvangelismo.id == models.SesionGrupo.grupo_id).filter(
            GrupoEvangelismo.sede_id == sede_id
        )
    rows = q.order_by(models.SesionGrupo.fecha_sesion.desc()).all()
    return [
        {
            "id": s.id,
            "grupo_id": s.cell_group_id,
            "session_date": s.session_date.isoformat() if s.session_date else None,
            "status": s.status or "Realizada",
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
    from backend.models_personas import Persona

    session = (
        db.query(SesionGrupo)
        .options(joinedload(models.SesionGrupo.grupo))
        .filter(models.SesionGrupo.id == session_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

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

    db_session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")

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
    """Cancela una sesión (soft-delete: marca como CANCELADA)."""

    db_session = db.query(SesionGrupo).filter(models.SesionGrupo.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Soft-delete: marcar como cancelada en lugar de borrar
    db_session.status = "Cancelada"
    db.session.commit()  # noqa — commit correcto
    return {"ok": True, "status": "cancelada"}


# ── Attendance ──


@router.post("/sessions/{session_id}/attendance", response_model=dict)
def submit_attendance(
    session_id: int,
    attendance_data: List[schemas.AsistenciaGrupoCreate],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Submit attendance for a session. Checks automation triggers."""

    session = db.query(SesionGrupo).filter(models.SesionGrupo.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Soft-delete existing attendance for this session
    db.query(Asistencia).filter(Asistencia.sesion_id == session_id).update(
        {Asistencia.deleted_at: utc_now()}, synchronize_session=False
    )

    submitted = []
    for att in attendance_data:
        # Map schema fields (status/notes) to model fields
        absence_reason_detail = None
        if att.status == "absent":
            absence_reason_detail = att.notes

        # Mapear estado nuevo (EstadoAsistenciaEnum)
        nuevo_estado = "presente"
        if att.status == "absent":
            nuevo_estado = "ausente"
        elif att.status == "first_time":
            nuevo_estado = "primera_vez"

        import uuid as _uuid

        persona_uuid = att.persona_id
        if isinstance(persona_uuid, str):
            persona_uuid = _uuid.UUID(persona_uuid)

        db_att = Asistencia(
            session_id=session_id,
            persona_id=persona_uuid,
            detalle_excusa=absence_reason_detail,
            estado=nuevo_estado,
            es_primera_vez=(att.status == "first_time"),
        )
        db.add(db_att)
        submitted.append(db_att)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    for att in submitted:
        db.refresh(att)

    # ── Automation triggers ──
    _check_absence_trigger(db, session_id)
    _check_first_time_lead_trigger(db, session_id)

    # ── CRM Bridge: first-time / seguimiento ──
    from backend.services.evangelism_crm_bridge import crear_caso_desde_asistencia
    from backend.models_personas import Persona

    evento = None
    for att in submitted:
        if att.es_primera_vez or att.requiere_seguimiento:
            persona = db.query(Persona).filter(Persona.id == att.persona_id).first()
            if not persona:
                continue
            grupo = session.grupo
            if not grupo:
                continue
            sede_id = grupo.sede_id
            if not sede_id:
                continue
            caso = crear_caso_desde_asistencia(db, att, persona, grupo, session, sede_id)
            if caso:
                estrategia = grupo.estrategia
                tags_nuevos = [
                    f"VISITANTE_ESTRATEGIA_{estrategia.id}" if estrategia else "VISITANTE_ESTRATEGIA_NONE",
                    f"GRUPO_{grupo.nombre}",
                    f"SESION_{session.fecha_sesion.date().isoformat()}"
                    if session.fecha_sesion
                    else f"SESION_{session.id}",
                ]
                persona.tags = list(set((persona.tags or []) + tags_nuevos))
                if estrategia:
                    persona.origen_estrategia_id = estrategia.id
                persona.origen_grupo_id = grupo.id
                persona.origen_fecha = _datetime.now(_timezone.utc)
                persona.spiritual_status = "VISITANTE_EVANGELISMO"
                db.commit()
                db.refresh(persona)
                db.refresh(caso)

                evento = {
                    "origen_modulo": "EVANGELISMO",
                    "grupo_id": str(grupo.id),
                    "sesion_id": str(session.id),
                    "visitante_kernel": {
                        "persona_id": str(persona.id),
                        "nombre": f"{persona.first_name} {persona.last_name}",
                        "rol_iglesia": persona.spiritual_status,
                        "tags_aplicados": persona.tags,
                    },
                    "crm_consolidacion": {
                        "caso_id": str(caso.id),
                        "pipeline": "NUEVOS_VISITANTES",
                        "etapa_inicial": caso.etapa_actual.nombre if caso.etapa_actual else "NUEVO_CONTACTO",
                        "SLA_limite_horas": 48,
                        "sla_deadline": caso.sla_vencimiento_contacto.isoformat()
                        if caso.sla_vencimiento_contacto
                        else None,
                    },
                }
                break

    return {
        "evento_integracion": evento,
        "metadata": {
            "engine": "Mesh CCF",
            "trazabilidad": "AUTOMATIC_EVENT_TRIGGER_SUCCESS",
        },
    }


def _check_absence_trigger(db: Session, session_id: int):
    """If a member has 3 consecutive absences, create N2 task in Consolidation."""
    from backend.models import (
        Asistencia,
        SesionGrupo,
        GrupoEvangelismo,
    )
    from backend.models_personas import Persona

    session = db.query(SesionGrupo).filter(SesionGrupo.id == session_id).first()
    if not session:
        return

    house = db.query(GrupoEvangelismo).filter(GrupoEvangelismo.id == session.grupo_id).first()
    if not house:
        return

    # Get last 3 sessions for this house
    recent_sessions = (
        db.query(SesionGrupo)
        .filter(SesionGrupo.grupo_id == house.id)
        .order_by(SesionGrupo.fecha_sesion.desc())
        .limit(3)
        .all()
    )

    if len(recent_sessions) < 3:
        return  # Not enough data

    # Check attendance for each member in base attendees
    for base_member in house.base_attendees or []:
        member_id = base_member.persona_id
        absent_count = 0
        for s in recent_sessions:
            att = (
                db.query(Asistencia)
                .filter(
                    Asistencia.sesion_id == s.id,
                    Asistencia.persona_id == member_id,
                    Asistencia.estado == "ausente",
                )
                .first()
            )
            if att:
                absent_count += 1

        if absent_count >= 3:
            # Create N2 task in Consolidation
            p = db.query(Persona).filter(Persona.id == member_id).first()
            if not p:
                continue
            from backend.models_crm import SupportTicket

            ticket = SupportTicket(
                persona_id=member_id,
                ticket_type="consolidation",
                title=f"Inasistencia recurrente: {p.nombre_completo}",
                description=f"{p.nombre_completo} ha faltado 3 sesiones consecutivas en {house.name}. Requiere contacto pastoral.",
                status="open",
                priority="high",
                severity="N2",
            )
            db.add(ticket)
            db.commit()


def _check_first_time_lead_trigger(db: Session, session_id: int):
    """If a first_time attendee is recorded, mark as LEAD_NUEVO in CRM."""
    from backend.models_personas import Persona
    from backend.models_evangelism import Asistencia

    first_timers = (
        db.query(Asistencia)
        .filter(
            Asistencia.sesion_id == session_id,
            Asistencia.estado == "primera_vez",
        )
        .all()
    )

    for att in first_timers:
        p = db.query(Persona).filter(Persona.id == att.persona_id).first()
        if p and str(getattr(p, "church_role", "")).lower() not in ("lead", "lead_nuevo"):
            try:
                p.church_role = "lead_nuevo"
                db.commit()
            except Exception:
                pass


# ── Dashboard Metrics ──


@router.get("/strategies/{strategy_id}/metrics", response_model=dict)
def get_strategy_metrics(
    strategy_id: int,
    weeks: int = 12,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Weekly metrics for a strategy: attendance, absences, first-timers, groups."""
    from backend.models import (
        SesionGrupo,
        Asistencia,
        GrupoEvangelismo,
    )
    from datetime import timedelta

    # Get all houses for this strategy
    strategy_ref = str(strategy_id)
    houses = db.query(GrupoEvangelismo).filter(GrupoEvangelismo.estrategia_id == strategy_ref).all()
    house_ids = [h.id for h in houses]

    if not house_ids:
        return {
            "strategy_id": strategy_id,
            "weekly": [],
            "summary": {
                "total_groups": 0,
                "total_sessions": 0,
                "avg_attendance": 0,
                "total_first_timers": 0,
                "total_absences": 0,
            },
        }

    cutoff = _datetime.now(_timezone.utc) - timedelta(weeks=weeks)

    sessions = (
        db.query(SesionGrupo)
        .filter(
            models.SesionGrupo.grupo_id.in_(house_ids),
            models.SesionGrupo.fecha_sesion >= cutoff.date(),
        )
        .order_by(models.SesionGrupo.fecha_sesion)
        .all()
    )

    if not sessions:
        return {
            "strategy_id": strategy_id,
            "weekly": [],
            "summary": {
                "total_groups": len(houses),
                "total_sessions": 0,
                "avg_attendance": 0,
                "total_first_timers": 0,
                "total_absences": 0,
            },
        }

    session_ids = [s.id for s in sessions]

    # Single query: load ALL attendance for all sessions at once
    all_attendance = db.query(Asistencia).filter(models.Asistencia.sesion_id.in_(session_ids)).all()

    # Group attendance by session_id in memory
    att_by_session = collections.defaultdict(list)
    for a in all_attendance:
        att_by_session[a.session_id].append(a)

    weekly = collections.defaultdict(
        lambda: {
            "present": 0,
            "absent": 0,
            "first_time": 0,
            "sessions": 0,
            "offering": 0.0,
        }
    )

    for s in sessions:
        week_key = s.session_date.strftime("%Y-%m-%d")
        weekly[week_key]["sessions"] += 1

        if s.offering_amount:
            weekly[week_key]["offering"] += float(s.offering_amount)

        for a in att_by_session.get(s.id, []):
            # Map model fields: attended (bool), absence_reason
            if a.attended:
                weekly[week_key]["present"] += 1
            elif a.absence_reason:
                weekly[week_key]["absent"] += 1

    weekly_list = []
    total_present = 0
    total_absent = 0
    total_first = 0

    for week_key in sorted(weekly.keys()):
        data = weekly[week_key]
        total_present += data["present"]
        total_absent += data["absent"]
        total_first += data["first_time"]
        total_att = data["present"] + data["absent"]
        weekly_list.append(
            {
                "week": week_key,
                **data,
                "attendance_rate": round(data["present"] / total_att * 100, 1) if total_att > 0 else 0,
            }
        )

    return {
        "strategy_id": strategy_id,
        "weekly": weekly_list,
        "summary": {
            "total_groups": len(houses),
            "total_sessions": len(sessions),
            "avg_attendance": round(total_present / len(sessions), 1) if sessions else 0,
            "total_first_timers": total_first,
            "total_absences": total_absent,
        },
    }


# ──────────────────────────────────────────────
# SEGUIMIENTO (FOLLOW-UP)
# ──────────────────────────────────────────────


@router.get("/follow-up/pending", response_model=List[schemas.RegistroSeguimientoResponse])
def list_pending_follow_ups(
    limit: int = 50,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_pastor_or_admin),
):
    """Lista todos los seguimientos pendientes (no completados)."""
    from backend.crud.evangelism import get_pendientes_seguimiento

    return get_pendientes_seguimiento(db, limit=limit)


@router.get("/follow-up/{asistencia_id}", response_model=List[schemas.RegistroSeguimientoResponse])
def list_seguimientos_for_attendance(
    asistencia_id: int,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_pastor_or_admin),
):
    """Lista los seguimientos de una asistencia."""
    from backend.crud.evangelism import get_seguimientos

    return get_seguimientos(db, asistencia_id)


@router.post("/follow-up/{asistencia_id}", response_model=schemas.RegistroSeguimientoResponse)
def create_seguimiento(
    asistencia_id: int,
    payload: schemas.RegistroSeguimientoCreate,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_pastor_or_admin),
):
    """Crea un registro de seguimiento para una asistencia."""
    from backend.crud.evangelism import create_seguimiento

    asistencia = db.query(Asistencia).filter(models.Asistencia.id == asistencia_id).first()
    if not asistencia:
        raise HTTPException(status_code=404, detail="Asistencia no encontrada")

    payload.asistencia_id = asistencia_id
    return create_seguimiento(db, payload)


@router.patch("/follow-up/{seguimiento_id}", response_model=schemas.RegistroSeguimientoResponse)
def update_seguimiento(
    seguimiento_id: int,
    payload: schemas.RegistroSeguimientoUpdate,
    db: Session = Depends(get_db),
    _user: models.User = Depends(require_pastor_or_admin),
):
    """Actualiza un seguimiento (marcar completado, agregar resultado, etc.)."""
    from backend.crud.evangelism import update_seguimiento

    result = update_seguimiento(db, seguimiento_id, payload)
    if not result:
        raise HTTPException(status_code=404, detail="Seguimiento no encontrado")
    return result
