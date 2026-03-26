export interface ProjectRecord {
  id: number;
  title: string;
  description?: string | null;
  status: string;
  color?: string | null;
  icon?: string | null;
  owner_id: number;
  created_at: string;
  updated_at: string;
  tasks?: ProjectTaskRecord[];
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
  order_index: number;
  subtasks?: ProjectTaskRecord[];
}
