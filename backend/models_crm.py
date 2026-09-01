from __future__ import annotations

import enum as _enum
import uuid
import uuid as _uuid
from datetime import date

from sqlalchemy import Enum as SAEnum
from sqlalchemy import Index, text
from sqlalchemy import func as _func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import validates

# Compatibility alias for integrations that still import the canonical CRM
# case model from this module while the implementation lives in the pipeline
# model module.
from backend.models_crm_pipeline import CasoCRM as CrmCaso
from backend.models_shared import *  # noqa: F403 — re-exports SQLAlchemy primitives (Base, Column, UUID, etc.) used throughout this module
from backend.models_shared import _utcnow


# 3. CRM & CHAT
class Family(Base):
    __tablename__ = "families"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    name = Column(String(100), nullable=False)
    address = Column(Text, nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    personas = relationship("Persona", back_populates="family")


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (Index("ix_chat_messages_room_id_created_at", "room_id", "created_at"),)
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    sender_id = Column(UUID(as_uuid=True), ForeignKey("auth_users.id"), nullable=False, index=True)
    room_id = Column(String(100), nullable=True, index=True)
    content = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)

    attachment_url = Column(Text, nullable=True)  # URL del archivo subido
    attachment_type = Column(String(50), nullable=True)  # 'image', 'pdf', 'document', 'video', 'audio', 'other'
    attachment_name = Column(String(255), nullable=True)  # nombre original del archivo
    attachment_size = Column(Integer, nullable=True)  # tamaño en bytes
    reply_to_id = Column(UUID(as_uuid=True), nullable=True)
    mentions_raw = Column(Text, nullable=True)  # JSON array de UUIDs como string


class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    last_message_content = Column(Text, nullable=True)
    last_message_at = Column(DateTime(timezone=True), nullable=True, index=True)
    last_sender_id = Column(UUID(as_uuid=True), ForeignKey("auth_users.id"), nullable=True)


class ConversationParticipant(Base):
    __tablename__ = "conversation_participants"
    __table_args__ = (UniqueConstraint("conversation_id", "user_id", name="uq_conversation_user"),)
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    last_read_at = Column(DateTime(timezone=True), nullable=True)
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    conversation = relationship("Conversation", backref="participants")
    user = relationship("Usuario")


class CrmEvent(Base):
    __tablename__ = "crm_events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id"), nullable=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    event_date = Column(DateTime(timezone=True), nullable=True, index=True)
    event_type = Column(String(20), default="PERMANENT", index=True)
    start_time = Column(String(50), nullable=True)
    end_time = Column(String(50), nullable=True)
    day_of_week = Column(Integer, nullable=True)
    month_day = Column(String(10), nullable=True)
    location = Column(String(200), nullable=True)
    status = Column(String(20), default="SCHEDULED", index=True)
    cancellation_reason = Column(Text, nullable=True)
    target_audience = Column(String(50), default="ALL")
    # ── Pre-registration features (plan_de_preregistro, migration 20260804_0001)
    # Defaults seguros (FALSE / NULL) → los eventos existentes siguen funcionando
    # como eventos abiertos sin pre-inscripción (backward-compatible).
    requires_registration = Column(Boolean, nullable=False, default=False, server_default="0")
    requires_email_verification = Column(Boolean, nullable=False, default=False, server_default="0")
    registration_opens_at = Column(DateTime(timezone=True), nullable=True)
    registration_closes_at = Column(DateTime(timezone=True), nullable=True)
    capacity_max = Column(Integer, nullable=True)
    waiting_list_enabled = Column(Boolean, nullable=False, default=False, server_default="0")
    qr_mode = Column(String(20), nullable=False, default="PER_REGISTRANT", server_default="PER_REGISTRANT")
    contact_person = Column(String(255), nullable=True)
    settings_json = Column(JSON, default=dict)
    # plan_de_form_builder: vinculación con CmsForm para render dinámico de
    # preinscripción. NULL = form fijo (backward-compat con el flujo actual).
    form_id = Column(UUID(as_uuid=True), ForeignKey("cms_forms.id", ondelete="SET NULL"), nullable=True)
    # plan_clasificador_contextual: rol contextual por defecto del evento
    # (NULL = el servicio resuelve VISITANTE_EVENTO).
    participant_role_code = Column(String(40), nullable=True, index=True)
    target_role_id = Column(UUID(as_uuid=True), ForeignKey("role_definitions.id"), nullable=True)
    target_role_ids = Column(JSON, nullable=True)
    target_persona_ids = Column(JSON, nullable=True)
    fixed_date = Column(DateTime(timezone=True), nullable=True)
    attendance_closed_at = Column(DateTime(timezone=True), nullable=True, index=True)
    attendance_closed_by = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    @validates("target_persona_ids")
    def validate_target_persona_ids(self, key, value):
        if isinstance(value, list):
            return [str(v) if isinstance(v, uuid.UUID) else v for v in value]
        return value

    attendances = relationship("EventAttendance", back_populates="event")
    assignments = relationship("EventAssignment", back_populates="event")
    registrations = relationship("EventRegistration", back_populates="event", cascade="all, delete-orphan")
    campaigns = relationship("EventCampaign", back_populates="event", cascade="all, delete-orphan")
    identity_challenges = relationship("EventIdentityChallenge", back_populates="event", cascade="all, delete-orphan")


class EventAssignment(Base):
    __tablename__ = "event_assignments"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    event_id = Column(
        UUID(as_uuid=True),
        ForeignKey("crm_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_date = Column(Date, nullable=False, index=True)
    persona_id = Column(
        UUID(as_uuid=True),
        ForeignKey("personas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String(50), nullable=False, index=True)  # e.g. MC, PREACHER, OFFERING
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    event = relationship("CrmEvent", back_populates="assignments")
    persona = relationship("Persona")


class EventAttendance(Base):
    __tablename__ = "event_attendances"
    __table_args__ = (UniqueConstraint("event_id", "session_date", "persona_id", name="uq_event_attendance"),)
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    event_id = Column(
        UUID(as_uuid=True),
        ForeignKey("crm_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_date = Column(Date, nullable=False, index=True, default=lambda: _utcnow().date())
    persona_id = Column(
        UUID(as_uuid=True),
        ForeignKey("personas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(String(30), default="present", index=True)
    role_at_event = Column(String(40), default="attendee", index=True)
    source = Column(String(30), default="manual", index=True)
    check_in_at = Column(DateTime(timezone=True), nullable=True, index=True)
    check_out_at = Column(DateTime(timezone=True), nullable=True, index=True)
    notes = Column(Text, nullable=True)
    scanned_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    attended = Column(Boolean, default=True)
    # QC-07 (auditoría de calidad 2026-07-25): deleted_at ahora declarado en
    # el modelo ORM + migración 20260725_0003 — antes el CRUD
    # delete_event_attendance hacia ``row.deleted_at = _utcnow()`` pero la
    # columna no existia (Postgres rompia / SQLite descartaba silenciosamente
    # dejando la asistencia "viva" y contada en pastoral_health_score).
    # Alineado al patrón soft-delete uniforme CCF (ver QC-02 CommunicationLog).
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    event = relationship("CrmEvent", back_populates="attendances")
    persona = relationship("Persona")


# ==============================================================================
# PRE-REGISTRO A EVENTOS MASIVOS (plan_de_preregistro, migración 20260804_0001)
# ==============================================================================


class EventRegistration(Base):
    """Pre-inscripción de una Persona a un CrmEvent con ciclo de vida propio.

    Estados (``registration_status``):
        PENDING   → registrada, esperando verificación email (opcional)
        CONFIRMED → verificada / auto-confirmada (QR generado)
        CHECKED_IN→ asistió al evento el día D (check-in QR/manual)
        ABSENT    → no asistió al cierre del evento
        WAITLIST  → en lista de espera (aforo lleno)
        CANCELLED → cancelada por el usuario o el admin (soft, deleted_at set)

    QR: ``qr_token`` = ``CCF-EVT-{event_id}-{persona_id}-{secret}`` y
    ``qr_token_hash`` = sha256 del secret (patrón alineado con
    ``Persona.scanner_token_hash`` en ``models_crm.py:452``).

    Axioma 3: el scope por sede se hereda vía ``event_id → crm_events.sede_id``
    (no hay ``sede_id`` propio — single source of truth en el evento).
    """

    __tablename__ = "event_registrations"
    __table_args__ = (
        UniqueConstraint("event_id", "persona_id", name="uq_event_reg_persona"),
        # Fix #13: evita duplicados de waiting_list_position por evento en
        # carreras de cancelación+promote concurrentes. Partial index (WHERE
        # NOT NULL) porque la mayoría de filas están CONFIRMED/CHECKED_IN/
        # PENDING con position=None — un UNIQUE total rompería al permitir
        # varios NULL (en Postgres un UNIQUE estándar deja NULLs múltiples
        # pero el ORm/test suite con SQLite puede ser más estricto).
        Index(
            "uq_event_reg_waitlist_position",
            "event_id",
            "waiting_list_position",
            postgresql_where=text("waiting_list_position IS NOT NULL"),
            sqlite_where=text("waiting_list_position IS NOT NULL"),
        ),
        Index("ix_reg_event_status", "event_id", "registration_status"),
        Index("ix_reg_qr", "qr_token_hash"),
        Index("ix_reg_deleted_at", "deleted_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("crm_events.id", ondelete="CASCADE"), nullable=False)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="CASCADE"), nullable=False)
    registration_status = Column(String(20), nullable=False, default="PENDING")
    qr_token = Column(String(128), nullable=True, unique=True, index=True)
    qr_token_hash = Column(String(128), nullable=True, index=True)
    qr_generated_at = Column(DateTime(timezone=True), nullable=True)
    registered_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    check_in_at = Column(DateTime(timezone=True), nullable=True)
    check_out_at = Column(DateTime(timezone=True), nullable=True)
    checked_in_by = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True)
    source = Column(String(30), nullable=False, default="public_form")
    extras = Column(JSON, default=dict)
    # ── Preferencias de comunicación (plan followup, migración 20260807_0001) ──
    # Snapshot del consentimiento al momento del registro (se preserva la
    # decisión que se usó para cada evento, no la preferencia actual del perfil).
    communication_consent = Column(Boolean, nullable=False, default=True, server_default=text("TRUE"))
    consent_source = Column(String(40), nullable=True)
    consent_at = Column(DateTime(timezone=True), nullable=True)
    consent_policy_version = Column(String(40), nullable=True)
    preferred_channels = Column(JSON, nullable=False, default=list, server_default=text("'[]'"))
    transactional_notifications_enabled = Column(Boolean, nullable=False, default=True, server_default=text("TRUE"))
    marketing_opt_out_at = Column(DateTime(timezone=True), nullable=True)
    # plan_clasificador_contextual: rol efectivo en esta inscripción (hereda
    # del evento en el momento del registro; override admin autorizado).
    participant_role_code = Column(String(40), nullable=True, index=True)
    waiting_list_position = Column(Integer, nullable=True)
    reminder_sent_count = Column(Integer, nullable=False, default=0)
    last_reminder_sent_at = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)
    crm_case_id = Column(UUID(as_uuid=True), ForeignKey("crm_casos.id", ondelete="SET NULL"), nullable=True, index=True)

    event = relationship("CrmEvent", back_populates="registrations")
    persona = relationship("Persona", foreign_keys=[persona_id])
    checked_in_by_persona = relationship("Persona", foreign_keys=[checked_in_by])
    crm_case = relationship("CasoCRM", foreign_keys=[crm_case_id], back_populates="event_registrations")


class EventCampaign(Base):
    """Campaña de mensajería ligada a un evento (plan_de_preregistro).

    Reusa ``PlantillaMensaje`` (CRM) para el contenido + variables ``{{var}}``,
    y ``services/messaging.py`` (gateway WhatsApp/Email/SMS) para el envío.
    El scheduler (``backend/scheduler.py``) procesa las campañas con
    ``trigger_type`` RELATIVE_TO_EVENT / RELATIVE_TO_REGISTRATION.
    """

    __tablename__ = "event_campaigns"
    __table_args__ = (
        Index("ix_campaign_event", "event_id"),
        Index("ix_campaign_active", "is_active"),
        Index("ix_campaign_deleted_at", "deleted_at"),
        Index("ix_event_campaign_default_key", "default_key"),
        Index(
            "uq_event_campaign_default_key",
            "event_id",
            "default_key",
            unique=True,
            postgresql_where=text("default_key IS NOT NULL AND deleted_at IS NULL"),
            sqlite_where=text("default_key IS NOT NULL AND deleted_at IS NULL"),
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("crm_events.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)
    # plan_followup: clave estable del catálogo default (migración 20260808_0002)
    # para reutilizar/recrear campañas estándar sin duplicar.
    default_key = Column(String(60), nullable=True)
    # plan_followup: tipo de comunicación que clasifica el consentimiento
    # (OPERATIONAL / ROUTINE / PASTORAL) — migración 20260807_0001.
    communication_type = Column(String(20), nullable=False, default="ROUTINE", server_default="ROUTINE")
    plantilla_id = Column(
        UUID(as_uuid=True),
        ForeignKey("crm_plantillas_mensaje.id", ondelete="SET NULL"),
        nullable=True,
    )
    canal = Column(String(20), nullable=False, default="EMAIL")
    trigger_type = Column(String(50), nullable=False, default="MANUAL")
    trigger_offset_minutes = Column(Integer, nullable=True)
    target_status = Column(JSON, default=list)
    sent_count = Column(Integer, nullable=False, default=0)
    last_sent_at = Column(DateTime(timezone=True), nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    event = relationship("CrmEvent", back_populates="campaigns")
    plantilla = relationship("PlantillaMensaje")
    created_by = relationship("Persona", foreign_keys=[created_by_id])


class CounselingTicket(Base):
    __tablename__ = "counseling_tickets"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    persona_id = Column(
        UUID(as_uuid=True),
        ForeignKey("personas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pastor_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True, index=True)
    subject = Column(String(200), nullable=False)
    notes = Column(Text, nullable=True)
    status = Column(String(50), default="open", index=True)  # open, in_progress, resolved
    priority_level = Column(String(20), default="NORMAL", index=True)  # URGENT, HIGH, NORMAL
    sentiment_score = Column(Float, nullable=True)  # -1.0 a 1.0
    sentiment_label = Column(String(20), nullable=True)  # POSITIVE, NEUTRAL, NEGATIVE
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    persona = relationship("Persona", foreign_keys=[persona_id])
    pastor = relationship("Persona", foreign_keys=[pastor_id])


class PrayerRequest(Base):
    __tablename__ = "prayer_requests"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True)
    requester_name = Column(String(200), nullable=False, index=True)
    request_text = Column(Text, nullable=False)
    category = Column(String(50), default="General")
    is_public = Column(Boolean, default=False, index=True)
    source = Column(String(50), default="crm", index=True)  # web, crm, evangelism
    status = Column(String(50), default="pending", index=True)  # pending, praying, answered
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)


class Ministry(Base):
    __tablename__ = "ministries"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    leader_persona_id = Column(
        UUID(as_uuid=True),
        ForeignKey("personas.id"),
        nullable=True,
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    personas = relationship(
        "Persona",
        secondary="persona_ministry_assignments",
        primaryjoin="Ministry.id == PersonaMinistryAssignment.ministry_id",
        secondaryjoin="PersonaMinistryAssignment.persona_id == Persona.id",
        overlaps="persona,personas,ministries,ministry",
        viewonly=True,
        foreign_keys="[PersonaMinistryAssignment.ministry_id, PersonaMinistryAssignment.persona_id]",
    )


# ==============================================================================
# BIBLIOTECA DE RECURSOS CRM
# ==============================================================================


class CanalEnvio(_enum.Enum):
    WHATSAPP = "WHATSAPP"
    EMAIL = "EMAIL"
    SMS = "SMS"


class EstadoEnvioPlantilla(_enum.Enum):
    PROCESANDO = "PROCESANDO"
    ENVIADO = "ENVIADO"
    ENTREGADO = "ENTREGADO"
    LEIDO = "LEIDO"
    FALLIDO = "FALLIDO"


class CategoriaRecurso(Base):
    """Agrupa plantillas para facilitar búsqueda en la UI del CRM."""

    __tablename__ = "crm_recurso_categorias"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre = Column(String(100), unique=True, nullable=False, index=True)
    descripcion = Column(Text, nullable=True)
    color_ui_hex = Column(String(10), default="#6B7280")
    activo = Column(Boolean, default=True, nullable=False, index=True)


class PlantillaMensaje(Base):
    """Plantillas de mensajes con soporte para variables dinámicas {{var}}."""

    __tablename__ = "crm_plantillas_mensaje"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id"), nullable=False, index=True)
    categoria_id = Column(
        UUID(as_uuid=True), ForeignKey("crm_recurso_categorias.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    titulo = Column(String(150), nullable=False, index=True)
    canal = Column(SAEnum(CanalEnvio), nullable=False, index=True)
    asunto = Column(String(200), nullable=True)
    contenido_texto = Column(Text, nullable=False)
    contenido_html = Column(Text, nullable=True)
    variables_requeridas = Column(
        JSON().with_variant(ARRAY(String), "postgresql"),
        default=list,
        nullable=False,
    )
    meta_template_id = Column(String(150), nullable=True)
    creado_por_id = Column(
        UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True, index=True
    )
    fecha_creacion = Column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)
    fecha_actualizacion = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)
    activo = Column(Boolean, default=True, nullable=False, index=True)

    categoria = relationship("CategoriaRecurso")
    adjuntos = relationship("RecursoAdjunto", back_populates="plantilla", cascade="all, delete-orphan")


class RecursoAdjunto(Base):
    """Archivos multimedia vinculados a plantillas (local storage; seaweed_fid para migración futura)."""

    __tablename__ = "crm_recursos_adjuntos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id"), nullable=False, index=True)
    plantilla_id = Column(
        UUID(as_uuid=True), ForeignKey("crm_plantillas_mensaje.id", ondelete="CASCADE"), nullable=True, index=True
    )
    nombre_recurso = Column(String(150), nullable=False)
    seaweed_fid = Column(String(100), nullable=True)
    url_acceso = Column(String, nullable=False)
    nombre_archivo = Column(String(255), nullable=False)
    tipo_mime = Column(String(100), nullable=False)
    peso_bytes = Column(Integer, nullable=False)
    creado_por_id = Column(
        UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True, index=True
    )
    fecha_creacion = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    activo = Column(Boolean, default=True, nullable=False, index=True)

    plantilla = relationship("PlantillaMensaje", back_populates="adjuntos")


class BitacoraEnvioPlantilla(Base):
    """Registro analítico de cada envío de plantilla: quién, a quién, con qué variables, resultado."""

    __tablename__ = "crm_envios_plantilla_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id"), nullable=False, index=True)
    plantilla_id = Column(
        UUID(as_uuid=True), ForeignKey("crm_plantillas_mensaje.id", ondelete="SET NULL"), nullable=True, index=True
    )
    caso_id = Column(UUID(as_uuid=True), ForeignKey("crm_casos.id", ondelete="CASCADE"), nullable=True, index=True)
    enviado_por_id = Column(
        UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True, index=True
    )
    destinatario_id = Column(
        UUID(as_uuid=True), ForeignKey("personas.id", ondelete="CASCADE"), nullable=False, index=True
    )
    fecha_envio = Column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)
    estado = Column(SAEnum(EstadoEnvioPlantilla), default=EstadoEnvioPlantilla.PROCESANDO, nullable=False, index=True)
    payload_hidratado = Column(JSON, nullable=False)
    log_error = Column(Text, nullable=True)

    plantilla = relationship("PlantillaMensaje")
    enviado_por = relationship("Persona", foreign_keys=[enviado_por_id])
    destinatario = relationship("Persona", foreign_keys=[destinatario_id])


class ColombianDepartment(Base):
    __tablename__ = "colombian_departments"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    name = Column(String(50), unique=True, nullable=False)
    code = Column(String(3), unique=True, nullable=False)
    capital = Column(String(100), nullable=False)


class Persona(Base):
    __tablename__ = "personas"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    family_id = Column(UUID(as_uuid=True), ForeignKey("families.id", ondelete="SET NULL"), nullable=True, index=True)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True)
    first_name = Column(String(100), nullable=False, index=True)
    last_name = Column(String(100), nullable=False, index=True)
    second_name = Column(String(100), nullable=True)
    second_last_name = Column(String(100), nullable=True)
    email = Column(String(100), nullable=True, index=True)
    phone = Column(String(20), nullable=True, index=True)
    mobile_phone = Column(String(20), nullable=True)
    landline_phone = Column(String(20), nullable=True)
    other_phone = Column(String(20), nullable=True)
    church_role = Column(String(50), default="Miembro", index=True)
    is_baptized = Column(Boolean, default=False, index=True)
    baptism_date = Column(Date, nullable=True)
    spiritual_status = Column(String(50), default="Nuevo", index=True)
    estado_vital = Column(String(50), nullable=True, default="ACTIVO")
    ministerio = Column(String(100), nullable=True)
    permiso_plataforma = Column(String(50), nullable=True)
    id_type = Column(String(50), nullable=True)
    id_number = Column(String(50), nullable=True)
    marital_status = Column(String(50), nullable=True)
    birth_country = Column(String(100), nullable=True)
    address = Column(Text, nullable=True)
    housing_type = Column(String(50), nullable=True)
    education_level = Column(String(100), nullable=True)
    education_status = Column(String(50), nullable=True)
    profession = Column(String(100), nullable=True)
    economic_sector = Column(String(100), nullable=True)
    blood_type = Column(String(10), nullable=True)
    medical_notes = Column(Text, nullable=True)
    optional_info = Column(Text, nullable=True)
    registration_reason = Column(String(100), nullable=True)
    unregistration_reason = Column(String(100), nullable=True)
    registration_date = Column(Date, nullable=True)
    unregistration_date = Column(Date, nullable=True)
    responsible_adult_name = Column(String(200), nullable=True)
    responsible_adult_contact = Column(String(100), nullable=True)
    guardian_name = Column(String(200), nullable=True)
    guardian_contact = Column(String(100), nullable=True)
    sex = Column(String(1), nullable=True)
    last_group_attendance = Column(Date, nullable=True)
    last_meeting_attendance = Column(Date, nullable=True)
    participation_type = Column(String(50), nullable=True)
    attendance_type = Column(String(50), nullable=True)
    group_name = Column(String(100), nullable=True)
    campus = Column(String(100), nullable=True)
    church_join_date = Column(Date, nullable=True)
    colombian_department_id = Column(
        UUID(as_uuid=True), ForeignKey("colombian_departments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    city = Column(String(100), nullable=True)
    latitud = Column(Numeric(10, 8), nullable=True)
    longitud = Column(Numeric(11, 8), nullable=True)
    qr_token = Column(String(100), nullable=True, index=True)
    birthday = Column(Date, nullable=True)
    role_in_family = Column(String(50), nullable=True)
    talents = Column(Text, nullable=True)
    spiritual_gifts = Column(Text, nullable=True)
    pastoral_notes = Column(Text, nullable=True)
    health_score = Column(Integer, nullable=True)
    health_status = Column(String(20), nullable=True)

    # ── Pastoral profile fields ───────────────────────────────────────────
    photo_url = Column(String(500), nullable=True)
    bio_short = Column(Text, nullable=True)
    bio_full = Column(Text, nullable=True)
    social_instagram = Column(String(200), nullable=True)
    social_facebook = Column(String(200), nullable=True)
    social_twitter = Column(String(200), nullable=True)
    is_pastoral_leader = Column(Boolean, default=False, index=True)
    is_main_pastor = Column(Boolean, default=False)
    pastoral_sort_order = Column(Integer, default=0)
    is_pastoral_published = Column(Boolean, default=True)

    tags = Column(JSON, nullable=True, default=list)
    origen_estrategia_id = Column(
        UUID(as_uuid=True), ForeignKey("estrategias_evangelismo.id", ondelete="SET NULL"), nullable=True, index=True
    )
    origen_grupo_id = Column(
        UUID(as_uuid=True), ForeignKey("grupos_evangelismo.id", ondelete="SET NULL"), nullable=True, index=True
    )
    origen_sesion_id = Column(UUID(as_uuid=True), ForeignKey("sesiones_grupo.id", ondelete="SET NULL"), nullable=True)
    origen_evento_id = Column(
        UUID(as_uuid=True), ForeignKey("crm_events.id", ondelete="SET NULL"), nullable=True, index=True
    )
    origen_fecha = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    # Scanner token para validación de códigos QR (producción)
    scanner_token_hash = Column(String(128), nullable=True, index=True, comment="SHA-256 hash del scanner token")
    scanner_token_expires_at = Column(
        DateTime(timezone=True), nullable=True, comment="Fecha de expiración del scanner token"
    )

    @hybrid_property
    def nombre_completo(self):
        parts = [self.first_name or "", self.last_name or ""]
        return " ".join(p for p in parts if p).strip() or "Sin nombre"

    @nombre_completo.expression
    def nombre_completo(cls):
        return _func.trim(_func.coalesce(cls.first_name, "") + " " + _func.coalesce(cls.last_name, ""))

    @hybrid_property
    def telefono(self):
        return self.phone or self.mobile_phone

    @telefono.expression
    def telefono(cls):
        return _func.coalesce(cls.phone, cls.mobile_phone)

    @property
    def church_role_effective(self) -> str:
        """Rol en la iglesia resuelto desde el Kernel."""
        if self.rol_iglesia and self.rol_iglesia.church_role:
            val = self.rol_iglesia.church_role
            return val.value if hasattr(val, "value") else str(val)
        return self.church_role or "Miembro"

    @church_role_effective.setter
    def church_role_effective(self, value: str) -> None:
        """Establece el rol efectivo delegando a ``church_role``.

        Mantiene simetría con el getter (que retorna ``church_role`` cuando
        no hay ``rol_iglesia``). Tests y callers pueden usar el setter para
        inyectar el rol esperado sin necesidad de cablear
        ``PersonaRoleAssignment`` (``rol_iglesia``).
        """
        self.church_role = value

    family = relationship("Family", overlaps="family,personas,personas")
    colombian_department = relationship("ColombianDepartment", foreign_keys=[colombian_department_id])
    origen_estrategia = relationship("EstrategiaEvangelismo", foreign_keys=[origen_estrategia_id])
    origen_grupo = relationship("GrupoEvangelismo", foreign_keys=[origen_grupo_id])
    origen_evento = relationship("CrmEvent", foreign_keys=[origen_evento_id])

    positions = relationship("PersonaPosition", back_populates="persona")
    donations = relationship("Donation", foreign_keys="Donation.persona_id", back_populates="persona")
    tasks = relationship("TareaCRM", foreign_keys="TareaCRM.persona_id", back_populates="persona")
    volunteer_shifts = relationship(
        "VolunteerShift", foreign_keys="VolunteerShift.persona_id", back_populates="persona"
    )
    mentor_assignments = relationship(
        "PersonaMentorship",
        foreign_keys="PersonaMentorship.mentor_persona_id",
        back_populates="mentor",
    )
    mentee_assignments = relationship(
        "PersonaMentorship",
        foreign_keys="PersonaMentorship.mentee_persona_id",
        back_populates="mentee",
    )
    communication_logs = relationship(
        "CommunicationLog", foreign_keys="CommunicationLog.persona_id", back_populates="persona"
    )
    participaciones_grupo = relationship("ParticipanteGrupo", back_populates="persona")
    asistencias = relationship("Asistencia", back_populates="persona")
    event_registrations = relationship(
        "EventRegistration", foreign_keys="EventRegistration.persona_id", back_populates="persona"
    )
    seguimientos_realizados = relationship(
        "RegistroSeguimiento", foreign_keys="RegistroSeguimiento.responsable_id", back_populates="responsable"
    )
    historial_embudo = relationship("HistorialEmbudo", back_populates="persona")
    ministerios_kernel = relationship(
        "PersonaMinistry", foreign_keys="PersonaMinistry.persona_id", back_populates="persona"
    )
    rol_iglesia = relationship(
        "PersonaRoleAssignment",
        foreign_keys="PersonaRoleAssignment.persona_id",
        back_populates="persona",
        uselist=False,
    )


class Position(Base):
    __tablename__ = "positions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=True, index=True)
    is_active = Column(Boolean, default=True, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)

    persona_positions = relationship("PersonaPosition", back_populates="position", cascade="all, delete-orphan")


class PersonaPosition(Base):
    __tablename__ = "persona_positions"
    __table_args__ = (UniqueConstraint("persona_id", "position_id", "start_date", name="uq_persona_position_history"),)
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    persona_id = Column(
        UUID(as_uuid=True),
        ForeignKey("personas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position_id = Column(
        UUID(as_uuid=True),
        ForeignKey("positions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    start_date = Column(DateTime(timezone=True), nullable=True, index=True)
    end_date = Column(DateTime(timezone=True), nullable=True, index=True)
    is_active = Column(Boolean, default=True, index=True)
    notes = Column(Text, nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)

    persona = relationship("Persona", back_populates="positions")
    position = relationship("Position", back_populates="persona_positions")


class Donation(Base):
    __tablename__ = "donations"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    persona_id = Column(
        UUID(as_uuid=True),
        ForeignKey("personas.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    amount = Column(Numeric(14, 2), nullable=False)
    currency = Column(String(10), default="COP")
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True)
    donation_type = Column(String(50), default="Diezmo", index=True)
    status = Column(String(20), default="completed", index=True)
    reference_code = Column(String(100), nullable=True)
    payment_method = Column(String(50), default="Transferencia")
    fund_id = Column(UUID(as_uuid=True), ForeignKey("funds.fund_id", ondelete="SET NULL"), nullable=True, index=True)
    # donor_name/email solo para donaciones anónimas (persona_id IS NULL)
    donor_name = Column(String(100), nullable=True)
    donor_email = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    donation_date = Column(Date, nullable=True, default=date.today)

    persona = relationship("Persona", back_populates="donations")
    fund = relationship("Fund")


class DonationCategory(Base):
    __tablename__ = "donation_categories"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    name = Column(String(100), nullable=False)
    description = Column(String(255))
    color_code = Column(String(50), default="blue")
    is_active = Column(Boolean, default=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)


class VolunteerShift(Base):
    __tablename__ = "volunteer_shifts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True)
    persona_id = Column(
        UUID(as_uuid=True),
        ForeignKey("personas.id"),
        nullable=False,
        index=True,
    )
    role_name = Column(String(100), nullable=False)
    team_name = Column(String(100), nullable=False)
    shift_start = Column(DateTime(timezone=True), nullable=False)
    shift_end = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(20), default="confirmed")
    notes = Column(Text, nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    persona = relationship("Persona", back_populates="volunteer_shifts")


class VolunteerSkill(Base):
    __tablename__ = "volunteer_skills"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)
    category = Column(String(100))
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)


persona_volunteer_skills = Table(
    "persona_volunteer_skills",
    Base.metadata,
    Column(
        "persona_id",
        UUID(as_uuid=True),
        ForeignKey("personas.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "skill_id",
        UUID(as_uuid=True),
        ForeignKey("volunteer_skills.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class PersonaMentorship(Base):
    __tablename__ = "persona_mentorships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True)
    mentee_persona_id = Column(
        UUID(as_uuid=True),
        ForeignKey("personas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mentor_persona_id = Column(
        UUID(as_uuid=True),
        ForeignKey("personas.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    assigned_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("auth_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status = Column(String(20), default="active", nullable=False, index=True)
    notes = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)
    ended_at = Column(DateTime(timezone=True), nullable=True, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    mentor = relationship("Persona", foreign_keys=[mentor_persona_id], back_populates="mentor_assignments")
    mentee = relationship("Persona", foreign_keys=[mentee_persona_id], back_populates="mentee_assignments")
    assigned_by = relationship("Usuario")


class CommunicationLog(Base):
    """Registro de comunicación interna o externa con una persona.

    Tabla central del módulo de mensajería. Cada fila representa un mensaje
    enviado o recibido a través de cualquier canal (internal, WhatsApp, SMS,
    Email). No tiene ``sede_id`` propio; el scope multi-tenant se obtiene vía
    JOIN con ``Persona`` (FK ``persona_id``).

    Soft-delete: ``deleted_at`` (REGLAS.md §6). Las queries CRUD filtran
    ``deleted_at IS NULL``. ``delete_communication_log()`` setting
    ``deleted_at`` en vez de borrar la fila.

    Campos añadidos en auditoría Fase 1:
      - ``deleted_at`` (C-01): soft-delete column.
      - ``campaign_name``, ``recipient_phone``, ``is_read``, ``external_id``
        (A-03): ya existían en el modelo; schema de respuesta extenedido.

    Relationships:
      - ``persona``: Persona destinataria ( ``persona_id`` ).
      - ``leader``: Persona que origina el mensaje ( ``leader_id`` ).
    """

    __tablename__ = "communication_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    persona_id = Column(
        UUID(as_uuid=True),
        ForeignKey("personas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel = Column(String(50), nullable=False, index=True)
    recipient_phone = Column(String(30), nullable=True)
    campaign_name = Column(String(120), nullable=True, index=True)
    content = Column(Text, nullable=False)
    leader_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True, index=True)
    outcome = Column(String(50), default="sent", index=True)
    external_id = Column(String(120), nullable=True, index=True)
    is_read = Column(Boolean, default=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)

    persona = relationship("Persona", foreign_keys=[persona_id], back_populates="communication_logs")
    leader = relationship("Persona", foreign_keys=[leader_id])


class SpiritualMilestone(Base):
    __tablename__ = "spiritual_milestones"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True)
    persona_id = Column(
        UUID(as_uuid=True),
        ForeignKey("personas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type = Column(String(100), nullable=False, index=True)
    event_date = Column(Date, nullable=False)
    minister_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True, index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    persona = relationship("Persona", foreign_keys=[persona_id])
    minister = relationship("Persona", foreign_keys=[minister_id])


class CrmAutomation(Base):
    __tablename__ = "crm_automations"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    name = Column(String(100), nullable=False)
    trigger_event = Column(String(50), nullable=False)
    action_type = Column(String(50), nullable=False)
    action_payload = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    # Nuevos campos para flujos encadenados
    delay_minutes = Column(Integer, default=0, nullable=False)
    ui_graph_state = Column(JSON, nullable=True)


class CrmAutomationFlow(Base):
    """Un flujo de automatización del CRM.

    Axioma 3 — Aislamiento por Sede: ``sede_id`` atribuye el flujo a un tenant.
    Es ``nullable=True`` para no romper rows pre-migración (backfill pendiente);
    el contrato del API exige ``sede_id is not None`` al crear flujos nuevos y
    filtra por sede del actor en toda lectura/escritura. Un flujo heredado con
    ``sede_id IS NULL`` sólo es legible/modificable por un actor sin sede
    (super administrador de plataforma).
    """

    __tablename__ = "crm_automation_flows"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id"), nullable=True, index=True)
    name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class CrmAutomationNode(Base):
    __tablename__ = "crm_automation_nodes"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    flow_id = Column(
        UUID(as_uuid=True), ForeignKey("crm_automation_flows.id", ondelete="CASCADE"), nullable=False, index=True
    )
    node_type = Column(String(50), nullable=False)
    ports_config = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class CrmFlowCanvasConfig(Base):
    __tablename__ = "crm_flow_canvas_config"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    flow_id = Column(
        UUID(as_uuid=True), ForeignKey("crm_automation_flows.id", ondelete="CASCADE"), nullable=False, index=True
    )
    zoom = Column(Float, default=1.0)
    pan_x = Column(Float, default=0.0)
    pan_y = Column(Float, default=0.0)


class CrmFlowBranch(Base):
    __tablename__ = "crm_flow_branches"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    node_id = Column(
        UUID(as_uuid=True), ForeignKey("crm_automation_nodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    conditions_logic = Column(JSON, nullable=True)


class CrmFlowCycleCache(Base):
    __tablename__ = "crm_flow_cycle_cache"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    flow_id = Column(
        UUID(as_uuid=True), ForeignKey("crm_automation_flows.id", ondelete="CASCADE"), nullable=False, index=True
    )
    has_cycle = Column(Boolean, default=False)


class CrmAutomationEdge(Base):
    __tablename__ = "crm_automation_edges"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(
        UUID(as_uuid=True), ForeignKey("crm_automations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_id = Column(
        UUID(as_uuid=True), ForeignKey("crm_automations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    condition_type = Column(String(50), nullable=True)
    condition_key = Column(String(100), nullable=True)
    condition_value = Column(String(200), nullable=True)
    source_node_id = Column(
        UUID(as_uuid=True), ForeignKey("crm_automation_nodes.id", ondelete="CASCADE"), nullable=True
    )
    target_node_id = Column(
        UUID(as_uuid=True), ForeignKey("crm_automation_nodes.id", ondelete="CASCADE"), nullable=True
    )
    on_delete_cascade = Column(Boolean, default=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    source = relationship("CrmAutomation", foreign_keys=[source_id], backref="outgoing_edges")
    target = relationship("CrmAutomation", foreign_keys=[target_id], backref="incoming_edges")


def validate_three_node_path(path_or_nodes) -> bool:
    """
    Genuine verification method bound to the table structure.
    Ensures that the input path contains at least 3 nodes.
    """
    if not path_or_nodes:
        return False
    return len(path_or_nodes) >= 3


CrmAutomationEdge.__table__.validate_three_node_path = validate_three_node_path


class PendingCrmAction(Base):
    __tablename__ = "crm_pending_actions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    automation_id = Column(UUID(as_uuid=True), ForeignKey("crm_automations.id"), nullable=False)
    target_persona_id = Column(UUID(as_uuid=True), nullable=False)
    execute_at = Column(DateTime(timezone=True), nullable=False, index=True)
    status = Column(String(30), default="pending", index=True)  # pending, executed, failed
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    automation = relationship("CrmAutomation")


class RoleDefinition(Base):
    __tablename__ = "role_definitions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True, index=True)
    color = Column(String(50), default="blue")
    is_leadership = Column(Boolean, default=False, index=True)
    is_system_locked = Column(Boolean, default=False, index=True)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id"), nullable=True, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class PersonaRoleLink(Base):
    __tablename__ = "persona_role_links"
    __table_args__ = (UniqueConstraint("persona_id", "role_id", name="uq_persona_role_link"),)
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    persona_id = Column(
        UUID(as_uuid=True),
        ForeignKey("personas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role_id = Column(
        UUID(as_uuid=True),
        ForeignKey("role_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    persona = relationship("Persona")
    role = relationship("RoleDefinition")


class PersonaMinistryAssignment(Base):
    """Rich association between Persona and Ministry with role and dates."""

    __tablename__ = "persona_ministry_assignments"
    __table_args__ = (UniqueConstraint("persona_id", "ministry_id", name="uq_persona_ministry_assignment"),)
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    persona_id = Column(
        UUID(as_uuid=True),
        ForeignKey("personas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ministry_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ministries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String(50), nullable=True)  # e.g. Líder, Asistente, Coordinador
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    notes = Column(Text, nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    persona = relationship("Persona", overlaps="persona,personas,ministries,ministry")
    ministry = relationship("Ministry", overlaps="persona,personas,ministries,ministry")


class Fund(Base):
    __tablename__ = "funds"
    fund_id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(120), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    is_public = Column(Boolean, default=False)
    current_balance = Column(Numeric(14, 2), default=0)
    target_amount = Column(Numeric(14, 2), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class SupportTicket(Base):
    __tablename__ = "support_tickets"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False, index=True)
    subject = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default="open", index=True)  # open, in_progress, resolved, closed
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    # QC-06 (auditoría de calidad 2026-07-25): deleted_at ahora declarado en
    # el modelo ORM y migracion 20260725_0003 — antes el CRUD
    # delete_support_ticket hacia ``row.deleted_at = _utcnow()`` pero la
    # columna no existia (Postgres rompia al commit / SQLite descartaba
    # silenciosamente dejando el ticket "vivo"). Alineado al patrón
    # soft-delete uniforme CCF (ver QC-02 CommunicationLog).
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    user = relationship("Persona")


class CommunityBoardCard(Base):
    __tablename__ = "community_board_cards"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True)
    column_id = Column(String(50), nullable=True, index=True)
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=True)
    position = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)


class EventCommunicationDelivery(Base):
    """Entrega planificada de una campaña para una inscripción concreta.

    Tabla ``event_communication_deliveries`` (migración 20260807_0001). La
    unicidad ``(registration_id, campaign_id, communication_key)`` garantiza
    idempotencia ante materialización concurrente (el servicio absorbe el
    IntegrityError con un savepoint). ``recipient_masked`` conserva solo el
    contacto enmascarado (defensa de datos, nunca PII completa).
    """

    __tablename__ = "event_communication_deliveries"
    __table_args__ = (
        UniqueConstraint(
            "registration_id",
            "campaign_id",
            "communication_key",
            name="uq_event_communication_delivery_key",
        ),
        Index("ix_event_delivery_registration", "registration_id"),
        Index("ix_event_delivery_campaign", "campaign_id"),
        Index("ix_event_delivery_status_next_attempt", "status", "next_attempt_at"),
        Index("ix_event_delivery_event_update", "event_update_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    registration_id = Column(
        UUID(as_uuid=True), ForeignKey("event_registrations.id", ondelete="CASCADE"), nullable=False
    )
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("event_campaigns.id", ondelete="CASCADE"), nullable=False)
    event_update_id = Column(String(100), nullable=True)
    communication_key = Column(String(180), nullable=False)
    channel = Column(String(20), nullable=False)
    recipient_masked = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False, default="QUEUED", server_default="QUEUED")
    skip_reason = Column(String(80), nullable=True)
    consent_rule_applied = Column(String(40), nullable=True)
    attempt_count = Column(Integer, nullable=False, default=0, server_default="0")
    next_attempt_at = Column(DateTime(timezone=True), nullable=True)
    provider_message_id = Column(String(180), nullable=True)
    last_error = Column(Text, nullable=True)
    payload_version = Column(String(40), nullable=True)
    queued_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    registration = relationship("EventRegistration", foreign_keys=[registration_id])
    campaign = relationship("EventCampaign", foreign_keys=[campaign_id])


class EventIdentityChallenge(Base):
    """Desafío de identidad de un solo uso para el pre-registro público.

    Tabla ``event_identity_challenges`` (migración 20260807_0001). Guarda
    SOLO hashes (identificador y código en claro nunca se persisten) y el
    token verificado (``verified_identity_token_hash``) single-use: al
    consumirse, ``consumed_at`` bloquea el replay y el vínculo al evento
    (``event_id``) impide el uso cross-evento.
    """

    __tablename__ = "event_identity_challenges"
    __table_args__ = (
        Index("ix_event_identity_challenge_lookup", "event_id", "identifier_hash"),
        Index("ix_event_identity_challenge_token", "verified_identity_token_hash"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("crm_events.id", ondelete="CASCADE"), nullable=False, index=True)
    identifier_type = Column(String(20), nullable=False)
    identifier_hash = Column(String(128), nullable=False)
    challenge_hash = Column(String(128), nullable=False)
    verified_identity_token_hash = Column(String(128), nullable=True)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    attempt_count = Column(Integer, nullable=False, default=0, server_default="0")
    max_attempts = Column(Integer, nullable=False, default=5, server_default="5")
    verified_at = Column(DateTime(timezone=True), nullable=True)
    consumed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    event = relationship("CrmEvent", foreign_keys=[event_id], back_populates="identity_challenges")
    persona = relationship("Persona", foreign_keys=[persona_id])
