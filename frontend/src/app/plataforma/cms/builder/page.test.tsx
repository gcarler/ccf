/* eslint-disable @typescript-eslint/no-explicit-any */
import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import CmsBuilderPage from "./page";
import * as cmsV2 from "@/lib/cms/v2";
import { apiFetch } from "@/lib/http";

// ── Mocks ───────────────────────────────────────────────────────────────────

let mockSearchParams = new URLSearchParams("site=ccf&page=home");
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
  listCmsSections: vi.fn().mockResolvedValue([
    {
      id: "sec-hero-1",
      type: "hero",
      props_json: { title: "Hero Test Title" },
      sort_order: 1,
    },
  ]),
  patchCmsSection: vi.fn().mockResolvedValue({ id: "sec-hero-1", type: "hero", props_json: {} }),
  createCmsSection: vi.fn().mockResolvedValue({ id: "sec-new-1", type: "hero", props_json: {} }),
  deleteCmsSection: vi.fn().mockResolvedValue(undefined),
}));

vi.mock("@/lib/http", () => ({
  apiFetch: vi.fn().mockImplementation((url: string) => {
    if (url.includes("/theme")) {
      return Promise.resolve({
        id: "theme-1",
        name: "Tema Faro",
        tokens_json: { "--site-background": "#001134" },
      });
    }
    if (url.includes("/cms/media")) {
      return Promise.resolve({ items: [], total: 0 });
    }
    return Promise.resolve(null);
  }),
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

vi.mock("@puckeditor/core", () => ({
  Puck: (props: any) => (
    <div data-testid="puck-editor-mock">
      <span>Puck Editor Canvas</span>
      <button
        data-testid="puck-trigger-publish"
        onClick={() => props.onPublish?.(props.data)}
      >
        Trigger Publish
      </button>
    </div>
  ),
}));

// ── Tests ───────────────────────────────────────────────────────────────────

describe("CmsBuilderPage (Puck visual editor main route)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSearchParams = new URLSearchParams("site=ccf&page=home");
    mockAuth = { token: "mock-token", user: { role: "admin" } };
  });

  it("renders the main Puck builder page layout and header elements", async () => {
    render(<CmsBuilderPage />);

    await waitFor(() => {
      expect(screen.getByRole("main")).toHaveAttribute("aria-label", "Editor visual Puck");
    });

    expect(screen.getByText(/Editando página:/i)).toBeInTheDocument();
    expect(screen.getByText("/home")).toBeInTheDocument();
    expect(screen.getByText("Guardado en borrador")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Guardar" })).toBeInTheDocument();
  });

  it("fetches CMS page sections and site theme on initial load", async () => {
    render(<CmsBuilderPage />);

    await waitFor(() => {
      expect(cmsV2.listCmsSections).toHaveBeenCalledWith("ccf", "home", "mock-token");
    });

    expect(apiFetch).toHaveBeenCalledWith(
      "/cms/v2/public/sites/ccf/theme",
      expect.objectContaining({ method: "GET" })
    );
  });

  it("displays missing parameters prompt when page parameter is empty", async () => {
    mockSearchParams = new URLSearchParams("site=ccf");

    render(<CmsBuilderPage />);

    await waitFor(() => {
      expect(screen.getByText("Selecciona un sitio y página en la lista de páginas para editar.")).toBeInTheDocument();
    });

    const returnBtn = screen.getByRole("button", { name: "Volver a Páginas" });
    expect(returnBtn).toBeInTheDocument();

    fireEvent.click(returnBtn);
    expect(mockPush).toHaveBeenCalledWith("/plataforma/cms/pages");
  });

  it("handles manual Save button click to trigger persistence flow", async () => {
    render(<CmsBuilderPage />);

    await waitFor(() => {
      expect(screen.getByTestId("puck-editor-mock")).toBeInTheDocument();
    });

    const saveBtn = screen.getByRole("button", { name: "Guardar" });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(cmsV2.patchCmsSection).toHaveBeenCalled();
    });
  });

  it("navigates back to CMS pages list when back arrow is clicked", async () => {
    render(<CmsBuilderPage />);

    await waitFor(() => {
      expect(screen.getByTitle("Volver a Páginas")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTitle("Volver a Páginas"));
    expect(mockPush).toHaveBeenCalledWith("/plataforma/cms/pages?site=ccf");
  });
});
