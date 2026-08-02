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
    // Reset the spy but KEEP it installed (restoreAllMocks would detach it
    // from the module export, breaking every subsequent test in this file).
    apiFetchSpy.mockReset();
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
    expect(result.current.isDirty).toBe(true);
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
    expect(result.current.isDirty).toBe(false);
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
    expect(result.current.isDirty).toBe(false);
  });

  it("keeps isDirty true when a save fails and clears it on the next success", async () => {
    // Fail 4 times (initial + 3 retries)
    apiFetchSpy.mockRejectedValueOnce(new Error("network"));
    apiFetchSpy.mockRejectedValueOnce(new Error("network"));
    apiFetchSpy.mockRejectedValueOnce(new Error("network"));
    apiFetchSpy.mockRejectedValueOnce(new Error("network"));
    apiFetchSpy.mockResolvedValueOnce({ id: "board-1" });
    const canvas = createCanvasMock();

    const { result } = renderHook(() =>
      useWhiteboardSave({ projectId: "project-1", token: "token-1" })
    );

    act(() => {
      result.current.saveNow(canvas);
    });
    expect(result.current.isDirty).toBe(true);

    await act(async () => {
      // Advance enough time and flush microtasks to exhaust all retries
      for (let i = 0; i < 10; i++) {
        vi.advanceTimersByTime(2000);
        await Promise.resolve();
      }
    });
    expect(result.current.saveStatus).toBe("error");
    // Unsaved edits remain dirty after a failure.
    expect(result.current.isDirty).toBe(true);

    act(() => {
      result.current.saveNow(canvas);
    });
    await act(async () => {
      // Flush all timers and microtasks for the successful save to complete
      await vi.runAllTimersAsync();
    });
    // After successful save, status goes to "saved" then "idle" after 2s reset timer
    expect(result.current.saveStatus).toBe("idle");
    expect(result.current.isDirty).toBe(false);
  });

  it("flushPending persists a pending debounced save immediately", async () => {
    apiFetchSpy.mockResolvedValueOnce({ id: "board-1" });
    const canvas = createCanvasMock();

    const { result } = renderHook(() =>
      useWhiteboardSave({ projectId: "project-1", token: "token-1" })
    );

    act(() => {
      result.current.save(canvas);
    });

    expect(apiFetchSpy).not.toHaveBeenCalled();

    act(() => {
      result.current.flushPending();
    });

    expect(apiFetchSpy).toHaveBeenCalledTimes(1);
    expect(apiFetchSpy).toHaveBeenCalledWith("/projects/project-1/whiteboard", {
      method: "POST",
      token: "token-1",
      body: {
        title: "Pizarra Estrategica",
        elements_json: JSON.stringify({ objects: [] }),
      },
    });

    // The canceled debounce timer must not fire a second POST.
    await act(async () => {
      vi.advanceTimersByTime(1000);
      await Promise.resolve();
    });
    expect(apiFetchSpy).toHaveBeenCalledTimes(1);
  });

  it("flushPending is a no-op when nothing is pending", () => {
    const { result } = renderHook(() =>
      useWhiteboardSave({ projectId: "project-1", token: "token-1" })
    );

    act(() => {
      result.current.flushPending();
    });

    expect(apiFetchSpy).not.toHaveBeenCalled();
  });

  it("serializes rapid saves: a newer save is queued until the in-flight one resolves", async () => {
    let resolveFirst!: (value: unknown) => void;
    apiFetchSpy.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveFirst = resolve;
        })
    );
    apiFetchSpy.mockResolvedValueOnce({ id: "board-1" });

    const canvas1 = createCanvasMock();
    const canvas2 = createCanvasMock();
    const { result } = renderHook(() =>
      useWhiteboardSave({ projectId: "project-1", token: "token-1" })
    );

    act(() => {
      result.current.saveNow(canvas1);
    });
    act(() => {
      result.current.saveNow(canvas2);
    });

    // Only the first request starts; the second is queued (ordered writes).
    expect(apiFetchSpy).toHaveBeenCalledTimes(1);

    await act(async () => {
      resolveFirst({});
      await Promise.resolve();
    });

    expect(apiFetchSpy).toHaveBeenCalledTimes(2);

    await act(async () => {
      await Promise.resolve();
    });
  });
});
