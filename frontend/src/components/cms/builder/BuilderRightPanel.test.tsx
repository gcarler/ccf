import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import type { PageBuilderState } from "@/hooks/usePageBuilder";
import type { CmsPage } from "@/types/cms-v2";
import BuilderRightPanel from "./BuilderRightPanel";

// ── Mocks ─────────────────────────────────────────────────────────────────────

vi.mock("@/components/ui/OptimizedImage", () => ({
  default: ({ src, alt }: { src: string; alt: string }) => <img src={src} alt={alt} />,
}));

vi.mock("./BuilderSectionInspector", () => ({
  default: () => <div data-testid="section-inspector" />,
}));

vi.mock("@/lib/cms/v2", () => ({
  getPageAnalytics: vi.fn().mockResolvedValue({
    total_views: 1234,
    daily_views: [{ views: 100 }, { views: 200 }],
    days: 7,
  }),
}));

// ── Helpers ─────────────────────────────────────────────────────────────────

function createMockBuilder(overrides: Partial<PageBuilderState> = {}): PageBuilderState {
  const base: Partial<PageBuilderState> = {
    activePage: {
      id: "page-1",
      site_id: "site-1",
      slug: "home",
      title: "Home",
      status: "draft",
      seo_json: {},
      published_version_id: null,
      publish_at: null,
      expires_at: null,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    } as CmsPage,
    activeSlug: "home",
    siteKey: "ccf",
    canEdit: true,
    canPublish: true,
    note: "",
    setNote: vi.fn(),
    versions: [],
    publishLogs: [],
    runWorkflow: vi.fn(),
    rollback: vi.fn(),
    savePageMetadata: vi.fn(),
    togglePageArchive: vi.fn(),
    pageTitleDraft: "Título",
    setPageTitleDraft: vi.fn(),
    pageSlugDraft: "home",
    setPageSlugDraft: vi.fn(),
    seoTitleDraft: "SEO Title",
    setSeoTitleDraft: vi.fn(),
    seoDescriptionDraft: "SEO Description",
    setSeoDescriptionDraft: vi.fn(),
    seoImageDraft: "",
    setSeoImageDraft: vi.fn(),
    seoCanonicalDraft: "",
    setSeoCanonicalDraft: vi.fn(),
    seoRobotsDraft: "",
    setSeoRobotsDraft: vi.fn(),
    seoKeyword: "keyword",
    setSeoKeyword: vi.fn(),
    seoAnalysis: { score: 75, checks: [] },
    readabilityScore: { score: 80, label: "Fácil de leer" },
    serpPreviewDevice: "desktop",
    setSerpPreviewDevice: vi.fn(),
    activeRightTab: "config",
    setActiveRightTab: vi.fn(),
    aiPrompt: "",
    setAiPrompt: vi.fn(),
    aiGenerating: false,
    aiOutput: "",
    aiTone: "warm",
    setAiTone: vi.fn(),
    aiTemplate: "aida",
    setAiTemplate: vi.fn(),
    handleAiGenerate: vi.fn(),
    handleAiImageGenerate: vi.fn(),
    handleInsertAiAsSection: vi.fn(),
    handleReplaceActiveSectionWithAi: vi.fn(),
    aiImagePrompt: "",
    setAiImagePrompt: vi.fn(),
    aiImageResult: "",
    setAiImageResult: vi.fn(),
    aiImageGenerating: false,
    showHeatmap: false,
    setShowHeatmap: vi.fn(),
    timeframe: "7d",
    setTimeframe: vi.fn(),
    heatmapType: "clicks",
    setHeatmapType: vi.fn(),
    abTestingActive: false,
    setAbTestingActive: vi.fn(),
    abTrafficSplit: 50,
    setAbTrafficSplit: vi.fn(),
    activeSite: null,
    setMediaPickerOpen: vi.fn(),
    setMediaPickerTarget: vi.fn(),
    activeSectionId: null,
    activeSection: null,
    updateSectionPropsLocal: vi.fn(),
    saveSectionProps: vi.fn(),
    sections: [],
  };
  return { ...base, ...overrides } as unknown as PageBuilderState;
}

// ── Tests ───────────────────────────────────────────────────────────────────

describe("BuilderRightPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the config tab by default", () => {
    const builder = createMockBuilder();
    render(<BuilderRightPanel builder={builder} />);

    expect(screen.getByText(/estado página/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/título de página/i)).toBeInTheDocument();
  });

  it("switches tabs when clicking the tab buttons", () => {
    const setActiveRightTab = vi.fn();
    const builder = createMockBuilder({ setActiveRightTab });

    render(<BuilderRightPanel builder={builder} />);

    fireEvent.click(screen.getByRole("button", { name: "SEO" }));
    expect(setActiveRightTab).toHaveBeenCalledWith("seo");

    fireEvent.click(screen.getByRole("button", { name: "Asistente IA" }));
    expect(setActiveRightTab).toHaveBeenCalledWith("ai");

    fireEvent.click(screen.getByRole("button", { name: "Métricas" }));
    expect(setActiveRightTab).toHaveBeenCalledWith("analytics");
  });

  it("calls savePageMetadata when clicking the save button", () => {
    const savePageMetadata = vi.fn();
    const builder = createMockBuilder({ savePageMetadata });

    render(<BuilderRightPanel builder={builder} />);

    fireEvent.click(screen.getByRole("button", { name: /guardar pagina\/seo/i }));
    expect(savePageMetadata).toHaveBeenCalled();
  });

  it("calls runWorkflow with the correct action for each workflow button", () => {
    const runWorkflow = vi.fn();
    const builder = createMockBuilder({ runWorkflow });

    render(<BuilderRightPanel builder={builder} />);

    fireEvent.click(screen.getByRole("button", { name: /review/i }));
    expect(runWorkflow).toHaveBeenCalledWith("submit_review");

    fireEvent.click(screen.getByRole("button", { name: /aprobar/i }));
    expect(runWorkflow).toHaveBeenCalledWith("approve");

    fireEvent.click(screen.getByRole("button", { name: /publicar/i }));
    expect(runWorkflow).toHaveBeenCalledWith("publish");

    fireEvent.click(screen.getByRole("button", { name: /draft/i }));
    expect(runWorkflow).toHaveBeenCalledWith("revert_draft");
  });

  it("disables workflow buttons when permissions are missing", () => {
    const runWorkflow = vi.fn();
    const builder = createMockBuilder({ canEdit: false, canPublish: false, runWorkflow });

    render(<BuilderRightPanel builder={builder} />);

    const reviewButton = screen.getByRole("button", { name: /review/i });
    const publishButton = screen.getByRole("button", { name: /publicar/i });

    expect(reviewButton).toBeDisabled();
    expect(publishButton).toBeDisabled();

    fireEvent.click(reviewButton);
    fireEvent.click(publishButton);
    expect(runWorkflow).not.toHaveBeenCalled();
  });

  it("updates draft inputs and calls setters", () => {
    const setPageTitleDraft = vi.fn();
    const setPageSlugDraft = vi.fn();
    const builder = createMockBuilder({ setPageTitleDraft, setPageSlugDraft });

    render(<BuilderRightPanel builder={builder} />);

    const titleInput = screen.getByPlaceholderText(/título de página/i);
    fireEvent.change(titleInput, { target: { value: "Nuevo título" } });
    expect(setPageTitleDraft).toHaveBeenCalledWith("Nuevo título");

    const slugInput = screen.getByPlaceholderText(/slug-de-pagina/i);
    fireEvent.change(slugInput, { target: { value: "nuevo-slug" } });
    expect(setPageSlugDraft).toHaveBeenCalledWith("nuevo-slug");
  });

  it("renders the SEO tab with score and checks", () => {
    const builder = createMockBuilder({
      activeRightTab: "seo",
      seoAnalysis: {
        score: 85,
        checks: [{ id: "check-1", label: "Check 1", passed: true, tip: "Tip", type: "success" }],
      },
    });

    render(<BuilderRightPanel builder={builder} />);

    expect(screen.getByText(/palabra clave objetivo/i)).toBeInTheDocument();
    expect(screen.getByText(/85%/i)).toBeInTheDocument();
    expect(screen.getByText(/check 1/i)).toBeInTheDocument();
  });

  it("toggles SERP preview device", () => {
    const setSerpPreviewDevice = vi.fn();
    const builder = createMockBuilder({ activeRightTab: "seo", setSerpPreviewDevice });

    render(<BuilderRightPanel builder={builder} />);

    fireEvent.click(screen.getByRole("button", { name: /móvil/i }));
    expect(setSerpPreviewDevice).toHaveBeenCalledWith("mobile");
  });

  it("renders the AI tab and triggers generation", () => {
    const setAiPrompt = vi.fn();
    const handleAiGenerate = vi.fn();
    const builder = createMockBuilder({
      activeRightTab: "ai",
      aiPrompt: "Prompt inicial",
      setAiPrompt,
      handleAiGenerate,
    });

    render(<BuilderRightPanel builder={builder} />);

    const textarea = screen.getByPlaceholderText(/ej: queremos invitar/i);
    fireEvent.change(textarea, { target: { value: "Prompt de prueba" } });
    expect(setAiPrompt).toHaveBeenCalledWith("Prompt de prueba");

    fireEvent.click(screen.getByRole("button", { name: /generar contenido ia/i }));
    expect(handleAiGenerate).toHaveBeenCalled();
  });

  it("shows AI output insertion buttons when aiOutput is present", () => {
    const handleInsertAiAsSection = vi.fn();
    const builder = createMockBuilder({
      activeRightTab: "ai",
      aiOutput: "Texto generado",
      handleInsertAiAsSection,
    });

    render(<BuilderRightPanel builder={builder} />);

    expect(screen.getByText(/texto generado/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /insertar final/i }));
    expect(handleInsertAiAsSection).toHaveBeenCalled();
  });

  it("fetches and displays analytics when the analytics tab is active", async () => {
    const setTimeframe = vi.fn();
    const builder = createMockBuilder({ activeRightTab: "analytics", setTimeframe });

    render(<BuilderRightPanel builder={builder} />);

    expect(screen.getByText(/visitas totales/i)).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText("1,234")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /30 días/i }));
    expect(setTimeframe).toHaveBeenCalledWith("30d");
  });

  it("toggles heatmap and heatmap type in analytics tab", () => {
    const setShowHeatmap = vi.fn();
    const setHeatmapType = vi.fn();
    const builder = createMockBuilder({
      activeRightTab: "analytics",
      showHeatmap: true,
      heatmapType: "clicks",
      setShowHeatmap,
      setHeatmapType,
    });

    render(<BuilderRightPanel builder={builder} />);

    fireEvent.click(screen.getByRole("button", { name: /scroll/i }));
    expect(setHeatmapType).toHaveBeenCalledWith("scroll");

    fireEvent.click(screen.getByRole("button", { name: /ver activo/i }));
    expect(setShowHeatmap).toHaveBeenCalledWith(false);
  });

  it("calls togglePageArchive when clicking the archive button", () => {
    const togglePageArchive = vi.fn();
    const builder = createMockBuilder({ togglePageArchive });

    render(<BuilderRightPanel builder={builder} />);

    fireEvent.click(screen.getByRole("button", { name: /archivar pagina/i }));
    expect(togglePageArchive).toHaveBeenCalled();
  });
});
