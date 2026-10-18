import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/components/projects/ProjectsShell", () => ({
  default: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}));

import ProjectAutomationsPage from "./page";

describe("ProjectAutomationsPage compatibility landing", () => {
  it("directs users to project-scoped automation management", () => {
    render(<ProjectAutomationsPage />);

    expect(
      screen.getByRole("heading", { name: "Administra las reglas desde su proyecto" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Ir a mis proyectos" }),
    ).toHaveAttribute("href", "/plataforma/projects");
  });

  it("renders PMI §4.4 & §8.2 process automation governance banner and pillars", () => {
    render(<ProjectAutomationsPage />);

    const banner = screen.getByTestId("projects-automations-pmi-banner");
    expect(banner).toHaveTextContent(
      "Gobernanza de Flujos Automatizados y Control de Procesos · PMI §4.4 & §8.2",
    );

    const pillars = screen.getByTestId("projects-automations-pmi-pillars");
    expect(pillars).toHaveTextContent("Escalamiento Automático SLA (§6.6)");
    expect(pillars).toHaveTextContent("Transición Stage-Gate Auditable (§4.3)");
    expect(pillars).toHaveTextContent("Aislamiento Multi-Proyecto y RBAC (§4.6)");
  });
});
