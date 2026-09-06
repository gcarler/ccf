/**
 * Test Suite for Milestone 2: Interactive Reordering Controls in CMS Builder
 * File: frontend/src/app/plataforma/cms/builder/__tests__/PublicContentEditorReorder.test.tsx
 *
 * Verifies:
 * 1. Boundary button disabled states (index 0 cannot move up, index length - 1 cannot move down).
 * 2. Optimistic UI update and API call with exact [{ id, sort_order }] payload.
 * 3. Error rollback on API failure restoring previous section order and displaying error toast.
 * 4. In-flight mutation locking preventing concurrent requests and duplicate API calls.
 * 5. Read-only permissions guard (canEdit=false disables all reordering buttons).
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

// ── Test Fixtures ───────────────────────────────────────────────────────────

const createMockSections = (): ContentSection[] => [
  {
    id: "sec-hero",
    section_key: "hero",
    type: "hero",
    sort_order: 0,
    props_json: { title_lead: "Bienvenidos a", title_accent: "CCF", title_tail: "Faro" },
  },
  {
    id: "sec-welcome",
    section_key: "welcome",
    type: "feed",
    sort_order: 1,
    props_json: { title: "Bienvenidos a Casa" },
  },
  {
    id: "sec-activities",
    section_key: "activities",
    type: "events_calendar",
    sort_order: 2,
    props_json: { title: "Próximas Actividades" },
  },
];

// ── Test Suite ──────────────────────────────────────────────────────────────

describe("PublicContentEditor Reordering Controls (Milestone 2)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ── Test 1: Boundary Buttons ─────────────────────────────────────────────
  describe("Test 1: Disabled Boundary Buttons", () => {
    it("disables Move Up for the first item (index 0) and Move Down for the last item (index length - 1)", () => {
      const sections = createMockSections();

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

      // Section 0 (sec-hero): index 0 -> Move Up disabled, Move Down enabled
      const moveUp0 = screen.getByTestId("move-up-sec-hero");
      const moveDown0 = screen.getByTestId("move-down-sec-hero");
      expect(moveUp0).toBeDisabled();
      expect(moveDown0).toBeEnabled();

      // Section 1 (sec-welcome): index 1 (middle) -> both enabled
      const moveUp1 = screen.getByTestId("move-up-sec-welcome");
      const moveDown1 = screen.getByTestId("move-down-sec-welcome");
      expect(moveUp1).toBeEnabled();
      expect(moveDown1).toBeEnabled();

      // Section 2 (sec-activities): index 2 (last) -> Move Up enabled, Move Down disabled
      const moveUp2 = screen.getByTestId("move-up-sec-activities");
      const moveDown2 = screen.getByTestId("move-down-sec-activities");
      expect(moveUp2).toBeEnabled();
      expect(moveDown2).toBeDisabled();
    });

    it("disables both Move Up and Move Down when there is only one section", () => {
      const singleSection: ContentSection[] = [createMockSections()[0]];

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

      expect(screen.getByTestId("move-up-sec-hero")).toBeDisabled();
      expect(screen.getByTestId("move-down-sec-hero")).toBeDisabled();
    });

    it("disables all reordering buttons when canEdit is false", () => {
      const sections = createMockSections();

      render(
        <PublicContentEditor
          siteKey="ccf"
          pageSlug="home"
          sections={sections}
          token="mock-token"
          canEdit={false}
          canPublish={true}
          onBack={vi.fn()}
        />
      );

      expect(screen.getByTestId("move-up-sec-hero")).toBeDisabled();
      expect(screen.getByTestId("move-down-sec-hero")).toBeDisabled();
      expect(screen.getByTestId("move-up-sec-welcome")).toBeDisabled();
      expect(screen.getByTestId("move-down-sec-welcome")).toBeDisabled();
      expect(screen.getByTestId("move-up-sec-activities")).toBeDisabled();
      expect(screen.getByTestId("move-down-sec-activities")).toBeDisabled();
    });
  });

  // ── Test 2: Optimistic Reordering & API Payload ──────────────────────────
  describe("Test 2: Optimistic Reordering & Exact API Payload", () => {
    it("optimistically moves section down and calls reorderCmsSections with exact items payload", async () => {
      const sections = createMockSections();
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

      // Verify initial DOM sequence: sec-hero, sec-welcome, sec-activities
      let cards = screen.getAllByTestId(/^section-card-/);
      expect(cards[0]).toHaveAttribute("data-section-id", "sec-hero");
      expect(cards[1]).toHaveAttribute("data-section-id", "sec-welcome");
      expect(cards[2]).toHaveAttribute("data-section-id", "sec-activities");

      // Click Move Down on sec-hero
      fireEvent.click(screen.getByTestId("move-down-sec-hero"));

      // 1. Assert optimistic DOM update: sec-welcome is now index 0, sec-hero is index 1
      cards = screen.getAllByTestId(/^section-card-/);
      expect(cards[0]).toHaveAttribute("data-section-id", "sec-welcome");
      expect(cards[1]).toHaveAttribute("data-section-id", "sec-hero");
      expect(cards[2]).toHaveAttribute("data-section-id", "sec-activities");

      // 3. Assert API was called with exact [{ id, sort_order }] payload
      await waitFor(() => {
        expect(cmsV2.reorderCmsSections).toHaveBeenCalledTimes(1);
      });

      // 2. Assert updated boundary buttons after swap completes
      expect(screen.getByTestId("move-up-sec-welcome")).toBeDisabled();
      expect(screen.getByTestId("move-down-sec-welcome")).toBeEnabled();
      expect(screen.getByTestId("move-up-sec-hero")).toBeEnabled();
      expect(screen.getByTestId("move-down-sec-hero")).toBeEnabled();

      expect(cmsV2.reorderCmsSections).toHaveBeenCalledWith(
        "ccf",
        "home",
        [
          { id: "sec-welcome", sort_order: 0 },
          { id: "sec-hero", sort_order: 1 },
          { id: "sec-activities", sort_order: 2 },
        ],
        "mock-token"
      );

      // 4. Assert success toast
      expect(toast.success).toHaveBeenCalledWith("Sección movida hacia abajo");
    });

    it("optimistically moves section up and calls reorderCmsSections with exact items payload", async () => {
      const sections = createMockSections();
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

      // Click Move Up on sec-activities (index 2)
      fireEvent.click(screen.getByTestId("move-up-sec-activities"));

      // 1. Assert optimistic DOM update: sec-hero, sec-activities, sec-welcome
      const cards = screen.getAllByTestId(/^section-card-/);
      expect(cards[0]).toHaveAttribute("data-section-id", "sec-hero");
      expect(cards[1]).toHaveAttribute("data-section-id", "sec-activities");
      expect(cards[2]).toHaveAttribute("data-section-id", "sec-welcome");

      // 2. Assert API was called with exact items payload
      await waitFor(() => {
        expect(cmsV2.reorderCmsSections).toHaveBeenCalledTimes(1);
      });

      expect(cmsV2.reorderCmsSections).toHaveBeenCalledWith(
        "ccf",
        "home",
        [
          { id: "sec-hero", sort_order: 0 },
          { id: "sec-activities", sort_order: 1 },
          { id: "sec-welcome", sort_order: 2 },
        ],
        "mock-token"
      );

      // 3. Assert success toast
      expect(toast.success).toHaveBeenCalledWith("Sección movida hacia arriba");
    });
  });

  // ── Test 3: Error Rollback on API Failure ─────────────────────────────────
  describe("Test 3: Error Rollback on API Failure", () => {
    it("rolls back to previous order and displays error toast when reorderCmsSections fails", async () => {
      const sections = createMockSections();
      vi.mocked(cmsV2.reorderCmsSections).mockRejectedValueOnce(
        new Error("Network timeout: 504 Gateway Timeout")
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

      // Initial state: sec-hero at index 0
      expect(screen.getAllByTestId(/^section-card-/)[0]).toHaveAttribute("data-section-id", "sec-hero");

      // Click Move Down on sec-hero
      fireEvent.click(screen.getByTestId("move-down-sec-hero"));

      // Wait for error toast and rollback
      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith(
          "Error al reordenar las secciones. Se han restaurado los cambios."
        );
      });

      // Assert DOM order has reverted back to original sequence
      const cards = screen.getAllByTestId(/^section-card-/);
      expect(cards[0]).toHaveAttribute("data-section-id", "sec-hero");
      expect(cards[1]).toHaveAttribute("data-section-id", "sec-welcome");
      expect(cards[2]).toHaveAttribute("data-section-id", "sec-activities");

      // Assert boundary states are restored
      expect(screen.getByTestId("move-up-sec-hero")).toBeDisabled();
      expect(screen.getByTestId("move-down-sec-hero")).toBeEnabled();
    });
  });

  // ── Test 4: Concurrency & In-Flight Locking ──────────────────────────────
  describe("Test 4: In-Flight Request Locking", () => {
    it("locks all reordering buttons while a reorder request is in-flight and ignores spam clicks", async () => {
      const sections = createMockSections();
      let resolvePromise!: (val: unknown) => void;
      const pendingPromise = new Promise((resolve) => {
        resolvePromise = resolve;
      });
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      vi.mocked(cmsV2.reorderCmsSections).mockReturnValueOnce(pendingPromise as any);

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

      // Trigger first reorder
      fireEvent.click(screen.getByTestId("move-down-sec-hero"));

      // While request is in-flight, all reordering buttons must be disabled
      expect(screen.getByTestId("move-up-sec-welcome")).toBeDisabled();
      expect(screen.getByTestId("move-down-sec-welcome")).toBeDisabled();
      expect(screen.getByTestId("move-up-sec-hero")).toBeDisabled();
      expect(screen.getByTestId("move-down-sec-hero")).toBeDisabled();

      // Click another button while in-flight -> ignored, no extra API calls
      fireEvent.click(screen.getByTestId("move-down-sec-hero"));
      expect(cmsV2.reorderCmsSections).toHaveBeenCalledTimes(1);

      // Resolve the in-flight request
      await act(async () => {
        resolvePromise([]);
      });

      // After resolution, buttons return to active state
      await waitFor(() => {
        expect(screen.getByTestId("move-down-sec-hero")).toBeEnabled();
      });
    });
  });

  // ── Test 5: In-Flight Draft Edits Preservation ───────────────────────────
  describe("Test 5: Draft State Preservation", () => {
    it("preserves uncommitted field edits in drafts state when sections are reordered", async () => {
      const sections = createMockSections();
      vi.mocked(cmsV2.reorderCmsSections).mockResolvedValueOnce([]);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      vi.mocked(cmsV2.patchCmsSection).mockResolvedValue({} as any);

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

      // Find the input containing "Bienvenidos a Casa" and modify it
      const input = screen.getByDisplayValue("Bienvenidos a Casa");
      fireEvent.change(input, { target: { value: "Bienvenidos a Nuestra Casa Modificada" } });
      expect(screen.getByDisplayValue("Bienvenidos a Nuestra Casa Modificada")).toBeInTheDocument();

      // Move section down
      fireEvent.click(screen.getByTestId("move-down-sec-hero"));

      // Wait for reorder to complete
      await waitFor(() => {
        expect(cmsV2.reorderCmsSections).toHaveBeenCalledTimes(1);
      });

      // Assert draft value is still preserved after reordering
      expect(screen.getByDisplayValue("Bienvenidos a Nuestra Casa Modificada")).toBeInTheDocument();

      // Click "Guardar Borrador"
      const saveBtn = screen.getByRole("button", { name: /Guardar/i });
      fireEvent.click(saveBtn);

      // Assert patchCmsSection is called with the modified draft props_json
      await waitFor(() => {
        expect(cmsV2.patchCmsSection).toHaveBeenCalledWith(
          "ccf",
          "home",
          "sec-welcome",
          { props_json: expect.objectContaining({ title: "Bienvenidos a Nuestra Casa Modificada" }) },
          "mock-token"
        );
      });
    });
  });
});

