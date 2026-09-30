"""API Router para el Módulo de Encuestas Dinámicas (Google Forms Parity).

Cumple estrictamente con los Axiomas y Estándares de Plataforma CCF:
- Axioma 1: Kernel de Personas (persona_id / auth_users)
- Axioma 3: Aislamiento Multi-Tenant (sede_id)
- Fechas en UTC con DateTime(timezone=True) y datetime.now(timezone.utc)
- Soft Deletes (deleted_at, is_active)
- Reversibilidad y trazabilidad forense
"""

from __future__ import annotations

import csv
import hashlib
import io
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from jose import JWTError, jwt
from sqlalchemy import asc, desc, func, or_
from sqlalchemy.orm import Session, joinedload

from backend import models, models_surveys
from backend.core.config import get_settings
from backend.core.database import get_db
from backend.core.permissions import (
    ALGORITHM,
    SECRET_KEY,
    get_current_user,
)
from backend.crud.crm import get_user_sede_id
from backend.schemas import surveys as schemas

router = APIRouter()
public_router = APIRouter()

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB


def _slugify(text: str) -> str:
    """Convierte texto en un slug URL-friendly limpio."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return re.sub(r"^-+|-+$", "", text) or "encuesta"


def _resolve_persona_from_request(request: Request, db: Session) -> tuple[Optional[uuid.UUID], Optional[uuid.UUID]]:
    """Axioma 1: Intenta resolver persona_id y usuario_id del JWT si el usuario está autenticado."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None, None
    token = auth_header.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        subject = payload.get("sub")
        if not subject:
            return None, None
        user_uuid = uuid.UUID(str(subject))
        # Verificar usuario en DB
        user = db.query(models.Usuario).filter(models.Usuario.id == user_uuid).first()
        if not user:
            return None, None
        # Axioma 1: usuario_id comparte UUID con persona_id en el Kernel de Personas
        persona = db.query(models.Persona).filter(models.Persona.id == user_uuid).first()
        persona_id = persona.id if persona else user_uuid
        return persona_id, user_uuid
    except (JWTError, ValueError):
        return None, None


# ── RUTAS PÚBLICAS (RESPUESTAS Y ACCESO AL FORMULARIO) ────────────────────────


@public_router.get(
    "/surveys/{identifier}",
    response_model=schemas.EncuestaFormularioPublicResponse,
    summary="Obtener definición pública de una encuesta por ID o Slug",
)
def get_public_survey(
    identifier: str,
    db: Session = Depends(get_db),
):
    query = (
        db.query(models_surveys.EncuestaFormulario)
        .options(joinedload(models_surveys.EncuestaFormulario.preguntas))
        .filter(models_surveys.EncuestaFormulario.deleted_at.is_(None))
    )

    try:
        as_uuid = uuid.UUID(identifier)
        survey = query.filter(models_surveys.EncuestaFormulario.id == as_uuid).first()
    except ValueError:
        survey = query.filter(models_surveys.EncuestaFormulario.slug == identifier).first()

    if not survey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La encuesta solicitada no existe o no se encuentra disponible.",
        )

    if survey.estado != schemas.EstadoFormulario.PUBLICADO.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Esta encuesta no está disponible actualmente (Estado: {survey.estado}).",
        )

    # Ordenar preguntas por orden ASC
    survey.preguntas.sort(key=lambda p: p.orden)
    return schemas.EncuestaFormularioPublicResponse.model_validate(survey)


@public_router.post(
    "/surveys/{identifier}/submit",
    response_model=schemas.EncuestaSubmitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enviar respuesta a una encuesta pública",
)
async def submit_public_survey_response(
    identifier: str,
    payload: schemas.EncuestaSubmitRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    query = (
        db.query(models_surveys.EncuestaFormulario)
        .options(joinedload(models_surveys.EncuestaFormulario.preguntas))
        .filter(models_surveys.EncuestaFormulario.deleted_at.is_(None))
    )

    try:
        as_uuid = uuid.UUID(identifier)
        survey = query.filter(models_surveys.EncuestaFormulario.id == as_uuid).first()
    except ValueError:
        survey = query.filter(models_surveys.EncuestaFormulario.slug == identifier).first()

    if not survey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La encuesta solicitada no existe.",
        )

    if survey.estado != schemas.EstadoFormulario.PUBLICADO.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta encuesta no se encuentra abierta para recibir respuestas.",
        )

    now = datetime.now(timezone.utc)
    if survey.fecha_apertura and now < survey.fecha_apertura:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esta encuesta aún no ha abierto su periodo de recepción.",
        )
    if survey.fecha_cierre and now > survey.fecha_cierre:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El plazo para responder esta encuesta ha finalizado.",
        )
    if survey.max_respuestas and survey.total_respuestas >= survey.max_respuestas:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esta encuesta ha alcanzado el límite máximo de respuestas permitidas.",
        )

    # Validar preguntas requeridas
    preguntas_map = {p.id: p for p in survey.preguntas}
    respuestas_map = {r.pregunta_id: r for r in payload.respuestas}

    for p in survey.preguntas:
        if p.es_requerida and p.tipo_pregunta != schemas.TipoPregunta.SECCION_SALTO.value:
            resp = respuestas_map.get(p.id)
            if not resp:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"La pregunta obligatoria '{p.titulo}' no ha sido respondida.",
                )
            # Verificar contenido no vacío
            has_content = any([
                resp.valor_texto is not None and str(resp.valor_texto).strip() != "",
                resp.valor_numero is not None,
                resp.valor_fecha is not None,
                resp.valor_hora is not None and str(resp.valor_hora).strip() != "",
                resp.valor_json is not None and resp.valor_json != [] and resp.valor_json != {},
            ])
            if not has_content:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"La pregunta obligatoria '{p.titulo}' requiere una respuesta.",
                )

    # Axioma 1: Kernel de Personas
    persona_id, usuario_id = _resolve_persona_from_request(request, db)

    # Hash IP para privacidad / evitar duplicados sin almacenar IP en plano
    client_ip = request.client.host if request.client else "unknown"
    ip_hash = hashlib.sha256(client_ip.encode("utf-8")).hexdigest()

    user_agent = request.headers.get("user-agent") or ""
    if len(user_agent) > 500:
        user_agent = user_agent[:500]

    # Crear Envío
    envio = models_surveys.EncuestaRespuestaEnvio(
        formulario_id=survey.id,
        persona_id=persona_id,
        usuario_id=usuario_id,
        ip_hash=ip_hash,
        user_agent=user_agent,
        email_respondente=payload.email_respondente,
        nombre_respondente=payload.nombre_respondente,
        metadatos=payload.metadatos,
        created_at=now,
        updated_at=now,
    )
    db.add(envio)
    db.flush()

    # Guardar detalles
    for r in payload.respuestas:
        if r.pregunta_id not in preguntas_map:
            continue  # Ignorar preguntas que no pertenecen a este formulario

        detalle = models_surveys.EncuestaRespuestaDetalle(
            envio_id=envio.id,
            pregunta_id=r.pregunta_id,
            valor_texto=r.valor_texto,
            valor_numero=r.valor_numero,
            valor_fecha=r.valor_fecha,
            valor_hora=r.valor_hora,
            valor_json=r.valor_json,
            created_at=now,
        )
        db.add(detalle)

    # Incrementar contador atómico
    survey.total_respuestas = (survey.total_respuestas or 0) + 1
    survey.updated_at = now
    db.commit()

    return schemas.EncuestaSubmitResponse(
        status="success",
        envio_id=envio.id,
        mensaje_confirmacion=survey.mensaje_confirmacion or "¡Tu respuesta ha sido registrada exitosamente!",
        redirigir_url=survey.redirigir_url,
    )


@public_router.post(
    "/surveys/{identifier}/upload-file",
    summary="Subir archivo para una pregunta tipo SUBIR_ARCHIVO",
)
async def upload_survey_file(
    identifier: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    query = db.query(models_surveys.EncuestaFormulario).filter(models_surveys.EncuestaFormulario.deleted_at.is_(None))
    try:
        as_uuid = uuid.UUID(identifier)
        survey = query.filter(models_surveys.EncuestaFormulario.id == as_uuid).first()
    except ValueError:
        survey = query.filter(models_surveys.EncuestaFormulario.slug == identifier).first()

    if not survey or survey.estado != schemas.EstadoFormulario.PUBLICADO.value:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Encuesta no disponible para subida de archivos.",
        )

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo excede el tamaño máximo permitido de 20MB.",
        )

    settings = get_settings()
    surveys_upload_dir = os.path.join(settings.uploads_dir, "surveys")
    os.makedirs(surveys_upload_dir, exist_ok=True)

    original_filename = file.filename or "archivo"
    safe_name = re.sub(r"[^\w\.-]", "_", original_filename)
    unique_name = f"survey_{uuid.uuid4().hex[:8]}_{safe_name}"
    file_path = os.path.join(surveys_upload_dir, unique_name)

    # Path traversal guard
    if not os.path.abspath(file_path).startswith(os.path.abspath(surveys_upload_dir) + os.sep):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nombre de archivo inválido.")

    with open(file_path, "wb") as f:
        f.write(contents)

    file_url = f"/uploads/surveys/{unique_name}"
    return {
        "url": file_url,
        "filename": original_filename,
        "size": len(contents),
        "mime_type": file.content_type or "application/octet-stream",
    }


# ── RUTAS DE GESTIÓN Y ANALÍTICA (ADMIN / PASTORES / TENANT) ─────────────────


@router.get(
    "/surveys",
    response_model=List[schemas.EncuestaFormularioResponse],
    summary="Listar formularios accesibles para la sede del usuario",
)
def list_surveys(
    estado: Optional[schemas.EstadoFormulario] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user),
):
    # Axioma 3: Aislamiento Multi-Tenant
    user_sede_id = get_user_sede_id(db, current_user.id)

    query = (
        db.query(models_surveys.EncuestaFormulario)
        .options(joinedload(models_surveys.EncuestaFormulario.preguntas))
        .filter(models_surveys.EncuestaFormulario.deleted_at.is_(None))
    )

    if user_sede_id is not None:
        query = query.filter(
            or_(
                models_surveys.EncuestaFormulario.sede_id.is_(None),
                models_surveys.EncuestaFormulario.sede_id == user_sede_id,
            )
        )

    if estado:
        query = query.filter(models_surveys.EncuestaFormulario.estado == estado.value)

    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                models_surveys.EncuestaFormulario.titulo.ilike(term),
                models_surveys.EncuestaFormulario.descripcion.ilike(term),
            )
        )

    query = query.order_by(desc(models_surveys.EncuestaFormulario.updated_at))
    formularios = query.offset(skip).limit(limit).all()

    for f in formularios:
        f.preguntas.sort(key=lambda p: p.orden)

    return [schemas.EncuestaFormularioResponse.model_validate(f) for f in formularios]


@router.post(
    "/surveys",
    response_model=schemas.EncuestaFormularioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un nuevo formulario de encuesta",
)
def create_survey(
    payload: schemas.EncuestaFormularioCreate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user),
):
    # Axioma 3: Sede resuelta desde el actor autenticado
    user_sede_id = get_user_sede_id(db, current_user.id)

    # Validar o generar slug único
    slug = _slugify(payload.slug or payload.titulo)
    existing_slug = (
        db.query(models_surveys.EncuestaFormulario)
        .filter(
            models_surveys.EncuestaFormulario.slug == slug,
            models_surveys.EncuestaFormulario.deleted_at.is_(None),
        )
        .first()
    )
    if existing_slug:
        slug = f"{slug}-{uuid.uuid4().hex[:6]}"

    now = datetime.now(timezone.utc)
    formulario = models_surveys.EncuestaFormulario(
        sede_id=user_sede_id,
        titulo=payload.titulo,
        descripcion=payload.descripcion,
        slug=slug,
        es_publico=payload.es_publico,
        requiere_autenticacion=payload.requiere_autenticacion,
        limitar_una_respuesta=payload.limitar_una_respuesta,
        permitir_editar_respuesta=payload.permitir_editar_respuesta,
        mostrar_barra_progreso=payload.mostrar_barra_progreso,
        mensaje_confirmacion=payload.mensaje_confirmacion,
        redirigir_url=payload.redirigir_url,
        fecha_apertura=payload.fecha_apertura,
        fecha_cierre=payload.fecha_cierre,
        max_respuestas=payload.max_respuestas,
        total_respuestas=0,
        estado=payload.estado.value,
        config_visual=payload.config_visual,
        ajustes=payload.ajustes,
        creado_por_id=current_user.id,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db.add(formulario)
    db.flush()

    if payload.preguntas:
        for idx, p_in in enumerate(payload.preguntas):
            pregunta = models_surveys.EncuestaPregunta(
                formulario_id=formulario.id,
                titulo=p_in.titulo,
                descripcion=p_in.descripcion,
                tipo_pregunta=p_in.tipo_pregunta.value,
                orden=idx,
                es_requerida=p_in.es_requerida,
                opciones=p_in.opciones,
                filas=p_in.filas,
                columnas=p_in.columnas,
                escala_min=p_in.escala_min,
                escala_max=p_in.escala_max,
                escala_min_etiqueta=p_in.escala_min_etiqueta,
                escala_max_etiqueta=p_in.escala_max_etiqueta,
                archivo_tipos_permitidos=p_in.archivo_tipos_permitidos,
                archivo_max_mb=p_in.archivo_max_mb,
                archivo_max_archivos=p_in.archivo_max_archivos,
                configuracion=p_in.configuracion,
                created_at=now,
                updated_at=now,
            )
            db.add(pregunta)

    db.commit()
    db.refresh(formulario)
    formulario.preguntas.sort(key=lambda p: p.orden)
    return schemas.EncuestaFormularioResponse.model_validate(formulario)


@router.get(
    "/surveys/{survey_id}",
    response_model=schemas.EncuestaFormularioResponse,
    summary="Obtener detalle completo de un formulario con sus preguntas",
)
def get_survey_detail(
    survey_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user),
):
    survey = (
        db.query(models_surveys.EncuestaFormulario)
        .options(joinedload(models_surveys.EncuestaFormulario.preguntas))
        .filter(
            models_surveys.EncuestaFormulario.id == survey_id,
            models_surveys.EncuestaFormulario.deleted_at.is_(None),
        )
        .first()
    )
    if not survey:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Formulario no encontrado.")

    # Axioma 3: Aislamiento Tenant
    user_sede_id = get_user_sede_id(db, current_user.id)
    if user_sede_id is not None and survey.sede_id is not None and survey.sede_id != user_sede_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a los recursos de otra sede.",
        )

    survey.preguntas.sort(key=lambda p: p.orden)
    return schemas.EncuestaFormularioResponse.model_validate(survey)


@router.patch(
    "/surveys/{survey_id}",
    response_model=schemas.EncuestaFormularioResponse,
    summary="Actualizar propiedades y ajustes de un formulario",
)
def update_survey(
    survey_id: uuid.UUID,
    payload: schemas.EncuestaFormularioUpdate,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user),
):
    survey = (
        db.query(models_surveys.EncuestaFormulario)
        .options(joinedload(models_surveys.EncuestaFormulario.preguntas))
        .filter(
            models_surveys.EncuestaFormulario.id == survey_id,
            models_surveys.EncuestaFormulario.deleted_at.is_(None),
        )
        .first()
    )
    if not survey:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Formulario no encontrado.")

    user_sede_id = get_user_sede_id(db, current_user.id)
    if user_sede_id is not None and survey.sede_id is not None and survey.sede_id != user_sede_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado para modificar esta encuesta.")

    update_data = payload.model_dump(exclude_unset=True)
    if "slug" in update_data and update_data["slug"]:
        slug = _slugify(update_data["slug"])
        existing = (
            db.query(models_surveys.EncuestaFormulario)
            .filter(
                models_surveys.EncuestaFormulario.slug == slug,
                models_surveys.EncuestaFormulario.id != survey.id,
                models_surveys.EncuestaFormulario.deleted_at.is_(None),
            )
            .first()
        )
        if existing:
            slug = f"{slug}-{uuid.uuid4().hex[:6]}"
        update_data["slug"] = slug

    if "estado" in update_data and update_data["estado"] is not None:
        update_data["estado"] = update_data["estado"].value

    for k, v in update_data.items():
        setattr(survey, k, v)

    survey.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(survey)
    survey.preguntas.sort(key=lambda p: p.orden)
    return schemas.EncuestaFormularioResponse.model_validate(survey)


@router.delete(
    "/surveys/{survey_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete de un formulario",
)
def delete_survey(
    survey_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user),
):
    survey = (
        db.query(models_surveys.EncuestaFormulario)
        .filter(
            models_surveys.EncuestaFormulario.id == survey_id,
            models_surveys.EncuestaFormulario.deleted_at.is_(None),
        )
        .first()
    )
    if not survey:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Formulario no encontrado.")

    user_sede_id = get_user_sede_id(db, current_user.id)
    if user_sede_id is not None and survey.sede_id is not None and survey.sede_id != user_sede_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado.")

    now = datetime.now(timezone.utc)
    survey.deleted_at = now
    survey.is_active = False
    survey.updated_at = now
    db.commit()
    return None


@router.put(
    "/surveys/{survey_id}/questions",
    response_model=List[schemas.EncuestaPreguntaResponse],
    summary="Sincronización en batch del set de preguntas del formulario",
)
def sync_survey_questions(
    survey_id: uuid.UUID,
    payload: schemas.EncuestaPreguntasBatchRequest,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user),
):
    survey = (
        db.query(models_surveys.EncuestaFormulario)
        .filter(
            models_surveys.EncuestaFormulario.id == survey_id,
            models_surveys.EncuestaFormulario.deleted_at.is_(None),
        )
        .first()
    )
    if not survey:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Formulario no encontrado.")

    user_sede_id = get_user_sede_id(db, current_user.id)
    if user_sede_id is not None and survey.sede_id is not None and survey.sede_id != user_sede_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado.")

    # Reemplazo limpio y sincronizado de preguntas del formulario
    db.query(models_surveys.EncuestaPregunta).filter(
        models_surveys.EncuestaPregunta.formulario_id == survey_id
    ).delete(synchronize_session="fetch")

    now = datetime.now(timezone.utc)
    created_questions = []
    for idx, p_in in enumerate(payload.preguntas):
        p = models_surveys.EncuestaPregunta(
            formulario_id=survey_id,
            titulo=p_in.titulo,
            descripcion=p_in.descripcion,
            tipo_pregunta=p_in.tipo_pregunta.value,
            orden=idx,
            es_requerida=p_in.es_requerida,
            opciones=p_in.opciones,
            filas=p_in.filas,
            columnas=p_in.columnas,
            escala_min=p_in.escala_min,
            escala_max=p_in.escala_max,
            escala_min_etiqueta=p_in.escala_min_etiqueta,
            escala_max_etiqueta=p_in.escala_max_etiqueta,
            archivo_tipos_permitidos=p_in.archivo_tipos_permitidos,
            archivo_max_mb=p_in.archivo_max_mb,
            archivo_max_archivos=p_in.archivo_max_archivos,
            configuracion=p_in.configuracion,
            created_at=now,
            updated_at=now,
        )
        db.add(p)
        created_questions.append(p)

    survey.updated_at = now
    db.commit()

    for p in created_questions:
        db.refresh(p)
    return [schemas.EncuestaPreguntaResponse.model_validate(p) for p in created_questions]


@router.get(
    "/surveys/{survey_id}/analytics/summary",
    response_model=schemas.EncuestaAnalyticsSummary,
    summary="Resumen estadístico y analítica de respuestas",
)
def get_survey_analytics(
    survey_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user),
):
    survey = (
        db.query(models_surveys.EncuestaFormulario)
        .options(joinedload(models_surveys.EncuestaFormulario.preguntas))
        .filter(
            models_surveys.EncuestaFormulario.id == survey_id,
            models_surveys.EncuestaFormulario.deleted_at.is_(None),
        )
        .first()
    )
    if not survey:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Formulario no encontrado.")

    user_sede_id = get_user_sede_id(db, current_user.id)
    if user_sede_id is not None and survey.sede_id is not None and survey.sede_id != user_sede_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado.")

    # Fechas límite de respuestas
    bounds = (
        db.query(
            func.min(models_surveys.EncuestaRespuestaEnvio.created_at).label("primera"),
            func.max(models_surveys.EncuestaRespuestaEnvio.created_at).label("ultima"),
        )
        .filter(models_surveys.EncuestaRespuestaEnvio.formulario_id == survey_id)
        .first()
    )

    primera_resp = bounds.primera if bounds else None
    ultima_resp = bounds.ultima if bounds else None

    # Procesar analítica de cada pregunta
    survey.preguntas.sort(key=lambda p: p.orden)
    preguntas_stats = []

    for p in survey.preguntas:
        if p.tipo_pregunta == schemas.TipoPregunta.SECCION_SALTO.value:
            continue

        detalles = (
            db.query(models_surveys.EncuestaRespuestaDetalle)
            .filter(models_surveys.EncuestaRespuestaDetalle.pregunta_id == p.id)
            .all()
        )

        total_p_respuestas = len(detalles)
        distribucion: Dict[str, int] = {}
        promedio: Optional[float] = None
        minimo: Optional[float] = None
        maximo: Optional[float] = None
        recientes: List[str] = []

        if p.tipo_pregunta in (
            schemas.TipoPregunta.OPCION_MULTIPLE.value,
            schemas.TipoPregunta.DESPLEGABLE.value,
        ):
            for d in detalles:
                val = d.valor_texto
                if val:
                    distribucion[val] = distribucion.get(val, 0) + 1

        elif p.tipo_pregunta == schemas.TipoPregunta.CASILLAS.value:
            for d in detalles:
                if isinstance(d.valor_json, list):
                    for item in d.valor_json:
                        if item:
                            distribucion[str(item)] = distribucion.get(str(item), 0) + 1
                elif d.valor_texto:
                    distribucion[d.valor_texto] = distribucion.get(d.valor_texto, 0) + 1

        elif p.tipo_pregunta in (schemas.TipoPregunta.ESCALA_LINEAL.value,):
            nums = [d.valor_numero for d in detalles if d.valor_numero is not None]
            if nums:
                promedio = round(float(sum(nums) / len(nums)), 2)
                minimo = float(min(nums))
                maximo = float(max(nums))
                for n in nums:
                    key = str(int(n) if n.is_integer() else n)
                    distribucion[key] = distribucion.get(key, 0) + 1

        elif p.tipo_pregunta in (
            schemas.TipoPregunta.TEXTO_CORTO.value,
            schemas.TipoPregunta.PARRAFO.value,
        ):
            recientes = [
                d.valor_texto
                for d in detalles
                if d.valor_texto and d.valor_texto.strip()
            ][:10]

        elif p.tipo_pregunta in (schemas.TipoPregunta.FECHA.value, schemas.TipoPregunta.HORA.value):
            recientes = [
                str(d.valor_fecha if d.valor_fecha else d.valor_hora or "")
                for d in detalles
                if d.valor_fecha or d.valor_hora
            ][:10]

        elif p.tipo_pregunta == schemas.TipoPregunta.SUBIR_ARCHIVO.value:
            recientes = [
                d.valor_texto
                for d in detalles
                if d.valor_texto
            ][:10]

        preguntas_stats.append(
            schemas.PreguntaAnalyticsSummary(
                pregunta_id=p.id,
                titulo=p.titulo,
                tipo_pregunta=p.tipo_pregunta,
                total_respuestas=total_p_respuestas,
                distribucion_opciones=distribucion,
                promedio=promedio,
                minimo=minimo,
                maximo=maximo,
                respuestas_recientes=recientes,
            )
        )

    return schemas.EncuestaAnalyticsSummary(
        formulario_id=survey.id,
        titulo=survey.titulo,
        total_respuestas=survey.total_respuestas or 0,
        primera_respuesta=primera_resp,
        ultima_respuesta=ultima_resp,
        preguntas=preguntas_stats,
    )


@router.get(
    "/surveys/{survey_id}/responses/table",
    response_model=schemas.EncuestaRespuestasTableResponse,
    summary="Tabla estructurada de respuestas para visualización tipo hoja de cálculo",
)
def get_survey_responses_table(
    survey_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user),
):
    survey = (
        db.query(models_surveys.EncuestaFormulario)
        .options(joinedload(models_surveys.EncuestaFormulario.preguntas))
        .filter(
            models_surveys.EncuestaFormulario.id == survey_id,
            models_surveys.EncuestaFormulario.deleted_at.is_(None),
        )
        .first()
    )
    if not survey:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Formulario no encontrado.")

    user_sede_id = get_user_sede_id(db, current_user.id)
    if user_sede_id is not None and survey.sede_id is not None and survey.sede_id != user_sede_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado.")

    survey.preguntas.sort(key=lambda p: p.orden)
    valid_preguntas = [p for p in survey.preguntas if p.tipo_pregunta != schemas.TipoPregunta.SECCION_SALTO.value]

    columnas = [
        {"key": "envio_id", "label": "ID Envío"},
        {"key": "created_at", "label": "Fecha Envío (UTC)"},
        {"key": "nombre_respondente", "label": "Nombre"},
        {"key": "email_respondente", "label": "Email"},
    ]
    for p in valid_preguntas:
        columnas.append({"key": f"p_{p.id}", "label": p.titulo})

    total_envios = (
        db.query(models_surveys.EncuestaRespuestaEnvio)
        .filter(models_surveys.EncuestaRespuestaEnvio.formulario_id == survey_id)
        .count()
    )

    envios = (
        db.query(models_surveys.EncuestaRespuestaEnvio)
        .options(joinedload(models_surveys.EncuestaRespuestaEnvio.detalles))
        .filter(models_surveys.EncuestaRespuestaEnvio.formulario_id == survey_id)
        .order_by(desc(models_surveys.EncuestaRespuestaEnvio.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )

    filas = []
    for e in envios:
        det_map = {d.pregunta_id: d for d in e.detalles}
        fila = {
            "envio_id": str(e.id),
            "created_at": e.created_at.isoformat() if e.created_at else "",
            "nombre_respondente": e.nombre_respondente or "",
            "email_respondente": e.email_respondente or "",
        }
        for p in valid_preguntas:
            d = det_map.get(p.id)
            if not d:
                fila[f"p_{p.id}"] = ""
                continue

            if d.valor_texto is not None:
                fila[f"p_{p.id}"] = d.valor_texto
            elif d.valor_numero is not None:
                fila[f"p_{p.id}"] = d.valor_numero
            elif d.valor_fecha is not None:
                fila[f"p_{p.id}"] = str(d.valor_fecha)
            elif d.valor_hora is not None:
                fila[f"p_{p.id}"] = d.valor_hora
            elif d.valor_json is not None:
                if isinstance(d.valor_json, list):
                    fila[f"p_{p.id}"] = ", ".join(str(x) for x in d.valor_json)
                else:
                    fila[f"p_{p.id}"] = str(d.valor_json)
            else:
                fila[f"p_{p.id}"] = ""

        filas.append(fila)

    return schemas.EncuestaRespuestasTableResponse(
        total=total_envios,
        skip=skip,
        limit=limit,
        columnas=columnas,
        filas=filas,
    )


@router.get(
    "/surveys/{survey_id}/responses/individual/{envio_id}",
    response_model=schemas.EncuestaRespuestaEnvioIndividualResponse,
    summary="Ver respuesta individual detallada",
)
def get_individual_response(
    survey_id: uuid.UUID,
    envio_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user),
):
    survey = (
        db.query(models_surveys.EncuestaFormulario)
        .filter(
            models_surveys.EncuestaFormulario.id == survey_id,
            models_surveys.EncuestaFormulario.deleted_at.is_(None),
        )
        .first()
    )
    if not survey:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Formulario no encontrado.")

    user_sede_id = get_user_sede_id(db, current_user.id)
    if user_sede_id is not None and survey.sede_id is not None and survey.sede_id != user_sede_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado.")

    envio = (
        db.query(models_surveys.EncuestaRespuestaEnvio)
        .options(joinedload(models_surveys.EncuestaRespuestaEnvio.detalles))
        .filter(
            models_surveys.EncuestaRespuestaEnvio.id == envio_id,
            models_surveys.EncuestaRespuestaEnvio.formulario_id == survey_id,
        )
        .first()
    )
    if not envio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Respuesta no encontrada.")

    return schemas.EncuestaRespuestaEnvioIndividualResponse.model_validate(envio)


@router.get(
    "/surveys/{survey_id}/export/csv",
    summary="Exportar respuestas en CSV compatible con Excel (UTF-8 BOM)",
)
def export_survey_csv(
    survey_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_user),
):
    survey = (
        db.query(models_surveys.EncuestaFormulario)
        .options(joinedload(models_surveys.EncuestaFormulario.preguntas))
        .filter(
            models_surveys.EncuestaFormulario.id == survey_id,
            models_surveys.EncuestaFormulario.deleted_at.is_(None),
        )
        .first()
    )
    if not survey:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Formulario no encontrado.")

    user_sede_id = get_user_sede_id(db, current_user.id)
    if user_sede_id is not None and survey.sede_id is not None and survey.sede_id != user_sede_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado.")

    survey.preguntas.sort(key=lambda p: p.orden)
    valid_preguntas = [p for p in survey.preguntas if p.tipo_pregunta != schemas.TipoPregunta.SECCION_SALTO.value]

    output = io.StringIO()
    # Escribir UTF-8 BOM para que Excel en Windows y Mac reconozca tildes y caracteres especiales
    output.write("\ufeff")
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    # Cabeceras
    headers = ["ID Envío", "Fecha (UTC)", "Nombre", "Email"]
    headers.extend([p.titulo for p in valid_preguntas])
    writer.writerow(headers)

    envios = (
        db.query(models_surveys.EncuestaRespuestaEnvio)
        .options(joinedload(models_surveys.EncuestaRespuestaEnvio.detalles))
        .filter(models_surveys.EncuestaRespuestaEnvio.formulario_id == survey_id)
        .order_by(asc(models_surveys.EncuestaRespuestaEnvio.created_at))
        .all()
    )

    for e in envios:
        det_map = {d.pregunta_id: d for d in e.detalles}
        row = [
            str(e.id),
            e.created_at.strftime("%Y-%m-%d %H:%M:%S") if e.created_at else "",
            e.nombre_respondente or "",
            e.email_respondente or "",
        ]
        for p in valid_preguntas:
            d = det_map.get(p.id)
            if not d:
                row.append("")
                continue

            if d.valor_texto is not None:
                row.append(d.valor_texto)
            elif d.valor_numero is not None:
                row.append(str(d.valor_numero))
            elif d.valor_fecha is not None:
                row.append(str(d.valor_fecha))
            elif d.valor_hora is not None:
                row.append(d.valor_hora)
            elif d.valor_json is not None:
                if isinstance(d.valor_json, list):
                    row.append(", ".join(str(x) for x in d.valor_json))
                else:
                    row.append(str(d.valor_json))
            else:
                row.append("")

        writer.writerow(row)

    csv_data = output.getvalue().encode("utf-8")
    filename = f"encuesta_{survey.slug or str(survey.id)[:8]}.csv"

    return Response(
        content=csv_data,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "text/csv; charset=utf-8",
        },
    )
