import type { ProjectStatus } from '@/lib/projects/constants';

/**
 * Candidato para menciones/asignaciones que regresa
 * `GET /projects/assignee-candidates` (y, en fallback, `GET /crm/personas`).
 * El fallback de CRM envuelve la persona en `user`, por eso es opcional.
 */
export interface AssigneeCandidate {
  id?: string | number;
  user?: { id?: string | number };
  nombre_completo?: string;
  first_name?: string;
  last_name?: string;
  username?: string;
}

/** Respuesta de `POST .../files/upload` (o attachments de tarea). */
export interface AttachmentUploadResponse {
  id?: string;
  name?: string;
  file_url?: string;
  url?: string;
  file_type?: string;
  file_size?: number;
}

/** Adjunto normalizado para adjuntar a un comentario. */
export interface CommentAttachmentInput {
  id?: string;
  name: string;
  url: string;
  type: string;
  size?: number;
}

/** Cuerpo de `POST /projects.../comments`. */
export interface CommentPayload {
  content: string;
  task_id?: string | null;
  mentions: string[];
  project_id?: string;
  attachments?: CommentAttachmentInput[];
}

export interface ProjectKPI {
  id: string;
  project_id: string;
  title: string;
  description?: string | null;
  target_value: number;
  current_value: number;
  unit: string;
  category: string;
  source_type?: string | null;
  component_id?: string | null;
  component_name?: string | null;
  last_spi?: number | null;
  frente?: string | null;
  is_auto_synced?: boolean;
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
  component_id?: string | null;
  task_id?: string | null;
  task_title?: string | null;
  category: string;
  description?: string | null;
  amount: number;
  date: string;
  receipt_url?: string | null;
  status: 'planned' | 'committed' | 'paid';
  is_auto_generated?: boolean;
  source_supply_id?: string | null;
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
  start_date?: string | null;
  target_date?: string | null;
  created_at: string;
  updated_at?: string | null;
  tasks?: ProjectTaskRecord[];
  milestones?: ProjectMilestoneRecord[];
  task_count?: number;
  completed_task_count?: number;
  in_progress_task_count?: number;
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
  execution_matrix?: ProjectExecutionMatrix | null;
}

export interface ProjectPageResponse {
  items: ProjectRecord[];
  total: number;
  skip: number;
  limit: number;
}

export interface ProjectSummaryRecord extends ProjectRecord {
  task_count: number;
  completed_task_count: number;
  in_progress_task_count: number;
  progress_percent: number;
  health_status: 'on_track' | 'at_risk' | 'off_track' | 'completed';
}

export interface ProjectSummaryPageResponse extends Omit<ProjectPageResponse, 'items'> {
  items: ProjectSummaryRecord[];
}

export interface ProjectTaskPageResponse {
  items: ProjectTaskRecord[];
  total: number;
  skip: number;
  limit: number;
}

export interface ProjectWorkloadTaskItem {
  id: string;
  title: string;
  status: string;
  priority: string;
  due_date?: string | null;
  is_overdue: boolean;
  estimated_hours?: number;
  actual_hours?: number;
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
  estimated_hours_total?: number;
  actual_hours_logged?: number;
  hours_utilization_pct?: number;
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
  total_estimated_hours?: number;
  total_actual_hours?: number;
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
  project_title?: string | null;
  title: string;
  description?: string | null;
  created_at?: string;
  updated_at?: string | null;
  deleted_at?: string | null;
  status: string;
  priority: string;
  assignee_id?: string | null;
  parent_id?: string | null;
  component_id?: string | null;
  start_date?: string | null;
  due_date?: string | null;
  node?: string | null;
  physical_progress_pct?: number;
  estimated_hours?: number;
  actual_hours?: number;
  actual_cost?: number;
  labels?: string[];
  order_index?: number;
  supplies?: TaskSupplyRecord[];
  subtasks?: ProjectTaskRecord[];
  attachments?: ProjectAttachment[];
  expenses?: ProjectExpense[];
  comments_count?: number;
}

export interface TaskSupplyRecord {
  id: string;
  task_id: string;
  item_name: string;
  quantity: number;
  status: string;
  unit_cost?: number;
  total_cost?: number;
  expense_id?: string | null;
  linked_expense_id?: string | null;
  auto_create_expense?: boolean;
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
  cpi?: number | null;
  spi?: number | null;
  cost_variance?: number | null;
  cpi_status?: string | null;
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
  lag_days?: number;
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
  excluded_parent_tasks_count?: number;
  total_lag_days?: number;
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
    bac?: number;
    budget_allocated?: number;
    budget_spent?: number;
    progress_percentage?: number;
    evm?: Record<string, unknown>;
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
  | "due_date_approaching"
  | "milestone_completed"
  | "expense_approved";

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
  condition_data: Record<string, unknown>;
  action_type: string;
  action_data: Record<string, unknown>;
  is_active: boolean;
  execution_count: number;
  trigger_count?: number;
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
  condition_data?: Record<string, unknown>;
  action_type: string;
  action_data?: Record<string, unknown>;
  is_active?: boolean;
  sede_id?: string | null;
}

export interface ProjectAutomationRuleUpdate {
  name?: string;
  description?: string | null;
  trigger_event?: string;
  condition_data?: Record<string, unknown>;
  action_type?: string;
  action_data?: Record<string, unknown>;
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
    start_date?: string | null;
    end_date?: string | null;
  }>;
  execution_matrix?: ProjectExecutionMatrix | null;
  submodules_summary?: ProjectSubmodulesSummary | null;
  kpis?: ProjectKPI[];
  indicators?: ProjectIndicator[];
  generated_at: string;
  organization: string;
}

export interface ProjectSubmodulesSummary {
  baseline: {
    has_active_baseline: boolean;
    baseline_id?: string | null;
    baseline_name?: string | null;
    baseline_bac?: number | null;
    baseline_variance_cost: number;
    baseline_variance_schedule: number;
    snapshots_count: number;
  };
  supplies: {
    total_supplies_count: number;
    delivered_supplies_count: number;
    total_supplies_cost: number;
    auto_generated_expenses_count: number;
    auto_generated_expenses_total: number;
  };
  time_tracking: {
    logs_count: number;
    billable_hours: number;
    non_billable_hours: number;
    total_logged_hours: number;
    estimated_hours_total: number;
    hours_utilization_pct: number;
  };
  workload: {
    members_with_tasks_count: number;
    overloaded_members_count: number;
    avg_utilization_pct: number;
  };
  cpm: {
    critical_tasks_count: number;
    critical_completed_count: number;
    dependencies_count: number;
  };
  automations: {
    total_rules_count: number;
    active_rules_count: number;
    total_executions_count: number;
  };
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
  crema_evaluation: CremaValidationResult | Record<string, unknown>;
  source_type?: string | null;
  component_id?: string | null;
  component_name?: string | null;
  frente?: string | null;
  is_auto_synced?: boolean;
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
  crema_evaluation?: CremaValidationResult | Record<string, unknown>;
  source_type?: string | null;
  component_id?: string | null;
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
  source_type?: string | null;
  component_id?: string | null;
}

export interface ProjectExecutionComponentActivity {
  task_id: string;
  title: string;
  status: string;
  physical_progress_pct: number;
  rolled_up_progress_pct: number;
  estimated_hours: number;
  actual_hours: number;
  subtasks_count: number;
  completed_subtasks_count: number;
}

export interface ProjectExecutionComponentRollup {
  component_id: string;
  code: string;
  name: string;
  budget_allocated: number;
  budget_weight_pct: number;
  physical_progress_pct: number;
  financial_progress_pct: number;
  spi: number;
  cpi: number;
  cr: number;
  ev: number;
  pv: number;
  ac: number;
  health_status: string;
  health_color: string;
  activities_count: number;
  subtasks_count: number;
  estimated_hours: number;
  actual_hours: number;
  activities: ProjectExecutionComponentActivity[];
}

export interface ProjectExecutionMatrix {
  project_id: string;
  calculated_at: string;
  frentes: {
    tiempo: {
      spi: number;
      spi_t?: number;
      sv: number;
      progress_pct: number;
      planned_duration_days?: number;
      actual_time_days?: number;
      earned_schedule_days?: number;
      estimated_hours: number;
      actual_hours: number;
      hours_efficiency_pct: number;
      milestones_total: number;
      milestones_completed: number;
      milestones_ontime: number;
      milestones_ontime_pct: number;
      tasks_total: number;
      tasks_completed: number;
      tasks_overdue: number;
    };
    financiero: {
      cpi: number;
      cv: number;
      bac: number;
      ac: number;
      remaining_budget: number;
      burn_rate_pct: number;
      financial_progress_pct: number;
      expenses_count: number;
      budget_100_rule?: {
        is_satisfied?: boolean;
        is_fully_allocated?: boolean;
        allocation_percentage?: number;
        components_budget_total?: number;
        budget_difference?: number;
        status?: string;
      };
    };
    cruce_evm: {
      ev: number;
      pv: number;
      ac: number;
      bac: number;
      cpi: number;
      spi: number;
      cr: number;
      eac: number;
      vac: number;
      balance_gap_pct: number;
      health_status: string;
      health_color: string;
    };
  };
  familias_pro: Record<
    string,
    {
      code: string;
      title: string;
      current_value: number;
      target_value: number;
      unit: string;
      spi: number;
      frente: string;
    }
  >;
  rollup_hierarchy: {
    overall_progress_pct: number;
    components: ProjectExecutionComponentRollup[];
    unassigned_activities_count: number;
    unassigned_progress_pct: number;
  };
  raid_summary: {
    total_risks: number;
    mitigated_risks: number;
    active_risks: number;
    occurred_risks: number;
    mitigated_pct: number;
  };
  sources_catalog: Record<
    string,
    {
      label: string;
      frente: string;
      unit: string;
      default_target: number;
      category: string;
    }
  >;
}

export interface ProjectExecutionSyncResponse {
  project_id: string;
  synced_indicators: number;
  synced_kpis: number;
  seeded_indicators: number;
  seeded_kpis: number;
  execution_matrix: ProjectExecutionMatrix;
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

// ── Earned Value Management (EVM / PMI) ──────────────────────────────────
export interface ProjectEVMMetrics {
  project_id: string;
  calculated_at: string;
  bac: number;
  ac: number;
  ev: number;
  pv: number;
  progress_percentage: number;
  financial_percentage: number;
  cpi: number;
  spi: number;
  cv: number;
  sv: number;
  cr: number;
  eac: number;
  vac: number;
  has_baseline?: boolean;
  baseline_id?: string | null;
  baseline_name?: string | null;
  baseline_bac?: number | null;
  baseline_progress_pct?: number | null;
  baseline_variance_cost?: number | null;
  baseline_variance_schedule?: number | null;
  health_status: string;
  health_color: 'success' | 'warning' | 'destructive';
  recommendations: string[];
}

export interface ProjectCurveSPoint {
  date: string;
  label: string;
  pv: number;
  baseline_pv?: number | null;
  ev: number | null;
  ac: number | null;
  cpi: number | null;
  spi: number | null;
}

export interface ProjectCurveSResponse {
  project_id: string;
  summary: ProjectEVMMetrics;
  points: ProjectCurveSPoint[];
  execution_matrix?: ProjectExecutionMatrix | null;
}

// ── EDT Nivel 2: Componentes y Regla del 100% ──────────────────────────────

export interface ComponentEVMMetrics {
  component_id: string;
  code: string;
  name: string;
  budget_allocated: number;
  total_tasks: number;
  completed_tasks: number;
  physical_progress_pct: number;
  ev: number;
  pv: number;
  ac: number;
  cpi: number;
  spi: number;
  cv: number;
  sv: number;
  cr: number;
  financial_progress_pct: number;
  balance_gap_pct: number;
  health_status: string;
  health_color: 'success' | 'warning' | 'destructive';
}

export interface ProjectComponent {
  id: string;
  project_id: string;
  code: string;
  name: string;
  description?: string | null;
  budget_allocated: number;
  order_index: number;
  color?: string | null;
  status: string;
  created_at: string;
  updated_at?: string | null;
  deleted_at?: string | null;
}

export interface ProjectComponentDetail extends ProjectComponent {
  tasks_count: number;
  expenses_count: number;
  evm?: ComponentEVMMetrics | null;
}

export interface ProjectBudget100RuleValidation {
  project_id: string;
  project_budget_allocated: number;
  components_budget_total: number;
  budget_difference: number;
  allocation_percentage: number;
  is_rule_satisfied: boolean;
  is_fully_allocated: boolean;
  status: 'balanced' | 'under_allocated' | 'over_allocated' | 'no_project_budget';
  components_count: number;
  recommendations: string[];
}

export interface ProjectComponentsBreakdown {
  project_id: string;
  components: ProjectComponentDetail[];
  budget_rule: ProjectBudget100RuleValidation;
}

// ── WBS EDT Nivel 3: Paquetes de Trabajo, 3 Dimensiones y Roll-Up (Fase 3) ────

export interface TaskTimeDimension {
  estimated_hours: number;
  actual_hours: number;
  start_date?: string | null;
  due_date?: string | null;
  duration_days?: number | null;
  subtasks_estimated_hours: number;
  total_estimated_hours: number;
}

export interface TaskProgressDimension {
  physical_progress_pct: number;
  rolled_up_progress_pct: number;
  is_leaf: boolean;
  subtasks_count: number;
  completed_subtasks_count: number;
  weight_basis: 'estimated_hours' | 'equal_count';
}

export interface TaskCostDimension {
  direct_cost: number;
  subtasks_cost: number;
  total_cost: number;
  actual_cost: number;
  planned_cost: number;
  committed_cost: number;
  expenses_count: number;
}

export interface TaskDimensionsDetail {
  task_id: string;
  project_id: string;
  title: string;
  status: string;
  priority: string;
  parent_id?: string | null;
  component_id?: string | null;
  component_name?: string | null;
  time: TaskTimeDimension;
  progress: TaskProgressDimension;
  cost: TaskCostDimension;
  expenses: ProjectExpense[];
}

export interface ProjectTasksRollupSummary {
  project_id: string;
  total_tasks: number;
  leaf_tasks_count: number;
  parent_tasks_count: number;
  total_estimated_hours: number;
  total_actual_hours: number;
  overall_physical_progress_pct: number;
  total_expenses_cost: number;
  tasks_with_expenses_count: number;
  tasks_rollup: TaskDimensionsDetail[];
}

// ── WBS / EDT Nivel 4: Cuadrantes, Organigrama y Pronósticos (Fase 4) ─────────

export interface EarnedScheduleMetrics {
  planned_duration_days: number;
  actual_time_days: number;
  earned_schedule_days: number;
  schedule_variance_time_days: number;
  schedule_performance_index_time: number;
  estimated_duration_at_completion_days: number;
  time_variance_at_completion_days: number;
  projected_finish_date?: string | null;
}

export interface EACForecastModel {
  model_key: 'typical' | 'atypical' | 'composite';
  title: string;
  description: string;
  formula: string;
  eac: number;
  etc: number;
  vac: number;
  vac_percentage: number;
}

export interface TCPIMetrics {
  tcpi_bac?: number | null;
  tcpi_eac?: number | null;
  is_budget_depleted: boolean;
  difficulty_level: 'feasible' | 'moderate' | 'hard' | 'critical';
  explanation: string;
}

export interface EarlyWarningAlert {
  metric: string;
  level: 'critical' | 'warning' | 'info';
  title: string;
  detail: string;
  threshold: string;
  current_value: number;
}

export interface CPIversusSPIQuadrant {
  quadrant_id: 'quadrant_1' | 'quadrant_2' | 'quadrant_3' | 'quadrant_4';
  quadrant_number: number;
  name: string;
  health_status: 'OPTIMO' | 'RIESGO' | 'CRITICO' | 'ATENCION';
  badge_color: 'success' | 'warning' | 'destructive' | 'accent';
  description: string;
  action_recommendation: string;
  cpi: number;
  spi: number;
  point_x_pct: number;
  point_y_pct: number;
  rule_15_triggered: boolean;
  alerts: EarlyWarningAlert[];
}

export interface ProjectEVMAdvancedResponse {
  project_id: string;
  calculated_at: string;
  standard_evm: ProjectEVMMetrics;
  earned_schedule: EarnedScheduleMetrics;
  forecast_models: {
    typical: EACForecastModel;
    atypical: EACForecastModel;
    composite: EACForecastModel;
  };
  tcpi: TCPIMetrics;
  quadrant: CPIversusSPIQuadrant;
  early_warnings: EarlyWarningAlert[];
}

export interface WBSNode {
  id: string;
  wbs_code: string;
  title: string;
  type: 'project' | 'component' | 'task';
  level: number;
  status: string;
  progress_pct: number;
  estimated_hours: number;
  actual_hours: number;
  budget_allocated?: number | null;
  cost: number;
  is_leaf: boolean;
  health_status?: string | null;
  children: WBSNode[];
}

export interface ProjectWBSTreeResponse {
  project_id: string;
  project_title: string;
  total_nodes: number;
  max_depth: number;
  root: WBSNode;
}

// ── Fase 5: AnyDoc Universal & Doctrina PMI ────────────────────────────────

export interface DocumentConversionResponse {
  filename: string;
  format: string;
  markdown: string;
  char_count: number;
  word_count: number;
  processing_time_ms: number;
  engine: string;
  success: boolean;
  error?: string | null;
}

export interface ConvertAndPublishWikiRequest {
  filename: string;
  content_base64?: string;
  format_hint?: string;
  target_type: 'project_wiki' | 'platform_wiki';
  title?: string;
  category?: string;
  tags?: string[];
}

export interface ConvertAndPublishWikiResponse {
  conversion: DocumentConversionResponse;
  published_to: string;
  document_id?: string | null;
  page_key?: string | null;
  title: string;
  message: string;
}

export interface PMIKnowledgeVolume {
  vol: number;
  page_key: string;
  file_name: string;
  title: string;
  summary: string;
  tags: string[];
  char_count: number;
  word_count: number;
  content?: string | null;
}

export interface PMIDoctrineIndexResponse {
  total_volumes: number;
  volumes: PMIKnowledgeVolume[];
  kb_indexed_count: number;
  wiki_seeded_count: number;
}



