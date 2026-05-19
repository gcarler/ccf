f = open('backend/api/crm.py', encoding='utf-8')
c = f.read()
f.close()

n1_old = """    sessions_data = []
    for s in sessions:
        att_count = db.query(models.GloryHouseAttendance).filter(models.GloryHouseAttendance.session_id == s.id).count()
        season = db.query(models.FaroSeason).filter(models.FaroSeason.id == s.season_id).first()
        sessions_data.append({
            "id": s.id,
            "session_date": s.session_date.isoformat(),
            "status": s.status,
            "season_name": season.name if season else None,
            "attendance_count": att_count
        })"""

n1_new = """    # Batch queries to avoid N+1
    if sessions:
        from sqlalchemy import func as _func
        session_ids = [s.id for s in sessions]
        season_ids = list({s.season_id for s in sessions})
        att_rows = db.query(
            models.GloryHouseAttendance.session_id,
            _func.count(models.GloryHouseAttendance.id).label("cnt")
        ).filter(models.GloryHouseAttendance.session_id.in_(session_ids)).group_by(
            models.GloryHouseAttendance.session_id
        ).all()
        att_map = {r.session_id: r.cnt for r in att_rows}
        seasons_batch = db.query(models.FaroSeason).filter(models.FaroSeason.id.in_(season_ids)).all()
        season_map = {s.id: s.name for s in seasons_batch}
    else:
        att_map, season_map = {}, {}

    sessions_data = [
        {
            "id": s.id,
            "session_date": s.session_date.isoformat(),
            "status": s.status,
            "season_name": season_map.get(s.season_id),
            "attendance_count": att_map.get(s.id, 0)
        }
        for s in sessions
    ]"""

if n1_old in c:
    c = c.replace(n1_old, n1_new)
    # Also fix lat/lon serialization
    c = c.replace(
        '        "latitude": house.latitude,\n        "longitude": house.longitude,',
        '        "latitude": float(house.latitude) if house.latitude else None,\n        "longitude": float(house.longitude) if house.longitude else None,'
    )
    c = c.replace(
        '        "day_of_week": getattr(house, "day_of_week", None),\n        "time": getattr(house, "time", None),',
        '        "day_of_week": house.day_of_week,\n        "time": house.time,'
    )
    open('backend/api/crm.py', 'w', encoding='utf-8').write(c)
    print("N+1 fix applied")
else:
    # Try with CRLF
    n1_old_crlf = n1_old.replace('\n', '\r\n')
    if n1_old_crlf in c:
        c = c.replace(n1_old_crlf, n1_new)
        open('backend/api/crm.py', 'w', encoding='utf-8').write(c)
        print("N+1 fix applied (CRLF)")
    else:
        print("WARN: pattern not found, check manually")
        # Find and print context
        idx = c.find('sessions_data = []\n    for s in sessions:')
        if idx < 0:
            idx = c.find('sessions_data = []\r\n    for s in sessions:')
        print(f"Found at idx: {idx}")
        if idx > 0:
            print(repr(c[idx:idx+300]))
