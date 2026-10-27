import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { apiFetch } from "@/lib/http";
import { AgendaEventResources } from "./AgendaEventResources";

vi.mock("@/lib/http", () => ({ apiFetch: vi.fn() }));
vi.mock("sonner", () => ({ toast: { error: vi.fn() } }));
const resource = { id: "r1", name: "Sala principal", resource_type: "sala", capacity: 30, is_active: true };
const reservation = { id: "b1", event_id: "e1", resource_id: "r1", starts_at: "2026-07-28T10:00:00Z", ends_at: "2026-07-28T12:00:00Z" };

describe("Agenda event resources", () => {
  beforeEach(() => { vi.mocked(apiFetch).mockReset(); });
  it("announces independent loading states", () => {
    vi.mocked(apiFetch).mockImplementation(() => new Promise(() => undefined));
    render(<AgendaEventResources eventId="e1" token="token" />);
    expect(screen.getByRole("status", { name: "Cargando recursos" })).toBeInTheDocument();
    expect(screen.getByRole("status", { name: "Cargando reservas" })).toBeInTheDocument();
  });
  it("joins reservations to the canonical resource inventory and displays capacity and time", async () => {
    vi.mocked(apiFetch).mockImplementation(async url => String(url).endsWith("/resources") ? [resource] : [reservation]);
    render(<AgendaEventResources eventId="e1" token="token" />);
    const resources = screen.getByRole("region", { name: "Recursos disponibles" });
    expect(await within(resources).findByText("Capacidad: 30")).toBeInTheDocument();
    expect(within(resources).getByText("sala")).toBeInTheDocument();
    const reservations = screen.getByRole("region", { name: "Reservas del evento" });
    expect(await within(reservations).findByText("Sala principal")).toBeInTheDocument();
    expect(reservations.querySelector('time[datetime="2026-07-28T10:00:00Z"]')).toBeInTheDocument();
    expect(apiFetch).toHaveBeenCalledWith("/agenda/events/e1/reservations", { token: "token", cache: "no-store" });
  });
  it("distinguishes successful empty collections", async () => {
    vi.mocked(apiFetch).mockResolvedValue([]);
    render(<AgendaEventResources eventId="e1" token="token" />);
    expect(await screen.findByText("No hay recursos disponibles.")).toBeInTheDocument();
    expect(screen.getByText("No hay reservas para este evento.")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
  it("keeps reservations visible when resources fail and retries only the failed collection", async () => {
    let resourceCalls = 0;
    vi.mocked(apiFetch).mockImplementation(async url => {
      if (String(url).endsWith("/resources")) {
        if (++resourceCalls === 1) throw new Error("offline");
        return [resource];
      }
      return [reservation];
    });
    render(<AgendaEventResources eventId="e1" token="token" />);
    expect(await screen.findByRole("alert")).toHaveTextContent("No se pudieron cargar los recursos.");
    expect(screen.getByText("Recurso no disponible")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Reintentar recursos" }));
    await waitFor(() => expect(screen.queryByRole("alert")).not.toBeInTheDocument());
    expect(within(screen.getByRole("region", { name: "Reservas del evento" })).getByText("Sala principal")).toBeInTheDocument();
    expect(vi.mocked(apiFetch).mock.calls.filter(([url]) => String(url).includes("/reservations"))).toHaveLength(1);
  });
});
