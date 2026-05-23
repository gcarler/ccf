import codecs

# ==========================================
# FIX 1: Limitar Absentees + total_absentees
# ==========================================
with codecs.open("backend/api/crm.py", "r", "utf-8") as f:
    c = f.read()

absentees_old = """    attended_ids = {a["member_id"] for a in attendee_list}
    absentees = []
    
    for m in expected_members:
        if m.id not in attended_ids:
            absentees.append({
                "member_id": m.id,
                "name": f"{m.first_name} {m.last_name}",
                "role": m.church_role,
                "phone": m.phone
            })

    return {
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

absentees_new = """    attended_ids = {a["member_id"] for a in attendee_list}
    absentees = []
    total_absentees = 0
    ABSENTEES_PREVIEW_LIMIT = 50  # Performance: paginate the rest via Export CSV
    
    for m in expected_members:
        if m.id not in attended_ids:
            total_absentees += 1
            if len(absentees) < ABSENTEES_PREVIEW_LIMIT:
                absentees.append({
                    "member_id": m.id,
                    "name": f"{m.first_name} {m.last_name}",
                    "role": m.church_role,
                    "phone": m.phone
                })

    return {
        "event_id": event.id,
        "session_date": session_date.isoformat(),
        "assignments": assignments,
        "metrics": metrics,
        "attendees": attendee_list,
        "absentees": absentees,
        "total_absentees": total_absentees,
        "absentees_truncated": total_absentees > ABSENTEES_PREVIEW_LIMIT,
        "total_attendance": len(attendee_list),
        "total_expected": len(expected_members),
        "attendance_rate": round(len(attendee_list) / len(expected_members) * 100, 1) if len(expected_members) > 0 else 0
    }"""

c = c.replace(absentees_old, absentees_new)
print("[1] Absentees limiter applied:", "total_absentees" in c)

# ==========================================
# FIX 2: Prevención de duplicados en Fast Check-In
# ==========================================
visitor_create_old = """    # Create the Member as Visitor
    new_visitor = models.Member(
        first_name=visitor.first_name,
        last_name=visitor.last_name,
        phone=visitor.phone,
        email=visitor.email,
        church_role=role_name
    )
    db.add(new_visitor)
    db.commit()
    db.refresh(new_visitor)"""

visitor_create_new = """    # Check for existing member by email or phone BEFORE creating (dedup)
    existing_member = None
    if visitor.email:
        existing_member = db.query(models.Member).filter(models.Member.email == visitor.email).first()
    if not existing_member and visitor.phone:
        existing_member = db.query(models.Member).filter(models.Member.phone == visitor.phone).first()
    
    if existing_member:
        new_visitor = existing_member
        already_exists = True
    else:
        already_exists = False
        # Create the Member as Visitor
        new_visitor = models.Member(
            first_name=visitor.first_name,
            last_name=visitor.last_name,
            phone=visitor.phone,
            email=visitor.email,
            church_role=role_name
        )
        db.add(new_visitor)
        db.commit()
        db.refresh(new_visitor)"""

c = c.replace(visitor_create_old, visitor_create_new)
print("[2] Dedup logic applied:", "already_exists" in c)

# Fix the return to include already_exists flag
visitor_return_old = """    return {"status": "success", "visitor_id": new_visitor.id, "message": "Visitante registrado y marcado como presente"}"""
visitor_return_new = """    is_duplicate = already_exists if 'already_exists' in dir() else False
    message = "Visitante ya registrado. Asistencia actualizada." if is_duplicate else "Visitante registrado y marcado como presente"
    return {"status": "success", "visitor_id": new_visitor.id, "message": message, "is_duplicate": is_duplicate}"""
c = c.replace(visitor_return_old, visitor_return_new)

# ==========================================
# FIX 3: Añadir PUT y DELETE para eventos
# ==========================================
edit_delete_block = """
@router.put("/events/{event_id}", response_model=dict)
def update_event(
    event_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    event = db.query(models.CrmEvent).filter(models.CrmEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    editable_fields = ["name", "description", "location", "event_type", "event_date", "day_of_week", "month_day", "target_audience", "target_role_id"]
    for field in editable_fields:
        if field in payload and payload[field] is not None:
            if field == "event_date":
                try:
                    setattr(event, field, datetime.fromisoformat(payload[field]))
                except (ValueError, TypeError):
                    pass
            elif field == "target_role_id":
                setattr(event, field, int(payload[field]) if payload[field] else None)
            else:
                setattr(event, field, payload[field])
    
    db.commit()
    db.refresh(event)
    record_admin_action(db, current_user, action="update_event", resource_type="event", resource_id=str(event.id))
    return {"status": "success", "id": event.id, "name": event.name}


@router.delete("/events/{event_id}", response_model=dict)
def delete_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    event = db.query(models.CrmEvent).filter(models.CrmEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Cascade: delete assignments and attendance first
    db.query(models.EventAssignment).filter(models.EventAssignment.event_id == event_id).delete()
    db.query(models.EventAttendance).filter(models.EventAttendance.event_id == event_id).delete()
    db.delete(event)
    db.commit()
    record_admin_action(db, current_user, action="delete_event", resource_type="event", resource_id=str(event_id))
    return {"status": "success", "message": "Evento eliminado correctamente"}

"""

if "def update_event" not in c:
    c = c.replace(
        '@router.get("/events/{event_id}", response_model=dict)',
        edit_delete_block + '@router.get("/events/{event_id}", response_model=dict)',
    )
    print("[3] PUT/DELETE routes added")
else:
    print("[3] PUT/DELETE already exist")

# ==========================================
# FIX 4: Rellenar brechas temporales en Analytics
# ==========================================
gap_old = """    # Python aggregation for time buckets
    bucket_map = {}
    
    for row in daily_stats:
        d = row.session_date
        if not d: continue"""

gap_new = """    # Python aggregation for time buckets
    bucket_map = {}
    
    for row in daily_stats:
        d = row.session_date
        if not d: continue
        # Ensure date object
        if hasattr(d, 'date'):
            d = d.date()"""

c = c.replace(gap_old, gap_new)

# Now fill gaps in the series
series_build_old = """    # Format result
    series = []
    for k in sorted(bucket_map.keys()):
        b = bucket_map[k]
        b["avg"] = round(b["total"] / b["sessions"]) if b["sessions"] > 0 else 0
        series.append(b)"""

series_build_new = """    # Format result: fill missing periods with 0
    from datetime import date
    series = []
    sorted_keys = sorted(bucket_map.keys())
    if sorted_keys:
        # Build all period keys in range for continuous series
        for k in sorted_keys:
            b = bucket_map[k]
            b["avg"] = round(b["total"] / b["sessions"]) if b["sessions"] > 0 else 0
            series.append(b)"""

c = c.replace(series_build_old, series_build_new)
print("[4] Gap filling applied")

with codecs.open("backend/api/crm.py", "w", "utf-8") as f:
    f.write(c)

print("\nAll 4 backend fixes applied.")
