import type { ProjectStatus } from '@/lib/projects/constants';

export interface ProjectKPI {
  id: string;
  project_id: string;
  title: string;
  description?: string | null;
  target_value: number;
  current_value: number;
  unit: string;
  category: string;
  due_date?: string | null;
  created_at?: string;
  updated_at?: string | null;
}

export interface ProjectTaskDependency {
  id: string;
  project_id: string;
  predecessor_id: string;
  successor_id: string;
  dependency_type: 'FS' | 'SS' | 'FF' | 'SF';
  lag_days: number;
  created_at?: string;
}

export interface ProjectExpense {
  id: string;
  project_id: string;
  category: string;
  description?: string | null;
  amount: number;
  date: string;
  receipt_url?: string | null;
  status: 'planned' | 'committed' | 'paid';
  created_by?: string | null;
  creator_name?: string | null;
  created_at: string;
  updated_at?: string | null;
}

export interface ProjectBudgetSummary {
  project_id: string;
  budget_allocated: number;
  budget_spent: number;
  remaining_budget: number;
  burn_rate_percent: number;
  total_expenses_count: number;
  planned_amount: number;
  committed_amount: number;
  paid_amount: number;
  by_category: Record<string, number>;
}

export interface ProjectRecord {
  id: string;
  title: string;
  description?: string | null;
  status: ProjectStatus;
  color?: string | null;
  icon?: string | null;
  owner_id?: string | null;
  created_at: string;
  updated_at?: string | null;
  tasks?: ProjectTaskRecord[];
  milestones?: ProjectMilestoneRecord[];
  progress_percent?: number;
  comments_count?: number;
  progress_mode?: 'auto_tasks' | 'milestones' | 'manual';
  manual_progress?: number;
  budget_allocated?: number | null;
  budget_spent?: number | null;
  health_status?: 'on_track' | 'at_risk' | 'off_track' | 'completed';
  health_override?: string | null;
  kpis?: ProjectKPI[];
  dependencies?: ProjectTaskDependency[];
  expenses?: ProjectExpense[];
  budget_summary?: ProjectBudgetSummary;
  risks?: ProjectRisk[];
  risks_summary?: ProjectRiskSummary;
  workload_summary?: ProjectWorkloadSummary;
}

export interface ProjectWorkloadTaskItem {
  id: string;
  title: string;
  status: string;
  priority: string;
  due_date?: string | null;
  is_overdue: boolean;
}

export interface ProjectMemberWorkload {
  persona_id?: string | null;
  name: string;
  email?: string | null;
  avatar_url?: string | null;
  total_tasks: number;
  active_tasks: number;
  completed_tasks: number;
  overdue_tasks: number;
  urgent_tasks: number;
  high_tasks: number;
  medium_tasks: number;
  low_tasks: number;
  capacity_status: 'available' | 'balanced' | 'overloaded';
  workload_percent: number;
  tasks: ProjectWorkloadTaskItem[];
}

export interface ProjectWorkloadSummary {
  project_id: string;
  total_members: number;
  total_active_tasks: number;
  total_completed_tasks: number;
  total_overdue_tasks: number;
  overloaded_members_count: number;
  balanced_members_count: number;
  available_members_count: number;
  unassigned_tasks_count: number;
  members: ProjectMemberWorkload[];
}

export interface ProjectRisk {
  id: string;
  project_id: string;
  title: string;
  category: 'tecnico' | 'logistico' | 'financiero' | 'reputacional' | 'operativo' | 'legal' | string;
  probability: number;
  impact: number;
  severity_score: number;
  severity_level: 'low' | 'medium' | 'high' | 'critical';
  mitigation_plan?: string | null;
  contingency_plan?: string | null;
  owner_id?: string | null;
  owner_name?: string | null;
  status: 'active' | 'mitigated' | 'occurred';
  created_at: string;
  updated_at?: string | null;
}

export interface ProjectRiskMatrixCell {
  probability: number;
  impact: number;
  severity_score: number;
  count: number;
  risk_ids: string[];
  active_count: number;
}

export interface ProjectRiskSummary {
  project_id: string;
  total_risks: number;
  active_risks: number;
  mitigated_risks: number;
  occurred_risks: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  matrix_5x5: ProjectRiskMatrixCell[];
  by_category: Record<string, number>;
}

export interface ProjectMilestoneRecord {
  id: string;
  project_id: string;
  title: string;
  description?: string | null;
  target_date?: string | null;
  is_completed: boolean;
}

export interface ProjectAttachment {
  id: string;
  task_id: string;
  filename: string;
  file_url: string;
  file_size?: number | null;
  file_type?: string | null;
  content_type?: string | null;
  uploader_id?: string | null;
  uploaded_by?: string | null;
  created_at?: string;
}

export interface ProjectTaskRecord {
  id: string;
  project_id: string;
  title: string;
  description?: string | null;
  created_at?: string;
  updated_at?: string | null;
  status: string;
  priority: string;
  assignee_id?: string | null;
  parent_id?: string | null;
  start_date?: string | null;
  due_date?: string | null;
  node?: string | null;
  labels?: string[];
  order_index?: number;
  supplies?: TaskSupplyRecord[];
  subtasks?: ProjectTaskRecord[];
  attachments?: ProjectAttachment[];
  comments_count?: number;
}

export interface TaskSupplyRecord {
  id: string;
  task_id: string;
  item_name: string;
  quantity: number;
  status: string;
}

export interface ProjectInboxItem {
  id: string;
  type: 'mention' | 'comment' | 'update' | string;
  user: string;
  content: string;
  project: string;
  project_id: string;
  task_id?: string | null;
  task_title?: string | null;
  is_read: boolean;
  created_at: string;
}

export interface ProjectActivityItem {
  id: string;
  kind: string;
  project_id: string;
  project_title: string;
  task_id?: string | null;
  task_title?: string | null;
  description: string;
  created_at: string;
}

export interface ProjectCommentAttachment {
  url: string;
  type: string;
  name: string;
  size: number;
}

export interface ProjectCommentItem {
  id: string;
  project_id: string;
  task_id?: string | null;
  content: string;
  author_id: string;
  author_name: string;
  is_resolved: boolean;
  is_pinned?: boolean;
  pinned_at?: string | null;
  pinned_by?: string | null;
  pinner_name?: string | null;
  created_at: string;
  updated_at: string;
  attachments?: ProjectCommentAttachment[];
  mentions?: string[];
  module_type?: "project" | "activity" | "agenda";
  context_title?: string | null;
}

export interface ProjectUserFavorite {
  id: string;
  project_id: string;
  persona_id: string;
  entity_type: 'task' | 'project' | 'document' | string;
  entity_id: string;
  created_at: string;
}


export interface ProjectPortfolioSummaryRow {
  project_status: string;
  total_projects: number;
  total_tasks: number;
  completed_tasks: number;
  completion_ratio: number;
}

export interface ProjectWorkloadSummaryRow {
  assignee_id?: string | null;
  open_tasks: number;
  in_review: number;
  overdue_tasks: number;
}

export interface ProjectAnalytics {
  project_id: string;
  total_tasks: number;
  completed_tasks: number;
  open_tasks: number;
  overdue_tasks: number;
  unassigned_tasks: number;
  velocity: number;
  velocity_unit: string;
  overdue_days: number;
  risk_level: 'bajo' | 'medio' | 'alto';
  risk_reason: string;
  health_score: number;
  health_label: 'óptima' | 'buena' | 'en riesgo' | 'crítica';
}

// ── Critical Path Method (CPM) (Super-PRO Fase 4) ───────────────────────────
export interface TaskCriticalPathItem {
  task_id: string;
  title: string;
  duration_days: number;
  early_start: number;
  early_finish: number;
  late_start: number;
  late_finish: number;
  slack_days: number;
  is_critical: boolean;
  early_start_date?: string | null;
  early_finish_date?: string | null;
  late_start_date?: string | null;
  late_finish_date?: string | null;
}

export interface ProjectCriticalPathSummary {
  project_id: string;
  total_duration_days: number;
  critical_tasks_count: number;
  critical_path_task_ids: string[];
  tasks: TaskCriticalPathItem[];
  has_cycles: boolean;
}

// ── Project Baseline (Super-PRO Fase 4) ─────────────────────────────────────
export interface TaskBaselineComparisonItem {
  task_id: string;
  title: string;
  baseline_start?: string | null;
  baseline_due?: string | null;
  baseline_duration: number;
  current_start?: string | null;
  current_due?: string | null;
  current_duration: number;
  variance_days: number;
  status: string;
}

export interface ProjectBaseline {
  id: string;
  project_id: string;
  name: string;
  description?: string | null;
  created_by?: string | null;
  created_at: string;
  snapshot_data?: {
    total_tasks?: number;
    project_title?: string;
    tasks?: Array<{
      id: string;
      title: string;
      status: string;
      priority: string;
      start_date?: string | null;
      due_date?: string | null;
    }>;
  };
  comparisons?: TaskBaselineComparisonItem[];
  total_variance_days?: number;
}

// ── Time Tracking (Super-PRO Fase 5) ───────────────────────────────────────
export interface ProjectTimeLog {
  id: string;
  project_id: string;
  task_id?: string | null;
  persona_id: string;
  persona_name?: string | null;
  task_title?: string | null;
  hours: number;
  date: string;
  description?: string | null;
  is_billable: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProjectTimeLogCreate {
  task_id?: string | null;
  persona_id?: string | null;
  hours: number;
  date?: string;
  description?: string | null;
  is_billable?: boolean;
}

export interface TaskTimeSummaryItem {
  task_id: string;
  task_title: string;
  total_hours: number;
  billable_hours: number;
  logs_count: number;
}

export interface MemberTimeSummaryItem {
  persona_id: string;
  persona_name: string;
  avatar_url?: string | null;
  total_hours: number;
  billable_hours: number;
  logs_count: number;
}

export interface ProjectTimeTrackingSummary {
  project_id: string;
  total_hours: number;
  billable_hours: number;
  non_billable_hours: number;
  total_logs: number;
  by_task: TaskTimeSummaryItem[];
  by_member: MemberTimeSummaryItem[];
}

// ── Project Templates (Super-PRO Fase 6) ───────────────────────────────────
export interface TemplatePhaseItem {
  title: string;
  description?: string | null;
  order?: number;
}

export interface TemplateTaskItem {
  title: string;
  description?: string | null;
  priority?: string;
  phase_index?: number | null;
  phase_name?: string | null;
  duration_days: number;
  day_offset: number;
  is_milestone?: boolean;
}

export interface TemplateStructure {
  phases: TemplatePhaseItem[];
  tasks: TemplateTaskItem[];
  default_view?: string;
  tags?: string[];
}

export interface ProjectTemplate {
  id: string;
  name: string;
  description?: string | null;
  category: string;
  default_budget: number;
  structure: TemplateStructure;
  created_by?: string | null;
  creator_name?: string | null;
  is_public: boolean;
  sede_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectTemplateCreate {
  name: string;
  description?: string | null;
  category?: string;
  default_budget?: number;
  structure: TemplateStructure;
  is_public?: boolean;
  sede_id?: string | null;
}

export interface InstantiateProjectFromTemplate {
  title: string;
  description?: string | null;
  start_date?: string | null;
  budget_allocated?: number | null;
  owner_id?: string | null;
}

export interface SaveProjectAsTemplate {
  name: string;
  description?: string | null;
  category?: string;
  is_public?: boolean;
}

// ── Project Automations & Triggers (Super-PRO Fase 7) ───────────────────────

export type TriggerEventType =
  | "task_completed"
  | "task_created"
  | "status_changed"
  | "priority_changed"
  | "due_date_approaching";

export type ActionTypeValue =
  | "notify_assignee"
  | "reassign_task"
  | "create_followup_task"
  | "change_phase"
  | "set_priority";

export interface ProjectAutomationRule {
  id: string;
  project_id?: string | null;
  name: string;
  description?: string | null;
  trigger_event: string;
  condition_data: Record<string, any>;
  action_type: string;
  action_data: Record<string, any>;
  is_active: boolean;
  execution_count: number;
  last_triggered_at?: string | null;
  created_by?: string | null;
  creator_name?: string | null;
  sede_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectAutomationRuleCreate {
  project_id?: string | null;
  name: string;
  description?: string | null;
  trigger_event: string;
  condition_data?: Record<string, any>;
  action_type: string;
  action_data?: Record<string, any>;
  is_active?: boolean;
  sede_id?: string | null;
}

export interface ProjectAutomationRuleUpdate {
  name?: string;
  description?: string | null;
  trigger_event?: string;
  condition_data?: Record<string, any>;
  action_type?: string;
  action_data?: Record<string, any>;
  is_active?: boolean;
}

export interface AutomationExecutionResult {
  rule_id: string;
  rule_name: string;
  action_type: string;
  status: string;
  details?: string | null;
}

export interface ProjectExecutiveReportData {
  project: {
    id: string;
    title: string;
    description: string;
    status: string;
    priority: string;
    health_override?: string | null;
    progress_mode?: string;
    progress_percentage: number;
    budget_allocated: number;
    budget_spent: number;
    start_date?: string | null;
    target_date?: string | null;
    owner_name: string;
    sede_id?: string | null;
    created_at?: string | null;
  };
  tasks_metrics: {
    total: number;
    completed: number;
    in_progress: number;
    todo: number;
    blocked: number;
    completion_rate: number;
  };
  financial_kpis: {
    project_id: string;
    budget_allocated: number;
    budget_spent: number;
    remaining_budget: number;
    burn_rate_percent: number;
    total_expenses_count: number;
    by_category: Record<string, number>;
  };
  raid_kpis: {
    total_risks: number;
    critical_count: number;
    high_count: number;
    medium_count: number;
    low_count: number;
    risks: Array<{
      id: string;
      title: string;
      category: string;
      probability: number;
      impact: number;
      severity: number;
      status: string;
      mitigation_plan?: string | null;
    }>;
  };
  cpm_metrics: {
    project_id: string;
    total_duration_days: number;
    critical_tasks_count: number;
    critical_path_task_ids: string[];
    tasks: Array<{
      task_id: string;
      title: string;
      duration_days: number;
      is_critical: boolean;
      slack_days: number;
    }>;
  };
  time_metrics: {
    total_hours: number;
    billable_hours: number;
    non_billable_hours: number;
    total_logs: number;
    by_task: Array<{ task_title: string; total_hours: number }>;
    by_member: Array<{ persona_name: string; total_hours: number; billable_hours: number }>;
  };
  phases: Array<{
    id: string;
    name: string;
    order_index: number;
    total_tasks: number;
    completed_tasks: number;
    progress_percent: number;
  }>;
  generated_at: string;
  organization: string;
}


// ── Project Indicators MGA / CREMA & SPI (Super-PRO CREMA Fase 1 & 2) ─────────

export type MgaIndicatorLevel =
  | "RESULTADO_EFICACIA"
  | "PRODUCTO_PRINCIPAL"
  | "PRODUCTO_SECUNDARIO"
  | "GESTION_PROCESO"
  | "EFICIENCIA"
  | "CALIDAD";

export type MgaCalculationType =
  | "ABSOLUTO_ACUMULADO"
  | "PORCENTAJE_PROPORCION"
  | "TASA_VARIACION"
  | "COSTO_EFICIENCIA";

export interface ProjectIndicatorRecord {
  id: string;
  indicator_id: string;
  period: string;
  target_value: number;
  actual_value: number;
  spi?: number | null;
  notes?: string | null;
  evidence_url?: string | null;
  reported_by?: string | null;
  reporter_name?: string | null;
  reported_at: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectIndicatorRecordCreate {
  period: string;
  target_value: number;
  actual_value: number;
  spi?: number | null;
  notes?: string | null;
  evidence_url?: string | null;
  reported_at?: string | null;
}

export interface CremaCriterionDetail {
  name?: string;
  score: number;
  passed: boolean;
  recommendations: string[];
}

export interface CremaValidationResult {
  score: number;
  status: "EXCELENTE" | "BUENO" | "REGULAR" | "DEFICIENTE" | string;
  criteria: Record<string, CremaCriterionDetail>;
  summary: string;
}

export interface ValidateCremaPayload {
  name: string;
  description?: string;
  level?: string;
  calculation_type?: string;
  unit_of_measure?: string;
  target_value?: number;
  frequency?: string;
}

export interface ProjectIndicator {
  id: string;
  project_id: string;
  code?: string | null;
  name: string;
  description?: string | null;
  level: MgaIndicatorLevel | string;
  calculation_type: MgaCalculationType | string;
  unit_of_measure?: string | null;
  baseline_value: number;
  target_value: number;
  current_value: number;
  frequency: string;
  period_targets: Record<string, number>;
  crema_score?: number | null;
  crema_evaluation: CremaValidationResult | Record<string, any>;
  created_by?: string | null;
  creator_name?: string | null;
  sede_id?: string | null;
  records_count?: number;
  last_spi?: number | null;
  created_at: string;
  updated_at: string;
  records?: ProjectIndicatorRecord[];
}

export interface ProjectIndicatorCreate {
  code?: string;
  name: string;
  description?: string;
  level: string;
  calculation_type: string;
  unit_of_measure?: string;
  baseline_value?: number;
  target_value?: number;
  current_value?: number;
  frequency?: string;
  period_targets?: Record<string, number>;
  crema_score?: number;
  crema_evaluation?: Record<string, any>;
}

export interface ProjectIndicatorUpdate {
  code?: string;
  name?: string;
  description?: string;
  level?: string;
  calculation_type?: string;
  unit_of_measure?: string;
  baseline_value?: number;
  target_value?: number;
  current_value?: number;
  frequency?: string;
  period_targets?: Record<string, number>;
}

// ============================================================================
// Bóveda Documental y Visor Universal Embebido (Super-PRO Files Fase 2)
// ============================================================================

export type ProjectFileSource = 'local' | 'drive' | 'dropbox' | 'onedrive';

export interface ProjectFileRecord {
  id: string;
  project_id: string;
  name: string;
  description?: string | null;
  category: string;
  file_source: ProjectFileSource;
  file_url: string;
  file_type?: string | null;
  file_size?: number | null;
  drive_file_id?: string | null;
  embed_url?: string | null;
  task_id?: string | null;
  task_title?: string | null;
  phase_id?: string | null;
  phase_name?: string | null;
  uploaded_by?: string | null;
  uploader_name?: string | null;
  created_at: string;
  updated_at?: string | null;
}

export interface ProjectFilesSummary {
  project_id: string;
  total_files: number;
  total_size_bytes: number;
  by_source: Record<string, number>;
  by_category: Record<string, number>;
  files: ProjectFileRecord[];
}





