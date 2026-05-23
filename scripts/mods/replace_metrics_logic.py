import re
import sys

with open("backend/api/crm.py", "r", encoding="utf-8") as f:
    c = f.read()

old_logic = """    liderazgo_roles = ["Apstol", "Profeta", "Evangelista", "Pastor", "Maestro", "Lder"]

    metrics = {
        "Liderazgo": 0,
        "Servidor": 0,
        "Miembro Bautizado": 0,
        "Asistente": 0,
        "Visitante Servicios": 0,
        "Visitante Faro en Casa": 0,
        "Visitante Online": 0,
        "Otros": 0
    }

    attendee_list = []
    for att in attendances_db:
        member = att.member
        if not member:
            continue
        
        role = member.church_role or "Miembro"
        # Categorize
        if role in liderazgo_roles:
            metrics["Liderazgo"] += 1
        elif role == "Servidor":
            metrics["Servidor"] += 1
        elif role == "Miembro Bautizado":
            metrics["Miembro Bautizado"] += 1
        elif role in ["Asistentes", "Asistente"]:
            metrics["Asistente"] += 1
        elif "Visitante Servicios" in role:
            metrics["Visitante Servicios"] += 1
        elif "Visitante Faro" in role:
            metrics["Visitante Faro en Casa"] += 1
        elif "Online" in role:
            metrics["Visitante Online"] += 1
        else:
            metrics["Otros"] += 1

        attendee_list.append({
            "member_id": member.id,
            "name": f"{member.first_name} {member.last_name}",
            "role": role,
            "scanned_at": att.scanned_at.isoformat() if att.scanned_at else None
        })"""

# Handle encoding issues in string literal
match = re.search(
    r"    liderazgo_roles = .*?        attendee_list\.append\(\{.*?\}\)",
    c,
    flags=re.DOTALL,
)
if not match:
    print("Could not find the block to replace!")
    sys.exit(1)

new_logic = """    
    roles_db = db.query(models.RoleDefinition).all()
    roles_map = {r.name: r for r in roles_db}
    
    metrics = {"Liderazgo": 0}
    for r in roles_db:
        if not r.is_leadership:
            metrics[r.name] = 0
    metrics["Otros"] = 0

    attendee_list = []
    for att in attendances_db:
        member = att.member
        if not member:
            continue
        
        role_name = member.church_role or "Miembro"
        role_def = roles_map.get(role_name)
        
        if role_def and role_def.is_leadership:
            metrics["Liderazgo"] += 1
        elif role_name in metrics:
            metrics[role_name] += 1
        else:
            metrics["Otros"] += 1

        attendee_list.append({
            "member_id": member.id,
            "name": f"{member.first_name} {member.last_name}",
            "role": role_name,
            "scanned_at": att.scanned_at.isoformat() if att.scanned_at else None
        })"""

c = c[: match.start()] + new_logic + c[match.end() :]

with open("backend/api/crm.py", "w", encoding="utf-8") as f:
    f.write(c)

print("Logic replaced successfully!")
