import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "jest-axe";
import { ClipboardCheck, FolderArchive, ListTree, Target } from "lucide-react";
import { SidebarLayerProvider } from "@/context/SidebarLayerContext";
import {
  ProjectManagementHubDrawer,
  type ProjectHubModuleMeta,
} from "@/components/projects/ProjectManagementHubDrawer";

const META: ProjectHubModuleMeta[] = [
  { key: "kpis", label: "KPIs", icon: Target },
  { key: "wbs", label: "EDT / WBS y Diccionario", icon: ListTree },
  { key: "drive", label: "Drive", icon: FolderArchive },
  { key: "governance", label: "Gobernanza PMI", icon: ClipboardCheck },
  { key: "pmo", label: "Matriz PMO", icon: ClipboardCheck },
];

const RENDERERS = {
  kpis: () => <div data-testid="kpis-content">KPIs</div>,
  drive: () => <div data-testid="drive-content">Drive</div>,
  governance: () => <div data-testid="governance-content">Gobernanza PMI</div>,
  wbs: () => <div data-testid="wbs-content">EDT / WBS y Diccionario</div>,
  pmo: () => <div data-testid="pmo-content">Matriz PMO</div>,
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
  it("keeps tab activation and closing as separate accessible controls", async () => {
    const { container } = renderHub();
    expect(screen.getByRole("tab", { name: "KPIs" }).querySelector("button")).toBeNull();
    const tablist = screen.getByRole("tablist", { name: "Herramientas abiertas" });
    expect(tablist).toHaveAttribute("aria-owns", screen.getAllByRole("tab").map(tab => tab.id).join(' '));
    expect(tablist.querySelector('button[aria-label^="Cerrar"]')).toBeNull();
    expect((await axe(container)).violations).toEqual([]);
  });
  it("soporta la llave 'ccb' en la tira de pestañas y monta solo su contenido activo", () => {
    const ccbMeta: ProjectHubModuleMeta[] = [
      { key: "kpis", label: "KPIs", icon: Target },
      { key: "ccb", label: "Control de Cambios (CCB)", icon: FolderArchive },
    ];
    const ccbRenderers = {
      kpis: () => <div data-testid="kpis-content">KPIs</div>,
      ccb: () => <div data-testid="ccb-content">CCB</div>,
    };

    // Módulo ccb activo → solo su contenido se monta (sin cascada de drawers).
    const { unmount: unmountCcb } = renderHub({
      openModules: ["kpis", "ccb"],
      moduleMeta: ccbMeta,
      activeModule: "ccb",
      moduleRenderers: ccbRenderers,
    });
    expect(screen.getByTestId("ccb-content")).toBeInTheDocument();
    expect(screen.queryByTestId("kpis-content")).not.toBeInTheDocument();
    const ccbTab = screen.getByRole("tab", { name: /Control de Cambios \(CCB\)/ });
    expect(ccbTab).toHaveAttribute("aria-selected", "true");
    unmountCcb();

    // Módulo kpis activo tras reabrir → ccb queda desmontado.
    renderHub({
      openModules: ["kpis", "ccb"],
      moduleMeta: ccbMeta,
      activeModule: "kpis",
      moduleRenderers: ccbRenderers,
    });    expect(screen.getByTestId("kpis-content")).toBeInTheDocument();
    expect(screen.queryByTestId("ccb-content")).not.toBeInTheDocument();
  });

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

  it("renderiza correctamente el módulo 'components' cuando está activo", () => {
    renderHub({
      openModules: ["components"],
      moduleMeta: [{ key: "components", label: "Componentes EDT", icon: Target }],
      activeModule: "components",
      moduleRenderers: {
        components: () => <div data-testid="components-content">Componentes EDT</div>,
      },
    });
    expect(screen.getByTestId("components-content")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Componentes EDT/ })).toHaveAttribute("aria-selected", "true");
  });

  it("expone Gobernanza PMI en las pestañas del hub y monta su renderer activo", async () => {
    const user = userEvent.setup();
    const { props, rerender } = renderHub({
      openModules: ["governance"],
      activeModule: "governance",
    });

    expect(screen.getByRole("tab", { name: /Gobernanza PMI/ })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByTestId("governance-content")).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: /Gobernanza PMI/ }));
    expect(props.onActivateModule).toHaveBeenCalledWith("governance");

    rerender(
      <SidebarLayerProvider>
        <ProjectManagementHubDrawer {...props} activeModule="governance" />
      </SidebarLayerProvider>
    );
    expect(screen.getByTestId("governance-content")).toBeInTheDocument();
  });

  it("expone el EDT / WBS y Diccionario en el Hub y monta solo su renderer activo", async () => {
    const user = userEvent.setup();
    const { props } = renderHub({
      openModules: ["wbs"],
      activeModule: "wbs",
    });

    expect(screen.getByRole("tab", { name: /EDT \/ WBS y Diccionario/ })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByTestId("wbs-content")).toBeInTheDocument();
    expect(screen.queryByTestId("governance-content")).not.toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: /EDT \/ WBS y Diccionario/ }));
    expect(props.onActivateModule).toHaveBeenCalledWith("wbs");
  });

  it("operar en modo coexistencia: sin backdrop ni aria-modal y con offsetRight aplicado", () => {
    renderHub({ offsetRight: 420 });

    const dialog = screen.getByRole("dialog");
    // El hub NO es modal: el resto de la plataforma (sidebar de contexto,
    // otras herramientas) debe seguir clickeable mientras se trabaja.
    expect(dialog).not.toHaveAttribute("aria-modal");
    // Se retira del borde derecho el ancho del panel de contexto adjacente.
    expect(dialog).toHaveStyle({ right: "420px" });
  });

  it("expone Matriz PMO en el Hub y monta solo su renderer activo", async () => {
    const user = userEvent.setup();
    const { props } = renderHub({
      openModules: ["pmo"],
      activeModule: "pmo",
    });

    expect(screen.getByRole("tab", { name: /Matriz PMO/ })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByTestId("pmo-content")).toBeInTheDocument();
    expect(screen.queryByTestId("kpis-content")).not.toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: /Matriz PMO/ }));
    expect(props.onActivateModule).toHaveBeenCalledWith("pmo");
  });
});
