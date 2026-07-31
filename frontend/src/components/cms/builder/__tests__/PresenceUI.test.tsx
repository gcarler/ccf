import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import BuilderCanvas from "../BuilderCanvas";
import type { PageBuilderState } from "@/hooks/usePageBuilder";
import type { PresenceUser } from "@/hooks/usePresence";

// Mock usePresence to control presenceUsers state
const mockPresenceUsers: PresenceUser[] = [];
vi.mock("@/hooks/usePresence", () => ({
  usePresence: () => ({
    presenceUsers: mockPresenceUsers,
    isConnected: true,
  }),
}));

vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({
    token: "mock-token",
    user: { id: "u1", name: "Admin User", role: "admin" },
  }),
}));

vi.mock("@/components/cms/builder/SectionPreview", () => ({
  SectionPreview: () => <div>Preview</div>,
  SectionRenderPreview: () => <div>RenderPreview</div>,
}));

function createMockBuilder(overrides: Partial<PageBuilderState> = {}): PageBuilderState {
  const base: Partial<PageBuilderState> = {
    sections: [],
    activeSectionId: null,
    setActiveSectionId: vi.fn(),
    activeSlug: "home",
    canEdit: true,
    siteKey: "main",
    canvasMode: "esquema",
    setCanvasMode: vi.fn(),
    previewDevice: "desktop",
    setPreviewDevice: vi.fn(),
    showHeatmap: false,
    heatmapType: "clicks",
    draggedSectionId: null,
    setDraggedSectionId: vi.fn(),
    moveSection: vi.fn(),
    moveSectionToIndex: vi.fn(),
    loadSectionsAndVersions: vi.fn(),
    newSectionType: "hero",
    setNewSectionType: vi.fn(),
    addSection: vi.fn(),
    token: "fake-token",
    canvasTokens: {},
    canvasThemeName: "Default",
    themeLoading: false,
    reloadTheme: vi.fn(),
  };
  return { ...base, ...overrides } as unknown as PageBuilderState;
}

describe("Presence UI Component (BuilderCanvas)", () => {
  it("renders single active user with '1 persona editando ahora' label and tooltip", () => {
    mockPresenceUsers.length = 0;
    mockPresenceUsers.push({
      id: "u1",
      name: "Carlos Gomez",
      color: "#10B981",
      initials: "CG",
    });

    const builder = createMockBuilder();
    render(<BuilderCanvas builder={builder} />);

    expect(screen.getByText("1 persona editando ahora")).toBeInTheDocument();
    expect(screen.getByText("CG")).toBeInTheDocument();
    expect(screen.getByText("Carlos Gomez")).toBeInTheDocument();
  });

  it("renders multiple active users with plural label and avatar circles", () => {
    mockPresenceUsers.length = 0;
    mockPresenceUsers.push(
      { id: "u1", name: "Carlos Gomez", color: "#10B981", initials: "CG" },
      { id: "u2", name: "Elena Diaz", color: "#EF4444", initials: "ED" },
      { id: "u3", name: "Mateo Silva", color: "#8B5CF6", initials: "MS" }
    );

    const builder = createMockBuilder();
    render(<BuilderCanvas builder={builder} />);

    expect(screen.getByText("3 personas editando ahora")).toBeInTheDocument();
    expect(screen.getByText("CG")).toBeInTheDocument();
    expect(screen.getByText("ED")).toBeInTheDocument();
    expect(screen.getByText("MS")).toBeInTheDocument();
  });

  it("renders +N más indicator when there are more than 4 active users", () => {
    mockPresenceUsers.length = 0;
    mockPresenceUsers.push(
      { id: "u1", name: "User 1", color: "#3B82F6", initials: "U1" },
      { id: "u2", name: "User 2", color: "#10B981", initials: "U2" },
      { id: "u3", name: "User 3", color: "#F59E0B", initials: "U3" },
      { id: "u4", name: "User 4", color: "#EF4444", initials: "U4" },
      { id: "u5", name: "User 5", color: "#8B5CF6", initials: "U5" },
      { id: "u6", name: "User 6", color: "#EC4899", initials: "U6" }
    );

    const builder = createMockBuilder();
    render(<BuilderCanvas builder={builder} />);

    expect(screen.getByText("6 personas editando ahora")).toBeInTheDocument();
    expect(screen.getByText("+2 más")).toBeInTheDocument();
    // Only top 4 avatars are displayed directly
    expect(screen.getByText("U1")).toBeInTheDocument();
    expect(screen.getByText("U4")).toBeInTheDocument();
    expect(screen.queryByText("U5")).not.toBeInTheDocument();
  });
});
