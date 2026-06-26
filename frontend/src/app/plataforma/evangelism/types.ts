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
 target_role_ids?: string[];
 target_persona_ids?: string[];
 day_of_week?: number;
 month_day?: string;
 fixed_date?: string;
 status?: string;
 cancellation_reason?: string;
}

export interface Persona {
 id: string;
 nombre_completo: string;
 email: string;
 church_role?: string;
}

export type Member = Persona;

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

export interface ScanValidationResult {
 valid: boolean;
 persona_id: string;
 member_name: string;
 role?: string;
}

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
}

export interface StrategyGroup {
 id: number;
 name: string;
 zone: string | null;
 address?: string | null;
 leader_name: string | null;
 leader_id?: string | null;
 assistant_id?: string | null;
 host_id?: string | null;
 members_count: number;
 capacity?: number;
 day_of_week?: string | null;
 start_time?: string | null;
 status?: string;
 evangelism_strategy_id?: string | null;
}

export interface SessionRow {
 id: number;
 grupo_id: number;
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
 session_id: number;
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
 session_ids?: number[];
 sessions_per_group?: number;
 total_sessions_created?: number;
}

export interface SessionDetailResponse {
 session: {
 id: number;
 cell_group_id: number;
 session_date: string | null;
 topic: string | null;
 offering_amount: number | null;
 status: string;
 report_notes: string | null;
 };
 attendance: Array<{
 id: number;
 session_id: number;
 persona_id: string;
 persona_name: string;
 status: string;
 notes: string | null;
 attended: boolean;
 }>;
 cell_group: {
 id: number;
 name: string;
 leader_name: string;
 } | null;
}

export interface GroupDetailResponse {
 id: number;
 code?: string | null;
 name: string;
 zone?: string | null;
 address?: string | null;
 leader_name: string | null;
 leader_id?: string | null;
 assistant_id?: string | null;
 host_id?: string | null;
 members_count: number;
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
 church_role?: string;
 phone?: string;
 }>;
 sessions: SessionRow[];
 total_sessions?: number;
 total_attendance?: number;
 monitoring: {
 expected_members: number;
 average_attendance: number;
 average_attendance_rate: number;
 attendance_trend: Array<{
 session_id: number;
 session_date: string;
 status: string;
 attendance_rate: number;
 present_count: number;
 absent_count: number;
 }>;
 recent_sessions: Array<{
 session_id: number;
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
 session_id: number;
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
