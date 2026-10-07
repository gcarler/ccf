import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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
    mocks.apiFetch.mockImplementation((path: string) =>
      path.endsWith("/summary") ? Promise.resolve(summary) : Promise.resolve([unsafeFile]),
    );
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
