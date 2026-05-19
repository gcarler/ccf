export type EventAudience = 'ALL' | 'ROLE' | 'MANUAL';

export interface RoleDefinition {
  id: number;
  name: string;
  color?: string;
  is_leadership?: boolean;
}

export interface MinistryEvent {
  id: number;
  name: string;
  description: string;
  event_type: string;
  event_date?: string | null;
  location?: string | null;
  start_time?: string | null;
  end_time?: string | null;
  target_audience?: EventAudience;
  target_role_id?: number | null;
  target_role_ids?: number[];
  target_member_ids?: number[];
  day_of_week?: number;
  month_day?: string;
  fixed_date?: string;
  status?: string;
  cancellation_reason?: string;
}

export interface Member {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  church_role?: string;
}

export interface EventDashboardStat {
  event_id: number;
  latest_session: string | null;
  attended: number;
  expected: number;
  rate: number;
}

export interface EventSessionAttendanceData {
  attendees: { member_id: number }[];
}

export interface ScanValidationResult {
  valid: boolean;
  member_id: number;
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
