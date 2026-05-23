import codecs
import re

with codecs.open("backend/api/crm.py", "r", "utf-8") as f:
    c = f.read()

# I need to add an import for fastapi.responses.StreamingResponse if it doesn't exist.
if "from fastapi.responses import StreamingResponse" not in c:
    c = c.replace(
        "from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File",
        "from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File\nfrom fastapi.responses import StreamingResponse",
    )

if "import io" not in c:
    c = c.replace("import uuid", "import uuid\nimport io\nimport csv")

export_endpoint = """
@router.get("/events/{event_id}/sessions/{session_date}/export")
def export_event_session_report(
    event_id: int,
    session_date: datetime.date,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    event = db.query(models.CrmEvent).filter(models.CrmEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    attendances_db = db.query(models.EventAttendance).filter(
        models.EventAttendance.event_id == event_id,
        models.EventAttendance.session_date == session_date
    ).all()
    attended_ids = {a.member_id for a in attendances_db}

    # Determine Universe Expected
    if event.target_audience == "ROLE" and event.target_role_id:
        target_role = db.query(models.RoleDefinition).filter(models.RoleDefinition.id == event.target_role_id).first()
        expected_members = db.query(models.Member).filter(models.Member.church_role == target_role.name).all() if target_role else []
    else:
        expected_members = db.query(models.Member).all()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=',', quoting=csv.QUOTE_MINIMAL)
    
    # Headers
    writer.writerow(["Nombre", "Apellido", "Telefono", "Email", "Rol", "Estado Asistencia"])
    
    # Write attendees
    for member in expected_members:
        status = "Presente" if member.id in attended_ids else "Ausente"
        writer.writerow([
            member.first_name,
            member.last_name,
            member.phone or "",
            member.email or "",
            member.church_role or "Miembro",
            status
        ])
        
    # Write attendees who were not originally expected (e.g. Visitors added manually)
    expected_ids = {m.id for m in expected_members}
    for att in attendances_db:
        if att.member_id not in expected_ids:
            member = att.member
            if member:
                writer.writerow([
                    member.first_name,
                    member.last_name,
                    member.phone or "",
                    member.email or "",
                    member.church_role or "Visitante Servicios",
                    "Presente (Invitado/No Esperado)"
                ])

    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]), 
        media_type="text/csv", 
        headers={"Content-Disposition": f"attachment; filename=reporte_asistencia_{event.name}_{session_date}.csv"}
    )
"""

if "def export_event_session_report" not in c:
    c += export_endpoint
    with codecs.open("backend/api/crm.py", "w", "utf-8") as f:
        f.write(c)
    print("Export endpoint added")
else:
    print("Export endpoint already exists")
