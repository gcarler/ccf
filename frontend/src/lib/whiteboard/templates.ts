import type { Canvas } from "fabric";
import * as fabric from "fabric";
import { WHITEBOARD_COLORS } from "@/lib/whiteboards";
import { generateShapeId } from "./connectors";

export interface TemplateInfo {
  id: string;
  name: string;
  description: string;
  icon: string;
  category: "brainstorm" | "planning" | "process" | "strategy" | "meeting";
}

export const WHITEBOARD_TEMPLATES: TemplateInfo[] = [
  { id: "brainstorm", name: "Brainstorming", description: "Lluvia de ideas libre", icon: "🧠", category: "brainstorm" },
  { id: "retro", name: "Retrospectiva", description: "Qué fue bien, qué mejorar, acciones", icon: "🔄", category: "meeting" },
  { id: "process", name: "Mapa de Procesos", description: "Flujo paso a paso con decisiones", icon: "⚙️", category: "process" },
  { id: "okr", name: "OKR", description: "Objetivos y Resultados Clave", icon: "🎯", category: "strategy" },
  { id: "flowchart", name: "Diagrama de Flujo", description: "Flujo ministerial estándar", icon: "🔀", category: "process" },
  { id: "kanban", name: "Board Kanban", description: "Por hacer, En curso, Hecho", icon: "📋", category: "planning" },
  { id: "timeline", name: "Timeline", description: "Línea de tiempo del proyecto", icon: "⏳", category: "planning" },
  { id: "matrix", name: "Matriz Eisenhower", description: "Importante vs Urgente", icon: "📊", category: "planning" },
  { id: "swot", name: "Análisis FODA", description: "Fortalezas, Oportunidades, Debilidades, Amenazas", icon: "🛡️", category: "strategy" },
  { id: "customer_journey", name: "Customer Journey", description: "Mapa de jornada del usuario", icon: "🚶", category: "strategy" },
];

function makeText(text: string, opts: { left: number; top: number; fontSize?: number; fill?: string; fontWeight?: string; width?: number; textAlign?: "left" | "center" | "right"; fontFamily?: string; angle?: number; originX?: "left" | "center" | "right"; originY?: "top" | "center" | "bottom" } = { left: 0, top: 0 }): fabric.IText {
  return new fabric.IText(text, {
    left: opts.left,
    top: opts.top,
    fontSize: opts.fontSize ?? 14,
    fill: opts.fill ?? WHITEBOARD_COLORS.textPrimary,
    fontWeight: opts.fontWeight ?? "normal",
    fontFamily: opts.fontFamily ?? "Inter, sans-serif",
    width: opts.width,
    textAlign: opts.textAlign ?? "left",
    originX: opts.originX ?? "left",
    originY: opts.originY ?? "top",
    angle: opts.angle ?? 0,
    data: { shapeId: generateShapeId(), shapeType: "text" },
  });
}

function makeSticky(text: string, opts: { left: number; top: number; width?: number; height?: number; fill?: string; color?: string } = { left: 0, top: 0 }): fabric.Group {
  const w = opts.width ?? 180;
  const h = opts.height ?? 140;
  const fill = opts.fill ?? "#fef3c7";
  const stroke = opts.color ?? "#f59e0b";

  const body = new fabric.Polygon(
    [
      { x: 0, y: 0 }, { x: w - 16, y: 0 },
      { x: w, y: 16 }, { x: w, y: h },
      { x: 0, y: h },
    ],
    { fill, stroke, strokeWidth: 1.5, originX: "left", originY: "top" }
  );
  const fold = new fabric.Polygon(
    [{ x: w - 16, y: 0 }, { x: w - 16, y: 16 }, { x: w, y: 16 }],
    { fill: "rgba(0,0,0,0.05)", stroke, strokeWidth: 1, originX: "left", originY: "top" }
  );
  const label = new fabric.IText(text, {
    left: 12, top: 12,
    fontSize: 13,
    fill: "#374151",
    fontFamily: "Inter, sans-serif",
    width: w - 24,
    lineHeight: 1.4,
    originX: "left", originY: "top",
  });

  const group = new fabric.Group([body, fold, label], {
    left: opts.left, top: opts.top,
    subTargetCheck: true,
    interactive: true,
  });
  group.data = { shapeId: generateShapeId(), shapeType: "sticky", stickyColor: fill };
  return group;
}

function makeRect(label: string, opts: { left: number; top: number; width?: number; height?: number; fill?: string; stroke?: string; rx?: number; ry?: number } = { left: 0, top: 0 }): fabric.Group {
  const w = opts.width ?? 180;
  const h = opts.height ?? 90;
  const rect = new fabric.Rect({
    width: w, height: h, rx: opts.rx ?? 12, ry: opts.ry ?? 12,
    fill: opts.fill ?? "rgba(37,99,235,0.1)", stroke: opts.stroke ?? WHITEBOARD_COLORS.primary, strokeWidth: 2,
    originX: "center", originY: "center",
  });
  const text = new fabric.IText(label, {
    fontSize: 14, fontWeight: "600", fill: "#1e3a5f",
    fontFamily: "Inter, sans-serif", textAlign: "center",
    originX: "center", originY: "center", width: w - 20,
  });
  const group = new fabric.Group([rect, text], {
    left: opts.left, top: opts.top, subTargetCheck: true, interactive: true,
  });
  group.data = { shapeId: generateShapeId(), shapeType: "rect" };
  return group;
}

function makeDiamond(label: string, opts: { left: number; top: number } = { left: 0, top: 0 }): fabric.Group {
  const s = 110, h = s / 2;
  const diamond = new fabric.Polygon(
    [{ x: h, y: 0 }, { x: s, y: h }, { x: h, y: s }, { x: 0, y: h }],
    { fill: "rgba(245,158,11,0.12)", stroke: WHITEBOARD_COLORS.warning, strokeWidth: 2, originX: "center", originY: "center" }
  );
  const text = new fabric.IText(label, { fontSize: 12, fontWeight: "600", fill: "#92400e", fontFamily: "Inter, sans-serif", textAlign: "center", originX: "center", originY: "center", width: s - 20 });
  const group = new fabric.Group([diamond, text], { left: opts.left, top: opts.top, subTargetCheck: true, interactive: true });
  group.data = { shapeId: generateShapeId(), shapeType: "diamond" };
  return group;
}

function makePill(label: string, opts: { left: number; top: number; fill?: string; stroke?: string } = { left: 0, top: 0 }): fabric.Group {
  const rect = new fabric.Rect({ width: 160, height: 48, rx: 24, ry: 24, fill: opts.fill ?? "rgba(139,92,246,0.1)", stroke: opts.stroke ?? WHITEBOARD_COLORS.lavender, strokeWidth: 2, originX: "center", originY: "center" });
  const text = new fabric.IText(label, { fontSize: 13, fontWeight: "600", fill: "#5b21b6", fontFamily: "Inter, sans-serif", textAlign: "center", originX: "center", originY: "center" });
  const group = new fabric.Group([rect, text], { left: opts.left, top: opts.top, subTargetCheck: true, interactive: true });
  group.data = { shapeId: generateShapeId(), shapeType: "pill" };
  return group;
}

function makeColumnHeader(label: string, opts: { left: number; top: number; width: number }): fabric.Group {
  const rect = new fabric.Rect({ width: opts.width, height: 40, rx: 8, ry: 8, fill: "#e5e7eb", stroke: "#d1d5db", strokeWidth: 1.5, originX: "center", originY: "center" });
  const text = new fabric.IText(label, { fontSize: 13, fontWeight: "700", fill: "#374151", fontFamily: "Inter, sans-serif", textAlign: "center", originX: "center", originY: "center" });
  const group = new fabric.Group([rect, text], { left: opts.left, top: opts.top, subTargetCheck: true, interactive: true });
  group.data = { shapeId: generateShapeId(), shapeType: "column-header" };
  return group;
}

export function applyTemplate(canvas: Canvas, templateId: string) {
  canvas.clear();
  canvas.backgroundColor = "transparent";

  const templates: Record<string, () => fabric.FabricObject[]> = {
    brainstorm: () => createBrainstormTemplate(),
    retro: () => createRetroTemplate(),
    process: () => createProcessTemplate(),
    okr: () => createOKRTemplate(),
    flowchart: () => createFlowchartTemplate(),
    kanban: () => createKanbanTemplate(),
    timeline: () => createTimelineTemplate(),
    matrix: () => createEisenhowerTemplate(),
    swot: () => createSWOTTemplate(),
    customer_journey: () => createCustomerJourneyTemplate(),
  };

  const factory = templates[templateId];
  if (!factory) return;

  const objects = factory();
  objects.forEach(obj => canvas.add(obj));
  canvas.renderAll();
}

function createBrainstormTemplate(): fabric.FabricObject[] {
  const objs: fabric.FabricObject[] = [];
  const centerX = 400, centerY = 300;

  objs.push(makeText("🧠 Brainstorming", { left: centerX - 100, top: centerY - 280, fontSize: 28, fontWeight: "bold", fill: WHITEBOARD_COLORS.primary }));
  objs.push(makeText("Tema central", { left: centerX - 60, top: centerY - 230, fontSize: 16, fill: "#64748b" }));

  const mainCircle = new fabric.Circle({
    left: centerX, top: centerY, radius: 80,
    fill: "rgba(37,99,235,0.1)", stroke: WHITEBOARD_COLORS.primary, strokeWidth: 3,
    originX: "center", originY: "center",
  });
  const mainLabel = new fabric.IText("IDEA\nCENTRAL", { left: centerX, top: centerY, fontSize: 18, fontWeight: "bold", fill: "#1e3a5f", fontFamily: "Inter, sans-serif", textAlign: "center", originX: "center", originY: "center", width: 120 });
  const mainGroup = new fabric.Group([mainCircle, mainLabel], { left: centerX, top: centerY, subTargetCheck: true, interactive: true });
  mainGroup.data = { shapeId: generateShapeId(), shapeType: "brainstorm-center" };
  objs.push(mainGroup);

  const branches = [
    { angle: -135, label: "Idea 1", color: "#2563eb" },
    { angle: -90, label: "Idea 2", color: "#10b981" },
    { angle: -45, label: "Idea 3", color: "#f59e0b" },
    { angle: 45, label: "Idea 4", color: "#8b5cf6" },
    { angle: 90, label: "Idea 5", color: "#ec4899" },
    { angle: 135, label: "Idea 6", color: "#0ea5e9" },
  ];

  branches.forEach((b) => {
    const rad = (b.angle * Math.PI) / 180;
    const x = centerX + Math.cos(rad) * 220;
    const y = centerY + Math.sin(rad) * 220;
    const sticky = makeSticky(b.label, { left: x - 90, top: y - 70, fill: `${b.color}15`, color: b.color });
    objs.push(sticky);

    const line = new fabric.Line([centerX, centerY, x, y], {
      stroke: b.color, strokeWidth: 2, strokeDashArray: [8, 4],
      selectable: false, evented: false,
      originX: "center", originY: "center",
    });
    line.data = { shapeId: generateShapeId(), shapeType: "connector", fromShapeId: mainGroup.data?.shapeId };
    objs.push(line);
  });

  objs.push(makeText("💡 Agrega más ideas con la herramienta Post-it (N)", { left: centerX - 180, top: centerY + 320, fontSize: 12, fill: "#94a3b8" }));
  return objs;
}

function createRetroTemplate(): fabric.FabricObject[] {
  const objs: fabric.FabricObject[] = [];
  const startX = 150, startY = 120, colW = 320, colH = 500, gap = 40;

  objs.push(makeText("🔄 Retrospectiva del Sprint", { left: startX, top: startY - 60, fontSize: 26, fontWeight: "bold", fill: WHITEBOARD_COLORS.primary }));
  objs.push(makeText("¿Qué fue bien?  |  ¿Qué mejorar?  |  Acciones", { left: startX, top: startY - 20, fontSize: 13, fill: "#64748b" }));

  const columns = [
    { id: "went_well", title: "✅ Qué fue bien", color: "#10b981", bg: "#ecfdf5", icon: "👍" },
    { id: "to_improve", title: "🔧 Qué mejorar", color: "#f59e0b", bg: "#fffbeb", icon: "💡" },
    { id: "actions", title: "🚀 Acciones", color: "#2563eb", bg: "#eff6ff", icon: "✅" },
  ];

  columns.forEach((col, i) => {
    const x = startX + i * (colW + gap);
    const y = startY;

    const header = makeColumnHeader(col.title, { left: x + colW / 2, top: y + 20, width: colW });
    objs.push(header);

    const bgRect = new fabric.Rect({
      left: x, top: y + 50, width: colW, height: colH,
      rx: 12, ry: 12, fill: col.bg, stroke: col.color, strokeWidth: 1.5, strokeDashArray: [4, 4],
      originX: "left", originY: "top",
    });
    bgRect.data = { shapeId: generateShapeId(), shapeType: "retro-column", columnId: col.id };
    objs.push(bgRect);

    let sampleStickies = [
      "Equipo colaboró bien",
      "Deploy sin incidencias",
      "Pair programming útil",
    ];
    if (col.id === "to_improve") sampleStickies = ["Reuniones muy largas", "Deuda técnica en auth", "Faltan tests E2E"];
    if (col.id === "actions") sampleStickies = ["Acortar dailies a 15min", "Refactor auth module", "Añadir tests críticos"];

    sampleStickies.forEach((text, j) => {
      const sticky = makeSticky(text, {
        left: x + 20, top: y + 70 + j * 110,
        width: colW - 40, height: 90,
        fill: col.bg === "#ecfdf5" ? "#d1fae5" : col.bg === "#fffbeb" ? "#fef3c7" : "#dbeafe",
        color: col.color,
      });
      objs.push(sticky);
    });

    const addBtn = makeText(`+ Agregar ${col.icon}`, {
      left: x + 20, top: y + 50 + colH - 50,
      fontSize: 12, fill: col.color, fontWeight: "600",
    });
    addBtn.data = { shapeId: generateShapeId(), shapeType: "add-sticky-btn", columnId: col.id };
    objs.push(addBtn);
  });

  objs.push(makeText("💡 Haz clic en '+' para añadir post-its. Arrastra entre columnas.", { left: startX, top: startY + colH + 80, fontSize: 12, fill: "#94a3b8" }));
  return objs;
}

function createProcessTemplate(): fabric.FabricObject[] {
  const objs: fabric.FabricObject[] = [];
  const startX = 100, startY = 200, stepX = 220;

  objs.push(makeText("⚙️ Mapa de Procesos", { left: startX, top: startY - 80, fontSize: 26, fontWeight: "bold", fill: WHITEBOARD_COLORS.primary }));
  objs.push(makeText("Inicio → Proceso → Decisión → Fin", { left: startX, top: startY - 40, fontSize: 13, fill: "#64748b" }));

  const steps = [
    { type: "pill", label: "Inicio", x: startX, y: startY, fill: "rgba(16,185,129,0.1)", stroke: "#10b981" },
    { type: "process", label: "Recibir\nsolicitud", x: startX + stepX, y: startY },
    { type: "process", label: "Validar\ndatos", x: startX + stepX * 2, y: startY },
    { type: "diamond", label: "¿Válido?", x: startX + stepX * 3, y: startY },
    { type: "process", label: "Procesar", x: startX + stepX * 4, y: startY - 80 },
    { type: "process", label: "Notificar", x: startX + stepX * 5, y: startY - 80 },
    { type: "pill", label: "Fin", x: startX + stepX * 6, y: startY - 80, fill: "rgba(244,63,94,0.1)", stroke: "#f43f5e" },
    { type: "process", label: "Rechazar", x: startX + stepX * 4, y: startY + 80 },
    { type: "pill", label: "Fin", x: startX + stepX * 5, y: startY + 80, fill: "rgba(244,63,94,0.1)", stroke: "#f43f5e" },
  ];

  const shapeMap: Record<string, fabric.FabricObject> = {};
  steps.forEach((s, i) => {
    let shape: fabric.FabricObject;
    if (s.type === "pill") shape = makePill(s.label, { left: s.x, top: s.y, fill: s.fill, stroke: s.stroke });
    else if (s.type === "process") shape = makeRect(s.label, { left: s.x, top: s.y });
    else shape = makeDiamond(s.label, { left: s.x, top: s.y });
    shape.data = { ...shape.data, shapeId: generateShapeId(), stepIndex: i };
    shapeMap[`step${i}`] = shape;
    objs.push(shape);
  });

  const connections = [
    { from: "step0", to: "step1" },
    { from: "step1", to: "step2" },
    { from: "step2", to: "step3" },
    { from: "step3", to: "step4", label: "Sí" },
    { from: "step4", to: "step5" },
    { from: "step5", to: "step6" },
    { from: "step3", to: "step7", label: "No" },
    { from: "step7", to: "step8" },
  ];

  connections.forEach(c => {
    const fromObj = shapeMap[c.from];
    const toObj = shapeMap[c.to];
    if (!fromObj || !toObj) return;
    const line = new fabric.Line(
      [fromObj.left!, fromObj.top!, toObj.left!, toObj.top!],
      { stroke: "#64748b", strokeWidth: 2, selectable: false, evented: false, strokeLineCap: "round" }
    );
    line.data = { shapeId: generateShapeId(), shapeType: "connector", fromShapeId: fromObj.data?.shapeId, toShapeId: toObj.data?.shapeId, label: c.label };
    objs.push(line);
    if (c.label) {
      const midX = (fromObj.left! + toObj.left!) / 2;
      const midY = (fromObj.top! + toObj.top!) / 2;
      objs.push(makeText(c.label, { left: midX + 10, top: midY - 20, fontSize: 11, fill: "#64748b", fontWeight: "500" }));
    }
  });

  return objs;
}

function createOKRTemplate(): fabric.FabricObject[] {
  const objs: fabric.FabricObject[] = [];
  const startX = 100, startY = 100, objW = 350, objH = 160, gapX = 40;

  objs.push(makeText("🎯 OKR - Objetivos y Resultados Clave", { left: startX, top: startY - 50, fontSize: 26, fontWeight: "bold", fill: WHITEBOARD_COLORS.primary }));
  objs.push(makeText("Trimestre Actual", { left: startX, top: startY - 10, fontSize: 14, fill: "#64748b" }));

  const objectives = [
    { title: "O1: Mejorar experiencia de usuario", krs: ["KR1: NPS ≥ 50", "KR2: Tiempo carga < 2s", "KR3: Tasa rebote < 30%"] },
    { title: "O2: Escalar plataforma", krs: ["KR1: 10k usuarios activos", "KR2: 99.9% uptime", "KR3: < 100ms p95 latency"] },
    { title: "O3: Cultura de excelencia", krs: ["KR1: 0 bugs críticos", "KR2: 80% coverage tests", "KR3: 4 deploy/semana"] },
  ];

  objectives.forEach((obj, i) => {
    const x = startX + i * (objW + gapX);
    const y = startY;

    const card = new fabric.Rect({ left: x, top: y, width: objW, height: objH, rx: 12, ry: 12, fill: "#fafafa", stroke: "#e5e7eb", strokeWidth: 1.5, originX: "left", originY: "top" });
    card.data = { shapeId: generateShapeId(), shapeType: "okr-objective" };
    objs.push(card);

    objs.push(makeText("🎯", { left: x + 16, top: y + 16, fontSize: 20 }));
    objs.push(makeText(obj.title, { left: x + 48, top: y + 16, fontSize: 15, fontWeight: "700", fill: "#111827", width: objW - 64 }));

    obj.krs.forEach((kr, j) => {
      const krY = y + 56 + j * 30;
      objs.push(makeText("📊", { left: x + 16, top: krY, fontSize: 14 }));
      objs.push(makeText(kr, { left: x + 40, top: krY + 1, fontSize: 12, fill: "#374151", width: objW - 56 }));

      const progress = new fabric.Rect({ left: x + 16, top: krY + 20, width: (objW - 32) * (0.3 + j * 0.2), height: 6, rx: 3, ry: 3, fill: WHITEBOARD_COLORS.primary, originX: "left", originY: "top" });
      progress.data = { shapeId: generateShapeId(), shapeType: "okr-progress", value: 0.3 + j * 0.2 };
      objs.push(progress);
      const progressBg = new fabric.Rect({ left: x + 16, top: krY + 20, width: objW - 32, height: 6, rx: 3, ry: 3, fill: "#e5e7eb", originX: "left", originY: "top" });
      progressBg.data = { shapeId: generateShapeId(), shapeType: "okr-progress-bg" };
      objs.splice(objs.indexOf(progress), 0, progressBg);
    });
  });

  return objs;
}

function createFlowchartTemplate(): fabric.FabricObject[] {
  const objs: fabric.FabricObject[] = [];
  const startX = 100, startY = 200, stepX = 220;

  objs.push(makeText("🔀 Diagrama de Flujo Ministerial", { left: startX, top: startY - 80, fontSize: 24, fontWeight: "bold", fill: WHITEBOARD_COLORS.primary }));
  objs.push(makeText("Estándar: Inicio → Proceso → Decisión → Documento → Fin", { left: startX, top: startY - 40, fontSize: 12, fill: "#64748b" }));

  const shapes = [
    { type: "pill", label: "Inicio", x: startX, y: startY },
    { type: "process", label: "Recibir\nDocumento", x: startX + stepX, y: startY },
    { type: "process", label: "Validar\nCampos", x: startX + stepX * 2, y: startY },
    { type: "diamond", label: "¿Completo?", x: startX + stepX * 3, y: startY },
    { type: "process", label: "Registrar\nen Sistema", x: startX + stepX * 4, y: startY - 80 },
    { type: "document", label: "Generar\nAcuse", x: startX + stepX * 5, y: startY - 80 },
    { type: "pill", label: "Archivar", x: startX + stepX * 6, y: startY - 80, fill: "rgba(16,185,129,0.1)", stroke: "#10b981" },
    { type: "process", label: "Solicitar\nCorrección", x: startX + stepX * 4, y: startY + 80 },
    { type: "pill", label: "Devolver", x: startX + stepX * 5, y: startY + 80, fill: "rgba(244,63,94,0.1)", stroke: "#f43f5e" },
  ];

  const shapeObjs: Record<string, fabric.FabricObject> = {};
  shapes.forEach((s, i) => {
    let shape: fabric.FabricObject;
    if (s.type === "pill") shape = makePill(s.label, { left: s.x, top: s.y, fill: s.fill, stroke: s.stroke });
    else if (s.type === "process") shape = makeRect(s.label, { left: s.x, top: s.y });
    else if (s.type === "document") {
      const w = 160, h = 80, wave = 10;
      const pathStr = `M 0 0 L ${w} 0 L ${w} ${h - wave} Q ${w * 0.75} ${h + wave}, ${w * 0.5} ${h - wave} Q ${w * 0.25} ${h - wave * 3}, 0 ${h - wave} Z`;
      const docShape = new fabric.Path(pathStr, { fill: "rgba(14,165,233,0.1)", stroke: "#0ea5e9", strokeWidth: 2, originX: "center", originY: "center" });
      const label = new fabric.IText(s.label, { fontSize: 13, fontWeight: "600", fill: "#0369a1", fontFamily: "Inter, sans-serif", textAlign: "center", originX: "center", originY: "center", width: w - 20 });
      shape = new fabric.Group([docShape, label], { left: s.x, top: s.y, subTargetCheck: true, interactive: true });
    } else shape = makeDiamond(s.label, { left: s.x, top: s.y });
    shape.data = { ...shape.data, shapeId: generateShapeId(), stepIndex: i };
    shapeObjs[`step${i}`] = shape;
    objs.push(shape);
  });

  const connections = [
    { from: "step0", to: "step1" },
    { from: "step1", to: "step2" },
    { from: "step2", to: "step3" },
    { from: "step3", to: "step4", label: "Sí" },
    { from: "step4", to: "step5" },
    { from: "step5", to: "step6" },
    { from: "step3", to: "step7", label: "No" },
    { from: "step7", to: "step8" },
  ];

  connections.forEach(c => {
    const fromObj = shapeObjs[c.from];
    const toObj = shapeObjs[c.to];
    if (!fromObj || !toObj) return;
    const line = new fabric.Line([fromObj.left!, fromObj.top!, toObj.left!, toObj.top!], { stroke: "#64748b", strokeWidth: 2, selectable: false, evented: false });
    line.data = { shapeId: generateShapeId(), shapeType: "connector", fromShapeId: fromObj.data?.shapeId, toShapeId: toObj.data?.shapeId, label: c.label };
    objs.push(line);
    if (c.label) {
      const midX = (fromObj.left! + toObj.left!) / 2;
      const midY = (fromObj.top! + toObj.top!) / 2;
      objs.push(makeText(c.label, { left: midX + 10, top: midY - 20, fontSize: 11, fill: "#64748b", fontWeight: "500" }));
    }
  });

  return objs;
}

function createKanbanTemplate(): fabric.FabricObject[] {
  const objs: fabric.FabricObject[] = [];
  const startX = 80, startY = 100, colW = 280, colH = 520, gap = 30;

  objs.push(makeText("📋 Board Kanban", { left: startX, top: startY - 50, fontSize: 26, fontWeight: "bold", fill: WHITEBOARD_COLORS.primary }));

  const columns = [
    { id: "backlog", title: "📥 Backlog", color: "#64748b", bg: "#f8fafc", items: ["Investigar nueva API", "Actualizar docs", "Refactor login", "Añadir tests unitarios"] },
    { id: "todo", title: "📋 Por Hacer", color: "#2563eb", bg: "#eff6ff", items: ["Diseñar pantalla perfil", "Implementar auth", "Crear API usuarios"] },
    { id: "in_progress", title: "⚙️ En Curso", color: "#f59e0b", bg: "#fffbeb", items: ["Fix bug #234", "Code review PR #45"] },
    { id: "review", title: "👀 En Revisión", color: "#8b5cf6", bg: "#faf5ff", items: ["Deploy staging", "Validar métricas"] },
    { id: "done", title: "✅ Hecho", color: "#10b981", bg: "#ecfdf5", items: ["Sprint planning", "Retrospectiva"] },
  ];

  columns.forEach((col, i) => {
    const x = startX + i * (colW + gap);
    const y = startY;

    const header = makeColumnHeader(col.title, { left: x + colW / 2, top: y + 20, width: colW });
    objs.push(header);

    const bgRect = new fabric.Rect({ left: x, top: y + 50, width: colW, height: colH, rx: 12, ry: 12, fill: col.bg, stroke: col.color, strokeWidth: 1.5, strokeDashArray: [4, 4], originX: "left", originY: "top" });
    bgRect.data = { shapeId: generateShapeId(), shapeType: "kanban-column", columnId: col.id };
    objs.push(bgRect);

    col.items.forEach((text, j) => {
      const card = makeRect(text, { left: x + colW / 2, top: y + 70 + j * 105, width: colW - 30, height: 80, fill: "#ffffff", stroke: "#e5e7eb", rx: 8, ry: 8 });
      card.data = { ...card.data, shapeType: "kanban-card", columnId: col.id, order: j };
      objs.push(card);
    });

    const addBtn = makeText("+ Nueva tarjeta", { left: x + 15, top: y + 50 + colH - 35, fontSize: 11, fill: col.color, fontWeight: "600" });
    addBtn.data = { shapeId: generateShapeId(), shapeType: "add-card-btn", columnId: col.id };
    objs.push(addBtn);
  });

  return objs;
}

function createTimelineTemplate(): fabric.FabricObject[] {
  const objs: fabric.FabricObject[] = [];
  const startX = 100, startY = 300, itemW = 200, gap = 60;

  objs.push(makeText("⏳ Timeline del Proyecto", { left: startX, top: startY - 120, fontSize: 26, fontWeight: "bold", fill: WHITEBOARD_COLORS.primary }));
  objs.push(makeText("Hitos y entregables", { left: startX, top: startY - 80, fontSize: 14, fill: "#64748b" }));

  const line = new fabric.Line([startX - 50, startY, startX + 8 * (itemW + gap) + 50, startY], { stroke: "#e5e7eb", strokeWidth: 3, selectable: false, evented: false });
  line.data = { shapeId: generateShapeId(), shapeType: "timeline-axis" };
  objs.push(line);

  const milestones = [
    { date: "Ene 2025", label: "Kickoff", desc: "Inicio proyecto", color: "#2563eb", top: -120 },
    { date: "Feb 2025", label: "Discovery", desc: "Investigación", color: "#8b5cf6", top: 120 },
    { date: "Mar 2025", label: "Diseño", desc: "UI/UX + Arquitectura", color: "#0ea5e9", top: -120 },
    { date: "Abr 2025", label: "Desarrollo", desc: "Sprint 1-3", color: "#f59e0b", top: 120 },
    { date: "May 2025", label: "Testing", desc: "QA + UAT", color: "#ec4899", top: -120 },
    { date: "Jun 2025", label: "Lanzamiento", desc: "Go-live 🚀", color: "#10b981", top: 120 },
    { date: "Jul 2025", label: "Iteración", desc: "Feedback + v2", color: "#6366f1", top: -120 },
    { date: "Ago 2025", label: "Escalado", desc: "Nuevos features", color: "#f43f5e", top: 120 },
  ];

  milestones.forEach((m, i) => {
    const x = startX + i * (itemW + gap) + itemW / 2;
    const circle = new fabric.Circle({ left: x, top: startY, radius: 12, fill: m.color, stroke: "#fff", strokeWidth: 3, originX: "center", originY: "center" });
    circle.data = { shapeId: generateShapeId(), shapeType: "timeline-milestone" };
    objs.push(circle);

    objs.push(makeText(m.date, { left: x - 40, top: startY + 30, fontSize: 11, fontWeight: "600", fill: "#374151", textAlign: "center", width: 80 }));
    objs.push(makeText(m.label, { left: x - itemW / 2, top: startY + m.top - 50, fontSize: 13, fontWeight: "700", fill: m.color, textAlign: "center", width: itemW }));
    objs.push(makeText(m.desc, { left: x - itemW / 2, top: startY + m.top - 30, fontSize: 11, fill: "#6b7280", textAlign: "center", width: itemW }));
  });

  return objs;
}

function createEisenhowerTemplate(): fabric.FabricObject[] {
  const objs: fabric.FabricObject[] = [];
  const startX = 100, startY = 150, cellW = 350, cellH = 280, gap = 30;

  objs.push(makeText("📊 Matriz Eisenhower", { left: startX, top: startY - 70, fontSize: 26, fontWeight: "bold", fill: WHITEBOARD_COLORS.primary }));
  objs.push(makeText("Importante vs Urgente", { left: startX, top: startY - 30, fontSize: 14, fill: "#64748b" }));

  objs.push(makeText("URGENTE →", { left: startX + cellW + gap / 2, top: startY - 50, fontSize: 13, fontWeight: "700", fill: "#ef4444", textAlign: "center", width: cellW }));
  objs.push(makeText("IMPORTANTE", { left: startX - 80, top: startY + cellH / 2 - 10, fontSize: 13, fontWeight: "700", fill: "#22c55e", angle: -90, originX: "center", originY: "center" }));

  const quadrants = [
    { id: "do", x: 0, y: 0, title: "HACER AHORA", desc: "Urgente + Importante", color: "#ef4444", bg: "#fef2f2", items: ["Incidente producción", "Deadline hoy", "Cliente VIP"] },
    { id: "schedule", x: 1, y: 0, title: "PROGRAMAR", desc: "No Urgente + Importante", color: "#22c55e", bg: "#f0fdf4", items: ["Planificación estratégica", "Formación equipo", "Refactoring"] },
    { id: "delegate", x: 0, y: 1, title: "DELEGAR", desc: "Urgente + No Importante", color: "#f59e0b", bg: "#fffbeb", items: ["Reuniones rutinarias", "Emails operativos", "Interrupciones"] },
    { id: "delete", x: 1, y: 1, title: "ELIMINAR", desc: "No Urgente + No Importante", color: "#6b7280", bg: "#f9fafb", items: ["Time-wasters", "Scroll infinito", "Tareas obsoletas"] },
  ];

  quadrants.forEach((q) => {
    const x = startX + q.x * (cellW + gap);
    const y = startY + q.y * (cellH + gap);

    const bg = new fabric.Rect({ left: x, top: y, width: cellW, height: cellH, rx: 12, ry: 12, fill: q.bg, stroke: q.color, strokeWidth: 2, originX: "left", originY: "top" });
    bg.data = { shapeId: generateShapeId(), shapeType: "eisenhower-quadrant", quadrantId: q.id };
    objs.push(bg);

    objs.push(makeText(q.title, { left: x + 20, top: y + 16, fontSize: 15, fontWeight: "800", fill: q.color }));
    objs.push(makeText(q.desc, { left: x + 20, top: y + 40, fontSize: 11, fill: "#6b7280", width: cellW - 40 }));

    q.items.forEach((item, j) => {
      const sticky = makeSticky(item, { left: x + 20, top: y + 65 + j * 60, width: cellW - 40, height: 50, fill: q.bg === "#fef2f2" ? "#fee2e2" : q.bg === "#f0fdf4" ? "#dcfce7" : q.bg === "#fffbeb" ? "#fef3c7" : "#f3f4f6", color: q.color });
      objs.push(sticky);
    });

    const addBtn = makeText("+ Agregar", { left: x + 20, top: y + cellH - 30, fontSize: 11, fill: q.color, fontWeight: "600" });
    addBtn.data = { shapeId: generateShapeId(), shapeType: "add-eisenhower-btn", quadrantId: q.id };
    objs.push(addBtn);
  });

  return objs;
}

function createSWOTTemplate(): fabric.FabricObject[] {
  const objs: fabric.FabricObject[] = [];
  const startX = 80, startY = 120, cellW = 360, cellH = 300, gap = 30;

  objs.push(makeText("🛡️ Análisis FODA / SWOT", { left: startX, top: startY - 60, fontSize: 26, fontWeight: "bold", fill: WHITEBOARD_COLORS.primary }));
  objs.push(makeText("Fortalezas, Oportunidades, Debilidades, Amenazas", { left: startX, top: startY - 20, fontSize: 14, fill: "#64748b" }));

  objs.push(makeText("INTERNO", { left: startX + cellW + gap / 2, top: startY - 50, fontSize: 13, fontWeight: "700", fill: "#2563eb", textAlign: "center", width: cellW }));
  objs.push(makeText("EXTERNO", { left: startX + cellW + gap / 2, top: startY + cellH + gap - 10, fontSize: 13, fontWeight: "700", fill: "#f59e0b", textAlign: "center", width: cellW }));
  objs.push(makeText("POSITIVO", { left: startX - 60, top: startY + cellH / 2, fontSize: 13, fontWeight: "700", fill: "#10b981", angle: -90, originX: "center", originY: "center" }));
  objs.push(makeText("NEGATIVO", { left: startX + cellW * 2 + gap + 60, top: startY + cellH / 2, fontSize: 13, fontWeight: "700", fill: "#ef4444", angle: -90, originX: "center", originY: "center" }));

  const quadrants = [
    { id: "strengths", x: 0, y: 0, title: "FORTALEZAS 💪", color: "#10b981", bg: "#ecfdf5", items: ["Equipo experimentado", "Tecnología propia", "Marca reconocida", "Clientes fieles"] },
    { id: "weaknesses", x: 1, y: 0, title: "DEBILIDADES 📉", color: "#ef4444", bg: "#fef2f2", items: ["Deuda técnica", "Pocos recursos", "Procesos manuales", "Silos de info"] },
    { id: "opportunities", x: 0, y: 1, title: "OPORTUNIDADES 🚀", color: "#2563eb", bg: "#eff6ff", items: ["Nuevo mercado", "IA/Automatización", "Alianzas estratégicas", "Fondos disponibles"] },
    { id: "threats", x: 1, y: 1, title: "AMENAZAS ⚠️", color: "#f59e0b", bg: "#fffbeb", items: ["Competencia agresiva", "Cambios regulatorios", "Rotación talento", "Recesión económica"] },
  ];

  quadrants.forEach((q) => {
    const x = startX + q.x * (cellW + gap);
    const y = startY + q.y * (cellH + gap);

    const bg = new fabric.Rect({ left: x, top: y, width: cellW, height: cellH, rx: 12, ry: 12, fill: q.bg, stroke: q.color, strokeWidth: 2, originX: "left", originY: "top" });
    bg.data = { shapeId: generateShapeId(), shapeType: "swot-quadrant", quadrantId: q.id };
    objs.push(bg);

    objs.push(makeText(q.title, { left: x + 20, top: y + 16, fontSize: 16, fontWeight: "800", fill: q.color }));

    q.items.forEach((item, j) => {
      const sticky = makeSticky(item, { left: x + 20, top: y + 50 + j * 55, width: cellW - 40, height: 45, fill: "#ffffff", color: q.color });
      objs.push(sticky);
    });

    const addBtn = makeText("+ Agregar", { left: x + 20, top: y + cellH - 30, fontSize: 11, fill: q.color, fontWeight: "600" });
    addBtn.data = { shapeId: generateShapeId(), shapeType: "add-swot-btn", quadrantId: q.id };
    objs.push(addBtn);
  });

  return objs;
}

function createCustomerJourneyTemplate(): fabric.FabricObject[] {
  const objs: fabric.FabricObject[] = [];
  const startX = 60, startY = 100, stageW = 220, stageH = 380, gap = 20;

  objs.push(makeText("🚶 Customer Journey Map", { left: startX, top: startY - 60, fontSize: 26, fontWeight: "bold", fill: WHITEBOARD_COLORS.primary }));
  objs.push(makeText("Descubrimiento → Consideración → Decisión → Retención → Defensa", { left: startX, top: startY - 20, fontSize: 13, fill: "#64748b" }));

  const stages = [
    { id: "discovery", title: "1️⃣ Descubrimiento", color: "#8b5cf6", bg: "#faf5ff", rows: ["Acciones", "Puntos de contacto", "Emociones", "Oportunidades"], items: [["Busca en Google", "Ve anuncio", "Escucha recomendación"], ["Web, Ads, Social", "Blog, SEO", "Boca a boca"], ["Curiosidad", "Interés", "Confianza"], ["SEO, Content Mktg", "Lead magnet", "Referral program"]] },
    { id: "consideration", title: "2️⃣ Consideración", color: "#0ea5e9", bg: "#f0f9ff", rows: ["Acciones", "Puntos de contacto", "Emociones", "Oportunidades"], items: [[ "Compara opciones", "Lee reviews", "Pide demo" ], [ "Web, Comparadores", "G2, Capterra", "Sales call" ], [ "Evaluación", "Duda", "Expectativa" ], [ "Case studies", "Free trial", "Demo personalizada" ] ] },
    { id: "decision", title: "3️⃣ Decisión", color: "#10b981", bg: "#ecfdf5", rows: ["Acciones", "Puntos de contacto", "Emociones", "Oportunidades"], items: [[ "Elige plan", "Negocia", "Firma contrato" ], [ "Pricing page", "Email, Call", "DocuSign" ], [ "Confianza", "Alivio", "Compromiso" ], [ "Onboarding guiado", "Welcome pack", "Quick wins" ] ] },
    { id: "retention", title: "4️⃣ Retención", color: "#f59e0b", bg: "#fffbeb", rows: ["Acciones", "Puntos de contacto", "Emociones", "Oportunidades"], items: [[ "Usa producto", "Contacta soporte", "Renueva" ], [ "App, Dashboard", "Chat, Email", "Facturación" ], [ "Satisfacción", "Frustración", "Lealtad" ], [ "Health checks", "Nuevas features", "Comunidad" ] ] },
    { id: "advocacy", title: "5️⃣ Defensa", color: "#ec4899", bg: "#fdf2f8", rows: ["Acciones", "Puntos de contacto", "Emociones", "Oportunidades"], items: [[ "Recomienda", "Escribe review", "Habla en eventos" ], [ "NPS survey", "G2, Twitter", "Conferencias" ], [ "Orgullo", "Pertenencia", "Evangelismo" ], [ "Referral bonus", "Case study", "Programa partners" ] ] },
  ];

  stages.forEach((stage, i) => {
    const x = startX + i * (stageW + gap);
    const y = startY;

    const headerBg = new fabric.Rect({ left: x, top: y, width: stageW, height: 50, rx: 10, ry: 10, fill: stage.color, originX: "left", originY: "top" });
    headerBg.data = { shapeId: generateShapeId(), shapeType: "journey-header" };
    objs.push(headerBg);

    objs.push(makeText(stage.title, { left: x + stageW / 2, top: y + 12, fontSize: 13, fontWeight: "700", fill: "#fff", textAlign: "center" }));

    const gridBg = new fabric.Rect({ left: x, top: y + 50, width: stageW, height: stageH, rx: 0, ry: 0, fill: stage.bg, stroke: "#e5e7eb", strokeWidth: 1, originX: "left", originY: "top" });
    gridBg.data = { shapeId: generateShapeId(), shapeType: "journey-grid" };
    objs.push(gridBg);

    const rowH = stageH / 4;
    stage.rows.forEach((rowLabel, r) => {
      const ry = y + 50 + r * rowH;
      const rowLine = new fabric.Line([x, ry, x + stageW, ry], { stroke: "#e5e7eb", strokeWidth: 0.5, selectable: false, evented: false });
      objs.push(rowLine);
      if (r === 0) {
        objs.push(makeText(rowLabel, { left: x + 8, top: ry + 4, fontSize: 10, fontWeight: "700", fill: stage.color, width: 80 }));
      }

      stage.items[r].forEach((item, c) => {
        const cx = x + 8 + (c % 1) * (stageW - 16);
        const cy = ry + 20;
        const sticky = makeSticky(item, { left: cx, top: cy, width: stageW - 16, height: rowH - 24, fill: "#ffffff", color: stage.color });
        objs.push(sticky);
      });
    });
  });

  return objs;
}