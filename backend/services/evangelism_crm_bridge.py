"""Bridge automático Evangelismo → CRM."""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy import MetaData, Table, insert, inspect
from sqlalchemy.orm import Session, load_only

from backend.models_crm import Persona
from backend.models_crm_pipeline import (
    CanalOrigenEnum,
    CasoCRM,
    EstadoCasoEnum,
    EtapaPipeline,
    PipelineCRM,
    PrioridadCasoEnum,
    TipoPipelineEnum,
)
from backend.models_evangelism import Asistencia, GrupoEvangelismo, SesionGrupo

logger = logging.getLogger(__name__)


def _stringify_uuid_payload(payload: dict) -> dict:
    normalized = {}
    for key, value in payload.items():
        if isinstance(value, uuid.UUID):
            normalized[key] = str(value)
        else:
            normalized[key] = value
    return normalized


def _crm_etapa_pipeline_live_column_names(db: Session) -> set[str]:
    bind = db.get_bind()
    if bind is None:
        return set()
    try:
        columns = inspect(bind).get_columns("crm_etapas_pipeline")
    except Exception:
        return set()
    return {str(column.get("name")) for column in columns if column.get("name")}


def _crm_casos_live_column_names(db: Session) -> set[str]:
    bind = db.get_bind()
    if bind is None:
        return set()
    try:
        columns = inspect(bind).get_columns("crm_casos")
    except Exception:
        return set()
    return {str(column.get("name")) for column in columns if column.get("name")}


def _crm_etapa_pipeline_read_only_options(db: Session):
    live_cols = _crm_etapa_pipeline_live_column_names(db)
    selectable_names = [
        name
        for name in [
            "id",
            "pipeline_id",
            "nombre",
            "orden",
            "requiere_accion",
            "deleted_at",
            "created_at",
            "visual_color",
        ]
        if name in live_cols and hasattr(EtapaPipeline, name)
    ]
    if not selectable_names:
        return None
    return load_only(*[getattr(EtapaPipeline, name) for name in selectable_names])


def _build_transient_caso(
    *,
    caso_id: uuid.UUID,
    persona_id: uuid.UUID,
    sede_id: uuid.UUID,
    pipeline_id: uuid.UUID,
    etapa: EtapaPipeline,
    titulo_caso: str,
    origen_grupo_id: Optional[uuid.UUID],
    origen_estrategia_id: Optional[UUID],
    origen_sesion_id: Optional[UUID],
    sla_vencimiento_contacto: datetime,
) -> CasoCRM:
    caso = CasoCRM(
        id=caso_id,
        persona_id=persona_id,
        sede_id=sede_id,
        pipeline_id=pipeline_id,
        etapa_actual_id=etapa.id,
        titulo_caso=titulo_caso,
        prioridad=PrioridadCasoEnum.ALTA,
        estado=EstadoCasoEnum.ABIERTO,
        origen_canal=CanalOrigenEnum.EVANGELISMO,
        origen_grupo_id=origen_grupo_id,
        origen_estrategia_id=origen_estrategia_id,
        origen_sesion_id=origen_sesion_id,
        sla_vencimiento_contacto=sla_vencimiento_contacto,
    )
    caso.etapa_actual = etapa
    return caso


def _insert_caso_nuevo_visitante(
    db: Session,
    persona: Persona,
    sede_id: uuid.UUID,
    pipeline: PipelineCRM,
    etapa: EtapaPipeline,
    titulo_prefix: str,
    origen_grupo_id: Optional[uuid.UUID] = None,
    origen_estrategia_id: Optional[UUID] = None,
    origen_sesion_id: Optional[UUID] = None,
) -> Optional[CasoCRM]:
    caso_id = uuid.uuid4()
    bind = db.get_bind()
    if bind is not None and getattr(bind.dialect, "name", "") == "sqlite":
        caso = _build_transient_caso(
            caso_id=caso_id,
            persona_id=persona.id,
            sede_id=sede_id,
            pipeline_id=pipeline.id,
            etapa=etapa,
            titulo_caso=f"{titulo_prefix}: {persona.first_name} {persona.last_name}".strip(),
            origen_grupo_id=origen_grupo_id,
            origen_estrategia_id=origen_estrategia_id,
            origen_sesion_id=origen_sesion_id,
            sla_vencimiento_contacto=datetime.now(timezone.utc) + timedelta(hours=48),
        )
        db.add(caso)
        db.flush()
        return caso

    live_cols = _crm_casos_live_column_names(db)
    caso_data = {
        "id": caso_id,
        "persona_id": persona.id,
        "sede_id": sede_id,
        "pipeline_id": pipeline.id,
        "etapa_actual_id": etapa.id,
        "titulo_caso": f"{titulo_prefix}: {persona.first_name} {persona.last_name}".strip(),
        "prioridad": PrioridadCasoEnum.ALTA,
        "estado": EstadoCasoEnum.ABIERTO,
        "origen_canal": CanalOrigenEnum.EVANGELISMO,
        "origen_grupo_id": origen_grupo_id,
        "origen_estrategia_id": origen_estrategia_id,
        "origen_sesion_id": origen_sesion_id,
        "sla_vencimiento_contacto": datetime.now(timezone.utc) + timedelta(hours=48),
        "fecha_creacion": datetime.now(timezone.utc),
        "fecha_cierre": None,
        "deleted_at": None,
        "payload_web": None,
        "asignado_a_id": None,
    }
    if "sort_order" in live_cols:
        caso_data["sort_order"] = 0
    if "drag_source_etapa_id" in live_cols:
        caso_data["drag_source_etapa_id"] = None
    if "drag_target_etapa_id" in live_cols:
        caso_data["drag_target_etapa_id"] = None
    if "is_locked_for_reorder" in live_cols:
        caso_data["is_locked_for_reorder"] = False
    if "last_reorder_failed" in live_cols:
        caso_data["last_reorder_failed"] = False

    caso_table = Table(
        "crm_casos",
        MetaData(),
        autoload_with=db.get_bind(),
    )
    db.execute(
        insert(caso_table),
        [_stringify_uuid_payload({k: v for k, v in caso_data.items() if k in live_cols})],
    )
    return _build_transient_caso(
        caso_id=caso_id,
        persona_id=persona.id,
        sede_id=sede_id,
        pipeline_id=pipeline.id,
        etapa=etapa,
        titulo_caso=caso_data["titulo_caso"],
        origen_grupo_id=origen_grupo_id,
        origen_estrategia_id=origen_estrategia_id,
        origen_sesion_id=origen_sesion_id,
        sla_vencimiento_contacto=caso_data["sla_vencimiento_contacto"],
    )


def _obtener_o_crear_pipeline_nuevos_visitantes(
    db: Session, sede_id: uuid.UUID
) -> Optional[PipelineCRM]:
    pipeline = (
        db.query(PipelineCRM)
        .filter(
            PipelineCRM.sede_id == sede_id,
            PipelineCRM.tipo == TipoPipelineEnum.NUEVOS_VISITANTES,
            PipelineCRM.activo,
            PipelineCRM.deleted_at.is_(None),
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
        sp = db.begin_nested()  # SAVEPOINT — no destruye la transacción exterior
        db.add(pipeline)
        sp.commit()  # RELEASE SAVEPOINT — pipeline.id queda asignado
    except IntegrityError:
        sp.rollback()  # ROLLBACK TO SAVEPOINT — objetos flusheados previamente intactos
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
            logger.warning("Pipeline race condition: still missing after savepoint rollback (sede=%s)", sede_id)
            return None
        if pipeline.deleted_at is not None:
            pipeline.deleted_at = None
            db.flush()
        return pipeline  # pipeline existente ya tiene su etapa — no crear otra

    # Solo se llega aquí cuando el pipeline acaba de ser creado
    live_cols = _crm_etapa_pipeline_live_column_names(db)
    etapa_id = uuid.uuid4()
    etapa_data = {
        "id": etapa_id,
        "pipeline_id": pipeline.id,
        "nombre": "Nuevo Contacto",
        "orden": 1,
        "requiere_accion": True,
        "deleted_at": None,
        "created_at": datetime.now(timezone.utc),
    }
    if "visual_color" in live_cols:
        etapa_data["visual_color"] = None

    if "visual_color" in live_cols:
        db.add(
            EtapaPipeline(
                **{k: v for k, v in etapa_data.items() if hasattr(EtapaPipeline, k)}
            )
        )
        db.flush()  # flush sin commit — el caller hace el único db.commit() final
    else:
        etapa_table = Table(
            "crm_etapas_pipeline",
            MetaData(),
            autoload_with=db.get_bind(),
        )
        db.execute(insert(etapa_table), [{k: v for k, v in etapa_data.items() if k in live_cols}])
    return pipeline


def _obtener_o_crear_etapa_nuevo_contacto(
    db: Session,
    pipeline: PipelineCRM,
    sede_id: uuid.UUID,
) -> Optional[EtapaPipeline]:
    etapa_options = _crm_etapa_pipeline_read_only_options(db)
    etapa_query = db.query(EtapaPipeline)
    if etapa_options is not None:
        etapa_query = etapa_query.options(etapa_options)
    etapa = (
        etapa_query.filter(
            EtapaPipeline.pipeline_id == pipeline.id,
            EtapaPipeline.deleted_at.is_(None),
        )
        .order_by(EtapaPipeline.orden.asc())
        .first()
    )
    if etapa:
        return etapa

    live_cols = _crm_etapa_pipeline_live_column_names(db)
    etapa_id = uuid.uuid4()
    etapa_data = {
        "id": etapa_id,
        "pipeline_id": pipeline.id,
        "nombre": "Nuevo Contacto",
        "orden": 1,
        "requiere_accion": True,
        "deleted_at": None,
        "created_at": datetime.now(timezone.utc),
    }
    if "visual_color" in live_cols:
        etapa_data["visual_color"] = None

    try:
        sp = db.begin_nested()
        if "visual_color" in live_cols:
            db.add(
                EtapaPipeline(
                    **{k: v for k, v in etapa_data.items() if hasattr(EtapaPipeline, k)}
                )
            )
            db.flush()
        else:
            etapa_table = Table(
                "crm_etapas_pipeline",
                MetaData(),
                autoload_with=db.get_bind(),
            )
            db.execute(
                insert(etapa_table),
                [_stringify_uuid_payload({k: v for k, v in etapa_data.items() if k in live_cols})],
            )
        sp.commit()
    except IntegrityError:
        sp.rollback()
        etapa = (
            db.query(EtapaPipeline)
            .filter(EtapaPipeline.pipeline_id == pipeline.id)
            .order_by(EtapaPipeline.orden.asc())
            .first()
        )
        if etapa:
            if etapa.deleted_at is not None:
                etapa.deleted_at = None
                db.flush()
            return etapa
        logger.warning(
            "Failed to create fallback etapa Nuevo Contacto for pipeline %s (sede=%s)",
            pipeline.id,
            sede_id,
        )
        return None

    etapa = (
        db.query(EtapaPipeline)
        .filter(
            EtapaPipeline.pipeline_id == pipeline.id,
            EtapaPipeline.deleted_at.is_(None),
        )
        .order_by(EtapaPipeline.orden.asc())
        .first()
    )
    if etapa:
        return etapa
    logger.warning(
        "Fallback etapa Nuevo Contacto missing after creation for pipeline %s (sede=%s)",
        pipeline.id,
        sede_id,
    )
    return None


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
    if pipeline is None:
        logger.warning("No se pudo obtener/crear pipeline para sede=%s — skipping caso creation", sede_id)
        return None

    etapa = _obtener_o_crear_etapa_nuevo_contacto(db, pipeline, sede_id)
    if not etapa:
        logger.warning("No se pudo garantizar una etapa inicial para pipeline %s (sede=%s)", pipeline.id, sede_id)
        return None

    caso = _insert_caso_nuevo_visitante(
        db=db,
        persona=persona,
        sede_id=sede_id,
        pipeline=pipeline,
        etapa=etapa,
        titulo_prefix="Consolidar",
        origen_grupo_id=grupo.id,
        origen_estrategia_id=grupo.estrategia_id,
        origen_sesion_id=sesion.id,
    )
    db.commit()
    return caso


def crear_caso_nuevo_visitante(
    db: Session,
    persona: Persona,
    sede_id: uuid.UUID,
    titulo_prefix: str = "Seguimiento",
    origen_grupo_id: Optional[uuid.UUID] = None,
    origen_estrategia_id: Optional[UUID] = None,
    origen_sesion_id: Optional[UUID] = None,
) -> Optional[CasoCRM]:
    """Crea un caso CRM de nuevos visitantes usando el pipeline canonico por sede.
    Hace el db.commit() final — debe llamarse al final de la transacción del caller.
    """
    pipeline = _obtener_o_crear_pipeline_nuevos_visitantes(db, sede_id)
    if pipeline is None:
        logger.warning("No se pudo obtener/crear pipeline para sede=%s — skipping caso creation", sede_id)
        return None

    etapa = _obtener_o_crear_etapa_nuevo_contacto(db, pipeline, sede_id)
    if not etapa:
        logger.warning("No se pudo garantizar una etapa inicial para pipeline %s (sede=%s)", pipeline.id, sede_id)
        return None

    caso = _insert_caso_nuevo_visitante(
        db=db,
        persona=persona,
        sede_id=sede_id,
        pipeline=pipeline,
        etapa=etapa,
        titulo_prefix=titulo_prefix,
        origen_grupo_id=origen_grupo_id,
        origen_estrategia_id=origen_estrategia_id,
        origen_sesion_id=origen_sesion_id,
    )
    db.commit()  # commit único: persona + participante + pipeline nuevo (si aplica) + caso
    return caso
