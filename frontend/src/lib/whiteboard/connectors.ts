/**
 * Whiteboard connector system — arrows, anchors, and arrowhead rendering.
 *
 * Connectors are stored as fabric.Line objects with custom `data` holding
 * the connection metadata. Arrowheads and anchor indicators are drawn
 * natively via the canvas `after:render` callback so they always stay in
 * sync with the viewport without needing extra Fabric objects.
 */

import * as fabric from "fabric";

// Fabric.js v6 runtime supports `data` on every object but the shipped
// type declarations don't include it.  This augmentation adds it globally.
declare module "fabric" {
  interface FabricObject {
    data?: Record<string, unknown>;
  }
}

// ═══════════════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════════════

export type AnchorPosition = "top" | "right" | "bottom" | "left";

export interface ConnectorData {
  type: "connector";
  connectorId: string;
  fromShapeId: string;
  toShapeId: string;
  fromAnchor: AnchorPosition;
  toAnchor: AnchorPosition;
  label?: string;
}

// ═══════════════════════════════════════════════════════════════════════
// ID generators
// ═══════════════════════════════════════════════════════════════════════

export function generateShapeId(): string {
  return `s_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`;
}

export function generateConnectorId(): string {
  return `c_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`;
}

// ═══════════════════════════════════════════════════════════════════════
// Anchor‑point geometry (object‑space coordinates)
// ═══════════════════════════════════════════════════════════════════════

/**
 * Return the anchor‑point position in the same coordinate space as
 * `obj.left / obj.top` (i.e. scene coordinates, before viewport xform).
 */
export function getAnchorPoint(
  obj: fabric.FabricObject,
  anchor: AnchorPosition,
): { x: number; y: number } {
  const w = (obj.width || 0) * (obj.scaleX || 1);
  const h = (obj.height || 0) * (obj.scaleY || 1);
  const l = obj.left || 0;
  const t = obj.top || 0;

  switch (anchor) {
    case "top":
      return { x: l + w / 2, y: t };
    case "bottom":
      return { x: l + w / 2, y: t + h };
    case "left":
      return { x: l, y: t + h / 2 };
    case "right":
      return { x: l + w, y: t + h / 2 };
  }
}

/** Find the nearest anchor on `obj` to a given scene‑space point. */
export function findNearestAnchor(
  obj: fabric.FabricObject,
  point: { x: number; y: number },
): { anchor: AnchorPosition; point: { x: number; y: number }; distance: number } {
  const anchors: AnchorPosition[] = ["top", "right", "bottom", "left"];
  let best: AnchorPosition = "top";
  let bestDist = Infinity;
  let bestPt = { x: 0, y: 0 };

  for (const a of anchors) {
    const p = getAnchorPoint(obj, a);
    const d = Math.hypot(p.x - point.x, p.y - point.y);
    if (d < bestDist) {
      bestDist = d;
      best = a;
      bestPt = p;
    }
  }

  return { anchor: best, point: bestPt, distance: bestDist };
}

// ═══════════════════════════════════════════════════════════════════════
// Shape lookup helpers
// ═══════════════════════════════════════════════════════════════════════

export function findShapeById(
  canvas: fabric.Canvas,
  id: string,
): fabric.FabricObject | undefined {
  return canvas.getObjects().find((o) => o.data?.shapeId === id);
}

/**
 * Find the connectable shape whose nearest anchor is closest to `point`.
 * Returns null if nothing is within `threshold` pixels.
 */
export function findShapeNearPoint(
  canvas: fabric.Canvas,
  point: { x: number; y: number },
  threshold = 28,
): {
  shape: fabric.FabricObject;
  anchor: AnchorPosition;
  anchorPoint: { x: number; y: number };
} | null {
  type Hit = {
    shape: fabric.FabricObject;
    anchor: AnchorPosition;
    anchorPoint: { x: number; y: number };
    dist: number;
  };
  let best: Hit | null = null;

  for (const obj of canvas.getObjects()) {
    if (!obj.data?.shapeId || obj.data?.type === "connector") continue;
    const { anchor, point: ap, distance } = findNearestAnchor(obj, point);
    if (distance < threshold && (!best || distance < best.dist)) {
      best = { shape: obj, anchor, anchorPoint: ap, dist: distance };
    }
  }

  return best
    ? { shape: best.shape, anchor: best.anchor, anchorPoint: best.anchorPoint }
    : null;
}

// ═══════════════════════════════════════════════════════════════════════
// Connector CRUD
// ═══════════════════════════════════════════════════════════════════════

/**
 * Create a connector Line between two shapes.
 * The Line is *not* added to the canvas — the caller must do that.
 */
export function createConnectorLine(
  canvas: fabric.Canvas,
  fromShapeId: string,
  toShapeId: string,
  fromAnchor: AnchorPosition,
  toAnchor: AnchorPosition,
  opts: { color?: string; strokeWidth?: number; label?: string } = {},
): fabric.Line | null {
  const fromObj = findShapeById(canvas, fromShapeId);
  const toObj = findShapeById(canvas, toShapeId);
  if (!fromObj || !toObj) return null;

  const from = getAnchorPoint(fromObj, fromAnchor);
  const to = getAnchorPoint(toObj, toAnchor);

  const line = new fabric.Line([from.x, from.y, to.x, to.y], {
    stroke: opts.color || "#2563eb",
    strokeWidth: opts.strokeWidth || 2,
    fill: "transparent",
    selectable: true,
    evented: true,
    hasBorders: false,
    hasControls: false,
    lockMovementX: true,
    lockMovementY: true,
    perPixelTargetFind: true,
    padding: 8, // easier click‑target
    hoverCursor: "pointer",
  });

  line.data = {
    type: "connector",
    connectorId: generateConnectorId(),
    fromShapeId,
    toShapeId,
    fromAnchor,
    toAnchor,
    label: opts.label,
  };

  return line;
}

/**
 * Recalculate endpoints of every connector on the canvas so they
 * follow the shapes they're attached to.
 */
export function updateConnectors(canvas: fabric.Canvas): void {
  for (const obj of canvas.getObjects()) {
    if (obj.data?.type !== "connector") continue;
    const d = obj.data as unknown as ConnectorData;
    const fromObj = findShapeById(canvas, d.fromShapeId);
    const toObj = findShapeById(canvas, d.toShapeId);
    if (!fromObj || !toObj) continue;

    const from = getAnchorPoint(fromObj, d.fromAnchor);
    const to = getAnchorPoint(toObj, d.toAnchor);
    const line = obj as fabric.Line;
    line.set({ x1: from.x, y1: from.y, x2: to.x, y2: to.y });
    line.setCoords();
  }
}

/**
 * Assign a `data.shapeId` to every object on the canvas that doesn't
 * have one yet (e.g. shapes loaded from a pre‑connector‑era save).
 */
export function ensureShapeIds(canvas: fabric.Canvas): void {
  for (const obj of canvas.getObjects()) {
    if (obj.data?.type === "connector") continue;
    if (!obj.data) obj.data = {};
    if (!obj.data.shapeId) {
      obj.data.shapeId = generateShapeId();
    }
  }
}

// ═══════════════════════════════════════════════════════════════════════
// Rendering helpers (called from canvas after:render)
// ═══════════════════════════════════════════════════════════════════════

/** Transform a scene‑space point to screen (canvas‑element) space. */
function toScreen(x: number, y: number, vpt: number[]): { x: number; y: number } {
  return {
    x: x * vpt[0] + y * vpt[2] + vpt[4],
    y: x * vpt[1] + y * vpt[3] + vpt[5],
  };
}

/** Draw arrowheads + labels for every connector. */
export function renderArrowheads(
  canvas: fabric.Canvas,
  ctx: CanvasRenderingContext2D,
): void {
  const vpt = canvas.viewportTransform || [1, 0, 0, 1, 0, 0];

  for (const obj of canvas.getObjects()) {
    if (obj.data?.type !== "connector") continue;
    const line = obj as fabric.Line;
    if (line.x1 == null || line.y1 == null || line.x2 == null || line.y2 == null) continue;

    const p1 = toScreen(line.x1, line.y1, vpt);
    const p2 = toScreen(line.x2, line.y2, vpt);
    const angle = Math.atan2(p2.y - p1.y, p2.x - p1.x);
    const headLen = 13;
    const spread = Math.PI / 7;

    // ── Arrow tip ──
    ctx.save();
    ctx.beginPath();
    ctx.moveTo(p2.x, p2.y);
    ctx.lineTo(p2.x - headLen * Math.cos(angle - spread), p2.y - headLen * Math.sin(angle - spread));
    ctx.lineTo(p2.x - headLen * Math.cos(angle + spread), p2.y - headLen * Math.sin(angle + spread));
    ctx.closePath();
    ctx.fillStyle = (line.stroke as string) || "#2563eb";
    ctx.fill();
    ctx.restore();

    // ── Label ──
    const data = obj.data as unknown as ConnectorData;
    if (data.label) {
      const mx = (p1.x + p2.x) / 2;
      const my = (p1.y + p2.y) / 2;
      ctx.save();
      ctx.font = "600 11px 'Inter', sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      const tw = ctx.measureText(data.label).width;
      const pad = 5;
      // pill background
      ctx.fillStyle = "rgba(255,255,255,0.94)";
      ctx.beginPath();
      ctx.roundRect(mx - tw / 2 - pad, my - 8, tw + pad * 2, 16, 6);
      ctx.fill();
      ctx.strokeStyle = "rgba(0,0,0,0.06)";
      ctx.lineWidth = 0.5;
      ctx.stroke();
      // text
      ctx.fillStyle = "#334155";
      ctx.fillText(data.label, mx, my);
      ctx.restore();
    }
  }
}

/** Draw anchor dots on shapes when the connector tool is active. */
export function renderAnchors(
  canvas: fabric.Canvas,
  ctx: CanvasRenderingContext2D,
  opts: {
    hoveredShapeId?: string | null;
    connectingFromId?: string | null;
  } = {},
): void {
  const vpt = canvas.viewportTransform || [1, 0, 0, 1, 0, 0];
  const positions: AnchorPosition[] = ["top", "right", "bottom", "left"];

  for (const obj of canvas.getObjects()) {
    if (!obj.data?.shapeId || obj.data?.type === "connector") continue;

    const id = obj.data.shapeId as string;
    const show =
      id === opts.hoveredShapeId ||
      id === opts.connectingFromId ||
      canvas.getActiveObject() === obj;
    if (!show) continue;

    const isFrom = id === opts.connectingFromId;

    for (const anchor of positions) {
      const p = getAnchorPoint(obj, anchor);
      const sp = toScreen(p.x, p.y, vpt);

      ctx.save();
      // outer glow
      ctx.beginPath();
      ctx.arc(sp.x, sp.y, 9, 0, Math.PI * 2);
      ctx.fillStyle = isFrom ? "rgba(16,185,129,0.18)" : "rgba(37,99,235,0.14)";
      ctx.fill();
      // ring
      ctx.beginPath();
      ctx.arc(sp.x, sp.y, 6, 0, Math.PI * 2);
      ctx.strokeStyle = isFrom ? "#10b981" : "#2563eb";
      ctx.lineWidth = 2;
      ctx.stroke();
      // center
      ctx.beginPath();
      ctx.arc(sp.x, sp.y, 2.5, 0, Math.PI * 2);
      ctx.fillStyle = isFrom ? "#10b981" : "#2563eb";
      ctx.fill();
      ctx.restore();
    }
  }
}
