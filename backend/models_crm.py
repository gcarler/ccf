# ruff: noqa: F405
from __future__ import annotations

import enum as _enum
import uuid
import uuid as _uuid
from datetime import date

from sqlalchemy import Enum as SAEnum
from sqlalchemy import func as _func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.hybrid import hybrid_property

from backend.models_shared import *  # noqa: F403
from backend.models_shared import _utcnow


# 3. CRM & CHAT
class Family(Base):
    __tablename__ = "families"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    name = Column(String(100), nullable=False)
    address = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    personas = relationship("Persona", back_populates="family")


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    sender_id = Column(UUID(as_uuid=True), ForeignKey("auth_users.id"), nullable=False, index=True)
    room_id = Column(String(100), nullable=True, index=True)
    content = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)


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
    target_role_id = Column(UUID(as_uuid=True), ForeignKey("role_definitions.id"), nullable=True)
    target_role_ids = Column(JSON, nullable=True)
    target_persona_ids = Column(JSON, nullable=True)
    fixed_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)

    import uuid

    from sqlalchemy.orm import validates

    @validates("target_persona_ids")
    def validate_target_persona_ids(self, key, value):
        if isinstance(value, list):
            return [str(v) if isinstance(v, uuid.UUID) else v for v in value]
        return value

    attendances = relationship("EventAttendance", back_populates="event")
    assignments = relationship("EventAssignment", back_populates="event")


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
    role_at_event = Column(String(30), default="attendee", index=True)
    source = Column(String(30), default="manual", index=True)
    check_in_at = Column(DateTime(timezone=True), nullable=True, index=True)
    check_out_at = Column(DateTime(timezone=True), nullable=True, index=True)
    notes = Column(Text, nullable=True)
    scanned_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    attended = Column(Boolean, default=True)

    event = relationship("CrmEvent", back_populates="attendances")
    persona = relationship("Persona")


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

    positions = relationship("PersonaPosition", back_populates="persona")
    donations = relationship("Donation", foreign_keys="Donation.persona_id", back_populates="persona")
    tasks = relationship("TareaCRM", foreign_keys="TareaCRM.persona_id", back_populates="persona")
    volunteer_shifts = relationship(
        "VolunteerShift", foreign_keys="VolunteerShift.persona_id", back_populates="persona"
    )
    communication_logs = relationship(
        "CommunicationLog", foreign_keys="CommunicationLog.persona_id", back_populates="persona"
    )
    participaciones_grupo = relationship("ParticipanteGrupo", back_populates="persona")
    asistencias = relationship("Asistencia", back_populates="persona")
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


class VolunteerShift(Base):
    __tablename__ = "volunteer_shifts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
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


class CommunicationLog(Base):
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
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    # Nuevos campos para flujos encadenados
    delay_minutes = Column(Integer, default=0, nullable=False)
    ui_graph_state = Column(JSON, nullable=True)


class CrmAutomationFlow(Base):
    __tablename__ = "crm_automation_flows"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class CrmAutomationNode(Base):
    __tablename__ = "crm_automation_nodes"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    flow_id = Column(UUID(as_uuid=True), ForeignKey("crm_automation_flows.id", ondelete="CASCADE"), nullable=False, index=True)
    node_type = Column(String(50), nullable=False)
    ports_config = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class CrmFlowCanvasConfig(Base):
    __tablename__ = "crm_flow_canvas_config"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    flow_id = Column(UUID(as_uuid=True), ForeignKey("crm_automation_flows.id", ondelete="CASCADE"), nullable=False, index=True)
    zoom = Column(Float, default=1.0)
    pan_x = Column(Float, default=0.0)
    pan_y = Column(Float, default=0.0)


class CrmFlowBranch(Base):
    __tablename__ = "crm_flow_branches"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    node_id = Column(UUID(as_uuid=True), ForeignKey("crm_automation_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    conditions_logic = Column(JSON, nullable=True)


class CrmFlowCycleCache(Base):
    __tablename__ = "crm_flow_cycle_cache"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    flow_id = Column(UUID(as_uuid=True), ForeignKey("crm_automation_flows.id", ondelete="CASCADE"), nullable=False, index=True)
    has_cycle = Column(Boolean, default=False)


class CrmAutomationEdge(Base):
    __tablename__ = "crm_automation_edges"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("crm_automations.id", ondelete="CASCADE"), nullable=False, index=True)
    target_id = Column(UUID(as_uuid=True), ForeignKey("crm_automations.id", ondelete="CASCADE"), nullable=False, index=True)
    condition_type = Column(String(50), nullable=True)
    condition_key = Column(String(100), nullable=True)
    condition_value = Column(String(200), nullable=True)
    source_node_id = Column(UUID(as_uuid=True), ForeignKey("crm_automation_nodes.id", ondelete="CASCADE"), nullable=True)
    target_node_id = Column(UUID(as_uuid=True), ForeignKey("crm_automation_nodes.id", ondelete="CASCADE"), nullable=True)
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
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    persona = relationship("Persona", overlaps="persona,personas,ministries,ministry")
    ministry = relationship("Ministry", overlaps="persona,personas,ministries,ministry")


class Fund(Base):
    __tablename__ = "funds"
    fund_id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    name = Column(String(120), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    is_public = Column(Boolean, default=False)
    current_balance = Column(Numeric(14, 2), default=0)
    target_amount = Column(Numeric(14, 2), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


class SupportTicket(Base):
    __tablename__ = "support_tickets"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False, index=True)
    subject = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default="open", index=True)  # open, in_progress, resolved, closed
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

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
