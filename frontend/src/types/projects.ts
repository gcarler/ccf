export interface ProjectRecord {
  id: string;
  title: string;
  description?: string | null;
  status: string;
  color?: string | null;
  icon?: string | null;
  owner_id?: string | null;
  created_at: string;
  updated_at?: string | null;
  tasks?: ProjectTaskRecord[];
  milestones?: ProjectMilestoneRecord[];
  progress_percent?: number;
  comments_count?: number;
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
  id: number;
  task_id: string;
  filename: string;
  file_url: string;
  file_size?: number | null;
  file_type?: string | null;
  content_type?: string | null;
  uploader_id?: number | null;
  uploaded_by?: number | null;
  created_at?: string;
}

export interface ProjectTaskRecord {
  id: string;
  project_id: string;
  title: string;
  description?: string | null;
  created_at?: string;
  status: string;
  priority: string;
  assignee_id?: string | null;
  parent_id?: string | null;
  start_date?: string | null;
  due_date?: string | null;
  labels?: string[];
  order_index?: number;
  supplies?: TaskSupplyRecord[];
  subtasks?: ProjectTaskRecord[];
  attachments?: ProjectAttachment[];
  comments_count?: number;
}

export interface TaskSupplyRecord {
  id: number;
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

export interface ProjectCommentItem {
  id: number;
  project_id: string;
  task_id?: string | null;
  content: string;
  author_id: number;
  author_name: string;
  author: string;       // author display name
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
  assignee_id?: string | null;
  open_tasks: number;
  in_review: number;
  overdue_tasks: number;
}
