import json

from pydantic import BaseModel

new_endpoints = """
# --- DYNAMIC ROLES ---

class RoleDefinitionCreate(BaseModel):
    name: str
    color: str
    is_leadership: bool

class RoleDefinitionUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    is_leadership: Optional[bool] = None

@router.get("/roles")
def get_roles(db: Session = Depends(get_db)):
    roles = db.query(models.RoleDefinition).order_by(models.RoleDefinition.is_leadership.desc(), models.RoleDefinition.name.asc()).all()
    return roles

@router.post("/roles")
def create_role(payload: RoleDefinitionCreate, db: Session = Depends(get_db), current_user: models.User = Depends(require_pastor_or_admin)):
    exists = db.query(models.RoleDefinition).filter(models.RoleDefinition.name == payload.name).first()
    if exists:
        raise HTTPException(status_code=400, detail="El rol ya existe")
    r = models.RoleDefinition(**payload.dict())
    db.add(r)
    db.commit()
    db.refresh(r)
    return r

@router.put("/roles/{role_id}")
def update_role(role_id: int, payload: RoleDefinitionUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(require_pastor_or_admin)):
    r = db.query(models.RoleDefinition).filter(models.RoleDefinition.id == role_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    
    if payload.name is not None:
        # Check unique
        exists = db.query(models.RoleDefinition).filter(models.RoleDefinition.name == payload.name, models.RoleDefinition.id != role_id).first()
        if exists:
            raise HTTPException(status_code=400, detail="Ya existe otro rol con ese nombre")
        
        # update the members table where church_role == old name
        db.query(models.Member).filter(models.Member.church_role == r.name).update({"church_role": payload.name})
        r.name = payload.name
        
    if payload.color is not None:
        r.color = payload.color
    if payload.is_leadership is not None:
        r.is_leadership = payload.is_leadership
        
    db.commit()
    db.refresh(r)
    return r

@router.delete("/roles/{role_id}")
def delete_role(role_id: int, fallback_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(require_pastor_or_admin)):
    if fallback_id == role_id:
        raise HTTPException(status_code=400, detail="El rol de reemplazo no puede ser el mismo rol a eliminar")
        
    r = db.query(models.RoleDefinition).filter(models.RoleDefinition.id == role_id).first()
    fallback = db.query(models.RoleDefinition).filter(models.RoleDefinition.id == fallback_id).first()
    
    if not r:
        raise HTTPException(status_code=404, detail="Rol a eliminar no encontrado")
    if not fallback:
        raise HTTPException(status_code=400, detail="Rol de reemplazo no valido")
        
    # Reassign members
    db.query(models.Member).filter(models.Member.church_role == r.name).update({"church_role": fallback.name})
    
    # Delete role
    db.delete(r)
    db.commit()
    return {"success": True, "message": "Rol eliminado y miembros reasignados correctamente"}
"""

with open("backend/api/crm.py", "a", encoding="utf-8") as f:
    f.write(new_endpoints)
