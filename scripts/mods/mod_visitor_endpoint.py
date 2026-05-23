import codecs
import re

with codecs.open("backend/api/crm.py", "r", "utf-8") as f:
    c = f.read()

visitor_endpoint = """
class VisitorCreate(BaseModel):
    first_name: str
    last_name: str
    phone: Optional[str] = None
    email: Optional[str] = None

@router.post("/events/{event_id}/sessions/{session_date}/visitors")
def fast_checkin_visitor(event_id: int, session_date: str, visitor: VisitorCreate, db: Session = Depends(get_db)):
    # Verify event exists
    event = db.query(models.CrmEvent).filter(models.CrmEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
        
    try:
        dt = datetime.strptime(session_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format, expected YYYY-MM-DD")
        
    # Get or Create the "Visitante Servicios" Role
    role_name = "Visitante Servicios"
    role = db.query(models.RoleDefinition).filter(models.RoleDefinition.name == role_name).first()
    if not role:
        role = models.RoleDefinition(name=role_name, is_system_locked=True)
        db.add(role)
        db.commit()
        db.refresh(role)
        
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
    db.refresh(new_visitor)
    
    # Check if a MemberRole assignment is needed
    if role:
        mr = models.MemberRole(member_id=new_visitor.id, role_id=role.id)
        db.add(mr)
    
    # Mark as attended for this session
    attendance = models.EventAttendance(
        event_id=event_id,
        session_date=dt,
        member_id=new_visitor.id,
        attended=True
    )
    db.add(attendance)
    db.commit()
    
    return {"status": "success", "visitor_id": new_visitor.id, "message": "Visitante registrado y marcado como presente"}
"""

if "def fast_checkin_visitor" not in c:
    c += visitor_endpoint
    with codecs.open("backend/api/crm.py", "w", "utf-8") as f:
        f.write(c)
    print("Fast check-in endpoint added")
else:
    print("Already exists")
