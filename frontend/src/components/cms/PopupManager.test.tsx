import React from "react";
import { render, screen, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { PopupManager } from "./PopupManager";

const mockUsePathname = vi.fn();
vi.mock("next/navigation", () => ({
  usePathname: () => mockUsePathname(),
}));

vi.mock("@/lib/cms/v2", () => ({
  listPublicPopups: vi.fn(),
}));

import { listPublicPopups } from "@/lib/cms/v2";

describe("PopupManager", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
    mockUsePathname.mockReturnValue("/");
  });

  it("renders null when no active popups match", async () => {
    vi.mocked(listPublicPopups).mockResolvedValue([]);

    const { container } = render(<PopupManager />);

    await act(async () => {
      await Promise.resolve();
    });

    expect(container.firstChild).toBeNull();
  });

  it("displays on_load popup when route matches and not already shown", async () => {
    vi.mocked(listPublicPopups).mockResolvedValue([
      {
        id: "popup-1",
        name: "Welcome Popup",
        content_html: "<p>Welcome to CCF!</p>",
        trigger_type: "on_load",
        trigger_value: null,
        show_on_pages: ["*"],
      },
    ]);

    render(<PopupManager />);

    await act(async () => {
      await Promise.resolve();
    });

    expect(await screen.findByText("Welcome to CCF!")).toBeInTheDocument();
    expect(sessionStorage.getItem("popup_shown_popup-1")).toBe("1");
  });

  it("respects sessionStorage and does not re-show popup", async () => {
    sessionStorage.setItem("popup_shown_popup-1", "1");
    vi.mocked(listPublicPopups).mockResolvedValue([
      {
        id: "popup-1",
        name: "Welcome Popup",
        content_html: "<p>Welcome to CCF!</p>",
        trigger_type: "on_load",
        trigger_value: null,
        show_on_pages: ["*"],
      },
    ]);

    const { container } = render(<PopupManager />);

    await act(async () => {
      await Promise.resolve();
    });

    expect(screen.queryByText("Welcome to CCF!")).not.toBeInTheDocument();
  });
});
