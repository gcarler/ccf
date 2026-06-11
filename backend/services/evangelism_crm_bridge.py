"""Bridge automático Evangelismo → CRM."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models_crm import Persona
from backend.models_evangelism import Asistencia, GrupoEvangelismo, SesionGrupo
from backend.models_crm_core import (
    CasoCRM,
    CanalOrigenEnum,
    EstadoCasoEnum,
    EtapaPipeline,
    PipelineCRM,
    PrioridadCasoEnum,
    TipoPipelineEnum,
)

logger = logging.getLogger(__name__)


def _obtener_o_crear_pipeline_nuevos_visitantes(
    db: Session, sede_id: uuid.UUID
) -> Optional[PipelineCRM]:
    pipeline = (
        db.query(PipelineCRM)
        .filter(
            PipelineCRM.sede_id == sede_id,
            PipelineCRM.tipo == TipoPipelineEnum.NUEVOS_VISITANTES,
            PipelineCRM.activo,
        )
        .first()
    )
    if pipeline:
        return pipeline

    pipeline = PipelineCRM(
        sede_id=sede_id,
        nombre="Nuevos Visitantes",
        tipo=TipoPipelineEnum.NUEVOS_VISITANTES,
        activo=True,
    )
    try:
        sp = db.begin_nested()  # SAVEPOINT — no afecta la transacción exterior
        db.add(pipeline)
        sp.commit()
    except IntegrityError:
        sp.rollback()  # ROLLBACK TO SAVEPOINT — persona/participante intactos
        pipeline = (
            db.query(PipelineCRM)
            .filter(
                PipelineCRM.sede_id == sede_id,
                PipelineCRM.tipo == TipoPipelineEnum.NUEVOS_VISITANTES,
                PipelineCRM.activo,
            )
            .first()
        )
        if not pipeline:
            logger.error("Pipeline race condition: still missing after rollback to savepoint (sede=%s)", sede_id)
            return None

    etapa = EtapaPipeline(
        pipeline_id=pipeline.id,
        nombre="Nuevo Contacto",
        orden=1,
        requiere_accion=True,
    )
    db.add(etapa)
    db.commit()
    db.refresh(pipeline)
    return pipeline


def crear_caso_desde_asistencia(
    db: Session,
    asistencia: Asistencia,
    persona: Persona,
    grupo: GrupoEvangelismo,
    sesion: SesionGrupo,
    sede_id: uuid.UUID,
) -> Optional[CasoCRM]:
    """Crea un CasoCRM en pipeline NUEVOS_VISITANTES cuando:
    - asistencia.es_primera_vez == True
    - asistencia.requiere_seguimiento == True
    """
    if not (asistencia.es_primera_vez or asistencia.requiere_seguimiento):
        return None

    pipeline = _obtener_o_crear_pipeline_nuevos_visitantes(db, sede_id)

    etapa = (
        db.query(EtapaPipeline)
        .filter(EtapaPipeline.pipeline_id == pipeline.id)
        .order_by(EtapaPipeline.orden.asc())
        .first()
    )
    if not etapa:
        logger.warning(
            "No etapas found for pipeline %s (sede=%s) — skipping caso creation",
            pipeline.id, sede_id,
        )
        return None

    sla = datetime.now(timezone.utc) + timedelta(hours=48)

    caso = CasoCRM(
        persona_id=persona.id,
        sede_id=sede_id,
        pipeline_id=pipeline.id,
        etapa_actual_id=etapa.id,
        titulo_caso=f"Consolidar: {persona.first_name} {persona.last_name}",
        prioridad=PrioridadCasoEnum.ALTA,
        estado=EstadoCasoEnum.ABIERTO,
        origen_canal=CanalOrigenEnum.EVANGELISMO,
        sla_vencimiento_contacto=sla,
    )
    db.add(caso)
    db.commit()
    db.refresh(caso)
    return caso


def crear_caso_nuevo_visitante(
    db: Session,
    persona: Persona,
    sede_id: uuid.UUID,
    titulo_prefix: str = "Seguimiento",
    origen_grupo_id: Optional[uuid.UUID] = None,
    origen_estrategia_id: Optional[str] = None,
    origen_sesion_id: Optional[int] = None,
) -> Optional[CasoCRM]:
    """Crea un caso CRM de nuevos visitantes usando el pipeline canonico por sede."""
    pipeline = _obtener_o_crear_pipeline_nuevos_visitantes(db, sede_id)
    etapa = (
        db.query(EtapaPipeline)
        .filter(EtapaPipeline.pipeline_id == pipeline.id)
        .order_by(EtapaPipeline.orden.asc())
        .first()
    )
    if not etapa:
        logger.warning(
            "No etapas found for pipeline %s (sede=%s) — skipping caso creation",
            pipeline.id, sede_id,
        )
        return None

    caso = CasoCRM(
        persona_id=persona.id,
        sede_id=sede_id,
        pipeline_id=pipeline.id,
        etapa_actual_id=etapa.id,
        titulo_caso=f"{titulo_prefix}: {persona.first_name} {persona.last_name}".strip(),
        prioridad=PrioridadCasoEnum.ALTA,
        estado=EstadoCasoEnum.ABIERTO,
        origen_canal=CanalOrigenEnum.EVANGELISMO,
        origen_grupo_id=origen_grupo_id,
        origen_estrategia_id=origen_estrategia_id,
        origen_sesion_id=origen_sesion_id,
        sla_vencimiento_contacto=datetime.now(timezone.utc) + timedelta(hours=48),
    )
    db.add(caso)
    db.commit()
    db.refresh(caso)
    return caso
