import codecs
import re

with codecs.open("backend/api/crm.py", "r", "utf-8") as f:
    c = f.read()

analytics_endpoint = """
@router.get("/events/analytics/global")
def get_global_event_analytics(
    period: str = Query("MONTH"),
    event_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    from sqlalchemy import func
    from datetime import datetime
    import calendar
    import math

    # Base query for attendance
    q = db.query(
        models.EventAttendance.session_date,
        func.count(models.EventAttendance.id).label('attended_count')
    ).join(models.CrmEvent)

    if event_type and event_type != "ALL":
        q = q.filter(models.CrmEvent.event_type == event_type)

    # Group by session_date (since multiple events might happen on same date, we aggregate per day first)
    daily_stats = q.group_by(models.EventAttendance.session_date).all()
    
    # Python aggregation for time buckets
    bucket_map = {}
    
    for row in daily_stats:
        d = row.session_date
        if not d: continue
        
        # Determine bucket key
        if period == "WEEK":
            # format: YYYY-Www
            isocal = d.isocalendar()
            key = f"{isocal[0]}-W{isocal[1]:02d}"
            label = f"Sem {isocal[1]}, {isocal[0]}"
        elif period == "MONTH":
            key = d.strftime("%Y-%m")
            label = f"{calendar.month_abbr[d.month]} {d.year}"
        elif period == "BIMESTER":
            bimester = math.ceil(d.month / 2)
            key = f"{d.year}-B{bimester}"
            label = f"Bimestre {bimester}, {d.year}"
        elif period == "TRIMESTER":
            trimester = math.ceil(d.month / 3)
            key = f"{d.year}-Q{trimester}"
            label = f"Trim {trimester}, {d.year}"
        elif period == "SEMESTER":
            semester = math.ceil(d.month / 6)
            key = f"{d.year}-S{semester}"
            label = f"Semestre {semester}, {d.year}"
        elif period == "YEAR":
            key = f"{d.year}"
            label = f"{d.year}"
        else: # Default MONTH
            key = d.strftime("%Y-%m")
            label = f"{calendar.month_abbr[d.month]} {d.year}"
            
        if key not in bucket_map:
            bucket_map[key] = {"key": key, "label": label, "total": 0, "sessions": 0}
            
        bucket_map[key]["total"] += row.attended_count
        bucket_map[key]["sessions"] += 1

    # Format result
    series = []
    for k in sorted(bucket_map.keys()):
        b = bucket_map[k]
        b["avg"] = round(b["total"] / b["sessions"]) if b["sessions"] > 0 else 0
        series.append(b)

    # Calculate Global KPIs
    total_attendance = sum(b["total"] for b in bucket_map.values())
    total_sessions = sum(b["sessions"] for b in bucket_map.values())
    avg_per_session = round(total_attendance / total_sessions) if total_sessions > 0 else 0
    
    peak_period = max(series, key=lambda x: x["total"]) if series else {"label": "N/A", "total": 0}

    # Growth Trend (Last vs Previous)
    trend = 0
    if len(series) >= 2:
        last = series[-1]["total"]
        prev = series[-2]["total"]
        if prev > 0:
            trend = round(((last - prev) / prev) * 100, 1)

    return {
        "kpis": {
            "total_attendance": total_attendance,
            "avg_per_session": avg_per_session,
            "peak_period": peak_period,
            "trend_percentage": trend
        },
        "series": series
    }
"""

if "def get_global_event_analytics" not in c:
    c = c.replace(
        '@router.get("/events/dashboard-stats")',
        analytics_endpoint + '\n@router.get("/events/dashboard-stats")',
    )
    with codecs.open("backend/api/crm.py", "w", "utf-8") as f:
        f.write(c)
    print("Backend endpoint injected")
else:
    print("Endpoint already exists")
