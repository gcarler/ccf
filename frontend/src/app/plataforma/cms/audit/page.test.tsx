import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import AuditPage from "./page";

const authMock = vi.hoisted(() => ({ token: "test-token", user: { role: "admin" } }));
vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({ token: authMock.token, user: authMock.user }),
}));

const apiFetchMock = vi.hoisted(() => vi.fn());
vi.mock("@/lib/http", () => ({ apiFetch: apiFetchMock }));

vi.mock("sonner", () => ({ toast: { error: vi.fn(), success: vi.fn() } }));

function makeLog(id: string, overrides: Record<string, unknown> = {}) {
  return {
    id,
    actor_email: "admin@ccf.test",
    actor_role: "ADMINISTRADOR",
    action: "page.create",
    entity_type: "cms_page",
    entity_id: "p1",
    entity_slug: "inicio",
    changes_json: null,
    ip_address: "127.0.0.1",
    severity: "info",
    created_at: "2026-08-01T10:00:00Z",
    ...overrides,
  };
}

describe("AuditPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiFetchMock.mockReset();
  });

  it("muestra 'Cargando...' y luego los registros", async () => {
    apiFetchMock.mockResolvedValueOnce([makeLog("l1")]);
    render(<AuditPage />);
    expect(screen.getByText("Cargando...")).toBeInTheDocument();

    expect(await screen.findByText("admin@ccf.test")).toBeInTheDocument();
    expect(screen.getByText("page.create")).toBeInTheDocument();
    expect(screen.getByText("cms_page")).toBeInTheDocument();
    expect(screen.getByText(/Mostrando 1 registros/)).toBeInTheDocument();
    expect(apiFetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/cms/v2/audit-logs?limit=50&offset=0"),
      { silent: true }
    );
  });

  it("muestra 'Sin registros' cuando no hay datos", async () => {
    apiFetchMock.mockResolvedValueOnce([]);
    render(<AuditPage />);
    expect(await screen.findByText("Sin registros")).toBeInTheDocument();
  });

  it("refiltra al escribir en el filtro de actor", async () => {
    apiFetchMock.mockResolvedValueOnce([makeLog("l1")]);
    render(<AuditPage />);
    await screen.findByText("admin@ccf.test");

    apiFetchMock.mockResolvedValueOnce([]);
    fireEvent.change(screen.getByPlaceholderText("Actor email..."), {
      target: { value: "otro@ccf.test" },
    });

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        expect.stringContaining("actor_email=otro%40ccf.test"),
        { silent: true }
      );
    });
  });

  it("filtra por entidad y severidad en la URL", async () => {
    apiFetchMock.mockResolvedValueOnce([]);
    render(<AuditPage />);
    await screen.findByText("Sin registros");

    apiFetchMock.mockResolvedValueOnce([]);
    fireEvent.change(screen.getByDisplayValue("Todas las entidades"), {
      target: { value: "cms_section" },
    });
    fireEvent.change(screen.getByDisplayValue("Todas"), {
      target: { value: "critical" },
    });

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenLastCalledWith(
        expect.stringContaining("entity_type=cms_section"),
        { silent: true }
      );
      expect(apiFetchMock).toHaveBeenLastCalledWith(
        expect.stringContaining("severity=critical"),
        { silent: true }
      );
    });
  });

  it("habilita paginación cuando hay 50 registros y navega con offset", async () => {
    const logs = Array.from({ length: 50 }, (_, i) => makeLog(`l${i}`, { action: `a${i}` }));
    apiFetchMock.mockResolvedValueOnce(logs);
    render(<AuditPage />);
    await screen.findByText(/Mostrando 50 registros/);

    const next = screen.getByRole("button", { name: "Siguiente" });
    expect(next).not.toBeDisabled();

    apiFetchMock.mockResolvedValueOnce([]);
    fireEvent.click(next);

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenLastCalledWith(
        expect.stringContaining("offset=50"),
        { silent: true }
      );
    });
  });

  it("deshabilita 'Anterior' en la primera página", async () => {
    apiFetchMock.mockResolvedValueOnce([makeLog("l1")]);
    render(<AuditPage />);
    await screen.findByText("admin@ccf.test");
    expect(screen.getByRole("button", { name: "Anterior" })).toBeDisabled();
  });

  it("exporta CSV con los logs actuales", async () => {
    const origCreateObjectURL = URL.createObjectURL;
    const createObjectURL = vi.fn(() => "blob:test");
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    Object.defineProperty(URL, "createObjectURL", { writable: true, value: createObjectURL });

    apiFetchMock.mockResolvedValueOnce([makeLog("l1")]);
    render(<AuditPage />);
    await screen.findByText("admin@ccf.test");

    fireEvent.click(screen.getByRole("button", { name: /Exportar CSV/i }));
    expect(createObjectURL).toHaveBeenCalled();
    expect(clickSpy).toHaveBeenCalled();

    clickSpy.mockRestore();
    Object.defineProperty(URL, "createObjectURL", { writable: true, value: origCreateObjectURL });
  });
});
