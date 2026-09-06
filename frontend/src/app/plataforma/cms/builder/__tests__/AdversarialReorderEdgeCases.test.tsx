/**
 * Empirical Adversarial Test Suite for Milestone 2:
 * Edge cases, boundary conditions, disabled button behavior, and data-testid completeness.
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import PuckBuilderPage, { type ContentSection } from "../page";
import * as cmsV2 from "@/lib/cms/v2";

const PublicContentEditor = (PuckBuilderPage as unknown as {
  PublicContentEditor: React.ComponentType<{
    siteKey: string;
    pageSlug: string;
    sections: ContentSection[];
    token: string;
    canEdit: boolean;
    canPublish: boolean;
    onBack: () => void;
    onSectionsChange?: (sections: ContentSection[]) => void;
  }>;
}).PublicContentEditor;

// ── Mocks ───────────────────────────────────────────────────────────────────

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams("site=ccf&page=home"),
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({
    token: "mock-token",
    user: { role: "admin" },
  }),
}));

vi.mock("@/lib/cms/permissions", () => ({
  canEditCms: () => true,
  canPublishCms: () => true,
}));

vi.mock("@/lib/cms/v2", () => ({
  reorderCmsSections: vi.fn(),
  patchCmsSection: vi.fn(),
  workflowCmsPage: vi.fn(),
  listCmsSections: vi.fn(),
}));

vi.mock("@/lib/http", () => ({
  apiFetch: vi.fn().mockImplementation(() => Promise.resolve(null)),
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

vi.mock("@puckeditor/core", () => ({
  Puck: () => <div data-testid="puck-mock" />,
}));

vi.mock("@/components/cms/builder/MediaPicker", () => ({
  default: () => null,
}));

vi.mock("@/components/ui/OptimizedImage", () => ({
  default: (props: { src?: string; alt?: string }) => (
    <img src={props.src} alt={props.alt || "mock"} />
  ),
}));

// ── Test Fixtures ───────────────────────────────────────────────────────────

const createFiveSections = (): ContentSection[] => [
  { id: "sec-hero", section_key: "hero", type: "hero", sort_order: 0, props_json: { title_lead: "Hero" } },
  { id: "sec-welcome", section_key: "welcome", type: "feed", sort_order: 1, props_json: { title: "Welcome" } },
  { id: "sec-activities", section_key: "activities", type: "events_calendar", sort_order: 2, props_json: { title: "Activities" } },
  { id: "sec-newsletter", section_key: "newsletter", type: "newsletter", sort_order: 3, props_json: { title: "Newsletter" } },
  { id: "sec-discover", section_key: "discover_cta", type: "cta_block", sort_order: 4, props_json: { title: "Discover" } },
];

describe("Adversarial Reordering Edge Cases & Boundary Conditions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Edge Case: sections length 0", () => {
    it("renders cleanly without throwing when sections is empty array []", () => {
      const onBackMock = vi.fn();
      const { container } = render(
        <PublicContentEditor
          siteKey="ccf"
          pageSlug="home"
          sections={[]}
          token="mock-token"
          canEdit={true}
          canPublish={true}
          onBack={onBackMock}
        />
      );

      // Verify no cards are rendered
      const cards = screen.queryAllByTestId(/^section-card-/);
      expect(cards).toHaveLength(0);

      // Verify page layout is still intact
      expect(screen.getByRole("heading", { name: /\/home/i })).toBeInTheDocument();
      expect(container.querySelector("main")).toBeInTheDocument();
    });

    it("allows saveDraft and publish actions with empty sections array without crashing", async () => {
      render(
        <PublicContentEditor
          siteKey="ccf"
          pageSlug="home"
          sections={[]}
          token="mock-token"
          canEdit={true}
          canPublish={true}
          onBack={vi.fn()}
        />
      );

      const saveBtn = screen.getByRole("button", { name: /Guardar/i });
      fireEvent.click(saveBtn);
      expect(cmsV2.reorderCmsSections).not.toHaveBeenCalled();
    });
  });

  describe("Edge Case: sections length 1", () => {
    it("renders exactly 1 section with both move-up and move-down buttons strictly disabled", () => {
      const singleSection: ContentSection[] = [createFiveSections()[0]];

      render(
        <PublicContentEditor
          siteKey="ccf"
          pageSlug="home"
          sections={singleSection}
          token="mock-token"
          canEdit={true}
          canPublish={true}
          onBack={vi.fn()}
        />
      );

      const cards = screen.getAllByTestId(/^section-card-/);
      expect(cards).toHaveLength(1);

      const moveUp = screen.getByTestId("move-up-sec-hero");
      const moveDown = screen.getByTestId("move-down-sec-hero");

      expect(moveUp).toBeDisabled();
      expect(moveDown).toBeDisabled();
      expect(moveUp).toHaveAttribute("disabled");
      expect(moveDown).toHaveAttribute("disabled");
    });

    it("clicking disabled move-up or move-down on single section does NOT trigger reorder API", () => {
      const singleSection: ContentSection[] = [createFiveSections()[0]];

      render(
        <PublicContentEditor
          siteKey="ccf"
          pageSlug="home"
          sections={singleSection}
          token="mock-token"
          canEdit={true}
          canPublish={true}
          onBack={vi.fn()}
        />
      );

      fireEvent.click(screen.getByTestId("move-up-sec-hero"));
      fireEvent.click(screen.getByTestId("move-down-sec-hero"));

      expect(cmsV2.reorderCmsSections).not.toHaveBeenCalled();
    });
  });

  describe("Edge Case: Disabled Buttons Non-Clickability & Pointer Events", () => {
    it("ensures disabled buttons have disabled attribute, disabled styling classes, and block action execution", () => {
      const sections = createFiveSections();

      render(
        <PublicContentEditor
          siteKey="ccf"
          pageSlug="home"
          sections={sections}
          token="mock-token"
          canEdit={true}
          canPublish={true}
          onBack={vi.fn()}
        />
      );

      // First item: move-up must be disabled
      const firstMoveUp = screen.getByTestId("move-up-sec-hero");
      expect(firstMoveUp).toBeDisabled();
      expect(firstMoveUp).toHaveAttribute("disabled");
      expect(firstMoveUp.className).toContain("disabled:cursor-not-allowed");
      expect(firstMoveUp.className).toContain("disabled:opacity-30");

      // Last item: move-down must be disabled
      const lastMoveDown = screen.getByTestId("move-down-sec-discover");
      expect(lastMoveDown).toBeDisabled();
      expect(lastMoveDown).toHaveAttribute("disabled");
      expect(lastMoveDown.className).toContain("disabled:cursor-not-allowed");
      expect(lastMoveDown.className).toContain("disabled:opacity-30");

      // Attempt clicking boundary disabled buttons
      fireEvent.click(firstMoveUp);
      fireEvent.click(lastMoveDown);

      expect(cmsV2.reorderCmsSections).not.toHaveBeenCalled();
    });

    it("ensures when canEdit is false, every single move-up and move-down button has disabled attribute and clicks do nothing", () => {
      const sections = createFiveSections();

      render(
        <PublicContentEditor
          siteKey="ccf"
          pageSlug="home"
          sections={sections}
          token="mock-token"
          canEdit={false}
          canPublish={false}
          onBack={vi.fn()}
        />
      );

      for (const sec of sections) {
        const moveUp = screen.getByTestId(`move-up-${sec.id}`);
        const moveDown = screen.getByTestId(`move-down-${sec.id}`);
        expect(moveUp).toBeDisabled();
        expect(moveDown).toBeDisabled();

        fireEvent.click(moveUp);
        fireEvent.click(moveDown);
      }

      expect(cmsV2.reorderCmsSections).not.toHaveBeenCalled();
    });
  });

  describe("Edge Case: data-testid completeness across all sections", () => {
    it("verifies data-testid is present on every section card, reorder control group, move-up, and move-down", () => {
      const sections = createFiveSections();

      render(
        <PublicContentEditor
          siteKey="ccf"
          pageSlug="home"
          sections={sections}
          token="mock-token"
          canEdit={true}
          canPublish={true}
          onBack={vi.fn()}
        />
      );

      expect(screen.getAllByTestId(/^section-card-/)).toHaveLength(5);

      for (const sec of sections) {
        // 1. section-card-${id}
        const card = screen.getByTestId(`section-card-${sec.id}`);
        expect(card).toBeInTheDocument();
        expect(card).toHaveAttribute("data-section-id", sec.id);

        // 2. reorder-controls-${id}
        const controls = screen.getByTestId(`reorder-controls-${sec.id}`);
        expect(controls).toBeInTheDocument();

        // 3. move-up-${id}
        const moveUp = screen.getByTestId(`move-up-${sec.id}`);
        expect(moveUp).toBeInTheDocument();
        expect(moveUp).toHaveAttribute("aria-label", "Mover arriba");

        // 4. move-down-${id}
        const moveDown = screen.getByTestId(`move-down-${sec.id}`);
        expect(moveDown).toBeInTheDocument();
        expect(moveDown).toHaveAttribute("aria-label", "Mover abajo");
      }
    });
  });

  describe("Edge Case: Unordered incoming sort_order normalization", () => {
    it("correctly sorts incoming sections by sort_order ASC even if provided in scrambled order", () => {
      const scrambledSections: ContentSection[] = [
        { id: "sec-discover", section_key: "discover_cta", type: "cta_block", sort_order: 4, props_json: {} },
        { id: "sec-hero", section_key: "hero", type: "hero", sort_order: 0, props_json: {} },
        { id: "sec-activities", section_key: "activities", type: "events_calendar", sort_order: 2, props_json: {} },
        { id: "sec-welcome", section_key: "welcome", type: "feed", sort_order: 1, props_json: {} },
        { id: "sec-newsletter", section_key: "newsletter", type: "newsletter", sort_order: 3, props_json: {} },
      ];

      render(
        <PublicContentEditor
          siteKey="ccf"
          pageSlug="home"
          sections={scrambledSections}
          token="mock-token"
          canEdit={true}
          canPublish={true}
          onBack={vi.fn()}
        />
      );

      const cards = screen.getAllByTestId(/^section-card-/);
      expect(cards[0]).toHaveAttribute("data-section-id", "sec-hero");
      expect(cards[1]).toHaveAttribute("data-section-id", "sec-welcome");
      expect(cards[2]).toHaveAttribute("data-section-id", "sec-activities");
      expect(cards[3]).toHaveAttribute("data-section-id", "sec-newsletter");
      expect(cards[4]).toHaveAttribute("data-section-id", "sec-discover");
    });
  });
});
