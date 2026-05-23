f = open("backend/api/crm.py", encoding="utf-8")
c = f.read()
f.close()

faro_endpoints = """
# ─── FARO EN CASA: TEMPORADAS & SESIONES ─────────────────────────────────────

@router.get("/faro/seasons")
def list_faro_seasons(db: Session = Depends(get_db), current_user: models.User = Depends(require_pastor_or_admin)):
    seasons = db.query(models.FaroSeason).order_by(models.FaroSeason.start_date.desc()).all()
    return [
        {
            "id": s.id,
            "name": s.name,
            "start_date": s.start_date.isoformat(),
            "end_date": s.end_date.isoformat(),
            "periodicity": s.periodicity,
            "status": s.status,
            "created_at": s.created_at.isoformat() if s.created_at else None
        }
        for s in seasons
    ]


@router.post("/faro/seasons", response_model=dict)
def create_faro_season(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    name = str(payload.get("name", "")).strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    try:
        from datetime import date as date_type
        start = date_type.fromisoformat(payload["start_date"])
        end = date_type.fromisoformat(payload["end_date"])
    except (KeyError, ValueError):
        raise HTTPException(status_code=400, detail="start_date and end_date required in YYYY-MM-DD format")
    
    if end <= start:
        raise HTTPException(status_code=400, detail="end_date must be after start_date")
    
    season = models.FaroSeason(
        name=name,
        start_date=start,
        end_date=end,
        periodicity=payload.get("periodicity", "SEMANAL"),
        status="Activa"
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
    current_user: models.User = Depends(require_pastor_or_admin)
):
    season = db.query(models.FaroSeason).filter(models.FaroSeason.id == season_id).first()
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
    current_user: models.User = Depends(require_pastor_or_admin)
):
    from sqlalchemy.orm import joinedload
    q = db.query(models.GloryHouseSession).options(
        joinedload(models.GloryHouseSession.glory_house),
        joinedload(models.GloryHouseSession.season)
    )
    if season_id:
        q = q.filter(models.GloryHouseSession.season_id == season_id)
    if glory_house_id:
        q = q.filter(models.GloryHouseSession.glory_house_id == glory_house_id)
    sessions = q.order_by(models.GloryHouseSession.session_date.desc()).all()
    return [
        {
            "id": s.id,
            "glory_house_id": s.glory_house_id,
            "glory_house_name": s.glory_house.name if s.glory_house else None,
            "season_id": s.season_id,
            "season_name": s.season.name if s.season else None,
            "session_date": s.session_date.isoformat(),
            "status": s.status,
            "attendance_count": db.query(models.GloryHouseAttendance).filter(
                models.GloryHouseAttendance.session_id == s.id
            ).count()
        }
        for s in sessions
    ]


@router.post("/faro/sessions", response_model=dict)
def create_faro_session(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    try:
        from datetime import date as date_type
        session_date = date_type.fromisoformat(payload["session_date"])
    except (KeyError, ValueError):
        raise HTTPException(status_code=400, detail="session_date required in YYYY-MM-DD format")
    
    season_id = payload.get("season_id")
    glory_house_id = payload.get("glory_house_id")
    if not season_id or not glory_house_id:
        raise HTTPException(status_code=400, detail="season_id and glory_house_id required")
    
    # Verify season is active and date is in range
    season = db.query(models.FaroSeason).filter(models.FaroSeason.id == season_id).first()
    if not season:
        raise HTTPException(status_code=404, detail="Season not found")
    if season.start_date > session_date or season.end_date < session_date:
        raise HTTPException(status_code=400, detail=f"La fecha debe estar dentro de la temporada ({season.start_date} - {season.end_date})")
    
    # Prevent duplicate session for same house + date
    existing = db.query(models.GloryHouseSession).filter(
        models.GloryHouseSession.glory_house_id == glory_house_id,
        models.GloryHouseSession.season_id == season_id,
        models.GloryHouseSession.session_date == session_date
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe una sesión registrada para ese Faro en esa fecha")
    
    session = models.GloryHouseSession(
        glory_house_id=glory_house_id,
        season_id=season_id,
        session_date=session_date,
        status="Realizada"
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"id": session.id, "session_date": session.session_date.isoformat(), "status": session.status}


@router.get("/faro/sessions/{session_id}/attendance")
def get_faro_session_attendance(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    from sqlalchemy.orm import joinedload
    session = db.query(models.GloryHouseSession).filter(models.GloryHouseSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    attendances = db.query(models.GloryHouseAttendance).filter(
        models.GloryHouseAttendance.session_id == session_id
    ).options(joinedload(models.GloryHouseAttendance.member)).all()
    
    return {
        "session_id": session_id,
        "session_date": session.session_date.isoformat(),
        "glory_house_id": session.glory_house_id,
        "total": len(attendances),
        "attendees": [
            {
                "member_id": a.member_id,
                "name": f"{a.member.first_name} {a.member.last_name}" if a.member else "Desconocido",
                "role": a.member.church_role if a.member else None,
                "scanned_at": a.scanned_at.isoformat() if a.scanned_at else None
            }
            for a in attendances
        ]
    }


@router.post("/faro/sessions/{session_id}/attendance", response_model=dict)
def add_faro_attendance(
    session_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    member_ids = payload.get("member_ids", [])
    if not member_ids:
        raise HTTPException(status_code=400, detail="member_ids is required")
    
    session = db.query(models.GloryHouseSession).filter(models.GloryHouseSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    added = 0
    for mid in member_ids:
        exists = db.query(models.GloryHouseAttendance).filter(
            models.GloryHouseAttendance.session_id == session_id,
            models.GloryHouseAttendance.member_id == mid
        ).first()
        if not exists:
            att = models.GloryHouseAttendance(session_id=session_id, member_id=mid, attended=True)
            db.add(att)
            added += 1
    
    db.commit()
    return {"status": "success", "added": added, "total": len(member_ids)}


@router.get("/faro/analytics")
def get_faro_analytics(
    season_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    from sqlalchemy import func
    
    q = db.query(
        models.GloryHouseSession.glory_house_id,
        models.GloryHouseSession.season_id,
        func.count(models.GloryHouseAttendance.id).label("total_attendance"),
        func.count(models.GloryHouseSession.id.distinct()).label("total_sessions")
    ).join(
        models.GloryHouseAttendance,
        models.GloryHouseAttendance.session_id == models.GloryHouseSession.id,
        isouter=True
    )
    
    if season_id:
        q = q.filter(models.GloryHouseSession.season_id == season_id)
    
    rows = q.group_by(models.GloryHouseSession.glory_house_id, models.GloryHouseSession.season_id).all()
    
    total_attendance = sum(r.total_attendance or 0 for r in rows)
    total_sessions = sum(r.total_sessions or 0 for r in rows)
    active_faros = len(set(r.glory_house_id for r in rows))
    
    return {
        "total_attendance": total_attendance,
        "total_sessions": total_sessions,
        "active_faros": active_faros,
        "avg_per_session": round(total_attendance / total_sessions) if total_sessions > 0 else 0,
        "per_faro": [
            {
                "glory_house_id": r.glory_house_id,
                "total_attendance": r.total_attendance or 0,
                "total_sessions": r.total_sessions or 0,
                "avg": round((r.total_attendance or 0) / r.total_sessions) if r.total_sessions else 0
            }
            for r in rows
        ]
    }

"""

if "def list_faro_seasons" not in c:
    # Insert before the closing route aliases block
    c = c.replace(
        "# ─── ROUTE ALIASES ──────────────────────────────────────────────────────────",
        faro_endpoints
        + "\n# ─── ROUTE ALIASES ──────────────────────────────────────────────────────────",
    )
    open("backend/api/crm.py", "w", encoding="utf-8").write(c)
    print("Faro endpoints injected")
else:
    print("Already exists")
