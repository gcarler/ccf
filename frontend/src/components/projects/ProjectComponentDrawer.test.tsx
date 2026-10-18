import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ProjectComponentDrawer } from "./ProjectComponentDrawer";
import type { ProjectComponentsBreakdown } from "@/types/projects";

const mocks = vi.hoisted(() => ({
  apiFetch: vi.fn(),
  toast: { error: vi.fn(), success: vi.fn() },
}));

const mockBreakdownResponse: ProjectComponentsBreakdown = {
  project_id: "proj-123",
  components: [
    {
      id: "comp-1",
      project_id: "proj-123",
      code: "EDT-1.0",
      name: "Infraestructura Cloud",
      description: "Servidores y VPC",
      budget_allocated: 40000,
      order_index: 1,
      color: "#3b82f6",
      status: "active",
      created_at: "2026-10-09T00:00:00Z",
      tasks_count: 5,
      expenses_count: 2,
      evm: {
        component_id: "comp-1",
        code: "EDT-1.0",
        name: "Infraestructura Cloud",
        budget_allocated: 40000,
        total_tasks: 5,
        completed_tasks: 3,
        physical_progress_pct: 60.0,
        ev: 24000,
        pv: 20000,
        ac: 18000,
        cpi: 1.33,
        spi: 1.2,
        cv: 6000,
        sv: 4000,
        cr: 1.6,
        financial_progress_pct: 45.0,
        balance_gap_pct: 15.0,
        health_status: "OPTIMO",
        health_color: "success",
      },
    },
    {
      id: "comp-2",
      project_id: "proj-123",
      code: "EDT-2.0",
      name: "Desarrollo Frontend",
      description: "UI y componentes Next.js",
      budget_allocated: 60000,
      order_index: 2,
      color: "#10b981",
      status: "active",
      created_at: "2026-10-09T00:00:00Z",
      tasks_count: 8,
      expenses_count: 1,
      evm: {
        component_id: "comp-2",
        code: "EDT-2.0",
        name: "Desarrollo Frontend",
        budget_allocated: 60000,
        total_tasks: 8,
        completed_tasks: 4,
        physical_progress_pct: 50.0,
        ev: 30000,
        pv: 30000,
        ac: 35000,
        cpi: 0.86,
        spi: 1.0,
        cv: -5000,
        sv: 0,
        cr: 0.86,
        financial_progress_pct: 58.3,
        balance_gap_pct: -8.3,
        health_status: "ADELANTADO_CON_SOBRECOSTO",
        health_color: "warning",
      },
    },
  ],
  budget_rule: {
    project_id: "proj-123",
    project_budget_allocated: 100000,
    components_budget_total: 100000,
    budget_difference: 0,
    allocation_percentage: 100,
    is_rule_satisfied: true,
    is_fully_allocated: true,
    status: "balanced",
    components_count: 2,
    recommendations: [
      "El presupuesto de los componentes cubre exactamente el 100% del presupuesto del proyecto.",
    ],
  },
};

vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({ token: "test-token" }),
}));
vi.mock("@/lib/http", () => ({ apiFetch: mocks.apiFetch }));
vi.mock("sonner", () => ({ toast: mocks.toast }));
vi.mock("@/components/ui/RightPanel", () => ({
  default: ({
    isOpen,
    children,
    title,
    subtitle,
    width,
  }: {
    isOpen: boolean;
    children: React.ReactNode;
    title?: React.ReactNode;
    subtitle?: React.ReactNode;
    width?: string;
  }) =>
    isOpen ? (
      <aside data-testid="right-panel" data-width={width}>
        <div>{title}</div>
        <div>{subtitle}</div>
        {children}
      </aside>
    ) : null,
}));

describe("ProjectComponentDrawer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.apiFetch.mockResolvedValue(mockBreakdownResponse);
  });

  it("renders components, EVM metrics and PMI 100% rule correctly", async () => {
    render(
      <ProjectComponentDrawer
        projectId="proj-123"
        projectTitle="Construcción Templo Sede Norte"
        isOpen={true}
        onClose={vi.fn()}
      />
    );

    // Esperar a que se carguen los datos
    await waitFor(() => {
      expect(screen.getByText("Regla del 100% del Presupuesto (PMI)")).toBeDefined();
    });

    // Validar estado 100% Balanceado
    expect(screen.getByText("100% Balanceado")).toBeDefined();
    expect(screen.getByText("Cobertura EDT: 100%")).toBeDefined();

    // Validar componentes listados
    expect(screen.getByText("Infraestructura Cloud")).toBeDefined();
    expect(screen.getByText("EDT-1.0")).toBeDefined();
    expect(screen.getByText("CPI: 1.33")).toBeDefined();
    expect(screen.getByText("SPI: 1.2")).toBeDefined();

    expect(screen.getByText("Desarrollo Frontend")).toBeDefined();
    expect(screen.getByText("EDT-2.0")).toBeDefined();
    expect(screen.getByText("CPI: 0.86")).toBeDefined();
  });

  it("opens create form and submits new component", async () => {
    render(
      <ProjectComponentDrawer
        projectId="proj-123"
        projectTitle="Construcción Templo Sede Norte"
        isOpen={true}
        onClose={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText("Nuevo Componente")).toBeDefined();
    });

    // Abrir formulario
    fireEvent.click(screen.getByText("Nuevo Componente"));

    expect(screen.getByText("Nuevo Componente EDT (Nivel 2)")).toBeDefined();

    const nameInput = screen.getByPlaceholderText("ej. Fase de Infraestructura Tecnológica");
    fireEvent.change(nameInput, { target: { value: "Seguridad y Compliance" } });

    // Guardar
    mocks.apiFetch.mockResolvedValueOnce({ id: "comp-3", code: "EDT-3.0", name: "Seguridad" });

    fireEvent.click(screen.getByText("Guardar Componente"));

    await waitFor(() => {
      expect(mocks.apiFetch).toHaveBeenCalledWith(
        "/projects/proj-123/components",
        expect.objectContaining({
          method: "POST",
          token: "test-token",
        })
      );
    });
  });

  it("handles deletion flow without centered modals", async () => {
    render(
      <ProjectComponentDrawer
        projectId="proj-123"
        projectTitle="Construcción Templo Sede Norte"
        isOpen={true}
        onClose={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByLabelText("Eliminar componente EDT-1.0")).toBeDefined();
    });

    // Click en eliminar para abrir confirmación en drawer (sin modal centrado)
    fireEvent.click(screen.getByLabelText("Eliminar componente EDT-1.0"));

    expect(screen.getByText("¿Eliminar componente [EDT-1.0]?")).toBeDefined();

    // Confirmar
    mocks.apiFetch.mockResolvedValueOnce({ message: "Eliminado" });
    fireEvent.click(screen.getByText("Confirmar"));

    await waitFor(() => {
      expect(mocks.apiFetch).toHaveBeenCalledWith(
        "/projects/proj-123/components/comp-1",
        expect.objectContaining({
          method: "DELETE",
          token: "test-token",
        })
      );
    });
  });

  it("clasifica Cuentas de Control (CA) y Paquetes de Planificación (Rolling Wave — PMI Vol. 3)", async () => {
    const breakdownWithPlanning: ProjectComponentsBreakdown = {
      project_id: "proj-123",
      components: [
        ...mockBreakdownResponse.components,
        {
          id: "comp-3",
          project_id: "proj-123",
          code: "EDT-3.0",
          name: "Mobiliario Litúrgico",
          description: "Reserva presupuestal pendiente de descomposición",
          budget_allocated: 0,
          order_index: 3,
          color: "#f59e0b",
          status: "active",
          created_at: "2026-10-10T00:00:00Z",
          tasks_count: 0,
          expenses_count: 0,
          evm: null,
        },
      ],
      budget_rule: {
        ...mockBreakdownResponse.budget_rule,
        components_count: 3,
      },
    };
    mocks.apiFetch.mockResolvedValueOnce(breakdownWithPlanning);

    render(
      <ProjectComponentDrawer
        projectId="proj-123"
        projectTitle="Construcción Templo Sede Norte"
        isOpen={true}
        onClose={vi.fn()}
      />
    );

    // Resumen de gobernanza: 2 Cuentas de Control + 1 Paquete de Planificación
    const summary = await screen.findByTestId("control-accounts-summary");
    expect(summary).toHaveTextContent("Gobernanza de Cuentas de Control y Planificación Gradual (Rolling Wave — PMI Vol. 3)");
    expect(summary).toHaveTextContent("2 Cuenta(s) de Control (CA)");
    expect(summary).toHaveTextContent("1 Paquete(s) de Planificación");

    // Badge doctrinal por tarjeta: 2 CA (con tareas) + 1 Rolling Wave (sin tareas)
    const caBadges = await screen.findAllByTestId("control-account-badge");
    expect(caBadges).toHaveLength(3);
    expect(
      caBadges.filter((badge) => badge.textContent === "Cuenta de Control (CA)")
    ).toHaveLength(2);
    expect(screen.getByText("Paquete de Planificación (Rolling Wave)")).toBeInTheDocument();
    expect(screen.getByText("Mobiliario Litúrgico")).toBeInTheDocument();
  });

  it("muestra la tupla EVM completa PV, EV, AC, CV, SV y EAC por Cuenta de Control", async () => {
    render(
      <ProjectComponentDrawer
        projectId="proj-123"
        projectTitle="Construcción Templo Sede Norte"
        isOpen={true}
        onClose={vi.fn()}
      />
    );

    const tuples = await screen.findAllByTestId("evm-tuple");
    expect(tuples).toHaveLength(2); // una por Cuenta de Control con evm

    // Comp-1: PV 20000, EV 24000, AC 18000, CV +6000, SV +4000, EAC = 40000 / 1.33 ≈ 30,075
    expect(screen.getAllByText("PV (Valor Planificado)")).toHaveLength(2);
    expect(screen.getByText("$20,000")).toBeInTheDocument();
    expect(screen.getByText("$24,000")).toBeInTheDocument();
    // $18,000 también aparece en la métrica existente “Gastos Reales (AC)”
    expect(screen.getAllByText("$18,000")).toHaveLength(2);
    expect(screen.getByText("+$6,000")).toBeInTheDocument(); // CV favorable
    expect(screen.getByText("+$4,000")).toBeInTheDocument(); // SV favorable
    expect(screen.getAllByText(/EAC Proyectado \(CA\)/).length).toBe(2);

    // Comp-2: CV -5000 desfavorable (sin prefijo +) y SV 0
    expect(screen.getByText("$-5,000")).toBeInTheDocument();
    // $0 aparece al menos 2 veces: SV de comp-2 y el BAC del paquete de planificación
    expect(screen.getAllByText("$0").length).toBeGreaterThanOrEqual(2);
  });

  it("renders RightPanel with responsive wide dimensions (max-w-6xl)", async () => {
    render(
      <ProjectComponentDrawer
        projectId="proj-123"
        projectTitle="Construcción Templo Sede Norte"
        isOpen={true}
        onClose={vi.fn()}
      />
    );

    const panel = screen.getByTestId("right-panel");
    expect(panel.getAttribute("data-width")).toBe(
      "w-full sm:w-[88vw] lg:w-[72vw] xl:w-[64vw] max-w-6xl"
    );
  });
});
