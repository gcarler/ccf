/**
 * Shared TypeScript types for the Admin module.
 *
 * These types mirror the canonical backend schemas from
 * backend/schemas/admin.py and the permission taxonomy in
 * backend/core/permissions.py.
 */

// ── Backend API Response Types ────────────────────────────────────────────

/** A platform role as returned by /api/admin/roles */
export interface AdminRoleRead {
  id: string;
  nombre: string;
  permisos: Record<string, string>;
  users_count?: number;
}

/** A user row as returned by /api/admin/users */
export interface AdminUserRead {
  id: string;
  username: string;
  email: string;
  role: string;
  is_active: boolean;
  rol_plataforma_id?: string | null;
  role_name?: string | null;
  permissions?: Record<string, string>;
}

/** Response from /api/admin/users/{id}/permissions */
export interface AdminUserPermissionsRead {
  user_id: string;
  username: string;
  email: string;
  role: string;
  role_permissions: Record<string, string>;
  override_permissions: Record<string, string>;
  module_roles: Array<{ module: string; role_id: string }>;
  effective_permissions: Record<string, string>;
}

/** Response from /api/admin/permissions */
export interface AdminPermissionsTaxonomy {
  permissions: Record<string, { label: string; description: string }>;
  modules: Record<string, string[]>;
  levels: Record<string, string[]>;
}

/** Canonical module levels used by the backend */
export type AdminModuleLevel = 'read' | 'edit' | 'manage' | 'study' | 'none';

/** A module entry rendered in the permission matrix */
export interface AdminPermissionModule {
  id: string;
  label: string;
  levels: AdminModuleLevel[];
}

/** Internal state of the permission matrix */
export type ModulePermissionMap = Record<string, AdminModuleLevel>;

/** Admin dashboard stats from /api/admin/stats */
export interface AdminStatsRead {
  personas: number;
  usuarios_activos: number;
  donaciones_mes: number;
  donantes_mes: number;
  personas_nuevas_mes: number;
  diezmos_mes: number;
  ofrendas_mes: number;
}

/** A comment for forum moderation */
export interface AdminCommentRead {
  id: string;
  author: string;
  text?: string | null;
  context: string;
  type: string;
  created_at?: string | null;
}

/** A milestone/badge */
export interface AdminMilestoneRead {
  id: string;
  name: string;
  description?: string | null;
  icon?: string | null;
  xp: number;
  count: number;
}

/** A donation category */
export interface AdminDonationCategoryRead {
  id: string;
  name: string;
  description?: string | null;
  color?: string | null;
  active: boolean;
}

/** A system variable */
export interface AdminVariableRead {
  key: string;
  value?: string | null;
}

/** Provisioning result */
export interface AdminProvisionResult {
  created: number;
  skipped: number;
  truncated: boolean;
  errors: Array<Record<string, unknown>>;
  accounts: Array<Record<string, unknown>>;
  message: string;
}

/** A user with platform + modular roles (combined view) */
export interface AdminUserWithRolesRead {
  user_id: string;
  username: string;
  email: string;
  nombre: string;
  is_active: boolean;
  rol_plataforma?: { id: string; nombre: string } | null;
  roles_modulares: Array<{ id: string; modulo: string; rol_id: string; rol_nombre: string }>;
}

// ── Dashboard & Stats Types ───────────────────────────────────────────────

/** Dashboard card with value and trend */
export interface DashboardCard {
  title: string;
  value: string;
  trend?: string | null;
  tone?: string;
  icon?: string;
}

/** Dashboard admin response from backend */
export interface AdminDashboardResponse {
  cards: DashboardCard[];
  sesiones_activas: number;
  errores_recientes: number;
  filters: unknown[];
  last_updated: string;
}

/** Academy metrics from dashboard */
export interface AcademyMetrics {
  active_students: number;
  completion_rate: number;
  certificates_issued: number;
  formal_stats: { total: number; completed: number; rate: number; avg_grade: number };
  no_formal_stats: { total: number; completed: number; rate: number; avg_grade: number };
  top_courses: Array<{ title: string; count: number }>;
}

/** Admin testimonials */
export interface AdminTestimonial {
  id: number;
  title?: string;
  content?: string;
  is_approved?: boolean;
  author?: string;
  created_at?: string;
}

/** Agent task from admin dashboard */
export interface AgentTask {
  id: string | number;
  title: string;
  description?: string;
  priority?: string;
  status?: string;
  is_special?: boolean;
  payload?: string;
}

/** Agent insight from admin dashboard */
export interface AgentInsight {
  id: string | number;
  title: string;
  insight_type?: string;
  payload?: string;
}

/** Admin activity log entry */
export interface ActivityLogEntry {
  icon?: React.ComponentType<any>;
  title: string;
  user: string;
  time: string;
  color?: string;
  bg?: string;
}

// ── Finance Types ─────────────────────────────────────────────────────────

/** A finance transaction row */
export interface FinanceTransaction {
  id: number | string;
  amount: number;
  description?: string;
  date?: string;
  status?: string;
  type?: string;
  fund_id?: number;
  category?: string;
  currency?: string;
  persona_id?: string | number | null;
  created_at?: string;
  updated_at?: string;
}

/** Finance summary response */
export interface FinanceSummary {
  total_income?: number;
  total_expenses?: number;
  total_expense?: number;
  funds_total?: number;
  balance?: number;
}

/** Calendar event for UniversalCalendarView */
export interface CalendarEvent {
  id: number | string;
  title: string;
  date: string;
  color: 'blue' | 'sky' | 'emerald' | 'rose' | 'amber';
  location?: string;
}

/** Gantt item for UniversalGanttView */
export interface GanttItem {
  id: number | string;
  title: string;
  subtitle?: string;
  start_date: string;
  end_date: string;
  color: 'blue' | 'sky' | 'emerald' | 'rose' | 'amber';
  progress: number;
}

// ── System Settings Types ─────────────────────────────────────────────────

/** Feature flag rule */
export interface FeatureRule {
  roles_allow?: string[];
  roles_deny?: string[];
  users_allow?: string[];
  users_deny?: string[];
  rollout_percent?: number;
}

/** System configuration */
export interface SystemConfig {
  features_enabled?: Record<string, boolean>;
  feature_rules?: Record<string, FeatureRule>;
  health?: Record<string, string>;
}

/** Audit event log entry */
export interface AuditEvent {
  id: string;
  action: string;
  feature_id?: string;
  actor?: string;
  updated_by?: string;
  timestamp?: string;
  diff?: {
    count?: number;
    changes?: Array<{ key: string; before: unknown; after: unknown }>;
    summary?: string;
  };
}

/** Audit summary */
export interface AuditSummary {
  total_events?: number;
  by_action?: Record<string, number>;
  top_actors?: Array<{ actor: string; count: number }>;
  top_features?: Array<{ feature: string; count: number }>;
}

/** Audit anomalies */
export interface AuditAnomalies {
  has_anomaly?: boolean;
  lookback_hours?: number;
  recent_events?: number;
  actor_spikes?: Array<{ actor: string; count: number; threshold?: number }>;
  action_spikes?: Array<{ action: string; count: number; threshold?: number }>;
}

/** Incident from compliance/audit */
export interface Incident {
  id: string;
  title?: string;
  kind?: string;
  key?: string;
  count?: number;
  threshold?: number;
  severity?: string;
  status?: string;
  created_at?: string;
  updated_at?: string;
  closed_at?: string;
  ack_at?: string;
  silenced_until?: string | null;
  note?: string;
  mtta_minutes?: number;
  mttr_minutes?: number;
  history?: Array<{ status: string; timestamp: string; note?: string }>;
}

/** Incidents summary */
export interface IncidentsSummary {
  counts?: Record<string, number>;
  severity_counts?: Record<string, number>;
  total?: number;
  mtta_minutes?: number | null;
  mttr_minutes?: number | null;
  open_age_p95_minutes?: number | null;
  targets?: { mtta_minutes: number; mttr_minutes: number };
  breaches?: { mtta: boolean; mttr: boolean };
}

// ── Announcements Types ───────────────────────────────────────────────────

/** A published announcement */
export interface Announcement {
  id: number;
  title: string;
  content: string;
  category: string;
  featured: boolean;
  date: string;
  status: 'draft' | 'published' | 'archived';
}

/** Raw announcement from the API */
export interface RawAnnouncement {
  id: number;
  title?: string;
  content?: string;
  category?: string;
  is_featured?: boolean;
  featured?: boolean;
  published_at?: string;
  created_at?: string;
  status?: 'draft' | 'published' | 'archived';
}

// ── Announcements Views ───────────────────────────────────────────────────

/** Grouped announcements by status */
export interface AnnouncementGroup {
  id: string;
  label: string;
  items: Announcement[];
}

// ── Common Component Prop Types ───────────────────────────────────────────

/** Generic props for a stat/dashboard card component */
export interface StatCardProps {
  label: string;
  value: string | number;
  icon?: React.ComponentType<any>;
  trend?: string;
  color?: string;
  bg?: string;
  auraColor?: string;
}

/** Props for a tab button */
export interface TabButtonProps {
  label: string;
  active?: boolean;
  onClick?: () => void;
  icon?: React.ComponentType<any>;
}

/** Props for a progress bar item */
export interface ProgressItemProps {
  label: string;
  value: string | number;
  color?: string;
  percent?: number;
}

/** Props for a summary card with trend */
export interface SummaryCardProps {
  title: string;
  value: string;
  trend?: string;
  icon?: React.ComponentType<any>;
  color?: string;
  auraColor?: string;
}

/** Props for a modality/academic card */
export interface ModalityCardProps {
  title: string;
  stats?: { total: number; completed: number; rate: number; avg_grade: number } | null;
  icon?: React.ComponentType<any>;
  color?: string;
}

/** Props for admin task row */
export interface AdminTaskRowProps {
  task: AgentTask;
  onOpen: (task: AgentTask) => void;
  index?: number;
}

/** Props for a finance drawer stat */
export interface DrawerStatProps {
  label: string;
  value?: string | number | null;
  icon?: React.ComponentType<any>;
}

/** Props for a budget item */
export interface BudgetItemProps {
  label: string;
  percent: number;
  color?: string;
}

/** Props for log/item in activity feed */
export interface LogItemProps {
  icon?: React.ComponentType<any>;
  title: string;
  user: string;
  time: string;
  color?: string;
  bg?: string;
}

/** Props for a health card in system settings */
export interface HealthCardProps {
  label: string;
  value: string | number;
  status?: string;
  icon?: React.ComponentType<any>;
}

/** Props for a feature toggle */
export interface FeatureToggleProps {
  label: string;
  desc?: string;
  active?: boolean;
  onToggle?: () => void;
  loading?: boolean;
}

/** Props for a provider row */
export interface ProviderRowProps {
  icon?: React.ComponentType<any>;
  name: string;
  status?: string;
  color?: string;
  detail?: string;
}

/** Props for security check item */
export interface SecurityCheckProps {
  label: string;
  active?: boolean;
  passed?: boolean;
}

/** Props for cluster node */
export interface ClusterNodeProps {
  label: string;
  status?: string;
  load?: string | number;
}

/** Props for storage stat in assets */
export interface StorageStatProps {
  label: string;
  count: number | string;
  size: string;
  icon?: React.ComponentType<any>;
  color?: string;
}

/** Props for an impact stat card */
export interface ImpactStatProps {
  label: string;
  value: string | number;
  icon?: React.ComponentType<any>;
  color?: string;
  auraColor?: string;
}

/** Props for goal progress */
export interface GoalProgressProps {
  label: string;
  current: number;
  target: number;
  color?: string;
}

/** Props for goal item in radar */
export interface GoalItemProps {
  label: string;
  target: number;
  current: number;
  color?: string;
}

/** Props for radar stat */
export interface RadarStatProps {
  label: string;
  value: string | number;
  icon?: React.ComponentType<any>;
  color?: string;
  trend?: string;
  auraColor?: string;
}

/** Props for status card in intelligence */
export interface StatusCardProps {
  label: string;
  value: string | number;
  status?: string;
  icon?: React.ComponentType<any>;
  color?: string;
}

/** Props for agent state in intelligence */
export interface AgentStateProps {
  label: string;
  load: number;
  status?: string;
  color?: string;
}

/** Props for payment method item */
export interface PaymentMethodItemProps {
  icon?: React.ComponentType<any>;
  label: string;
  active?: boolean;
}

/** Props for KPI card on admin dashboard */
export interface KpiCardProps {
  title: string;
  value: string;
  trend?: string;
  icon?: React.ComponentType<any>;
  color?: string;
}

/** Props for candidate stat in analytics */
export interface CandidateStatProps {
  label: string;
  value: string | number;
  icon?: React.ComponentType<any>;
  color?: string;
  auraColor?: string;
}

/** Props for a content/goal row */
export interface GoalRowProps {
  label: string;
  value: string | number;
}

/** Props for asset normalization */
export interface NormalizeAssetFn {
  (asset: unknown): Record<string, unknown>;
}

// ── Legacy / transitional types ───────────────────────────────────────────

/** CSS custom properties for aura/glow effects — use instead of `as any` */
export type CSSAuraProperties = React.CSSProperties & {
  '--aura-color'?: string;
};
