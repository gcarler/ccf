import re
import sys

with open("backend/api/crm.py", "r", encoding="utf-8") as f:
    c = f.read()

# We need to find the `attendee_list` logic in `get_event_session_detail`
old_logic = """        attendee_list.append({
            "member_id": member.id,
            "name": f"{member.first_name} {member.last_name}",
            "role": role_name,
            "scanned_at": att.scanned_at.isoformat() if att.scanned_at else None
        })"""

new_logic = """        attendee_list.append({
            "member_id": member.id,
            "name": f"{member.first_name} {member.last_name}",
            "role": role_name,
            "scanned_at": att.scanned_at.isoformat() if att.scanned_at else None
        })

    # Calcular Inasistencias (Absentees)
    # 1. Determinar el Universo Esperado
    if event.target_audience == "ROLE" and event.target_role_id:
        target_role = db.query(models.RoleDefinition).filter(models.RoleDefinition.id == event.target_role_id).first()
        expected_members = db.query(models.Member).filter(models.Member.church_role == target_role.name).all() if target_role else []
    else:
        # ALL
        expected_members = db.query(models.Member).all()
        
    attended_ids = {a["member_id"] for a in attendee_list}
    absentees = []
    
    for m in expected_members:
        if m.id not in attended_ids:
            absentees.append({
                "member_id": m.id,
                "name": f"{m.first_name} {m.last_name}",
                "role": m.church_role,
                "phone": m.phone
            })"""

c = c.replace(old_logic, new_logic)

# Replace return
old_ret = """    return {
        "event_id": event.id,
        "session_date": session_date.isoformat(),
        "assignments": assignments,
        "metrics": metrics,
        "attendees": attendee_list,
        "total_attendance": len(attendee_list)
    }"""

new_ret = """    return {
        "event_id": event.id,
        "session_date": session_date.isoformat(),
        "assignments": assignments,
        "metrics": metrics,
        "attendees": attendee_list,
        "absentees": absentees,
        "total_attendance": len(attendee_list),
        "total_expected": len(expected_members),
        "attendance_rate": round(len(attendee_list) / len(expected_members) * 100, 1) if len(expected_members) > 0 else 0
    }"""

c = c.replace(old_ret, new_ret)

# ADD EVENT UPDATE AUDIENCE ENDPOINT
new_endpoint = """
class EventAudienceUpdate(BaseModel):
    target_audience: str
    target_role_id: Optional[int] = None

@router.put("/events/{event_id}/audience")
def update_event_audience(event_id: int, payload: EventAudienceUpdate, db: Session = Depends(get_db)):
    event = db.query(models.CrmEvent).filter(models.CrmEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    event.target_audience = payload.target_audience
    event.target_role_id = payload.target_role_id
    db.commit()
    return {"success": True}

@router.get("/events/dashboard-stats")
def get_events_dashboard_stats(db: Session = Depends(get_db)):
    events = db.query(models.CrmEvent).all()
    stats = []
    
    for ev in events:
        # Get the latest attendance session
        latest_att = db.query(models.EventAttendance).filter(models.EventAttendance.event_id == ev.id).order_by(models.EventAttendance.session_date.desc()).first()
        if latest_att:
            # Recompute for that day
            day = latest_att.session_date
            atts = db.query(models.EventAttendance).filter(models.EventAttendance.event_id == ev.id, models.EventAttendance.session_date == day).all()
            attended = len(atts)
            
            if ev.target_audience == "ROLE" and ev.target_role_id:
                target_role = db.query(models.RoleDefinition).filter(models.RoleDefinition.id == ev.target_role_id).first()
                expected = db.query(models.Member).filter(models.Member.church_role == target_role.name).count() if target_role else 0
            else:
                expected = db.query(models.Member).count()
                
            rate = round((attended / expected) * 100, 1) if expected > 0 else 0
            
            stats.append({
                "event_id": ev.id,
                "latest_session": day.isoformat(),
                "attended": attended,
                "expected": expected,
                "rate": rate
            })
        else:
            stats.append({
                "event_id": ev.id,
                "latest_session": None,
                "attended": 0,
                "expected": 0,
                "rate": 0
            })
            
    return stats
"""

# Append
c += new_endpoint

with open("backend/api/crm.py", "w", encoding="utf-8") as f:
    f.write(c)
print("Logic updated")
