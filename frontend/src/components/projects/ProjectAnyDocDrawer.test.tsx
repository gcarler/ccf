import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ProjectAnyDocDrawer } from "./ProjectAnyDocDrawer";

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

describe("ProjectAnyDocDrawer Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renderiza correctamente el Drawer lateral sin modales centrados", () => {
    render(
      <ProjectAnyDocDrawer
        projectId="proj-test-123"
        projectTitle="Proyecto Catedral"
        isOpen={true}
        onClose={vi.fn()}
      />
    );

    expect(screen.getByText(/Conversor Universal AnyDoc/i)).toBeInTheDocument();
    expect(screen.getByText(/Pipeline de Documentación PMI • Proyecto Catedral/i)).toBeInTheDocument();
    expect(screen.getByText(/Arrastra y suelta tu archivo/i)).toBeInTheDocument();
    expect(screen.getByText(/Motor AnyDoc v0.2.4/i)).toBeInTheDocument();

    // Regla de Arquitectura: Cero modales centrados o AlertDialog
    expect(document.querySelector('[role="alertdialog"]')).toBeNull();
  });

  it("muestra estadísticas de conversión y permite alternar entre vista previa y markdown puro", async () => {
    mocks.apiFetch.mockResolvedValueOnce({
      filename: "reporte.xlsx",
      format: "xlsx",
      markdown: "# Reporte Financiero\n\n| Item | Valor |\n| --- | --- |\n| Total | $50,000 |",
      char_count: 85,
      word_count: 14,
      processing_time_ms: 8.5,
      engine: "anydoc_v0.2.4",
      success: true,
      error: null,
    });

    render(
      <ProjectAnyDocDrawer
        projectId="proj-test-123"
        projectTitle="Proyecto Catedral"
        isOpen={true}
        onClose={vi.fn()}
      />
    );

    // Simular subida de archivo
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    expect(fileInput).not.toBeNull();

    const file = new File(["test data"], "reporte.xlsx", { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText("reporte.xlsx")).toBeInTheDocument();
      expect(screen.getByText("8.5 ms")).toBeInTheDocument();
      expect(screen.getByText("Palabras")).toBeInTheDocument();
      expect(screen.getByText("Caracteres")).toBeInTheDocument();
    });

    // Alternar a Markdown Puro
    const tabSource = screen.getByRole("button", { name: /Markdown Puro/i });
    fireEvent.click(tabSource);
    expect(screen.getByRole("textbox")).toHaveValue("# Reporte Financiero\n\n| Item | Valor |\n| --- | --- |\n| Total | $50,000 |");
  });

  it("permite publicar el contenido a la Wiki del Proyecto", async () => {
    mocks.apiFetch
      .mockResolvedValueOnce({
        filename: "especificacion.docx",
        format: "docx",
        markdown: "# Especificación Técnica EDT",
        char_count: 32,
        word_count: 4,
        processing_time_ms: 12.0,
        engine: "anydoc_v0.2.4",
        success: true,
      })
      .mockResolvedValueOnce({
        conversion: {
          filename: "especificacion.docx",
          format: "docx",
          markdown: "# Especificación Técnica EDT",
          char_count: 32,
          word_count: 4,
          processing_time_ms: 12.0,
          engine: "anydoc_v0.2.4",
          success: true,
        },
        published_to: "project_wiki",
        document_id: "doc-uuid-123",
        title: "Especificación Técnica EDT",
        message: "Documento publicado exitosamente",
      });

    const onPublishedMock = vi.fn();

    render(
      <ProjectAnyDocDrawer
        projectId="proj-test-123"
        isOpen={true}
        onClose={vi.fn()}
        onPublished={onPublishedMock}
      />
    );

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(["docx content"], "especificacion.docx", { type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText("especificacion.docx")).toBeInTheDocument();
    });

    const publishProjectWikiBtn = screen.getByText("Wiki del Proyecto").closest("button");
    expect(publishProjectWikiBtn).not.toBeNull();
    fireEvent.click(publishProjectWikiBtn!);

    await waitFor(() => {
      expect(mocks.apiFetch).toHaveBeenCalledWith(
        "/projects/proj-test-123/documents/convert-and-publish",
        expect.objectContaining({
          method: "POST",
        })
      );
      expect(mocks.toast.success).toHaveBeenCalledWith("Documento publicado exitosamente");
      expect(onPublishedMock).toHaveBeenCalled();
    });
  });
});
