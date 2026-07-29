import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import type { PageBuilderState } from "@/hooks/usePageBuilder";
import { createMockCmsSection } from "@/test-utils/factories";
import CmsBuilderPage from "./page";

// ── Mocks ───────────────────────────────────────────────────────────────────

let mockAuth: { token: string | null; user: { role: string } | null } = {
  token: "mock-token",
  user: { role: "admin" },
};

vi.mock("@/context/AuthContext", () => ({
  useAuth: () => mockAuth,
}));

vi.mock("@/lib/cms/permissions", () => ({
  canEditCms: (role?: string | null) => role === "admin",
  canPublishCms: (role?: string | null) => role === "admin",
}));

vi.mock("@/hooks/usePageBuilder", () => ({
  usePageBuilder: vi.fn(),
}));

vi.mock("@/components/cms/builder/BuilderSidebar", () => ({
  default: ({ builder }: { builder: PageBuilderState }) => (
    <div data-testid="builder-sidebar">Sidebar · {builder.siteKey}</div>
  ),
}));

vi.mock("@/components/cms/builder/BuilderCanvas", () => ({
  default: ({ builder }: { builder: PageBuilderState }) => (
    <div data-testid="builder-canvas">Canvas · {builder.activeSlug || "empty"}</div>
  ),
}));

vi.mock("@/components/cms/builder/BuilderRightPanel", () => ({
  default: ({ builder }: { builder: PageBuilderState }) => (
    <div data-testid="builder-right-panel">RightPanel · {builder.activeRightTab}</div>
  ),
}));

vi.mock("@/components/cms/builder/MediaPicker", () => ({
  default: ({
    open,
    selectedUrl,
    onClose,
    onSelect,
  }: {
    open: boolean;
    selectedUrl?: string;
    onClose: () => void;
    onSelect: (item: { url: string }) => void;
  }) => (
    <div data-testid="media-picker">
      <span data-testid="media-picker-open">{open ? "open" : "closed"}</span>
      <span data-testid="media-picker-selected-url">{selectedUrl ?? "none"}</span>
      <button onClick={() => onClose()}>Close</button>
      <button onClick={() => onSelect({ url: "https://example.com/selected.jpg" })}>Select</button>
    </div>
  ),
}));

import { usePageBuilder } from "@/hooks/usePageBuilder";

const mockUsePageBuilder = usePageBuilder as unknown as ReturnType<typeof vi.fn>;

// ── Helpers ─────────────────────────────────────────────────────────────────

function createMockBuilder(overrides: Partial<PageBuilderState> = {}): PageBuilderState {
  const base: Partial<PageBuilderState> = {
    token: "mock-token",
    siteKey: "ccf",
    activeSlug: "home",
    activeRightTab: "config",
    mediaPickerOpen: false,
    mediaPickerTarget: "section",
    activeSection: null,
    seoImageDraft: "",
    setMediaPickerOpen: vi.fn(),
    updateSectionPropsLocal: vi.fn(),
    saveSectionProps: vi.fn(),
    setSeoImageDraft: vi.fn(),
  };
  return { ...base, ...overrides } as unknown as PageBuilderState;
}

// ── Tests ───────────────────────────────────────────────────────────────────

describe("CmsBuilderPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAuth = { token: "mock-token", user: { role: "admin" } };
  });

  it("renders the main builder layout and child components", () => {
    const builder = createMockBuilder({ siteKey: "test-site", activeSlug: "about" });
    mockUsePageBuilder.mockReturnValue(builder);

    render(<CmsBuilderPage />);

    expect(screen.getByRole("main")).toBeInTheDocument();
    expect(screen.getByRole("main")).toHaveAttribute("aria-label", "Constructor visual CMS");
    expect(screen.getByText(/constructor visual multisitio/i)).toBeInTheDocument();
    expect(screen.getByTestId("builder-sidebar")).toHaveTextContent("test-site");
    expect(screen.getByTestId("builder-canvas")).toHaveTextContent("about");
    expect(screen.getByTestId("builder-right-panel")).toBeInTheDocument();
  });

  it("passes token and computed permissions to usePageBuilder", () => {
    mockUsePageBuilder.mockReturnValue(createMockBuilder());

    render(<CmsBuilderPage />);

    expect(mockUsePageBuilder).toHaveBeenCalledWith(
      expect.objectContaining({
        token: "mock-token",
        canEdit: true,
        canPublish: true,
      }),
    );
  });

  it("passes canEdit=false and canPublish=false for non-admin users", () => {
    mockAuth = { token: "mock-token", user: { role: "lector" } };
    mockUsePageBuilder.mockReturnValue(createMockBuilder());

    render(<CmsBuilderPage />);

    expect(mockUsePageBuilder).toHaveBeenCalledWith(
      expect.objectContaining({
        canEdit: false,
        canPublish: false,
      }),
    );
  });

  it("passes empty token when user is not authenticated", () => {
    mockAuth = { token: null, user: null };
    mockUsePageBuilder.mockReturnValue(createMockBuilder());

    render(<CmsBuilderPage />);

    expect(mockUsePageBuilder).toHaveBeenCalledWith(
      expect.objectContaining({
        token: null,
        canEdit: false,
        canPublish: false,
      }),
    );
  });

  it("does not render MediaPicker when mediaPickerOpen is false", () => {
    const builder = createMockBuilder({ mediaPickerOpen: false });
    mockUsePageBuilder.mockReturnValue(builder);

    render(<CmsBuilderPage />);

    expect(screen.queryByTestId("media-picker")).not.toBeInTheDocument();
  });

  it("renders MediaPicker with the active section image URL when target is section", () => {
    const builder = createMockBuilder({
      mediaPickerOpen: true,
      mediaPickerTarget: "section",
      activeSection: createMockCmsSection("hero", {
        id: "section-1",
        props_json: { image_url: "https://example.com/hero.jpg" },
      }),
    });
    mockUsePageBuilder.mockReturnValue(builder);

    render(<CmsBuilderPage />);

    expect(screen.getByTestId("media-picker-open")).toHaveTextContent("open");
    expect(screen.getByTestId("media-picker-selected-url")).toHaveTextContent("https://example.com/hero.jpg");
  });

  it("uses bg_image for hero sections when selecting an image for a section", () => {
    const updateSectionPropsLocal = vi.fn();
    const saveSectionProps = vi.fn();
    const setSeoImageDraft = vi.fn();

    const builder = createMockBuilder({
      mediaPickerOpen: true,
      mediaPickerTarget: "section",
      activeSection: createMockCmsSection("hero", {
        id: "section-1",
        props_json: { title: "Hero" },
      }),
      updateSectionPropsLocal,
      saveSectionProps,
      setSeoImageDraft,
    });
    mockUsePageBuilder.mockReturnValue(builder);

    render(<CmsBuilderPage />);

    fireEvent.click(screen.getByRole("button", { name: /select/i }));
    expect(updateSectionPropsLocal).toHaveBeenCalledWith({ title: "Hero", bg_image: "https://example.com/selected.jpg" });
    expect(saveSectionProps).toHaveBeenCalledWith({ title: "Hero", bg_image: "https://example.com/selected.jpg" });
    expect(setSeoImageDraft).not.toHaveBeenCalled();
  });

  it("uses image_url for non-hero sections when selecting an image for a section", () => {
    const updateSectionPropsLocal = vi.fn();
    const saveSectionProps = vi.fn();

    const builder = createMockBuilder({
      mediaPickerOpen: true,
      mediaPickerTarget: "section",
      activeSection: createMockCmsSection("cards", {
        id: "section-1",
        props_json: { title: "Cards" },
      }),
      updateSectionPropsLocal,
      saveSectionProps,
    });
    mockUsePageBuilder.mockReturnValue(builder);

    render(<CmsBuilderPage />);

    fireEvent.click(screen.getByRole("button", { name: /select/i }));
    expect(updateSectionPropsLocal).toHaveBeenCalledWith({ title: "Cards", image_url: "https://example.com/selected.jpg" });
    expect(saveSectionProps).toHaveBeenCalledWith({ title: "Cards", image_url: "https://example.com/selected.jpg" });
  });

  it("updates SEO image draft when target is seo and an image is selected", () => {
    const setSeoImageDraft = vi.fn();
    const updateSectionPropsLocal = vi.fn();
    const saveSectionProps = vi.fn();

    const builder = createMockBuilder({
      mediaPickerOpen: true,
      mediaPickerTarget: "seo",
      seoImageDraft: "https://example.com/seo.jpg",
      setSeoImageDraft,
      updateSectionPropsLocal,
      saveSectionProps,
    });
    mockUsePageBuilder.mockReturnValue(builder);

    render(<CmsBuilderPage />);

    fireEvent.click(screen.getByRole("button", { name: /select/i }));
    expect(setSeoImageDraft).toHaveBeenCalledWith("https://example.com/selected.jpg");
    expect(updateSectionPropsLocal).not.toHaveBeenCalled();
    expect(saveSectionProps).not.toHaveBeenCalled();
  });

  it("closes the media picker when onClose is triggered", () => {
    const setMediaPickerOpen = vi.fn();
    const builder = createMockBuilder({
      mediaPickerOpen: true,
      setMediaPickerOpen,
    });
    mockUsePageBuilder.mockReturnValue(builder);

    const { rerender } = render(<CmsBuilderPage />);

    fireEvent.click(screen.getByRole("button", { name: /close/i }));
    expect(setMediaPickerOpen).toHaveBeenCalledWith(false);

    mockUsePageBuilder.mockReturnValue({ ...builder, mediaPickerOpen: false });
    rerender(<CmsBuilderPage />);
    expect(screen.queryByTestId("media-picker")).not.toBeInTheDocument();
  });

  it("shows the SEO image URL in MediaPicker when target is seo", () => {
    const builder = createMockBuilder({
      mediaPickerOpen: true,
      mediaPickerTarget: "seo",
      seoImageDraft: "https://example.com/seo.jpg",
    });
    mockUsePageBuilder.mockReturnValue(builder);

    render(<CmsBuilderPage />);

    expect(screen.getByTestId("media-picker-selected-url")).toHaveTextContent("https://example.com/seo.jpg");
  });
});
