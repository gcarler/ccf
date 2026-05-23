import collections
import json

with open("d:/ccf/backend/api/evangelism_faro.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add alias
content = content.replace(
    '@router.get("/glory-houses/{house_id}", response_model=dict)',
    '@router.get("/glory-houses/{house_id}", response_model=dict)\n@router.get("/micro/{house_id}", response_model=dict)',
)

# 2. Append new endpoint
new_endpoint = """

@router.get("/macro/despliegue", response_model=dict)
def get_macro_despliegue(
    season_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    from sqlalchemy import func
    
    # 1. Determine active season if not provided
    if not season_id:
        active_season = db.query(models.FaroSeason).filter(models.FaroSeason.status == "Activa").order_by(models.FaroSeason.id.desc()).first()
        if active_season:
            season_id = active_season.id
            season_name = active_season.name
        else:
            return {"season": "No hay temporada activa", "total_houses": 0, "despliegue": []}
    else:
        season = db.query(models.FaroSeason).filter(models.FaroSeason.id == season_id).first()
        season_name = season.name if season else f"Temporada {season_id}"

    # 2. Get all active houses
    houses = db.query(models.GloryHouse).filter(models.GloryHouse.status == "Activo").order_by(models.GloryHouse.name.asc()).all()

    # 3. Get all sessions for the season
    sessions = db.query(
        models.GloryHouseSession
    ).filter(
        models.GloryHouseSession.season_id == season_id
    ).all()
    
    # Group sessions by house
    sessions_by_house = collections.defaultdict(list)
    for s in sessions:
        sessions_by_house[s.glory_house_id].append(s)
        
    # Get attendance counts per session
    attendance_counts = db.query(
        models.GloryHouseAttendance.session_id,
        func.count(models.GloryHouseAttendance.id).label("cnt")
    ).group_by(models.GloryHouseAttendance.session_id).all()
    att_map = {row.session_id: row.cnt for row in attendance_counts}

    # 4. Build the dense JSON
    despliegue = []
    for house in houses:
        house_sessions = sorted(sessions_by_house.get(house.id, []), key=lambda x: x.session_date)
        matrix = []
        for idx, s in enumerate(house_sessions):
            matrix.append({
                "week": idx + 1,
                "status": s.status,
                "date": s.session_date.isoformat(),
                "attendance": att_map.get(s.id, 0),
                "reason": s.cancellation_reason
            })
        
        realizadas = sum(1 for m in matrix if m["status"] == "Realizada")
        total = len(matrix)
        compliance_rate = round((realizadas / total) * 100, 1) if total > 0 else 0
        
        despliegue.append({
            "house_id": house.id,
            "code": house.code,
            "name": house.name,
            "expected_day": house.day_of_week,
            "leader_name": house.leader_name,
            "compliance_matrix": matrix,
            "compliance_rate": compliance_rate
        })
        
    return {
        "season": season_name,
        "total_houses": len(houses),
        "despliegue": despliegue
    }
"""

content += new_endpoint

with open("d:/ccf/backend/api/evangelism_faro.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Python modifications done")
