"""CRM Core — Pipeline, Casos, Interacciones, Tareas (Centro de Consolidación).

Modelos para el CRM 2.0: pipelines configurables, call center omnicanal,
trazabilidad de origen, y SLAs de tiempo de respuesta.
"""
import enum
import uuid as _uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, synonym

from backend.core.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


# ──────────────────────────────────────────────
# ENUMS
# ──────────────────────────────────────────────

class TipoPipelineEnum(str, enum.Enum):
    NUEVOS_VISITANTES = "NUEVOS_VISITANTES"
    CONSEJERIA = "CONSEJERIA"
    RETENCION = "RETENCION"
    VOLUNTARIADO = "VOLUNTARIADO"


class EstadoCasoEnum(str, enum.Enum):
    ABIERTO = "ABIERTO"
    EN_PROGRESO = "EN_PROGRESO"
    ESPERANDO_RESPUESTA = "ESPERANDO_RESPUESTA"
    RESUELTO_EXITO = "RESUELTO_EXITO"
    CERRADO_PERDIDO = "CERRADO_PERDIDO"


class PrioridadCasoEnum(str, enum.Enum):
    BAJA = "BAJA"
    MEDIA = "MEDIA"
    ALTA = "ALTA"
    URGENTE = "URGENTE"


class CanalOrigenEnum(str, enum.Enum):
    WEB_FORM = "WEB_FORM"
    EVANGELISMO = "EVANGELISMO"
    ASISTENCIA_SERVICIO = "ASISTENCIA_SERVICIO"
    DERIVACION_INTERNA = "DERIVACION_INTERNA"


class TipoInteraccionEnum(str, enum.Enum):
    LLAMADA_OUTBOUND = "LLAMADA_OUTBOUND"
    LLAMADA_INBOUND = "LLAMADA_INBOUND"
    WHATSAPP = "WHATSAPP"
    EMAIL = "EMAIL"
    VISITA_PRESENCIAL = "VISITA_PRESENCIAL"
    CITA_CONSEJERIA = "CITA_CONSEJERIA"


# ──────────────────────────────────────────────
# PIPELINES
# ──────────────────────────────────────────────

class PipelineCRM(Base):
    __tablename__ = "crm_pipelines"
    __table_args__ = (
        UniqueConstraint("sede_id", "tipo", name="uq_pipeline_sede_tipo"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id"), nullable=False)
    nombre = Column(String(100), nullable=False)
    tipo = Column(SAEnum(TipoPipelineEnum), nullable=False)
    descripcion = Column(Text)
    activo = Column(Boolean, default=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    etapas = relationship("EtapaPipeline", back_populates="pipeline",
                          order_by="EtapaPipeline.orden",
                          cascade="all, delete-orphan")
    casos = relationship("CasoCRM", back_populates="pipeline")


class EtapaPipeline(Base):
    __tablename__ = "crm_etapas_pipeline"
    __table_args__ = (
        UniqueConstraint("pipeline_id", "orden", name="uq_etapa_pipeline_orden"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    pipeline_id = Column(UUID(as_uuid=True), ForeignKey("crm_pipelines.id", ondelete="CASCADE"), nullable=False, index=True)
    nombre = Column(String(100), nullable=False)
    orden = Column(Integer, nullable=False)
    requiere_accion = Column(Boolean, default=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    visual_color = Column(String(50), nullable=True)

    pipeline = relationship("PipelineCRM", back_populates="etapas")
    casos = relationship("CasoCRM", back_populates="etapa_actual")


# PlantillaMensaje vive en backend.models_crm (versión normalizada con UUID, categorías, adjuntos y bitácora).

# ──────────────────────────────────────────────
# CASOS (TICKETS)
# ──────────────────────────────────────────────

class CasoCRM(Base):
    __tablename__ = "crm_casos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="CASCADE"), nullable=False, index=True)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id"), nullable=False, index=True)
    pipeline_id = Column(UUID(as_uuid=True), ForeignKey("crm_pipelines.id"), nullable=False, index=True)
    etapa_actual_id = Column(UUID(as_uuid=True), ForeignKey("crm_etapas_pipeline.id"), nullable=False, index=True)
    titulo_caso = Column(String(200), nullable=False)
    prioridad = Column(SAEnum(PrioridadCasoEnum), default=PrioridadCasoEnum.MEDIA, index=True)
    estado = Column(SAEnum(EstadoCasoEnum), default=EstadoCasoEnum.ABIERTO, index=True)
    origen_canal = Column(SAEnum(CanalOrigenEnum), nullable=False, index=True)
    origen_detalle_id = Column(String(200), nullable=True, index=True)
    origen_sesion_id = Column(UUID(as_uuid=True), ForeignKey("sesiones_grupo.id", ondelete="SET NULL"), nullable=True)
    origen_grupo_id = Column(UUID(as_uuid=True), ForeignKey("grupos_evangelismo.id", ondelete="SET NULL"), nullable=True)
    origen_estrategia_id = Column(UUID(as_uuid=True), ForeignKey("estrategias_evangelismo.id", ondelete="SET NULL"), nullable=True)
    payload_web = Column(JSON, nullable=True)
    asignado_a_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True, index=True)
    fecha_creacion = Column(DateTime(timezone=True), default=_utcnow, index=True)
    fecha_cierre = Column(DateTime(timezone=True), nullable=True)
    sla_vencimiento_contacto = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    sort_order = Column(Integer, default=0, nullable=False)
    drag_source_etapa_id = Column(UUID(as_uuid=True), nullable=True)
    drag_target_etapa_id = Column(UUID(as_uuid=True), nullable=True)
    is_locked_for_reorder = Column(Boolean, default=False)
    last_reorder_failed = Column(Boolean, default=False)

    @hybrid_property
    def is_overdue(self) -> bool:
        if self.sla_vencimiento_contacto is None:
            return False
        return _utcnow() > self.sla_vencimiento_contacto

    @is_overdue.expression
    def is_overdue(cls):
        return (cls.sla_vencimiento_contacto != None) & (cls.sla_vencimiento_contacto < func.now())  # noqa: E711

    @classmethod
    def atomic_sort_reorder(cls, db, payload, user_sede_id, commit=True) -> None:
        case_ids = []
        for item in payload:
            cid = item["id"]
            if isinstance(cid, str):
                case_ids.append(_uuid.UUID(cid))
            else:
                case_ids.append(cid)
        
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("Duplicate IDs in reorder payload.")

        existing_cases = db.query(cls).filter(cls.id.in_(case_ids)).all()
        if len(existing_cases) != len(case_ids):
            raise ValueError("Case not found")

        for c in existing_cases:
            if c.sede_id != user_sede_id:
                raise ValueError("Sede isolation violation: some cases do not belong to user's Sede.")

        all_stage_ids = set()
        for c in existing_cases:
            all_stage_ids.add(c.etapa_actual_id)
        for item in payload:
            for key in ("stage_id", "etapa_actual_id", "etapa_id", "target_stage_id", "drag_target_etapa_id"):
                val = item.get(key)
                if val is not None:
                    if isinstance(val, str):
                        all_stage_ids.add(_uuid.UUID(val))
                    else:
                        all_stage_ids.add(val)

        if all_stage_ids:
            stage_count = db.query(EtapaPipeline).join(PipelineCRM, EtapaPipeline.pipeline_id == PipelineCRM.id).filter(
                EtapaPipeline.id.in_(list(all_stage_ids)),
                PipelineCRM.sede_id == user_sede_id
            ).count()
            if stage_count != len(all_stage_ids):
                raise ValueError("Sede isolation violation: some target stages do not belong to user's Sede.")

        try:
            all_stage_cases = db.query(cls).filter(cls.etapa_actual_id.in_(list(all_stage_ids))).order_by(cls.id).with_for_update().all()
            locked_cases_map = {c.id: c for c in all_stage_cases}
            
            for cid in case_ids:
                if cid in locked_cases_map:
                    locked_cases_map[cid].is_locked_for_reorder = True

            for item in payload:
                cid = _uuid.UUID(str(item["id"]))
                sort_order = item.get("sort_order")
                if sort_order is not None:
                    if sort_order < 0 and not cls.allow_negative_sort_indices():
                        raise ValueError("Negative sort indices are not allowed.")
                    locked_cases_map[cid].sort_order = sort_order
                
                for key in ("stage_id", "etapa_actual_id", "etapa_id", "target_stage_id", "drag_target_etapa_id"):
                    target_stage = item.get(key)
                    if target_stage is not None:
                        target_stage_uuid = _uuid.UUID(str(target_stage))
                        # Validate stage belongs to the case's pipeline
                        target_etapa = db.query(EtapaPipeline).filter(EtapaPipeline.id == target_stage_uuid).first()
                        if not target_etapa:
                            raise ValueError("Stage not found")
                        if target_etapa.pipeline_id != locked_cases_map[cid].pipeline_id:
                            raise ValueError("Stage does not belong to the case's pipeline.")
                        locked_cases_map[cid].etapa_actual_id = target_stage_uuid

            for stage_id in all_stage_ids:
                cases_in_stage = db.query(cls).filter(cls.etapa_actual_id == stage_id).all()
                has_null = any(c.sort_order is None for c in cases_in_stage)
                orders = [c.sort_order for c in cases_in_stage if c.sort_order is not None]
                has_dup = len(orders) != len(set(orders))
                
                if has_null:
                    cls.handle_null_sort_order(db, stage_id)
                if has_dup:
                    cls.resolve_duplicate_sort_index(db, stage_id)
                    cls.consecutive_sort_order(db, stage_id)

            for cid in case_ids:
                if cid in locked_cases_map:
                    locked_cases_map[cid].is_locked_for_reorder = False
                    locked_cases_map[cid].last_reorder_failed = False
            
            if commit:
                db.commit()
        except Exception as e:
            cls.reorder_transaction_rollback(db)
            raise e

    @classmethod
    def handle_null_sort_order(cls, db, stage_id) -> None:
        cases = db.query(cls).filter(cls.etapa_actual_id == stage_id).all()
        max_order = -1
        for c in cases:
            if c.sort_order is not None and c.sort_order > max_order:
                max_order = c.sort_order
        next_order = max_order + 1
        for c in cases:
            if c.sort_order is None:
                c.sort_order = next_order
                next_order += 1

    @classmethod
    def resolve_duplicate_sort_index(cls, db, stage_id) -> None:
        cases = db.query(cls).filter(cls.etapa_actual_id == stage_id).order_by(cls.sort_order, cls.id).all()
        for idx, c in enumerate(cases):
            c.sort_order = idx

    @classmethod
    def consecutive_sort_order(cls, db, stage_id) -> None:
        cls.resolve_duplicate_sort_index(db, stage_id)

    @classmethod
    def reorder_transaction_rollback(cls, db) -> None:
        db.rollback()

    @classmethod
    def allow_negative_sort_indices(cls) -> bool:
        return False

    @classmethod
    def verify_sede_isolation_on_reorder(cls, db, case_ids, user_sede_id) -> bool:
        if not case_ids:
            return True
        count = db.query(cls).filter(cls.id.in_(case_ids), cls.sede_id == user_sede_id).count()
        return count == len(case_ids)

    @classmethod
    def atomic_drag_drop_reorder(cls, db, payload, user_sede_id) -> None:
        cls.atomic_sort_reorder(db, payload, user_sede_id)

    @classmethod
    def atomic_reorder_branching_eval(cls, db, payload, user_sede_id) -> None:
        case_ids = []
        for item in payload:
            cid = item["id"]
            if isinstance(cid, str):
                case_ids.append(_uuid.UUID(cid))
            else:
                case_ids.append(cid)
        
        # Load the original stage for each case before reordering
        original_stages = {}
        for case in db.query(cls).filter(cls.id.in_(case_ids)).all():
            original_stages[case.id] = case.etapa_actual_id

        try:
            # Perform the sorting reorder without committing
            cls.atomic_sort_reorder(db, payload, user_sede_id, commit=False)

            # Compare and identify cases that changed stage
            changed_cases = []
            for case in db.query(cls).filter(cls.id.in_(case_ids)).all():
                orig_stage = original_stages.get(case.id)
                if orig_stage and orig_stage != case.etapa_actual_id:
                    changed_cases.append(case)

            if changed_cases:
                from backend.models_crm import CrmAutomation, PendingCrmAction
                from datetime import timedelta

                automations = db.query(CrmAutomation).filter(
                    CrmAutomation.trigger_event == "stage_change",
                    CrmAutomation.is_active == True
                ).all()

                for case in changed_cases:
                    for automation in automations:
                        execute_at = _utcnow() + timedelta(minutes=automation.delay_minutes or 0)
                        action = PendingCrmAction(
                            automation_id=automation.id,
                            target_persona_id=case.persona_id,
                            execute_at=execute_at,
                            status="pending"
                        )
                        db.add(action)
            db.commit()
        except Exception as e:
            cls.reorder_transaction_rollback(db)
            raise e

    persona = relationship("Persona", foreign_keys=[persona_id])
    asignado_a = relationship("Persona", foreign_keys=[asignado_a_id])
    pipeline = relationship("PipelineCRM", back_populates="casos")
    etapa_actual = relationship("EtapaPipeline", back_populates="casos")
    interacciones = relationship("InteraccionCRM", back_populates="caso",
                                 cascade="all, delete-orphan")
    tareas = relationship("TareaCRM", back_populates="caso",
                          cascade="all, delete-orphan")


# ──────────────────────────────────────────────
# INTERACCIONES (BITÁCORA CALL CENTER)
# ──────────────────────────────────────────────

class InteraccionCRM(Base):
    __tablename__ = "crm_interacciones"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    caso_id = Column(UUID(as_uuid=True), ForeignKey("crm_casos.id", ondelete="CASCADE"), nullable=False, index=True)
    realizado_por_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False, index=True)
    tipo = Column(SAEnum(TipoInteraccionEnum), nullable=False, index=True)
    fecha_interaccion = Column(DateTime(timezone=True), default=_utcnow, index=True)
    resumen = Column(Text, nullable=False)
    duration_seconds = Column(Integer, default=0)
    plantilla_usada_id = Column(UUID(as_uuid=True), ForeignKey("crm_plantillas_mensaje.id", ondelete="SET NULL"), nullable=True)

    caso = relationship("CasoCRM", back_populates="interacciones")
    realizado_por = relationship("Persona", foreign_keys=[realizado_por_id])


# ──────────────────────────────────────────────
# TAREAS CRM
# ──────────────────────────────────────────────

class TareaCRM(Base):
    __tablename__ = "crm_tareas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    caso_id = Column(UUID(as_uuid=True), ForeignKey("crm_casos.id", ondelete="CASCADE"), nullable=True, index=True)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True, index=True)
    asignado_a_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True, index=True)
    titulo = Column(String(200), nullable=False)
    descripcion = Column(Text)
    categoria = Column(String(100), default="Pastoral", nullable=True, index=True)
    fecha_vencimiento = Column(DateTime(timezone=True), nullable=True, index=True)
    estado = Column(String(20), default="pending", nullable=False, index=True)
    prioridad = Column(String(20), default="medium", nullable=False)
    fecha_completada = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)

    caso = relationship("CasoCRM", back_populates="tareas")
    persona = relationship("Persona", foreign_keys=[persona_id], back_populates="tasks")
    asignado_a = relationship("Persona", foreign_keys=[asignado_a_id])
    assignee = synonym("asignado_a")
    assignee_id = synonym("asignado_a_id")
    title = synonym("titulo")
    description = synonym("descripcion")
    category = synonym("categoria")
    due_date = synonym("fecha_vencimiento")
    status = synonym("estado")
    priority = synonym("prioridad")
    completed_at = synonym("fecha_completada")

    @hybrid_property
    def completada(self) -> bool:
        return self.estado == "completed"

    @completada.expression
    def completada(cls):
        return cls.estado == "completed"

    @completada.setter
    def completada(self, value: bool) -> None:
        self.estado = "completed" if value else "pending"


class CrmReorderLock(Base):
    __tablename__ = "crm_reorder_locks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    stage_id = Column(UUID(as_uuid=True), nullable=True)
    locked_at = Column(DateTime(timezone=True), default=_utcnow)


class CrmDragDropEvent(Base):
    __tablename__ = "crm_drag_drop_events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    caso_id = Column(UUID(as_uuid=True), nullable=True)
    source_stage_id = Column(UUID(as_uuid=True), nullable=True)
    target_stage_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
