/* eslint-disable @typescript-eslint/no-explicit-any */
import React from "react";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import PuckBuilderPage from "@/app/plataforma/cms/builder-puck/page";
import * as cmsV2 from "@/lib/cms/v2";
import { toast } from "sonner";

// Mocks
vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams("site=ccf&page=home&mode=visual"),
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({ token: "test-token", user: { role: "admin" } }),
}));

vi.mock("@/lib/cms/permissions", () => ({
  canEditCms: () => true,
  canPublishCms: () => true,
}));

vi.mock("@/lib/cms/v2", () => ({
  listCmsSections: vi.fn(),
  patchCmsSection: vi.fn(),
  createCmsSection: vi.fn(),
  deleteCmsSection: vi.fn(),
  workflowCmsPage: vi.fn().mockResolvedValue({ status: "published" }),
}));

vi.mock("@/lib/http", () => ({
  apiFetch: vi.fn().mockResolvedValue(null),
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

let puckPropsCaptured: any = null;
vi.mock("@puckeditor/core", () => ({
  Puck: (props: any) => {
    puckPropsCaptured = props;
    return (
      <div data-testid="puck-editor-mock">
        <input data-testid="test-input" defaultValue="Input field focus target" />
        <textarea data-testid="test-textarea" defaultValue="Textarea focus target" />
      </div>
    );
  },
}));

describe("Empirical Challenge M5: Keyboard Shortcuts, Save Button UI & Toast Notifications", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    puckPropsCaptured = null;
    (cmsV2.listCmsSections as any).mockResolvedValue([
      { id: "sec-1", type: "hero", sort_order: 0, props_json: { title: "Initial Title" } },
    ]);
    (cmsV2.patchCmsSection as any).mockResolvedValue({ id: "sec-1", type: "hero" });
    (cmsV2.createCmsSection as any).mockResolvedValue({ id: "sec-2", type: "rich_text" });
    (cmsV2.deleteCmsSection as any).mockResolvedValue({ success: true });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe("1 & 2. Keyboard Shortcuts (Ctrl+S / Cmd+S) and e.preventDefault() across focus targets", () => {
    it("intercepts Ctrl+S and suppresses browser default when focused on an <input> element", async () => {
      render(<PuckBuilderPage />);
      await act(async () => {
        await vi.runAllTimersAsync();
      });

      const input = screen.getByTestId("test-input");
      input.focus();
      expect(document.activeElement).toBe(input);

      const event = new KeyboardEvent("keydown", {
        key: "s",
        ctrlKey: true,
        bubbles: true,
        cancelable: true,
      });
      const preventDefaultSpy = vi.spyOn(event, "preventDefault");

      await act(async () => {
        input.dispatchEvent(event);
        await vi.runAllTimersAsync();
      });

      expect(preventDefaultSpy).toHaveBeenCalledTimes(1);
      expect(cmsV2.patchCmsSection).toHaveBeenCalledTimes(1);
      expect(toast.success).toHaveBeenCalledWith("¡Página publicada exitosamente con Puck!");
    });

    it("intercepts Cmd+S and suppresses browser default when focused on a <textarea> element", async () => {
      render(<PuckBuilderPage />);
      await act(async () => {
        await vi.runAllTimersAsync();
      });

      const textarea = screen.getByTestId("test-textarea");
      textarea.focus();
      expect(document.activeElement).toBe(textarea);

      const event = new KeyboardEvent("keydown", {
        key: "s",
        metaKey: true,
        bubbles: true,
        cancelable: true,
      });
      const preventDefaultSpy = vi.spyOn(event, "preventDefault");

      await act(async () => {
        textarea.dispatchEvent(event);
        await vi.runAllTimersAsync();
      });

      expect(preventDefaultSpy).toHaveBeenCalledTimes(1);
      expect(cmsV2.patchCmsSection).toHaveBeenCalledTimes(1);
      expect(toast.success).toHaveBeenCalledWith("¡Página publicada exitosamente con Puck!");
    });

    it("intercepts Ctrl+S and Cmd+S and suppresses browser default when focused on background (body)", async () => {
      render(<PuckBuilderPage />);
      await act(async () => {
        await vi.runAllTimersAsync();
      });

      document.body.focus();

      // Ctrl+S on background
      const ctrlEvent = new KeyboardEvent("keydown", {
        key: "s",
        ctrlKey: true,
        bubbles: true,
        cancelable: true,
      });
      const preventDefaultCtrl = vi.spyOn(ctrlEvent, "preventDefault");

      await act(async () => {
        window.dispatchEvent(ctrlEvent);
        await vi.runAllTimersAsync();
      });

      expect(preventDefaultCtrl).toHaveBeenCalledTimes(1);

      // Cmd+S on background (uppercase 'S' test as well)
      const cmdEvent = new KeyboardEvent("keydown", {
        key: "S",
        metaKey: true,
        bubbles: true,
        cancelable: true,
      });
      const preventDefaultCmd = vi.spyOn(cmdEvent, "preventDefault");

      await act(async () => {
        window.dispatchEvent(cmdEvent);
        await vi.runAllTimersAsync();
      });

      expect(preventDefaultCmd).toHaveBeenCalledTimes(1);
      expect(cmsV2.patchCmsSection).toHaveBeenCalledTimes(2);
    });

    it("suppresses e.preventDefault() even when a save is already in progress, but prevents duplicate API calls", async () => {
      let resolveSave: (val: any) => void;
      (cmsV2.patchCmsSection as any).mockImplementation(
        () => new Promise((res) => { resolveSave = res; })
      );

      render(<PuckBuilderPage />);
      await act(async () => {
        await vi.runAllTimersAsync();
      });

      // Fire 1st save shortcut
      const event1 = new KeyboardEvent("keydown", { key: "s", ctrlKey: true, bubbles: true, cancelable: true });
      const preventDefault1 = vi.spyOn(event1, "preventDefault");
      act(() => {
        window.dispatchEvent(event1);
      });
      expect(preventDefault1).toHaveBeenCalledTimes(1);
      expect(cmsV2.patchCmsSection).toHaveBeenCalledTimes(1);

      // Fire 2nd save shortcut while 1st is in flight
      const event2 = new KeyboardEvent("keydown", { key: "s", ctrlKey: true, bubbles: true, cancelable: true });
      const preventDefault2 = vi.spyOn(event2, "preventDefault");
      act(() => {
        window.dispatchEvent(event2);
      });

      // Browser save dialog MUST still be suppressed even during active save!
      expect(preventDefault2).toHaveBeenCalledTimes(1);
      // But no second patch call should have been initiated!
      expect(cmsV2.patchCmsSection).toHaveBeenCalledTimes(1);

      // Clean up in-flight promise
      await act(async () => {
        resolveSave!({ id: "sec-1" });
        await vi.runAllTimersAsync();
      });
    });
  });

  describe("3. Save Button UI Disabled States during active save operations", () => {
    it("shows enabled button in idle state and transitions to disabled state with spinner while saving", async () => {
      let resolveSave: (val: any) => void;
      (cmsV2.patchCmsSection as any).mockImplementation(
        () => new Promise((res) => { resolveSave = res; })
      );

      render(<PuckBuilderPage />);
      await act(async () => {
        await vi.runAllTimersAsync();
      });

      const button = screen.getByRole("button", { name: /guardar/i });
      expect(button).not.toBeDisabled();

      // Click button to start manual save
      act(() => {
        fireEvent.click(button);
      });

      // Button must immediately become disabled
      expect(button).toBeDisabled();
      expect(screen.getByText("Guardando cambios...")).toBeInTheDocument();

      // Attempting to click disabled button should do nothing
      act(() => {
        fireEvent.click(button);
      });
      expect(cmsV2.patchCmsSection).toHaveBeenCalledTimes(1);

      // Finish save operation
      await act(async () => {
        resolveSave!({ id: "sec-1" });
        await vi.runAllTimersAsync();
      });

      // Button returns to enabled state
      expect(button).not.toBeDisabled();
      expect(screen.getByText("Guardado en borrador")).toBeInTheDocument();
    });

    it("disables save button during debounced background auto-save", async () => {
      let resolveSave: (val: any) => void;
      (cmsV2.patchCmsSection as any).mockImplementation(
        () => new Promise((res) => { resolveSave = res; })
      );

      render(<PuckBuilderPage />);
      await act(async () => {
        await vi.runAllTimersAsync();
      });

      // Suppress initial mount
      act(() => {
        puckPropsCaptured.onChange({ content: [] });
      });

      // Trigger user change
      act(() => {
        puckPropsCaptured.onChange({
          content: [{ type: "hero", props: { id: "sec-1", title: "Background AutoSave" } }],
        });
      });

      // Fast-forward 3000ms to trigger auto-save
      act(() => {
        vi.advanceTimersByTime(3000);
      });

      const button = screen.getByRole("button", { name: /guardar/i });
      // While auto-save is in flight, button is disabled (saveStatus === "saving")
      expect(button).toBeDisabled();
      expect(screen.getByText("Guardando cambios...")).toBeInTheDocument();

      await act(async () => {
        resolveSave!({ id: "sec-1" });
        await vi.runAllTimersAsync();
      });

      expect(button).not.toBeDisabled();
    });
  });

  describe("4. Toast Notifications for Manual and Auto-Save Operations", () => {
    it("fires toast.success only on manual save, never on background auto-save", async () => {
      render(<PuckBuilderPage />);
      await act(async () => {
        await vi.runAllTimersAsync();
      });

      // Suppress initial mount
      act(() => {
        puckPropsCaptured.onChange({ content: [] });
      });

      // 1. Auto-save edit
      act(() => {
        puckPropsCaptured.onChange({
          content: [{ type: "hero", props: { id: "sec-1", title: "Auto Save Toast Test" } }],
        });
      });

      await act(async () => {
        vi.advanceTimersByTime(3000);
        await vi.runAllTimersAsync();
      });

      expect(cmsV2.patchCmsSection).toHaveBeenCalledTimes(1);
      // Auto-save MUST NOT show success toast
      expect(toast.success).not.toHaveBeenCalled();

      // 2. Manual save edit
      act(() => {
        puckPropsCaptured.onChange({
          content: [{ type: "hero", props: { id: "sec-1", title: "Manual Save Toast Test" } }],
        });
      });

      const button = screen.getByRole("button", { name: /guardar/i });
      await act(async () => {
        fireEvent.click(button);
        await vi.runAllTimersAsync();
      });

      expect(toast.success).toHaveBeenCalledWith("¡Página publicada exitosamente con Puck!");
    });

    it("fires distinct error toast on manual save vs auto-save failure", async () => {
      (cmsV2.patchCmsSection as any).mockRejectedValue(new Error("API failure"));

      render(<PuckBuilderPage />);
      await act(async () => {
        await vi.runAllTimersAsync();
      });

      // Suppress initial mount
      act(() => {
        puckPropsCaptured.onChange({ content: [] });
      });

      // 1. Auto-save failure toast
      act(() => {
        puckPropsCaptured.onChange({
          content: [{ type: "hero", props: { id: "sec-1", title: "Auto Save Failure" } }],
        });
      });

      await act(async () => {
        vi.advanceTimersByTime(3000);
        await vi.runAllTimersAsync();
      });

      expect(toast.error).toHaveBeenCalledWith("Error en el auto-guardado", { id: "autosave-err" });

      // 2. Manual save failure toast
      act(() => {
        puckPropsCaptured.onChange({
          content: [{ type: "hero", props: { id: "sec-1", title: "Manual Save Failure" } }],
        });
      });

      const button = screen.getByRole("button", { name: /guardar/i });
      await act(async () => {
        fireEvent.click(button);
        await vi.runAllTimersAsync();
      });

      expect(toast.error).toHaveBeenCalledWith("Error al guardar y publicar la página");
    });
  });
});
