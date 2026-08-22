/**
 * Shared TypeScript types for Dashboard & BI metrics in CCF Platform.
 */

export interface MetricCard {
  title: string;
  value: string;
  trend?: string | null;
  tone?: 'blue' | 'emerald' | 'amber' | 'rose' | 'indigo' | 'slate';
  icon?: string | null;
}

export interface ChartDataPoint {
  label: string;
  value: number;
}

export interface SedeFilter {
  id: string;
  nombre: string;
}

export interface BaseDashboard {
  cards: MetricCard[];
  filters?: SedeFilter[];
  last_updated: string;
}

export interface CrmDashboard extends BaseDashboard {
  pipeline_distribution?: ChartDataPoint[];
  monthly_conversions?: ChartDataPoint[];
  active_cases_count?: number;
  unassigned_cases_count?: number;
}

export interface AcademyDashboard extends BaseDashboard {
  enrollments_by_course?: ChartDataPoint[];
  completion_rate?: number;
  monthly_enrollments?: ChartDataPoint[];
}

export interface EvangelismDashboard extends BaseDashboard {
  attendance_series?: ChartDataPoint[];
  active_groups_count?: number;
  new_decisions_month?: number;
}

export interface FinanceDashboard extends BaseDashboard {
  income_by_category?: ChartDataPoint[];
  monthly_series?: ChartDataPoint[];
  latest_donations?: Array<{
    donor: string;
    type?: string | null;
    amount: number;
    date: string;
  }>;
}

export interface AgendaDashboard extends BaseDashboard {
  eventos_proximos?: Array<{
    titulo: string;
    ubicacion?: string;
    fecha: string;
    participantes?: number;
  }>;
  colisiones_recurso?: number;
}

export interface ProjectsDashboard extends BaseDashboard {
  tasks_by_status?: ChartDataPoint[];
  active_projects_count?: number;
}

export interface CmsDashboard extends BaseDashboard {
  published_pages_count?: number;
  monthly_views?: ChartDataPoint[];
}

export interface AdminGlobalDashboard extends BaseDashboard {
  sesiones_activas?: number;
  errores_recientes?: number;
}
