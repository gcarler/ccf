/**
 * Mock data for the Projects module.
 *
 * Provides typed, realistic mock data that frontend components can consume
 * without an active backend. All IDs are valid UUIDs; all relationships
 * (project → tasks → comments → supplies) are internally consistent.
 *
 * Import directly in pages / stories / tests:
 *   import { MOCK_PROJECTS, getMockProjectById } from "@/lib/mocks/projects";
 */

import type {
  ProjectActivityItem,
  ProjectCommentItem,
  ProjectInboxItem,
  ProjectMilestoneRecord,
  ProjectPortfolioSummaryRow,
  ProjectRecord,
  ProjectTaskRecord,
  ProjectWorkloadSummaryRow,
  TaskSupplyRecord,
} from "@/types/projects";

// ── Seed IDs ──────────────────────────────────────────────────────────
// Fixed UUIDs so mock data is deterministic across reloads.

const P1_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890";
const P2_ID = "b2c3d4e5-f6a7-8901-bcde-f12345678901";
const P3_ID = "c3d4e5f6-a7b8-9012-cdef-123456789012";
const PERSONA_A = "d4e5f6a7-b8c9-0123-def1-234567890123";
const PERSONA_B = "e5f6a7b8-c9d0-1234-ef12-345678901234";

// ── Timeline helper ───────────────────────────────────────────────────

function daysAgo(n: number): string {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString();
}

function daysFromNow(n: number): string {
  const d = new Date();
  d.setDate(d.getDate() + n);
  return d.toISOString();
}

// ── Milestones ────────────────────────────────────────────────────────

const MOCK_MILESTONES: Record<string, ProjectMilestoneRecord[]> = {
  [P1_ID]: [
    { id: "f1a2b3c4-d5e6-7890-abcd-ef1234567890", project_id: P1_ID, title: "MVP v1.0", target_date: daysFromNow(14), is_completed: false },
    { id: "f2a3b4c5-e6f7-8901-bcde-f12345678901", project_id: P1_ID, title: "Diseño aprobado", target_date: daysAgo(3), is_completed: true },
    { id: "f3a4b5c6-f7a8-9012-cdef-123456789012", project_id: P1_ID, title: "Lanzamiento", target_date: daysFromNow(45), is_completed: false },
  ],
  [P2_ID]: [
    { id: "f4a5b6c7-a8b9-0123-def1-234567890123", project_id: P2_ID, title: "Ronda oración 2025-Q3", target_date: daysFromNow(7), is_completed: false },
    { id: "f5a6b7c8-b9c0-1234-ef12-345678901234", project_id: P2_ID, title: "Logística lista", target_date: daysAgo(1), is_completed: true },
  ],
  [P3_ID]: [
    { id: "f6a7b8c9-c0d1-2345-f123-456789012345", project_id: P3_ID, title: "Retrospectiva final", target_date: daysFromNow(90), is_completed: false },
  ],
};

// ── Supplies by task ─────────────────────────────────────────────────

const SUPPLIES_BY_TASK: Record<string, TaskSupplyRecord[]> = {
  // task T1 (project 1)
  "11111111-1111-1111-1111-111111111001": [
    { id: "11111111-aaaa-4000-8000-000000000001", task_id: "11111111-1111-1111-1111-111111111001", item_name: "Hosting mensual", quantity: 3, status: "purchased" },
    { id: "11111111-aaaa-4000-8000-000000000002", task_id: "11111111-1111-1111-1111-111111111001", item_name: "Dominio .com", quantity: 1, status: "pending" },
  ],
  // task T3 (project 1)
  "11111111-1111-1111-1111-111111111003": [
    { id: "11111111-aaaa-4000-8000-000000000003", task_id: "11111111-1111-1111-1111-111111111003", item_name: "Cuenta Figma Pro", quantity: 1, status: "purchased" },
  ],
};

// ── Tasks ────────────────────────────────────────────────────────────

const MOCK_TASKS: ProjectTaskRecord[] = [
  // ── Project 1: Campaña Redes Sociales ──
  {
    id: "11111111-1111-1111-1111-111111111001",
    project_id: P1_ID,
    title: "Diseñar piezas gráficas para Instagram",
    description: "Crear 5 diseños de tarjetas con versículos para la campaña de redes.",
    status: "in_progress",
    priority: "high",
    assignee_id: PERSONA_A,
    due_date: daysFromNow(7),
    created_at: daysAgo(5),
    labels: ["diseño", "redes"],
    order_index: 0,
    supplies: SUPPLIES_BY_TASK["11111111-1111-1111-1111-111111111001"],
  },
  {
    id: "11111111-1111-1111-1111-111111111002",
    project_id: P1_ID,
    title: "Programar publicaciones en Meta Business",
    description: "Usar el calendario de Meta para agendar 15 posts.",
    status: "todo",
    priority: "medium",
    assignee_id: PERSONA_B,
    due_date: daysFromNow(14),
    created_at: daysAgo(3),
    labels: ["redes", "programación"],
    order_index: 1,
  },
  {
    id: "11111111-1111-1111-1111-111111111003",
    project_id: P1_ID,
    title: "Diseñar logo para la campaña",
    description: "Logo temporal mientras se define la identidad visual.",
    status: "completed",
    priority: "urgent",
    assignee_id: PERSONA_A,
    due_date: daysAgo(2),
    created_at: daysAgo(10),
    labels: ["diseño"],
    order_index: 2,
    supplies: SUPPLIES_BY_TASK["11111111-1111-1111-1111-111111111003"],
  },
  {
    id: "11111111-1111-1111-1111-111111111004",
    project_id: P1_ID,
    title: "Revisar métricas de alcance semanal",
    status: "review",
    priority: "low",
    assignee_id: null,
    due_date: daysFromNow(3),
    created_at: daysAgo(1),
    labels: ["métricas"],
    order_index: 3,
  },

  // ── Project 2: Vigilia de Oración ──
  {
    id: "22222222-2222-2222-2222-222222222001",
    project_id: P2_ID,
    title: "Coordinar voluntarios para la vigilia",
    status: "in_progress",
    priority: "high",
    assignee_id: PERSONA_A,
    due_date: daysFromNow(5),
    created_at: daysAgo(7),
    labels: ["logística"],
    order_index: 0,
  },
  {
    id: "22222222-2222-2222-2222-222222222002",
    project_id: P2_ID,
    title: "Preparar guía de oración impresa",
    status: "todo",
    priority: "medium",
    assignee_id: PERSONA_B,
    due_date: daysFromNow(10),
    created_at: daysAgo(4),
    labels: ["impresión"],
    order_index: 1,
  },

  // ── Project 3: Construcción Salón ──
  {
    id: "33333333-3333-3333-3333-333333333001",
    project_id: P3_ID,
    title: "Cotizar materiales de construcción",
    status: "todo",
    priority: "urgent",
    due_date: daysFromNow(30),
    created_at: daysAgo(15),
    labels: ["compras"],
    order_index: 0,
  },
];

// ── Comments ─────────────────────────────────────────────────────────

// SPR1: real UUID4 layout (8-4-4-4-12 hex) so these parse with
// ``uuid.UUID(s)`` if ever used as e2e seeds. The middle ``4000`` is the
// UUIDv4 version marker (RFC 4122) and the trailing ``8`` in segment 4
// is the RFC 4122 variant marker.
const C1 = "22222222-aaaa-4000-8000-000000000101";
const C2 = "22222222-aaaa-4000-8000-000000000102";
const C3 = "22222222-aaaa-4000-8000-000000000103";
const C4 = "22222222-aaaa-4000-8000-000000000104";
const C5 = "22222222-aaaa-4000-8000-000000000105";
const C6 = "22222222-aaaa-4000-8000-000000000106";

const MOCK_COMMENTS: ProjectCommentItem[] = [
  {
    id: C1,
    project_id: P1_ID,
    task_id: "11111111-1111-1111-1111-111111111001",
    content: "Me gusta el diseño propuesto. Revisemos los colores con el equipo de comunicaciones.",
    author_id: PERSONA_B,
    author_name: "María García",
    author: "María García",
    is_resolved: false,
    created_at: daysAgo(1),
    updated_at: daysAgo(1),
  },
  {
    id: C2,
    project_id: P1_ID,
    task_id: "11111111-1111-1111-1111-111111111001",
    content: "Ya compartí los archivos en la carpeta compartida de Drive.",
    author_id: PERSONA_A,
    author_name: "Carlos López",
    author: "Carlos López",
    is_resolved: true,
    created_at: daysAgo(3),
    updated_at: daysAgo(2),
  },
  {
    id: C3,
    project_id: P1_ID,
    task_id: null,
    content: "El cronograma general necesita ajustes, hablemos en la reunión del viernes.",
    author_id: PERSONA_A,
    author_name: "Carlos López",
    author: "Carlos López",
    is_resolved: false,
    created_at: daysAgo(0),
    updated_at: daysAgo(0),
  },
  {
    id: C4,
    project_id: P2_ID,
    task_id: "22222222-2222-2222-2222-222222222001",
    content: "Confirmé con 8 voluntarios. Pendiente el transporte.",
    author_id: PERSONA_B,
    author_name: "María García",
    author: "María García",
    is_resolved: false,
    created_at: daysAgo(0),
    updated_at: daysAgo(0),
  },
  {
    id: C5,
    project_id: P2_ID,
    task_id: null,
    content: "Recordatorio: la vigilia es el sábado a las 7pm.",
    author_id: PERSONA_A,
    author_name: "Carlos López",
    author: "Carlos López",
    is_resolved: true,
    created_at: daysAgo(2),
    updated_at: daysAgo(2),
  },
  {
    id: C6,
    project_id: P3_ID,
    task_id: null,
    content: "La última cotización llegó por $12.5M. Esperando la de los acabados.",
    author_id: PERSONA_B,
    author_name: "María García",
    author: "María García",
    is_resolved: false,
    created_at: daysAgo(5),
    updated_at: daysAgo(5),
  },
];

// ── Inbox Items ──────────────────────────────────────────────────────

const MOCK_INBOX_ITEMS: ProjectInboxItem[] = [
  {
    id: "comment-101",
    type: "comment",
    user: "María García",
    content: "Me gusta el diseño propuesto. Revisemos los colores...",
    project: "Campaña Redes Sociales",
    project_id: P1_ID,
    task_id: "11111111-1111-1111-1111-111111111001",
    is_read: false,
    created_at: daysAgo(1),
  },
  {
    id: "comment-103",
    type: "comment",
    user: "Carlos López",
    content: "El cronograma general necesita ajustes, hablemos...",
    project: "Campaña Redes Sociales",
    project_id: P1_ID,
    task_id: null,
    is_read: false,
    created_at: daysAgo(0),
  },
  {
    id: "comment-104",
    type: "comment",
    user: "María García",
    content: "Confirmé con 8 voluntarios. Pendiente el transporte.",
    project: "Vigilia de Oración",
    project_id: P2_ID,
    task_id: "22222222-2222-2222-2222-222222222001",
    is_read: true,
    created_at: daysAgo(0),
  },
];

// ── Activities ───────────────────────────────────────────────────────

const MOCK_ACTIVITIES: ProjectActivityItem[] = [
  { id: "act-001", kind: "project_created", project_id: P1_ID, project_title: "Campaña Redes Sociales", description: "Proyecto 'Campaña Redes Sociales' creado", created_at: daysAgo(10) },
  { id: "act-002", kind: "task_created", project_id: P1_ID, project_title: "Campaña Redes Sociales", task_id: "11111111-1111-1111-1111-111111111001", task_title: "Diseñar piezas gráficas", description: "Tarea 'Diseñar piezas gráficas para Instagram' creada", created_at: daysAgo(8) },
  { id: "act-003", kind: "task_completed", project_id: P1_ID, project_title: "Campaña Redes Sociales", task_id: "11111111-1111-1111-1111-111111111003", task_title: "Diseñar logo", description: "Tarea 'Diseñar logo para la campaña' completada", created_at: daysAgo(2) },
  { id: "act-004", kind: "comment_added", project_id: P1_ID, project_title: "Campaña Redes Sociales", description: "María García comentó en 'Diseñar piezas gráficas'", created_at: daysAgo(1) },
  { id: "act-005", kind: "milestone_completed", project_id: P1_ID, project_title: "Campaña Redes Sociales", description: "Hito 'Diseño aprobado' completado", created_at: daysAgo(3) },
];

// ── Projects ─────────────────────────────────────────────────────────

const MOCK_PROJECTS: ProjectRecord[] = [
  {
    id: P1_ID,
    title: "Campaña Redes Sociales",
    description: "Estrategia de contenido para Instagram y Facebook durante el mes de la familia.",
    status: "active",
    color: "#3b82f6",
    owner_id: PERSONA_A,
    created_at: daysAgo(10),
    updated_at: daysAgo(0),
    progress_percent: 35,
    comments_count: 3,
  },
  {
    id: P2_ID,
    title: "Vigilia de Oración",
    description: "Organización de la vigilia trimestral de la iglesia.",
    status: "active",
    color: "#8b5cf6",
    owner_id: PERSONA_B,
    created_at: daysAgo(20),
    updated_at: daysAgo(1),
    progress_percent: 60,
    comments_count: 2,
  },
  {
    id: P3_ID,
    title: "Remodelación Salón Principal",
    description: "Construcción y adecuación del salón de eventos.",
    status: "planning",
    color: "#f59e0b",
    owner_id: PERSONA_A,
    created_at: daysAgo(60),
    updated_at: daysAgo(5),
    progress_percent: 5,
    comments_count: 1,
  },
];

// ── Portfolio & Workload ─────────────────────────────────────────────

const MOCK_PORTFOLIO: ProjectPortfolioSummaryRow[] = [
  { project_status: "active", total_projects: 2, total_tasks: 6, completed_tasks: 1, completion_ratio: 0.17 },
  { project_status: "planning", total_projects: 1, total_tasks: 1, completed_tasks: 0, completion_ratio: 0.0 },
  { project_status: "completed", total_projects: 1, total_tasks: 0, completed_tasks: 0, completion_ratio: 1.0 },
];

const MOCK_WORKLOAD: ProjectWorkloadSummaryRow[] = [
  { assignee_id: PERSONA_A, open_tasks: 3, in_review: 0, overdue_tasks: 1 },
  { assignee_id: PERSONA_B, open_tasks: 2, in_review: 1, overdue_tasks: 0 },
];

const MOCK_WIKI_CONTENT = `# Wiki Ministerial

Bienvenido a la documentación del proyecto.

## Objetivos

- Cumplir con el cronograma establecido
- Mantener comunicación semanal con el equipo
- Documentar cada fase del proyecto

## Recursos

- [Guía de diseño](https://figma.com/...)
- [Calendario](https://calendar.google.com/...)`;

// ── Helper functions ─────────────────────────────────────────────────

export function getMockProjectById(id: string): ProjectRecord | undefined {
  return MOCK_PROJECTS.find((p) => p.id === id);
}

export function getMockTasksByProjectId(projectId: string): ProjectTaskRecord[] {
  return MOCK_TASKS.filter((t) => t.project_id === projectId);
}

export function getMockMilestonesByProjectId(projectId: string): ProjectMilestoneRecord[] {
  return MOCK_MILESTONES[projectId] ?? [];
}

export function getMockCommentsByProjectId(projectId: string): ProjectCommentItem[] {
  return MOCK_COMMENTS.filter((c) => c.project_id === projectId);
}

export function getMockCommentsByTaskId(taskId: string): ProjectCommentItem[] {
  return MOCK_COMMENTS.filter((c) => c.task_id === taskId);
}

export function getMockSuppliesByTaskId(taskId: string): TaskSupplyRecord[] {
  return SUPPLIES_BY_TASK[taskId] ?? [];
}

export function getMockInboxItems(): ProjectInboxItem[] {
  return MOCK_INBOX_ITEMS;
}

export function getMockActivities(projectId?: string): ProjectActivityItem[] {
  if (projectId) return MOCK_ACTIVITIES.filter((a) => a.project_id === projectId);
  return MOCK_ACTIVITIES;
}

// ── Exports ──────────────────────────────────────────────────────────

export {
  MOCK_PROJECTS,
  MOCK_TASKS,
  MOCK_MILESTONES,
  MOCK_COMMENTS,
  MOCK_INBOX_ITEMS,
  MOCK_ACTIVITIES,
  MOCK_PORTFOLIO,
  MOCK_WORKLOAD,
  MOCK_WIKI_CONTENT,
  SUPPLIES_BY_TASK,
  P1_ID,
  P2_ID,
  P3_ID,
  PERSONA_A,
  PERSONA_B,
};
