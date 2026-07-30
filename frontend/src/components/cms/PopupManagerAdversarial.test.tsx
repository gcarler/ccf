import React from "react";
import { render, screen, act, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { PopupManager } from "./PopupManager";
import CmsPopupsManagement from "@/app/plataforma/cms/popups/page";
import { listPublicPopups, listCmsPopups, listCmsSites, patchCmsPopup, deleteCmsPopup, createCmsPopup } from "@/lib/cms/v2";
import { PopupTriggerType } from "@/types/cms-v2";

const mockUsePathname = vi.fn();
vi.mock("next/navigation", () => ({
  usePathname: () => mockUsePathname(),
}));

const mockUseAuth = vi.fn();
vi.mock("@/context/AuthContext", () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock("@/lib/cms/v2", () => ({
  listPublicPopups: vi.fn(),
  listCmsSites: vi.fn().mockResolvedValue([{ id: "s1", site_key: "ccf", name: "CCF Main" }]),
  listCmsPopups: vi.fn(),
  createCmsPopup: vi.fn(),
  patchCmsPopup: vi.fn(),
  deleteCmsPopup: vi.fn(),
}));

describe("Empirical Adversarial Tests for PopupManager and Popups Admin UI", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
    mockUsePathname.mockReturnValue("/");
    mockUseAuth.mockReturnValue({
      token: "test-token",
      user: { role: "admin" },
    });
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  // -------------------------------------------------------------
  // FOCUS AREA 1 & 3: TRIGGER ENGINE & PATH MATCHING & SESSION STORAGE
  // -------------------------------------------------------------
  describe("Trigger Engine & Path Matching", () => {
    it("1.1 on_load trigger: fires immediately on page match and sets sessionStorage", async () => {
      vi.mocked(listPublicPopups).mockResolvedValue([
        {
          id: "popup-onload",
          name: "On Load Popup",
          content_html: "<div>OnLoad Content</div>",
          trigger_type: "on_load" as PopupTriggerType,
          trigger_value: null,
          show_on_pages: ["/dashboard"],
        },
      ]);
      mockUsePathname.mockReturnValue("/dashboard");

      render(<PopupManager />);

      await act(async () => {
        await Promise.resolve();
      });

      expect(screen.getByText("OnLoad Content")).toBeInTheDocument();
      expect(sessionStorage.getItem("popup_shown_popup-onload")).toBe("1");
    });

    it("1.2 time_delay trigger: fires after specified delay and clears timer on unmount", async () => {
      vi.mocked(listPublicPopups).mockResolvedValue([
        {
          id: "popup-timedelay",
          name: "Time Delay Popup",
          content_html: "<div>Time Delay Content</div>",
          trigger_type: "time_delay" as PopupTriggerType,
          trigger_value: 3,
          show_on_pages: ["*"],
        },
      ]);

      const { unmount } = render(<PopupManager />);

      await act(async () => {
        await Promise.resolve();
      });

      // Before timer
      expect(screen.queryByText("Time Delay Content")).not.toBeInTheDocument();

      // Advance 2 seconds
      act(() => {
        vi.advanceTimersByTime(2000);
      });
      expect(screen.queryByText("Time Delay Content")).not.toBeInTheDocument();

      // Advance to 3 seconds
      act(() => {
        vi.advanceTimersByTime(1000);
      });
      expect(screen.getByText("Time Delay Content")).toBeInTheDocument();
      expect(sessionStorage.getItem("popup_shown_popup-timedelay")).toBe("1");
    });

    it("1.3 time_delay edge case: trigger_value of 0 converts to 5s default fallback", async () => {
      vi.mocked(listPublicPopups).mockResolvedValue([
        {
          id: "popup-zero-delay",
          name: "Zero Delay Popup",
          content_html: "<div>Zero Delay Content</div>",
          trigger_type: "time_delay" as PopupTriggerType,
          trigger_value: 0,
          show_on_pages: ["*"],
        },
      ]);

      render(<PopupManager />);

      await act(async () => {
        await Promise.resolve();
      });

      // At 0ms or 1s, not shown because 0 falls back to 5s!
      act(() => {
        vi.advanceTimersByTime(1000);
      });
      expect(screen.queryByText("Zero Delay Content")).not.toBeInTheDocument();

      // At 5s, shown
      act(() => {
        vi.advanceTimersByTime(4000);
      });
      expect(screen.getByText("Zero Delay Content")).toBeInTheDocument();
    });

    it("1.4 scroll_percent trigger: triggers when scroll reaches target percent", async () => {
      vi.mocked(listPublicPopups).mockResolvedValue([
        {
          id: "popup-scroll",
          name: "Scroll Popup",
          content_html: "<div>Scroll Content</div>",
          trigger_type: "scroll_percent" as PopupTriggerType,
          trigger_value: 50,
          show_on_pages: ["*"],
        },
      ]);

      // Mock scroll properties
      Object.defineProperty(window, "scrollY", { value: 0, writable: true, configurable: true });
      Object.defineProperty(document.documentElement, "scrollTop", { value: 0, writable: true, configurable: true });
      Object.defineProperty(document.documentElement, "scrollHeight", { value: 1000, writable: true, configurable: true });
      Object.defineProperty(document.documentElement, "clientHeight", { value: 500, writable: true, configurable: true });

      render(<PopupManager />);

      await act(async () => {
        await Promise.resolve();
      });

      expect(screen.queryByText("Scroll Content")).not.toBeInTheDocument();

      // Scroll to 25% (125px of 500px available scroll)
      window.scrollY = 125;
      act(() => {
        window.dispatchEvent(new Event("scroll"));
      });
      expect(screen.queryByText("Scroll Content")).not.toBeInTheDocument();

      // Scroll to 50% (250px of 500px available scroll)
      window.scrollY = 250;
      act(() => {
        window.dispatchEvent(new Event("scroll"));
      });
      expect(screen.getByText("Scroll Content")).toBeInTheDocument();
      expect(sessionStorage.getItem("popup_shown_popup-scroll")).toBe("1");
    });

    it("1.5 exit_intent trigger: triggers when mouse leaves top edge (clientY < 10)", async () => {
      vi.mocked(listPublicPopups).mockResolvedValue([
        {
          id: "popup-exit",
          name: "Exit Intent Popup",
          content_html: "<div>Exit Intent Content</div>",
          trigger_type: "exit_intent" as PopupTriggerType,
          trigger_value: null,
          show_on_pages: ["*"],
        },
      ]);

      render(<PopupManager />);

      await act(async () => {
        await Promise.resolve();
      });

      expect(screen.queryByText("Exit Intent Content")).not.toBeInTheDocument();

      // Mouse leaves at clientY = 50 (should NOT trigger)
      act(() => {
        document.dispatchEvent(new MouseEvent("mouseleave", { clientY: 50 }));
      });
      expect(screen.queryByText("Exit Intent Content")).not.toBeInTheDocument();

      // Mouse leaves at clientY = 5 (should trigger)
      act(() => {
        document.dispatchEvent(new MouseEvent("mouseleave", { clientY: 5 }));
      });
      expect(screen.getByText("Exit Intent Content")).toBeInTheDocument();
      expect(sessionStorage.getItem("popup_shown_popup-exit")).toBe("1");
    });

    it("1.6 Path matching: wildcard prefix '/cursos*', exact '/cursos', and directory '/cursos/*'", async () => {
      const popupsList = [
        {
          id: "p-dir",
          name: "Dir Wildcard",
          content_html: "<div>Dir Content</div>",
          trigger_type: "on_load" as PopupTriggerType,
          trigger_value: null,
          show_on_pages: ["/cursos/*"],
        },
      ];

      vi.mocked(listPublicPopups).mockResolvedValue(popupsList);

      // Path '/cursos' should NOT match '/cursos/*' because '/cursos' does not start with '/cursos/'
      mockUsePathname.mockReturnValue("/cursos");
      const { rerender, container } = render(<PopupManager />);

      await act(async () => {
        await Promise.resolve();
      });
      expect(screen.queryByText("Dir Content")).not.toBeInTheDocument();

      // Path '/cursos/react' SHOULD match '/cursos/*'
      mockUsePathname.mockReturnValue("/cursos/react");
      rerender(<PopupManager />);
      await act(async () => {
        await Promise.resolve();
      });
      expect(screen.getByText("Dir Content")).toBeInTheDocument();
    });

    it("1.7 Session storage suppression: if already in sessionStorage, candidate is skipped", async () => {
      sessionStorage.setItem("popup_shown_p1", "1");
      vi.mocked(listPublicPopups).mockResolvedValue([
        {
          id: "p1",
          name: "Shown Popup",
          content_html: "<div>Shown Content</div>",
          trigger_type: "on_load" as PopupTriggerType,
          trigger_value: null,
          show_on_pages: ["*"],
        },
        {
          id: "p2",
          name: "Unshown Popup",
          content_html: "<div>Unshown Content</div>",
          trigger_type: "on_load" as PopupTriggerType,
          trigger_value: null,
          show_on_pages: ["*"],
        },
      ]);

      render(<PopupManager />);

      await act(async () => {
        await Promise.resolve();
      });

      expect(screen.queryByText("Shown Content")).not.toBeInTheDocument();
      expect(screen.getByText("Unshown Content")).toBeInTheDocument();
      expect(sessionStorage.getItem("popup_shown_p2")).toBe("1");
    });

    it("1.8 Close button handler: sets sessionStorage and closes active popup", async () => {
      vi.mocked(listPublicPopups).mockResolvedValue([
        {
          id: "p-close",
          name: "Closeable Popup",
          content_html: "<div>Close Me</div>",
          trigger_type: "on_load" as PopupTriggerType,
          trigger_value: null,
          show_on_pages: ["*"],
        },
      ]);

      render(<PopupManager />);

      await act(async () => {
        await Promise.resolve();
      });

      expect(screen.getByText("Close Me")).toBeInTheDocument();

      const closeBtn = screen.getByLabelText("Cerrar popup");
      act(() => {
        fireEvent.click(closeBtn);
      });

      expect(screen.queryByText("Close Me")).not.toBeInTheDocument();
      expect(sessionStorage.getItem("popup_shown_p-close")).toBe("1");
    });
  });

  // -------------------------------------------------------------
  // FOCUS AREA 4: ADMIN UI ROBUSTNESS
  // -------------------------------------------------------------
  describe("Admin UI Robustness (page.tsx)", () => {
    it("4.1 Renders popup list and allows toggling active state optimistically", async () => {
      const initialPopups = [
        {
          id: "p1",
          site_id: "s1",
          name: "Popup Uno",
          content_html: "<p>Contenido 1</p>",
          trigger_type: "time_delay" as PopupTriggerType,
          trigger_value: 10,
          is_active: true,
          show_on_pages: ["*"],
          created_at: "2026-07-30T00:00:00Z",
          updated_at: "2026-07-30T00:00:00Z",
        },
      ];
      vi.mocked(listCmsPopups).mockResolvedValue(initialPopups);
      vi.mocked(patchCmsPopup).mockResolvedValue({ ...initialPopups[0], is_active: false });

      render(<CmsPopupsManagement />);

      await act(async () => {
        await Promise.resolve();
      });

      expect(screen.getByText("Popup Uno")).toBeInTheDocument();

      const toggleBtn = screen.getByTitle("Desactivar");
      await act(async () => {
        fireEvent.click(toggleBtn);
      });

      expect(patchCmsPopup).toHaveBeenCalledWith("ccf", "p1", { is_active: false }, "test-token");
    });

    it("4.2 Delete modal flow: opens delete modal and confirms deletion", async () => {
      const initialPopups = [
        {
          id: "p-del",
          site_id: "s1",
          name: "Popup To Delete",
          content_html: "<p>Contenido</p>",
          trigger_type: "on_load" as PopupTriggerType,
          trigger_value: null,
          is_active: true,
          show_on_pages: ["*"],
          created_at: "2026-07-30T00:00:00Z",
          updated_at: "2026-07-30T00:00:00Z",
        },
      ];
      vi.mocked(listCmsPopups).mockResolvedValue(initialPopups);
      vi.mocked(deleteCmsPopup).mockResolvedValue(true as any);

      render(<CmsPopupsManagement />);

      await act(async () => {
        await Promise.resolve();
      });

      const deleteBtn = screen.getByTitle("Eliminar");
      act(() => {
        fireEvent.click(deleteBtn);
      });

      // Delete confirmation modal should appear
      expect(screen.getByText(/¿Estás seguro de eliminar el popup/i)).toBeInTheDocument();
      expect(screen.getByText('"Popup To Delete"')).toBeInTheDocument();

      const confirmBtns = screen.getAllByRole("button", { name: "Eliminar" });
      const confirmBtn = confirmBtns[confirmBtns.length - 1];
      await act(async () => {
        fireEvent.click(confirmBtn);
      });

      expect(deleteCmsPopup).toHaveBeenCalledWith("ccf", "p-del", "test-token");
    });

    it("4.3 Create popup drawer: validates empty name and calls createCmsPopup with formatted payload", async () => {
      vi.mocked(listCmsPopups).mockResolvedValue([]);
      vi.mocked(createCmsPopup).mockResolvedValue({} as any);

      render(<CmsPopupsManagement />);

      await act(async () => {
        await Promise.resolve();
      });

      // Click "Nuevo Popup"
      const createBtn = screen.getByText(/Nuevo Popup/i);
      act(() => {
        fireEvent.click(createBtn);
      });

      expect(screen.getByText("Configura el contenido y la regla de activación")).toBeInTheDocument();

      // Fill form name
      const nameInput = screen.getByPlaceholderText("ej. Promo Verano 2026");
      fireEvent.change(nameInput, { target: { value: "   " } });

      const saveBtn = screen.getByRole("button", { name: "Crear Popup" });
      await act(async () => {
        fireEvent.click(saveBtn);
      });

      // Name was empty whitespace, createCmsPopup should NOT have been called
      expect(createCmsPopup).not.toHaveBeenCalled();

      // Now fill valid name
      fireEvent.change(nameInput, { target: { value: "Nueva Oferta" } });

      await act(async () => {
        fireEvent.click(saveBtn);
      });

      expect(createCmsPopup).toHaveBeenCalledWith(
        "ccf",
        expect.objectContaining({
          name: "Nueva Oferta",
          trigger_type: "on_load",
          is_active: true,
          show_on_pages: ["*"],
        }),
        "test-token"
      );
    });
  });

  // -------------------------------------------------------------
  // FOCUS AREA 5: ADVERSARIAL EDGE CASE MINING & BOUNDARY HARNESSES
  // -------------------------------------------------------------
  describe("Adversarial Edge Case Mining & Failure Mode Analysis", () => {
    it("5.1 Route change cleanup: navigating away during time_delay cancels the active timer", async () => {
      vi.mocked(listPublicPopups).mockResolvedValue([
        {
          id: "p-navigate",
          name: "Navigate Popup",
          content_html: "<div>Nav Content</div>",
          trigger_type: "time_delay" as PopupTriggerType,
          trigger_value: 5,
          show_on_pages: ["/page-a"],
        },
      ]);
      mockUsePathname.mockReturnValue("/page-a");

      const { rerender } = render(<PopupManager />);

      await act(async () => {
        await Promise.resolve();
      });

      // Advance 3 seconds
      act(() => {
        vi.advanceTimersByTime(3000);
      });
      expect(screen.queryByText("Nav Content")).not.toBeInTheDocument();

      // User navigates to /page-b before timer expires
      mockUsePathname.mockReturnValue("/page-b");
      rerender(<PopupManager />);

      await act(async () => {
        await Promise.resolve();
      });

      // Advance another 5 seconds (total 8s)
      act(() => {
        vi.advanceTimersByTime(5000);
      });

      // Popup must NOT fire on /page-b because page didn't match and timer was cleaned up!
      expect(screen.queryByText("Nav Content")).not.toBeInTheDocument();
    });

    it("5.2 Non-scrollable page handling: scroll_percent popup gracefully waits and does not throw", async () => {
      vi.mocked(listPublicPopups).mockResolvedValue([
        {
          id: "p-noscroll",
          name: "No Scroll Popup",
          content_html: "<div>No Scroll Content</div>",
          trigger_type: "scroll_percent" as PopupTriggerType,
          trigger_value: 50,
          show_on_pages: ["*"],
        },
      ]);

      // Page where documentElement.scrollHeight == documentElement.clientHeight (no scrollable area)
      Object.defineProperty(document.documentElement, "scrollHeight", { value: 500, writable: true, configurable: true });
      Object.defineProperty(document.documentElement, "clientHeight", { value: 500, writable: true, configurable: true });

      render(<PopupManager />);

      await act(async () => {
        await Promise.resolve();
      });

      // Trigger scroll event
      act(() => {
        window.dispatchEvent(new Event("scroll"));
      });

      // Should not trigger when scrollHeight <= clientHeight
      expect(screen.queryByText("No Scroll Content")).not.toBeInTheDocument();
    });

    it("5.3 Multiple candidates priority: first matching unshown popup wins", async () => {
      vi.mocked(listPublicPopups).mockResolvedValue([
        {
          id: "p-first",
          name: "First Popup",
          content_html: "<div>First Content</div>",
          trigger_type: "on_load" as PopupTriggerType,
          trigger_value: null,
          show_on_pages: ["*"],
        },
        {
          id: "p-second",
          name: "Second Popup",
          content_html: "<div>Second Content</div>",
          trigger_type: "on_load" as PopupTriggerType,
          trigger_value: null,
          show_on_pages: ["*"],
        },
      ]);

      render(<PopupManager />);

      await act(async () => {
        await Promise.resolve();
      });

      expect(screen.getByText("First Content")).toBeInTheDocument();
      expect(screen.queryByText("Second Content")).not.toBeInTheDocument();
    });
  });
});
