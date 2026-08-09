import logging
import os
import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.core.config import get_settings
from backend.core.database import get_db
from backend.core.rate_limit import rate_limiter
from backend.models_academy_core import Course, Lesson

# plan_followup: identidad por desafío single-use (identify/verify + register
# con verified_identity_token).
from backend.services.event_followup_service import (
    consume_verified_identity_token,
    request_identity_challenge,
    resolve_verified_identity_token,
    verify_identity_challenge,
)
from backend.services.event_registration_service import (
    RegistrationError,
    capacity_remaining,
    find_by_email_or_phone,
    find_by_qr_token,
    is_cancel_token_expired,
    is_event_open_for_registration,
)
from backend.services.event_registration_service import (
    cancel as cancel_registration,
)
from backend.services.event_registration_service import (
    register as register_persona,
)
from backend.services.event_registration_service import (
    verify as verify_registration,
)

# plan_de_form_builder: validación server-side de campos dinámicos
from backend.services.form_validation import (
    ValidationError,
    validate_submission,
    verify_hcaptcha,
)
from backend.services.public_contact_tracking import ContactRecord, tracker

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/register", response_model=schemas.PersonaResponse)
def public_register_event(payload: schemas.PublicRegistrationCreate, db: Session = Depends(get_db)) -> Any:
    """
    Registra a una persona desde un QR publico y vincula su asistencia a un evento.
    Si la persona ya existe (por email o telefono), se usa ese perfil.
    Si no existe, se crea un nuevo Persona con spiritual_status = 'Nuevo'.
    """
    event = db.query(models.CrmEvent).filter(models.CrmEvent.id == payload.event_id).first()
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
        logger.info(f"Nuevo visitante creado desde QR: {persona.first_name} {persona.last_name}")

    # 3. Registrar asistencia al evento si no esta registrada aun
    session_date = event.event_date.date() if event.event_date else datetime.now(datetime.UTC).date()
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
        try:
            db.commit()
            logger.info(f"Asistencia registrada para {persona.first_name} al evento {event.name} (ID {event.id})")
        except IntegrityError:
            # Race condition: concurrent request inserted the same
            # (event_id, session_date, persona_id) first. Rollback and
            # treat as idempotent success (TOCTOU fix).
            db.rollback()

    return persona


class PublicCursoResponse(BaseModel):
    """Respuesta pública de curso — campos alineados con el frontend CourseItem."""

    id: str  # slug, usado como URL key
    title: str
    desc: Optional[str] = None
    excerpt: Optional[str] = None
    tag: Optional[str] = None
    modality: Optional[str] = None
    cta: Optional[str] = "Inscribirme"
    lessons: Optional[int] = None  # duration_hours interpretado como semanas
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
    """Lista de cursos publicados para la landing page /cursos.

    Filtra por ``access_level`` IN ('open', 'persona') — ambos son valores del
    enum canónico ``Literal["open", "persona", "advanced"]`` en
    ``backend/schemas/academy.py`` que representan catálogo de captación
    pública. ``"advanced"`` queda fuera (curso avanzado para personas ya
    inscritas, no captación pública). ``"privado"`` nunca fue legítimo (no
    está en el enum); la migración ``20260803_0005_academy_normalize_privado_to_persona``
    lo normaliza a ``"persona"`` para que los cursos生产 preexistentes vuelvan a ser
    visibles. Sin este ajuste, un curso ``open`` publicado tampoco aparecería
    en la landing (contradictorio — ``open`` es más "público" que ``persona``).
    """
    cursos = (
        db.query(Course)
        .filter(
            Course.is_published.is_(True),
            Course.deleted_at.is_(None),
            Course.access_level.in_(["open", "persona"]),
        )
        .order_by(Course.id)
        .all()
    )
    # Batch: count lessons per course in one query (N+1 fix).
    course_ids = [c.id for c in cursos]
    lesson_counts = {}
    if course_ids:
        rows = (
            db.query(Lesson.course_id, func.count(Lesson.id))
            .filter(
                Lesson.course_id.in_(course_ids),
                Lesson.deleted_at.is_(None),
            )
            .group_by(Lesson.course_id)
            .all()
        )
        lesson_counts = {cid: cnt for cid, cnt in rows}
    result = []
    for c in cursos:
        lecciones = lesson_counts.get(c.id, 0)
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
    lecciones = db.query(Lesson).filter(Lesson.course_id == curso.id, Lesson.deleted_at.is_(None)).count()
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

    result = tracker.record_contact(
        db,
        ContactRecord(
            email=email or None,
            phone=phone or None,
            first_name=(payload.full_name or "").strip().split(" ", 1)[0] or "Visitante",
            last_name=(payload.full_name or "").strip().split(" ", 1)[1]
            if payload.full_name and " " in (payload.full_name or "").strip()
            else "",
            source="academy-enrollment",
            landing_page=payload.landing_page,
            campaign=payload.campaign,
            spiritual_status="Nuevo",
            church_role="Visitante",
            extra_notes=[f"Interesado en curso: {curso.title}"],
        ),
    )
    persona = result.persona
    db.commit()

    return {
        "status": "enrolled",
        "persona_id": str(persona.id) if persona else None,
        "course_slug": course_slug,
        "course_title": curso.title,
    }


class PublicContactCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=160)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=40)
    notes: Optional[str] = Field(default=None, max_length=5000)
    status: Optional[str] = Field(default="prospect", max_length=40)
    source: Optional[str] = Field(default="conocer-a-jesus", max_length=120)


@router.post(
    "/contact",
    response_model=dict,
    dependencies=[Depends(rate_limiter(limit=10, window_seconds=60))],
)
def public_contact(payload: PublicContactCreate, db: Session = Depends(get_db)):
    """Recibe un contacto desde un formulario publico."""
    result = tracker.record_contact(
        db,
        ContactRecord(
            first_name=payload.full_name.strip().split(" ", 1)[0] if payload.full_name else "Anonimo",
            last_name=payload.full_name.strip().split(" ", 1)[1]
            if payload.full_name and " " in payload.full_name.strip()
            else "",
            phone=payload.phone,
            source=payload.source or "conocer-a-jesus",
            notes=payload.notes,
            spiritual_status="Nuevo",
            church_role="Visitante",
        ),
    )

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

    result = tracker.record_contact(
        db,
        ContactRecord(
            email=email or None,
            phone=phone or None,
            first_name=payload.full_name,
            source="books-web",
            landing_page=payload.landing_page,
            extra_notes=[f"Libro: {payload.title}"],
        ),
    )

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
    from backend.core.uploads import sanitize_filename

    safe_name = sanitize_filename(file.filename or "")
    ext = os.path.splitext(safe_name)[1].lower()
    if ext not in ALLOWED_DOC_TYPES:
        raise HTTPException(status_code=400, detail=f"Tipo no permitido: {ext}")

    contents = await file.read()
    if len(contents) > MAX_DOC_SIZE:
        raise HTTPException(status_code=400, detail="Archivo muy grande (max 20MB)")

    settings = get_settings()
    uploads_dir = settings.uploads_dir
    os.makedirs(uploads_dir, exist_ok=True)

    unique_name = f"doc_{uuid.uuid4().hex[:8]}_{safe_name}"
    file_path = os.path.join(uploads_dir, unique_name)

    # Path traversal guard — ensure resolved path stays inside uploads_dir
    if not os.path.abspath(file_path).startswith(os.path.abspath(uploads_dir) + os.sep):
        raise HTTPException(status_code=400, detail="Nombre de archivo inválido")

    with open(file_path, "wb") as f:
        f.write(contents)

    file_size = len(contents)
    mime_type = ALLOWED_DOC_TYPES.get(ext, file.content_type or "application/octet-stream")

    sede = db.query(models.Sede).filter(models.Sede.es_activa.is_(True)).first()
    if not sede:
        sede = db.query(models.Sede).first()

    persona = db.query(models.Persona).first()
    if not persona:
        persona = models.Persona(first_name="Sistema", last_name="Público", sede_id=sede.id if sede else None)
        db.add(persona)
        db.flush()

    media = models.CmsMediaItem(
        url=f"/uploads/{unique_name}",
        filename=unique_name,
        mime_type=mime_type,
        file_size=file_size,
        alt_text=file.filename,
        section="public_documents",
        created_by_persona_id=persona.id,
        sede_id=sede.id if sede else persona.sede_id,
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


# =============================================================================
# PRE-REGISTRO PÚBLICO A EVENTOS MASIVOS (plan_de_preregistro, Fase 2)
# =============================================================================

PUBLIC_EVENT_RATE_LIMIT = 120  # por minuto, por IP
PUBLIC_STATUS_RATE_LIMIT = 10  # por minuto, por IP — más estricto para /status (PII risk)


def _public_event_or_404(db: Session, event_id):
    event = db.query(models.CrmEvent).filter(models.CrmEvent.id == event_id).first()
    if not event or event.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    return event


def _settings_public_base_url() -> str:
    """Resuelve la URL pública base para links de QR/verify (configurable)."""
    try:
        s = get_settings()
        return getattr(s, "public_base_url", None) or "https://ccf.co"
    except Exception:
        return "https://ccf.co"


def _reg_error_to_http(exc: RegistrationError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail={"code": exc.code, "detail": exc.detail})


@router.get("/events/{event_id}", response_model=schemas.PublicEventRead)
def public_get_event(event_id: uuid.UUID, db: Session = Depends(get_db)):
    """Metadata pública del evento para la landing de pre-registro."""
    event = _public_event_or_404(db, event_id)
    remaining = capacity_remaining(db, event)
    return schemas.PublicEventRead(
        id=event.id,
        name=event.name,
        description=event.description,
        event_date=event.event_date,
        start_time=event.start_time,
        end_time=event.end_time,
        location=event.location,
        event_type=event.event_type,
        requires_registration=event.requires_registration,
        requires_email_verification=event.requires_email_verification,
        capacity_max=event.capacity_max,
        waiting_list_enabled=event.waiting_list_enabled,
        registration_opens_at=event.registration_opens_at,
        registration_closes_at=event.registration_closes_at,
        contact_person=event.contact_person,
        is_open=is_event_open_for_registration(event),
        capacity_remaining=remaining,
        form_id=event.form_id,
        # plan_clasificador_contextual: rol contextual visible en la landing.
        participant_role_code=event.participant_role_code,
    )


@router.post(
    "/events/{event_id}/identify",
    response_model=dict,
    dependencies=[Depends(rate_limiter(limit=PUBLIC_EVENT_RATE_LIMIT, window_seconds=60))],
)
def public_event_identify(
    event_id: uuid.UUID,
    payload: schemas.PublicEventIdentify,
    db: Session = Depends(get_db),
):
    """Solicita un desafío de identidad (código de 6 dígitos por email).

    plan_followup: el público envía SOLO su email; el backend crea un
    ``EventIdentityChallenge`` con hashes (nunca el valor ni el código en
    claro) y entrega el código por el canal verificado de la persona. La
    respuesta es indistinguible exista o no coincidencia (no revela PII).
    El ``challenge_id`` devuelto correlaciona la verificación posterior.
    """
    event = _public_event_or_404(db, event_id)
    try:
        result = request_identity_challenge(
            db,
            event,
            identifier_type="email",
            identifier_value=payload.email,
        )
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from None
    db.commit()
    return result


@router.post(
    "/events/{event_id}/identify/verify",
    response_model=dict,
    dependencies=[Depends(rate_limiter(limit=PUBLIC_EVENT_RATE_LIMIT, window_seconds=60))],
)
def public_event_identity_verify(
    event_id: uuid.UUID,
    payload: schemas.PublicEventIdentityVerify,
    db: Session = Depends(get_db),
):
    """Verifica el código del desafío y emite un token de identidad single-use.

    plan_followup: valida que el challenge pertenezca a este evento y a este
    identificador (rechaza challenges cross-evento con 403), compara el código
    con ``secrets.compare_digest`` contra el hash, y emite
    ``verified_identity_token`` (single-use) que ``/register`` consume.
    """
    event = _public_event_or_404(db, event_id)
    identifier_type = next(iter(payload.identifier))
    identifier_value = payload.identifier[identifier_type]
    try:
        result = verify_identity_challenge(
            db,
            event,
            identifier_type=identifier_type,
            identifier_value=identifier_value,
            code=payload.code,
            challenge_id=payload.challenge_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from None
    db.commit()
    return {
        "verified_identity_token": result["verified_identity_token"],
        "fields": result["fields"],
    }


def _validate_event_form_data(db: Session, event: models.CrmEvent, payload: schemas.PublicEventRegister) -> None:
    """Valida ``payload.form_data`` + ``captcha_token`` contra el ``CmsForm``
    vinculado al evento (``event.form_id``).

    Plan Form Builder Dinámico §5.4: el pre-registro sigue yendo a
    ``/public/events/{event_id}/register`` (para crear ``EventRegistration`` +
    QR) pero el backend valida ``form_data`` contra el ``CmsForm`` y persiste
    los datos limpios en ``payload.extras["_form_data"]`` — así el servicio
    de preinscripción los captura sin tocar código.

    Flujo:
      1. Cargar el ``CmsForm`` (404 si fue eliminado o está inactivo).
      2. hCaptcha si ``form.captcha_enabled`` (raise 400 si falta/falla).
      3. ``validate_submission(form.fields, payload.form_data)`` → 422 si
         algún campo falla (required, tipo, regex, opciones, condicional).
      4. Persistir el dict limpio en ``payload.extras["_form_data"]`` para
         que ``register_persona`` lo capture en ``extras``.

    Lanza ``HTTPException`` en fallos (404 form, 400 captcha, 422 validación).

    Nota: el honeypot NO se aplica a pre-registro de eventos. ``PublicEventRegister``
    no expone un campo trampa ``_hp`` (esencial para formularios genéricos pero
    impropio para preregistro, donde el plan §5.4 solo valida ``form_data``).
    La protección anti-bot del preregistro es captcha + rate-limit por IP.
    """
    form = db.query(models.CmsForm).filter(models.CmsForm.id == event.form_id).first()
    if not form or not form.is_active:
        raise HTTPException(
            status_code=404,
            detail={"code": "FORM_NOT_FOUND", "detail": "El formulario asociado al evento ya no está disponible."},
        )

    # hCaptcha — el token llega en ``payload.captcha_token``. La verificación
    # se corre con remote_ip=None (este helper no recibe ``request``).
    if form.captcha_enabled:
        token = (payload.captcha_token or "").strip()
        if not token:
            raise HTTPException(
                status_code=400,
                detail={"code": "CAPTCHA_REQUIRED", "detail": "Captcha requerido para este formulario."},
            )

        # ``verify_hcaptcha`` es async; este endpoint es síncrono. Reuso el
        # patrón ``_run_hcaptcha_sync`` (thread con event loop propio) que
        # ``cms_v2/forms.py`` ya estableció para endpoints no-async — evita
        # ``asyncio.run`` cuando ya hay un event loop activo (p.ej. tests).
        ok = _run_hcaptcha_sync(token, remote_ip=None)
        if not ok:
            raise HTTPException(
                status_code=400,
                detail={"code": "CAPTCHA_FAILED", "detail": "Captcha inválido."},
            )

    # Validación server-side de campos dinámicos.
    try:
        clean = validate_submission(
            form.fields or [],
            payload.form_data or {},
            honeypot_enabled=False,  # honeypot no aplica en preregistro (ver docstring)
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": exc.code, "detail": exc.detail, "field_id": exc.field_id},
        ) from None

    # Persistir los datos limpios en ``extras._form_data`` — el servicio
    # de preinscripción guarda ``extras`` en ``event_registrations.extras``.
    extras = dict(payload.extras or {})
    extras["_form_data"] = clean
    payload.extras = extras


def _run_hcaptcha_sync(token: str, *, remote_ip: str | None = None) -> bool:
    """Wrapper síncrono sobre ``verify_hcaptcha`` para endpoints no-async.

    Si ya hay un event loop activo (p.ej. dentro de un runner de tests o un
    request async), ejecuta la corrutina en un thread con su propio loop —
    el mismo patrón que ``cms_v2/forms.py:_run_hcaptcha_sync``.
    """
    import asyncio as _asyncio

    try:
        loop = _asyncio.get_event_loop()
        if loop.is_running():
            import threading

            result: list[bool] = []

            def _runner() -> None:
                new_loop = _asyncio.new_event_loop()
                try:
                    result.append(new_loop.run_until_complete(verify_hcaptcha(token, remote_ip=remote_ip)))
                finally:
                    new_loop.close()

            t = threading.Thread(target=_runner, daemon=True)
            t.start()
            t.join(timeout=15)
            return bool(result[0]) if result else False
        return loop.run_until_complete(verify_hcaptcha(token, remote_ip=remote_ip))
    except RuntimeError:
        return _asyncio.run(verify_hcaptcha(token, remote_ip=remote_ip))


@router.post(
    "/events/{event_id}/register",
    response_model=schemas.EventRegistrationRead,
    dependencies=[Depends(rate_limiter(limit=PUBLIC_EVENT_RATE_LIMIT, window_seconds=60))],
)
def public_register_for_event(
    event_id: uuid.UUID,
    payload: schemas.PublicEventRegister,
    db: Session = Depends(get_db),
):
    """Pre-registro público a un evento masivo con QR + (opcional) verify email.

    Rate-limited por IP. Idempotente: si la persona ya está CONFIRMED/WAITLIST,
    retorna la inscripción existente sin crear duplicados.

    plan_followup: si el payload trae ``verified_identity_token`` (emitido por
    ``/identify/verify``), la persona se resuelve desde el token single-use y
    NO se re-colecta PII del formulario. El token se consume al registrar:
    un replay con el mismo token o un uso cross-evento devuelve 403.
    """
    event = _public_event_or_404(db, event_id)

    if payload.verified_identity_token:
        try:
            persona, _challenge = resolve_verified_identity_token(db, event, payload.verified_identity_token)
        except ValueError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from None
        # Payload derivado desde la persona verificada: ``upsert_persona`` la
        # encuentra por email/phone y no crea un duplicado (el test de contrato
        # verifica exactamente 1 Persona con ese email tras registrar).
        derived = schemas.PublicEventRegister(
            first_name=persona.first_name or "",
            last_name=persona.last_name or "",
            email=persona.email,
            phone=persona.phone,
            accept_contact=payload.accept_contact,
            extras=payload.extras or {},
        )
        try:
            reg = register_persona(
                db,
                event,
                derived,
                public_base_url=_settings_public_base_url(),
            )
        except RegistrationError as exc:
            raise _reg_error_to_http(exc) from None
        # El token es de un solo uso: consumirlo tras materializar la
        # inscripción (replay con el mismo token → 403 en resolve).
        # Nota: ``register_persona`` ya hace commit interno; este commit final
        # es el que persiste ``consumed_at`` del challenge — no eliminarlo.
        # Capturar los tokens transientes inmediatamente tras register_persona
        # (que ya hizo commit + refresh internos): el commit extra que persiste
        # ``consumed_at`` del challenge expira ``reg`` (expire_on_commit=True)
        # y descarta los atributos Python no mapeados ``_qr_token_transient`` /
        # ``_cancel_token_transient``, volátiles emitidos una sola vez aquí.
        qr_token_plain = getattr(reg, "_qr_token_transient", None)
        cancel_token_plain = getattr(reg, "_cancel_token_transient", None)
        # El token es de un solo uso: consumirlo tras materializar la
        # inscripción (replay con el mismo token → 403 en resolve).
        # Nota: ``register_persona`` ya hace commit interno; este commit final
        # es el que persiste ``consumed_at`` del challenge — no eliminarlo.
        consume_verified_identity_token(db, event, payload.verified_identity_token)
        db.commit()
        db.refresh(reg)
        return _serialize_registration(
            reg,
            persona,
            qr_token_override=qr_token_plain,
            cancel_token_override=cancel_token_plain,
        )

    # plan_de_form_builder: si el evento tiene un CmsForm vinculado, validar
    # form_data + captcha server-side contra el contrato del formulario.
    if event.form_id:
        _validate_event_form_data(db, event, payload)

    try:
        reg = register_persona(
            db,
            event,
            payload,
            public_base_url=_settings_public_base_url(),
        )
    except RegistrationError as exc:
        raise _reg_error_to_http(exc) from None

    persona = db.query(models.Persona).filter(models.Persona.id == reg.persona_id).first()
    # Tras register/verify, exponer el QR al usuario en la respuesta (runtime)
    # — el token NO está persistido en DB, se emite una sola vez acá y por email.
    qr_token_plain = getattr(reg, "_qr_token_transient", None)
    cancel_token_plain = getattr(reg, "_cancel_token_transient", None)
    return _serialize_registration(
        reg,
        persona,
        qr_token_override=qr_token_plain,
        cancel_token_override=cancel_token_plain,
    )


@router.get("/events/{event_id}/verify", response_model=schemas.EventRegistrationRead)
def public_verify_event(
    event_id: uuid.UUID,
    token: str = Query(..., min_length=10, max_length=200),
    db: Session = Depends(get_db),
):
    """Verifica una inscripción con el token enviado por email."""
    event = _public_event_or_404(db, event_id)
    try:
        reg = verify_registration(db, event, token, public_base_url=_settings_public_base_url())
    except RegistrationError as exc:
        raise _reg_error_to_http(exc) from None

    persona = db.query(models.Persona).filter(models.Persona.id == reg.persona_id).first()
    qr_token_plain = getattr(reg, "_qr_token_transient", None)
    cancel_token_plain = getattr(reg, "_cancel_token_transient", None)
    return _serialize_registration(
        reg,
        persona,
        qr_token_override=qr_token_plain,
        cancel_token_override=cancel_token_plain,
    )


@router.get(
    "/events/{event_id}/ticket",
    response_model=schemas.EventRegistrationRead,
    dependencies=[Depends(rate_limiter(limit=PUBLIC_EVENT_RATE_LIMIT, window_seconds=60))],
)
def public_event_ticket(
    event_id: uuid.UUID,
    token: str = Query(..., min_length=10, max_length=300),
    db: Session = Depends(get_db),
):
    """Ticket público por QR token (hash-bound).

    El QR nunca se busca por el token plano (no se persiste): se deriva el
    sha256 del secret y se busca por ``qr_token_hash`` (plan §4.3). Devuelve
    la inscripción con su rol contextual, sin re-exponer tokens internos.
    """
    event = _public_event_or_404(db, event_id)
    reg = find_by_qr_token(db, token)
    if not reg or reg.event_id != event.id:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    if reg.registration_status not in {"CONFIRMED", "CHECKED_IN"}:
        raise HTTPException(
            status_code=409,
            detail=f"Ticket no activo (estado: {reg.registration_status})",
        )
    persona = db.query(models.Persona).filter(models.Persona.id == reg.persona_id).first()
    return _serialize_registration(reg, persona, include_qr=False)


@router.get(
    "/events/{event_id}/status",
    response_model=schemas.EventRegistrationRead,
    dependencies=[Depends(rate_limiter(limit=PUBLIC_STATUS_RATE_LIMIT, window_seconds=60))],
)
def public_status_event(
    event_id: uuid.UUID,
    email: Optional[str] = Query(None),
    phone: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Consulta el estado de una inscripción por email o phone.

    Por diseño, este endpoint NO devuelve PII (nombre/email/phone) ni
    ``qr_token`` — solo el estado de la inscripción. Es el canal
    público de "¿estoy inscrito?"; el QR se obtiene por el correo de
    confirmación o por el token de verificación (``/verify``).
    """
    event = _public_event_or_404(db, event_id)
    if not email and not phone:
        raise HTTPException(status_code=400, detail="email o phone requerido")
    reg = find_by_email_or_phone(db, event.id, email=email, phone=phone)
    if not reg:
        raise HTTPException(status_code=404, detail="No se encontró inscripción con esos datos")
    persona = db.query(models.Persona).filter(models.Persona.id == reg.persona_id).first()
    return _serialize_registration(reg, persona, include_pii=False, include_qr=False)


@router.post(
    "/events/{event_id}/cancel",
    response_model=schemas.EventRegistrationRead,
    dependencies=[Depends(rate_limiter(limit=PUBLIC_EVENT_RATE_LIMIT, window_seconds=60))],
)
def public_cancel_event(
    event_id: uuid.UUID,
    payload: schemas.PublicEventCancel,
    db: Session = Depends(get_db),
):
    """Auto-cancelación con el token embebido en el QR link."""
    event = _public_event_or_404(db, event_id)
    token = payload.cancel_token
    if not token.startswith("CCF-CXL-"):
        raise HTTPException(status_code=400, detail="Token de cancelación inválido")
    payload_str = token.removeprefix("CCF-CXL-")
    if "-" not in payload_str:
        raise HTTPException(status_code=400, detail="Token malformado")
    try:
        # El secret es el último segmento; el id es todo lo anterior (los
        # UUID contienen guiones, así que split por el primer '-' truncaría).
        reg_id_str, _secret = payload_str.rsplit("-", 1)
        reg_id = uuid.UUID(reg_id_str)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail="Token malformado") from exc

    reg = (
        db.query(models.EventRegistration)
        .filter(
            models.EventRegistration.id == reg_id,
            models.EventRegistration.event_id == event.id,
            models.EventRegistration.deleted_at.is_(None),
        )
        .first()
    )
    if not reg:
        raise HTTPException(status_code=404, detail="Inscripción no encontrada")
    if reg.registration_status == "CANCELLED":
        raise HTTPException(status_code=409, detail="Inscripción ya cancelada")

    import hashlib
    import secrets

    stored_hash = (reg.extras or {}).get("_cancel_token_hash")
    if not stored_hash or not secrets.compare_digest(hashlib.sha256(_secret.encode()).hexdigest(), stored_hash):
        raise HTTPException(status_code=403, detail="Token inválido")

    # plan_clasificador_contextual §4.3: el token de cancelación expira a las 72h.
    if is_cancel_token_expired(reg):
        raise HTTPException(status_code=410, detail="Token de cancelación expirado")

    reg = cancel_registration(db, event, reg)
    persona = db.query(models.Persona).filter(models.Persona.id == reg.persona_id).first()
    return _serialize_registration(reg, persona)


# ── Helper de serialización ─────────────────────────────────────────────────


def _serialize_registration(
    reg: models.EventRegistration,
    persona: Optional[models.Persona],
    *,
    include_pii: bool = True,
    include_qr: bool = True,
    qr_token_override: str | None = None,
    cancel_token_override: str | None = None,
) -> schemas.EventRegistrationRead:
    """Construye el schema de respuesta, ocultando hashes internos.

    Flags de minimización de datos (defensa en profundidad contra IDOR/PII leak):
      - ``include_pii``: si False, omite ``persona_name/email/phone`` (por defecto
        True para admin, False para ``/status`` público).
      - ``include_qr``:  si False, omite ``qr_token`` y ``cancel_token``
        (``/status`` nunca expone el QR — solo el correo de confirmación o
        ``/verify`` lo emiten).
      - ``qr_token_override`` / ``cancel_token_override``: tokens planos
        volatile (en runtime, no persistidos). Se usan tras ``/register`` y
        ``/verify`` para mostrar el QR y el link de auto-cancelación al
        usuario en la respuesta. Si None, no se emiten.

    Las columnas ``qr_token`` y ``_cancel_token`` nunca se persisten en DB.
    """
    extras_clean = {k: v for k, v in (reg.extras or {}).items() if not k.startswith("_")}
    return schemas.EventRegistrationRead(
        id=reg.id,
        event_id=reg.event_id,
        persona_id=reg.persona_id,
        persona_name=(persona.nombre_completo if persona else None) if include_pii else None,
        persona_email=(persona.email if persona else None) if include_pii else None,
        persona_phone=(persona.phone if persona else None) if include_pii else None,
        registration_status=reg.registration_status,
        # QR: si hay override volatile (recién emitido), úsalo; si no, None.
        # El estado debe ser CONFIRMED/CHECKED_IN para exponerlo.
        qr_token=(
            qr_token_override
            if include_qr and qr_token_override and reg.registration_status in {"CONFIRMED", "CHECKED_IN"}
            else None
        ),
        # cancel_token volatile: mismo patrón que qr_token.
        cancel_token=(
            cancel_token_override
            if include_qr and cancel_token_override and reg.registration_status in {"CONFIRMED", "CHECKED_IN"}
            else None
        ),
        qr_generated_at=reg.qr_generated_at,
        registered_at=reg.registered_at,
        confirmed_at=reg.confirmed_at,
        cancelled_at=reg.cancelled_at,
        check_in_at=reg.check_in_at,
        check_out_at=reg.check_out_at,
        checked_in_by=reg.checked_in_by,
        source=reg.source,
        extras=extras_clean,
        # plan_clasificador_contextual: rol efectivo de la inscripción.
        participant_role_code=reg.participant_role_code,
        waiting_list_position=reg.waiting_list_position,
        reminder_sent_count=reg.reminder_sent_count,
        last_reminder_sent_at=reg.last_reminder_sent_at,
    )
