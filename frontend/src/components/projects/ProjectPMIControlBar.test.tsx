import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import ProjectPMIControlBar, { isDirectActionKey } from "./ProjectPMIControlBar";

const baseActions = [
  { key: "whiteboard", label: "Pizarra" },
  { key: "phases", label: "Fases" },
  { key: "components", label: "Componentes EDT" },
  { key: "evm", label: "Valor Ganado (EVM / CPI)" },
  { key: "governance", label: "Gobernanza PMI" },
  { key: "time", label: "Horas" },
  { key: "settings", label: "Editar proyecto" },
  { key: "delete", label: "Eliminar proyecto" },
];

function renderBar(props: Partial<Parameters<typeof ProjectPMIControlBar>[0]> = {}) {
  return render(
    <ProjectPMIControlBar
      statusLabel="active"
      wbsAveragePct={42}
      wbsPackagesCount={7}
      actions={baseActions}
      onSelectAction={vi.fn()}
      {...props}
    />
  );
}

describe("ProjectPMIControlBar — Control PMI §4.3 & §4.5 (H-PROJ-UI-01)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("expone las métricas del proyecto en la barra de control", () => {
    renderBar();
    const bar = screen.getByTestId("project-detail-pmi-control-bar");
    expect(within(bar).getByText("Control PMI §4.3 & §4.5")).toBeInTheDocument();
    expect(within(bar).getByText("Etapa / Estado: active")).toBeInTheDocument();
    expect(within(bar).getByText("Avance WBS (0/50/100): 42%")).toBeInTheDocument();
    expect(within(bar).getByText("Paquetes WBS: 7 paquete(s)")).toBeInTheDocument();
  });

  it("consolida EVM y Gobernanza PMI dentro del selector, sin botones sueltos por fuera", () => {
    renderBar();
    const select = screen.getByTestId("project-detail-tools-switcher") as HTMLSelectElement;
    const optionLabels = Array.from(select.options).map((option) => option.textContent);
    // Sin duplicados sueltos: solo el selector con las herramientas.
    expect(optionLabels).toContain("Valor Ganado (EVM / CPI)");
    expect(optionLabels).toContain("Gobernanza PMI");
    // No existen botones duplicados fuera del selector (regresión del bug elimina aquí).
    expect(screen.queryByRole("button", { name: /EVM/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Gobernanza PMI/i })).not.toBeInTheDocument();
    // No hay opciones repetidas.
    const keys = Array.from(select.options).map((option) => option.value);
    expect(new Set(keys).size).toBe(keys.length);
  });

  it("resuelve la selección vía la acción canónica (cubre módulos y acciones directas)", () => {
    const onSelectAction = vi.fn();
    renderBar({ onSelectAction });

    const select = screen.getByTestId("project-detail-tools-switcher");
    // Módulo del hub: EVM.
    fireEvent.change(select, { target: { value: "evm" } });
    expect(onSelectAction).toHaveBeenCalledWith("evm");
    // Acción directa: Pizarra.
    fireEvent.change(select, { target: { value: "whiteboard" } });
    expect(onSelectAction).toHaveBeenCalledWith("whiteboard");
    // Placeholder no dispara nada.
    fireEvent.change(select, { target: { value: "" } });
    expect(onSelectAction).toHaveBeenCalledTimes(2);
  });

  it("refleja la herramienta activa del hub en el selector", () => {
    renderBar({ activeKey: "evm" });
    const select = screen.getByTestId("project-detail-tools-switcher") as HTMLSelectElement;
    expect(select.value).toBe("evm");
  });

  it("agrupa las opciones en Módulos del Hub vs Acciones directas (H-PROJ-UI-05)", () => {
    renderBar();
    const hubGroup = screen.getByRole("group", { name: "Módulos del Hub" });
    const directGroup = screen.getByRole("group", { name: "Acciones directas" });
    expect(within(hubGroup).getByRole("option", { name: "Horas" })).toBeInTheDocument();
    expect(within(hubGroup).getByRole("option", { name: "Valor Ganado (EVM / CPI)" })).toBeInTheDocument();
    expect(within(directGroup).getByRole("option", { name: "Pizarra" })).toBeInTheDocument();
    expect(within(directGroup).getByRole("option", { name: "Eliminar proyecto" })).toBeInTheDocument();
  });

  it("deduplica acciones con la misma key de forma defensiva", () => {
    renderBar({ actions: [{ key: "evm", label: "Valor Ganado (EVM / CPI)" }, { key: "evm", label: "EVM duplicado" }] });
    const select = screen.getByTestId("project-detail-tools-switcher") as HTMLSelectElement;
    expect(Array.from(select.options).filter((o) => o.value === "evm")).toHaveLength(1);
  });

  it("clasifica las keys directas canónicas fuera del Hub", () => {
    expect(isDirectActionKey("whiteboard")).toBe(true);
    expect(isDirectActionKey("phases")).toBe(true);
    expect(isDirectActionKey("settings")).toBe(true);
    expect(isDirectActionKey("delete")).toBe(true);
    expect(isDirectActionKey("evm")).toBe(false);
    expect(isDirectActionKey("governance")).toBe(false);
  });
});
