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
});
