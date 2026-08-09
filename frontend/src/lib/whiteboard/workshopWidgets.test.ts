import { describe, it, expect, vi, beforeEach } from "vitest";

const fabricMock = vi.hoisted(() => ({
  Rect: vi.fn((opts: Record<string, unknown>) => ({
    left: 0, top: 0, width: 0, height: 0,
    rx: 0, ry: 0, fill: "", stroke: "", strokeWidth: 0,
    originX: "left", originY: "top",
    ...opts,
  })),
  Text: vi.fn((text: string, opts: Record<string, unknown>) => ({
    left: 0, top: 0, fontSize: 0, fill: "", fontWeight: "",
    originX: "left", originY: "top", fontFamily: "",
    ...opts,
  })),
  Circle: vi.fn((opts: Record<string, unknown>) => ({
    left: 0, top: 0, radius: 0, fill: "", stroke: "",
    strokeWidth: 0, strokeDashArray: [],
    originX: "left", originY: "top",
    ...opts,
  })),
  Group: vi.fn(function (objects: unknown[], options: Record<string, unknown>) {
    return {
      objects,
      left: options.left,
      top: options.top,
      subTargetCheck: options.subTargetCheck,
      interactive: options.interactive,
      data: {} as Record<string, unknown>,
    };
  }),
}));

vi.mock("fabric", () => ({
  Rect: fabricMock.Rect,
  Text: fabricMock.Text,
  Circle: fabricMock.Circle,
  Group: fabricMock.Group,
}));

import { createVoteWidget, createTimerWidget, createReactionWidget } from "./workshopWidgets";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("whiteboard/workshopWidgets — createVoteWidget", () => {
  it("crea Group con 5 objetos (bg, heartChar, border, count, title)", () => {
    const widget = createVoteWidget({ left: 10, top: 20 });
    expect(fabricMock.Group).toHaveBeenCalledTimes(1);
    const [objects, opts] = fabricMock.Group.mock.calls[0] as [unknown[], { left: number; top: number; subTargetCheck: boolean; interactive: boolean; data: unknown }];
    expect(objects).toHaveLength(5);
    expect(opts.left).toBe(10);
    expect(opts.top).toBe(20);
    expect(opts.subTargetCheck).toBe(true);
    expect(opts.interactive).toBe(true);
    expect(widget.data).toEqual(expect.objectContaining({
      shapeId: expect.any(String),
      shapeType: "vote-widget",
      votes: 1,
    }));
  });

  it("usa color y label por defecto", () => {
    createVoteWidget({ left: 0, top: 0 });
    // heartChar fill = default color #ef4444
    const heartCall = fabricMock.Text.mock.calls.find((c) => c[0] === "❤");
    expect(heartCall).toBeDefined();
    expect(heartCall![1].fill).toBe("#ef4444");
    // title text = "Votar"
    const titleCall = fabricMock.Text.mock.calls.find((c) => c[0] === "Votar");
    expect(titleCall).toBeDefined();
  });

  it("respeta color y label personalizados", () => {
    createVoteWidget({ left: 0, top: 0, label: "Custom", color: "#ff0000" });
    const heartCall = fabricMock.Text.mock.calls.find((c) => c[0] === "❤");
    expect(heartCall![1].fill).toBe("#ff0000");
    const titleCall = fabricMock.Text.mock.calls.find((c) => c[0] === "Custom");
    expect(titleCall).toBeDefined();
  });

  it("bg Rect con propiedades esperadas", () => {
    createVoteWidget({ left: 5, top: 10 });
    const bgCall = fabricMock.Rect.mock.calls.find((c) => c[0].width === 150 && c[0].height === 56);
    expect(bgCall).toBeDefined();
    expect(bgCall![0].rx).toBe(14);
    expect(bgCall![0].ry).toBe(14);
    expect(bgCall![0].fill).toBe("#ffffff");
    expect(bgCall![0].stroke).toBe("#e2e8f0");
    expect(bgCall![0].strokeWidth).toBe(1.5);
  });
});

describe("whiteboard/workshopWidgets — createTimerWidget", () => {
  it("crea Group con 4 objetos (bg, time, hint, ring)", () => {
    const widget = createTimerWidget({ left: 0, top: 0 });
    expect(fabricMock.Group).toHaveBeenCalledTimes(1);
    const [objects] = fabricMock.Group.mock.calls[0] as [unknown[], { data: { shapeType: string; minutes: number } }];
    expect(objects).toHaveLength(4);
    expect(widget.data).toEqual(expect.objectContaining({
      shapeId: expect.any(String),
      shapeType: "timer-widget",
      minutes: 5,
    }));
  });

  it("usa minutes y color por defecto", () => {
    createTimerWidget({ left: 0, top: 0 });
    const timeCall = fabricMock.Text.mock.calls.find((c) => c[0] === "5:00");
    expect(timeCall).toBeDefined();
    expect(timeCall![1].fontSize).toBe(26);
    expect(timeCall![1].fill).toBe("#2563eb");
    // ring Circle con color por defecto
    const ringCall = fabricMock.Circle.mock.calls[0];
    expect(ringCall[0].stroke).toBe("#2563eb");
    expect(ringCall[0].strokeWidth).toBe(3);
  });

  it("respeta minutes y color personalizados", () => {
    createTimerWidget({ left: 0, top: 0, minutes: 10, color: "#ff0000" });
    const timeCall = fabricMock.Text.mock.calls.find((c) => c[0] === "10:00");
    expect(timeCall).toBeDefined();
    expect(timeCall![1].fill).toBe("#ff0000");
    const ringCall = fabricMock.Circle.mock.calls[0];
    expect(ringCall[0].stroke).toBe("#ff0000");
  });

  it("bg Rect propiedades esperadas", () => {
    createTimerWidget({ left: 0, top: 0 });
    const bgCall = fabricMock.Rect.mock.calls.find((c) => c[0].width === 150 && c[0].height === 62);
    expect(bgCall).toBeDefined();
    expect(bgCall![0].fill).toBe("#eff6ff");
    expect(bgCall![0].stroke).toBe("#bfdbfe");
  });

  it("hint Text con texto esperado", () => {
    createTimerWidget({ left: 0, top: 0 });
    const hintCall = fabricMock.Text.mock.calls.find((c) => c[0] === "min⁻ caja para contar");
    expect(hintCall).toBeDefined();
  });
});

describe("whiteboard/workshopWidgets — createReactionWidget", () => {
  it("crea Group con 3 objetos (bg, stamp, text)", () => {
    const widget = createReactionWidget({ left: 0, top: 0 });
    expect(fabricMock.Group).toHaveBeenCalledTimes(1);
    const [objects] = fabricMock.Group.mock.calls[0] as [unknown[], { data: { shapeType: string; emoji: string } }];
    expect(objects).toHaveLength(3);
    expect(widget.data).toEqual(expect.objectContaining({
      shapeId: expect.any(String),
      shapeType: "reaction-widget",
      emoji: "👍",
    }));
  });

  it("usa emoji y label por defecto", () => {
    createReactionWidget({ left: 0, top: 0 });
    const stampCall = fabricMock.Text.mock.calls.find((c) => c[0] === "👍");
    expect(stampCall).toBeDefined();
    const textCall = fabricMock.Text.mock.calls.find((c) => c[0] === "Reacción");
    expect(textCall).toBeDefined();
  });

  it("respeta emoji y label personalizados", () => {
    createReactionWidget({ left: 0, top: 0, emoji: "🔥", label: "Fuego" });
    const stampCall = fabricMock.Text.mock.calls.find((c) => c[0] === "🔥");
    expect(stampCall).toBeDefined();
    const textCall = fabricMock.Text.mock.calls.find((c) => c[0] === "Fuego");
    expect(textCall).toBeDefined();
  });

  it("bg Rect propiedades esperadas", () => {
    createReactionWidget({ left: 0, top: 0 });
    const bgCall = fabricMock.Rect.mock.calls.find((c) => c[0].width === 130 && c[0].height === 56);
    expect(bgCall).toBeDefined();
    expect(bgCall![0].rx).toBe(16);
    expect(bgCall![0].ry).toBe(16);
    expect(bgCall![0].fill).toBe("#f8fafc");
    expect(bgCall![0].stroke).toBe("#e2e8f0");
  });
});

describe("whiteboard/workshopWidgets — newShapeId (internal)", () => {
  it("genera IDs únicos", () => {
    // Podemos testear indirectamente que cada widget genera shapeId distinto
    const w1 = createVoteWidget({ left: 0, top: 0 });
    const w2 = createVoteWidget({ left: 0, top: 0 });
    expect(w1.data!.shapeId).not.toBe(w2.data!.shapeId);
  });
});