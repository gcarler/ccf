import { act, renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { Canvas } from "fabric";

import { useWhiteboardHistory } from "@/hooks/useWhiteboardHistory";

function makeCanvasMock(payload: unknown) {
  return {
    toJSON: vi.fn(() => payload),
    loadFromJSON: vi.fn(),
    renderAll: vi.fn(),
  } as unknown as Canvas;
}

describe("useWhiteboardHistory", () => {
  it("restores the history index if undo restoration fails", async () => {
    const { result } = renderHook(() => useWhiteboardHistory({ maxStates: 5 }));
    const initialCanvas = makeCanvasMock({ version: 1 });
    const secondCanvas = makeCanvasMock({ version: 2 });
    const restoreCanvas = makeCanvasMock({ version: 2 });
    const loadFromJSON = vi.fn().mockRejectedValue(new Error("boom"));
    (restoreCanvas as unknown as { loadFromJSON: typeof loadFromJSON }).loadFromJSON = loadFromJSON;

    act(() => {
      result.current.pushHistory(initialCanvas);
      result.current.pushHistory(secondCanvas);
    });

    await act(async () => {
      result.current.undo(restoreCanvas);
      await Promise.resolve();
    });

    expect(loadFromJSON).toHaveBeenCalledTimes(1);
    expect(result.current.canUndo).toBe(true);
    expect(result.current.canRedo).toBe(false);
    expect(restoreCanvas.renderAll).not.toHaveBeenCalled();
  });
});
