import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiFetch } from "@/lib/http";
import { useCalendarData } from "./useCalendarData";

vi.mock("@/lib/http", () => ({ apiFetch: vi.fn() }));

describe("calendar data recovery", () => {
  beforeEach(() => { vi.mocked(apiFetch).mockReset(); });
  it("exposes a failed request and clears the error after a successful retry", async () => {
    vi.mocked(apiFetch).mockRejectedValueOnce(new Error("offline")).mockResolvedValueOnce([
      { id: "e1", title: "Reunión", start: "2026-07-28T10:00:00Z", type: "agenda_event" },
    ]);
    const { result } = renderHook(() => useCalendarData({ token: "token", calendarView: "todo" }));
    await waitFor(() => expect(result.current.error).toBe("No se pudieron cargar los datos del calendario."));
    expect(result.current.loading).toBe(false);
    await act(async () => { await result.current.refresh(); });
    expect(result.current.error).toBeNull();
    expect(result.current.events[0].title).toBe("Reunión");
    expect(result.current.events[0].start).toBeInstanceOf(Date);
  });
  it("treats a successful empty response as an empty calendar", async () => {
    vi.mocked(apiFetch).mockResolvedValue([]);
    const { result } = renderHook(() => useCalendarData({ token: "token", calendarView: "todo" }));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.events).toEqual([]);
    expect(result.current.error).toBeNull();
  });
});
