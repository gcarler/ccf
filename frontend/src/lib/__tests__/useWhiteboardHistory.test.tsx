import { renderHook, act, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { Canvas } from "fabric";
import { useWhiteboardHistory } from "@/hooks/useWhiteboardHistory";

function createCanvasMock() {
  let version = 1;
  return {
    toJSON: vi.fn(() => ({ version })),
    loadFromJSON: vi.fn().mockResolvedValue(undefined),
    renderAll: vi.fn(),
    setVersion(next: number) {
      version = next;
    },
  } as unknown as Canvas & { setVersion: (next: number) => void };
}

describe("useWhiteboardHistory", () => {
  it("keeps only the configured snapshot window", async () => {
    const canvas = createCanvasMock();
    const { result } = renderHook(() => useWhiteboardHistory({ maxStates: 3 }));

    for (let i = 1; i <= 4; i += 1) {
      canvas.setVersion(i);
      act(() => {
        result.current.pushHistory(canvas);
      });
    }

    expect(result.current.canUndo).toBe(true);

    await act(async () => {
      result.current.undo(canvas);
    });

    await waitFor(() => {
      expect(canvas.loadFromJSON).toHaveBeenCalledTimes(1);
    });

    const loadFromJSON = canvas.loadFromJSON as unknown as ReturnType<typeof vi.fn>;
    expect(loadFromJSON.mock.calls[0][0]).toEqual({ version: 3 });

    await act(async () => {
      result.current.undo(canvas);
    });

    await waitFor(() => {
      expect(canvas.loadFromJSON).toHaveBeenCalledTimes(2);
    });

    expect(loadFromJSON.mock.calls[1][0]).toEqual({ version: 2 });

    await act(async () => {
      result.current.undo(canvas);
    });

    expect(canvas.loadFromJSON).toHaveBeenCalledTimes(2);
  });

  it("truncates redo history after a new snapshot is pushed", async () => {
    const canvas = createCanvasMock();
    const { result } = renderHook(() => useWhiteboardHistory({ maxStates: 5 }));

    for (let i = 1; i <= 3; i += 1) {
      canvas.setVersion(i);
      act(() => {
        result.current.pushHistory(canvas);
      });
    }

    await act(async () => {
      result.current.undo(canvas);
    });

    await waitFor(() => {
      expect(result.current.canRedo).toBe(true);
    });

    canvas.setVersion(4);
    act(() => {
      result.current.pushHistory(canvas);
    });

    expect(result.current.canRedo).toBe(false);

    await act(async () => {
      result.current.redo(canvas);
    });

    expect(canvas.loadFromJSON).toHaveBeenCalledTimes(1);
  });
});
