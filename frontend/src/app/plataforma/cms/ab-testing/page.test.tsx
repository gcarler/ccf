import React from "react";
import { render, screen, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import CmsAbTestingManagement from "./page";

const mockUseAuth = vi.fn();
vi.mock("@/context/AuthContext", () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock("@/lib/http", () => ({
  apiFetch: vi.fn().mockResolvedValue({ total: 0, items: [] }),
}));


vi.mock("@/lib/cms/v2", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/cms/v2")>();
  return {
    ...actual,
    listCmsSites: vi.fn().mockResolvedValue([{ id: "s1", site_key: "ccf", name: "CCF Main" }]),
    listCmsAbTests: vi.fn(),
    createCmsAbTest: vi.fn(),
    patchCmsAbTest: vi.fn(),
    deleteCmsAbTest: vi.fn(),
    getCmsAbTestResults: vi.fn(),
    applyCmsAbTestWinner: vi.fn(),
    listCmsPostsByCategory: vi.fn().mockResolvedValue([]),
    postToTestimonial: vi.fn(),
  };
});


import { listCmsAbTests } from "@/lib/cms/v2";

describe("CmsAbTestingManagement", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({
      token: "test-token",
      user: { role: "admin" },
    });
  });

  it("renders page header and empty state when no experiments exist", async () => {
    vi.mocked(listCmsAbTests).mockResolvedValue([]);

    render(<CmsAbTestingManagement />);

    expect(screen.getByText(/Experimentos A\/B de Secciones/i)).toBeInTheDocument();

    await act(async () => {
      await Promise.resolve();
    });

    expect(screen.getByText(/No se encontraron experimentos A\/B/i)).toBeInTheDocument();
  });

  it("renders experiments grid when items exist", async () => {
    vi.mocked(listCmsAbTests).mockResolvedValue([
      {
        id: "test1",
        site_id: "s1",
        page_id: "page1-uuid",
        name: "Prueba Call To Action Hero",
        section_a_id: "sec-a-uuid",
        section_b_id: "sec-b-uuid",
        traffic_split: 0.5,
        status: "active",
        winner_section_id: null,
        created_at: "2026-07-30T00:00:00Z",
        started_at: "2026-07-30T00:00:00Z",
        ended_at: null,
      },
    ]);

    render(<CmsAbTestingManagement />);

    await act(async () => {
      await Promise.resolve();
    });

    expect(screen.getByText("Prueba Call To Action Hero")).toBeInTheDocument();
    expect(screen.getByText("Activo")).toBeInTheDocument();
    expect(screen.getByText("Split: 50% A / 50% B")).toBeInTheDocument();
  });
});
