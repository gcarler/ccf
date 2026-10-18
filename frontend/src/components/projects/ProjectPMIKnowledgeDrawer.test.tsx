import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ProjectPMIKnowledgeDrawer } from "./ProjectPMIKnowledgeDrawer";
import type { PMIDoctrineIndexResponse } from "@/types/projects";

const mocks = vi.hoisted(() => ({
  apiFetch: vi.fn(),
  toast: { error: vi.fn(), success: vi.fn() },
}));

vi.mock("@/lib/http", () => ({
  apiFetch: mocks.apiFetch,
}));

vi.mock("sonner", () => ({
  toast: mocks.toast,
}));

vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({ token: "test-token" }),
}));

vi.mock("@/components/ui/RightPanel", () => ({
  default: ({
    isOpen,
    children,
    title,
    subtitle,
  }: {
    isOpen: boolean;
    children: React.ReactNode;
    title?: React.ReactNode;
    subtitle?: React.ReactNode;
  }) =>
    isOpen ? (
      <aside data-testid="right-panel">
        <div>{title}</div>
        <div>{subtitle}</div>
        {children}
      </aside>
    ) : null,
}));

const mockDoctrineResponse: PMIDoctrineIndexResponse = {
  total_volumes: 2,
  kb_indexed_count: 7,
  wiki_seeded_count: 7,
  volumes: [
    {
      vol: 0,
      page_key: "wiki_pmi_00_indice_maestro",
      file_name: "00_INDICE_MAESTRO_PMI_CCF.md",
      title: "Compendio Maestro de Dirección de Proyectos (Estándar PMI / PMBOK)",
      summary: "Índice maestro y arquitectura metodológica del compendio canónico PMI.",
      tags: ["pmi", "pmbok", "indice"],
      char_count: 1200,
      word_count: 250,
      content: "# Compendio Maestro\n\nTexto de doctrina metodológica volumen 0.",
    },
    {
      vol: 4,
      page_key: "wiki_pmi_04_metricas_evm",
      file_name: "04_BATERIA_DE_INDICADORES_METRICAS_EVM.md",
      title: "Batería Canónica de Indicadores y Métricas EVM (Estándar PMI)",
      summary: "Fórmulas y métricas de Valor Ganado: BAC, PV, EV, AC, CPI, SPI.",
      tags: ["pmi", "evm", "cpi", "spi"],
      char_count: 2400,
      word_count: 480,
      content: "# Batería EVM\n\nFórmulas canónicas de Valor Ganado volumen 4.\n\n## Métricas EVM\n\nCPI y SPI describen el desempeño.\n\n## Pronóstico EAC\n\nEAC proyecta el costo al cierre.",
    },
  ],
};

describe("ProjectPMIKnowledgeDrawer Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renderiza correctamente el Drawer lateral de doctrina PMI sin modales centrados", async () => {
    mocks.apiFetch.mockResolvedValueOnce(mockDoctrineResponse);

    render(
      <ProjectPMIKnowledgeDrawer
        isOpen={true}
        onClose={vi.fn()}
      />
    );

    expect(screen.getByText(/Biblioteca Metodológica Oficial PMI \/ PMBOK/i)).toBeInTheDocument();
    expect(screen.getByText(/Compendio Canónico de 7 Volúmenes/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText(/Compendio Maestro de Dirección de Proyectos/i)).toBeInTheDocument();
      expect(screen.getByText(/Índice maestro y arquitectura metodológica/i)).toBeInTheDocument();
    });

    // Cero modales centrados
    expect(document.querySelector('[role="alertdialog"]')).toBeNull();
  });

  it("permite seleccionar otro volumen y muestra su contenido", async () => {
    mocks.apiFetch.mockResolvedValueOnce(mockDoctrineResponse);

    render(
      <ProjectPMIKnowledgeDrawer
        isOpen={true}
        onClose={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/Volumen 4/i)).toBeInTheDocument();
    });

    const vol4Button = screen.getByText(/Volumen 4/i).closest("button");
    expect(vol4Button).not.toBeNull();
    fireEvent.click(vol4Button!);

    expect(screen.getByRole("heading", { name: /Batería Canónica de Indicadores y Métricas EVM/i })).toBeInTheDocument();
    expect(screen.getByText(/Fórmulas y métricas de Valor Ganado/i)).toBeInTheDocument();
  });

  it("permite filtrar volúmenes por término de búsqueda y sincronizar con Wiki", async () => {
    mocks.apiFetch
      .mockResolvedValueOnce(mockDoctrineResponse)
      .mockResolvedValueOnce({
        total_volumes: 2,
        kb_indexed_count: 7,
        wiki_seeded_count: 7,
        volumes: mockDoctrineResponse.volumes,
      });

    render(
      <ProjectPMIKnowledgeDrawer
        isOpen={true}
        onClose={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Buscar en la doctrina PMI/i)).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/Buscar en la doctrina PMI/i);
    fireEvent.change(searchInput, { target: { value: "EVM" } });

    expect(screen.getByRole("heading", { name: /Batería Canónica de Indicadores/i })).toBeInTheDocument();

    // Sincronizar
    const syncButton = screen.getByRole("button", { name: /Sincronizar a Wiki de Sede/i });
    fireEvent.click(syncButton);

    await waitFor(() => {
      expect(mocks.apiFetch).toHaveBeenCalledWith("/projects/pmi-doctrine/sync", {
        method: "POST",
      });
      expect(mocks.toast.success).toHaveBeenCalledWith(
        expect.stringContaining("Doctrina PMI sincronizada")
      );
    });
  });

  it("filtra por tags, busca dentro del Markdown y selecciona el primer resultado coincidente", async () => {
    mocks.apiFetch.mockResolvedValueOnce(mockDoctrineResponse);

    render(<ProjectPMIKnowledgeDrawer isOpen onClose={vi.fn()} />);
    await screen.findByRole("heading", { name: /Compendio Maestro de Dirección de Proyectos/i });

    const searchInput = screen.getByPlaceholderText(/Buscar en la doctrina PMI/i);
    fireEvent.change(searchInput, { target: { value: "evm" } });

    expect(await screen.findByRole("heading", { name: /Batería Canónica de Indicadores/i })).toBeInTheDocument();
    expect(screen.getByText("Volumen 4 (Compendio de 2 volúmenes)")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Volumen 0/i })).not.toBeInTheDocument();

    fireEvent.change(searchInput, { target: { value: "volumen 4" } });
    expect(screen.getByRole("heading", { name: /Batería Canónica de Indicadores/i })).toBeInTheDocument();
    expect(screen.getByText(/Fórmulas canónicas de Valor Ganado volumen 4/i)).toBeInTheDocument();

    fireEvent.change(searchInput, { target: { value: "indice" } });
    expect(await screen.findByRole("heading", { name: /Compendio Maestro de Dirección de Proyectos/i })).toBeInTheDocument();
    expect(screen.getByText(/Índice maestro y arquitectura metodológica/i)).toBeInTheDocument();
  });

  it("muestra estado vacío cuando ningún volumen coincide con el término", async () => {
    mocks.apiFetch.mockResolvedValueOnce(mockDoctrineResponse);

    render(<ProjectPMIKnowledgeDrawer isOpen onClose={vi.fn()} />);
    await screen.findByRole("heading", { name: /Compendio Maestro de Dirección de Proyectos/i });
    fireEvent.change(screen.getByPlaceholderText(/Buscar en la doctrina PMI/i), {
      target: { value: "sin-coincidencias-ccf" },
    });

    expect(screen.getByText(/No se encontraron volúmenes que coincidan con la búsqueda/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Volumen [04]/i })).not.toBeInTheDocument();
  });

  it("extrae encabezados H2 y construye enlaces al contenido del volumen activo", async () => {
    mocks.apiFetch.mockResolvedValueOnce(mockDoctrineResponse);

    render(<ProjectPMIKnowledgeDrawer isOpen onClose={vi.fn()} />);
    await screen.findByRole("heading", { name: /Compendio Maestro de Dirección de Proyectos/i });
    fireEvent.click(screen.getByRole("button", { name: /Volumen 4/i }));

    const index = screen.getByRole("navigation", { name: "Índice rápido de secciones" });
    const metricsLink = screen.getByRole("link", { name: "Métricas EVM" });
    const forecastLink = screen.getByRole("link", { name: "Pronóstico EAC" });
    expect(index).toContainElement(metricsLink);
    expect(metricsLink).toHaveAttribute("href", "#pmi-volume-4-section-1");
    expect(forecastLink).toHaveAttribute("href", "#pmi-volume-4-section-2");
    expect(document.getElementById("pmi-volume-4-section-1")).toHaveTextContent("Métricas EVM");
  });
});
