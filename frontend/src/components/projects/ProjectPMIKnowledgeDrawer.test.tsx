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
      content: "# Batería EVM\n\nFórmulas canónicas de Valor Ganado volumen 4.",
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

    expect(screen.getByText(/Batería Canónica de Indicadores/i)).toBeInTheDocument();

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
});
