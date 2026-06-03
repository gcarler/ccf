import logging
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.core.config import get_settings
from backend.core.database import get_db
from backend.services.public_contact_tracking import ContactRecord, tracker

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/register", response_model=schemas.PersonaResponse)
def public_register_event(
    payload: schemas.PublicRegistrationCreate, db: Session = Depends(get_db)
) -> Any:
    """
    Registra a una persona desde un QR publico y vincula su asistencia a un evento.
    Si la persona ya existe (por email o telefono), se usa ese perfil.
    Si no existe, se crea un nuevo Persona con spiritual_status = 'Nuevo'.
    """
    event = (
        db.query(models.CrmEvent).filter(models.CrmEvent.id == payload.event_id).first()
    )
    if not event:
        raise HTTPException(status_code=404, detail="Evento no encontrado.")

    # 1. Buscar si ya existe la persona por email o telefono
    persona = None
    if payload.email or payload.phone:
        query = db.query(models.Persona)
        conditions = []
        if payload.email:
            conditions.append(models.Persona.email == payload.email)
        if payload.phone:
            conditions.append(models.Persona.phone == payload.phone)

        persona = query.filter(or_(*conditions)).first()

    # 2. Si no existe, lo creamos
    if not persona:
        persona = models.Persona(
            first_name=payload.first_name,
            last_name=payload.last_name,
            email=payload.email,
            phone=payload.phone,
            spiritual_status="Nuevo",
            church_role="Visitante",
        )
        db.add(persona)
        db.commit()
        db.refresh(persona)
        logger.info(
            f"Nuevo visitante creado desde QR: {persona.first_name} {persona.last_name}"
        )

    # 3. Registrar asistencia al evento si no esta registrada aun
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
            models.EventAttendance.persona_id == persona.id,
        )
        .first()
    )

    if not existing_attendance:
        attendance = models.EventAttendance(
            event_id=event.id,
            session_date=session_date,
            persona_id=persona.id,
            attended=True,
        )
        db.add(attendance)
        db.commit()
        logger.info(
            f"Asistencia registrada para {persona.first_name} al evento {event.name} (ID {event.id})"
        )

    return persona


@router.get("/courses", response_model=list[schemas.Course])
def public_list_courses(db: Session = Depends(get_db)):
    """Retorna la lista de cursos publicos disponibles."""
    courses = db.query(models.Course).filter(models.Course.is_published).all()  # Cursos públicos globales (landing page) — OK sin sede_id
    for c in courses:
        c.lesson_count = (
            db.query(models.Lesson).filter(models.Lesson.course_id == c.id).count()
        )
    return courses


@router.get("/courses/{course_id}", response_model=schemas.Course)
def public_get_course(course_id: int, db: Session = Depends(get_db)):
    """Retorna los detalles de un curso especifico."""
    course = (
        db.query(models.Course)
        .filter(models.Course.id == course_id, models.Course.is_published)
        .first()
    )
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    course.lesson_count = (
        db.query(models.Lesson).filter(models.Lesson.course_id == course.id).count()
    )
    return course



class PublicEnrollCreate(BaseModel):
    """Datos para inscripcion publica a un curso."""
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
    """Inscripcion publica a un curso."""
    course = (
        db.query(models.Course)
        .filter(models.Course.id == course_id, models.Course.is_published)
        .first()
    )
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    email = (payload.email or "").strip().lower()
    phone = (payload.phone or "").strip()

    user = None
    if email:
        user = db.query(models.User).filter(models.User.email == email).first()

    if not user:
        username = email.split("@")[0] if email else f"web_{secrets.token_hex(6)}"
        existing = db.query(models.User).filter(models.User.username == username).first()
        if existing:
            username = f"{username}_{secrets.token_hex(4)}"

        user = models.User(
            username=username,
            email=email or f"{secrets.token_hex(8)}@temp.faro",
            password_hash=secrets.token_hex(32),
            role="estudiante",
            is_active=True,
            is_email_verified=False,
        )
        db.add(user)
        db.flush()

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

    notes_parts = [f"Curso: {course.title}"]

    result = tracker.record_contact(db, ContactRecord(
        email=email or None,
        phone=phone or None,
        first_name=(payload.full_name or "").strip().split(" ", 1)[0] or "Visitante",
        last_name=(payload.full_name or "").strip().split(" ", 1)[1] if payload.full_name and " " in payload.full_name.strip() else "",
        source="academy-enrollment",
        landing_page=payload.landing_page,
        campaign=payload.campaign,
        spiritual_status="Nuevo",
        church_role="Visitante",
        extra_notes=notes_parts,
    ))
    persona = result.persona
    case = result.case

    enrollment = models.Enrollment(
        user_id=user.id,
        course_id=course_id,
        status="active",
    )
    db.add(enrollment)
    db.flush()

    if persona:
        followup_task = models.ConsolidationTask(
            case_id=case.id,
            title=f"Seguimiento: nuevo estudiante en {course.title}",
            description=f"Contactar a {persona.first_name} {persona.last_name} para dar la bienvenida al curso '{course.title}' y ofrecer apoyo pastoral.",
            due_date=datetime.now(timezone.utc) + timedelta(days=3),
            status="pending",
        )
        db.add(followup_task)

        comm_log = models.CommunicationLog(
            persona_id=persona.id,
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
        "persona_id": persona.id if persona else None,
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
    """Recibe un contacto desde un formulario publico."""
    result = tracker.record_contact(db, ContactRecord(
        first_name=payload.full_name.strip().split(" ", 1)[0] if payload.full_name else "Anonimo",
        last_name=payload.full_name.strip().split(" ", 1)[1] if payload.full_name and " " in payload.full_name.strip() else "",
        phone=payload.phone,
        source=payload.source or "conocer-a-jesus",
        notes=payload.notes,
        spiritual_status="Nuevo",
        church_role="Visitante",
    ))

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

    return {
        "status": "success",
        "persona_id": result.persona.id if result.persona else None,
        "case_id": result.case.id if result.case else None,
    }


class WishlistCreate(BaseModel):
    """Interes en un libro/recurso de la libreria."""
    title: str
    email: Optional[str] = None
    phone: Optional[str] = None
    full_name: Optional[str] = None
    landing_page: Optional[str] = None


@router.post("/wishlist", response_model=dict)
def public_wishlist(payload: WishlistCreate, db: Session = Depends(get_db)):
    """Cuando un visitante muestra interes en un libro de la libreria FARO."""
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
        "persona_id": result.persona.id if result.persona else None,
    }


ALLOWED_DOC_TYPES = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".txt": "text/plain",
    ".csv": "text/csv",
}
MAX_DOC_SIZE = 20 * 1024 * 1024  # 20MB


@router.post("/documents", response_model=dict, status_code=201)
async def upload_public_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Sube un documento publico (PDF, imagen, documento)."""
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_DOC_TYPES:
        raise HTTPException(status_code=400, detail=f"Tipo no permitido: {ext}")

    contents = await file.read()
    if len(contents) > MAX_DOC_SIZE:
        raise HTTPException(status_code=400, detail="Archivo muy grande (max 20MB)")

    settings = get_settings()
    uploads_dir = settings.uploads_dir
    os.makedirs(uploads_dir, exist_ok=True)

    unique_name = f"doc_{uuid.uuid4().hex[:8]}_{file.filename}"
    file_path = os.path.join(uploads_dir, unique_name)
    with open(file_path, "wb") as f:
        f.write(contents)

    file_size = len(contents)
    mime_type = ALLOWED_DOC_TYPES.get(ext, file.content_type or "application/octet-stream")

    media = models.CmsMediaItem(
        url=f"/uploads/{unique_name}",
        filename=unique_name,
        mime_type=mime_type,
        file_size=file_size,
        alt_text=file.filename,
        section="public_documents",
    )
    db.add(media)
    db.commit()
    db.refresh(media)

    return {
        "id": media.id,
        "url": media.url,
        "filename": file.filename,
        "size": file_size,
        "mime_type": mime_type,
    }
