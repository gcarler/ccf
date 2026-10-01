import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import AutomationsPage from "./page";
import * as http from "@/lib/http";
import * as authContext from "@/context/AuthContext";

vi.mock("@/context/AuthContext", () => ({
  useAuth: vi.fn(),
}));

vi.mock("@/context/SidebarLayerContext", () => ({
  useSidebarLayers: () => ({
    layers: { RIGHT: false, S2: false },
    openLayer: vi.fn(),
    closeLayer: vi.fn(),
    toggleLayer: vi.fn(),
    closeTopLayer: vi.fn(),
    rightMode: "overlay",
    setRightMode: vi.fn(),
    sidebarStack: [],
    stackDirection: "forward",
  }),
}));

vi.mock("@/lib/http", () => ({
  apiFetch: vi.fn(),
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

vi.mock("@/components/projects/ProjectsShell", () => ({
  default: ({ children }: { children: React.ReactNode }) => <div data-testid="projects-shell">{children}</div>,
}));

describe("AutomationsPage & AutomationRuleDrawer", () => {
  const mockRules = [
    {
      id: "rule-1",
      name: "Notificar por tarea completada",
      trigger_type: "task_completed",
      action_type: "notification",
      is_active: true,
    },
    {
      id: "rule-2",
      name: "Escalar urgencia en deadline",
      trigger_type: "deadline",
      action_type: "set_priority",
      is_active: false,
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(authContext.useAuth).mockReturnValue({
      token: "fake-token",
      loading: false,
      user: { id: "user-1", email: "admin@el-faro.org" },
    } as unknown as ReturnType<typeof authContext.useAuth>);

    vi.mocked(http.apiFetch).mockResolvedValue({
      items: mockRules,
      total: 2,
    });
  });

  it("renderiza el encabezado y lista las reglas de automatizacion", async () => {
    render(<AutomationsPage />);

    await waitFor(() => {
      expect(screen.getByText("Automatizaciones")).toBeInTheDocument();
      expect(screen.getByText("Notificar por tarea completada")).toBeInTheDocument();
      expect(screen.getByText("Escalar urgencia en deadline")).toBeInTheDocument();
    });

    expect(screen.getByText("1 activas")).toBeInTheDocument();
    expect(screen.getByText("1 inactivas")).toBeInTheDocument();
  });

  it("abre el Drawer de creacion al hacer clic en Nueva Regla", async () => {
    render(<AutomationsPage />);

    await waitFor(() => {
      expect(screen.getByText("Notificar por tarea completada")).toBeInTheDocument();
    });

    const newRuleBtn = screen.getByRole("button", { name: /Nueva Regla/i });
    fireEvent.click(newRuleBtn);

    await waitFor(() => {
      expect(screen.getByText("Nueva Automatización")).toBeInTheDocument();
      expect(screen.getByText("Constructor Trigger -> Action")).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/ej. Al completar tarea/i)).toBeInTheDocument();
    });
  });

  it("abre el Drawer de edicion al hacer clic en Configurar logica", async () => {
    render(<AutomationsPage />);

    await waitFor(() => {
      expect(screen.getByText("Notificar por tarea completada")).toBeInTheDocument();
    });

    const configButtons = screen.getAllByText(/Configurar lógica/i);
    fireEvent.click(configButtons[0]);

    await waitFor(() => {
      expect(screen.getByText("Editar Regla")).toBeInTheDocument();
      const input = screen.getByPlaceholderText(/ej. Al completar tarea/i) as HTMLInputElement;
      expect(input.value).toBe("Notificar por tarea completada");
    });
  });

  it("permite alternar el estado activo/inactivo de una regla", async () => {
    vi.mocked(http.apiFetch).mockImplementation(async (url, opts) => {
      if (url.includes("/admin/automations/rule-1") && opts?.method === "PATCH") {
        return { ...mockRules[0], is_active: false };
      }
      return { items: mockRules, total: 2 };
    });

    render(<AutomationsPage />);

    await waitFor(() => {
      expect(screen.getByText("Notificar por tarea completada")).toBeInTheDocument();
    });

    const toggleBtn = screen.getByLabelText("Desactivar regla");
    fireEvent.click(toggleBtn);

    await waitFor(() => {
      expect(http.apiFetch).toHaveBeenCalledWith(
        "/admin/automations/rule-1",
        expect.objectContaining({
          method: "PATCH",
          body: { is_active: false },
        })
      );
    });
  });
});
