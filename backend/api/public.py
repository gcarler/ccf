import logging
import secrets
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.core.database import get_db
from backend.services.public_contact_tracking import ContactRecord, tracker

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/register", response_model=schemas.MemberResponse)
def public_register_event(
    payload: schemas.PublicRegistrationCreate, db: Session = Depends(get_db)
) -> Any:
    """
    Registra a una persona desde un QR pblico y vincula su asistencia a un evento.
    Si la persona ya existe (por email o telfono), se usa ese perfil.
    Si no existe, se crea un nuevo Member con spiritual_status = 'Nuevo'.
    """
    event = (
        db.query(models.CrmEvent).filter(models.CrmEvent.id == payload.event_id).first()
    )
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
            church_role="Visitante",
        )
        db.add(member)
        db.commit()
        db.refresh(member)
        logger.info(
            f"Nuevo visitante creado desde QR: {member.first_name} {member.last_name}"
        )

    # 3. Registrar asistencia al evento si no est registrada an
    session_date = (
        event.event_date.date()
        if event.event_date
        else datetime.now(datetime.UTC).date()
    )
    existing_attendance = (
        db.query(models.EventAttendance)
        .filter(
            models.EventAttendance.event_id == event.id,
            models.EventAttendance.session_date == session_date,
            models.EventAttendance.member_id == member.id,
        )
        .first()
    )

    if not existing_attendance:
        attendance = models.EventAttendance(
            event_id=event.id,
            session_date=session_date,
            member_id=member.id,
            attended=True,
        )
        db.add(attendance)
        db.commit()
        logger.info(
            f"Asistencia registrada para {member.first_name} al evento {event.name} (ID {event.id})"
        )

    # podramos aadirlo a una pipeline de Consolidacin. Por ahora, el hecho
    # de tener el email/telfono y estar en la BD lo hace accesible al CRM.

    return member


@router.get("/courses", response_model=list[schemas.Course])
def public_list_courses(db: Session = Depends(get_db)):
    """
    Retorna la lista de cursos públicos disponibles.
    """
    courses = db.query(models.Course).filter(models.Course.is_published == True).all()
    # Mocking lesson count dynamically if needed
    for c in courses:
        c.lesson_count = (
            db.query(models.Lesson).filter(models.Lesson.course_id == c.id).count()
        )
    return courses


@router.get("/courses/{course_id}", response_model=schemas.Course)
def public_get_course(course_id: int, db: Session = Depends(get_db)):
    """
    Retorna los detalles de un curso específico.
    """
    course = (
        db.query(models.Course)
        .filter(models.Course.id == course_id, models.Course.is_published == True)
        .first()
    )
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    course.lesson_count = (
        db.query(models.Lesson).filter(models.Lesson.course_id == course.id).count()
    )
    return course


@router.post("/newsletter/subscribe", response_model=schemas.NewsletterSubscriptionRead)
def public_newsletter_subscribe(
    payload: schemas.NewsletterSubscriptionCreate, db: Session = Depends(get_db)
):
    """
    Registra un correo en el boletín (Newsletter).
    Además crea un Member y ConsolidationCase para que el equipo CRM pueda dar seguimiento.
    """
    email = payload.email.strip().lower()
    existing_sub = (
        db.query(models.NewsletterSubscription)
        .filter(models.NewsletterSubscription.email == email)
        .first()
    )

    if existing_sub:
        return existing_sub

    subscription = models.NewsletterSubscription(email=email)
    db.add(subscription)

    # Use unified contact tracker
    result = tracker.record_contact(db, ContactRecord(
        email=email,
        phone=payload.phone,
        first_name=payload.first_name,
        last_name=payload.last_name,
        source=payload.source or "newsletter-web",
        landing_page=payload.landing_page,
        campaign=payload.campaign,
    ))

    db.commit()
    db.refresh(subscription)
    return subscription


class PublicEnrollCreate(BaseModel):
    """Datos para inscripción pública a un curso."""
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    landing_page: Optional[str] = None
    campaign: Optional[str] = None


@router.post("/courses/{course_id}/enroll", response_model=dict)
def public_course_enroll(
    course_id: int,
    payload: PublicEnrollCreate,
    db: Session = Depends(get_db),
):
    """
    Inscripción pública a un curso.
    Crea User + Member + Enrollment + ConsolidationCase para visibilidad en CRM.
    """
    course = (
        db.query(models.Course)
        .filter(models.Course.id == course_id, models.Course.is_published == True)
        .first()
    )
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    email = (payload.email or "").strip().lower()
    phone = (payload.phone or "").strip()

    # Buscar User existente
    user = None
    if email:
        user = db.query(models.User).filter(models.User.email == email).first()

    if not user:
        # Crear User para el curso
        username = email.split("@")[0] if email else f"web_{secrets.token_hex(6)}"
        # Check username uniqueness
        existing = db.query(models.User).filter(models.User.username == username).first()
        if existing:
            username = f"{username}_{secrets.token_hex(4)}"

        user = models.User(
            username=username,
            email=email or f"{secrets.token_hex(8)}@temp.faro",
            password_hash=secrets.token_hex(32),  # Will set later on real registration
            role="estudiante",
            is_active=True,
            is_email_verified=False,
        )
        db.add(user)
        db.flush()

    # Check if already enrolled
    existing_enroll = (
        db.query(models.Enrollment)
        .filter(
            models.Enrollment.user_id == user.id,
            models.Enrollment.course_id == course_id,
        )
        .first()
    )
    if existing_enroll:
        return {
            "status": "already_enrolled",
            "user_id": user.id,
            "course_id": course_id,
            "enrollment_id": existing_enroll.id,
        }

    # Buscar Member existente
    member = None
    if phone:
        member = (
            db.query(models.Member)
            .filter(models.Member.phone == phone)
            .first()
        )
    if not member and email:
        member = (
            db.query(models.Member)
            .filter(models.Member.email == email)
            .first()
        )

    if not member and (payload.full_name or email):
        parts = (payload.full_name or "").strip().split(" ", 1)
        member = models.Member(
            first_name=parts[0] if parts else "Visitante",
            last_name=parts[1] if len(parts) > 1 else "",
            email=email,
            phone=phone,
            spiritual_status="Nuevo",
            church_role="Visitante",
        )
        db.add(member)
        db.flush()

    # Crear Enrollment
    enrollment = models.Enrollment(
        user_id=user.id,
        course_id=course_id,
        status="active",
    )
    db.add(enrollment)

    # Crear ConsolidationCase para CRM
    notes_parts = [f"Curso: {course.title}"]
    if payload.landing_page:
        notes_parts.append(f"Landing: {payload.landing_page}")
    if payload.campaign:
        notes_parts.append(f"Campaign: {payload.campaign}")

    case = models.ConsolidationCase(
        member_id=member.id if member else 0,
        stage="new",
        status="active",
        source="academy-enrollment",
        notes="\n".join(notes_parts),
    )
    db.add(case)
    db.flush()

    # Task 3.4: Auto-create follow-up task for CRM team
    if member:
        followup_task = models.ConsolidationFollowUpTask(
            case_id=case.id,
            title=f"Seguimiento: nuevo estudiante en {course.title}",
            description=f"Contactar a {member.first_name} {member.last_name} para dar la bienvenida al curso '{course.title}' y ofrecer apoyo pastoral.",
            due_date=datetime.utcnow() + timedelta(days=3),
            status="pending",
        )
        db.add(followup_task)

        # Log in CommunicationLog
        comm_log = models.CommunicationLog(
            member_id=member.id,
            channel="system",
            content=f"Auto follow-up task created: student enrolled in '{course.title}'",
            outcome="task_created",
            campaign_name="academy-auto-followup",
        )
        db.add(comm_log)

    db.commit()
    db.refresh(enrollment)

    return {
        "status": "enrolled",
        "user_id": user.id,
        "course_id": course_id,
        "enrollment_id": enrollment.id,
        "member_id": member.id if member else None,
        "course_title": course.title,
    }


class PublicContactCreate(BaseModel):
    full_name: str
    phone: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = "prospect"
    source: Optional[str] = "conocer-a-jesus"


@router.post("/contact", response_model=dict)
def public_contact(payload: PublicContactCreate, db: Session = Depends(get_db)):
    """
    Recibe un contacto desde un formulario pblico (ej. Conocer a Jesus).
    Crea el miembro si no existe y lo añade a un caso de consolidación.
    """
    parts = payload.full_name.strip().split(" ", 1)
    first_name = parts[0] if parts else "Anónimo"
    last_name = parts[1] if len(parts) > 1 else ""

    member = None
    if payload.phone:
        member = (
            db.query(models.Member).filter(models.Member.phone == payload.phone).first()
        )

    if not member:
        member = models.Member(
            first_name=first_name,
            last_name=last_name,
            phone=payload.phone,
            spiritual_status="Nuevo",
            church_role="Visitante",
        )
        db.add(member)
        db.commit()
        db.refresh(member)

    case = models.ConsolidationCase(
        member_id=member.id,
        stage="Nuevo",
        status="active",
        source=payload.source or "website",
        notes=payload.notes,
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


class WishlistCreate(BaseModel):
    """Interés en un libro/recurso de la librería."""
    title: str
    email: Optional[str] = None
    phone: Optional[str] = None
    full_name: Optional[str] = None
    landing_page: Optional[str] = None


@router.post("/wishlist", response_model=dict)
def public_wishlist(payload: WishlistCreate, db: Session = Depends(get_db)):
    """
    Cuando un visitante muestra interés en un libro de la librería FARO.
    Crea ConsolidationCase con source="books-web" para que el equipo CRM contacte.
    """
    email = (payload.email or "").strip().lower()
    phone = (payload.phone or "").strip()

    result = tracker.record_contact(db, ContactRecord(
        email=email or None,
        phone=phone or None,
        first_name=payload.full_name,
        source="books-web",
        landing_page=payload.landing_page,
        extra_notes=[f"Libro: {payload.title}"],
    ))

    db.commit()

    return {
        "status": "success",
        "title": payload.title,
        "member_id": result.member.id if result.member else None,
    }
