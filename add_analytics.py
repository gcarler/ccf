import sys
import collections
from datetime import datetime

with open('backend/api/crm.py', 'r', encoding='utf-8') as f:
    c = f.read()

analytics_endpoint = """
@router.get("/events/{event_id}/analytics")
def get_event_analytics(event_id: int, db: Session = Depends(get_db)):
    event = db.query(models.CrmEvent).filter(models.CrmEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
        
    attendances = db.query(models.EventAttendance).filter(models.EventAttendance.event_id == event_id).all()
    
    # Group by month (YYYY-MM) and session_date
    # We want to find the average attendance per session for each month
    sessions_by_month = collections.defaultdict(set)
    attendees_by_session = collections.defaultdict(int)
    
    for att in attendances:
        if att.session_date:
            month_key = att.session_date.strftime("%Y-%m")
            sessions_by_month[month_key].add(att.session_date)
            attendees_by_session[att.session_date] += 1
            
    monthly_data = []
    total_sessions = 0
    total_attendance_all = 0
    peak_month = {"month": "-", "avg": 0}
    
    for month in sorted(sessions_by_month.keys()):
        sessions = sessions_by_month[month]
        total_att_month = sum(attendees_by_session[s] for s in sessions)
        avg_att = round(total_att_month / len(sessions)) if sessions else 0
        
        monthly_data.append({
            "month": month,
            "avg_attendance": avg_att,
            "total_sessions": len(sessions)
        })
        
        total_sessions += len(sessions)
        total_attendance_all += total_att_month
        
        if avg_att > peak_month["avg"]:
            peak_month = {"month": month, "avg": avg_att}
            
    historical_avg = round(total_attendance_all / total_sessions) if total_sessions > 0 else 0
    
    # Calculate growth trend (last month vs previous month)
    trend = 0
    if len(monthly_data) >= 2:
        last = monthly_data[-1]["avg_attendance"]
        prev = monthly_data[-2]["avg_attendance"]
        if prev > 0:
            trend = round(((last - prev) / prev) * 100, 1)
            
    return {
        "monthly_data": monthly_data,
        "kpis": {
            "historical_avg": historical_avg,
            "peak_month": peak_month,
            "trend_percentage": trend
        }
    }
"""

if "def get_event_analytics" not in c:
    c += analytics_endpoint
    with open('backend/api/crm.py', 'w', encoding='utf-8') as f:
        f.write(c)
    print("Endpoint added!")
else:
    print("Endpoint already exists!")
