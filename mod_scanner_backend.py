import codecs
import re

with codecs.open('backend/api/crm.py', 'r', 'utf-8') as f:
    c = f.read()

# 1. Update validation endpoint to accept event_id
sig_old = """def validate_scanner_token(
    token: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):"""

sig_new = """def validate_scanner_token(
    token: str,
    event_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):"""

c = c.replace(sig_old, sig_new)

# 2. Add attendance logic
ret_old = """        return {
            "valid": True,
            "member_id": member.id,
            "name": f"{member.first_name} {member.last_name}",
            "role": member.church_role,
            "status": member.spiritual_status,
            "timestamp": utc_now().isoformat()
        }"""

ret_new = """        if event_id:
            event = db.query(models.CrmEvent).filter(models.CrmEvent.id == event_id).first()
            if event:
                today = utc_now().date()
                existing = db.query(models.EventAttendance).filter(
                    models.EventAttendance.event_id == event_id,
                    models.EventAttendance.session_date == today,
                    models.EventAttendance.member_id == member.id
                ).first()
                if not existing:
                    attendance = models.EventAttendance(
                        event_id=event_id,
                        session_date=today,
                        member_id=member.id,
                        attended=True
                    )
                    db.add(attendance)
                    db.commit()

        return {
            "valid": True,
            "member_id": member.id,
            "member_name": f"{member.first_name} {member.last_name}",
            "role": member.church_role,
            "status": member.spiritual_status,
            "timestamp": utc_now().isoformat()
        }"""

c = c.replace(ret_old, ret_new)
# Fix member_name mismatch (it was 'name' instead of 'member_name' in the old endpoint but frontend used `result.member_name`)

with codecs.open('backend/api/crm.py', 'w', 'utf-8') as f:
    f.write(c)

print("Backend scanner endpoint updated")
