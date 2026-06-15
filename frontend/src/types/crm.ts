// ── CRM - Tipos compartidos ──────────────────────────────────────────────

// ── Personas ──────────────────────────────────────────────────────────────
export interface Department {
  id: number;
  name: string;
  code: string;
}

export interface City {
  id: number;
  department_id: number;
  name: string;
}

export interface MemberFormData {
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  church_role: string;
  second_name: string;
  second_last_name: string;
  id_type: string;
  id_number: string;
  birth_country: string;
  sex: string;
  marital_status: string;
  birthday: string;
  landline_phone: string;
  other_phone: string;
  mobile_phone: string;
  address: string;
  housing_type: string;
  colombian_department_id: number | null;
  city: string;
  education_level: string;
  education_status: string;
  profession: string;
  economic_sector: string;
  blood_type: string;
  medical_notes: string;
  membership_type: string;
  attendance_type: string;
  group_name: string;
  campus: string;
  church_join_date: string;
  baptism_date: string;
  responsible_adult_name: string;
  responsible_adult_contact: string;
  guardian_name: string;
  guardian_contact: string;
  talents: string;
  spiritual_gifts: string;
  pastoral_notes: string;
  registration_reason: string;
  unregistration_reason: string;
  registration_date: string;
  unregistration_date: string;
  optional_info: string;
  last_group_attendance: string;
  last_meeting_attendance: string;
}

export const ID_TYPES = ['Cédula de Ciudadanía', 'Cédula de Extranjería', 'Pasaporte', 'Tarjeta de Identidad', 'NIT', 'Otro'];
export const MARITAL_STATUSES = ['Soltero(a)', 'Casado(a)', 'Unión Libre', 'Divorciado(a)', 'Viudo(a)', 'Separado(a)'];
export const SEX_OPTIONS = ['Masculino', 'Femenino'];
export const EDUCATION_LEVELS = ['Primaria', 'Secundaria', 'Técnico', 'Tecnólogo', 'Universitario', 'Postgrado', 'Maestría', 'Doctorado'];
export const EDUCATION_STATUSES = ['Cursando', 'Completado', 'Incompleto'];
export const BLOOD_TYPES = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'];
export const HOUSING_TYPES = ['Propia', 'Arriendo', 'Familiar', 'Otro'];
export const MEMBERSHIP_TYPES = ['Activo', 'Inactivo', 'Transferido', 'Fallecido'];
export const ATTENDANCE_TYPES = ['Regular', 'Constante', 'Irregular', 'Ausente'];

export const INITIAL_MEMBER: MemberFormData = {
  first_name: '', last_name: '', email: '', phone: '', church_role: 'Persona',
  second_name: '', second_last_name: '', id_type: '', id_number: '',
  birth_country: '', sex: '', marital_status: '', birthday: '',
  landline_phone: '', other_phone: '', mobile_phone: '', address: '', housing_type: '',
  colombian_department_id: null, city: '',
  education_level: '', education_status: '', profession: '', economic_sector: '',
  blood_type: '', medical_notes: '', membership_type: '', attendance_type: '',
  group_name: '', campus: '', church_join_date: '', baptism_date: '',
  responsible_adult_name: '', responsible_adult_contact: '',
  guardian_name: '', guardian_contact: '', talents: '', spiritual_gifts: '',
  pastoral_notes: '', registration_reason: '', unregistration_reason: '',
  registration_date: '', unregistration_date: '', optional_info: '',
  last_group_attendance: '', last_meeting_attendance: '',
};

export type Tab = 'overview' | 'spiritual' | 'academy' | 'financial' | 'history';

// ── Counseling ────────────────────────────────────────────────────────────
export interface CounselingSession {
  id: number;
  pastor_id: number;
  persona_id?: string;
  lead_id?: number;
  scheduled_at: string;
  duration_minutes: number;
  status: string;
  topic?: string;
  summary?: string;
  confidential_notes?: string;
  created_at: string;
}

// ── Groups ────────────────────────────────────────────────────────────────
export interface Grupo {
  id: string;
  name: string;
  zone?: string;
  address?: string;
  leader_name?: string;
  members_count?: number;
  capacity?: number;
  schedule?: string;
  status?: string;
  created_at?: string;
  latitude?: number;
  longitude?: number;
  code?: string;
  leader_id?: number;
  assistant_id?: number;
  host_id?: number;
  day_of_week?: string;
  start_time?: string;
  end_time?: string;
  base_attendee_ids?: number[];
  base_attendees?: Array<{ persona_id: string }>;
  total_personas?: number;
}

export interface GrupoDetail extends Grupo {
  total_personas?: number;
}

export interface GrupoMember {
  id: string;
  nombre_completo?: string;
}

export type GrupoApi = Grupo & { members_count?: number };
export type Season = { id: number; name: string; status: string };
export type Attendee = { persona_id: string; name: string };

// ── Tasks ─────────────────────────────────────────────────────────────────
export interface ConsolidationTask {
  id: number;
  title: string;
  description?: string;
  status: 'pending' | 'in_progress' | 'done' | 'urgent';
  priority: 'low' | 'medium' | 'high';
  assigned_to?: string;
  member_name?: string;
  due_date?: string;
  category: string;
  created_at: string;
}

export interface CrmTask {
  id: number;
  title: string;
  description: string;
  contact_name: string;
  due_date: string | null;
  status: string;
  priority: string;
  created_at: string;
}

// ── Volunteers ────────────────────────────────────────────────────────────
export interface Volunteer {
  id: number;
  member_id?: string;
  name?: string;
  role?: string;
  team?: string;
  status?: string;
  shift_start?: string;
  shift_end?: string;
  created_at?: string;
  notes?: string;
}

// ── Analytics ─────────────────────────────────────────────────────────────
export type KpiTone = 'neutral' | 'positive' | 'warning';

export interface KpiRow {
  label: string;
  value: string;
  context: string;
  tone: KpiTone;
}

export interface FunnelRow {
  stage: string;
  label: string;
  value: number;
  percent: number;
}

// ── CRM Resources (Biblioteca) ────────────────────────────────────────────
export type ResourceType = 'message' | 'script' | 'quick_reply';
export type ResourceChannel = 'whatsapp' | 'email' | 'sms' | 'general';
export type ResourceCategory =
  | 'bienvenida' | 'seguimiento' | 'invitacion' | 'pastoral'
  | 'consolidacion' | 'anuncio' | 'general';

export interface CrmResource {
  id: string;
  sede_id?: string | null;
  created_by?: string | null;
  name: string;
  description?: string | null;
  type: ResourceType;
  channel?: ResourceChannel | null;
  category: ResourceCategory;
  subject?: string | null;
  body: string;
  steps?: { order: number; text: string }[] | null;
  variables?: string[] | null;
  tags?: string[] | null;
  usage_count: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ── Messaging ─────────────────────────────────────────────────────────────
export type Channel = 'whatsapp' | 'email' | 'sms';

export interface MessagingHistoryRow {
  id: number;
  name: string;
  campaign_name?: string;
  channel: Channel;
  status: string;
  count: number;
  date: string;
  target_count: number;
  delivered_count: number;
  failed_count: number;
}

// ── CrmPersona (from old /crm/types.ts) ───────────────────────────────────
export interface CrmPersona {
  id: string;
  name: string;
  email?: string | null;
  group?: string | null;
  status: string;
  phone?: string | null;
  joinedAt?: string | null;
  church_role?: string | null;
  family_id?: string | null;
}

export interface CrmAnalyticsSummary {
  total_members: number;
  active_members: number;
  total_cases: number;
  cases_by_stage: Record<string, number>;
  open_counseling: number;
  events_this_month: number;
  total_groups: number;
  total_families: number;
}

export function normalizeMembers(payload: any[]): CrmPersona[] {
  if (!Array.isArray(payload)) return [];
  return payload.map((m) => ({
    id: m.id,
    name: m.nombre_completo || '',
    email: m.email,
    group: m.group || (m.grupo_id ? `Casa #${m.grupo_id}` : 'Sin Grupo'),
    status: m.spiritual_status || m.status || 'Nuevo',
    phone: m.telefono || m.phone,
    joinedAt: m.created_at,
    church_role: m.church_role || 'Persona',
    family_id: m.family_id,
  }));
}
