import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "jest-axe";
import { describe, expect, it, vi } from "vitest";
import { SidebarLayerProvider } from "@/context/SidebarLayerContext";
import type { ProjectFileRecord } from "@/types/projects";
import { ProjectFileViewerDrawer } from "./ProjectFileViewerDrawer";

vi.mock("@/lib/http", () => ({
  apiFetch: vi.fn(),
  apiFetchBlob: vi.fn(),
}));

import { apiFetch, apiFetchBlob } from "@/lib/http";
const mockApiFetch = vi.mocked(apiFetch);
const mockApiFetchBlob = vi.mocked(apiFetchBlob);

const imageFile: ProjectFileRecord = {
  id: "file-image-1",
  project_id: "project-1",
  name: "Plano del proyecto.png",
  category: "diseño",
  file_source: "local",
  file_url: "/files/plan.png",
  file_type: "image/png",
  created_at: "2026-10-04T12:00:00Z",
};

function renderViewer(file: ProjectFileRecord) {
  return render(
    <SidebarLayerProvider>
      <ProjectFileViewerDrawer file={file} isOpen onClose={vi.fn()} />
    </SidebarLayerProvider>,
  );
}

describe("ProjectFileViewerDrawer", () => {
  it("exposes named image controls and supports zoom and rotation by keyboard-accessible buttons", async () => {
    const user = userEvent.setup();
    const { container } = renderViewer(imageFile);

    expect(screen.getByRole("dialog", { name: "Visor Universal Embebido" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: imageFile.name })).toHaveClass(
      "text-[hsl(var(--text-primary))]",
    );
    const image = screen.getByRole("img", { name: imageFile.name });
    expect(image).toHaveStyle({ transform: "scale(1) rotate(0deg)" });

    await user.click(screen.getByRole("button", { name: "Acercar" }));
    expect(image).toHaveStyle({ transform: "scale(1.25) rotate(0deg)" });
    await user.click(screen.getByRole("button", { name: "Rotar 90°" }));
    expect(image).toHaveStyle({ transform: "scale(1.25) rotate(90deg)" });
    expect((await axe(container)).violations).toEqual([]);
  });

  it("uses a semantic surface token for the video letterbox background", () => {
    const videoFile: ProjectFileRecord = {
      ...imageFile,
      id: "file-video-1",
      name: "Presentación.mp4",
      file_url: "/files/presentation.mp4",
      file_type: "video/mp4",
    };
    renderViewer(videoFile);

    const video = document.querySelector("video");
    expect(video).not.toBeNull();
    expect(video).toHaveClass("bg-[hsl(var(--surface-2))]");
    expect(video).not.toHaveClass("bg-black");
  });

  it("does not embed an unsafe historical Drive preview URL", () => {
    const driveFile: ProjectFileRecord = {
      ...imageFile,
      id: "file-drive-1",
      name: "Minuta de comité.pdf",
      file_source: "drive",
      file_url: "https://drive.google.com/file/d/abc123/view",
      embed_url: "javascript:alert(document.domain)",
      file_type: "application/pdf",
    };
    renderViewer(driveFile);

    expect(screen.getByTitle(driveFile.name)).toHaveAttribute(
      "src",
      driveFile.file_url,
    );
  });

  it("blocks unsafe historical file URLs instead of rendering active content", () => {
    const unsafeFile: ProjectFileRecord = {
      ...imageFile,
      file_url: "javascript:alert(document.domain)",
    };
    renderViewer(unsafeFile);

    expect(screen.getByRole("alert")).toHaveTextContent(/enlace.*se bloqueó/i);
    expect(document.querySelector("iframe, img, audio, video, a[href]")).toBeNull();
  });

  it("renders embedded PDF iframe with toolbar and navpanes parameters", () => {
    const pdfFile: ProjectFileRecord = {
      ...imageFile,
      id: "file-pdf-1",
      name: "Especificaciones.pdf",
      file_url: "https://example.com/files/spec.pdf",
      file_type: "application/pdf",
    };
    renderViewer(pdfFile);

    const iframe = screen.getByTitle(pdfFile.name);
    expect(iframe).toBeInTheDocument();
    expect(iframe).toHaveAttribute(
      "src",
      "https://example.com/files/spec.pdf#toolbar=1&navpanes=0",
    );
  });

  it("converts and displays Office document (Excel) with GFM table, badges, stats, and tabs", async () => {
    const user = userEvent.setup();
    mockApiFetch.mockResolvedValueOnce({
      filename: "Presupuesto_2026.xlsx",
      format: "xlsx",
      markdown: "# Presupuesto General\n\n| Partida | Monto USD | Estado |\n| --- | --- | --- |\n| Personal | $15,000 | Aprobado |\n| Licencias | $2,500 | En revisión |\n\n> Fin del documento.",
      char_count: 140,
      word_count: 18,
      processing_time_ms: 45,
      engine: "anydoc_rs",
      success: true,
    });

    const excelFile: ProjectFileRecord = {
      ...imageFile,
      id: "file-excel-1",
      name: "Presupuesto_2026.xlsx",
      file_url: "https://example.com/files/presupuesto.xlsx",
      file_type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    };

    const { container } = renderViewer(excelFile);

    expect(await screen.findByText("Presupuesto General")).toBeInTheDocument();
    expect(screen.getByText("Partida")).toBeInTheDocument();
    expect(screen.getByText("Personal")).toBeInTheDocument();
    expect(screen.getByText("$15,000")).toBeInTheDocument();
    expect(screen.getByText("XLSX")).toBeInTheDocument();
    expect(screen.getByText("18")).toBeInTheDocument();
    expect(screen.getByText(/palabras/)).toBeInTheDocument();
    expect(screen.getByText(/45 ms/)).toBeInTheDocument();

    const previewTab = screen.getByRole("tab", { name: "Vista Previa" });
    const rawTab = screen.getByRole("tab", { name: "Markdown" });
    expect(previewTab).toHaveAttribute("aria-selected", "true");

    await user.click(rawTab);
    expect(rawTab).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText(/\| Partida \| Monto USD \|/)).toBeInTheDocument();

    // Verify strict semantic tokens compliance
    expect(screen.getByTestId("anydoc-reader-area").innerHTML).not.toMatch(
      /--(?:foreground|muted-foreground)\b/
    );
    expect((await axe(container)).violations).toEqual([]);
  });

  it("renders markdown files directly with native structured reader", async () => {
    mockApiFetchBlob.mockResolvedValueOnce({
      text: async () => "# Guía Rápida\n\nInstrucciones de configuración del proyecto.",
    } as unknown as Blob);

    const mdFile: ProjectFileRecord = {
      ...imageFile,
      id: "file-md-1",
      name: "README.md",
      file_url: "https://example.com/files/README.md",
      file_type: "text/markdown",
    };

    const { container } = renderViewer(mdFile);

    expect(await screen.findByText("Guía Rápida")).toBeInTheDocument();
    expect(screen.getByText("Instrucciones de configuración del proyecto.")).toBeInTheDocument();
    expect(screen.getByText("MD")).toBeInTheDocument();

    expect(screen.getByTestId("anydoc-reader-area").innerHTML).not.toMatch(
      /--(?:foreground|muted-foreground)\b/
    );
    expect((await axe(container)).violations).toEqual([]);
  });

  it("displays accessible error state and fallback download button when conversion fails", async () => {
    mockApiFetch.mockRejectedValueOnce(new Error("Documento dañado o corrupto"));

    const docxFile: ProjectFileRecord = {
      ...imageFile,
      id: "file-doc-1",
      name: "Contrato.docx",
      file_url: "https://example.com/files/contrato.docx",
      file_type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    };

    renderViewer(docxFile);

    expect(await screen.findByText("Documento dañado o corrupto")).toBeInTheDocument();
    const downloadLinks = screen.getAllByRole("link", { name: /Descargar/i });
    expect(downloadLinks.length).toBeGreaterThan(0);
    expect(downloadLinks[0]).toHaveAttribute(
      "href",
      "https://example.com/files/contrato.docx",
    );
  });

  it("converts and previews Word (.docx) documents passing file_url to backend", async () => {
    mockApiFetch.mockResolvedValueOnce({
      filename: "Acta_Comite.docx",
      format: "docx",
      markdown: "# Acta de Comité\n\n- Punto 1: Aprobación de alcance\n- Punto 2: Asignación de recursos",
      char_count: 85,
      word_count: 14,
      processing_time_ms: 32,
      engine: "anydoc_v0.2.4",
      success: true,
    });

    const docxFile: ProjectFileRecord = {
      ...imageFile,
      id: "file-doc-2",
      name: "Acta_Comite.docx",
      file_url: "/api/static/projects/acta_123.docx",
      file_type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    };

    renderViewer(docxFile);

    expect(await screen.findByText("Acta de Comité")).toBeInTheDocument();
    expect(screen.getByText("Punto 1: Aprobación de alcance")).toBeInTheDocument();
    expect(screen.getByText("DOCX")).toBeInTheDocument();

    expect(mockApiFetch).toHaveBeenCalledWith(
      "/projects/convert-document",
      expect.objectContaining({
        method: "POST",
        body: expect.objectContaining({
          filename: "Acta_Comite.docx",
          file_url: "/api/static/projects/acta_123.docx",
          format_hint: "docx",
        }),
      }),
    );
  });

  it("identifies and previews images converted to .webp in file_url even when file.name lacks extension", () => {
    const webpFile: ProjectFileRecord = {
      ...imageFile,
      id: "file-img-custom",
      name: "Fotografía del Evento Inaugural",
      file_url: "/api/static/projects/evento_inaugural_987.webp",
      file_type: "image/jpeg",
    };

    renderViewer(webpFile);

    const img = screen.getByRole("img", { name: webpFile.name });
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute("src", webpFile.file_url);
    expect(screen.getByRole("button", { name: "Acercar" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Rotar 90°" })).toBeInTheDocument();
  });

  it("converts and displays CSV documents as GFM tables", async () => {
    mockApiFetch.mockResolvedValueOnce({
      filename: "Reporte_Metricas.csv",
      format: "csv",
      markdown: "| Indicador | Meta | Actual |\n| --- | --- | --- |\n| Asistencia | 500 | 520 |\n| Conversiones | 50 | 62 |",
      char_count: 110,
      word_count: 12,
      processing_time_ms: 18,
      engine: "anydoc_v0.2.4",
      success: true,
    });

    const csvFile: ProjectFileRecord = {
      ...imageFile,
      id: "file-csv-1",
      name: "Reporte_Metricas.csv",
      file_url: "/api/static/projects/metricas.csv",
      file_type: "text/csv",
    };

    renderViewer(csvFile);

    expect(await screen.findByText("Indicador")).toBeInTheDocument();
    expect(screen.getByText("Meta")).toBeInTheDocument();
    expect(screen.getByText("Actual")).toBeInTheDocument();
    expect(screen.getByText("Asistencia")).toBeInTheDocument();
    expect(screen.getByText("520")).toBeInTheDocument();
    expect(screen.getByText("CSV")).toBeInTheDocument();
  });

  describe("PMI §10.2 & §5.5 — Franja de Trazabilidad y Control de Configuración", () => {
    it("clasifica el rol de artefacto PMI y el control de version documental", () => {
      // Línea Base / Gobernanza con versión explícita
      const { unmount: unmountBaseline } = renderViewer({
        ...imageFile,
        id: "file-pmi-baseline",
        name: "Acta de Constitución del Proyecto v2.pdf",
        file_type: "application/pdf",
      });
      expect(
        screen.getByTestId("file-viewer-pmi-traceability-strip")
      ).toBeInTheDocument();
      expect(screen.getByTestId("file-viewer-pmi-role")).toHaveTextContent(
        "Línea Base / Gobernanza"
      );
      expect(screen.getByTestId("file-viewer-pmi-version")).toHaveTextContent(
        "Version Controlada"
      );
      unmountBaseline();

      // Evidencia QA / DoD sin versión explícita
      const { unmount: unmountQa } = renderViewer({
        ...imageFile,
        id: "file-pmi-qa",
        name: "Reporte de Pruebas QA.csv",
        category: "general",
        file_type: "text/csv",
      });
      expect(screen.getByTestId("file-viewer-pmi-role")).toHaveTextContent(
        "Evidencia QA / DoD"
      );
      expect(screen.getByTestId("file-viewer-pmi-version")).toHaveTextContent(
        "Sin version explicita"
      );
      unmountQa();

      // Entregable Operativo (fallback)
      const { unmount: unmountOperational } = renderViewer({
        ...imageFile,
        id: "file-pmi-operational",
        name: "Registro Fotográfico de Obra.jpg",
        file_type: "image/jpeg",
      });
      expect(screen.getByTestId("file-viewer-pmi-role")).toHaveTextContent(
        "Entregable Operativo"
      );
      unmountOperational();
    });

    it("refleja el vínculo WBS (trazabilidad a paquete de trabajo) en la franja", () => {
      // Vinculado a tarea → Paquete WBS
      const { unmount: unmountLinked } = renderViewer({
        ...imageFile,
        id: "file-wbs-linked",
        name: "Acta_Comite_final.docx",
        task_id: "task-9",
        task_title: "Hito de Aprobación",
        file_type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      });
      expect(screen.getByTestId("file-viewer-pmi-wbs-link")).toHaveTextContent(
        "Vinculado a Paquete WBS"
      );
      unmountLinked();

      // Sin tarea vinculada → Artefacto General de Proyecto
      const { unmount: unmountUnlinked } = renderViewer({
        ...imageFile,
        id: "file-wbs-unlinked",
        name: "Registro Fotográfico de Obra.jpg",
        task_id: null,
        task_title: null,
        file_type: "image/jpeg",
      });
      expect(screen.getByTestId("file-viewer-pmi-wbs-link")).toHaveTextContent(
        "Artefacto General de Proyecto"
      );
      unmountUnlinked();
    });
  });
});

