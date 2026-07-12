import logging
import os
import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.core.config import get_settings
from backend.core.database import get_db
from backend.models_academy_core import Course, Lesson
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


class PublicCursoResponse(BaseModel):
    """Respuesta pública de curso — campos alineados con el frontend CourseItem."""
    id: str          # slug, usado como URL key
    title: str
    desc: Optional[str] = None
    excerpt: Optional[str] = None
    tag: Optional[str] = None
    modality: Optional[str] = None
    cta: Optional[str] = "Inscribirme"
    lessons: Optional[int] = None   # duration_hours interpretado como semanas
    imageUrl: Optional[str] = None
    syllabus: Optional[list] = None
    instructor: Optional[str] = None

    model_config = {"from_attributes": True}


def _curso_to_public(curso: Course, lesson_count: int = 0) -> PublicCursoResponse:
    return PublicCursoResponse(
        id=curso.slug or str(curso.id),
        title=curso.title,
        desc=curso.description,
        excerpt=curso.excerpt,
        tag=curso.tag,
        modality=curso.modality,
        cta=curso.cta_text or "Inscribirme",
        lessons=curso.duration_hours or lesson_count,
        imageUrl=curso.image_url,
        syllabus=curso.syllabus or [],
        instructor=curso.instructor_name,
    )


@router.get("/courses", response_model=list[PublicCursoResponse])
def public_list_courses(db: Session = Depends(get_db)):
    """Lista de cursos publicados para la landing page /cursos."""
    cursos = (
        db.query(Course)
        .filter(Course.is_published.is_(True), Course.deleted_at.is_(None))
        .order_by(Course.id)
        .all()
    )
    result = []
    for c in cursos:
        lecciones = db.query(Lesson).filter(
            Lesson.course_id == c.id, Lesson.deleted_at.is_(None)
        ).count()
        result.append(_curso_to_public(c, lecciones))
    return result


@router.get("/courses/{course_slug}", response_model=PublicCursoResponse)
def public_get_course(course_slug: str, db: Session = Depends(get_db)):
    """Detalle de un curso por slug."""
    curso = (
        db.query(Course)
        .filter(
            Course.slug == course_slug,
            Course.is_published.is_(True),
            Course.deleted_at.is_(None),
        )
        .first()
    )
    if not curso:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    lecciones = db.query(Lesson).filter(
        Lesson.course_id == curso.id, Lesson.deleted_at.is_(None)
    ).count()
    return _curso_to_public(curso, lecciones)


class PublicEnrollCreate(BaseModel):
    """Datos para inscripcion publica a un curso."""
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    landing_page: Optional[str] = None
    campaign: Optional[str] = None


@router.post("/courses/{course_slug}/enroll", response_model=dict)
def public_course_enroll(
    course_slug: str,
    payload: PublicEnrollCreate,
    db: Session = Depends(get_db),
):
    """Inscripcion publica a un curso por slug. Crea Persona en el kernel."""
    curso = (
        db.query(Course)
        .filter(
            Course.slug == course_slug,
            Course.is_published.is_(True),
            Course.deleted_at.is_(None),
        )
        .first()
    )
    if not curso:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    email = (payload.email or "").strip().lower()
    phone = (payload.phone or "").strip()

    result = tracker.record_contact(db, ContactRecord(
        email=email or None,
        phone=phone or None,
        first_name=(payload.full_name or "").strip().split(" ", 1)[0] or "Visitante",
        last_name=(payload.full_name or "").strip().split(" ", 1)[1] if payload.full_name and " " in (payload.full_name or "").strip() else "",
        source="academy-enrollment",
        landing_page=payload.landing_page,
        campaign=payload.campaign,
        spiritual_status="Nuevo",
        church_role="Visitante",
        extra_notes=[f"Interesado en curso: {curso.title}"],
    ))
    persona = result.persona
    db.commit()

    return {
        "status": "enrolled",
        "persona_id": str(persona.id) if persona else None,
        "course_slug": course_slug,
        "course_title": curso.title,
    }


class PublicContactCreate(BaseModel):
    full_name: str
    email: Optional[str] = None
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
            sede_id=result.persona.sede_id,
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
    """Cuando un visitante muestra interes en un libro de la libreria CCF."""
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
