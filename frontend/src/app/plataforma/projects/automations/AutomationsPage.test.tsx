import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import AutomationsPage from "./page";
import { AutomationRuleDrawer } from "./AutomationRuleDrawer";
import * as authContext from "@/context/AuthContext";

vi.mock("@/context/AuthContext", () => ({
  useAuth: vi.fn(),
}));

vi.mock("@/components/projects/ProjectsShell", () => ({
  default: ({ children }: { children: React.ReactNode }) => <div data-testid="projects-shell">{children}</div>,
}));

vi.mock("@/components/ui/RightPanel", () => ({
  RightPanel: ({ open, children }: { open: boolean; children: React.ReactNode }) =>
    open ? <div data-testid="right-panel">{children}</div> : null,
}));

describe("AutomationsPage (Compatibility Landing)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(authContext.useAuth).mockReturnValue({
      token: "fake-token",
      loading: false,
      user: { id: "user-1", email: "admin@el-faro.org" },
    } as unknown as ReturnType<typeof authContext.useAuth>);
  });

  it("renderiza el encabezado principal y la categoría de automatizaciones", () => {
    render(<AutomationsPage />);

    expect(
      screen.getByText("Automatizaciones de proyectos"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Administra las reglas desde su proyecto" }),
    ).toBeInTheDocument();
  });

  it("explica el alcance y la política de aislamiento de reglas por proyecto", () => {
    render(<AutomationsPage />);

    expect(
      screen.getByText(/Las reglas de Proyectos tienen alcance y permisos propios/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Abre un proyecto y selecciona/i),
    ).toBeInTheDocument();
    expect(screen.getByText("Automatizaciones")).toBeInTheDocument();
  });

  it("provee enlace directo de navegación a la lista de proyectos", () => {
    render(<AutomationsPage />);

    const link = screen.getByRole("link", { name: /Ir a mis proyectos/i });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute("href", "/plataforma/projects");
  });

  it("informa sobre la restricción de permisos para la ejecución de efectos", () => {
    render(<AutomationsPage />);

    expect(
      screen.getByText(/La ejecución de efectos está reservada a personas con permiso de gestión/i),
    ).toBeInTheDocument();
    expect(screen.getByTestId("projects-shell")).toBeInTheDocument();
  });

  it("renderiza previsualización PMI §4.6 en AutomationRuleDrawer y aplica preset SLA", () => {
    render(
      <AutomationRuleDrawer
        isOpen={true}
        onClose={vi.fn()}
        onSaved={vi.fn()}
      />,
    );

    const preview = screen.getByTestId("automation-rule-pmi-preview");
    expect(preview).toHaveTextContent("Tarea completada → Notificar al equipo");
    expect(preview).toHaveTextContent(
      "Ejecución y Monitoreo de Paquetes WBS (PMI §4.3 / §4.5)",
    );

    fireEvent.click(screen.getByTestId("automation-preset-sla"));

    expect(
      screen.getByPlaceholderText("ej. Al completar tarea notificar al pastor"),
    ).toHaveValue("Alerta PMI 24h antes de vencimiento");
    expect(preview).toHaveTextContent("Cerca del deadline → Notificar al equipo");
    expect(preview).toHaveTextContent(
      "Control de Cronograma y Nivelación de Recursos (PMI §6.6 / §9.6)",
    );
  });
});
