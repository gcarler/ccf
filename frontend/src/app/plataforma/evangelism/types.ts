export type EventAudience = 'ALL' | 'ROLE' | 'MANUAL';

export interface RoleDefinition {
 id: string;
 name: string;
 color?: string;
 is_leadership?: boolean;
}

export interface MinistryEvent {
 id: string;
 name: string;
 description: string;
 event_type: string;
 event_date?: string | null;
 location?: string | null;
 start_time?: string | null;
 end_time?: string | null;
 target_audience?: EventAudience;
 target_role_id?: string | null;
 target_role_ids: string[];
 target_persona_ids: string[];
 day_of_week?: number;
 month_day?: string;
 fixed_date?: string;
 status?: string;
 cancellation_reason?: string;
 requires_registration?: boolean;
 requires_email_verification?: boolean;
 capacity_max?: number | null;
 registration_opens_at?: string | null;
 registration_closes_at?: string | null;
 waiting_list_enabled?: boolean;
 qr_mode?: 'PER_REGISTRANT' | 'PER_EVENT';
 contact_person?: string | null;
 form_id?: string | null;
}

export interface Persona {
 id: string;
 nombre_completo: string;
 email: string;
 church_role?: string;
}

export interface EventDashboardStat {
 event_id: string;
 latest_session: string | null;
 attended: number;
 expected: number;
 rate: number;
}

export interface EventSessionAttendanceData {
 attendees: { persona_id: string }[];
}

export interface EventAssignment {
 id?: string;
 persona_id: string;
 role: string;
 persona_name?: string;
}

export interface EventSessionData {
 event_id: string;
 session_date: string;
 assignments: EventAssignment[];
 metrics: Record<string, number>;
 attendees: Array<{ persona_id: string; name: string; role: string; scanned_at: string | null }>;
 absentees: Array<{ persona_id: string; name: string; role: string; phone: string }>;
 total_absentees: number;
 absentees_truncated: boolean;
 total_attendance: number;
 total_expected: number;
 attendance_rate: number;
}

export interface EventAnalyticsData {
 kpis: {
 historical_avg: number;
 trend_percentage: number;
 peak_month: { month: string; avg: number };
 };
 monthly_data: Array<{ month: string; avg_attendance: number }>;
}

export interface ScanValidationResult {
 valid: boolean;
 persona_id: string;
 persona_name: string;
 role?: string;
 // plan_clasificador_contextual: rol efectivo de la inscripción (CCF-EVT-)
 // y el rol persistido en la asistencia del día del evento.
 participant_role_code?: string | null;
 role_at_event?: string | null;
}

// ── Rol contextual por evento (plan_clasificador_contextual) ──

export const PARTICIPANT_ROLES = {
    VISITANTE_EVENTO: 'Visitante del evento',
    CONTACTO_EVANGELISTICO: 'Contacto evangelístico',
    MIEMBRO: 'Persona de la comunidad',
    SERVIDOR: 'Servidor',
    INVITADO: 'Invitado',
    VOLUNTARIO: 'Voluntario',
} as const;

export type ParticipantRole = keyof typeof PARTICIPANT_ROLES;

export function participantRoleLabel(code: string | null | undefined): string {
    if (!code) return PARTICIPANT_ROLES.VISITANTE_EVENTO;
    return PARTICIPANT_ROLES[code as ParticipantRole] ?? code;
}

export interface ParticipantRoleOption {
    code: string;
    label: string;
}

export const PARTICIPANT_ROLE_OPTIONS: ParticipantRoleOption[] = Object.entries(PARTICIPANT_ROLES).map(
    ([code, label]) => ({ code, label }),
);

export interface BulkAttendanceSyncResult {
 recorded: number;
 marked_absent?: number;
}

export interface GlobalEventAnalyticsData {
 kpis: {
 total_attendance: number;
 avg_per_session: number;
 trend_percentage: number;
 peak_period?: { label: string; total: number } | null;
 };
 series: Array<{
 key: string;
 label: string;
 total: number;
 sessions: number;
 }>;
}

/** ── Evangelism strategy module types ── */

export interface Strategy {
 id: string;
 name: string;
 description: string;
 codigo?: string;
 clase_raiz?: string;
 activa: boolean;
 default_role_id?: string | null;
 typology: string;
 recurrence: string | null;
 day_of_week: string | null;
 start_time: string | null;
 start_date: string;
 end_date: string;
 categoria_id?: number | null;
 sede_id?: string;
 grupos_count?: number;
 sessions_count?: number;
 // Campos adicionales consumidos por EvangelismClient (badges de estado,
 // tipo legible y marcas de tiempo). El endpoint ``/api/evangelism/
 // strategies`` los devuelve siempre, por lo que se mantienen como
 // obligatorios para preservar la firma de tipo que el indexado por
 // ``Record<'pending'|'active'|'done', string>`` requiere en
 // EvangelismClient.
 status: 'active' | 'pending' | 'done';
 strategy_type: string;
 created_at: string;
 updated_at: string;
}

export interface StrategyGroup {
 id: string;
 name: string;
 zone: string | null;
 address?: string | null;
 leader_name: string | null;
 leader_id?: string | null;
 assistant_id?: string | null;
 host_id?: string | null;
 personas_count: number;
 capacity?: number;
 day_of_week?: string | null;
 start_time?: string | null;
 status?: string;
 evangelism_strategy_id?: string | null;
}

export interface SessionRow {
 id: string;
 grupo_id: string;
 session_date: string;
 status: string;
 estado_habilitacion: string;
 topic: string | null;
 offering_amount: number | null;
 report_notes: string | null;
 attendance_count?: number;
 present_count?: number;
 absent_count?: number;
 cancellation_reason?: string | null;
 novelty_type?: string | null;
 novelty_detail?: string | null;
}

export interface StrategyMetrics {
 strategy_id: string;
 weekly: Array<{
 week: string;
 present: number;
 absent: number;
 first_time: number;
 sessions: number;
 offering: number;
 attendance_rate: number;
 }>;
 summary: {
 total_groups: number;
 total_sessions: number;
 avg_attendance: number;
 total_first_timers: number;
 total_absences: number;
 };
}

export interface HabilitacionResponse {
 session_id: string;
 estado_habilitacion: string;
 habilitado_en: string | null;
}

export interface BulkHabilitacionResponse {
 strategy_id: string;
 sesiones_habilitadas?: number;
 sesiones_deshabilitadas?: number;
}

export interface GenerateSessionsResponse {
 message: string;
 created_count: number;
 session_ids?: string[];
 sessions_per_group?: number;
 total_sessions_created?: number;
}

export interface SessionDetailResponse {
 session: {
 id: string;
 grupo_id: string;
 session_date: string | null;
 topic: string | null;
 offering_amount: number | null;
 status: string;
 report_notes: string | null;
 };
  attendance: Array<{
 id: string;
 session_id: string;
 persona_id: string;
 persona_name: string;
 status: string;
 notes: string | null;
 attended: boolean;
 }>;
  grupo: {
 id: string;
 name: string;
 leader_name: string;
 } | null;
}

export interface GroupDetailResponse {
 id: string;
 code?: string | null;
 name: string;
 zone?: string | null;
 address?: string | null;
 leader_name: string | null;
 leader_id?: string | null;
 assistant_id?: string | null;
 host_id?: string | null;
 personas_count: number;
 capacity?: number;
 day_of_week?: string | null;
 start_time?: string | null;
 end_time?: string | null;
 status?: string;
 created_at?: string | null;
 latitude?: number | null;
 longitude?: number | null;
 base_attendee_ids?: string[];
  base_attendees?: Array<{
    persona_id: string;
    name: string;
    role: string;
    role_label?: string;
    church_role?: string;
    phone?: string;
    persona?: {
      nombre_completo?: string;
      email?: string;
      telefono?: string;
    };
  }>;
 sessions: SessionRow[];
 total_sessions?: number;
 total_attendance?: number;
 monitoring: {
 expected_personas: number;
 average_attendance: number;
 average_attendance_rate: number;
 attendance_trend: Array<{
 session_id: string;
 session_date: string;
 status: string;
 attendance_rate: number;
 present_count: number;
 absent_count: number;
 }>;
 recent_sessions: Array<{
 session_id: string;
 session_date: string;
 status: string;
 present_count: number;
 absent_count: number;
 attendance_rate: number;
 topic: string | null;
 offering_amount: number | null;
 novelty_type: string | null;
 }>;
 repeat_absentees: Array<{
 persona_id: string;
 name: string;
 absences: number;
 details: Array<{
 session_id: string;
 session_date: string | null;
 reason: string | null;
 reason_detail: string | null;
 }>;
 }>;
 alerts: Array<{
 type: string;
 message: string;
 session_id?: number;
 }>;
 };
}

export type HabilitacionAccion = 'HABILITAR' | 'DESHABILITAR' | 'CERRAR';

// ── Multiplication types ──

export interface GrupoSummary {
  id: string;
  nombre: string;
  total_personas: number;
}

export interface MultiplicationCheckItem {
  grupo_id: string;
  grupo_nombre: string;
  lider_nombre: string | null;
  total_personas: number;
  excede_umbral: boolean;
  sugerencia: string;
}

export interface MultiplicationHistoryItem {
  grupo_id: string;
  grupo_nombre: string;
  parent_group_id: string | null;
  parent_group_nombre: string | null;
  notes_historial: string | null;
  created_at: string | null;
  personas_actuales: number;
  lider_nombre: string | null;
}

export interface SplitResponse {
  ok: boolean;
  mensaje: string;
  grupo_original: GrupoSummary;
  nuevo_grupo: GrupoSummary;
  personas_transferidas: number;
}

// ── Attendance record for session forms ──

export interface AttendanceRecord {
  persona_id: string;
  name?: string;
  status: 'present' | 'absent' | 'excused' | 'first_time';
  notes?: string | null;
  es_primera_vez?: boolean;
  requires_seguimiento?: boolean;
}

// ── Post-Event Analytics & CRM Conversion (TKT-EVT-ANALYTICS-03) ──

export interface PostEventAttendanceMetrics {
  total_registered: number;
  total_confirmed: number;
  total_attended: number;
  total_absent: number;
  total_walk_ins: number;
  total_cancelled: number;
  attendance_rate: number;
  no_show_rate: number;
  capacity_utilization: number | null;
}

export interface PostEventFunnelStep {
  step: number;
  stage_id: string;
  name: string;
  count: number;
  pct_of_total: number;
  conversion_from_previous: number;
  dropoff_from_previous: number;
}

export interface PostEventVisitorRetention {
  new_visitors_count: number;
  retained_30d_count: number;
  retained_30d_rate: number;
  retained_60d_count: number;
  retained_60d_rate: number;
  retained_90d_count: number;
  retained_90d_rate: number;
  health_status: 'EXCELLENT' | 'HEALTHY' | 'ATTENTION_NEEDED' | 'CRITICAL';
}

export interface PostEventCrmCaseItem {
  stage_id: string;
  stage_name: string;
  count: number;
}

export interface PostEventCrmBreakdown {
  total_cases_created: number;
  pending_followup_count: number;
  cases_by_stage: PostEventCrmCaseItem[];
}

export interface PostEventAttendeeItem {
  persona_id: string;
  full_name: string;
  phone: string;
  email: string;
  church_role: string;
  is_new_visitor: boolean;
  attended: boolean;
  check_in_at: string | null;
  registration_code: string | null;
  has_crm_case: boolean;
  crm_case_id: string | null;
  crm_stage_name: string | null;
  crm_stage_color: string | null;
  assigned_agent_id: string | null;
  assigned_agent_name: string | null;
  life_group_id: string | null;
  life_group_name: string | null;
  current_funnel_step: string;
  current_funnel_step_label: string;
}

export interface PostEventAnalyticsData {
  event_id: string;
  event_name: string;
  event_date: string | null;
  capacity_max: number | null;
  attendance_metrics: PostEventAttendanceMetrics;
  conversion_funnel: PostEventFunnelStep[];
  visitor_retention: PostEventVisitorRetention;
  crm_breakdown: PostEventCrmBreakdown;
  attendees_funnel_summary: PostEventAttendeeItem[];
}

export interface PastoralExecutiveEventSummary {
  event_id: string;
  event_name: string;
  event_date: string | null;
  total_registered: number;
  total_attended: number;
  attendance_rate: number;
  new_visitors: number;
  retention_30d_rate: number;
  retention_health: string;
}

export interface PastoralExecutiveSummaryData {
  sede_id: string;
  calculated_at: string;
  kpis: {
    total_events: number;
    total_attended: number;
    total_new_visitors: number;
    avg_attendance_rate: number;
    avg_retention_30d_rate: number;
  };
  event_summaries: PastoralExecutiveEventSummary[];
}

export interface CrmChannelResponse {
  success: boolean;
  created_cases: number;
  message: string;
}

export interface FollowupStepSummary {
  name: string;
  sent_count: number;
  scheduled_count: number;
  completion_percentage: number;
}

export interface FollowupStepDefinition {
  step_number: number;
  name: string;
  channel: string;
  delay_hours: number;
  description: string;
  template_default: string;
}

export interface FollowupOverviewData {
  event_id: string;
  event_name: string;
  total_checked_in: number;
  total_enrolled: number;
  active_in_sequence: number;
  completed_sequence: number;
  mentors_assigned: number;
  mentors_unassigned: number;
  responses_received: number;
  response_rate_percentage: number;
  delivery_rate_percentage: number;
  steps_summary: {
    step_1: FollowupStepSummary;
    step_2: FollowupStepSummary;
    step_3: FollowupStepSummary;
  };
  sequence_definition: FollowupStepDefinition[];
}

export interface FollowupStepDetail {
  status: 'PENDING' | 'SENT' | 'FAILED' | 'SKIPPED';
  scheduled_for?: string | null;
  sent_at?: string | null;
  channel?: string | null;
  message_content?: string | null;
}

export interface FollowupAttendeeItem {
  registration_id: string;
  persona_id: string;
  full_name: string;
  first_name?: string | null;
  last_name?: string | null;
  email?: string | null;
  phone?: string | null;
  registration_code: string;
  check_in_at: string | null;
  status: 'ACTIVE' | 'COMPLETED' | 'PAUSED';
  current_step: number;
  mentor_persona_id?: string | null;
  mentor_name?: string | null;
  mentor_phone?: string | null;
  suggested_group_id?: string | null;
  suggested_group_name?: string | null;
  suggested_group_zone?: string | null;
  matched_by_zone: boolean;
  step_1?: FollowupStepDetail | null;
  step_2?: FollowupStepDetail | null;
  step_3?: FollowupStepDetail | null;
  response_received: boolean;
  response_notes?: string | null;
  response_at?: string | null;
}

export interface AvailableMentorItem {
  mentor_id: string;
  name: string;
  email?: string | null;
  phone?: string | null;
  group_id?: string | null;
  group_name?: string | null;
  group_zone?: string | null;
  active_mentees_count: number;
}

export interface AutoAssignMentorsResponse {
  success: boolean;
  assigned_count: number;
  already_assigned_count: number;
  total_checked_in: number;
  message: string;
}

export interface ManualAssignMentorPayload {
  persona_id: string;
  mentor_persona_id: string;
  suggested_group_id?: string | null;
  notes?: string | null;
}

export interface TriggerStepPayload {
  step_number: number;
  persona_ids?: string[] | null;
  force?: boolean;
  custom_content?: string | null;
}

export interface RecordResponsePayload {
  persona_id: string;
  notes: string;
  channel?: string | null;
}

export interface CohortDayMetric {
  count: number;
  percentage: number;
}

export interface CohortRetentionMetrics {
  day_30: CohortDayMetric;
  day_60: CohortDayMetric;
  day_90: CohortDayMetric;
}

export interface SpiritualMaturityDistribution {
  EXPLORADOR: number;
  CRECIENTE: number;
  DISCIPULO: number;
  COMPROMETIDO: number;
  MULTIPLICADOR: number;
}

export interface SpiritualLtvSummary {
  decision_rate_pct: number;
  group_integration_rate_pct: number;
  baptism_rate_pct: number;
  academy_rate_pct: number;
  service_leadership_rate_pct: number;
  avg_spiritual_maturity_score: number;
  maturity_distribution: SpiritualMaturityDistribution;
}

export interface SpiritualMilestoneItem {
  code: string;
  label: string;
  points: number;
}

export interface EventCohortAttendeeItem {
  persona_id: string;
  full_name: string;
  email?: string | null;
  phone?: string | null;
  registration_code: string;
  check_in_at?: string | null;
  retained_30d: boolean;
  retained_60d: boolean;
  retained_90d: boolean;
  group_attendances_count: number;
  has_academy_enrollment: boolean;
  is_baptized: boolean;
  is_servant_or_leader: boolean;
  spiritual_maturity_score: number;
  maturity_level: 'EXPLORADOR' | 'CRECIENTE' | 'DISCIPULO' | 'COMPROMETIDO' | 'MULTIPLICADOR';
  milestones: SpiritualMilestoneItem[];
}

export interface EventCohortRetentionData {
  event_id: string;
  event_name: string;
  event_date?: string | null;
  total_cohort_size: number;
  retention_metrics: CohortRetentionMetrics;
  spiritual_ltv_summary: SpiritualLtvSummary;
  attendees_cohort: EventCohortAttendeeItem[];
}

export interface SedeRetentionRankingItem {
  sede_id: string;
  sede_name: string;
  city: string;
  total_events: number;
  total_cohort_size: number;
  retention_30d_pct: number;
  retention_60d_pct: number;
  retention_90d_pct: number;
  baptism_rate_pct: number;
  academy_rate_pct: number;
  avg_spiritual_maturity_score: number;
  pastoral_efficiency_score: number;
  rank_position: number;
}

export interface MultiSedeCohortAnalysisData {
  calculated_at: string;
  global_kpis: {
    total_sedes: number;
    total_events: number;
    total_cohort_size: number;
    avg_retention_30d_pct: number;
    avg_retention_60d_pct: number;
    avg_retention_90d_pct: number;
    global_avg_spiritual_maturity: number;
  };
  sedes_ranking: SedeRetentionRankingItem[];
}

export interface TemporalCohortStep {
  count: number;
  percentage: number;
  status: 'COMPLETED' | 'IN_PROGRESS';
}

export interface TemporalCohortMatrixRow {
  cohort_key: string;
  cohort_label: string;
  events_count: number;
  total_cohort_size: number;
  m1_30d: TemporalCohortStep;
  m2_60d: TemporalCohortStep;
  m3_90d: TemporalCohortStep;
}

export interface TemporalCohortMatrixData {
  sede_id: string;
  generated_at: string;
  cohorts: TemporalCohortMatrixRow[];
}

export interface AttendeeJourneyEvent {
  event_id: string;
  event_name: string;
  attended_at?: string | null;
}

export interface AttendeeJourneyMilestone {
  title: string;
  date?: string | null;
  pts: number;
}

export interface AttendeeSpiritualJourneyData {
  persona_id: string;
  full_name: string;
  email?: string | null;
  phone?: string | null;
  church_role?: string | null;
  spiritual_status?: string | null;
  spiritual_maturity_score: number;
  maturity_level: 'EXPLORADOR' | 'CRECIENTE' | 'DISCIPULO' | 'COMPROMETIDO' | 'MULTIPLICADOR';
  events_attended_count: number;
  group_meetings_attended_count: number;
  academy_courses_count: number;
  milestones: AttendeeJourneyMilestone[];
  events: AttendeeJourneyEvent[];
}

