/**
 * Snap‑to‑grid and smart alignment guides for the whiteboard.
 */

// ═══════════════════════════════════════════════════════════════════════
// Snap to grid
// ═══════════════════════════════════════════════════════════════════════

export function snapToGrid(value: number, gridSize: number): number {
  return Math.round(value / gridSize) * gridSize;
}

/**
 * Snap a Fabric object's position to the nearest grid intersection.
 * Call from within the `object:moving` event handler.
 */
export function applySnapToGrid(
  target: { left?: number; top?: number; set: (props: Record<string, unknown>) => void },
  gridSize: number,
): void {
  target.set({
    left: snapToGrid(target.left || 0, gridSize),
    top: snapToGrid(target.top || 0, gridSize),
  });
}

// ═══════════════════════════════════════════════════════════════════════
// Smart alignment guides
// ═══════════════════════════════════════════════════════════════════════

export interface Guide {
  orientation: "h" | "v";
  position: number; // x for vertical, y for horizontal
}

/**
 * Calculate alignment guides for the active object against all other objects.
 * Returns guides that are within `threshold` pixels of alignment.
 */
export function calculateGuides(
  active: { left: number; top: number; width: number; height: number; scaleX: number; scaleY: number },
  others: Array<{ left: number; top: number; width: number; height: number; scaleX: number; scaleY: number }>,
  threshold = 6,
): { guides: Guide[]; snapX: number | null; snapY: number | null } {
  const aw = active.width * (active.scaleX || 1);
  const ah = active.height * (active.scaleY || 1);
  const acx = active.left + aw / 2;
  const acy = active.top + ah / 2;
  const ar = active.left + aw;
  const ab = active.top + ah;

  const guides: Guide[] = [];
  let snapX: number | null = null;
  let snapY: number | null = null;

  for (const o of others) {
    const ow = o.width * (o.scaleX || 1);
    const oh = o.height * (o.scaleY || 1);
    const ocx = o.left + ow / 2;
    const ocy = o.top + oh / 2;
    const or_ = o.left + ow;
    const ob = o.top + oh;

    // Vertical guides (snap X)
    const vChecks = [
      { activeVal: active.left, otherVal: o.left },       // left-left
      { activeVal: active.left, otherVal: ocx },           // left-center
      { activeVal: active.left, otherVal: or_ },           // left-right
      { activeVal: acx,         otherVal: ocx },           // center-center
      { activeVal: ar,          otherVal: o.left },        // right-left
      { activeVal: ar,          otherVal: ocx },           // right-center
      { activeVal: ar,          otherVal: or_ },           // right-right
    ];

    for (const { activeVal, otherVal } of vChecks) {
      if (Math.abs(activeVal - otherVal) < threshold) {
        guides.push({ orientation: "v", position: otherVal });
        if (snapX === null) snapX = active.left + (otherVal - activeVal);
      }
    }

    // Horizontal guides (snap Y)
    const hChecks = [
      { activeVal: active.top, otherVal: o.top },          // top-top
      { activeVal: active.top, otherVal: ocy },            // top-center
      { activeVal: active.top, otherVal: ob },             // top-bottom
      { activeVal: acy,        otherVal: ocy },            // center-center
      { activeVal: ab,         otherVal: o.top },          // bottom-top
      { activeVal: ab,         otherVal: ocy },            // bottom-center
      { activeVal: ab,         otherVal: ob },             // bottom-bottom
    ];

    for (const { activeVal, otherVal } of hChecks) {
      if (Math.abs(activeVal - otherVal) < threshold) {
        guides.push({ orientation: "h", position: otherVal });
        if (snapY === null) snapY = active.top + (otherVal - activeVal);
      }
    }
  }

  return { guides, snapX, snapY };
}

/**
 * Render alignment guide lines on the canvas.
 * Call from within the `after:render` event handler.
 */
export function renderGuides(
  ctx: CanvasRenderingContext2D,
  guides: Guide[],
  canvasWidth: number,
  canvasHeight: number,
  vpt: number[],
): void {
  if (guides.length === 0) return;

  ctx.save();
  ctx.strokeStyle = "#2563eb";
  ctx.lineWidth = 1;
  ctx.setLineDash([4, 4]);
  ctx.globalAlpha = 0.6;

  const seen = new Set<string>();
  for (const g of guides) {
    const key = `${g.orientation}-${Math.round(g.position)}`;
    if (seen.has(key)) continue;
    seen.add(key);

    ctx.beginPath();
    if (g.orientation === "v") {
      const sx = g.position * vpt[0] + vpt[4];
      ctx.moveTo(sx, 0);
      ctx.lineTo(sx, canvasHeight);
    } else {
      const sy = g.position * vpt[3] + vpt[5];
      ctx.moveTo(0, sy);
      ctx.lineTo(canvasWidth, sy);
    }
    ctx.stroke();
  }

  ctx.restore();
}
