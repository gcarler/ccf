import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FolderArchive, Target } from "lucide-react";
import { SidebarLayerProvider } from "@/context/SidebarLayerContext";
import {
  ProjectManagementHubDrawer,
  type ProjectHubModuleMeta,
} from "@/components/projects/ProjectManagementHubDrawer";

const META: ProjectHubModuleMeta[] = [
  { key: "kpis", label: "KPIs", icon: Target },
  { key: "drive", label: "Drive", icon: FolderArchive },
];

const RENDERERS = {
  kpis: () => <div data-testid="kpis-content">KPIs</div>,
  drive: () => <div data-testid="drive-content">Drive</div>,
};

function renderHub(
  overrides?: Partial<Parameters<typeof ProjectManagementHubDrawer>[0]>
) {
  const props = {
    isOpen: true,
    openModules: ["kpis", "drive"] as const,
    moduleMeta: META,
    activeModule: "kpis" as const,
    onActivateModule: vi.fn(),
    onCloseModule: vi.fn(),
    onCloseHub: vi.fn(),
    moduleRenderers: RENDERERS,
    ...overrides,
  };
  return {
    props,
    ...render(
      <SidebarLayerProvider>
        <ProjectManagementHubDrawer {...props} />
      </SidebarLayerProvider>
    ),
  };
}

describe("ProjectManagementHubDrawer", () => {
  it("monta solo el contenido del módulo activo (sin cascada de drawers)", () => {
    renderHub();
    expect(screen.getByTestId("kpis-content")).toBeInTheDocument();
    expect(screen.queryByTestId("drive-content")).not.toBeInTheDocument();
  });

  it("muestra las pestañas abiertas con la activa marcada", () => {
    renderHub();
    const kpisTab = screen.getByRole("tab", { name: /KPIs/ });
    const driveTab = screen.getByRole("tab", { name: /^Drive$/ });
    expect(kpisTab).toHaveAttribute("aria-selected", "true");
    expect(driveTab).toHaveAttribute("aria-selected", "false");
  });

  it("activa otra pestaña al hacer clic y unmount el módulo anterior", async () => {
    const user = userEvent.setup();
    const { props, rerender } = renderHub();
    await user.click(screen.getByRole("tab", { name: /^Drive$/ }));
    expect(props.onActivateModule).toHaveBeenCalledWith("drive");

    // Mismo hub con activeModule=drive: solo el contenido de drive vive
    rerender(
      <SidebarLayerProvider>
        <ProjectManagementHubDrawer {...props} activeModule="drive" />
      </SidebarLayerProvider>
    );
    await waitFor(() => {
      expect(screen.queryByTestId("kpis-content")).not.toBeInTheDocument();
      expect(screen.getByTestId("drive-content")).toBeInTheDocument();
    });
  });

  it("cierra una pestaña individual con su propio botón X", async () => {
    const user = userEvent.setup();
    const { props } = renderHub();
    await user.click(screen.getByRole("button", { name: "Cerrar KPIs" }));
    expect(props.onCloseModule).toHaveBeenCalledTimes(1);
    expect(props.onCloseModule).toHaveBeenCalledWith("kpis");
    expect(props.onCloseHub).not.toHaveBeenCalled();
  });

  it("cierra el hub completo con el botón del panel", async () => {
    const user = userEvent.setup();
    const { props } = renderHub();
    await user.click(screen.getByRole("button", { name: "Cerrar panel" }));
    expect(props.onCloseHub).toHaveBeenCalledTimes(1);
  });

  it("alterna pantalla completa con Maximize2/Minimize2", async () => {
    const user = userEvent.setup();
    renderHub();
    const maximizeBtn = screen.getByRole("button", {
      name: "Pantalla completa",
    });
    await user.click(maximizeBtn);
    expect(
      screen.getByRole("button", { name: "Salir de pantalla completa" })
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Pantalla completa" })
    ).not.toBeInTheDocument();
  });

  it("renderiza vacío (sin contenido) cuando no hay módulo activo", () => {
    renderHub({ activeModule: undefined });
    expect(screen.queryByTestId("kpis-content")).not.toBeInTheDocument();
    expect(screen.queryByTestId("drive-content")).not.toBeInTheDocument();
  });
});
