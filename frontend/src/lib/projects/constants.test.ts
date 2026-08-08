import { describe, it, expect } from "vitest";

import {
  TASK_STATUSES,
  TASK_PRIORITIES,
  TASK_NODES,
  NODE_LABELS,
  NODE_OPTIONS,
  getNodeOption,
  getNodeLabel,
  DEFAULT_TASK_STATUS,
  DEFAULT_TASK_PRIORITY,
  STATUS_LABELS,
  PRIORITY_LABELS,
  STATUS_CYCLE,
  PRIORITY_CYCLE,
  STATUS_OPTIONS,
  getStatusOption,
  buildStatusOptions,
  PRIORITY_OPTIONS,
  getPriorityOption,
  STATUS_GROUP_PILL,
  getValidStatus,
  getValidPriority,
  PROJECT_STATUSES,
  DEFAULT_PROJECT_STATUS,
  PROJECT_STATUS_LABELS,
  getValidProjectStatus,
} from "./constants";
import type { PhaseDef } from "@/context/ProjectUpdateContext";

describe("projects/constants — enums canónicos", () => {
  it("TASK_STATUSES son los 4 valores esperados, en orden", () => {
    expect([...TASK_STATUSES]).toEqual(["todo", "in_progress", "review", "completed"]);
  });
  it("TASK_PRIORITIES son 4 valores esperados, en orden", () => {
    expect([...TASK_PRIORITIES]).toEqual(["low", "medium", "high", "urgent"]);
  });
  it("TASK_NODES son 2 valores esperados, en orden", () => {
    expect([...TASK_NODES]).toEqual(["nutrition", "digital"]);
  });
  it("PROJECT_STATUSES son 5 valores esperados, en orden", () => {
    expect([...PROJECT_STATUSES]).toEqual([
      "planning",
      "active",
      "on_hold",
      "completed",
      "archived",
    ]);
  });
});

describe("projects/constants — defaults", () => {
  it("DEFAULT_TASK_STATUS = 'todo'", () => {
    expect(DEFAULT_TASK_STATUS).toBe("todo");
  });
  it("DEFAULT_TASK_PRIORITY = 'medium'", () => {
    expect(DEFAULT_TASK_PRIORITY).toBe("medium");
  });
  it("DEFAULT_PROJECT_STATUS = 'planning'", () => {
    expect(DEFAULT_PROJECT_STATUS).toBe("planning");
  });
});

describe("projects/constants — labels", () => {
  it("NODE_LABELS tiene entrada por cada TaskNode", () => {
    TASK_NODES.forEach((n) => {
      expect(typeof NODE_LABELS[n]).toBe("string");
      expect(NODE_LABELS[n].length).toBeGreaterThan(0);
    });
    expect(NODE_LABELS.nutrition).toBe("Nodo de Nutrición");
    expect(NODE_LABELS.digital).toBe("Nodo Digital");
  });
  it("STATUS_LABELS mapea todos los TaskStatus", () => {
    expect(STATUS_LABELS).toEqual({
      todo: "Pendiente",
      in_progress: "En Progreso",
      review: "En Revisión",
      completed: "Completado",
    });
  });
  it("PRIORITY_LABELS mapea todos los TaskPriority", () => {
    expect(PRIORITY_LABELS).toEqual({
      low: "Baja",
      medium: "Media",
      high: "Alta",
      urgent: "Urgente",
    });
  });
  it("PROJECT_STATUS_LABELS mapea todos los ProjectStatus", () => {
    expect(PROJECT_STATUS_LABELS).toEqual({
      planning: "Planificación",
      active: "Activo",
      on_hold: "En Pausa",
      completed: "Completado",
      archived: "Archivado",
    });
  });
  it("STATUS_GROUP_PILL tiene entrada para cada TaskStatus", () => {
    TASK_STATUSES.forEach((s) => {
      expect(typeof STATUS_GROUP_PILL[s]).toBe("string");
      expect(STATUS_GROUP_PILL[s].length).toBeGreaterThan(0);
    });
  });
});

describe("projects/constants — cycles", () => {
  it("STATUS_CYCLE replica TASK_STATUSES (orden)", () => {
    expect(STATUS_CYCLE).toEqual([...TASK_STATUSES]);
    expect(STATUS_CYCLE.length).toBe(4);
  });
  it("PRIORITY_CYCLE replica TASK_PRIORITIES (orden)", () => {
    expect(PRIORITY_CYCLE).toEqual([...TASK_PRIORITIES]);
    expect(PRIORITY_CYCLE.length).toBe(4);
  });
});

describe("projects/constants — opciones visuales (NODE/STATUS/PRIORITY_OPTIONS)", () => {
  it("NODE_OPTIONS tiene uno por TaskNode y value coincide", () => {
    expect(NODE_OPTIONS.length).toBe(TASK_NODES.length);
    TASK_NODES.forEach((n) => {
      expect(NODE_OPTIONS.find((o) => o.value === n)).toBeDefined();
    });
    expect(NODE_OPTIONS[0].value).toBe("nutrition");
    expect(NODE_OPTIONS[0].short).toBe("Nutrición");
    expect(NODE_OPTIONS[1].value).toBe("digital");
  });
  it("STATUS_OPTIONS tiene 4 entradas, una por TaskStatus", () => {
    expect(STATUS_OPTIONS.length).toBe(TASK_STATUSES.length);
    TASK_STATUSES.forEach((s) => {
      expect(STATUS_OPTIONS.find((o) => o.value === s)).toBeDefined();
    });
  });
  it("PRIORITY_OPTIONS tiene 4 entradas, una por TaskPriority", () => {
    expect(PRIORITY_OPTIONS.length).toBe(TASK_PRIORITIES.length);
    TASK_PRIORITIES.forEach((p) => {
      expect(PRIORITY_OPTIONS.find((o) => o.value === p)).toBeDefined();
    });
    expect(PRIORITY_OPTIONS[0].value).toBe("low");
    expect(PRIORITY_OPTIONS[1].value).toBe("medium");
    expect(PRIORITY_OPTIONS[1].fill).toContain("primary");
  });
});

describe("projects/constants — getNodeOption", () => {
  it.each(["nutrition", "digital"] as const)("value válido → option (%s)", (val) => {
    const opt = getNodeOption(val);
    expect(opt).toBeDefined();
    expect(opt!.value).toBe(val);
  });
  it("value inválido → undefined", () => {
    expect(getNodeOption("xyz")).toBeUndefined();
  });
  it("null → undefined", () => {
    expect(getNodeOption(null)).toBeUndefined();
  });
  it("undefined → undefined", () => {
    expect(getNodeOption(undefined)).toBeUndefined();
  });
  it("string vacío → undefined", () => {
    expect(getNodeOption("")).toBeUndefined();
  });
});

describe("projects/constants — getNodeLabel", () => {
  it("value válido → label del nodo", () => {
    expect(getNodeLabel("nutrition")).toBe("Nodo de Nutrición");
    expect(getNodeLabel("digital")).toBe("Nodo Digital");
  });
  it("value inválido → 'Sin nodo'", () => {
    expect(getNodeLabel("xyz")).toBe("Sin nodo");
  });
  it("null → 'Sin nodo'", () => {
    expect(getNodeLabel(null)).toBe("Sin nodo");
  });
  it("undefined → 'Sin nodo'", () => {
    expect(getNodeLabel(undefined)).toBe("Sin nodo");
  });
});

describe("projects/constants — getStatusOption", () => {
  it.each([...TASK_STATUSES])("value válido → option (%s)", (val) => {
    const opt = getStatusOption(val);
    expect(opt.value).toBe(val);
  });
  it("value inválido → fallback al primero (todo)", () => {
    expect(getStatusOption("xyz").value).toBe(STATUS_OPTIONS[0].value);
  });
  it("string vacío → fallback al primero", () => {
    expect(getStatusOption("").value).toBe(STATUS_OPTIONS[0].value);
  });
});

describe("projects/constants — getPriorityOption", () => {
  it.each([...TASK_PRIORITIES])("value válido → option (%s)", (val) => {
    const opt = getPriorityOption(val);
    expect(opt.value).toBe(val);
  });
  it("value inválido → fallback al índice 1 (medium)", () => {
    expect(getPriorityOption("xyz").value).toBe("medium");
  });
  it("string vacío → fallback a medium", () => {
    expect(getPriorityOption("").value).toBe("medium");
  });
});

describe("projects/constants — buildStatusOptions (dynamic phases)", () => {
  const phases: PhaseDef[] = [
    { slug: "kickoff", name: "Kick-off", color: "#ff0000", order_index: 0 },
    { slug: "build", name: "Construcción", color: "#00ff00", order_index: 1 },
  ];
  it("phases vacías → STATUS_OPTIONS canónico", () => {
    expect(buildStatusOptions(undefined)).toBe(STATUS_OPTIONS);
    expect(buildStatusOptions(null!)).toBe(STATUS_OPTIONS);
    expect(buildStatusOptions([])).toBe(STATUS_OPTIONS);
  });
  it("phases no-vacías → mapea a StatusOption[]", () => {
    const out = buildStatusOptions(phases);
    expect(out.length).toBe(2);
    expect(out[0]).toEqual({
      value: "kickoff",
      label: "Kick-off",
      dot: "",
      dotStyle: { backgroundColor: "#ff0000" },
      bg: expect.any(String),
      text: expect.any(String),
      border: expect.any(String),
    });
    expect(out[1].value).toBe("build");
    expect(out[1].dotStyle?.backgroundColor).toBe("#00ff00");
  });
  it("fase con color inválido → igualmente lo pasa", () => {
    const out = buildStatusOptions([{ slug: "p", name: "P", color: "", order_index: 0 }]);
    expect(out[0].dotStyle?.backgroundColor).toBe("");
  });
});

describe("projects/constants — getValidStatus (fallback DEFAULT_TASK_STATUS)", () => {
  it.each([...TASK_STATUSES])("status válido returna mismo (%s)", (val) => {
    expect(getValidStatus(val)).toBe(val);
  });
  it("status inválido → 'todo'", () => {
    expect(getValidStatus("xyz")).toBe(DEFAULT_TASK_STATUS);
  });
  it("null → 'todo'", () => {
    expect(getValidStatus(null)).toBe(DEFAULT_TASK_STATUS);
  });
  it("undefined → 'todo'", () => {
    expect(getValidStatus(undefined)).toBe(DEFAULT_TASK_STATUS);
  });
  it("string vacío → 'todo'", () => {
    expect(getValidStatus("")).toBe(DEFAULT_TASK_STATUS);
  });
});

describe("projects/constants — getValidPriority (fallback DEFAULT_TASK_PRIORITY)", () => {
  it.each([...TASK_PRIORITIES])("prioridad válida returna misma (%s)", (val) => {
    expect(getValidPriority(val)).toBe(val);
  });
  it("prioridad inválida → 'medium'", () => {
    expect(getValidPriority("xyz")).toBe(DEFAULT_TASK_PRIORITY);
  });
  it("null → 'medium'", () => {
    expect(getValidPriority(null)).toBe(DEFAULT_TASK_PRIORITY);
  });
  it("undefined → 'medium'", () => {
    expect(getValidPriority(undefined)).toBe(DEFAULT_TASK_PRIORITY);
  });
});

describe("projects/constants — getValidProjectStatus (fallback DEFAULT_PROJECT_STATUS)", () => {
  it.each([...PROJECT_STATUSES])("ProjectStatus válido returna mismo (%s)", (val) => {
    expect(getValidProjectStatus(val)).toBe(val);
  });
  it("ProjectStatus inválido → 'planning'", () => {
    expect(getValidProjectStatus("xyz")).toBe(DEFAULT_PROJECT_STATUS);
  });
  it("null → 'planning'", () => {
    expect(getValidProjectStatus(null)).toBe(DEFAULT_PROJECT_STATUS);
  });
  it("undefined → 'planning'", () => {
    expect(getValidProjectStatus(undefined)).toBe(DEFAULT_PROJECT_STATUS);
  });
  it("string vacío → 'planning'", () => {
    expect(getValidProjectStatus("")).toBe(DEFAULT_PROJECT_STATUS);
  });
});
