"""CRM — Biblioteca de Recursos: categorías, plantillas, adjuntos y bitácora de envíos."""
from __future__ import annotations

import uuid
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.api.crm._shared import _resolve_campaign_personas
from backend.core.database import get_db
from backend.core.permissions import require_module_access
from backend.core.storage import storage_service
from backend.core.uploads import ensure_allowed_extension, sanitize_filename
from backend.crud.crm import get_user_sede_id, resolve_persona_id_from_identity
from backend.crud.crm_.extended import (
    create_crm_automation,
    delete_crm_automation,
    get_crm_automation,
    get_crm_automations,
    update_crm_automation,
    create_crm_automation_edge,
    delete_crm_automation_edge,
    get_crm_automation_edge,
    get_crm_automation_edges,
)
from backend.crud.crm_.resources import (
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
from backend.schemas.crm.automation import (
    AutomationTriggerPayload,
    AutomationTriggerResult,
    CrmAutomationCreate,
    CrmAutomationOut,
    CrmAutomationUpdate,
    CrmAutomationEdgeCreate,
    CrmAutomationEdgeOut,
    CrmAutomationEdgeUpdate,
)
from backend.schemas.crm.resources import (
    BitacoraEnvioOut,
    CampaignFromPlantillaPayload,
    CampaignResultOut,
    CategoriaRecursoCreate,
    CategoriaRecursoOut,
    CategoriaRecursoUpdate,
    EnviarPlantillaPayload,
    PlantillaMensajeCreate,
    PlantillaMensajeOut,
    PlantillaMensajeUpdate,
    RecursoAdjuntoOut,
)
from backend.services.messaging import (
    CommunicationOutcome,
    MessagingGateway,
    get_messaging_gateway,
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
    sede_id = get_user_sede_id(db, str(user.id))
    if str(obj.sede_id) != str(sede_id):
        raise HTTPException(403, "Acceso no autorizado")
    return PlantillaMensajeOut.from_orm_safe(obj, total_envios=count_envios(db, plantilla_id))


@router.patch("/plantillas/{plantilla_id}", response_model=PlantillaMensajeOut)
def patch_plantilla(
    plantilla_id: str,
    payload: PlantillaMensajeUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_module_access("crm")),
):
    obj = get_plantilla(db, plantilla_id)
    if not obj:
        raise HTTPException(404, "Plantilla no encontrada")
    sede_id = get_user_sede_id(db, str(user.id))
    if str(obj.sede_id) != str(sede_id):
        raise HTTPException(403, "Acceso no autorizado")
    obj = update_plantilla(db, plantilla_id, payload)
    return PlantillaMensajeOut.from_orm_safe(obj, total_envios=count_envios(db, plantilla_id))


@router.delete("/plantillas/{plantilla_id}", status_code=204)
def del_plantilla(
    plantilla_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_module_access("crm")),
):
    obj = get_plantilla(db, plantilla_id)
    if not obj:
        raise HTTPException(404, "Plantilla no encontrada")
    sede_id = get_user_sede_id(db, str(user.id))
    if str(obj.sede_id) != str(sede_id):
        raise HTTPException(403, "Acceso no autorizado")
    if not delete_plantilla(db, plantilla_id):
        raise HTTPException(404, "Plantilla no encontrada")


# ── Adjuntos ──────────────────────────────────────────────────────────────────

@router.get("/plantillas/{plantilla_id}/adjuntos", response_model=List[RecursoAdjuntoOut])
def get_adjuntos(
    plantilla_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_module_access("crm")),
):
    obj = get_plantilla(db, plantilla_id)
    if not obj:
        raise HTTPException(404, "Plantilla no encontrada")
    sede_id = get_user_sede_id(db, str(user.id))
    if str(obj.sede_id) != str(sede_id):
        raise HTTPException(403, "Acceso no autorizado")
    return [RecursoAdjuntoOut.from_orm_safe(r) for r in list_adjuntos(db, plantilla_id=plantilla_id)]


@router.post("/plantillas/{plantilla_id}/adjuntos", response_model=RecursoAdjuntoOut, status_code=201)
async def upload_adjunto(
    plantilla_id: str,
    file: UploadFile = File(...),
    nombre_recurso: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_module_access("crm")),
):
    plantilla = get_plantilla(db, plantilla_id)
    if not plantilla:
        raise HTTPException(404, "Plantilla no encontrada")
    sede_id = get_user_sede_id(db, str(user.id))
    if str(plantilla.sede_id) != str(sede_id):
        raise HTTPException(403, "Acceso no autorizado")

    safe_name = sanitize_filename(file.filename or "upload")
    try:
        ensure_allowed_extension(safe_name)
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(400, "Archivo excede el límite de 10 MB")

    url = storage_service.save_file(contents, safe_name, subfolder="crm_recursos")
    seaweed_fid = storage_service.save_file_seaweed(contents, safe_name, subfolder="crm_recursos")
    persona_id = resolve_persona_id_from_identity(db, str(user.id))

    obj = create_adjunto(
        db,
        sede_id=sede_id,
        plantilla_id=plantilla_id,
        nombre_recurso=nombre_recurso,
        seaweed_fid=seaweed_fid,
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
    from backend.models_crm import RecursoAdjunto
    import uuid
    obj = db.query(RecursoAdjunto).filter_by(id=uuid.UUID(adjunto_id), activo=True).first()
    if not obj:
        raise HTTPException(404, "Adjunto no encontrado")
    sede_id = get_user_sede_id(db, str(user.id))
    if str(obj.sede_id) != str(sede_id):
        raise HTTPException(403, "Acceso no autorizado")
    if not delete_adjunto(db, adjunto_id):
        raise HTTPException(404, "Adjunto no encontrado")


# ── Bitácora / Envíos ─────────────────────────────────────────────────────────

@router.post("/plantillas/{plantilla_id}/enviar", response_model=BitacoraEnvioOut, status_code=201)
async def enviar_plantilla(
    plantilla_id: str,
    payload: EnviarPlantillaPayload,
    db: Session = Depends(get_db),
    user=Depends(require_module_access("crm")),
    gateway: MessagingGateway = Depends(get_messaging_gateway),
):
    plantilla = get_plantilla(db, plantilla_id)
    if not plantilla:
        raise HTTPException(404, "Plantilla no encontrada")
    sede_id = get_user_sede_id(db, str(user.id))
    if str(plantilla.sede_id) != str(sede_id):
        raise HTTPException(403, "Acceso no autorizado")

    texto = plantilla.contenido_texto
    for var, valor in payload.variables.items():
        texto = texto.replace(f"{{{{{var}}}}}", valor)

    canal_val = plantilla.canal.value if hasattr(plantilla.canal, "value") else str(plantilla.canal)
    payload_log: dict = {"variables": payload.variables, "texto_hidratado": texto, "canal": canal_val}

    persona_id = resolve_persona_id_from_identity(db, str(user.id))

    # ── Send through gateway ───────────────────────────────────────────
    comms_log_id = None
    external_id = None
    outcome = None
    log_error = None
    canal_lower = canal_val.lower()

    try:
        if canal_lower == "whatsapp":
            comms = await gateway.send_whatsapp(
                db, payload.destinatario_id, texto, str(user.id),
                campaign_name=plantilla.titulo,
            )
        elif canal_lower == "email":
            comms = await gateway.send_email(
                db, payload.destinatario_id, texto, str(user.id),
                campaign_name=plantilla.titulo,
            )
        else:
            comms = await gateway.send_sms(
                db, payload.destinatario_id, texto, str(user.id),
                campaign_name=plantilla.titulo,
            )
        comms_log_id = comms.id
        external_id = comms.external_id
        outcome = str(comms.outcome) if comms.outcome else CommunicationOutcome.INTERNAL_LOG.value
        payload_log["comms_log_id"] = comms_log_id
        payload_log["external_id"] = external_id
        payload_log["outcome"] = outcome
    except Exception as exc:
        log_error = str(exc)
        outcome = CommunicationOutcome.FAILED.value
        payload_log["error"] = log_error

    envio = create_envio(
        db,
        sede_id=sede_id,
        plantilla_id=plantilla_id,
        caso_id=payload.caso_id,
        enviado_por_id=str(persona_id) if persona_id else None,
        destinatario_id=payload.destinatario_id,
        payload_hidratado=payload_log,
    )
    estado_final = "FALLIDO" if log_error else "ENVIADO"
    envio = update_estado_envio(db, str(envio.id), estado_final)
    if log_error:
        envio.log_error = log_error
        db.commit()
    return BitacoraEnvioOut.from_orm_safe(
        envio,
        communication_log_id=comms_log_id,
        external_id=external_id,
        outcome=outcome,
    )


# ── Campañas masivas ─────────────────────────────────────────────────────────


@router.post("/plantillas/{plantilla_id}/campaign", response_model=CampaignResultOut, status_code=201)
async def send_plantilla_campaign(
    plantilla_id: str,
    payload: CampaignFromPlantillaPayload,
    db: Session = Depends(get_db),
    user=Depends(require_module_access("crm")),
    gateway: MessagingGateway = Depends(get_messaging_gateway),
):
    plantilla = get_plantilla(db, plantilla_id)
    if not plantilla:
        raise HTTPException(404, "Plantilla no encontrada")
    sede_id = get_user_sede_id(db, str(user.id))
    if str(plantilla.sede_id) != str(sede_id):
        raise HTTPException(403, "Acceso no autorizado")
    sender_persona_id = resolve_persona_id_from_identity(db, str(user.id))

    personas = _resolve_campaign_personas(db, payload.target_segments, sede_id=sede_id)
    if not personas:
        raise HTTPException(404, detail="No se encontraron destinatarios para los segmentos seleccionados")

    canal_val = plantilla.canal.value if hasattr(plantilla.canal, "value") else str(plantilla.canal)
    canal_lower = canal_val.lower()
    campaign_id = f"CMP-{uuid.uuid4().hex[:12]}"
    delivered_count = 0
    failed_count = 0
    envio_ids: list[str] = []

    for persona in personas:
        merged_vars = dict(payload.default_variables)
        persona_overrides = payload.variables_por_persona.get(str(persona.id), {})
        merged_vars.update(persona_overrides)

        texto = plantilla.contenido_texto
        for var, valor in merged_vars.items():
            texto = texto.replace(f"{{{{{var}}}}}", valor)

        try:
            if canal_lower == "whatsapp":
                await gateway.send_whatsapp(
                    db, str(persona.id), texto, str(user.id),
                    campaign_name=payload.campaign_name, external_id=campaign_id,
                )
            elif canal_lower == "email":
                await gateway.send_email(
                    db, str(persona.id), texto, str(user.id),
                    campaign_name=payload.campaign_name, external_id=campaign_id,
                )
            else:
                await gateway.send_sms(
                    db, str(persona.id), texto, str(user.id),
                    campaign_name=payload.campaign_name, external_id=campaign_id,
                )
        except ValueError:
            failed_count += 1
            envio = create_envio(
                db,
                sede_id=sede_id,
                plantilla_id=plantilla_id,
                enviado_por_id=str(sender_persona_id) if sender_persona_id else None,
                destinatario_id=str(persona.id),
                payload_hidratado={
                    "canal": canal_val,
                    "campaign_id": campaign_id,
                    "texto_hidratado": texto,
                    "variables": merged_vars,
                    "error": "Destinatario sin datos de contacto",
                },
            )
            envio = update_estado_envio(db, str(envio.id), "FALLIDO")
            envio_ids.append(str(envio.id))
            continue

        delivered_count += 1
        payload_log = {
            "canal": canal_val,
            "campaign_id": campaign_id,
            "campaign_name": payload.campaign_name,
            "texto_hidratado": texto,
            "variables": merged_vars,
        }
        envio = create_envio(
            db,
            sede_id=sede_id,
            plantilla_id=plantilla_id,
            enviado_por_id=str(sender_persona_id) if sender_persona_id else None,
            destinatario_id=str(persona.id),
            payload_hidratado=payload_log,
        )
        envio = update_estado_envio(db, str(envio.id), "ENVIADO")
        envio_ids.append(str(envio.id))

    return CampaignResultOut(
        status="success" if not failed_count else "partial",
        campaign_name=payload.campaign_name,
        external_id=campaign_id,
        target_count=len(personas),
        delivered_count=delivered_count,
        failed_count=failed_count,
        envio_ids=envio_ids,
    )


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


# ---- Automatizaciones -------------------------------------------------------


@router.get("/automations", response_model=List[CrmAutomationOut])
def list_automations(
    trigger_event: Optional[str] = None,
    only_active: bool = True,
    db: Session = Depends(get_db),
    user=Depends(require_module_access("crm")),
):
    rows = get_crm_automations(db, only_active=only_active, trigger_event=trigger_event)
    return [CrmAutomationOut.from_orm_safe(r) for r in rows]


@router.post("/automations", response_model=CrmAutomationOut, status_code=201)
def create_automation(
    payload: CrmAutomationCreate,
    db: Session = Depends(get_db),
    user=Depends(require_module_access("crm")),
):
    obj = create_crm_automation(db, payload)
    return CrmAutomationOut.from_orm_safe(obj)


@router.get("/automations/{automation_id}", response_model=CrmAutomationOut)
def get_one_automation(
    automation_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_module_access("crm")),
):
    obj = get_crm_automation(db, automation_id)
    if not obj:
        raise HTTPException(404, "Automatizacion no encontrada")
    return CrmAutomationOut.from_orm_safe(obj)


@router.patch("/automations/{automation_id}", response_model=CrmAutomationOut)
def patch_automation(
    automation_id: UUID,
    payload: CrmAutomationUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_module_access("crm")),
):
    obj = update_crm_automation(db, automation_id, payload)
    if not obj:
        raise HTTPException(404, "Automatizacion no encontrada")
    return CrmAutomationOut.from_orm_safe(obj)


@router.delete("/automations/{automation_id}", status_code=204)
def del_automation(
    automation_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_module_access("crm")),
):
    if not delete_crm_automation(db, automation_id):
        raise HTTPException(404, "Automatizacion no encontrada")


@router.get("/automations/edges", response_model=List[CrmAutomationEdgeOut])
def list_automation_edges(
    source_id: Optional[UUID] = None,
    target_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    user=Depends(require_module_access("crm")),
):
    rows = get_crm_automation_edges(db, source_id=source_id, target_id=target_id)
    return [CrmAutomationEdgeOut.from_orm_safe(r) for r in rows]


@router.post("/automations/edges", response_model=CrmAutomationEdgeOut, status_code=201)
def create_automation_edge(
    payload: CrmAutomationEdgeCreate,
    db: Session = Depends(get_db),
    user=Depends(require_module_access("crm")),
):
    # Validate source automation exists
    source = get_crm_automation(db, payload.source_id)
    if not source:
        raise HTTPException(404, f"Source automation with id {payload.source_id} not found")
        
    # Validate target automation exists
    target = get_crm_automation(db, payload.target_id)
    if not target:
        raise HTTPException(404, f"Target automation with id {payload.target_id} not found")
        
    obj = create_crm_automation_edge(db, payload)
    return CrmAutomationEdgeOut.from_orm_safe(obj)


@router.delete("/automations/edges/{edge_id}", status_code=204)
def delete_automation_edge(
    edge_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_module_access("crm")),
):
    if not delete_crm_automation_edge(db, edge_id):
        raise HTTPException(404, "Edge not found")


@router.post("/automations/trigger", response_model=List[AutomationTriggerResult])
async def trigger_automations(
    payload: AutomationTriggerPayload,
    db: Session = Depends(get_db),
    user=Depends(require_module_access("crm")),
    gateway: MessagingGateway = Depends(get_messaging_gateway),
):
    automations = get_crm_automations(db, only_active=True, trigger_event=payload.trigger_event)
    if not automations:
        return []

    target_persona_id = payload.context.get("persona_id")
    results: list[AutomationTriggerResult] = []

    for automation in automations:
        act = (automation.action_type or "").strip().lower()
        ap = automation.action_payload or {}

        if act != "send_plantilla":
            results.append(AutomationTriggerResult(
                automation_id=automation.id,
                automation_name=automation.name,
                status="skipped",
                detail=f"Tipo de accion '{act}' no implementado",
            ))
            continue

        plantilla_id = ap.get("plantilla_id")
        if not plantilla_id:
            results.append(AutomationTriggerResult(
                automation_id=automation.id,
                automation_name=automation.name,
                status="skipped",
                detail="action_payload.plantilla_id no especificado",
            ))
            continue

        if not target_persona_id:
            results.append(AutomationTriggerResult(
                automation_id=automation.id,
                automation_name=automation.name,
                status="skipped",
                detail="context.persona_id no especificado",
            ))
            continue

        plantilla = get_plantilla(db, plantilla_id)
        if not plantilla:
            results.append(AutomationTriggerResult(
                automation_id=automation.id,
                automation_name=automation.name,
                status="failed",
                detail="Plantilla no encontrada",
            ))
            continue

        texto = plantilla.contenido_texto
        for var, valor in (ap.get("variables") or {}).items():
            texto = texto.replace(f"{{{{{var}}}}}", str(valor))

        canal = (ap.get("canal") or str(plantilla.canal)).lower()
        ext_id = f"AUTO-{uuid.uuid4().hex[:12]}"

        try:
            if canal == "whatsapp":
                await gateway.send_whatsapp(
                    db, target_persona_id, texto, str(user.id),
                    campaign_name=f"Auto: {automation.name}", external_id=ext_id,
                )
            elif canal == "email":
                await gateway.send_email(
                    db, target_persona_id, texto, str(user.id),
                    campaign_name=f"Auto: {automation.name}", external_id=ext_id,
                )
            else:
                await gateway.send_sms(
                    db, target_persona_id, texto, str(user.id),
                    campaign_name=f"Auto: {automation.name}", external_id=ext_id,
                )
            results.append(AutomationTriggerResult(
                automation_id=automation.id,
                automation_name=automation.name,
                status="triggered",
            ))
        except ValueError as exc:
            results.append(AutomationTriggerResult(
                automation_id=automation.id,
                automation_name=automation.name,
                status="failed",
                detail=str(exc),
            ))

    return results
