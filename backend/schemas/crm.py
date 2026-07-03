from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.core.context import user_role_context
from backend.schemas._common import orm_config

# Catálogo oficial de tipos de evento CCF
EVENT_TYPES = [
    "PERMANENT",  # Semanal / rutinario (ej: culto dominical)
    "MONTHLY",  # Mensual (ej: ayuno, retiro primer domingo)
    "ANNUAL",  # Anual (ej: Navidad, aniversario de la iglesia)
    "ONCE",  # Única vez / fecha fija especial
    "SPECIAL",  # Campaña, conferencia invitada, evento especial
    "ONLINE",  # Transmisión en vivo / servicio virtual
    "CULTURE",  # Culto/cultura cristiana regular (alias semántico de PERMANENT)
    "CONFERENCE",  # Conferencia invitada (alias semántico de SPECIAL)
]


class EventType(str, Enum):
    PERMANENT = "PERMANENT"
    MONTHLY = "MONTHLY"
    ANNUAL = "ANNUAL"
    ONCE = "ONCE"
    SPECIAL = "SPECIAL"
    GROUPS = "GROUPS"
    ONLINE = "ONLINE"
    CULTURE = "CULTURE"
    CONFERENCE = "CONFERENCE"

class EventAudienceType(str, Enum):
    ALL = "ALL"
    ROLE = "ROLE"
    MANUAL = "MANUAL"


class CrmTaskStatus(str, Enum):
    """Estado del Ciclo de Vida de una Tarea CRM (Axioma 1).

    Catálogo cerrado y case-sensitive (Pydantic valida en la frontera).
    Valores mapean 1:1 a la columna `TareaCRM.estado` (String(20)) del modelo.

    Default: ``pending`` (alineado con ``server_default='pending'`` del DB).
    Callers que envíen valores fuera del catálogo o case-insensitive
    (e.g., ``"COMPLETED"``, ``"In Progress"``) reciben 422 estructurado.
    """

    todo = "todo"
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class CrmTaskPriority(str, Enum):
    """Prioridad de una Tarea CRM (alineado con el default ``medium`` del DB).

    Catálogo cerrado y case-sensitive. NO se aceptan alias anterior como
    ``"normal"`` o ``"alta"``; los callers deben normalizar ANTES de enviar.

    Default: ``medium`` (alineado con ``server_default='medium'`` del DB).
    """

    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"

class CrmEventBase(BaseModel):
    name: str
    description: Optional[str] = None
    event_type: EventType = EventType.PERMANENT
    target_audience: EventAudienceType = EventAudienceType.ALL
    target_role_id: Optional[UUID] = None
    target_role_ids: Optional[list[UUID]] = None
    target_persona_ids: Optional[list[str]] = None
    event_date: Optional[datetime] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    day_of_week: Optional[int] = None
    month_day: Optional[str] = None
    fixed_date: Optional[datetime] = None
    location: Optional[str] = None
    status: str = "SCHEDULED"
    cancellation_reason: Optional[str] = None

class CrmEventCreate(CrmEventBase):
    pass

class CrmEventUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    event_type: Optional[EventType] = None
    target_audience: Optional[EventAudienceType] = None
    target_role_ids: Optional[list[UUID]] = None
    target_persona_ids: Optional[list[str]] = None
    event_date: Optional[datetime] = None
    location: Optional[str] = None
    status: Optional[str] = None
    cancellation_reason: Optional[str] = None

class CrmEvent(CrmEventBase):
    id: UUID
    created_at: datetime
    model_config = orm_config

class EventAttendanceBase(BaseModel):
    event_id: UUID
    persona_id: UUID
    session_date: date = Field(default_factory=date.today)
    attended: bool = True
    status: str = "present"
    role_at_event: str = "attendee"
    source: str = "manual"
    check_in_at: Optional[datetime] = None
    check_out_at: Optional[datetime] = None
    notes: Optional[str] = None
    scanned_at: Optional[datetime] = None

class EventAttendanceCreate(EventAttendanceBase):
    pass

class EventAttendance(EventAttendanceBase):
    id: UUID
    scanned_at: Optional[datetime] = None
    model_config = orm_config

class CounselingTicketBase(BaseModel):
    persona_id: UUID
    subject: str
    notes: Optional[str] = None
    status: str = "open"

class CounselingTicketCreate(CounselingTicketBase):
    pastor_id: Optional[UUID] = None

class CounselingTicketUpdate(BaseModel):
    subject: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    priority_level: Optional[str] = None
    sentiment_score: Optional[float] = None
    sentiment_label: Optional[str] = None
    pastor_id: Optional[UUID] = None

class CounselingTicket(CounselingTicketBase):
    id: UUID
    pastor_id: Optional[UUID] = None
    priority_level: Optional[str] = None
    sentiment_score: Optional[float] = None
    sentiment_label: Optional[str] = None
    created_at: datetime
    model_config = orm_config

    @model_validator(mode="after")
    def restrict_counseling_notes(self) -> "CounselingTicket":
        from backend.core.permissions import is_crm_privileged

        role = user_role_context.get()
        if role and not is_crm_privileged(role):
            self.notes = "[RESTRINGIDO - SOLO PASTORES/ADMIN]"
        return self

class PrayerRequestBase(BaseModel):
    requester_name: str
    request_text: str
    category: str = "General"
    is_public: bool = False
    source: str = "crm"
    status: str = "pending"

class PrayerRequestCreate(PrayerRequestBase):
    pass

class PrayerRequestUpdate(BaseModel):
    request_text: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    is_public: Optional[bool] = None
    source: Optional[str] = None

class PrayerRequestPublicCreate(BaseModel):
    """Schema for public web prayer requests — minimal fields, no auth."""

    requester_name: str
    request_text: str
    category: str = "General"
    email: Optional[str] = None
    phone: Optional[str] = None
    landing_page: Optional[str] = None
    campaign: Optional[str] = None

class PrayerRequest(PrayerRequestBase):
    id: UUID
    created_at: datetime
    model_config = orm_config

class DonationBase(BaseModel):
    persona_id: Optional[UUID] = None
    amount: float
    donation_type: str = "Diezmo"
    fund_id: Optional[UUID] = None
    donor_name: Optional[str] = None

class DonationCreate(DonationBase):
    pass

class DonationUpdate(BaseModel):
    amount: Optional[float] = None
    donation_type: Optional[str] = None
    fund_name: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    anonymous: Optional[bool] = None
    method: Optional[str] = None

class Donation(DonationBase):
    id: UUID
    status: str = "completed"
    reference_code: Optional[str] = None
    payment_method: str = "Transferencia"
    created_at: datetime
    model_config = orm_config

class CrmTaskBase(BaseModel):
    """Schema base para tareas CRM (uso persistencia + auditoría, Axioma 1).

    `status` y `priority` son Pydantic ``str, Enum`` (case-sensitive) con
    valores explícitos del catálogo (`CrmTaskStatus` / `CrmTaskPriority`).
    `use_enum_values=True` garantiza que ``model_dump()`` y la serialización
    JSON retornen strings planos (alineados con la columna
    ``TareaCRM.estado``/``prioridad`` ``String(20)`` y JSONB-safe para la
    tabla ``logs_auditoria``).

    Defaults alineados con los ``server_default`` de las columnas:
      * ``status = CrmTaskStatus.pending`` (DB default: ``'pending'``).
      * ``priority = CrmTaskPriority.medium`` (DB default: ``'medium'``).
    Antes (pre-Enums) el schema tenía ``status="todo"`` y ``priority="normal"``,
    que NO están en el catálogo y NO coinciden con los DB defaults. El
    cleanup alinea schema ↔ DB (single source of truth: enum value ==
    DB-stored string == OpenAPI serialized value).
    """

    model_config = ConfigDict(use_enum_values=True)

    title: str
    description: Optional[str] = None
    persona_id: Optional[UUID] = None
    assignee_id: Optional[UUID] = None
    due_date: Optional[datetime] = None
    status: CrmTaskStatus = CrmTaskStatus.pending
    priority: CrmTaskPriority = CrmTaskPriority.medium
    completed_at: Optional[datetime] = None  # synonym en TareaCRM para fecha_completada

class CrmTaskCreate(CrmTaskBase):
    pass

class CrmTaskUpdate(BaseModel):
    """Schema para PATCH `/tasks/{id}`.

    `status` y `priority` son `Optional[CrmTaskStatus]` / `Optional[CrmTaskPriority]`
    (case-sensitive). Migración desde ``Optional[str]`` con whitelist inline
    en el endpoint — ahora la validación es declarativa en el schema y
    cualquier caller fuera del catálogo recibe 422 estruturado en la
    frontera.

    `use_enum_values=True` garantiza ``model_dump()`` retorna strings planos,
    alineados con la columna String(20) del modelo y JSONB-safe para el
    audit log.
    """

    model_config = ConfigDict(use_enum_values=True)

    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[CrmTaskStatus] = None
    priority: Optional[CrmTaskPriority] = None
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None  # side-effect: se estampa/limpia según status
    # FK fields (Axioma 3 Multi-Tenant):
    #   * persona_id: target persona de la tarea. Cambio cross-sede debe
    #     ser rechazado por el scope re-check del CRUD.
    #   * assignee_id: UUID canónico de la persona responsable. La
    #     validación de scope ocurre en el endpoint API antes del CRUD.
    #   * caso_id: vincula/desvincula la tarea a un CasoCRM. Cambio
    #     cross-sede debe ser rechazado.
    # Estos campos eran ignorados silenciosamente por `extra='ignore'`
    # default de Pydantic v2; ahora el schema los expone explícitamente
    # para alinear el contrato Pydantic con el contrato real del
    # endpoint API (que lee el body como dict JSON crudo).
    persona_id: Optional[UUID] = None
    assignee_id: Optional[UUID] = None
    caso_id: Optional[UUID] = None

class CrmTask(CrmTaskBase):
    id: UUID
    created_at: datetime
    model_config = orm_config

class VolunteerShiftBase(BaseModel):
    persona_id: UUID
    role_name: str
    team_name: str
    shift_start: datetime
    shift_end: datetime
    status: str = "confirmed"
    notes: Optional[str] = None

class VolunteerShiftCreate(VolunteerShiftBase):
    pass

class VolunteerShiftUpdate(BaseModel):
    persona_id: Optional[UUID] = None
    shift_start: Optional[datetime] = None
    shift_end: Optional[datetime] = None
    location: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None

class VolunteerShift(VolunteerShiftBase):
    id: UUID
    created_at: datetime
    model_config = orm_config

class ColombianCity(BaseModel):
    id: UUID
    department_id: UUID
    name: str
    model_config = orm_config

class ColombianDepartment(BaseModel):
    id: UUID
    name: str
    code: str
    capital: str
    cities: List[ColombianCity] = []
    model_config = orm_config

class PersonaResponse(BaseModel):
    model_config = orm_config

    @field_validator("id", mode="before")
    @classmethod
    def coerce_id(cls, v):
        return str(v) if v is not None else v

    id: UUID
    first_name: str
    last_name: str
    nombre_completo: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    church_role: Optional[str] = None
    spiritual_status: Optional[str] = "Nuevo"
    estado_vital: Optional[str] = None
    is_baptized: Optional[bool] = None
    baptism_date: Optional[date] = None
    birthday: Optional[date] = None
    created_at: Optional[datetime] = None
    family_id: Optional[UUID] = None
    talents: Optional[str] = None
    spiritual_gifts: Optional[str] = None
    pastoral_notes: Optional[str] = None
    id_type: Optional[str] = None
    id_number: Optional[str] = None
    second_name: Optional[str] = None
    second_last_name: Optional[str] = None
    marital_status: Optional[str] = None
    birth_country: Optional[str] = None
    landline_phone: Optional[str] = None
    other_phone: Optional[str] = None
    mobile_phone: Optional[str] = None
    address: Optional[str] = None
    housing_type: Optional[str] = None
    education_level: Optional[str] = None
    education_status: Optional[str] = None
    profession: Optional[str] = None
    economic_sector: Optional[str] = None
    blood_type: Optional[str] = None
    medical_notes: Optional[str] = None
    optional_info: Optional[str] = None
    registration_reason: Optional[str] = None
    unregistration_reason: Optional[str] = None
    registration_date: Optional[date] = None
    unregistration_date: Optional[date] = None
    responsible_adult_name: Optional[str] = None
    responsible_adult_contact: Optional[str] = None
    guardian_name: Optional[str] = None
    guardian_contact: Optional[str] = None
    sex: Optional[str] = None
    last_group_attendance: Optional[date] = None
    last_meeting_attendance: Optional[date] = None
    participation_type: Optional[str] = None
    attendance_type: Optional[str] = None
    group_name: Optional[str] = None
    campus: Optional[str] = None
    church_join_date: Optional[date] = None
    colombian_department_id: Optional[UUID] = None
    city: Optional[str] = None

class Persona(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    church_role: str = "Miembro"
    spiritual_status: str = "Nuevo"
    family_id: Optional[UUID] = None
    birthday: Optional[datetime] = None
    gender: Optional[str] = None
    spiritual_health: float = 0.8
    academy_progress: float = 0.0
    talents: Optional[str] = None
    spiritual_gifts: Optional[str] = None
    pastoral_notes: Optional[str] = None
    # Nuevos campos desde hoja de personas
    id_type: Optional[str] = None
    id_number: Optional[str] = None
    second_name: Optional[str] = None
    second_last_name: Optional[str] = None
    marital_status: Optional[str] = None
    birth_country: Optional[str] = None
    landline_phone: Optional[str] = None
    other_phone: Optional[str] = None
    mobile_phone: Optional[str] = None
    address: Optional[str] = None
    housing_type: Optional[str] = None
    education_level: Optional[str] = None
    education_status: Optional[str] = None
    profession: Optional[str] = None
    economic_sector: Optional[str] = None
    blood_type: Optional[str] = None
    medical_notes: Optional[str] = None
    optional_info: Optional[str] = None
    registration_reason: Optional[str] = None
    unregistration_reason: Optional[str] = None
    registration_date: Optional[date] = None
    unregistration_date: Optional[date] = None
    responsible_adult_name: Optional[str] = None
    responsible_adult_contact: Optional[str] = None
    guardian_name: Optional[str] = None
    guardian_contact: Optional[str] = None
    sex: Optional[str] = None
    last_group_attendance: Optional[date] = None
    last_meeting_attendance: Optional[date] = None
    participation_type: Optional[str] = None
    attendance_type: Optional[str] = None
    group_name: Optional[str] = None
    campus: Optional[str] = None
    church_join_date: Optional[date] = None
    colombian_department_id: Optional[UUID] = None
    city: Optional[str] = None
    created_at: datetime
    model_config = orm_config

    @model_validator(mode="after")
    def restrict_crm_fields(self) -> "Persona":
        from backend.core.permissions import is_crm_privileged

        role = user_role_context.get()
        if role and not is_crm_privileged(role):
            self.pastoral_notes = "[RESTRINGIDO]"
            self.spiritual_health = 0.0
            self.talents = "[RESTRINGIDO]"
            self.spiritual_gifts = "[RESTRINGIDO]"
        return self

class PersonaCreate(BaseModel):
    first_name: str = Field(..., min_length=2, max_length=100)
    last_name: str = Field(..., min_length=2, max_length=100)
    email: Optional[str] = None
    phone: Optional[str] = None
    family_id: Optional[UUID] = None
    church_role: str = "Miembro"
    spiritual_status: Optional[str] = None
    estado_vital: Optional[str] = None
    is_baptized: Optional[bool] = None
    baptism_date: Optional[date] = None
    birthday: Optional[date] = None
    talents: Optional[str] = None
    spiritual_gifts: Optional[str] = None
    pastoral_notes: Optional[str] = None
    # Nuevos campos desde hoja de personas
    id_type: Optional[str] = None
    id_number: Optional[str] = None
    second_name: Optional[str] = None
    second_last_name: Optional[str] = None
    marital_status: Optional[str] = None
    birth_country: Optional[str] = None
    landline_phone: Optional[str] = None
    other_phone: Optional[str] = None
    mobile_phone: Optional[str] = None
    address: Optional[str] = None
    housing_type: Optional[str] = None
    education_level: Optional[str] = None
    education_status: Optional[str] = None
    profession: Optional[str] = None
    economic_sector: Optional[str] = None
    blood_type: Optional[str] = None
    medical_notes: Optional[str] = None
    optional_info: Optional[str] = None
    registration_reason: Optional[str] = None
    unregistration_reason: Optional[str] = None
    registration_date: Optional[date] = None
    unregistration_date: Optional[date] = None
    responsible_adult_name: Optional[str] = None
    responsible_adult_contact: Optional[str] = None
    guardian_name: Optional[str] = None
    guardian_contact: Optional[str] = None
    sex: Optional[str] = None
    last_group_attendance: Optional[date] = None
    last_meeting_attendance: Optional[date] = None
    participation_type: Optional[str] = None
    attendance_type: Optional[str] = None
    group_name: Optional[str] = None
    campus: Optional[str] = None
    church_join_date: Optional[date] = None
    colombian_department_id: Optional[UUID] = None
    city: Optional[str] = None

class PersonaUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    church_role: Optional[str] = None
    spiritual_status: Optional[str] = None
    estado_vital: Optional[str] = None
    is_baptized: Optional[bool] = None
    baptism_date: Optional[date] = None
    birthday: Optional[date] = None
    family_id: Optional[UUID] = None
    talents: Optional[str] = None
    spiritual_gifts: Optional[str] = None
    pastoral_notes: Optional[str] = None
    # Nuevos campos desde hoja de personas
    id_type: Optional[str] = None
    id_number: Optional[str] = None
    second_name: Optional[str] = None
    second_last_name: Optional[str] = None
    marital_status: Optional[str] = None
    birth_country: Optional[str] = None
    landline_phone: Optional[str] = None
    other_phone: Optional[str] = None
    mobile_phone: Optional[str] = None
    address: Optional[str] = None
    housing_type: Optional[str] = None
    education_level: Optional[str] = None
    education_status: Optional[str] = None
    profession: Optional[str] = None
    economic_sector: Optional[str] = None
    blood_type: Optional[str] = None
    medical_notes: Optional[str] = None
    optional_info: Optional[str] = None
    registration_reason: Optional[str] = None
    unregistration_reason: Optional[str] = None
    registration_date: Optional[date] = None
    unregistration_date: Optional[date] = None
    responsible_adult_name: Optional[str] = None
    responsible_adult_contact: Optional[str] = None
    guardian_name: Optional[str] = None
    guardian_contact: Optional[str] = None
    sex: Optional[str] = None
    last_group_attendance: Optional[date] = None
    last_meeting_attendance: Optional[date] = None
    participation_type: Optional[str] = None
    attendance_type: Optional[str] = None
    group_name: Optional[str] = None
    campus: Optional[str] = None
    church_join_date: Optional[date] = None
    colombian_department_id: Optional[UUID] = None
    city: Optional[str] = None


class PersonaSelfProfileUpdate(BaseModel):
    """Campos permitidos para que la persona edite su propio perfil."""

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    second_name: Optional[str] = None
    second_last_name: Optional[str] = None
    phone: Optional[str] = None
    mobile_phone: Optional[str] = None
    landline_phone: Optional[str] = None
    address: Optional[str] = None
    birthday: Optional[date] = None
    city: Optional[str] = None

# ── PERSONA (reemplaza Persona — UUID PK) ────────────────────

class PositionBase(BaseModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    is_active: bool = True

class PositionCreate(PositionBase):
    pass

class PositionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None

class Position(PositionBase):
    id: UUID
    created_at: datetime
    model_config = orm_config


# --- Ministry Participation (Persona <-> Ministerio con Rol) ---

MINISTRY_ROLES = [
    "Apóstol",
    "Profeta",
    "Evangelista",
    "Pastor",
    "Maestro",
    "Ministro de Culto",
    "Líder",
    "Servidor",
    "Miembro Bautizado",
    "Asistente",
    "Visitante Servicios",
    "Visitante de Grupo",
    "Visitante Online",
]

class PersonaMinistryAssignmentBase(BaseModel):
    persona_id: UUID
    ministry_id: UUID
    role: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: bool = True
    notes: Optional[str] = None

class PersonaMinistryAssignmentCreate(PersonaMinistryAssignmentBase):
    pass

class PersonaMinistryAssignmentUpdate(BaseModel):
    role: Optional[str] = None
    end_date: Optional[datetime] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None

class PersonaMinistryAssignment(PersonaMinistryAssignmentBase):
    id: UUID
    model_config = orm_config

class PersonaPositionBase(BaseModel):
    persona_id: UUID
    position_id: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: bool = True
    notes: Optional[str] = None

class PersonaPositionCreate(PersonaPositionBase):
    pass

class PersonaPositionUpdate(BaseModel):
    position_id: Optional[UUID] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None

class PersonaPosition(PersonaPositionBase):
    id: UUID
    model_config = orm_config

class FormationLevelBase(BaseModel):
    name: str
    order_index: int = 0
    description: Optional[str] = None
    is_active: bool = True

class FormationLevelCreate(FormationLevelBase):
    pass

class FormationLevelUpdate(BaseModel):
    name: Optional[str] = None
    order_index: Optional[int] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class FormationLevel(FormationLevelBase):
    id: UUID
    created_at: datetime
    model_config = orm_config

class PersonaFormationBase(BaseModel):
    persona_id: UUID
    formation_level_id: str
    role_in_level: str = "student"
    cohort: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: bool = True
    notes: Optional[str] = None

class PersonaFormationCreate(PersonaFormationBase):
    pass

class PersonaFormationUpdate(BaseModel):
    formation_level_id: Optional[UUID] = None
    role_in_level: Optional[str] = None
    cohort: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None

class PersonaFormation(PersonaFormationBase):
    id: UUID
    model_config = orm_config


# ── EvangelismStrategy schemas re-exported from canonical schemas/evangelism.py ──
from backend.schemas.evangelism import (  # noqa: E402, F401
    EstrategiaEvangelismoCreate as EvangelismStrategyCreate,
)

# Response schema: id as str (UUID)
from backend.schemas.evangelism import (
    EstrategiaEvangelismoResponse as _EstrategiaEvangelismoResponse,  # noqa: E402, F401
)
from backend.schemas.evangelism import (
    EstrategiaEvangelismoUpdate as EvangelismStrategyUpdate,
)


class EvangelismStrategyBase(BaseModel):
    """Schema used by api/evangelism.py.

    All fields are inherited from EstrategiaEvangelismoBase.
    The id type changes from int to str (UUID).
    """
    name: str
    description: Optional[str] = None
    codigo: Optional[str] = None
    clase_raiz: Optional[str] = None
    activa: bool = True
    typology: Optional[str] = None
    recurrence: Optional[str] = None
    day_of_week: Optional[str] = None
    start_time: Optional[str] = None
    event_format: Optional[str] = None
    phases: Optional[list[dict]] = None
    phase_count: Optional[int] = None
    niche_objective: Optional[str] = None
    strategy_type: Optional[str] = None
    default_role_id: Optional[UUID] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: str = "active"
    group_count: Optional[int] = None

class EvangelismStrategy(EvangelismStrategyBase):
    """Respuesta canónica de una estrategia de evangelismo."""
    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    fecha_creacion: Optional[datetime] = None
    model_config = orm_config

class PersonaEvangelismBase(BaseModel):
    persona_id: UUID
    evangelism_strategy_id: UUID
    role: str = "assistant"
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: bool = True
    notes: Optional[str] = None

class PersonaEvangelismCreate(PersonaEvangelismBase):
    pass

class PersonaEvangelismUpdate(BaseModel):
    evangelism_strategy_id: Optional[UUID] = None  # UUID string
    role: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None

class PersonaEvangelism(PersonaEvangelismBase):
    id: UUID
    model_config = orm_config

class TeachingAssignmentBase(BaseModel):
    persona_id: UUID
    formation_level_id: str
    subject: Optional[str] = None
    group_name: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: bool = True
    notes: Optional[str] = None

class TeachingAssignmentCreate(TeachingAssignmentBase):
    pass

class TeachingAssignmentUpdate(BaseModel):
    formation_level_id: Optional[UUID] = None
    subject: Optional[str] = None
    group_name: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None

class TeachingAssignment(TeachingAssignmentBase):
    id: UUID
    model_config = orm_config

class CaseUpdate(BaseModel):
    stage: Optional[str] = None
    status: Optional[str] = None
    source: Optional[str] = None
    source_campaign: Optional[str] = None
    last_contact_at: Optional[datetime] = None
    next_contact_at: Optional[datetime] = None
    assigned_pastor_id: Optional[str] = None
    assigned_leader_id: Optional[str] = None
    notes: Optional[str] = None

class CaseInteractionCreate(BaseModel):
    interaction_type: str
    interaction_date: Optional[datetime] = None
    result: Optional[str] = None
    notes: Optional[str] = None
    next_action_date: Optional[datetime] = None

class CaseTaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    status: str = "pending"
    completed_at: Optional[datetime] = None

class CaseTaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    status: Optional[str] = None
    completed_at: Optional[datetime] = None

class Family(BaseModel):
    id: UUID
    name: str
    address: Optional[str] = None
    personas_count: int = 0
    created_at: datetime
    model_config = orm_config

class GroupAttendanceReportItem(BaseModel):
    persona_id: UUID
    attended: bool = True
    absence_reason: Optional[str] = None
    absence_reason_detail: Optional[str] = None
    estado: Optional[str] = None  # EstadoAsistenciaEnum
    es_primera_vez: bool = False

class GroupSessionReportUpdate(BaseModel):
    session_date: Optional[date] = None
    status: Optional[str] = None
    topic: Optional[str] = None
    offering_amount: Optional[float] = None
    report_notes: Optional[str] = None
    novelty_type: Optional[str] = None
    novelty_detail: Optional[str] = None
    cancellation_reason: Optional[str] = None
    reported_by_persona_id: Optional[str] = None
    attendees: Optional[List[GroupAttendanceReportItem]] = None

class GroupSessionAttendanceItem(BaseModel):
    persona_id: UUID
    name: str
    role: Optional[str] = None
    attended: bool = True
    absence_reason: Optional[str] = None
    absence_reason_detail: Optional[str] = None
    scanned_at: Optional[datetime] = None
    estado: Optional[str] = None  # EstadoAsistenciaEnum
    es_primera_vez: bool = False

class GroupSessionAttendance(BaseModel):
    session_id: UUID
    session_date: date
    grupo_id: str
    status: str
    topic: Optional[str] = None
    offering_amount: Optional[float] = None
    report_notes: Optional[str] = None
    novelty_type: Optional[str] = None
    novelty_detail: Optional[str] = None
    cancellation_reason: Optional[str] = None
    reported_by_persona_id: Optional[str] = None
    total: int
    attendees: List[GroupSessionAttendanceItem] = []
    absentees: List[GroupSessionAttendanceItem] = []
    expected_participantes: List[GroupSessionAttendanceItem] = []
    model_config = orm_config

class CaseCallCreate(BaseModel):
    persona_id: Optional[UUID] = None
    outcome: str
    notes: Optional[str] = None
    prayer_requests: Optional[str] = None
    duration_seconds: int = 0

class CaseCall(BaseModel):
    id: UUID
    case_id: Optional[str] = None
    persona_id: Optional[UUID] = None
    pastor_id: UUID
    outcome: str
    notes: Optional[str] = None
    prayer_requests: Optional[str] = None
    duration_seconds: int = 0
    created_at: datetime
    model_config = orm_config
