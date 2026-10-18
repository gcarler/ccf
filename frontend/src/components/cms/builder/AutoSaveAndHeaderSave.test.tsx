import React from "react";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import PuckBuilderPage from "@/app/plataforma/cms/builder-puck/page";
import * as cmsV2 from "@/lib/cms/v2";
import { toast } from "sonner";
import { makeDbSection, payloadTitle, type CapturedPuckProps, type PuckMockProps } from "@/types/cms-test-fixtures";
import type { PuckSectionData } from "@/types/cms-builder";
import type { CmsSection } from "@/types/cms-v2";

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

function getCapturedPuckProps(): PuckMockProps {
  if (!puckPropsCaptured) throw new Error("El stub de <Puck> aún no capturó props");
  return puckPropsCaptured;
}

let puckPropsCaptured: CapturedPuckProps = null;
vi.mock("@puckeditor/core", () => ({
  Puck: (props: PuckMockProps) => {
    puckPropsCaptured = props;
    return (
      <div data-testid="puck-editor-mock">
        <button
          data-testid="puck-trigger-change"
          onClick={() => {
            props.onChange({
              content: [
                { type: "hero", props: { id: "sec-1", title: "Updated Title" } },
              ],
            });
          }}
        >
          Trigger Puck Change
        </button>
      </div>
    );
  },
}));

describe("M5: Auto-Save & Manual Save Header Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    puckPropsCaptured = null;
    vi.mocked(cmsV2.listCmsSections).mockResolvedValue([
      makeDbSection({ id: "sec-1", type: "hero", sort_order: 0, props_json: { title: "Initial Title" } }),
    ]);
    vi.mocked(cmsV2.patchCmsSection).mockResolvedValue(makeDbSection({ id: "sec-1", type: "hero" }));
    vi.mocked(cmsV2.createCmsSection).mockResolvedValue(makeDbSection({ id: "sec-2", type: "rich_text" }));
    vi.mocked(cmsV2.deleteCmsSection).mockResolvedValue(undefined);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders SaveStatusBadge with 'Guardado en borrador' initially", async () => {
    render(<PuckBuilderPage />);

    await act(async () => {
      await vi.runAllTimersAsync();
    });

    expect(screen.getByTestId("puck-editor-mock")).toBeInTheDocument();
    expect(screen.getByText("Guardado en borrador")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /guardar/i })).not.toBeDisabled();
  });

  it("suppresses initial mount onChange event using isInitialLoadRef", async () => {
    render(<PuckBuilderPage />);

    await act(async () => {
      await vi.runAllTimersAsync();
    });

    // Simulate Puck firing onChange immediately upon mount with initial data
    await act(async () => {
      getCapturedPuckProps().onChange({
        content: [{ type: "hero", props: { id: "sec-1", title: "Initial Title" } }],
      });
    });

    // Status should remain 'saved' (Guardado en borrador), and no save API called
    expect(screen.getByText("Guardado en borrador")).toBeInTheDocument();
    expect(cmsV2.patchCmsSection).not.toHaveBeenCalled();
    expect(cmsV2.createCmsSection).not.toHaveBeenCalled();
  });

  it("triggers debounced auto-save after 3000ms of user change", async () => {
    render(<PuckBuilderPage />);

    await act(async () => {
      await vi.runAllTimersAsync();
    });

    // Suppress initial mount
    act(() => {
      getCapturedPuckProps().onChange({
        content: [{ type: "hero", props: { id: "sec-1", title: "Initial Title" } }],
      });
    });

    // User makes an edit
    act(() => {
      getCapturedPuckProps().onChange({
        content: [{ type: "hero", props: { id: "sec-1", title: "Edited Title" } }],
      });
    });

    // Immediately status becomes 'dirty' ("Sin guardar")
    expect(screen.getByText("Sin guardar")).toBeInTheDocument();
    expect(cmsV2.patchCmsSection).not.toHaveBeenCalled();

    // Advance 2000ms: still not called
    act(() => {
      vi.advanceTimersByTime(2000);
    });
    expect(cmsV2.patchCmsSection).not.toHaveBeenCalled();

    // Advance remaining 1000ms (total 3000ms)
    await act(async () => {
      vi.advanceTimersByTime(1000);
      await vi.runAllTimersAsync();
    });

    expect(cmsV2.patchCmsSection).toHaveBeenCalledWith(
      "ccf",
      "home",
      "sec-1",
      { sort_order: 0, section_key: "hero", props_json: { title: "Edited Title", title_lead: "Edited Title" } },
      "test-token"
    );
    expect(screen.getByText("Guardado en borrador")).toBeInTheDocument();
  });

  it("clears pending debounce timer when manual save button is clicked", async () => {
    render(<PuckBuilderPage />);

    await act(async () => {
      await vi.runAllTimersAsync();
    });

    // Suppress initial mount
    act(() => {
      getCapturedPuckProps().onChange({ content: [] });
    });

    // User makes an edit
    act(() => {
      getCapturedPuckProps().onChange({
        content: [{ type: "hero", props: { id: "sec-1", title: "Manual Save Target" } }],
      });
    });

    expect(screen.getByText("Sin guardar")).toBeInTheDocument();

    // Click prominent manual Guardar button immediately
    const saveButton = screen.getByRole("button", { name: /guardar/i });
    await act(async () => {
      fireEvent.click(saveButton);
      await vi.runAllTimersAsync();
    });

    expect(cmsV2.patchCmsSection).toHaveBeenCalledTimes(1);
    expect(toast.success).toHaveBeenCalledWith("¡Página publicada exitosamente con Puck!");

    // Advance 5000ms to ensure debounced timer was cancelled and does not run again
    await act(async () => {
      vi.advanceTimersByTime(5000);
      await vi.runAllTimersAsync();
    });

    expect(cmsV2.patchCmsSection).toHaveBeenCalledTimes(1);
  });

  it("invokes manual save on Ctrl+S and Cmd+S keyboard shortcuts", async () => {
    render(<PuckBuilderPage />);

    await act(async () => {
      await vi.runAllTimersAsync();
    });

    // Suppress initial mount with edit content
    act(() => {
      getCapturedPuckProps().onChange({
        content: [{ type: "hero", props: { id: "sec-1", title: "Shortcut Save" } }],
      });
    });

    // 1. Test Ctrl+S
    const ctrlSEvent = new KeyboardEvent("keydown", {
      key: "s",
      ctrlKey: true,
      bubbles: true,
      cancelable: true,
    });
    const preventDefaultSpy = vi.spyOn(ctrlSEvent, "preventDefault");

    await act(async () => {
      window.dispatchEvent(ctrlSEvent);
      await vi.runAllTimersAsync();
    });

    expect(preventDefaultSpy).toHaveBeenCalled();
    expect(cmsV2.patchCmsSection).toHaveBeenCalledTimes(1);
    expect(toast.success).toHaveBeenCalled();

    // 2. Test Cmd+S (metaKey)
    const cmdSEvent = new KeyboardEvent("keydown", {
      key: "s",
      metaKey: true,
      bubbles: true,
      cancelable: true,
    });
    const preventDefaultSpyCmd = vi.spyOn(cmdSEvent, "preventDefault");

    await act(async () => {
      window.dispatchEvent(cmdSEvent);
      await vi.runAllTimersAsync();
    });

    expect(preventDefaultSpyCmd).toHaveBeenCalled();
    expect(cmsV2.patchCmsSection).toHaveBeenCalledTimes(2);
  });

  it("assigns DB section IDs in-place when creating new sections", async () => {
    vi.mocked(cmsV2.createCmsSection).mockResolvedValue(
      makeDbSection({ id: "generated-db-id-999", type: "rich_text" })
    );

    render(<PuckBuilderPage />);

    await act(async () => {
      await vi.runAllTimersAsync();
    });

    // Suppress initial mount
    act(() => {
      getCapturedPuckProps().onChange({ content: [] });
    });

    const newBlock: PuckSectionData = { type: "rich_text", props: { title: "New Section Without ID" } };

    // User adds a new section without an ID
    act(() => {
      getCapturedPuckProps().onChange({
        content: [newBlock],
      });
    });

    // Trigger manual save
    const saveButton = screen.getByRole("button", { name: /guardar/i });
    await act(async () => {
      fireEvent.click(saveButton);
      await vi.runAllTimersAsync();
    });

    expect(cmsV2.createCmsSection).toHaveBeenCalledWith(
      "ccf",
      "home",
      { type: "rich_text", section_key: "rich_text", sort_order: 0, props_json: { title: "New Section Without ID", title_lead: "New Section Without ID" } },
      "test-token"
    );

    // Verify in-place ID assignment
    expect(newBlock.props.id).toBe("generated-db-id-999");
  });

  it("discards out-of-order HTTP responses using sequence tracking", async () => {
    // We create slow response for call 1, fast response for call 2
    let resolveFirstSave: (value: CmsSection | PromiseLike<CmsSection>) => void;
    const slowFirstPromise = new Promise<CmsSection>((resolve) => {
      resolveFirstSave = resolve;
    });

    let callCount = 0;
    vi.mocked(cmsV2.patchCmsSection).mockImplementation(() => {
      callCount++;
      if (callCount === 1) {
        return slowFirstPromise;
      }
      return Promise.resolve(makeDbSection({ id: "sec-1", type: "hero" }));
    });

    render(<PuckBuilderPage />);

    await act(async () => {
      await vi.runAllTimersAsync();
    });

    // Suppress initial mount
    act(() => {
      getCapturedPuckProps().onChange({ content: [] });
    });

    // First edit -> triggers save #1 (slow)
    act(() => {
      getCapturedPuckProps().onChange({
        content: [{ type: "hero", props: { id: "sec-1", title: "Version 1" } }],
      });
    });

    act(() => {
      vi.advanceTimersByTime(3000);
    });

    // Second edit -> triggers manual save #2 (fast)
    act(() => {
      getCapturedPuckProps().onChange({
        content: [{ type: "hero", props: { id: "sec-1", title: "Version 2" } }],
      });
    });

    const saveButton = screen.getByRole("button", { name: /guardar/i });
    await act(async () => {
      fireEvent.click(saveButton);
    });

    // With the serialized save queue, save #2 waits behind the in-flight
    // save #1: the header still shows the saving state at this point.
    expect(screen.getByText("Guardando cambios...")).toBeInTheDocument();

    // Now resolve slow save #1
    await act(async () => {
      resolveFirstSave!(makeDbSection({ id: "sec-1", type: "hero" }));
      await vi.runAllTimersAsync();
    });

    // State should still be 'saved' and listCmsSections called for fresh state
    expect(screen.getByText("Guardado en borrador")).toBeInTheDocument();
  });

  it("serializes server writes: patchCmsSection is not called for save #2 until save #1 resolves", async () => {
    let resolveFirstSave: (value: CmsSection | PromiseLike<CmsSection>) => void;
    const slowFirstPromise = new Promise<CmsSection>((resolve) => {
      resolveFirstSave = resolve;
    });

    const calls: Array<{ callIndex: number; title: string }> = [];

    vi.mocked(cmsV2.patchCmsSection).mockImplementation((_site, _slug, _id, payload) => {
      const callIndex = calls.length + 1;
      const title = payloadTitle(payload);
      calls.push({ callIndex, title });

      if (callIndex === 1) {
        return slowFirstPromise;
      }
      return Promise.resolve(makeDbSection({ id: "sec-1", type: "hero", props_json: payload?.props_json ?? {} }));
    });

    render(<PuckBuilderPage />);

    await act(async () => {
      await vi.runAllTimersAsync();
    });

    // Suppress initial mount
    act(() => {
      getCapturedPuckProps().onChange({ content: [] });
    });

    // First edit -> triggers save #1 (slow)
    act(() => {
      getCapturedPuckProps().onChange({
        content: [{ type: "hero", props: { id: "sec-1", title: "Version 1" } }],
      });
    });

    await act(async () => {
      vi.advanceTimersByTime(3000);
    });

    // Verify save #1 has started writing to server
    expect(calls).toHaveLength(1);
    expect(calls[0].title).toBe("Version 1");

    // Second edit -> triggers manual save #2 (fast)
    act(() => {
      getCapturedPuckProps().onChange({
        content: [{ type: "hero", props: { id: "sec-1", title: "Version 2" } }],
      });
    });

    const saveButton = screen.getByRole("button", { name: /guardar/i });
    await act(async () => {
      fireEvent.click(saveButton);
    });

    // CRITICAL GUARDIAN ASSERTION:
    // Because server writes are strictly serialized via saveQueueRef,
    // patchCmsSection MUST NOT have been invoked for save #2 yet while save #1 is pending.
    expect(calls).toHaveLength(1);

    // Now resolve slow save #1
    await act(async () => {
      resolveFirstSave!(makeDbSection({ id: "sec-1", type: "hero" }));
      await vi.runAllTimersAsync();
    });

    // Now save #2 has proceeded and written to server in strict order
    expect(calls).toHaveLength(2);
    expect(calls[1].title).toBe("Version 2");
    expect(screen.getByText("Guardado en borrador")).toBeInTheDocument();
  });

  it("displays error status badge and error toast when save fails", async () => {
    vi.mocked(cmsV2.patchCmsSection).mockRejectedValue(new Error("Network Error"));

    render(<PuckBuilderPage />);

    await act(async () => {
      await vi.runAllTimersAsync();
    });

    // Suppress initial mount
    act(() => {
      getCapturedPuckProps().onChange({ content: [] });
    });

    // User edit
    act(() => {
      getCapturedPuckProps().onChange({
        content: [{ type: "hero", props: { id: "sec-1", title: "Error Test" } }],
      });
    });

    // Click Guardar
    const saveButton = screen.getByRole("button", { name: /guardar/i });
    await act(async () => {
      fireEvent.click(saveButton);
      await vi.runAllTimersAsync();
    });

    expect(screen.getByText("Error al guardar")).toBeInTheDocument();
    expect(toast.error).toHaveBeenCalledWith("Error al guardar y publicar la página");
  });

  it("resets 3000ms debounce timer upon rapid consecutive edits", async () => {
    render(<PuckBuilderPage />);

    await act(async () => {
      await vi.runAllTimersAsync();
    });

    // Suppress initial mount
    act(() => {
      getCapturedPuckProps().onChange({ content: [] });
    });

    // Edit 1 at t=0
    act(() => {
      getCapturedPuckProps().onChange({
        content: [{ type: "hero", props: { id: "sec-1", title: "Edit 1" } }],
      });
    });

    // Advance 1000ms (t=1000)
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    expect(cmsV2.patchCmsSection).not.toHaveBeenCalled();

    // Edit 2 at t=1000
    act(() => {
      getCapturedPuckProps().onChange({
        content: [{ type: "hero", props: { id: "sec-1", title: "Edit 2" } }],
      });
    });

    // Advance 2000ms (t=3000) - original timer from Edit 1 would have fired here, but timer was reset!
    act(() => {
      vi.advanceTimersByTime(2000);
    });
    expect(cmsV2.patchCmsSection).not.toHaveBeenCalled();

    // Edit 3 at t=3000
    act(() => {
      getCapturedPuckProps().onChange({
        content: [{ type: "hero", props: { id: "sec-1", title: "Edit 3" } }],
      });
    });

    // Advance 2999ms (t=5999) - should still not be called
    act(() => {
      vi.advanceTimersByTime(2999);
    });
    expect(cmsV2.patchCmsSection).not.toHaveBeenCalled();

    // Advance 1ms (t=6000, which is 3000ms after Edit 3 at t=3000)
    await act(async () => {
      vi.advanceTimersByTime(1);
      await vi.runAllTimersAsync();
    });

    expect(cmsV2.patchCmsSection).toHaveBeenCalledTimes(1);
    expect(cmsV2.patchCmsSection).toHaveBeenCalledWith(
      "ccf",
      "home",
      "sec-1",
      { sort_order: 0, section_key: "hero", props_json: { title: "Edit 3", title_lead: "Edit 3" } },
      "test-token"
    );
  });

  it("recovers from save error state when user makes new edits and saves successfully", async () => {
    // First save fails
    vi.mocked(cmsV2.patchCmsSection).mockRejectedValueOnce(new Error("Network Failure"));

    render(<PuckBuilderPage />);

    await act(async () => {
      await vi.runAllTimersAsync();
    });

    // Suppress initial mount
    act(() => {
      getCapturedPuckProps().onChange({ content: [] });
    });

    // Edit 1
    act(() => {
      getCapturedPuckProps().onChange({
        content: [{ type: "hero", props: { id: "sec-1", title: "Failing Edit" } }],
      });
    });

    // Trigger auto-save
    await act(async () => {
      vi.advanceTimersByTime(3000);
      await vi.runAllTimersAsync();
    });

    expect(screen.getByText("Error al guardar")).toBeInTheDocument();

    // User makes a new Edit 2 after error
    act(() => {
      getCapturedPuckProps().onChange({
        content: [{ type: "hero", props: { id: "sec-1", title: "Recovery Edit" } }],
      });
    });

    // Status transitions back to 'Sin guardar' (dirty)
    expect(screen.getByText("Sin guardar")).toBeInTheDocument();

    // Subsequent save succeeds
    vi.mocked(cmsV2.patchCmsSection).mockResolvedValueOnce(makeDbSection({ id: "sec-1", type: "hero" }));

    await act(async () => {
      vi.advanceTimersByTime(3000);
      await vi.runAllTimersAsync();
    });

    expect(screen.getByText("Guardado en borrador")).toBeInTheDocument();
  });
});

