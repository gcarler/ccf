import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

// Mock de ToastContext (panel usa addToast).
const addToast = vi.fn();
vi.mock("@/context/ToastContext", () => ({
  useToast: () => ({ addToast }),
}));

// Mock de apiFetch: comportamientos mutables por test.
const { apiFetchMock } = vi.hoisted(() => ({
  apiFetchMock: vi.fn(),
}));
vi.mock("@/lib/http", () => ({
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}));

import NotificationPreferencesPanel from "@/components/messaging/NotificationPreferencesPanel";

function pref(channel: string, eventType: string, enabled: boolean) {
  return {
    id: `${channel}-${eventType}`,
    user_id: "u1",
    channel,
    event_type: eventType,
    enabled,
    created_at: "2026-10-11T00:00:00Z",
    updated_at: "2026-10-11T00:00:00Z",
  };
}

describe("NotificationPreferencesPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("muestra skeleton mientras carga", () => {
    apiFetchMock.mockReturnValue(new Promise(() => {}));
    render(<NotificationPreferencesPanel />);
    expect(document.querySelector('[aria-busy="true"]')).toBeTruthy();
  });

  it("renderiza la tabla de preferencias tras la carga", async () => {
    apiFetchMock.mockResolvedValue({
      preferences: [
        pref("in_app", "task_assigned", true),
        pref("email", "task_assigned", true),
      ],
    });
    render(<NotificationPreferencesPanel />);
    await waitFor(() => expect(apiFetchMock).toHaveBeenCalledWith(
      "/messaging/notifications/preferences",
      { cache: "no-store" }
    ));
    expect(await screen.findByText("Tarea asignada")).toBeTruthy();
    // Headers de canales
    expect(screen.getByText("In-app")).toBeTruthy();
    expect(screen.getByText("Email")).toBeTruthy();
  });

  it("hace PATCH con toggle optimista", async () => {
    apiFetchMock.mockResolvedValueOnce({
      preferences: [
        pref("in_app", "broadcast", true),
        pref("email", "broadcast", false),
      ],
    });
    apiFetchMock.mockResolvedValueOnce(pref("email", "broadcast", true));

    render(<NotificationPreferencesPanel />);
    const switchEl = await screen.findByRole("switch", { name: "Email: Anuncios generales" });
    expect(switchEl.getAttribute("aria-checked")).toBe("false");

    fireEvent.click(switchEl);

    await waitFor(() =>
      expect(apiFetchMock).toHaveBeenCalledWith("/messaging/notifications/preferences", {
        method: "PATCH",
        body: { channel: "email", event_type: "broadcast", enabled: true },
      })
    );
    await waitFor(() => expect(apiFetchMock.mock.calls[0][0]).toBe("/messaging/notifications/preferences"));
    expect(addToast).toHaveBeenCalledWith("Preferencia actualizada", "success");
  });

  it("hace rollback del toggle si el PATCH falla", async () => {
    apiFetchMock.mockResolvedValueOnce({
      preferences: [
        pref("in_app", "broadcast", true),
        pref("email", "broadcast", false),
      ],
    });
    apiFetchMock.mockRejectedValueOnce(new Error("network down"));

    render(<NotificationPreferencesPanel />);
    const switchEl = await screen.findByRole("switch", { name: "Email: Anuncios generales" });
    fireEvent.click(switchEl);

    await waitFor(() => expect(addToast).toHaveBeenCalledWith("No se pudo actualizar la preferencia", "error"));
    // Tras rollback, el switch vuelve a aria-checked=false.
    await waitFor(() => expect(switchEl.getAttribute("aria-checked")).toBe("false"));
  });

  it("muestra estado vacío si no hay preferencias", async () => {
    apiFetchMock.mockResolvedValue({ preferences: [] });
    render(<NotificationPreferencesPanel />);
    expect(
      await screen.findByText(/No hay preferencias de notificación/i)
    ).toBeTruthy();
  });
});
