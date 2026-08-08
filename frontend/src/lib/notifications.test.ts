import { describe, it, expect } from "vitest";

import {
  inferNotificationKind,
  toUiNotification,
  isRecentNotification,
  formatNotificationTime,
  type BackendNotification,
} from "./notifications";

describe("notifications — inferNotificationKind", () => {
  it("'ai' cuando contiene 'optimus'", () => {
    expect(inferNotificationKind("optimus generó insight external")).toBe("ai");
  });
  it("'ai' con 'mesh'", () => {
    expect(inferNotificationKind("mesh nuevo análisis", "")).toBe("ai");
  });
  it("'ai' con 'insight' (en content)", () => {
    expect(inferNotificationKind("x", "tu insight del día")).toBe("ai");
  });
  it("'mention' con '@'", () => {
    expect(inferNotificationKind("@carlos mencionó algo")).toBe("mention");
  });
  it("'mention' con 'mencion'", () => {
    expect(inferNotificationKind("te mencioné")).toBe("mention");
  });
  it("'comment' con 'comentario'", () => {
    expect(inferNotificationKind("nuevo comentario en tu post")).toBe("comment");
  });
  it("'task' con 'tarea'", () => {
    expect(inferNotificationKind("tarea creada")).toBe("task");
  });
  it("'task' con 'task' (en content)", () => {
    expect(inferNotificationKind("x", "new task available")).toBe("task");
  });
  it("'task' con 'asignad' (p.ej. 'asignada')", () => {
    expect(inferNotificationKind("estás asignada para esto")).toBe("task");
  });
  it("'reminder' con 'recordatorio'", () => {
    expect(inferNotificationKind("recordatorio: reunión hoy")).toBe("reminder");
  });
  it("'reminder' con 'reunion' (sin acento)", () => {
    expect(inferNotificationKind("reunion agendada")).toBe("reminder");
  });
  it("'reminder' con 'evento'", () => {
    expect(inferNotificationKind("evento cancelado")).toBe("reminder");
  });
  it("'system' fallback cuando no hay keyword", () => {
    expect(inferNotificationKind("algo default")).toBe("system");
  });
  it("case-insensitive (mayúsculas)", () => {
    expect(inferNotificationKind("TASK CREATED")).toBe("task");
    expect(inferNotificationKind("OPTIMUS")).toBe("ai");
  });
  it("ai gana sobre otras keyword (prioridad)", () => {
    expect(inferNotificationKind("mesh te mencionó @x")).toBe("ai");
    expect(inferNotificationKind("insight sobre tarea")).toBe("ai");
  });
  it("content undefined → usa sólo title", () => {
    expect(inferNotificationKind("sin contexto")).toBe("system");
  });
  it("ambos vacíos → system", () => {
    expect(inferNotificationKind("")).toBe("system");
  });
});

describe("notifications — toUiNotification", () => {
  const base: BackendNotification = {
    id: "n1",
    title: "Nueva tarea pendiente",
    content: "Te asignaron una task",
    is_read: false,
    created_at: "2024-01-01T00:00:00Z",
  };
  it("mapea campos y mapea kind + module", () => {
    const out = toUiNotification(base);
    expect(out.id).toBe("n1");
    expect(out.title).toBe("Nueva tarea pendiente");
    expect(out.body).toBe("Te asignaron una task");
    expect(out.read).toBe(false);
    expect(out.createdAt).toBe("2024-01-01T00:00:00Z");
    expect(out.kind).toBe("task");
    expect(out.module).toBe("Tareas");
  });
  it("content null → body vacío string", () => {
    const out = toUiNotification({ ...base, content: null });
    expect(out.body).toBe("");
  });
  it("content undefined → body vacío string", () => {
    const out = toUiNotification({ ...base, content: undefined });
    expect(out.body).toBe("");
  });
  it("is_read=true → read=true", () => {
    const out = toUiNotification({ ...base, is_read: true });
    expect(out.read).toBe(true);
  });
  it.each([
    ["mention", "Colaboracion"],
    ["comment", "Comentarios"],
    ["task", "Tareas"],
    ["system", "Sistema"],
    ["ai", "MESH AI"],
    ["reminder", "Agenda"],
  ] as const)("kind '%s' → module '%s'", (kind, expectedModule) => {
    const titles: Record<string, [string, string]> = {
      mention: ["mencionado @x", ""],
      comment: ["comentario nuevo", ""],
      task: ["tarea X", ""],
      system: ["info", ""],
      ai: ["mesh insight", ""],
      reminder: ["reunion", ""],
    };
    const [t, c] = titles[kind];
    const out = toUiNotification({ ...base, title: t, content: c });
    expect(out.kind).toBe(kind);
    expect(out.module).toBe(expectedModule);
  });
});

describe("notifications — isRecentNotification", () => {
  const NOW = new Date("2024-06-01T12:00:00Z").getTime();
  it("dentro de 24h → true", () => {
    expect(isRecentNotification("2024-06-01T00:00:00Z", NOW)).toBe(true);
  });
  it("justo en el límite 24h (23:59) → true", () => {
    const ts = new Date("2024-05-31T12:01:00Z").toISOString();
    expect(isRecentNotification(ts, NOW)).toBe(true);
  });
  it("exactamente fuera de 24h → false", () => {
    expect(isRecentNotification("2024-05-31T11:59:00Z", NOW)).toBe(false);
  });
  it("futuro → true (timestamp menor a now)", () => {
    expect(isRecentNotification("2024-06-01T13:00:00Z", NOW)).toBe(true);
  });
  it("string inválido → false", () => {
    expect(isRecentNotification("not-a-date", NOW)).toBe(false);
  });
  it("string vacío → false", () => {
    expect(isRecentNotification("", NOW)).toBe(false);
  });
  it("usa now por defecto (~now) → true para ahora", () => {
    const out = isRecentNotification(new Date().toISOString());
    expect(out).toBe(true);
  });
});

describe("notifications — formatNotificationTime", () => {
  const NOW = new Date("2024-06-01T12:00:00Z").getTime();
  it("menos de 30s → 'Ahora' (Math.round(0.5)=1 sube a 1 mín)", () => {
    const ts = new Date(NOW - 10_000).toISOString();
    expect(formatNotificationTime(ts, NOW)).toBe("Ahora");
  });
  it("exactamente 0 min (futuro) → 'Ahora'", () => {
    const ts = new Date(NOW + 10_000).toISOString();
    expect(formatNotificationTime(ts, NOW)).toBe("Ahora");
  });
  it("1 min → 'Hace 1 min'", () => {
    const ts = new Date(NOW - 60_000).toISOString();
    expect(formatNotificationTime(ts, NOW)).toBe("Hace 1 min");
  });
  it("59 min → 'Hace 59 min'", () => {
    const ts = new Date(NOW - 59 * 60_000).toISOString();
    expect(formatNotificationTime(ts, NOW)).toBe("Hace 59 min");
  });
  it("60 min → 'Hace 1 h'", () => {
    const ts = new Date(NOW - 60 * 60_000).toISOString();
    expect(formatNotificationTime(ts, NOW)).toBe("Hace 1 h");
  });
  it("más de 23h → 'Hace 23 h'", () => {
    const ts = new Date(NOW - 23 * 60 * 60_000).toISOString();
    expect(formatNotificationTime(ts, NOW)).toBe("Hace 23 h");
  });
  it("entre 24h y 48h → 'Ayer'", () => {
    const ts = new Date(NOW - 24 * 60 * 60_000).toISOString();
    expect(formatNotificationTime(ts, NOW)).toBe("Ayer");
    const ts2 = new Date(NOW - 47 * 60 * 60_000).toISOString();
    expect(formatNotificationTime(ts2, NOW)).toBe("Ayer");
  });
  it("≥48h → formato Intl.DateTimeFormat es-CO (día + mes corto)", () => {
    const ts = new Date("2024-05-30T12:00:00Z").toISOString();
    const out = formatNotificationTime(ts, NOW);
    expect(out).toMatch(/\d{1,2}\s+/);
  });
  it("string inválido → 'Sin fecha'", () => {
    expect(formatNotificationTime("no-date", NOW)).toBe("Sin fecha");
  });
  it("string vacío → 'Sin fecha'", () => {
    expect(formatNotificationTime("", NOW)).toBe("Sin fecha");
  });
});
