import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { axe } from "jest-axe";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ProjectFileRecord, ProjectFilesSummary } from "@/types/projects";
import { ProjectDriveDrawer } from "./ProjectDriveDrawer";

const mocks = vi.hoisted(() => ({ apiFetch: vi.fn() }));

vi.mock("@/lib/http", () => ({ apiFetch: mocks.apiFetch }));
vi.mock("@/context/AuthContext", () => ({ useAuth: () => ({ token: "test-token" }) }));
vi.mock("@/components/ui/RightPanel", () => ({
  RightPanel: ({
    open,
    title,
    children,
  }: {
    open: boolean;
    title: string;
    children: ReactNode;
  }) => (open ? <section aria-label={title}>{children}</section> : null),
}));

const unsafeFile: ProjectFileRecord = {
  id: "file-1",
  project_id: "project-1",
  name: "Minuta sospechosa.pdf",
  category: "actas",
  file_source: "drive",
  file_url: "javascript:alert(document.domain)",
  file_type: "application/pdf",
  created_at: "2026-10-04T12:00:00Z",
};

const summary: ProjectFilesSummary = {
  project_id: "project-1",
  total_files: 1,
  total_size_bytes: 1024,
  by_source: { drive: 1 },
  by_category: { actas: 1 },
  files: [unsafeFile],
};

describe("ProjectDriveDrawer", () => {
  beforeEach(() => {
    mocks.apiFetch.mockReset();
    mocks.apiFetch.mockImplementation((path: string) => {
      if (path.endsWith("/summary")) return Promise.resolve(summary);
      if (path.endsWith("/tasks")) return Promise.resolve([]);
      return Promise.resolve([unsafeFile]);
    });
  });

  it("labels file actions and blocks unsafe historical URLs", async () => {
    const { container } = render(
      <ProjectDriveDrawer projectId="project-1" isOpen onClose={vi.fn()} />,
    );

    expect(await screen.findByText(unsafeFile.name)).toBeInTheDocument();
    expect(container.innerHTML).not.toMatch(/--(?:foreground|muted-foreground)\b/);
    expect(container.innerHTML).toContain("--text-primary");
    expect(container.innerHTML).toContain("--text-secondary");
    expect(screen.getByRole("button", { name: `Previsualizar ${unsafeFile.name}` })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: `Eliminar ${unsafeFile.name} de la bóveda` })).toBeInTheDocument();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
    expect((await axe(container)).violations).toEqual([]);

    fireEvent.click(screen.getByRole("button", { name: `Previsualizar ${unsafeFile.name}` }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/enlace.*se bloqueó/i);
    expect(document.querySelector("iframe, img, audio, video, a[href]")).toBeNull();
  });

  it("requires a drawer confirmation before removing a file from the vault", async () => {
    const { container } = render(
      <ProjectDriveDrawer projectId="project-1" isOpen onClose={vi.fn()} />,
    );

    expect(await screen.findByText(unsafeFile.name)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: `Eliminar ${unsafeFile.name} de la bóveda` }));
    expect(await screen.findByRole("complementary", { name: "Eliminar archivo de la bóveda" })).toBeInTheDocument();
    expect(mocks.apiFetch.mock.calls.some(([, options]) => options?.method === "DELETE")).toBe(false);
    expect((await axe(container)).violations).toEqual([]);

    fireEvent.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(await screen.findByText(unsafeFile.name)).toBeInTheDocument();
    expect(mocks.apiFetch.mock.calls.some(([, options]) => options?.method === "DELETE")).toBe(false);

    fireEvent.click(screen.getByRole("button", { name: `Eliminar ${unsafeFile.name} de la bóveda` }));
    fireEvent.click(await screen.findByRole("button", { name: "Eliminar" }));

    await waitFor(() => expect(mocks.apiFetch).toHaveBeenCalledWith(
      "/projects/project-1/files/file-1",
      expect.objectContaining({ method: "DELETE", token: "test-token" }),
    ));
  });

  it("keeps the file and confirmation visible when removal fails", async () => {
    mocks.apiFetch.mockImplementation((path: string, options?: { method?: string }) => {
      if (path.endsWith("/summary")) return Promise.resolve(summary);
      if (path.endsWith("/tasks")) return Promise.resolve([]);
      if (options?.method === "DELETE") return Promise.reject(new Error("Servicio no disponible"));
      return Promise.resolve([unsafeFile]);
    });

    render(<ProjectDriveDrawer projectId="project-1" isOpen onClose={vi.fn()} />);
    expect(await screen.findByText(unsafeFile.name)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: `Eliminar ${unsafeFile.name} de la bóveda` }));
    fireEvent.click(await screen.findByRole("button", { name: "Eliminar" }));

    expect(await screen.findByRole("complementary", { name: "Eliminar archivo de la bóveda" })).toBeInTheDocument();
    expect(screen.getByText(unsafeFile.name)).toBeInTheDocument();
  });
});

const actaLinked: ProjectFileRecord = {
  id: "file-acta",
  project_id: "project-1",
  name: "Acta Comité de Construcción.pdf",
  category: "actas",
  file_source: "local",
  file_url: "https://storage.example.com/acta.pdf",
  file_type: "application/pdf",
  task_id: "task-1",
  task_title: "Comité de Construcción mensual",
  created_at: "2026-10-10T08:00:00Z",
};

const planoOrphan: ProjectFileRecord = {
  id: "file-plano",
  project_id: "project-1",
  name: "Plano Nivel Sótano.dwg",
  category: "disenos",
  file_source: "local",
  file_url: "https://storage.example.com/plano.dwg",
  created_at: "2026-10-11T08:00:00Z",
};

const presupuestoOrphan: ProjectFileRecord = {
  id: "file-presupuesto",
  project_id: "project-1",
  name: "Presupuesto Q4.xlsx",
  category: "finanzas",
  file_source: "drive",
  file_url: "https://docs.google.com/spreadsheets/d/xyz",
  created_at: "2026-10-12T08:00:00Z",
};

const auditSummary: ProjectFilesSummary = {
  project_id: "project-1",
  total_files: 3,
  total_size_bytes: 3072,
  by_source: { drive: 1 },
  by_category: { actas: 1, disenos: 1, finanzas: 1 },
  files: [actaLinked, planoOrphan, presupuestoOrphan],
};

describe("ProjectDriveDrawer — Gestión de la Configuración y Trazabilidad EDT PMI", () => {
  beforeEach(() => {
    mocks.apiFetch.mockReset();
    mocks.apiFetch.mockImplementation((path: string) => {
      if (path.endsWith("/summary")) return Promise.resolve(auditSummary);
      if (path.endsWith("/tasks"))
        return Promise.resolve([{ id: "task-1", title: "Comité de Construcción mensual" }]);
      return Promise.resolve([actaLinked, planoOrphan, presupuestoOrphan]);
    });
  });

  it("presenta el diagnóstico de trazabilidad EDT y la cobertura documental en drive-pmi-config-audit", async () => {
    const { container } = render(
      <ProjectDriveDrawer projectId="project-1" isOpen onClose={vi.fn()} />,
    );

    const audit = await screen.findByTestId("drive-pmi-config-audit");
    const auditText = () => audit.textContent ?? "";
    // 1 vinculado / 3 totales → 33% de trazabilidad, 2 huérfanos sin paquete de trabajo
    expect(auditText()).toMatch(/Trazabilidad EDT:/i);
    expect(auditText()).toMatch(/33\s*%/);
    expect(auditText()).toMatch(/Entregables sin vínculo EDT/);
    expect(auditText()).toMatch(/Cobertura Documental PMI:/);
    expect(auditText()).toMatch(/3\s*\/4 pilares/);
    // Pilares: actas (cubierta), diseños (cubierta pese a alerta), finanzas (cubierta), informes pendiente
    expect(audit).toHaveTextContent("Gobernanza / Actas");
    expect(audit).toHaveTextContent("Línea Base Técnica");
    expect(audit).toHaveTextContent("Finanzas / Adquisiciones");
    expect(audit).toHaveTextContent("Informes / Aceptación");
    expect((await axe(container)).violations).toEqual([]);
  });

  it("filtra la lista visual por trazabilidad EDT con drive-wbs-traceability-filter", async () => {
    render(<ProjectDriveDrawer projectId="project-1" isOpen onClose={vi.fn()} />);
    await screen.findByTestId("drive-wbs-traceability-filter");

    // Todos: los 3 archivos visibles
    expect(screen.getByText(actaLinked.name)).toBeInTheDocument();
    expect(screen.getByText(planoOrphan.name)).toBeInTheDocument();
    expect(screen.getByText(presupuestoOrphan.name)).toBeInTheDocument();

    const filter = screen.getByTestId("drive-wbs-traceability-filter");

    // Huérfanos sin EDT: oculta el acta vinculada
    fireEvent.click(within(filter).getByRole("button", { name: "Huérfanos sin EDT" }));
    expect(screen.queryByText(actaLinked.name)).not.toBeInTheDocument();
    expect(screen.getByText(planoOrphan.name)).toBeInTheDocument();
    expect(screen.getByText(presupuestoOrphan.name)).toBeInTheDocument();

    // Vinculados a EDT: muestra solo el acta con paquete de trabajo
    fireEvent.click(within(filter).getByRole("button", { name: "Vinculados a EDT" }));
    expect(screen.getByText(actaLinked.name)).toBeInTheDocument();
    expect(screen.queryByText(planoOrphan.name)).not.toBeInTheDocument();
    expect(screen.queryByText(presupuestoOrphan.name)).not.toBeInTheDocument();

    // Retorno a Todos: reconstituye la lista completa
    fireEvent.click(within(filter).getByRole("button", { name: "Todos" }));
    expect(screen.getByText(actaLinked.name)).toBeInTheDocument();
    expect(screen.getByText(planoOrphan.name)).toBeInTheDocument();
    expect(screen.getByText(presupuestoOrphan.name)).toBeInTheDocument();
  });
});
