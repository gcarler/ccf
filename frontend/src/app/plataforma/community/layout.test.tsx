import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import CommunityLayout from "./layout";

vi.mock("@/components/WorkspaceLayout", () => ({
  default: ({ sidebarSections, children }: {
    sidebarSections: Array<{ title: string; items: Array<{ label: string; href: string }> }>;
    children: ReactNode;
  }) => (
    <div>
      <nav aria-label="Community navigation">
        {sidebarSections.flatMap((section) => section.items).map((item) => (
          <a key={item.label} href={item.href}>{item.label}</a>
        ))}
      </nav>
      {children}
    </div>
  ),
}));

describe("CommunityLayout", () => {
  it("keeps all community sidebar destinations inside the platform route tree", () => {
    render(<CommunityLayout><p>Contenido</p></CommunityLayout>);

    const navigation = within(screen.getByRole("navigation", { name: "Community navigation" }));
    const links = navigation.getAllByRole("link");

    expect(links).toHaveLength(9);
    for (const link of links) {
      expect(link.getAttribute("href")).toMatch(/^\/plataforma\//);
    }
  });
});
