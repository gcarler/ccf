"""
Public Contact Tracking Service (Task 3.1)

Reusable service that encapsulates the pattern:
  "find-or-create Persona, create CasoCRM/Pipeline lead, track source"

All public-facing endpoints should use this service instead of inline duplication.
"""
import logging
from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend import models
from backend.models_crm_pipeline import (
    CanalOrigenEnum,
    EstadoCasoEnum,
    TipoPipelineEnum,
)

logger = logging.getLogger(__name__)


@dataclass
class ContactRecord:
    """Input record for a public contact."""
    email: Optional[str] = None
    phone: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    source: str = "web"
    landing_page: Optional[str] = None
    campaign: Optional[str] = None
    notes: Optional[str] = None
    spiritual_status: str = "Nuevo"
    church_role: str = "Visitante"
    extra_notes: list[str] = field(default_factory=list)
    sede_id: Optional[UUID] = None


@dataclass
class ContactResult:
    """Output record after tracking a contact."""
    persona: Optional[models.Persona] = None
    persona_created: bool = False
    case: Optional[models.CasoCRM] = None
    case_created: bool = False


def _normalize(val: Optional[str]) -> Optional[str]:
    if val is None:
        return None
    v = val.strip()
    return v if v else None


class PublicContactTracker:
    """
    Tracks every public contact into the CRM pipeline consistently.

    Usage:
        tracker = PublicContactTracker()
        result = tracker.record_contact(db, ContactRecord(...))
    """

    def record_contact(self, db: Session, record: ContactRecord) -> ContactResult:
        result = ContactResult()

        email = _normalize(record.email)
        phone = _normalize(record.phone)

        # 1. Find existing Persona by phone or email
        persona = self._find_persona(db, email, phone)
        sede = self._resolve_sede(db, record.sede_id, persona)
        if sede is None:
            raise RuntimeError("No active sede is configured for public contacts")

        # 2. Create Persona if not found
        if not persona:
            persona = models.Persona(
                first_name=record.first_name or "Visitante",
                last_name=record.last_name or "",
                email=email,
                phone=phone,
                sede_id=sede.id,
                spiritual_status=record.spiritual_status,
                church_role=record.church_role,
            )
            db.add(persona)
            db.flush()
            result.persona_created = True
            logger.info(
                "Nueva Persona creada via contacto público: %s %s (%s)",
                persona.first_name,
                persona.last_name,
                email or phone,
            )
        elif persona.sede_id is None:
            persona.sede_id = sede.id

        result.persona = persona

        # 3. Create a canonical CRM case in the sede visitor pipeline.
        notes_lines = list(record.extra_notes)
        if record.notes:
            notes_lines.append(record.notes)
        if record.landing_page:
            notes_lines.append(f"Landing: {record.landing_page}")
        if record.campaign:
            notes_lines.append(f"Campaign: {record.campaign}")

        pipeline = (
            db.query(models.PipelineCRM)
            .filter(
                models.PipelineCRM.sede_id == sede.id,
                models.PipelineCRM.tipo == TipoPipelineEnum.NUEVOS_VISITANTES,
                models.PipelineCRM.deleted_at.is_(None),
            )
            .first()
        )
        if pipeline is None:
            pipeline = models.PipelineCRM(
                sede_id=sede.id,
                nombre="Nuevos visitantes",
                tipo=TipoPipelineEnum.NUEVOS_VISITANTES,
                activo=True,
            )
            db.add(pipeline)
            db.flush()

        stage = (
            db.query(models.EtapaPipeline)
            .filter(
                models.EtapaPipeline.pipeline_id == pipeline.id,
                models.EtapaPipeline.deleted_at.is_(None),
            )
            .order_by(models.EtapaPipeline.orden)
            .first()
        )
        if stage is None:
            stage = models.EtapaPipeline(
                pipeline_id=pipeline.id,
                nombre="Nuevo",
                orden=1,
            )
            db.add(stage)
            db.flush()

        case = models.CasoCRM(
            persona_id=persona.id,
            sede_id=sede.id,
            pipeline_id=pipeline.id,
            etapa_actual_id=stage.id,
            titulo_caso=(notes_lines[0] if notes_lines else f"Contacto: {record.source}")[:200],
            estado=EstadoCasoEnum.ABIERTO,
            origen_canal=CanalOrigenEnum.WEB_FORM,
            origen_detalle_id=record.source[:200],
            payload_web={
                "source": record.source,
                "landing_page": record.landing_page,
                "campaign": record.campaign,
                "notes": notes_lines,
            },
        )
        db.add(case)
        db.flush()
        result.case = case
        result.case_created = True

        return result

    @staticmethod
    def _resolve_sede(
        db: Session, sede_id: Optional[UUID], persona: Optional[models.Persona]
    ):
        candidate = sede_id or (persona.sede_id if persona else None)
        query = db.query(models.Sede).filter(
            models.Sede.es_activa.is_(True),
            models.Sede.deleted_at.is_(None),
        )
        if candidate:
            return query.filter(models.Sede.id == candidate).first()
        return query.order_by(models.Sede.nombre).first()

    @staticmethod
    def _find_persona(
        db: Session, email: Optional[str], phone: Optional[str]
    ) -> Optional[models.Persona]:
        """Find an existing Persona by email or phone."""
        conditions = []
        if phone:
            conditions.append(models.Persona.phone == phone)
        if email:
            conditions.append(models.Persona.email == email)

        if not conditions:
            return None

        return db.query(models.Persona).filter(or_(*conditions)).first()


# Module-level convenience instance
tracker = PublicContactTracker()
