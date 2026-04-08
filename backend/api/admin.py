from __future__ import annotations
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.auth import require_admin
from backend import models, schemas, crud

router = APIRouter()

@router.get("/roles", response_model=List[Dict[str, Any]])
def list_roles(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin)
):
    """Lista todos los roles y el conteo de usuarios vinculados."""
    roles = db.query(models.Role).all()
    result = []
    for r in roles:
        count = db.query(models.User).filter(models.User.role_id == r.role_id).count()
        result.append({
            "id": r.role_id,
            "name": r.name,
            "permissions": r.permissions or {},
            "users_count": count
        })
    return result

@router.post("/roles", response_model=Dict[str, Any])
def create_role(
    name: str,
    permissions: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin)
):
    """Crea un nuevo rol ministerial."""
    role = models.Role(name=name, permissions=permissions)
    db.add(role)
    db.commit()
    db.refresh(role)
    return {"id": role.role_id, "name": role.name}

@router.patch("/roles/{role_id}")
def update_role(
    role_id: int,
    permissions: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin)
):
    """Actualiza los permisos de un rol."""
    role = db.query(models.Role).filter(models.Role.role_id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    role.permissions = permissions
    db.commit()
    return {"status": "success"}

# --- CHURCH LOCATIONS ---

@router.get("/locations", response_model=List[Dict[str, Any]])
def list_locations(db: Session = Depends(get_db)):
    """Lista todas las sedes de la iglesia."""
    locs = db.query(models.ChurchLocation).all()
    return [{"id": l.id, "name": l.name, "address": l.address, "pastor": l.pastor_name, "active": l.is_active, "type": l.location_type} for l in locs]

@router.post("/locations")
def create_location(payload: Dict[str, Any], db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    """Crea una nueva sede o anexo."""
    loc = models.ChurchLocation(
        name=payload["name"],
        address=payload.get("address"),
        pastor_name=payload.get("pastor"),
        location_type=payload.get("type", "Sede")
    )
    db.add(loc)
    db.commit()
    return {"status": "success"}

# --- SOCIAL CHANNELS ---

@router.get("/socials", response_model=List[Dict[str, Any]])
def list_socials(db: Session = Depends(get_db)):
    """Lista canales sociales oficiales."""
    channels = db.query(models.SocialChannel).all()
    return [{"id": c.id, "platform": c.platform, "url": c.url, "visible": c.is_visible} for c in channels]

# --- SYSTEM VARIABLES ---

@router.get("/variables")
def list_variables(db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    """Obtiene variables de configuración global del sistema."""
    vars = db.query(models.SystemVariable).all()
    return {v.key: v.value for v in vars}

@router.post("/variables")
def set_variable(key: str, value: str, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    """Define o actualiza una variable de sistema."""
    var = db.query(models.SystemVariable).filter(models.SystemVariable.key == key).first()
    if var:
        var.value = value
    else:
        var = models.SystemVariable(key=key, value=value)
        db.add(var)
    db.commit()
    return {"status": "success"}

# --- USER MANAGEMENT ---

@router.get("/users", response_model=List[Dict[str, Any]])
def list_admin_users(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin)
):
    """Lista usuarios para gestión de permisos."""
    users = db.query(models.User).all()
    result = []
    for u in users:
        result.append({
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role,
            "role_id": u.role_id,
            "is_active": u.is_active
        })
    return result

@router.patch("/users/{user_id}/role")
def change_user_role(
    user_id: int,
    role_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin)
):
    """Asigna un rol de sistema a un usuario."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    role = db.query(models.Role).filter(models.Role.role_id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
        
    user.role_id = role_id
    user.role = role.name.lower().replace(" ", "_") # Sync legacy field
    db.commit()
    return {"status": "success", "new_role": role.name}

# --- AUDIT & SECURITY ---

@router.get("/audit", response_model=List[Dict[str, Any]])
def list_admin_audit(
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin)
):
    """Obtiene el historial de auditoría del sistema."""
    logs = crud.get_admin_audit_logs(db, limit=limit)
    result = []
    for l in logs:
        result.append({
            "id": l.id,
            "actor_user_id": l.actor_user_id,
            "action": l.action,
            "resource_type": l.resource_type,
            "resource_id": l.resource_id,
            "created_at": l.created_at.isoformat(),
            "metadata": l.metadata_json or {}
        })
    return result

# --- FORUM MODERATION ---

@router.get("/comments", response_model=List[Dict[str, Any]])
def list_all_comments(db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    """Lista todos los comentarios para moderación."""
    comments = db.query(models.ForumComment).order_by(models.ForumComment.created_at.desc()).all()
    result = []
    for c in comments:
        user = db.query(models.User).filter(models.User.id == c.author_id).first()
        thread = db.query(models.ForumThread).filter(models.ForumThread.id == c.thread_id).first()
        result.append({
            "id": c.id,
            "author": user.username if user else "Anónimo",
            "text": c.content,
            "context": thread.title if thread else "General",
            "type": thread.category if thread else "Foro",
            "created_at": c.created_at.isoformat()
        })
    return result

@router.delete("/comments/{comment_id}")
def delete_comment(comment_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    """Elimina un comentario por moderación."""
    comment = db.query(models.ForumComment).filter(models.ForumComment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    db.delete(comment)
    db.commit()
    return {"status": "success"}

# --- ANNOUNCEMENTS ---

@router.get("/announcements", response_model=List[Dict[str, Any]])
def list_announcements(db: Session = Depends(get_db)):
    """Lista todos los anuncios ministeriales."""
    anns = db.query(models.Announcement).order_by(models.Announcement.published_at.desc()).all()
    return [{
        "id": a.id,
        "title": a.title,
        "content": a.content,
        "category": a.category,
        "featured": a.is_featured,
        "date": a.published_at.isoformat()
    } for a in anns]

@router.post("/announcements")
def create_announcement(payload: Dict[str, Any], db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    """Crea un nuevo comunicado global."""
    ann = models.Announcement(
        title=payload["title"],
        content=payload["content"],
        category=payload.get("category", "General"),
        is_featured=payload.get("featured", False)
    )
    db.add(ann)
    db.commit()
    return {"status": "success"}

# --- TESTIMONIALS ---

@router.get("/testimonials", response_model=List[Dict[str, Any]])
def list_testimonials(db: Session = Depends(get_db)):
    """Lista todos los testimonios para moderación."""
    tests = db.query(models.Testimonial).order_by(models.Testimonial.created_at.desc()).all()
    return [{
        "id": t.id,
        "content": t.content,
        "emotion": t.emotion,
        "is_approved": t.is_approved,
        "show_on_home": t.show_on_home,
        "author_id": t.author_id,
        "created_at": t.created_at.isoformat()
    } for t in tests]

@router.patch("/testimonials/{test_id}")
def update_testimonial(test_id: int, payload: Dict[str, Any], db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    """Aprueba o destaca un testimonio."""
    test = db.query(models.Testimonial).filter(models.Testimonial.id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Testimonial not found")
    
    if "is_approved" in payload:
        test.is_approved = payload["is_approved"]
    if "show_on_home" in payload:
        test.show_on_home = payload["show_on_home"]
        
    db.commit()
    return {"status": "success"}

# --- SPIRITUAL MILESTONES (BADGES) ---

@router.get("/milestones", response_model=List[Dict[str, Any]])
def list_milestones(db: Session = Depends(get_db)):
    """Lista hitos espirituales (insignias) y estadísticas de obtención."""
    badges = db.query(models.Badge).all()
    result = []
    for b in badges:
        count = db.query(models.UserBadge).filter(models.UserBadge.badge_id == b.id).count()
        result.append({
            "id": b.id,
            "name": b.name,
            "description": b.description,
            "icon": b.icon_key,
            "xp": b.xp_reward,
            "count": count
        })
    return result

@router.post("/milestones/award")
def award_milestone_bulk(payload: Dict[str, Any], db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    """Asigna un hito a una lista de miembros de forma masiva."""
    badge_id = payload["badge_id"]
    member_ids = payload["member_ids"] # List of member IDs
    
    awarded_count = 0
    for m_id in member_ids:
        member = db.query(models.Member).filter(models.Member.id == m_id).first()
        if member and member.user_id:
            # Verificar si ya lo tiene
            exists = db.query(models.UserBadge).filter(
                models.UserBadge.user_id == member.user_id,
                models.UserBadge.badge_id == badge_id
            ).first()
            
            if not exists:
                ub = models.UserBadge(user_id=member.user_id, badge_id=badge_id)
                db.add(ub)
                awarded_count += 1
                
    db.commit()
    return {"status": "success", "awarded": awarded_count}

# --- DONATION CATEGORIES ---

@router.get("/donation-categories", response_model=List[Dict[str, Any]])
def list_donation_categories(db: Session = Depends(get_db)):
    """Lista categorías de recaudación (Diezmos, Misiones, etc)."""
    cats = db.query(models.DonationCategory).all()
    return [{
        "id": c.id,
        "name": c.name,
        "description": c.description,
        "color": c.color_code,
        "active": c.is_active
    } for c in cats]

@router.post("/donation-categories")
def create_donation_category(payload: Dict[str, Any], db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    """Crea una nueva categoría de donación."""
    cat = models.DonationCategory(
        name=payload["name"],
        description=payload.get("description"),
        color_code=payload.get("color", "blue")
    )
    db.add(cat)
    db.commit()
    return {"status": "success"}

# --- CRM AUTOMATIONS ---

@router.get("/automations", response_model=List[Dict[str, Any]])
def list_automations(db: Session = Depends(get_db)):
    """Lista reglas de automatización configuradas."""
    rules = db.query(models.CrmAutomation).all()
    return [{
        "id": r.id,
        "name": r.name,
        "trigger": r.trigger_event,
        "action": r.action_type,
        "payload": r.action_payload or {},
        "active": r.is_active
    } for r in rules]

@router.post("/automations")
def create_automation(payload: Dict[str, Any], db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    """Crea una nueva regla de automatización pastoral."""
    rule = models.CrmAutomation(
        name=payload["name"],
        trigger_event=payload["trigger"],
        action_type=payload["action"],
        action_payload=payload.get("payload", {})
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return {"status": "success", "id": rule.id}

@router.patch("/automations/{rule_id}")
def update_automation(rule_id: int, payload: Dict[str, Any], db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    """Actualiza una regla de automatización (nombre, trigger, acción, activo)."""
    rule = db.query(models.CrmAutomation).filter(models.CrmAutomation.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Automation rule not found")
    if "name" in payload:
        rule.name = payload["name"]
    if "trigger" in payload:
        rule.trigger_event = payload["trigger"]
    if "action" in payload:
        rule.action_type = payload["action"]
    if "payload" in payload:
        rule.action_payload = payload["payload"]
    if "active" in payload:
        rule.is_active = payload["active"]
    db.commit()
    return {"status": "success"}

@router.delete("/automations/{rule_id}")
def delete_automation(rule_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    """Elimina una regla de automatización permanentemente."""
    rule = db.query(models.CrmAutomation).filter(models.CrmAutomation.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Automation rule not found")
    db.delete(rule)
    db.commit()
    return {"status": "success"}

