from __future__ import annotations

import collections
import uuid as _uuid_mod
from datetime import datetime as _datetime, timezone as _timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.models import SesionGrupo, GrupoEvangelismo
from backend.api.evangelism_shared import (
    FIRST_TIME_STATES,
    is_absent_status,
    _is_crm_admin_or_pastor,
    _get_persona_for_user,
    _can_manage_grupo,
)
from backend.auth import get_current_user, require_active_user, require_pastor_or_admin
from backend.core.database import get_db
from backend.core.tenant import require_user_sede_id

router = APIRouter()


# ── Cell Group CRUD ──

def _slug_role_name(value: str | None) -> str:
    import unicodedata

    text = unicodedata.normalize("NFD", str(value or "").strip().lower())
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    cleaned = []
    previous_dash = False
    for ch in text:
        if ch.isalnum():
            cleaned.append(ch)
            previous_dash = False
        elif not previous_dash:
            cleaned.append("-")
            previous_dash = True
    return "".join(cleaned).strip("-")


def _strategy_role_catalog(db: Session, strategy_id: str | None) -> tuple[set[int], set[str]]:
    if not strategy_id:
        return set(), set()
    rows = (
        db.query(models.RolPersonalizadoEstrategia)
        .filter(
            models.RolPersonalizadoEstrategia.estrategia_id == strategy_id,
            models.RolPersonalizadoEstrategia.deleted_at.is_(None),
        )
        .all()
    )
    return {r.id for r in rows}, {_slug_role_name(r.nombre_rol) for r in rows}


def _role_slug_tokens(slug: str) -> set[str]:
    return {token for token in slug.split("-") if token}


def _is_primary_leader_slug(slug: str) -> bool:
    tokens = _role_slug_tokens(slug)
    return "lider" in tokens and "co" not in tokens and "colider" not in tokens and "asistente" not in tokens


def _is_assistant_leader_slug(slug: str) -> bool:
    tokens = _role_slug_tokens(slug)
    return "asistente" in tokens or "colider" in tokens or ("co" in tokens and "lider" in tokens)


def _role_slug_has(slug: str, keyword: str) -> bool:
    return keyword in _role_slug_tokens(slug)


def _validate_strategy_group_roles(db: Session, strategy_id: str | None, body: dict) -> None:
    if not strategy_id:
        return

    allowed_custom_ids, allowed_slugs = _strategy_role_catalog(db, strategy_id)
    if body.get("leader_id") and not any(_is_primary_leader_slug(slug) for slug in allowed_slugs):
        raise HTTPException(status_code=400, detail="La estrategia no tiene un rol de líder configurado")
    if body.get("assistant_id") and not any(_is_assistant_leader_slug(slug) for slug in allowed_slugs):
        raise HTTPException(status_code=400, detail="La estrategia no tiene un rol de colíder/asistente configurado")
    if body.get("host_id") and not any(_role_slug_has(slug, "anfitrion") for slug in allowed_slugs):
        raise HTTPException(status_code=400, detail="La estrategia no tiene un rol de anfitrión configurado")

    base_roles = {"persona", "participante", "miembro", "visitante"}
    for item in body.get("base_attendees_with_roles") or []:
        role = str(item.get("role") or "").strip()
        custom_id = item.get("rol_personalizado_id")
        if role.startswith("custom:"):
            try:
                custom_id = int(role.split(":", 1)[1])
            except (TypeError, ValueError):
                raise HTTPException(status_code=400, detail=f"Rol inválido para participante: {role}")
        if custom_id is not None:
            try:
                custom_id_int = int(custom_id)
            except (TypeError, ValueError):
                raise HTTPException(status_code=400, detail="Rol personalizado inválido")
            if custom_id_int not in allowed_custom_ids:
                raise HTTPException(status_code=400, detail="El rol del participante no pertenece a esta estrategia")
            continue
        if _slug_role_name(role) not in base_roles:
            raise HTTPException(status_code=400, detail=f"Rol no configurado en la estrategia: {role}")


@router.get("/grupos", response_model=List[dict])
@router.get("/faro", response_model=List[dict])
def list_cell_groups(
    estrategia_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    user_sede = require_user_sede_id(db, current_user)
    q = db.query(GrupoEvangelismo).filter(
        GrupoEvangelismo.deleted_at.is_(None),
        GrupoEvangelismo.sede_id == user_sede,
    )
    if estrategia_id:
        q = q.filter(GrupoEvangelismo.estrategia_id == estrategia_id)
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
            "members_count": len({p.persona_id for p in (g.participantes or []) if p.activo and p.deleted_at is None} | ({g.lider_persona_id} if g.lider_persona_id else set())),
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
    user_sede = require_user_sede_id(db, current_user)
    if _is_crm_admin_or_pastor(current_user):
        return crud.get_cell_groups(db, sede_id=user_sede)
    persona = _get_persona_for_user(db, current_user.id)
    if not persona:
        return []
    return (
        db.query(GrupoEvangelismo)
        .filter(
            models.GrupoEvangelismo.deleted_at.is_(None),
            models.GrupoEvangelismo.sede_id == user_sede,
            (models.GrupoEvangelismo.lider_persona_id == persona.id)
            | (models.GrupoEvangelismo.asistente_persona_id == persona.id)
        )
        .order_by(models.GrupoEvangelismo.nombre.asc())
        .all()
    )


@router.get("/grupos/assignment-summary", response_model=dict)
@router.get("/faro/assignment-summary", response_model=dict)
def get_faro_assignment_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    user_sede = require_user_sede_id(db, current_user)
    q = (
        db.query(GrupoEvangelismo)
        .filter(
            models.GrupoEvangelismo.deleted_at.is_(None),
            models.GrupoEvangelismo.sede_id == user_sede,
        )
        .order_by(models.GrupoEvangelismo.nombre.asc())
    )
    houses = q.all()
    personas = db.query(models.Persona).filter(models.Persona.sede_id == user_sede).all()
    assigned_persona_ids = {
        row[0]
        for row in (
            db.query(models.ParticipanteGrupo.persona_id)
            .join(models.GrupoEvangelismo, models.GrupoEvangelismo.id == models.ParticipanteGrupo.grupo_id)
            .filter(models.GrupoEvangelismo.sede_id == user_sede)
            .filter(models.GrupoEvangelismo.deleted_at.is_(None))
            .filter(models.ParticipanteGrupo.deleted_at.is_(None))
            .distinct()
            .all()
        )
        if row and row[0] is not None
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
    grupo_id: UUID,
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
        .filter(
            models.ParticipanteGrupo.grupo_id == grupo_id,
            models.ParticipanteGrupo.deleted_at.is_(None),
        )
        .order_by(models.Persona.nombre_completo.asc())
        .all()
    )
    base_attendees = [
        {
            "persona_id": str(persona.id),
            "name": persona.nombre_completo,
            "role": f"custom:{row.rol_personalizado_id}" if row.rol_personalizado_id else (row.role or "miembro"),
            "role_label": (
                row.rol_personalizado.nombre_rol
                if row.rol_personalizado_id and row.rol_personalizado
                else (row.role or "miembro")
            ),
            "rol_personalizado_id": row.rol_personalizado_id,
            "church_role": persona.church_role,
            "phone": persona.telefono,
        }
        for row, persona in base_rows
    ]
    base_attendee_ids = [item["persona_id"] for item in base_attendees]

    # Include leader in base_attendees if not already a participant
    if house.lider_persona_id and str(house.lider_persona_id) not in base_attendee_ids:
        leader_persona = db.query(models.Persona).filter(models.Persona.id == house.lider_persona_id).first()
        if leader_persona:
            base_attendees.insert(0, {
                "persona_id": str(leader_persona.id),
                "name": leader_persona.nombre_completo,
                "role": "lider",
                "role_label": "Líder",
                "rol_personalizado_id": None,
                "church_role": leader_persona.church_role,
                "phone": leader_persona.telefono,
            })
            base_attendee_ids.insert(0, str(leader_persona.id))

    sessions = (
        db.query(SesionGrupo)
        .filter(
            models.SesionGrupo.grupo_id == grupo_id,
            models.SesionGrupo.deleted_at.is_(None),
        )
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
            "estado_habilitacion": getattr(session, "estado_habilitacion", "DESHABILITADO"),
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
async def create_cell_group(
    request: Request,
    payload: schemas.GrupoEvangelismoCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    # Frontend sends "estrategia_id" but the schema uses "evangelism_strategy_id".
    # Read from raw JSON before Pydantic discards unknown fields, then patch.
    import json as _json
    body = _json.loads(await request.body())
    if body.get("estrategia_id") and not payload.evangelism_strategy_id:
        object.__setattr__(payload, "evangelism_strategy_id", body["estrategia_id"])
    _validate_strategy_group_roles(db, payload.evangelism_strategy_id, body)
    # Infer sede_id from user's profile, fallback to first sede
    user_sede = crud.get_user_sede_id(db, current_user.id)
    if not user_sede:
        primera_sede = db.query(models.Sede).order_by("nombre").first()
        user_sede = str(primera_sede.id) if primera_sede else None
    obj = crud.create_cell_group(db, payload, sede_id=user_sede)
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
        "members_count": len({p.persona_id for p in (obj.participantes or []) if p.activo and p.deleted_at is None} | ({obj.lider_persona_id} if obj.lider_persona_id else set())),
        "evangelism_strategy_id": str(obj.estrategia_id) if obj.estrategia_id else None,
    }


@router.put("/grupos/{grupo_id}", response_model=dict)
@router.put("/faro/{grupo_id}", response_model=dict)
def update_cell_group(
    grupo_id: UUID,
    payload: schemas.GrupoEvangelismoUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    house_db = db.query(GrupoEvangelismo).filter(models.GrupoEvangelismo.id == grupo_id).first()
    if not house_db:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    if not _can_manage_grupo(db, current_user, house_db):
        raise HTTPException(status_code=403, detail="No autorizado para este grupo")
    _validate_strategy_group_roles(
        db,
        str(house_db.estrategia_id) if house_db.estrategia_id else None,
        payload.model_dump(exclude_unset=True),
    )
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
    grupo_id: UUID,
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


# ── Campaign Seasons ──


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


# ── Analytics ──


@router.get("/grupos/analytics")
@router.get("/faro/analytics")
def get_faro_analytics(
    season_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    from sqlalchemy import func

    user_sede = require_user_sede_id(db, current_user)
    query = db.query(
        models.SesionGrupo.grupo_id,
        models.SesionGrupo.season_id,
        func.count(models.Asistencia.id).label("total_attendance"),
        func.count(models.SesionGrupo.id.distinct()).label("total_sessions"),
    ).join(
        models.Asistencia,
        models.Asistencia.sesion_id == models.SesionGrupo.id,
        isouter=True,
    ).join(models.GrupoEvangelismo)
    if season_id:
        query = query.filter(models.SesionGrupo.season_id == season_id)
    query = query.filter(models.GrupoEvangelismo.sede_id == user_sede)

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


# ── Macro despliegue ──


@router.get("/macro/despliegue", response_model=dict)
def get_macro_despliegue(
    season_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    from sqlalchemy import func

    user_sede = require_user_sede_id(db, current_user)
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
    q = db.query(GrupoEvangelismo).filter(
        models.GrupoEvangelismo.activo.is_(True),
        models.GrupoEvangelismo.sede_id == user_sede,
    )
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
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    whatsapp: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    grupo_id: UUID
    session_id: Optional[int] = None


class FaroVisitorResponse(BaseModel):
    status: str           # "created" | "duplicate"
    persona_id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None


@router.post("/grupos/visitors", response_model=FaroVisitorResponse)
@router.post("/faro/visitors", response_model=FaroVisitorResponse)
def register_faro_visitor(
    visitor: FaroVisitorCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    """Register a new guest from a Faro session report as a Persona + CRM lead."""
    grupo = db.query(GrupoEvangelismo).filter(models.GrupoEvangelismo.id == visitor.grupo_id).first()
    if not grupo:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")

    # Fix #2: admins/pastores pueden registrar libremente; líderes solo en su propio grupo
    persona = _get_persona_for_user(db, current_user.id)
    if not _is_crm_admin_or_pastor(current_user):
        if persona is None or persona.id not in {
            grupo.lider_persona_id,
            grupo.asistente_persona_id,
            grupo.anfitrion_persona_id,
        }:
            raise HTTPException(status_code=403, detail="Solo el líder o asistente puede registrar visitantes")

    # Fix #5: validar que session_id pertenece a este grupo
    if visitor.session_id is not None:
        sesion = db.query(models.SesionGrupo).filter(
            models.SesionGrupo.id == visitor.session_id,
            models.SesionGrupo.grupo_id == visitor.grupo_id,
        ).first()
        if not sesion:
            raise HTTPException(status_code=400, detail="La sesión no pertenece a este grupo")

    # Fix #4: buscar duplicado solo dentro de la misma sede
    existing = None
    lookup_phone = visitor.phone or visitor.whatsapp
    if lookup_phone:
        existing = db.query(models.Persona).filter(
            models.Persona.telefono == lookup_phone,
            models.Persona.sede_id == grupo.sede_id,
        ).first()

    if existing:
        return FaroVisitorResponse(
            status="duplicate",
            persona_id=str(existing.id),
            first_name=existing.first_name,
            last_name=existing.last_name,
        )

    # Crear persona marcada con su origen evangelístico
    new_persona = models.Persona(
        first_name=visitor.first_name or "Visitante",
        last_name=visitor.last_name or "",
        phone=visitor.phone,
        mobile_phone=visitor.whatsapp,
        email=visitor.email,
        address=visitor.address,
        sede_id=grupo.sede_id,
        church_role="Visitante",
        origen_grupo_id=grupo.id,
        origen_estrategia_id=grupo.estrategia_id,
        origen_sesion_id=visitor.session_id,
    )
    db.add(new_persona)
    db.flush()  # obtener ID sin commitear — todo en una sola transacción
    db.refresh(new_persona)

    # Vincular al grupo
    db.add(
        models.ParticipanteGrupo(
            grupo_id=visitor.grupo_id,
            persona_id=new_persona.id,
            rol_base="visitante",
        )
    )

    from backend.services.evangelism_crm_bridge import crear_caso_nuevo_visitante
    crear_caso_nuevo_visitante(  # hace el db.commit() final
        db, new_persona, grupo.sede_id,
        origen_grupo_id=grupo.id,
        origen_estrategia_id=grupo.estrategia_id,
        origen_sesion_id=visitor.session_id,
    )

    return FaroVisitorResponse(
        status="created",
        persona_id=str(new_persona.id),
        first_name=new_persona.first_name,
        last_name=new_persona.last_name,
    )


# ── Dashboard Metrics ──


@router.get("/strategies/{strategy_id}/metrics", response_model=dict)
def get_strategy_metrics(
    strategy_id: str,
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
    user_sede = require_user_sede_id(db, current_user)
    houses = (
        db.query(GrupoEvangelismo)
        .filter(
            GrupoEvangelismo.estrategia_id == strategy_ref,
            GrupoEvangelismo.sede_id == user_sede,
            GrupoEvangelismo.deleted_at.is_(None),
        )
        .all()
    )
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
            models.SesionGrupo.deleted_at.is_(None),
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
            if a.es_primera_vez or str(a.estado).strip().lower() in FIRST_TIME_STATES:
                weekly[week_key]["first_time"] += 1
            elif is_absent_status(a.estado) or a.absence_reason:
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
