export interface ProjectRecord {
  id: number;
  title: string;
  description?: string | null;
  status: string;
  color?: string | null;
  icon?: string | null;
  owner_id?: number | null;
  created_at: string;
  updated_at?: string | null;
  tasks?: ProjectTaskRecord[];
  milestones?: ProjectMilestoneRecord[];
}

export interface ProjectMilestoneRecord {
  id: number;
  project_id: number;
  title: string;
  description?: string | null;
  target_date?: string | null;
  is_completed: boolean;
}

export interface ProjectTaskRecord {
  id: number;
  project_id: number;
  title: string;
  description?: string | null;
  status: string;
  priority: string;
  assignee_id?: number | null;
  parent_id?: number | null;
  start_date?: string | null;
  due_date?: string | null;
  labels?: string[];
  order_index?: number;
  supplies?: TaskSupplyRecord[];
  subtasks?: ProjectTaskRecord[];
}

export interface TaskSupplyRecord {
  id: number;
  task_id: number;
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
  project_id: number;
  task_id?: number | null;
  task_title?: string | null;
  is_read: boolean;
  created_at: string;
}

export interface ProjectActivityItem {
  id: string;
  kind: string;
  project_id: number;
  project_title: string;
  task_id?: number | null;
  task_title?: string | null;
  description: string;
  created_at: string;
}

export interface ProjectCommentItem {
  id: number;
  project_id: number;
  task_id?: number | null;
  content: string;
  author_id: number;
  author_name: string;
  is_resolved: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProjectPortfolioSummaryRow {
  project_status: string;
  total_projects: number;
  total_tasks: number;
  completed_tasks: number;
  completion_ratio: number;
}

export interface ProjectWorkloadSummaryRow {
  assignee_id?: number | null;
  open_tasks: number;
  in_review: number;
  overdue_tasks: number;
}
