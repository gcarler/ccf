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
  created_at: string;
  updated_at: string;
  attachments?: ProjectCommentAttachment[];
  mentions?: string[];
  module_type?: "project" | "activity" | "agenda";
  context_title?: string | null;
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
