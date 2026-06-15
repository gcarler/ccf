"""CRM — Biblioteca de Recursos: categorías, plantillas, adjuntos y bitácora de envíos."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.auth import require_module_access
from backend.core.database import get_db
from backend.core.storage import storage_service
from backend.core.uploads import ensure_allowed_extension, sanitize_filename
from backend.crud.crm import get_user_sede_id, resolve_persona_id_from_identity
from backend.crud.crm_resources import (
    count_envios,
    create_adjunto,
    create_categoria,
    create_envio,
    create_plantilla,
    delete_adjunto,
    delete_categoria,
    delete_plantilla,
    get_plantilla,
    list_adjuntos,
    list_categorias,
    list_envios_plantilla,
    list_envios_sede,
    list_plantillas,
    update_categoria,
    update_estado_envio,
    update_plantilla,
)
from backend.schemas.crm_resources import (
    BitacoraEnvioOut,
    CategoriaRecursoCreate,
    CategoriaRecursoOut,
    CategoriaRecursoUpdate,
    EnviarPlantillaPayload,
    PlantillaMensajeCreate,
    PlantillaMensajeOut,
    PlantillaMensajeUpdate,
    RecursoAdjuntoOut,
)

router = APIRouter(prefix="/resources", tags=["CRM Recursos"])


# ── Categorías ────────────────────────────────────────────────────────────────

@router.get("/categorias", response_model=List[CategoriaRecursoOut])
def get_categorias(
    db: Session = Depends(get_db),
    user=Depends(require_module_access("crm")),
):
    return [CategoriaRecursoOut.from_orm_safe(c) for c in list_categorias(db)]


@router.post("/categorias", response_model=CategoriaRecursoOut, status_code=201)
def post_categoria(
    payload: CategoriaRecursoCreate,
    db: Session = Depends(get_db),
    user=Depends(require_module_access("crm")),
):
    obj = create_categoria(db, payload)
    return CategoriaRecursoOut.from_orm_safe(obj)


@router.patch("/categorias/{categoria_id}", response_model=CategoriaRecursoOut)
def patch_categoria(
    categoria_id: str,
    payload: CategoriaRecursoUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_module_access("crm")),
):
    obj = update_categoria(db, categoria_id, payload)
    if not obj:
        raise HTTPException(404, "Categoría no encontrada")
    return CategoriaRecursoOut.from_orm_safe(obj)


@router.delete("/categorias/{categoria_id}", status_code=204)
def del_categoria(
    categoria_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_module_access("crm")),
):
    if not delete_categoria(db, categoria_id):
        raise HTTPException(404, "Categoría no encontrada")


# ── Plantillas ────────────────────────────────────────────────────────────────

@router.get("/plantillas", response_model=List[PlantillaMensajeOut])
def get_plantillas(
    canal: Optional[str] = None,
    categoria_id: Optional[str] = None,
    q: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    user=Depends(require_module_access("crm")),
):
    sede_id = get_user_sede_id(db, str(user.id))
    rows = list_plantillas(db, sede_id=sede_id, canal=canal, categoria_id=categoria_id, q=q, skip=skip, limit=limit)
    return [PlantillaMensajeOut.from_orm_safe(r, total_envios=count_envios(db, str(r.id))) for r in rows]


@router.post("/plantillas", response_model=PlantillaMensajeOut, status_code=201)
def post_plantilla(
    payload: PlantillaMensajeCreate,
    db: Session = Depends(get_db),
    user=Depends(require_module_access("crm")),
):
    sede_id = get_user_sede_id(db, str(user.id))
    persona_id = resolve_persona_id_from_identity(db, str(user.id))
    obj = create_plantilla(db, payload, sede_id=sede_id, creado_por_id=str(persona_id) if persona_id else None)
    return PlantillaMensajeOut.from_orm_safe(obj, total_envios=0)


@router.get("/plantillas/{plantilla_id}", response_model=PlantillaMensajeOut)
def get_one_plantilla(
    plantilla_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_module_access("crm")),
):
    obj = get_plantilla(db, plantilla_id)
    if not obj:
        raise HTTPException(404, "Plantilla no encontrada")
    return PlantillaMensajeOut.from_orm_safe(obj, total_envios=count_envios(db, plantilla_id))


@router.patch("/plantillas/{plantilla_id}", response_model=PlantillaMensajeOut)
def patch_plantilla(
    plantilla_id: str,
    payload: PlantillaMensajeUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_module_access("crm")),
):
    obj = update_plantilla(db, plantilla_id, payload)
    if not obj:
        raise HTTPException(404, "Plantilla no encontrada")
    return PlantillaMensajeOut.from_orm_safe(obj, total_envios=count_envios(db, plantilla_id))


@router.delete("/plantillas/{plantilla_id}", status_code=204)
def del_plantilla(
    plantilla_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_module_access("crm")),
):
    if not delete_plantilla(db, plantilla_id):
        raise HTTPException(404, "Plantilla no encontrada")


# ── Adjuntos ──────────────────────────────────────────────────────────────────

@router.get("/plantillas/{plantilla_id}/adjuntos", response_model=List[RecursoAdjuntoOut])
def get_adjuntos(
    plantilla_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_module_access("crm")),
):
    return [RecursoAdjuntoOut.from_orm_safe(r) for r in list_adjuntos(db, plantilla_id=plantilla_id)]


@router.post("/plantillas/{plantilla_id}/adjuntos", response_model=RecursoAdjuntoOut, status_code=201)
async def upload_adjunto(
    plantilla_id: str,
    file: UploadFile = File(...),
    nombre_recurso: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_module_access("crm")),
):
    if not get_plantilla(db, plantilla_id):
        raise HTTPException(404, "Plantilla no encontrada")

    safe_name = sanitize_filename(file.filename or "upload")
    try:
        ensure_allowed_extension(safe_name)
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(400, "Archivo excede el límite de 10 MB")

    url = storage_service.save_file(contents, safe_name, subfolder="crm_recursos")
    sede_id = get_user_sede_id(db, str(user.id))
    persona_id = resolve_persona_id_from_identity(db, str(user.id))

    obj = create_adjunto(
        db,
        sede_id=sede_id,
        plantilla_id=plantilla_id,
        nombre_recurso=nombre_recurso,
        url_acceso=url,
        nombre_archivo=file.filename or safe_name,
        tipo_mime=file.content_type or "application/octet-stream",
        peso_bytes=len(contents),
        creado_por_id=str(persona_id) if persona_id else None,
    )
    return RecursoAdjuntoOut.from_orm_safe(obj)


@router.delete("/adjuntos/{adjunto_id}", status_code=204)
def del_adjunto(
    adjunto_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_module_access("crm")),
):
    if not delete_adjunto(db, adjunto_id):
        raise HTTPException(404, "Adjunto no encontrado")


# ── Bitácora / Envíos ─────────────────────────────────────────────────────────

@router.post("/plantillas/{plantilla_id}/enviar", response_model=BitacoraEnvioOut, status_code=201)
def enviar_plantilla(
    plantilla_id: str,
    payload: EnviarPlantillaPayload,
    db: Session = Depends(get_db),
    user=Depends(require_module_access("crm")),
):
    plantilla = get_plantilla(db, plantilla_id)
    if not plantilla:
        raise HTTPException(404, "Plantilla no encontrada")

    texto = plantilla.contenido_texto
    for var, valor in payload.variables.items():
        texto = texto.replace(f"{{{{{var}}}}}", valor)

    canal_val = plantilla.canal.value if hasattr(plantilla.canal, "value") else str(plantilla.canal)
    payload_log = {"variables": payload.variables, "texto_hidratado": texto, "canal": canal_val}

    sede_id = get_user_sede_id(db, str(user.id))
    persona_id = resolve_persona_id_from_identity(db, str(user.id))

    envio = create_envio(
        db,
        sede_id=sede_id,
        plantilla_id=plantilla_id,
        caso_id=payload.caso_id,
        enviado_por_id=str(persona_id) if persona_id else None,
        destinatario_id=payload.destinatario_id,
        payload_hidratado=payload_log,
    )
    envio = update_estado_envio(db, str(envio.id), "ENVIADO")
    return BitacoraEnvioOut.from_orm_safe(envio)


@router.get("/plantillas/{plantilla_id}/bitacora", response_model=List[BitacoraEnvioOut])
def get_bitacora_plantilla(
    plantilla_id: str,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    user=Depends(require_module_access("crm")),
):
    rows = list_envios_plantilla(db, plantilla_id=plantilla_id, skip=skip, limit=limit)
    return [BitacoraEnvioOut.from_orm_safe(r) for r in rows]


@router.get("/bitacora", response_model=List[BitacoraEnvioOut])
def get_bitacora_sede(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    user=Depends(require_module_access("crm")),
):
    sede_id = get_user_sede_id(db, str(user.id))
    rows = list_envios_sede(db, sede_id=sede_id, skip=skip, limit=limit)
    return [BitacoraEnvioOut.from_orm_safe(r) for r in rows]
