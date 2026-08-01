import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import CmsBuilderPage from "./page";
import * as cmsV2 from "@/lib/cms/v2";

// ── Mocks ───────────────────────────────────────────────────────────────────

let mockSearchParams: URLSearchParams | null = new URLSearchParams("site=ccf&page=home");
const mockPush = vi.fn();

vi.mock("next/navigation", () => ({
  useSearchParams: () => mockSearchParams,
  useRouter: () => ({ push: mockPush }),
}));

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

vi.mock("@/lib/cms/v2", () => ({
  listCmsSections: vi.fn().mockResolvedValue([]),
  patchCmsSection: vi.fn().mockResolvedValue({ id: "sec-1", props_json: {} }),
  createCmsSection: vi.fn().mockResolvedValue({ id: "sec-new", props_json: {} }),
  deleteCmsSection: vi.fn().mockResolvedValue(undefined),
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
  Puck: () => (
    <div data-testid="puck-editor-mock">
      <span>Puck Editor Canvas</span>
    </div>
  ),
}));

// ── Tests ───────────────────────────────────────────────────────────────────

describe("CmsBuilderPage Route Handling & Edge Cases", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAuth = { token: "mock-token", user: { role: "admin" } };
  });

  it("uses fallback SITE_KEY ('ccf') when 'site' query parameter is missing", async () => {
    mockSearchParams = new URLSearchParams("page=contacto");

    render(<CmsBuilderPage />);

    await waitFor(() => {
      expect(cmsV2.listCmsSections).toHaveBeenCalledWith("ccf", "contacto", "mock-token");
    });

    expect(screen.getByText("/contacto")).toBeInTheDocument();
  });

  it("renders selection fallback when 'page' query parameter is completely missing", async () => {
    mockSearchParams = new URLSearchParams("site=ccf");

    render(<CmsBuilderPage />);

    expect(screen.getByText("Selecciona un sitio y página en la lista de páginas para editar.")).toBeInTheDocument();
    expect(screen.queryByRole("main", { name: "Editor visual Puck" })).not.toBeInTheDocument();
  });

  it("renders selection fallback when searchParams is empty / null", async () => {
    mockSearchParams = new URLSearchParams("");

    render(<CmsBuilderPage />);

    expect(screen.getByText("Selecciona un sitio y página en la lista de páginas para editar.")).toBeInTheDocument();
  });

  it("renders selection fallback when auth token is missing / null", async () => {
    mockSearchParams = new URLSearchParams("site=ccf&page=home");
    mockAuth = { token: null, user: null };

    render(<CmsBuilderPage />);

    expect(screen.getByText("Selecciona un sitio y página en la lista de páginas para editar.")).toBeInTheDocument();
  });

  it("preserves custom site parameter in back navigation when provided", async () => {
    mockSearchParams = new URLSearchParams("site=sede-sur&page=eventos");

    render(<CmsBuilderPage />);

    await waitFor(() => {
      expect(screen.getByTitle("Volver a Páginas")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTitle("Volver a Páginas"));
    expect(mockPush).toHaveBeenCalledWith("/plataforma/cms/pages?site=sede-sur");
  });

  it("gracefully handles API errors during initial section and theme loading", async () => {
    mockSearchParams = new URLSearchParams("site=ccf&page=home");
    vi.mocked(cmsV2.listCmsSections).mockRejectedValueOnce(new Error("Network Error"));

    render(<CmsBuilderPage />);

    await waitFor(() => {
      expect(screen.getByTestId("puck-editor-mock")).toBeInTheDocument();
    });
  });
});
