from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, model_validator

from backend.core.context import user_role_context
from backend.schemas._common import orm_config

# Catálogo oficial de tipos de evento CCF
EVENT_TYPES = [
    "PERMANENT",  # Semanal / rutinario (ej: culto dominical)
    "MONTHLY",  # Mensual (ej: ayuno, retiro primer domingo)
    "ANNUAL",  # Anual (ej: Navidad, aniversario de la iglesia)
    "ONCE",  # Única vez / fecha fija especial
    "SPECIAL",  # Campaña, conferencia invitada, evento especial
    "FARO",  # Servicio de Faro en Casa / célula
    "ONLINE",  # Transmisión en vivo / servicio virtual
]




class EventType(str, Enum):
    PERMANENT = "PERMANENT"
    MONTHLY = "MONTHLY"
    ANNUAL = "ANNUAL"
    ONCE = "ONCE"
    SPECIAL = "SPECIAL"
    FARO = "FARO"
    ONLINE = "ONLINE"

class EventAudienceType(str, Enum):
    ALL = "ALL"
    ROLE = "ROLE"
    MANUAL = "MANUAL"

class CrmEventBase(BaseModel):
    name: str
    description: Optional[str] = None
    event_type: EventType = EventType.PERMANENT
    target_audience: EventAudienceType = EventAudienceType.ALL
    target_role_id: Optional[int] = None
    target_role_ids: Optional[list[int]] = None
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
    target_role_ids: Optional[list[int]] = None
    target_persona_ids: Optional[list[str]] = None
    event_date: Optional[datetime] = None
    location: Optional[str] = None
    status: Optional[str] = None
    cancellation_reason: Optional[str] = None

class CrmEvent(CrmEventBase):
    id: int
    created_at: datetime
    model_config = orm_config

class AgendaEventBase(BaseModel):
    title: str
    description: Optional[str] = None
    start_at: datetime
    end_at: Optional[datetime] = None
    location: Optional[str] = None
    is_all_day: bool = True

class AgendaEventCreate(AgendaEventBase):
    pass

class AgendaEvent(AgendaEventBase):
    id: int
    created_by_user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    model_config = orm_config

class EventAttendanceBase(BaseModel):
    event_id: int
    persona_id: str
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
    id: int
    scanned_at: Optional[datetime] = None
    model_config = orm_config

class CounselingTicketBase(BaseModel):
    persona_id: int
    subject: str
    notes: Optional[str] = None
    status: str = "open"

class CounselingTicketCreate(CounselingTicketBase):
    pastor_id: Optional[int] = None

class CounselingTicketUpdate(BaseModel):
    subject: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    priority_level: Optional[str] = None
    sentiment_score: Optional[float] = None
    sentiment_label: Optional[str] = None
    pastor_id: Optional[int] = None

class CounselingTicket(CounselingTicketBase):
    id: int
    pastor_id: Optional[int] = None
    priority_level: Optional[str] = None
    sentiment_score: Optional[float] = None
    sentiment_label: Optional[str] = None
    created_at: datetime
    model_config = orm_config

    @model_validator(mode="after")
    def restrict_counseling_notes(self) -> "CounselingTicket":
        from backend.auth import is_crm_privileged

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
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    is_public: Optional[bool] = None
    answered: Optional[bool] = None

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
    id: int
    created_at: datetime
    model_config = orm_config

class DonationBase(BaseModel):
    persona_id: Optional[str] = None
    amount: float
    donation_type: str = "Diezmo"
    fund_id: Optional[int] = None
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
    id: int
    status: str = "completed"
    reference_code: Optional[str] = None
    payment_method: str = "Transferencia"
    created_at: datetime
    model_config = orm_config

class CrmTaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    persona_id: Optional[str] = None
    assignee_id: int
    due_date: Optional[datetime] = None
    status: str = "todo"
    priority: str = "normal"

class CrmTaskCreate(CrmTaskBase):
    pass

class CrmTaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[datetime] = None

class CrmTask(CrmTaskBase):
    id: int
    created_at: datetime
    model_config = orm_config

class VolunteerShiftBase(BaseModel):
    persona_id: str
    role_name: str
    team_name: str
    shift_start: datetime
    shift_end: datetime
    status: str = "confirmed"
    notes: Optional[str] = None

class VolunteerShiftCreate(VolunteerShiftBase):
    pass

class VolunteerShiftUpdate(BaseModel):
    persona_id: Optional[str] = None
    shift_start: Optional[datetime] = None
    shift_end: Optional[datetime] = None
    location: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None

class VolunteerShift(VolunteerShiftBase):
    id: int
    created_at: datetime
    model_config = orm_config

class ColombianCity(BaseModel):
    id: int
    department_id: int
    name: str
    model_config = orm_config

class ColombianDepartment(BaseModel):
    id: int
    name: str
    code: str
    capital: str
    cities: List[ColombianCity] = []
    model_config = orm_config

class PersonaResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    church_role: Optional[str] = None
    spiritual_status: Optional[str] = "Nuevo"
    created_at: Optional[datetime] = None
    model_config = orm_config

class Persona(BaseModel):
    id: str
    user_id: Optional[int] = None
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    church_role: str = "Miembro"
    spiritual_status: str = "Nuevo"
    family_id: Optional[int] = None
    birthday: Optional[datetime] = None
    gender: Optional[str] = None
    spiritual_health: float = 0.8
    academy_progress: float = 0.0
    talents: Optional[str] = None
    spiritual_gifts: Optional[str] = None
    pastoral_notes: Optional[str] = None
    # Nuevos campos desde hoja de miembros
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
    membership_type: Optional[str] = None
    attendance_type: Optional[str] = None
    group_name: Optional[str] = None
    campus: Optional[str] = None
    church_join_date: Optional[date] = None
    colombian_department_id: Optional[int] = None
    city: Optional[str] = None
    created_at: datetime
    model_config = orm_config

    @model_validator(mode="after")
    def restrict_crm_fields(self) -> "Persona":
        from backend.auth import is_crm_privileged

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
    family_id: Optional[int] = None
    church_role: str = "Miembro"
    talents: Optional[str] = None
    spiritual_gifts: Optional[str] = None
    pastoral_notes: Optional[str] = None
    # Nuevos campos desde hoja de miembros
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
    membership_type: Optional[str] = None
    attendance_type: Optional[str] = None
    group_name: Optional[str] = None
    campus: Optional[str] = None
    church_join_date: Optional[date] = None
    colombian_department_id: Optional[int] = None
    city: Optional[str] = None

class PersonaUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    church_role: Optional[str] = None
    spiritual_status: Optional[str] = None
    family_id: Optional[int] = None
    talents: Optional[str] = None
    spiritual_gifts: Optional[str] = None
    pastoral_notes: Optional[str] = None
    # Nuevos campos desde hoja de miembros
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
    membership_type: Optional[str] = None
    attendance_type: Optional[str] = None
    group_name: Optional[str] = None
    campus: Optional[str] = None
    church_join_date: Optional[date] = None
    colombian_department_id: Optional[int] = None
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
    id: int
    created_at: datetime
    model_config = orm_config

# --- Ministry Membership (Persona <-> Ministerio con Rol) ---

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
    "Visitante Faro en Casa",
    "Visitante Online",
]

class MemberMinistryBase(BaseModel):
    persona_id: str
    ministry_id: int
    role: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: bool = True
    notes: Optional[str] = None

class MemberMinistryCreate(MemberMinistryBase):
    pass

class MemberMinistryUpdate(BaseModel):
    role: Optional[str] = None
    end_date: Optional[datetime] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None

class MemberMinistry(MemberMinistryBase):
    id: int
    model_config = orm_config

class MemberPositionBase(BaseModel):
    persona_id: str
    position_id: int
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: bool = True
    notes: Optional[str] = None

class MemberPositionCreate(MemberPositionBase):
    pass

class MemberPositionUpdate(BaseModel):
    position_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None

class MemberPosition(MemberPositionBase):
    id: int
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
    id: int
    created_at: datetime
    model_config = orm_config

class MemberFormationBase(BaseModel):
    persona_id: str
    formation_level_id: int
    role_in_level: str = "student"
    cohort: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: bool = True
    notes: Optional[str] = None

class MemberFormationCreate(MemberFormationBase):
    pass

class MemberFormationUpdate(BaseModel):
    formation_level_id: Optional[int] = None
    role_in_level: Optional[str] = None
    cohort: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None

class MemberFormation(MemberFormationBase):
    id: int
    model_config = orm_config

class EvangelismStrategyBase(BaseModel):
    name: str
    description: Optional[str] = None
    codigo: Optional[str] = None
    clase_raiz: Optional[str] = None  # ClaseEstrategiaEnum values
    activa: bool = True
    typology: Optional[str] = None  # relacional | evento_masivo | sectorial

    # Relacional
    recurrence: Optional[str] = None  # SEMANAL | QUINCENAL | MENSUAL
    day_of_week: Optional[str] = None
    start_time: Optional[str] = None

    # Evento Masivo
    event_format: Optional[str] = None  # UNICA_LOCACION | MULTILOCACION
    phases: Optional[list[dict]] = None
    phase_count: Optional[int] = None

    # Sectorial
    niche_objective: Optional[str] = None

    strategy_type: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: str = "active"
    group_count: Optional[int] = None

class EvangelismStrategyCreate(EvangelismStrategyBase):
    pass

class EvangelismStrategyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    codigo: Optional[str] = None
    clase_raiz: Optional[str] = None
    activa: Optional[bool] = None
    typology: Optional[str] = None
    recurrence: Optional[str] = None
    day_of_week: Optional[str] = None
    start_time: Optional[str] = None
    event_format: Optional[str] = None
    phases: Optional[list[dict]] = None
    niche_objective: Optional[str] = None
    strategy_type: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[str] = None

class EvangelismStrategy(EvangelismStrategyBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = orm_config

class MemberEvangelismBase(BaseModel):
    persona_id: str
    evangelism_strategy_id: int
    role: str = "assistant"
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: bool = True
    notes: Optional[str] = None

class MemberEvangelismCreate(MemberEvangelismBase):
    pass

class MemberEvangelismUpdate(BaseModel):
    evangelism_strategy_id: Optional[int] = None
    role: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None

class MemberEvangelism(MemberEvangelismBase):
    id: int
    model_config = orm_config

class TeachingAssignmentBase(BaseModel):
    persona_id: str
    formation_level_id: int
    subject: Optional[str] = None
    group_name: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: bool = True
    notes: Optional[str] = None

class TeachingAssignmentCreate(TeachingAssignmentBase):
    pass

class TeachingAssignmentUpdate(BaseModel):
    formation_level_id: Optional[int] = None
    subject: Optional[str] = None
    group_name: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None

class TeachingAssignment(TeachingAssignmentBase):
    id: int
    model_config = orm_config

class ConsolidationCaseBase(BaseModel):
    persona_id: str
    stage: str = "new"
    status: str = "active"
    source: Optional[str] = None
    source_campaign: Optional[str] = None
    last_contact_at: Optional[datetime] = None
    next_contact_at: Optional[datetime] = None
    assigned_pastor_id: Optional[str] = None
    assigned_leader_id: Optional[str] = None
    notes: Optional[str] = None

class ConsolidationCaseCreate(ConsolidationCaseBase):
    pass

class ConsolidationCaseUpdate(BaseModel):
    stage: Optional[str] = None
    status: Optional[str] = None
    source: Optional[str] = None
    source_campaign: Optional[str] = None
    last_contact_at: Optional[datetime] = None
    next_contact_at: Optional[datetime] = None
    assigned_pastor_id: Optional[str] = None
    assigned_leader_id: Optional[str] = None
    notes: Optional[str] = None

class ConsolidationCase(ConsolidationCaseBase):
    id: str
    created_at: datetime
    updated_at: datetime
    model_config = orm_config

class ConsolidationAssignmentBase(BaseModel):
    case_id: str
    assigned_by_id: str
    assigned_to_id: str
    reason: Optional[str] = None
    priority: str = "normal"
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: str = "active"

class ConsolidationAssignmentCreate(ConsolidationAssignmentBase):
    pass

class ConsolidationAssignmentUpdate(BaseModel):
    assigned_by_id: Optional[str] = None
    assigned_to_id: Optional[str] = None
    reason: Optional[str] = None
    priority: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[str] = None

class ConsolidationAssignment(ConsolidationAssignmentBase):
    id: int
    created_at: datetime
    model_config = orm_config

class ConsolidationInteractionBase(BaseModel):
    case_id: str
    performed_by_id: str
    interaction_type: str
    interaction_date: Optional[datetime] = None
    result: Optional[str] = None
    notes: Optional[str] = None
    next_action_date: Optional[datetime] = None

class ConsolidationInteractionCreate(ConsolidationInteractionBase):
    pass

class ConsolidationInteractionUpdate(BaseModel):
    interaction_type: Optional[str] = None
    interaction_date: Optional[datetime] = None
    result: Optional[str] = None
    notes: Optional[str] = None
    next_action_date: Optional[datetime] = None

class ConsolidationInteraction(ConsolidationInteractionBase):
    id: int
    created_at: datetime
    model_config = orm_config

class ConsolidationTaskBase(BaseModel):
    case_id: str
    assignment_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    status: str = "pending"
    completed_at: Optional[datetime] = None

class ConsolidationTaskCreate(ConsolidationTaskBase):
    pass

class ConsolidationTaskUpdate(BaseModel):
    assignment_id: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    status: Optional[str] = None
    completed_at: Optional[datetime] = None

class ConsolidationTask(ConsolidationTaskBase):
    id: int
    created_at: datetime
    model_config = orm_config

class Family(BaseModel):
    id: int
    name: str
    address: Optional[str] = None
    members_count: int = 0
    created_at: datetime
    model_config = orm_config

class CellGroupMember(BaseModel):
    id: int
    cell_group_id: int
    persona_id: str
    role: str
    model_config = orm_config

class CellGroup(BaseModel):
    id: int
    code: Optional[str] = None
    name: str
    zone: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    leader_name: Optional[str] = None
    leader_id: Optional[str] = None
    assistant_id: Optional[str] = None
    host_id: Optional[str] = None
    evangelism_strategy_id: int
    members_count: int
    capacity: int
    status: str
    day_of_week: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    created_at: datetime
    model_config = orm_config

class CellGroupCreate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    zone: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    leader_name: Optional[str] = None
    evangelism_strategy_id: Optional[int] = None
    leader_id: Optional[str] = None
    assistant_id: Optional[str] = None
    host_id: Optional[str] = None
    capacity: int = 15
    status: Optional[str] = "Activo"
    day_of_week: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    base_attendee_ids: Optional[List[str]] = None

class CellGroupMemberWithRole(BaseModel):
    persona_id: str
    role: str = "miembro"  # lider | colider | miembro | visitante

class CellGroupUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    zone: Optional[str] = None
    address: Optional[str] = None
    leader_id: Optional[str] = None
    assistant_id: Optional[str] = None
    host_id: Optional[str] = None
    capacity: Optional[int] = None
    status: Optional[str] = None
    day_of_week: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    base_attendee_ids: Optional[List[str]] = None
    base_attendees_with_roles: Optional[List[CellGroupMemberWithRole]] = None

class FaroAttendanceReportItem(BaseModel):
    persona_id: str
    attended: bool = True
    absence_reason: Optional[str] = None
    absence_reason_detail: Optional[str] = None
    estado: Optional[str] = None  # EstadoAsistenciaEnum
    es_primera_vez: bool = False

class FaroSessionReportUpdate(BaseModel):
    session_date: Optional[date] = None
    status: Optional[str] = None
    topic: Optional[str] = None
    offering_amount: Optional[float] = None
    report_notes: Optional[str] = None
    novelty_type: Optional[str] = None
    novelty_detail: Optional[str] = None
    cancellation_reason: Optional[str] = None
    reported_by_persona_id: Optional[str] = None
    attendees: Optional[List[FaroAttendanceReportItem]] = None

class FaroSessionAttendanceItem(BaseModel):
    persona_id: str
    name: str
    role: Optional[str] = None
    attended: bool = True
    absence_reason: Optional[str] = None
    absence_reason_detail: Optional[str] = None
    scanned_at: Optional[datetime] = None
    estado: Optional[str] = None  # EstadoAsistenciaEnum
    es_primera_vez: bool = False

class FaroSessionAttendance(BaseModel):
    session_id: int
    session_date: date
    cell_group_id: int
    status: str
    topic: Optional[str] = None
    offering_amount: Optional[float] = None
    report_notes: Optional[str] = None
    novelty_type: Optional[str] = None
    novelty_detail: Optional[str] = None
    cancellation_reason: Optional[str] = None
    reported_by_persona_id: Optional[str] = None
    total: int
    attendees: List[FaroSessionAttendanceItem] = []
    absentees: List[FaroSessionAttendanceItem] = []
    expected_members: List[FaroSessionAttendanceItem] = []
    model_config = orm_config

class PastoralCallLogCreate(BaseModel):
    case_id: str
    persona_id: Optional[str] = None
    pastor_id: int
    outcome: str
    duration_seconds: int = 0

class PastoralCallLog(BaseModel):
    id: int
    case_id: Optional[str] = None
    persona_id: Optional[str] = None
    pastor_id: int
    outcome: str
    notes: Optional[str] = None
    duration_seconds: int = 0
    created_at: datetime
    model_config = orm_config

# ── Faro Sessions & Attendance ──

class CellGroupSessionBase(BaseModel):
    cell_group_id: int
    season_id: Optional[int] = None
    session_date: datetime
    topic: Optional[str] = None
    offering_amount: Optional[float] = None
    report_notes: Optional[str] = None
    novelty_type: Optional[str] = None
    novelty_detail: Optional[str] = None
    cancellation_reason: Optional[str] = None
    reported_by_persona_id: Optional[str] = None
    status: str = "Realizada"

class CellGroupSessionCreate(CellGroupSessionBase):
    pass

class CellGroupSession(CellGroupSessionBase):
    id: int
    reported_at: Optional[datetime] = None
    created_at: datetime
    model_config = orm_config

class CellGroupSessionUpdate(BaseModel):
    session_date: Optional[datetime] = None
    topic: Optional[str] = None
    offering_amount: Optional[float] = None
    report_notes: Optional[str] = None
    novelty_type: Optional[str] = None
    novelty_detail: Optional[str] = None
    cancellation_reason: Optional[str] = None
    reported_by_persona_id: Optional[str] = None
    status: Optional[str] = None

class CellGroupAttendanceBase(BaseModel):
    session_id: int
    persona_id: str
    status: str = "present"  # present | absent | first_time
    notes: Optional[str] = None

class CellGroupAttendanceCreate(CellGroupAttendanceBase):
    pass

class CellGroupAttendance(CellGroupAttendanceBase):
    id: int
    model_config = orm_config
