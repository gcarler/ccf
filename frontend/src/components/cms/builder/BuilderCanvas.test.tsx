import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import type { CmsSection } from "@/types/cms-v2";
import type { PageBuilderState } from "@/hooks/usePageBuilder";
import BuilderCanvas from "./BuilderCanvas";
import { createMockCmsSection } from "@/test-utils/factories";

// ── Mocks ─────────────────────────────────────────────────────────────────────

vi.mock("@/components/cms/builder/SectionPreview", () => ({
  SectionPreview: ({ section }: { section: CmsSection }) => (
    <div data-testid={`preview-${section.id}`}>{section.type}</div>
  ),
  SectionRenderPreview: ({ section }: { section: CmsSection }) => (
    <div data-testid={`render-${section.id}`}>{section.type}</div>
  ),
}));

vi.mock("@/lib/cms/v2", () => ({
  reorderCmsSections: vi.fn(),
}));

vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({ token: "mock-token", user: { id: "u1", name: "Test User", role: "admin" } }),
}));

// ── Helpers ─────────────────────────────────────────────────────────────────

function createMockBuilder(overrides: Partial<PageBuilderState> = {}): PageBuilderState {
  const base: Partial<PageBuilderState> = {
    sections: [],
    activeSectionId: null,
    setActiveSectionId: vi.fn(),
    activeSlug: "home",
    canEdit: true,
    siteKey: "ccf",
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

// ── Tests ───────────────────────────────────────────────────────────────────

describe("BuilderCanvas", () => {
  it("renders the canvas toolbar and empty state", () => {
    const builder = createMockBuilder();
    render(<BuilderCanvas builder={builder} />);

    expect(screen.getByText(/Canvas · \/home/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /esquema/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /render/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /desktop/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /mobile/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /añadir/i })).toBeInTheDocument();
    expect(screen.getByText(/No hay secciones en esta página/i)).toBeInTheDocument();
  });

  it("renders sections and marks the active one", () => {
    const sections = [
      createMockCmsSection("hero", { id: "sec-1", props_json: { title: "Hero principal" } }),
      createMockCmsSection("rich_text", { id: "sec-2", props_json: { title: "Texto" } }),
    ];
    const setActiveSectionId = vi.fn();
    const builder = createMockBuilder({
      sections,
      activeSectionId: "sec-1",
      setActiveSectionId,
    });

    render(<BuilderCanvas builder={builder} />);

    expect(screen.getByTestId("preview-sec-1")).toBeInTheDocument();
    expect(screen.getByTestId("preview-sec-2")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Hero principal"));
    expect(setActiveSectionId).toHaveBeenCalledWith("sec-1");
  });

  it("toggles canvas mode and preview device", () => {
    const setCanvasMode = vi.fn();
    const setPreviewDevice = vi.fn();
    const builder = createMockBuilder({ setCanvasMode, setPreviewDevice });

    render(<BuilderCanvas builder={builder} />);

    fireEvent.click(screen.getByRole("button", { name: /render/i }));
    expect(setCanvasMode).toHaveBeenCalledWith("render");

    fireEvent.click(screen.getByRole("button", { name: /mobile/i }));
    expect(setPreviewDevice).toHaveBeenCalledWith("mobile");
  });

  it("calls addSection when clicking Añadir", () => {
    const addSection = vi.fn();
    const builder = createMockBuilder({ addSection });

    render(<BuilderCanvas builder={builder} />);

    fireEvent.click(screen.getByRole("button", { name: /añadir/i }));
    expect(addSection).toHaveBeenCalled();
  });

  it("disables add section when canEdit is false", () => {
    const addSection = vi.fn();
    const builder = createMockBuilder({ addSection, canEdit: false });

    render(<BuilderCanvas builder={builder} />);

    const button = screen.getByRole("button", { name: /añadir/i });
    expect(button).toBeDisabled();
    fireEvent.click(button);
    expect(addSection).not.toHaveBeenCalled();
  });

  it("calls moveSection with up/down direction", () => {
    const moveSection = vi.fn();
    const sections = [
      createMockCmsSection("hero", { id: "sec-1", props_json: { title: "Hero" } }),
      createMockCmsSection("rich_text", { id: "sec-2", props_json: { title: "Texto" } }),
    ];
    const builder = createMockBuilder({ sections, moveSection });

    render(<BuilderCanvas builder={builder} />);

    const upButtons = screen.getAllByRole("button", { name: /subir sección/i });
    const downButtons = screen.getAllByRole("button", { name: /bajar sección/i });

    fireEvent.click(upButtons[1]);
    expect(moveSection).toHaveBeenCalledWith("sec-2", "up");

    fireEvent.click(downButtons[0]);
    expect(moveSection).toHaveBeenCalledWith("sec-1", "down");
  });

  it("renders the scroll heatmap overlay when enabled", () => {
    const sections = [createMockCmsSection("hero", { id: "sec-1" })];
    const builder = createMockBuilder({
      sections,
      showHeatmap: true,
      heatmapType: "scroll",
    });

    render(<BuilderCanvas builder={builder} />);

    expect(screen.getByText(/100% de usuarios visualizan esta zona/i)).toBeInTheDocument();
  });

  it("renders the clicks heatmap overlay when enabled", () => {
    const sections = [createMockCmsSection("hero", { id: "sec-1" })];
    const builder = createMockBuilder({
      sections,
      showHeatmap: true,
      heatmapType: "clicks",
    });

    render(<BuilderCanvas builder={builder} />);

    expect(screen.getByText(/72%/i)).toBeInTheDocument();
  });

  it("renders the attention heatmap overlay when enabled", () => {
    const sections = [createMockCmsSection("hero", { id: "sec-1" })];
    const builder = createMockBuilder({
      sections,
      showHeatmap: true,
      heatmapType: "attention",
    });

    const { container } = render(<BuilderCanvas builder={builder} />);

    expect(container.querySelector('[data-heatmap-type="attention"]')).toBeInTheDocument();
  });

  it("switches to render preview when canvasMode is render", () => {
    const sections = [createMockCmsSection("hero", { id: "sec-1" })];
    const builder = createMockBuilder({ sections, canvasMode: "render" });

    render(<BuilderCanvas builder={builder} />);

    expect(screen.getByTestId("render-sec-1")).toBeInTheDocument();
    expect(screen.queryByTestId("preview-sec-1")).not.toBeInTheDocument();
  });

  it("reloads theme when the reload button is clicked", () => {
    const reloadTheme = vi.fn();
    const builder = createMockBuilder({ reloadTheme });

    render(<BuilderCanvas builder={builder} />);

    fireEvent.click(screen.getByRole("button", { name: /recargar tema/i }));
    expect(reloadTheme).toHaveBeenCalled();
  });

  it("updates newSectionType when selecting a section type", () => {
    const setNewSectionType = vi.fn();
    const builder = createMockBuilder({ setNewSectionType });

    render(<BuilderCanvas builder={builder} />);

    const select = screen.getByRole("combobox");
    fireEvent.change(select, { target: { value: "rich_text" } });
    expect(setNewSectionType).toHaveBeenCalledWith("rich_text");
  });

  it("disables move up for the first section and move down for the last section", () => {
    const moveSection = vi.fn();
    const sections = [
      createMockCmsSection("hero", { id: "sec-1", props_json: { title: "Hero" } }),
      createMockCmsSection("rich_text", { id: "sec-2", props_json: { title: "Texto" } }),
    ];
    const builder = createMockBuilder({ sections, moveSection });

    render(<BuilderCanvas builder={builder} />);

    const upButtons = screen.getAllByRole("button", { name: /subir sección/i });
    const downButtons = screen.getAllByRole("button", { name: /bajar sección/i });

    expect(upButtons[0]).toBeDisabled();
    expect(downButtons[downButtons.length - 1]).toBeDisabled();

    fireEvent.click(upButtons[0]);
    fireEvent.click(downButtons[downButtons.length - 1]);
    expect(moveSection).not.toHaveBeenCalled();
  });
});
