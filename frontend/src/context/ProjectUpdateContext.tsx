"use client";

import React, { createContext, useContext, ReactNode } from "react";
import type {
  ProjectRecord,
  ProjectTaskRecord,
  ProjectActivityItem,
} from "@/types/projects";

export interface PhaseDef {
  slug: string;
  name: string;
  color: string;
  order_index: number;
}

export interface CreateTaskPayload {
  title: string;
  description?: string | null;
  priority: string;
  status: string;
  assignee_id?: string | null;
  due_date?: string | null;
}

export interface ProjectUpdateContextValue {
  project: ProjectRecord | null;
  tasks: ProjectTaskRecord[];
  phases: PhaseDef[];
  activities: ProjectActivityItem[];
  loading: boolean;

  reloadProject: () => Promise<void>;
  updateTask: (taskId: string, patch: Partial<ProjectTaskRecord>) => Promise<void>;
  createTask: (payload: CreateTaskPayload) => Promise<boolean> | Promise<void>;
  deleteTask: (taskId: string) => Promise<void>;
  updateProject: (patch: Partial<ProjectRecord>) => Promise<void>;
}

const ProjectUpdateContext = createContext<ProjectUpdateContextValue | null>(null);

export function ProjectUpdateProvider({
  children,
  value,
}: {
  children: ReactNode;
  value: ProjectUpdateContextValue;
}) {
  return <ProjectUpdateContext.Provider value={value}>{children}</ProjectUpdateContext.Provider>;
}

export function useProjectUpdate() {
  const ctx = useContext(ProjectUpdateContext);
  if (!ctx) {
    throw new Error("useProjectUpdate must be used within a ProjectUpdateProvider");
  }
  return ctx;
}
