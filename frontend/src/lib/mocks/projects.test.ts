import { describe, it, expect } from "vitest";

import {
  getMockProjectById,
  getMockTasksByProjectId,
  getMockMilestonesByProjectId,
  getMockCommentsByProjectId,
  getMockCommentsByTaskId,
  getMockSuppliesByTaskId,
  getMockInboxItems,
  getMockActivities,
  MOCK_PROJECTS,
  MOCK_TASKS,
  MOCK_COMMENTS,
  MOCK_INBOX_ITEMS,
  MOCK_ACTIVITIES,
  MOCK_MILESTONES,
  SUPPLIES_BY_TASK,
  P1_ID,
  P2_ID,
  P3_ID,
} from "./projects";

const TASK_T1 = "11111111-1111-4111-8111-111111111001";
const TASK_T3 = "11111111-1111-4111-8111-111111111003";

describe("mocks/projects — coherencia de datos base", () => {
  it("3 proyectos con IDs exportados P1/P2/P3", () => {
    expect(MOCK_PROJECTS.length).toBe(3);
    expect(MOCK_PROJECTS.map((p) => p.id).sort()).toEqual(
      [P1_ID, P2_ID, P3_ID].sort(),
    );
  });
  it("IDs de proyectos son únicos", () => {
    const ids = MOCK_PROJECTS.map((p) => p.id);
    expect(new Set(ids).size).toBe(ids.length);
  });
  it("7 tareas, todas con project_id válido (de los 3 proyectos)", () => {
    expect(MOCK_TASKS.length).toBe(7);
    const validIds = new Set([P1_ID, P2_ID, P3_ID]);
    MOCK_TASKS.forEach((t) => {
      expect(validIds.has(t.project_id), t.id).toBe(true);
    });
  });
  it("comentarios referencian project_id válido o task_id existente", () => {
    const taskIds = new Set(MOCK_TASKS.map((t) => t.id));
    const projectIds = new Set([P1_ID, P2_ID, P3_ID]);
    MOCK_COMMENTS.forEach((c) => {
      if (c.project_id) expect(projectIds.has(c.project_id), c.id).toBe(true);
      if (c.task_id) expect(taskIds.has(c.task_id), c.id).toBe(true);
    });
  });
  it("MILESTONES está indexado por project_id (no por task_id)", () => {
    const projectIds = new Set([P1_ID, P2_ID, P3_ID]);
    Object.keys(MOCK_MILESTONES).forEach((key) => {
      expect(projectIds.has(key), key).toBe(true);
    });
  });
  it("SUPPLIES_BY_TASK keys son taskId existentes", () => {
    const taskIds = new Set(MOCK_TASKS.map((t) => t.id));
    Object.keys(SUPPLIES_BY_TASK).forEach((key) => {
      expect(taskIds.has(key), key).toBe(true);
    });
  });
  it("todas las keys de MILESTONES y SUPPLIES no vacías", () => {
    Object.values(MOCK_MILESTONES).forEach((arr) => expect(arr.length).toBeGreaterThan(0));
    Object.values(SUPPLIES_BY_TASK).forEach((arr) => expect(arr.length).toBeGreaterThan(0));
  });
});

describe("mocks/projects — getMockProjectById", () => {
  it("busca proyecto por ID exacto", () => {
    expect(getMockProjectById(P1_ID)?.id).toBe(P1_ID);
    expect(getMockProjectById(P2_ID)?.id).toBe(P2_ID);
    expect(getMockProjectById(P3_ID)?.id).toBe(P3_ID);
  });
  it("ID inexistente → undefined", () => {
    expect(getMockProjectById("no-existe")).toBeUndefined();
  });
  it("string vacío → undefined", () => {
    expect(getMockProjectById("")).toBeUndefined();
  });
});

describe("mocks/projects — getMockTasksByProjectId", () => {
  it("P1 tiene ≥ 3 tareas (T1, T2, T3 visibles)", () => {
    const tasks = getMockTasksByProjectId(P1_ID);
    expect(tasks.length).toBeGreaterThanOrEqual(3);
    expect(tasks.map((t) => t.id)).toContain(TASK_T1);
    expect(tasks.map((t) => t.id)).toContain(TASK_T3);
  });
  it("todas las tareas retornadas pertenecen al projectId", () => {
    const tasks = getMockTasksByProjectId(P1_ID);
    tasks.forEach((t) => expect(t.project_id).toBe(P1_ID));
  });
  it("projectId inexistente → arreglo vacío", () => {
    expect(getMockTasksByProjectId("no-existe")).toEqual([]);
  });
  it("sumando tareas por proyecto = total MOCK_TASKS", () => {
    const t1 = getMockTasksByProjectId(P1_ID).length;
    const t2 = getMockTasksByProjectId(P2_ID).length;
    const t3 = getMockTasksByProjectId(P3_ID).length;
    expect(t1 + t2 + t3).toBe(MOCK_TASKS.length);
  });
});

describe("mocks/projects — getMockMilestonesByProjectId", () => {
  it("P1 tiene 3 milestones (MVP, Diseño, Lanzamiento)", () => {
    const ms = getMockMilestonesByProjectId(P1_ID);
    expect(ms.length).toBe(3);
    expect(ms.map((m) => m.title).sort()).toEqual(
      ["Diseño aprobado", "Lanzamiento", "MVP v1.0"].sort(),
    );
  });
  it("P2 tiene 2 milestones", () => {
    expect(getMockMilestonesByProjectId(P2_ID).length).toBe(2);
  });
  it("P3 tiene 1 milestone", () => {
    expect(getMockMilestonesByProjectId(P3_ID).length).toBe(1);
  });
  it("projectId inexistente → arreglo vacío (NO undefined)", () => {
    expect(getMockMilestonesByProjectId("no-existe")).toEqual([]);
  });
  it("todos los milestones retornados tienen project_id correcto", () => {
    const ms = getMockMilestonesByProjectId(P2_ID);
    ms.forEach((m) => expect(m.project_id).toBe(P2_ID));
  });
});

describe("mocks/projects — getMockCommentsByProjectId", () => {
  it("filtra comentarios por project_id", () => {
    const comments = getMockCommentsByProjectId(P1_ID);
    expect(comments.length).toBeGreaterThan(0);
    comments.forEach((c) => expect(c.project_id).toBe(P1_ID));
  });
  it("projectId inexistente → arreglo vacío", () => {
    expect(getMockCommentsByProjectId("no-existe")).toEqual([]);
  });
  it("P3 (o el que no tenga comentarios) → []", () => {
    const out = getMockCommentsByProjectId(P3_ID);
    expect(Array.isArray(out)).toBe(true);
  });
});

describe("mocks/projects — getMockCommentsByTaskId", () => {
  it("T1 tiene al menos un comentario", () => {
    const comments = getMockCommentsByTaskId(TASK_T1);
    expect(comments.length).toBeGreaterThan(0);
    comments.forEach((c) => expect(c.task_id).toBe(TASK_T1));
  });
  it("taskId inexistente → arreglo vacío", () => {
    expect(getMockCommentsByTaskId("no-existe")).toEqual([]);
  });
});

describe("mocks/projects — getMockSuppliesByTaskId", () => {
  it("T1 tiene 2 supplies (Hosting, Dominio)", () => {
    const supplies = getMockSuppliesByTaskId(TASK_T1);
    expect(supplies.length).toBe(2);
    expect(supplies.map((s) => s.item_name).sort()).toEqual(
      ["Dominio .com", "Hosting mensual"].sort(),
    );
  });
  it("T3 tiene 1 supply (Figma Pro)", () => {
    const supplies = getMockSuppliesByTaskId(TASK_T3);
    expect(supplies.length).toBe(1);
    expect(supplies[0].item_name).toBe("Cuenta Figma Pro");
  });
  it("taskId inexistente → arreglo vacío (NO undefined)", () => {
    expect(getMockSuppliesByTaskId("no-existe")).toEqual([]);
  });
  it("todas las supplies tienen task_id correcto", () => {
    const supplies = getMockSuppliesByTaskId(TASK_T1);
    supplies.forEach((s) => expect(s.task_id).toBe(TASK_T1));
  });
});

describe("mocks/projects — getMockInboxItems", () => {
  it("devuelve el array MOCK_INBOX_ITEMS completo", () => {
    const out = getMockInboxItems();
    expect(out).toBe(MOCK_INBOX_ITEMS);
    expect(out.length).toBe(MOCK_INBOX_ITEMS.length);
  });
  it("no vacío", () => {
    expect(getMockInboxItems().length).toBeGreaterThan(0);
  });
});

describe("mocks/projects — getMockActivities", () => {
  it("sin projectId → todas las actividades", () => {
    const out = getMockActivities();
    expect(out).toEqual(MOCK_ACTIVITIES);
    expect(out.length).toBe(MOCK_ACTIVITIES.length);
  });
  it("con projectId → filtra por project_id", () => {
    const out = getMockActivities(P1_ID);
    expect(out.length).toBeGreaterThan(0);
    out.forEach((a) => expect(a.project_id).toBe(P1_ID));
  });
  it("projectId inexistente → arreglo vacío", () => {
    expect(getMockActivities("no-existe")).toEqual([]);
  });
  it("todas las actividades tienen project_id válido", () => {
    const validIds = new Set([P1_ID, P2_ID, P3_ID]);
    MOCK_ACTIVITIES.forEach((a) => expect(validIds.has(a.project_id)).toBe(true));
  });
});
