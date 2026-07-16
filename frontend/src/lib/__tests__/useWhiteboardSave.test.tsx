import { renderHook, act } from "@testing-library/react";
import { describe, expect, it, vi, afterEach, beforeEach } from "vitest";
import type { Canvas } from "fabric";
import { useWhiteboardSave } from "@/hooks/useWhiteboardSave";
import * as http from "@/lib/http";

const apiFetchSpy = vi.spyOn(http, "apiFetch");

function createCanvasMock() {
  return {
    toJSON: vi.fn(() => ({ objects: [] })),
  } as unknown as Canvas;
}

describe("useWhiteboardSave", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.clearAllTimers();
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("debounces saves and resets status after success", async () => {
    apiFetchSpy.mockResolvedValueOnce({ id: "board-1" });
    const canvas = createCanvasMock();

    const { result } = renderHook(() =>
      useWhiteboardSave({ projectId: "project-1", token: "token-1" })
    );

    act(() => {
      result.current.save(canvas);
    });

    expect(result.current.saveStatus).toBe("saving");
    expect(apiFetchSpy).not.toHaveBeenCalled();

    await act(async () => {
      vi.advanceTimersByTime(1000);
      await Promise.resolve();
    });

    expect(apiFetchSpy).toHaveBeenCalledWith("/projects/project-1/whiteboard", {
      method: "POST",
      token: "token-1",
      body: {
        title: "Pizarra Estrategica",
        elements_json: JSON.stringify({ objects: [] }),
      },
    });

    await act(async () => {
      vi.advanceTimersByTime(2000);
      await Promise.resolve();
    });

    expect(result.current.saveStatus).toBe("idle");
  });

  it("does nothing silently when token is missing", () => {
    const canvas = createCanvasMock();

    const { result } = renderHook(() =>
      useWhiteboardSave({ projectId: "project-1", token: null })
    );

    act(() => {
      result.current.save(canvas);
    });

    expect(apiFetchSpy).not.toHaveBeenCalled();
    expect(result.current.saveStatus).toBe("idle");
  });
});
