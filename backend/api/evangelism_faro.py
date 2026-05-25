from __future__ import annotations

import collections
from datetime import datetime as _datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from backend import crud, models, schemas
from backend.api.evangelism_shared import (faro_expected_member_rows,
                                           faro_member_payload, utc_now)
from backend.auth import (get_current_user, normalize_role,
                          require_pastor_or_admin)
from backend.core.database import get_db

router = APIRouter()


def _is_crm_admin_or_pastor(user: models.User) -> bool:
    return normalize_role(str(getattr(user, "role", ""))) in {"admin", "pastor"}


def _get_member_for_user(db: Session, user_id: int) -> Optional[models.Member]:
    return db.query(models.Member).filter(models.Member.user_id == user_id).first()


def _can_manage_house(db: Session, user: models.User, house: models.GloryHouse) -> bool:
    if _is_crm_admin_or_pastor(user):
        return True
    member = _get_member_for_user(db, user.id)
    if not member:
        return False
    return member.id in {house.leader_id, house.assistant_id}


@router.get("/glory-houses", response_model=List[schemas.GloryHouse])
def list_glory_houses(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    return crud.get_glory_houses(db)


@router.get("/glory-houses/mine", response_model=List[schemas.GloryHouse])
def list_my_glory_houses(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if _is_crm_admin_or_pastor(current_user):
        return crud.get_glory_houses(db)
    member = _get_member_for_user(db, current_user.id)
    if not member:
        return []
    return (
        db.query(models.GloryHouse)
        .filter(
            (models.GloryHouse.leader_id == member.id)
            | (models.GloryHouse.assistant_id == member.id)
        )
        .order_by(models.GloryHouse.name.asc())
        .all()
    )


@router.get("/faro/assignment-summary", response_model=dict)
def get_faro_assignment_summary(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    houses = db.query(models.GloryHouse).order_by(models.GloryHouse.name.asc()).all()
    members = db.query(models.Member).all()
    assigned_member_ids = {
        row[0]
        for row in db.query(models.GloryHouseMember.member_id).distinct().all()
        if row and row[0] is not None
    }
    for house in houses:
        for member_id in [house.leader_id, house.assistant_id, house.host_id]:
            if member_id:
                assigned_member_ids.add(member_id)

    houses_with_leader = [house for house in houses if house.leader_id]
    houses_without_leader = [house for house in houses if not house.leader_id]
    houses_with_assistant = [house for house in houses if house.assistant_id]
    houses_without_assistant = [house for house in houses if not house.assistant_id]
    houses_with_host = [house for house in houses if house.host_id]
    houses_without_host = [house for house in houses if not house.host_id]
    houses_with_members = [house for house in houses if (house.members_count or 0) > 0]
    houses_without_members = [
        house for house in houses if (house.members_count or 0) == 0
    ]

    unassigned_members = [
        {
            "id": member.id,
            "name": f"{member.first_name} {member.last_name}",
            "church_role": member.church_role,
        }
        for member in members
        if member.id not in assigned_member_ids
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
        "members_total": len(members),
        "members_unassigned": len(unassigned_members),
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
        "unassigned_members": unassigned_members[:100],
    }


@router.get("/glory-houses/{house_id}", response_model=dict)
@router.get("/micro/{house_id}", response_model=dict)
def get_glory_house(
    house_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    house = db.query(models.GloryHouse).filter(models.GloryHouse.id == house_id).first()
    if not house:
        raise HTTPException(status_code=404, detail="Glory house not found")
    if not _can_manage_house(db, current_user, house):
        raise HTTPException(
            status_code=403, detail="No autorizado para este Faro en Casa"
        )

    base_rows = (
        db.query(models.GloryHouseMember, models.Member)
        .join(models.Member, models.Member.id == models.GloryHouseMember.member_id)
        .filter(models.GloryHouseMember.glory_house_id == house_id)
        .order_by(models.Member.last_name.asc(), models.Member.first_name.asc())
        .all()
    )
    base_attendees = [
        {
            "member_id": member.id,
            "name": f"{member.first_name} {member.last_name}",
            "role": row.role,
            "church_role": member.church_role,
            "phone": member.phone,
            "member": {
                "first_name": member.first_name,
                "last_name": member.last_name,
                "phone": member.phone,
            },
        }
        for row, member in base_rows
    ]
    base_attendee_ids = [item["member_id"] for item in base_attendees]

    sessions = (
        db.query(models.GloryHouseSession)
        .filter(models.GloryHouseSession.glory_house_id == house_id)
        .order_by(models.GloryHouseSession.session_date.desc())
        .limit(20)
        .all()
    )

    expected_rows = faro_expected_member_rows(db, house_id)
    expected_count = len(expected_rows)
    absence_counter = collections.Counter()
    absence_details: dict[int, list[dict]] = collections.defaultdict(list)
    attendance_by_session = collections.defaultdict(list)

    if sessions:
        from sqlalchemy import func as sqlfunc

        session_ids = [session.id for session in sessions]
        season_ids = list({session.season_id for session in sessions})
        attendance_rows = (
            db.query(models.GloryHouseAttendance)
            .options(joinedload(models.GloryHouseAttendance.member))
            .filter(models.GloryHouseAttendance.session_id.in_(session_ids))
            .all()
        )
        for row in attendance_rows:
            attendance_by_session[row.session_id].append(row)
            if not row.attended and row.member:
                absence_counter[row.member_id] += 1
                absence_details[row.member_id].append(
                    {
                        "session_id": row.session_id,
                        "session_date": (
                            row.session.session_date.isoformat()
                            if row.session and row.session.session_date
                            else None
                        ),
                        "reason": row.absence_reason,
                        "reason_detail": row.absence_reason_detail,
                    }
                )
        attendance_counts = (
            db.query(
                models.GloryHouseAttendance.session_id,
                sqlfunc.count(models.GloryHouseAttendance.id).label("cnt"),
            )
            .filter(models.GloryHouseAttendance.session_id.in_(session_ids))
            .group_by(models.GloryHouseAttendance.session_id)
            .all()
        )
        attendance_map = {row.session_id: row.cnt for row in attendance_counts}
        seasons_batch = (
            db.query(models.FaroSeason)
            .filter(models.FaroSeason.id.in_(season_ids))
            .all()
        )
        season_map = {season.id: season.name for season in seasons_batch}
    else:
        attendance_map = {}
        season_map = {}

    sessions_data = [
        {
            "id": session.id,
            "session_date": session.session_date.isoformat(),
            "status": session.status,
            "season_name": season_map.get(session.season_id),
            "attendance_count": attendance_map.get(session.id, 0),
            "present_count": sum(
                1 for row in attendance_by_session.get(session.id, []) if row.attended
            ),
            "absent_count": sum(
                1
                for row in attendance_by_session.get(session.id, [])
                if not row.attended
            ),
            "attendance_rate": (
                round(
                    (
                        sum(
                            1
                            for row in attendance_by_session.get(session.id, [])
                            if row.attended
                        )
                        / max(expected_count, 1)
                    )
                    * 100,
                    1,
                )
                if expected_count
                else 0
            ),
            "topic": session.topic,
            "report_deadline": (
                session.report_deadline.isoformat() if session.report_deadline else None
            ),
            "offering_amount": (
                float(session.offering_amount)
                if session.offering_amount is not None
                else None
            ),
            "novelty_type": session.novelty_type,
            "novelty_detail": session.novelty_detail,
            "cancellation_reason": session.cancellation_reason,
        }
        for session in sessions
    ]

    monitoring_sessions = sessions_data[:8]
    monitoring_rates = [
        session["attendance_rate"]
        for session in monitoring_sessions
        if session["attendance_rate"] is not None
    ]
    monitoring_average_rate = (
        round(sum(monitoring_rates) / len(monitoring_rates), 1)
        if monitoring_rates
        else 0
    )
    monitoring_average_presence = (
        round(
            sum(session["present_count"] for session in monitoring_sessions)
            / len(monitoring_sessions)
        )
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

    member_lookup = {member.id: member for _, member in expected_rows}
    repeat_absentees = []
    for member_id, count in absence_counter.items():
        if count >= 2:
            member = (
                member_lookup.get(member_id)
                or db.query(models.Member).filter(models.Member.id == member_id).first()
            )
            repeat_absentees.append(
                {
                    "member_id": member_id,
                    "name": (
                        f"{member.first_name} {member.last_name}"
                        if member
                        else "Miembro"
                    ),
                    "absences": count,
                    "details": absence_details.get(member_id, []),
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
        "leader_id": house.leader_id,
        "assistant_id": house.assistant_id,
        "host_id": house.host_id,
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
        "total_attendance": sum(
            session["attendance_count"] for session in sessions_data
        ),
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


@router.post("/glory-houses", response_model=schemas.GloryHouse)
def create_glory_house(
    payload: schemas.GloryHouseCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    return crud.create_glory_house(db, payload)


@router.put("/glory-houses/{house_id}", response_model=schemas.GloryHouse)
def update_glory_house(
    house_id: int,
    payload: schemas.GloryHouseUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    house_db = (
        db.query(models.GloryHouse).filter(models.GloryHouse.id == house_id).first()
    )
    if not house_db:
        raise HTTPException(status_code=404, detail="Glory house not found")
    if not _can_manage_house(db, current_user, house_db):
        raise HTTPException(
            status_code=403, detail="No autorizado para este Faro en Casa"
        )
    if not _is_crm_admin_or_pastor(current_user):
        allowed_fields = {"base_attendee_ids"}
        incoming_fields = set(payload.model_dump(exclude_unset=True).keys())
        if not incoming_fields:
            raise HTTPException(status_code=400, detail="No hay campos para actualizar")
        if not incoming_fields.issubset(allowed_fields):
            raise HTTPException(
                status_code=403,
                detail="Lideres y colideres solo pueden gestionar asistentes del Faro en Casa",
            )
    house = crud.update_glory_house(db, house_id, payload)
    if not house:
        raise HTTPException(status_code=404, detail="Glory house not found")
    return house


@router.delete("/glory-houses/{house_id}", status_code=204)
def delete_glory_house(
    house_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Elimina una casa de gloria."""
    house = db.query(models.GloryHouse).filter(models.GloryHouse.id == house_id).first()
    if not house:
        raise HTTPException(status_code=404, detail="Glory house not found")
    db.delete(house)
    db.commit()
    return None


@router.get("/faro/seasons")
def list_faro_seasons(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    seasons = (
        db.query(models.FaroSeason).order_by(models.FaroSeason.start_date.desc()).all()
    )
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


@router.post("/faro/seasons", response_model=dict)
def create_faro_season(
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

    season = models.FaroSeason(
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


@router.patch("/faro/seasons/{season_id}", response_model=dict)
def update_faro_season(
    season_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    season = (
        db.query(models.FaroSeason).filter(models.FaroSeason.id == season_id).first()
    )
    if not season:
        raise HTTPException(status_code=404, detail="Season not found")
    for field in ["name", "status", "periodicity"]:
        if field in payload:
            setattr(season, field, payload[field])
    db.commit()
    return {"id": season.id, "name": season.name, "status": season.status}


@router.get("/faro/sessions")
def list_faro_sessions(
    season_id: Optional[int] = None,
    glory_house_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    query = db.query(models.GloryHouseSession).options(
        joinedload(models.GloryHouseSession.glory_house),
        joinedload(models.GloryHouseSession.season),
    )
    if season_id:
        query = query.filter(models.GloryHouseSession.season_id == season_id)
    if glory_house_id:
        query = query.filter(models.GloryHouseSession.glory_house_id == glory_house_id)
    sessions = query.order_by(models.GloryHouseSession.session_date.desc()).all()

    # Single query: get attendance counts for all sessions at once
    if sessions:
        session_ids = [s.id for s in sessions]
        from sqlalchemy import func
        att_counts = dict(
            db.query(
                models.GloryHouseAttendance.session_id,
                func.count(models.GloryHouseAttendance.id),
            )
            .filter(models.GloryHouseAttendance.session_id.in_(session_ids))
            .group_by(models.GloryHouseAttendance.session_id)
            .all()
        )
    else:
        att_counts = {}

    return [
        {
            "id": session.id,
            "glory_house_id": session.glory_house_id,
            "glory_house_name": (
                session.glory_house.name if session.glory_house else None
            ),
            "season_id": session.season_id,
            "season_name": session.season.name if session.season else None,
            "session_date": session.session_date.isoformat(),
            "status": session.status,
            "attendance_count": att_counts.get(session.id, 0),
        }
        for session in sessions
    ]


@router.get("/faro/sessions/mine/pending")
def list_my_pending_faro_sessions(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    house_ids: list[int]
    if _is_crm_admin_or_pastor(current_user):
        house_ids = [row[0] for row in db.query(models.GloryHouse.id).all()]
    else:
        member = _get_member_for_user(db, current_user.id)
        if not member:
            return []
        house_ids = [
            row[0]
            for row in db.query(models.GloryHouse.id)
            .filter(
                (models.GloryHouse.leader_id == member.id)
                | (models.GloryHouse.assistant_id == member.id)
            )
            .all()
        ]
    if not house_ids:
        return []

    sessions = (
        db.query(models.GloryHouseSession)
        .options(
            joinedload(models.GloryHouseSession.glory_house),
            joinedload(models.GloryHouseSession.season),
        )
        .filter(models.GloryHouseSession.glory_house_id.in_(house_ids))
        .order_by(models.GloryHouseSession.session_date.desc())
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
                models.GloryHouseAttendance.session_id,
                func.count(models.GloryHouseAttendance.id),
            )
            .filter(models.GloryHouseAttendance.session_id.in_(session_ids))
            .group_by(models.GloryHouseAttendance.session_id)
            .all()
        )
    else:
        att_counts = {}

    for session in sessions:
        attendance_count = att_counts.get(session.id, 0)
        expected_count = len(faro_expected_member_rows(db, session.glory_house_id))
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
                "glory_house_id": session.glory_house_id,
                "glory_house_name": (
                    session.glory_house.name if session.glory_house else None
                ),
                "season_name": session.season.name if session.season else None,
                "session_date": (
                    session.session_date.isoformat() if session.session_date else None
                ),
                "status": session.status,
                "attendance_count": attendance_count,
                "expected_count": expected_count,
                "report_deadline": (
                    session.report_deadline.isoformat()
                    if session.report_deadline
                    else None
                ),
            }
        )
    return items


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
        raise HTTPException(
            status_code=400, detail="session_date required in YYYY-MM-DD format"
        )

    season_id = payload.get("season_id")
    glory_house_id = payload.get("glory_house_id")
    topic = payload.get("topic")
    report_deadline_str = payload.get("report_deadline")

    if not season_id or not glory_house_id:
        raise HTTPException(
            status_code=400, detail="season_id and glory_house_id required"
        )

    season = (
        db.query(models.FaroSeason).filter(models.FaroSeason.id == season_id).first()
    )
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
            report_deadline = datetime.fromisoformat(
                report_deadline_str.replace("Z", "+00:00")
            )
        except ValueError:
            pass

    # Gather houses
    houses_to_process = []
    if str(glory_house_id).lower() == "all":
        houses = (
            db.query(models.GloryHouse)
            .filter(models.GloryHouse.status == "Activo")
            .all()
        )
        houses_to_process = [h.id for h in houses]
    else:
        houses_to_process = [int(glory_house_id)]

    created_sessions = []
    for h_id in houses_to_process:
        existing = (
            db.query(models.GloryHouseSession)
            .filter(
                models.GloryHouseSession.glory_house_id == h_id,
                models.GloryHouseSession.season_id == season_id,
                models.GloryHouseSession.session_date == session_date,
            )
            .first()
        )
        if existing:
            if str(glory_house_id).lower() != "all":
                raise HTTPException(
                    status_code=400,
                    detail="Ya existe una sesión registrada para ese Faro en esa fecha",
                )
            continue  # In batch mode, we just skip existing

        session = models.GloryHouseSession(
            glory_house_id=h_id,
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


@router.get("/faro/sessions/{session_id}/attendance")
def get_faro_session_attendance(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    session = (
        db.query(models.GloryHouseSession)
        .filter(models.GloryHouseSession.id == session_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    house = (
        db.query(models.GloryHouse)
        .filter(models.GloryHouse.id == session.glory_house_id)
        .first()
    )
    if not house:
        raise HTTPException(status_code=404, detail="Glory house not found")
    if not _can_manage_house(db, current_user, house):
        raise HTTPException(
            status_code=403, detail="No autorizado para este Faro en Casa"
        )

    attendances = (
        db.query(models.GloryHouseAttendance)
        .filter(models.GloryHouseAttendance.session_id == session_id)
        .options(joinedload(models.GloryHouseAttendance.member))
        .all()
    )

    expected_rows = faro_expected_member_rows(db, session.glory_house_id)
    attendance_map = {attendance.member_id: attendance for attendance in attendances}
    present = []
    absent = []
    expected_members = []
    for _, member in expected_rows:
        attendance = attendance_map.get(member.id)
        payload = faro_member_payload(
            member,
            attended=bool(attendance.attended) if attendance else False,
            scanned_at=attendance.scanned_at if attendance else None,
            absence_reason=attendance.absence_reason if attendance else None,
            absence_reason_detail=(
                attendance.absence_reason_detail if attendance else None
            ),
        )
        expected_members.append(payload)
        if attendance and attendance.attended:
            present.append(payload)
        else:
            absent.append(payload)

    return {
        "session_id": session_id,
        "session_date": session.session_date.isoformat(),
        "glory_house_id": session.glory_house_id,
        "status": session.status,
        "topic": session.topic,
        "offering_amount": (
            float(session.offering_amount)
            if session.offering_amount is not None
            else None
        ),
        "report_notes": session.report_notes,
        "novelty_type": session.novelty_type,
        "novelty_detail": session.novelty_detail,
        "cancellation_reason": session.cancellation_reason,
        "reported_by_member_id": session.reported_by_member_id,
        "total": len(present),
        "present_count": len(present),
        "absent_count": len(absent),
        "attendees": present,
        "absentees": absent,
        "expected_members": expected_members,
    }


@router.post("/faro/sessions/{session_id}/attendance", response_model=dict)
def add_faro_attendance(
    session_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    member_ids = payload.get("member_ids", [])
    attendees = payload.get("attendees")

    session = (
        db.query(models.GloryHouseSession)
        .filter(models.GloryHouseSession.id == session_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    house = (
        db.query(models.GloryHouse)
        .filter(models.GloryHouse.id == session.glory_house_id)
        .first()
    )
    if not house:
        raise HTTPException(status_code=404, detail="Glory house not found")
    if not _can_manage_house(db, current_user, house):
        raise HTTPException(
            status_code=403, detail="No autorizado para este Faro en Casa"
        )

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

    if attendees and not isinstance(attendees, list):
        raise HTTPException(status_code=400, detail="attendees must be a list")

    if attendees:
        processed = 0
        for item in attendees:
            member_id = item.get("member_id")
            if not member_id:
                continue
            attended = bool(item.get("attended", True))
            absence_reason = item.get("absence_reason")
            absence_reason_detail = item.get("absence_reason_detail")

            if not attended and not absence_reason:
                raise HTTPException(
                    status_code=400,
                    detail=f"Razón de ausencia requerida para el miembro {member_id}.",
                )

            row = (
                db.query(models.GloryHouseAttendance)
                .filter(
                    models.GloryHouseAttendance.session_id == session_id,
                    models.GloryHouseAttendance.member_id == member_id,
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
                    models.GloryHouseAttendance(
                        session_id=session_id,
                        member_id=member_id,
                        attended=attended,
                        absence_reason=absence_reason,
                        absence_reason_detail=absence_reason_detail,
                    )
                )
            processed += 1
    else:
        if not member_ids:
            raise HTTPException(
                status_code=400, detail="member_ids or attendees is required"
            )
        processed = 0
        for member_id in member_ids:
            exists = (
                db.query(models.GloryHouseAttendance)
                .filter(
                    models.GloryHouseAttendance.session_id == session_id,
                    models.GloryHouseAttendance.member_id == member_id,
                )
                .first()
            )
            if not exists:
                db.add(
                    models.GloryHouseAttendance(
                        session_id=session_id, member_id=member_id, attended=True
                    )
                )
                processed += 1

    new_status = payload.get("status", session.status)
    new_cancellation_reason = payload.get(
        "cancellation_reason", session.cancellation_reason
    )

    if new_status in ["Cancelada", "No realizada"] and not new_cancellation_reason:
        raise HTTPException(
            status_code=400,
            detail=f"Motivo de cancelación es requerido cuando el estado es {new_status}.",
        )

    new_offering_amount = payload.get("offering_amount", session.offering_amount)
    if new_offering_amount is not None and float(new_offering_amount) < 0:
        raise HTTPException(
            status_code=400, detail="La ofrenda no puede ser un valor negativo."
        )

    session.topic = payload.get("topic", session.topic)
    session.offering_amount = new_offering_amount
    session.report_notes = payload.get("report_notes", session.report_notes)
    session.novelty_type = payload.get("novelty_type", session.novelty_type)
    session.novelty_detail = payload.get("novelty_detail", session.novelty_detail)
    session.cancellation_reason = new_cancellation_reason
    session.status = new_status
    session.reported_by_member_id = payload.get(
        "reported_by_member_id", session.reported_by_member_id
    )
    session.reported_at = utc_now()

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"status": "success", "processed": processed, "session_id": session_id}


@router.get("/faro/analytics")
def get_faro_analytics(
    season_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    from sqlalchemy import func

    query = db.query(
        models.GloryHouseSession.glory_house_id,
        models.GloryHouseSession.season_id,
        func.count(models.GloryHouseAttendance.id).label("total_attendance"),
        func.count(models.GloryHouseSession.id.distinct()).label("total_sessions"),
    ).join(
        models.GloryHouseAttendance,
        models.GloryHouseAttendance.session_id == models.GloryHouseSession.id,
        isouter=True,
    )
    if season_id:
        query = query.filter(models.GloryHouseSession.season_id == season_id)

    rows = query.group_by(
        models.GloryHouseSession.glory_house_id, models.GloryHouseSession.season_id
    ).all()
    total_attendance = sum(row.total_attendance or 0 for row in rows)
    total_sessions = sum(row.total_sessions or 0 for row in rows)
    active_faros = len({row.glory_house_id for row in rows})

    return {
        "total_attendance": total_attendance,
        "total_sessions": total_sessions,
        "active_faros": active_faros,
        "avg_per_session": (
            round(total_attendance / total_sessions) if total_sessions > 0 else 0
        ),
        "per_faro": [
            {
                "glory_house_id": row.glory_house_id,
                "total_attendance": row.total_attendance or 0,
                "total_sessions": row.total_sessions or 0,
                "avg": (
                    round((row.total_attendance or 0) / row.total_sessions)
                    if row.total_sessions
                    else 0
                ),
            }
            for row in rows
        ],
    }


@router.get("/macro/despliegue", response_model=dict)
def get_macro_despliegue(
    season_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    from sqlalchemy import func

    # 1. Determine active season if not provided
    if not season_id:
        active_season = (
            db.query(models.FaroSeason)
            .filter(models.FaroSeason.status == "Activa")
            .order_by(models.FaroSeason.id.desc())
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
        season = (
            db.query(models.FaroSeason)
            .filter(models.FaroSeason.id == season_id)
            .first()
        )
        season_name = season.name if season else f"Temporada {season_id}"

    # 2. Get all active houses
    houses = (
        db.query(models.GloryHouse)
        .filter(models.GloryHouse.status == "Activo")
        .order_by(models.GloryHouse.name.asc())
        .all()
    )

    # 3. Get all sessions for the season
    sessions = (
        db.query(models.GloryHouseSession)
        .filter(models.GloryHouseSession.season_id == season_id)
        .all()
    )

    # Group sessions by house
    sessions_by_house = collections.defaultdict(list)
    for s in sessions:
        sessions_by_house[s.glory_house_id].append(s)

    # Get attendance counts per session
    attendance_counts = (
        db.query(
            models.GloryHouseAttendance.session_id,
            func.count(models.GloryHouseAttendance.id).label("cnt"),
        )
        .group_by(models.GloryHouseAttendance.session_id)
        .all()
    )
    att_map = {row.session_id: row.cnt for row in attendance_counts}

    # 4. Build the dense JSON
    despliegue = []
    for house in houses:
        house_sessions = sorted(
            sessions_by_house.get(house.id, []), key=lambda x: x.session_date
        )
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


# ── Sessions & Attendance ──

@router.get("/sessions", response_model=List[schemas.GloryHouseSession])
def list_sessions(
    strategy_id: Optional[int] = None,
    house_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """List sessions, optionally filtered by strategy or house."""
    from backend.models_academy import GloryHouseSession, GloryHouse
    
    q = db.query(GloryHouseSession)
    if strategy_id:
        q = q.join(GloryHouse, GloryHouse.id == GloryHouseSession.glory_house_id).filter(
            GloryHouse.evangelism_strategy_id == strategy_id
        )
    if house_id:
        q = q.filter(GloryHouseSession.glory_house_id == house_id)
    return q.order_by(GloryHouseSession.session_date.desc()).all()


@router.post("/sessions", response_model=schemas.GloryHouseSession)
def create_session(
    session_data: schemas.GloryHouseSessionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Create a new session."""
    from backend.models_academy import GloryHouseSession as SessionModel
    
    db_session = SessionModel(
        glory_house_id=session_data.glory_house_id,
        season_id=session_data.season_id,
        session_date=session_data.session_date,
        topic=session_data.topic,
        offering_amount=session_data.offering_amount,
        report_notes=session_data.report_notes,
        novelty_type=session_data.novelty_type,
        novelty_detail=session_data.novelty_detail,
        cancellation_reason=session_data.cancellation_reason,
        reported_by_member_id=session_data.reported_by_member_id,
        reported_at=_datetime.utcnow(),
        status=session_data.status,
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session


@router.get("/sessions/{session_id}", response_model=dict)
def get_session_detail(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Get session with attendance records including member names."""
    from backend.models_academy import GloryHouseSession, GloryHouseAttendance, GloryHouseMember
    from backend.models_crm import Member

    session = (
        db.query(GloryHouseSession)
        .options(joinedload(GloryHouseSession.glory_house))
        .filter(GloryHouseSession.id == session_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    attendance_rows = db.query(GloryHouseAttendance).filter(
        GloryHouseAttendance.session_id == session_id
    ).all()

    # Build member name lookup for this session's glory_house
    member_map: dict[int, str] = {}
    house_members = db.query(GloryHouseMember).filter(
        GloryHouseMember.glory_house_id == session.glory_house_id
    ).all()
    for hm in house_members:
        m = db.query(Member).filter(Member.id == hm.member_id).first()
        if m:
            member_map[hm.member_id] = f"{m.first_name} {m.last_name}".strip()

    attendance_list = []
    for a in attendance_rows:
        status = a.status if a.status else ("present" if a.attended else "absent")
        attendance_list.append({
            "id": a.id,
            "session_id": a.session_id,
            "member_id": a.member_id,
            "member_name": member_map.get(a.member_id, f"Miembro {a.member_id}"),
            "status": status,
            "notes": a.notes,
            "attended": a.attended,
        })

    gh = session.glory_house
    return {
        "session": {
            "id": session.id,
            "glory_house_id": session.glory_house_id,
            "session_date": session.session_date.isoformat() if session.session_date else None,
            "topic": session.topic,
            "offering_amount": float(session.offering_amount) if session.offering_amount else None,
            "status": session.status,
            "report_notes": session.report_notes,
        },
        "attendance": attendance_list,
        "glory_house": {
            "id": gh.id,
            "name": gh.name,
            "leader_name": gh.leader_name,
        } if gh else None,
    }


@router.put("/sessions/{session_id}", response_model=schemas.GloryHouseSession)
def update_session(
    session_id: int,
    update: schemas.GloryHouseSessionUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Update session."""
    from backend.models_academy import GloryHouseSession as SessionModel
    
    db_session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_session, key, value)
    
    db_session.reported_at = _datetime.utcnow()
    db.commit()
    db.refresh(db_session)
    return db_session


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Delete session and its attendance."""
    from backend.models_academy import GloryHouseSession, GloryHouseAttendance
    
    db_session = db.query(GloryHouseSession).filter(GloryHouseSession.id == session_id).first()
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    db.query(GloryHouseAttendance).filter(
        GloryHouseAttendance.session_id == session_id
    ).delete()
    db.delete(db_session)
    db.commit()
    return {"ok": True}


# ── Attendance ──

@router.post("/sessions/{session_id}/attendance", response_model=List[schemas.GloryHouseAttendance])
def submit_attendance(
    session_id: int,
    attendance_data: List[schemas.GloryHouseAttendanceCreate],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    """Submit attendance for a session. Checks automation triggers."""
    from backend.models_academy import GloryHouseAttendance, GloryHouseSession
    
    session = db.query(GloryHouseSession).filter(GloryHouseSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Delete existing attendance for this session
    db.query(GloryHouseAttendance).filter(
        GloryHouseAttendance.session_id == session_id
    ).delete()
    
    submitted = []
    for att in attendance_data:
        # Map schema fields (status/notes) to model fields (attended/absence_reason)
        is_attended = att.status in ("present", "first_time")
        absence_reason = None
        absence_reason_detail = None
        if att.status == "absent":
            absence_reason = att.notes if att.notes else "sin_especificar"
            absence_reason_detail = att.notes

        db_att = GloryHouseAttendance(
            session_id=session_id,
            member_id=att.member_id,
            attended=is_attended,
            absence_reason=absence_reason,
            absence_reason_detail=absence_reason_detail,
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
    
    return submitted


def _check_absence_trigger(db: Session, session_id: int):
    """If a member has 3 consecutive absences, create N2 task in Consolidation."""
    from backend.models_academy import (
        GloryHouseAttendance,
        GloryHouseSession,
        GloryHouse,
    )
    from backend.models_crm import Member
    
    session = db.query(GloryHouseSession).filter(
        GloryHouseSession.id == session_id
    ).first()
    if not session:
        return
    
    house = db.query(GloryHouse).filter(
        GloryHouse.id == session.glory_house_id
    ).first()
    if not house:
        return
    
    # Get last 3 sessions for this house
    recent_sessions = (
        db.query(GloryHouseSession)
        .filter(GloryHouseSession.glory_house_id == house.id)
        .order_by(GloryHouseSession.session_date.desc())
        .limit(3)
        .all()
    )
    
    if len(recent_sessions) < 3:
        return  # Not enough data
    
    # Check attendance for each member in base attendees
    for base_member in (house.base_attendees or []):
        member_id = base_member.member_id
        absent_count = 0
        for s in recent_sessions:
            att = (
                db.query(GloryHouseAttendance)
                .filter(
                    GloryHouseAttendance.session_id == s.id,
                    GloryHouseAttendance.member_id == member_id,
                    GloryHouseAttendance.status == "absent",
                )
                .first()
            )
            if att:
                absent_count += 1
        
        if absent_count >= 3:
            # Create N2 task in Consolidation
            member = db.query(Member).filter(Member.id == member_id).first()
            if not member:
                continue
            from backend.models_crm import SupportTicket
            ticket = SupportTicket(
                member_id=member_id,
                ticket_type="consolidation",
                title=f"Inasistencia recurrente: {member.first_name} {member.last_name}",
                description=f"{member.first_name} {member.last_name} ha faltado 3 sesiones consecutivas en {house.name}. Requiere contacto pastoral.",
                status="open",
                priority="high",
                severity="N2",
            )
            db.add(ticket)
            db.commit()


def _check_first_time_lead_trigger(db: Session, session_id: int):
    """If a first_time attendee is recorded, mark as LEAD_NUEVO in CRM."""
    from backend.models_academy import GloryHouseAttendance
    from backend.models_crm import Member
    
    first_timers = (
        db.query(GloryHouseAttendance)
        .filter(
            GloryHouseAttendance.session_id == session_id,
            GloryHouseAttendance.status == "first_time",
        )
        .all()
    )
    
    for att in first_timers:
        member = db.query(Member).filter(Member.id == att.member_id).first()
        if member and str(getattr(member, "status", "")).lower() not in ("lead", "lead_nuevo"):
            try:
                member.status = "lead_nuevo"
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
    from backend.models_academy import (
        GloryHouseSession,
        GloryHouseAttendance,
        GloryHouse,
    )
    from datetime import timedelta
    
    # Get all houses for this strategy
    houses = db.query(GloryHouse).filter(
        GloryHouse.evangelism_strategy_id == strategy_id
    ).all()
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
    
    cutoff = _datetime.utcnow() - timedelta(weeks=weeks)

    sessions = (
        db.query(GloryHouseSession)
        .filter(
            GloryHouseSession.glory_house_id.in_(house_ids),
            GloryHouseSession.session_date >= cutoff.date(),
        )
        .order_by(GloryHouseSession.session_date)
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
    all_attendance = (
        db.query(GloryHouseAttendance)
        .filter(GloryHouseAttendance.session_id.in_(session_ids))
        .all()
    )

    # Group attendance by session_id in memory
    att_by_session = collections.defaultdict(list)
    for a in all_attendance:
        att_by_session[a.session_id].append(a)

    weekly = collections.defaultdict(lambda: {
        "present": 0, "absent": 0, "first_time": 0,
        "sessions": 0, "offering": 0.0,
    })

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
        weekly_list.append({
            "week": week_key,
            **data,
            "attendance_rate": round(data["present"] / total_att * 100, 1) if total_att > 0 else 0,
        })
    
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
