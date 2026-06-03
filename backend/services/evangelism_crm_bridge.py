"""Bridge automático Evangelismo → CRM."""

from datetime import datetime, timedelta, timezone
from typing import Optional
import uuid

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


def _obtener_o_crear_pipeline_nuevos_visitantes(
    db: Session, sede_id: uuid.UUID
) -> PipelineCRM:
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
    db.add(pipeline)
    db.flush()

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
