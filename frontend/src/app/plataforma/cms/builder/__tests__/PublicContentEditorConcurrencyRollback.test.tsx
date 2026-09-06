/**
 * Challenger 2 Empirical Stress Test Suite: Concurrency Locking, Rollback & Payload Contract
 * Milestone 2: Interactive Reordering Controls in CMS Builder
 */

import React from "react";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import PuckBuilderPage, { type ContentSection } from "../page";
import * as cmsV2 from "@/lib/cms/v2";
import { toast } from "sonner";

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

// ── Test Fixtures with Real UUIDs ───────────────────────────────────────────

const createRealisticSections = (): ContentSection[] => [
  {
    id: "f16d3cb1-c884-4a2a-8223-d6346588f701",
    section_key: "hero",
    type: "hero",
    sort_order: 0,
    props_json: { title_lead: "Bienvenidos a", title_accent: "CCF", title_tail: "Faro" },
  },
  {
    id: "ba35f51b-585b-48f3-82a3-2c66df0056a0",
    section_key: "welcome",
    type: "feed",
    sort_order: 1,
    props_json: { title: "Bienvenidos a Casa" },
  },
  {
    id: "cbc6c13c-7851-4483-818e-8ad9fa6b3acf",
    section_key: "activities",
    type: "events_calendar",
    sort_order: 2,
    props_json: { title: "Próximas Actividades" },
  },
  {
    id: "48233538-1c6b-4a68-a551-c47b61bb179a",
    section_key: "newsletter",
    type: "newsletter",
    sort_order: 3,
    props_json: { title: "Boletín Semanal" },
  },
  {
    id: "ae8443ae-278d-42b1-bfe5-376da142ef43",
    section_key: "discover_cta",
    type: "cta_block",
    sort_order: 4,
    props_json: { title: "Quiero conocer a Jesús" },
  },
];

describe("Challenger 2 Empirical Stress Tests: Concurrency, Rollback & Payload", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ── Test 1: Concurrency In-Flight Lock & Rapid Spam Clicks ─────────────────
  describe("Empirical Challenge: In-flight Lock & Spam Prevention", () => {
    it("strictly prevents duplicate API calls under 50 rapid clicks on the same button", async () => {
      const sections = createRealisticSections();
      let resolvePromise!: (val: unknown) => void;
      const pendingPromise = new Promise((resolve) => {
        resolvePromise = resolve;
      });
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      vi.mocked(cmsV2.reorderCmsSections).mockReturnValue(pendingPromise as any);

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

      const moveDownHero = screen.getByTestId("move-down-f16d3cb1-c884-4a2a-8223-d6346588f701");

      // Fire 50 rapid clicks in the exact same execution turn
      for (let i = 0; i < 50; i++) {
        fireEvent.click(moveDownHero);
      }

      // Assert only a single API call was initiated
      expect(cmsV2.reorderCmsSections).toHaveBeenCalledTimes(1);

      // Verify all buttons across all sections are disabled while in-flight
      for (const section of sections) {
        expect(screen.getByTestId(`move-up-${section.id}`)).toBeDisabled();
        expect(screen.getByTestId(`move-down-${section.id}`)).toBeDisabled();
      }

      // Resolve the in-flight request
      await act(async () => {
        resolvePromise([]);
      });

      // After resolution, verify toast was triggered exactly once
      expect(toast.success).toHaveBeenCalledTimes(1);
      expect(toast.success).toHaveBeenCalledWith("Sección movida hacia abajo");

      // Verify lock is released and a subsequent click can now trigger a new request
      vi.mocked(cmsV2.reorderCmsSections).mockResolvedValueOnce([]);
      const moveUpWelcome = screen.getByTestId("move-up-ba35f51b-585b-48f3-82a3-2c66df0056a0");
      expect(moveUpWelcome).toBeDisabled(); // welcome is now at index 0!

      const moveDownWelcome = screen.getByTestId("move-down-ba35f51b-585b-48f3-82a3-2c66df0056a0");
      expect(moveDownWelcome).toBeEnabled();

      fireEvent.click(moveDownWelcome);
      expect(cmsV2.reorderCmsSections).toHaveBeenCalledTimes(2);
    });

    it("strictly prevents concurrent calls when clicking different section buttons in flight", async () => {
      const sections = createRealisticSections();
      let resolvePromise!: (val: unknown) => void;
      const pendingPromise = new Promise((resolve) => {
        resolvePromise = resolve;
      });
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      vi.mocked(cmsV2.reorderCmsSections).mockReturnValue(pendingPromise as any);

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

      // Click move-down on hero (initiates request)
      fireEvent.click(screen.getByTestId("move-down-f16d3cb1-c884-4a2a-8223-d6346588f701"));
      expect(cmsV2.reorderCmsSections).toHaveBeenCalledTimes(1);

      // Attempt to click move-up and move-down on activities and newsletter while pending
      fireEvent.click(screen.getByTestId("move-up-cbc6c13c-7851-4483-818e-8ad9fa6b3acf"));
      fireEvent.click(screen.getByTestId("move-down-cbc6c13c-7851-4483-818e-8ad9fa6b3acf"));
      fireEvent.click(screen.getByTestId("move-up-48233538-1c6b-4a68-a551-c47b61bb179a"));
      fireEvent.click(screen.getByTestId("move-down-48233538-1c6b-4a68-a551-c47b61bb179a"));

      // Zero additional calls dispatched
      expect(cmsV2.reorderCmsSections).toHaveBeenCalledTimes(1);

      // Resolve
      await act(async () => {
        resolvePromise([]);
      });
    });
  });

  // ── Test 2: Rollback Mechanism on Network / API Failure ────────────────────
  describe("Empirical Challenge: Error Rollback Mechanism", () => {
    it("fully restores previous DOM order and triggers error toast when API rejects with Error", async () => {
      const sections = createRealisticSections();
      vi.mocked(cmsV2.reorderCmsSections).mockRejectedValueOnce(
        new Error("500 Internal Server Error: Database transaction aborted")
      );

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

      // Verify original order
      const initialCards = screen.getAllByTestId(/^section-card-/);
      expect(initialCards.map((c) => c.getAttribute("data-section-id"))).toEqual([
        "f16d3cb1-c884-4a2a-8223-d6346588f701",
        "ba35f51b-585b-48f3-82a3-2c66df0056a0",
        "cbc6c13c-7851-4483-818e-8ad9fa6b3acf",
        "48233538-1c6b-4a68-a551-c47b61bb179a",
        "ae8443ae-278d-42b1-bfe5-376da142ef43",
      ]);

      // Trigger move-down on activities (index 2)
      fireEvent.click(screen.getByTestId("move-down-cbc6c13c-7851-4483-818e-8ad9fa6b3acf"));

      // Wait for error handling
      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith(
          "Error al reordenar las secciones. Se han restaurado los cambios."
        );
      });

      // Verify that DOM order is completely restored to the pre-move state
      const restoredCards = screen.getAllByTestId(/^section-card-/);
      expect(restoredCards.map((c) => c.getAttribute("data-section-id"))).toEqual([
        "f16d3cb1-c884-4a2a-8223-d6346588f701",
        "ba35f51b-585b-48f3-82a3-2c66df0056a0",
        "cbc6c13c-7851-4483-818e-8ad9fa6b3acf",
        "48233538-1c6b-4a68-a551-c47b61bb179a",
        "ae8443ae-278d-42b1-bfe5-376da142ef43",
      ]);

      // Verify that lock is released and user can retry
      expect(screen.getByTestId("move-down-cbc6c13c-7851-4483-818e-8ad9fa6b3acf")).toBeEnabled();
    });

    it("maintains step integrity in sequential reordering: rolls back only to the immediately prior state", async () => {
      const sections = createRealisticSections();
      const onSectionsChange = vi.fn();

      // Step 1 succeeds
      vi.mocked(cmsV2.reorderCmsSections).mockResolvedValueOnce([]);
      // Step 2 fails
      vi.mocked(cmsV2.reorderCmsSections).mockRejectedValueOnce(new Error("Network disconnect"));

      const { rerender } = render(
        <PublicContentEditor
          siteKey="ccf"
          pageSlug="home"
          sections={sections}
          token="mock-token"
          canEdit={true}
          canPublish={true}
          onBack={vi.fn()}
          onSectionsChange={onSectionsChange}
        />
      );

      // Step 1: Move newsletter (index 3) up to index 2
      fireEvent.click(screen.getByTestId("move-up-48233538-1c6b-4a68-a551-c47b61bb179a"));

      await waitFor(() => {
        expect(cmsV2.reorderCmsSections).toHaveBeenCalledTimes(1);
      });
      expect(onSectionsChange).toHaveBeenCalledTimes(1);
      const intermediateSections = onSectionsChange.mock.calls[0][0];

      // Re-render with updated sections prop from parent
      rerender(
        <PublicContentEditor
          siteKey="ccf"
          pageSlug="home"
          sections={intermediateSections}
          token="mock-token"
          canEdit={true}
          canPublish={true}
          onBack={vi.fn()}
          onSectionsChange={onSectionsChange}
        />
      );

      // Check current DOM order: newsletter is now index 2, activities is index 3
      let cards = screen.getAllByTestId(/^section-card-/);
      expect(cards[2]).toHaveAttribute("data-section-id", "48233538-1c6b-4a68-a551-c47b61bb179a");
      expect(cards[3]).toHaveAttribute("data-section-id", "cbc6c13c-7851-4483-818e-8ad9fa6b3acf");

      // Step 2: Now attempt to move newsletter (index 2) up again to index 1 -> fails!
      fireEvent.click(screen.getByTestId("move-up-48233538-1c6b-4a68-a551-c47b61bb179a"));

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledTimes(1);
      });

      // Verify DOM rolled back to intermediate state (newsletter at index 2), NOT original state (newsletter at index 3)
      cards = screen.getAllByTestId(/^section-card-/);
      expect(cards[2]).toHaveAttribute("data-section-id", "48233538-1c6b-4a68-a551-c47b61bb179a");
      expect(cards[3]).toHaveAttribute("data-section-id", "cbc6c13c-7851-4483-818e-8ad9fa6b3acf");
    });
  });

  // ── Test 3: API Payload Contract Matching Backend Schema ───────────────────
  describe("Empirical Challenge: API Payload Contract", () => {
    it("sends payload matching schemas.CmsSectionReorderPayload with valid UUIDs and contiguous sort_orders", async () => {
      const sections = createRealisticSections();
      vi.mocked(cmsV2.reorderCmsSections).mockResolvedValueOnce([]);

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

      // Move discover_cta (index 4) up to index 3
      fireEvent.click(screen.getByTestId("move-up-ae8443ae-278d-42b1-bfe5-376da142ef43"));

      await waitFor(() => {
        expect(cmsV2.reorderCmsSections).toHaveBeenCalledTimes(1);
      });

      const calledArgs = vi.mocked(cmsV2.reorderCmsSections).mock.calls[0];
      const [siteKey, slug, items, token] = calledArgs;

      expect(siteKey).toBe("ccf");
      expect(slug).toBe("home");
      expect(token).toBe("mock-token");

      // Verify payload structure matches backend CmsSectionReorderPayload
      expect(Array.isArray(items)).toBe(true);
      expect(items).toHaveLength(5);

      const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

      items.forEach((item: { id: string; sort_order: number }, idx: number) => {
        // Contract 1: Every item has a valid string id formatted as UUID
        expect(item.id).toMatch(uuidRegex);
        // Contract 2: sort_order is an integer exactly matching index idx
        expect(typeof item.sort_order).toBe("number");
        expect(Number.isInteger(item.sort_order)).toBe(true);
        expect(item.sort_order).toBe(idx);
      });

      // Verify the specific swapped order
      expect(items[3].id).toBe("ae8443ae-278d-42b1-bfe5-376da142ef43"); // discover_cta moved up
      expect(items[4].id).toBe("48233538-1c6b-4a68-a551-c47b61bb179a"); // newsletter shifted down
    });
  });
});
