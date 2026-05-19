from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Any, Optional
from pydantic import BaseModel
from datetime import datetime

from backend.core.database import get_db
from backend import models, schemas
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/register", response_model=schemas.MemberResponse)
def public_register_event(
    payload: schemas.PublicRegistrationCreate,
    db: Session = Depends(get_db)
) -> Any:
    """
    Registra a una persona desde un QR pblico y vincula su asistencia a un evento.
    Si la persona ya existe (por email o telfono), se usa ese perfil.
    Si no existe, se crea un nuevo Member con spiritual_status = 'Nuevo'.
    """
    event = db.query(models.CrmEvent).filter(models.CrmEvent.id == payload.event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Evento no encontrado.")

    # 1. Buscar si ya existe el miembro por email o telfono
    member = None
    if payload.email or payload.phone:
        query = db.query(models.Member)
        conditions = []
        if payload.email:
            conditions.append(models.Member.email == payload.email)
        if payload.phone:
            conditions.append(models.Member.phone == payload.phone)
        
        member = query.filter(or_(*conditions)).first()

    # 2. Si no existe, lo creamos
    if not member:
        member = models.Member(
            first_name=payload.first_name,
            last_name=payload.last_name,
            email=payload.email,
            phone=payload.phone,
            spiritual_status="Nuevo",
            church_role="Visitante"
        )
        db.add(member)
        db.commit()
        db.refresh(member)
        logger.info(f"Nuevo visitante creado desde QR: {member.first_name} {member.last_name}")

    # 3. Registrar asistencia al evento si no est registrada an
    session_date = event.event_date.date() if event.event_date else datetime.now(datetime.UTC).date()
    existing_attendance = db.query(models.EventAttendance).filter(
        models.EventAttendance.event_id == event.id,
        models.EventAttendance.session_date == session_date,
        models.EventAttendance.member_id == member.id
    ).first()

    if not existing_attendance:
        attendance = models.EventAttendance(
            event_id=event.id,
            session_date=session_date,
            member_id=member.id,
            attended=True
        )
        db.add(attendance)
        db.commit()
        logger.info(f"Asistencia registrada para {member.first_name} al evento {event.name} (ID {event.id})")

    # podramos aadirlo a una pipeline de Consolidacin. Por ahora, el hecho 
    # de tener el email/telfono y estar en la BD lo hace accesible al CRM.

    return member


@router.get("/courses", response_model=list[schemas.Course])
def public_list_courses(
    db: Session = Depends(get_db)
):
    """
    Retorna la lista de cursos públicos disponibles.
    """
    courses = db.query(models.Course).filter(models.Course.is_published == True).all()
    # Mocking lesson count dynamically if needed
    for c in courses:
        c.lesson_count = db.query(models.Lesson).filter(models.Lesson.course_id == c.id).count()
    return courses


@router.get("/courses/{course_id}", response_model=schemas.Course)
def public_get_course(
    course_id: int,
    db: Session = Depends(get_db)
):
    """
    Retorna los detalles de un curso específico.
    """
    course = db.query(models.Course).filter(
        models.Course.id == course_id, 
        models.Course.is_published == True
    ).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    course.lesson_count = db.query(models.Lesson).filter(models.Lesson.course_id == course.id).count()
    return course


@router.post("/newsletter/subscribe", response_model=schemas.NewsletterSubscriptionRead)
def public_newsletter_subscribe(
    payload: schemas.NewsletterSubscriptionCreate,
    db: Session = Depends(get_db)
):
    """
    Registra un correo en el boletín (Newsletter).
    """
    existing = db.query(models.NewsletterSubscription).filter(
        models.NewsletterSubscription.email == payload.email.strip().lower()
    ).first()
    
    if existing:
        # If it already exists, just return it as success
        return existing
        
    subscription = models.NewsletterSubscription(
        email=payload.email.strip().lower()
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


class PublicContactCreate(BaseModel):
    full_name: str
    phone: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = "prospect"
    source: Optional[str] = "conocer-a-jesus"

@router.post("/contact", response_model=dict)
def public_contact(
    payload: PublicContactCreate,
    db: Session = Depends(get_db)
):
    """
    Recibe un contacto desde un formulario pblico (ej. Conocer a Jesus).
    Crea el miembro si no existe y lo añade a un caso de consolidación.
    """
    parts = payload.full_name.strip().split(" ", 1)
    first_name = parts[0] if parts else "Anónimo"
    last_name = parts[1] if len(parts) > 1 else ""
    
    member = None
    if payload.phone:
        member = db.query(models.Member).filter(models.Member.phone == payload.phone).first()
        
    if not member:
        member = models.Member(
            first_name=first_name,
            last_name=last_name,
            phone=payload.phone,
            spiritual_status="Nuevo",
            church_role="Visitante"
        )
        db.add(member)
        db.commit()
        db.refresh(member)
        
    case = models.ConsolidationCase(
        member_id=member.id,
        stage="Nuevo",
        status="active",
        source=payload.source or "website",
        notes=payload.notes
    )
    db.add(case)
    
    # Si dejó notas/mensaje, crear una solicitud de oración para el CRM
    if payload.notes and payload.notes.strip():
        prayer = models.PrayerRequest(
            requester_name=payload.full_name,
            request_text=payload.notes,
            category="Evangelismo",
            is_public=False,
            source=payload.source or "web",
            status="pending",
        )
        db.add(prayer)
        
    db.commit()
    
    return {"status": "success", "member_id": member.id}
