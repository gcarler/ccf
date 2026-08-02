import * as fabric from "fabric";

/** Generate a short unique id for a widget object. */
function newShapeId(): string {
    return typeof crypto !== "undefined" && crypto.randomUUID
        ? crypto.randomUUID()
        : `w-${Date.now()}-${Math.floor(Math.random() * 1e6)}`;
}

/** Build a simple voting widget (heart + counter). */
export function createVoteWidget(opts: { left: number; top: number; label?: string; color?: string }): fabric.Group {
    const { left, top } = opts;
    const color = opts.color ?? "#ef4444";
    const label = opts.label ?? "Votar";

    const bg = new fabric.Rect({
        left: 0, top: 0, width: 150, height: 56,
        rx: 14, ry: 14,
        fill: "#ffffff",
        stroke: "#e2e8f0",
        strokeWidth: 1.5,
        originX: "left", originY: "top",
    });

    const heartChar = new fabric.Text("❤", {
        left: 12, top: 12, fontSize: 22, fill: color,
        originX: "left", originY: "top",
    });

    const border = new fabric.Rect({
        left: 46, top: 8, width: 42, height: 40,
        rx: 10, ry: 10,
        fill: "#fff7ed",
        stroke: "#fed7aa",
        strokeWidth: 1,
        originX: "left", originY: "top",
    });

    const count = new fabric.Text("1", {
        left: 67, top: 17, fontSize: 18, fontWeight: "bold", fill: "#9a3412",
        originX: "left", originY: "top",
    });

    const title = new fabric.Text(label, {
        left: 96, top: 18, fontSize: 13, fontWeight: "600", fill: "#475569",
        originX: "left", originY: "top",
    });

    const group = new fabric.Group([bg, heartChar, border, count, title], {
        left, top,
        subTargetCheck: true,
        interactive: true,
    });
    group.data = { shapeId: newShapeId(), shapeType: "vote-widget", votes: 1 };
    return group;
}

/** Build a countdown timer widget. */
export function createTimerWidget(opts: { left: number; top: number; minutes?: number; color?: string }): fabric.Group {
    const { left, top } = opts;
    const minutes = opts.minutes ?? 5;
    const color = opts.color ?? "#2563eb";

    const bg = new fabric.Rect({
        left: 0, top: 0, width: 150, height: 62,
        rx: 14, ry: 14, fill: "#eff6ff",
        stroke: "#bfdbfe", strokeWidth: 1.5,
        originX: "left", originY: "top",
    });

    const time = new fabric.Text(`${minutes}:00`, {
        left: 14, top: 10, fontSize: 26, fontWeight: "bold", fill: color,
        originX: "left", originY: "top",
        fontFamily: "Manrope, sans-serif",
    });

    const hint = new fabric.Text("min⁻ caja para contar", {
        left: 14, top: 44, fontSize: 10, fill: "#64748b",
        originX: "left", originY: "top",
    });

    const ring = new fabric.Circle({
        left: 116, top: 12, radius: 20,
        fill: "transparent",
        stroke: color,
        strokeWidth: 3,
        strokeDashArray: [Math.PI * 2 * 20 * 0.75, Math.PI * 2 * 20],
        originX: "left", originY: "top",
    });

    const group = new fabric.Group([bg, time, hint, ring], {
        left, top, subTargetCheck: true, interactive: true,
    });
    group.data = { shapeType: "timer-widget", minutes };
    return group;
}

/** Build a reaction stamp widget (emoji + label). */
export function createReactionWidget(opts: { left: number; top: number; emoji?: string; label?: string }): fabric.Group {
    const { left, top } = opts;
    const emoji = opts.emoji ?? "👍";
    const label = opts.label ?? "Reacción";

    const bg = new fabric.Rect({
        left: 0, top: 0, width: 130, height: 56,
        rx: 16, ry: 16, fill: "#f8fafc",
        stroke: "#e2e8f0", strokeWidth: 1.5,
        originX: "left", originY: "top",
    });

    const stamp = new fabric.Text(emoji, {
        left: 10, top: 10, fontSize: 26,
        originX: "left", originY: "top",
    });

    const text = new fabric.Text(label, {
        left: 48, top: 20, fontSize: 13, fontWeight: "600", fill: "#475569",
        originX: "left", originY: "top",
    });

    const group = new fabric.Group([bg, stamp, text], {
        left, top, subTargetCheck: true, interactive: true,
    });
    group.data = { shapeType: "reaction-widget", emoji };
    return group;
}