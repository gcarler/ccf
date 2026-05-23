import sys

content = open("backend/api/evangelism.py", "r", encoding="utf-8").read()

# Replace the broken part
broken_str = """        "id": house.id,
        "name": house.name,
        "zone": house.zone,
    if value == "whatsapp":"""

fixed_str = """        "id": house.id,
        "name": house.name,
        "zone": house.zone,
        "address": house.address,
        "latitude": float(house.latitude) if house.latitude else None,
        "longitude": float(house.longitude) if house.longitude else None,
        "leader_name": house.leader_name,
        "leader_id": house.leader_id,
        "assistant_id": house.assistant_id,
        "host_id": house.host_id,
        "members_count": house.members_count,
        "capacity": house.capacity,
        "day_of_week": house.day_of_week,
        "start_time": house.start_time,
        "end_time": house.end_time,
        "status": house.status,
        "created_at": house.created_at.isoformat() if house.created_at else None,
        "sessions": sessions_data,
        "total_sessions": len(sessions_data),
        "total_attendance": sum(s["attendance_count"] for s in sessions_data),
    }

@router.post("/glory-houses", response_model=schemas.GloryHouse)
def create_glory_house(
    payload: schemas.GloryHouseCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    return crud.create_glory_house(db, payload)

@router.put("/glory-houses/{house_id}", response_model=schemas.GloryHouse)
def update_glory_house(
    house_id: int,
    payload: schemas.GloryHouseUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin)
):
    house = crud.update_glory_house(db, house_id, payload)
    if not house:
        raise HTTPException(status_code=404, detail="Glory house not found")
    return house

# --- MESSAGING & AUTOMATIONS ---

def _channel_label(channel: str) -> str:
    value = str(channel or "").strip().lower()
    if value == "whatsapp":"""

if broken_str in content:
    content = content.replace(broken_str, fixed_str)
    open("backend/api/evangelism.py", "w", encoding="utf-8").write(content)
    print("Fixed evangelism.py")
else:
    print("Broken string not found")
