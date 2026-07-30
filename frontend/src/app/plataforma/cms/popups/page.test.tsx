import React from "react";
import { render, screen, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import CmsPopupsManagement from "./page";

const mockUseAuth = vi.fn();
vi.mock("@/context/AuthContext", () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock("@/lib/cms/v2", () => ({
  listCmsSites: vi.fn().mockResolvedValue([{ id: "s1", site_key: "ccf", name: "CCF Main" }]),
  listCmsPopups: vi.fn(),
  createCmsPopup: vi.fn(),
  patchCmsPopup: vi.fn(),
  deleteCmsPopup: vi.fn(),
}));

import { listCmsPopups } from "@/lib/cms/v2";

describe("CmsPopupsManagement", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({
      token: "test-token",
      user: { role: "admin" },
    });
  });

  it("renders page header and empty state when no popups exist", async () => {
    vi.mocked(listCmsPopups).mockResolvedValue([]);

    render(<CmsPopupsManagement />);

    expect(screen.getByText(/Gestión de Popups Nativos/i)).toBeInTheDocument();

    await act(async () => {
      await Promise.resolve();
    });

    expect(screen.getByText(/No hay popups configurados/i)).toBeInTheDocument();
  });

  it("renders popups grid when items exist", async () => {
    vi.mocked(listCmsPopups).mockResolvedValue([
      {
        id: "p1",
        site_id: "s1",
        name: "Promo Verano",
        content_html: "<p>Descuento</p>",
        trigger_type: "time_delay",
        trigger_value: 10,
        is_active: true,
        show_on_pages: ["*"],
        created_at: "2026-07-30T00:00:00Z",
        updated_at: "2026-07-30T00:00:00Z",
      },
    ]);

    render(<CmsPopupsManagement />);

    await act(async () => {
      await Promise.resolve();
    });

    expect(screen.getByText("Promo Verano")).toBeInTheDocument();
    expect(screen.getByText(/Tiempo \(10s\)/i)).toBeInTheDocument();
  });
});
