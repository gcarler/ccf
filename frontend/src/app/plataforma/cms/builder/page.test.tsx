/* eslint-disable @typescript-eslint/no-explicit-any */
import React from "react";
import { render, screen, waitFor, fireEvent, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import CmsBuilderPage from "./page";
import { preserveSelectedMediaId } from "./media-utils";
import * as cmsV2 from "@/lib/cms/v2";
import { apiFetch } from "@/lib/http";
import { toast } from "sonner";

// ── Mocks ───────────────────────────────────────────────────────────────────

let mockSearchParams = new URLSearchParams("site=ccf&page=home&mode=visual");
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
  workflowCmsPage: vi.fn().mockResolvedValue({ status: "published" }),
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

let puckPropsCaptured: any = null;
vi.mock("@puckeditor/core", () => ({
  Puck: (props: any) => {
    puckPropsCaptured = props;
    return (
      <div data-testid="puck-editor-mock">
        <span>Puck Editor Canvas</span>
        <button
          data-testid="puck-trigger-publish"
          onClick={() => props.onPublish?.(props.data)}
        >
          Trigger Publish
        </button>
      </div>
    );
  },
}));

// ── Tests ───────────────────────────────────────────────────────────────────

describe("CmsBuilderPage (Puck visual editor main route)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSearchParams = new URLSearchParams("site=ccf&page=home&mode=visual");
    mockAuth = { token: "mock-token", user: { role: "admin" } };
    puckPropsCaptured = null;
    (cmsV2.listCmsSections as any).mockResolvedValue([
      {
        id: "sec-hero-1",
        type: "hero",
        props_json: { title: "Hero Test Title" },
        sort_order: 1,
      },
    ]);
    (cmsV2.workflowCmsPage as any).mockResolvedValue({ status: "published" });
  });

  it("preserves the selected media id alongside its URL in native and JSON sections", () => {
    const data = {
      content: [
        { type: "hero", props: { bg_image: "/hero.jpg" } },
        {
          type: "feed",
          props: { __cms_json: JSON.stringify({ gallery: [{ url: "/hero.jpg" }] }) },
        },
      ],
    };

    expect(preserveSelectedMediaId(data, { url: "/hero.jpg", media_id: "media-1" })).toEqual({
      content: [
        { type: "hero", props: { bg_image: "/hero.jpg", media_id: "media-1" } },
        {
          type: "feed",
          props: { __cms_json: JSON.stringify({ gallery: [{ url: "/hero.jpg", media_id: "media-1" }] }, null, 2) },
        },
      ],
    });
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

  it("round-trips generic CMS JSON sections and publishes the edited snapshot", async () => {
    const props = { title: "Contenido editable", nested: { enabled: true } };
    // The API returns an array; keep the mock explicit for both initial load
    // and the post-save refresh.
    (cmsV2.listCmsSections as any).mockResolvedValue([
      { id: "sec-feed-1", type: "feed", props_json: props, sort_order: 0 },
    ]);

    render(<CmsBuilderPage />);

    await waitFor(() => {
      expect(puckPropsCaptured?.data?.content?.[0]?.props?.__cms_json).toContain("Contenido editable");
    });

    await act(async () => {
      await puckPropsCaptured.onPublish({
        content: [
          {
            type: "feed",
            props: {
              id: "sec-feed-1",
              __cms_json: JSON.stringify({ title: "Texto publicado desde Puck", nested: { enabled: false } }),
            },
          },
        ],
      });
    });

    await waitFor(() => {
      expect(cmsV2.patchCmsSection).toHaveBeenCalledWith(
        "ccf",
        "home",
        "sec-feed-1",
        { sort_order: 0, props_json: { title: "Texto publicado desde Puck", nested: { enabled: false } } },
        "mock-token",
      );
      expect(cmsV2.workflowCmsPage).toHaveBeenCalledWith(
        "ccf",
        "home",
        "publish",
        "Publicado desde el editor visual",
        "mock-token",
      );
    });
  });

  it("rejects invalid generic JSON without overwriting the stored section", async () => {
    (cmsV2.listCmsSections as any).mockResolvedValue([
      { id: "sec-feed-1", type: "feed", props_json: { title: "Seguro" }, sort_order: 0 },
    ]);

    render(<CmsBuilderPage />);
    await waitFor(() => {
      expect(puckPropsCaptured?.data?.content?.[0]?.props?.__cms_json).toContain("Seguro");
    });

    await act(async () => {
      await puckPropsCaptured.onPublish({
        content: [{ type: "feed", props: { id: "sec-feed-1", __cms_json: "{ inválido" } }],
      });
    });

    expect(cmsV2.patchCmsSection).not.toHaveBeenCalled();
    expect(cmsV2.workflowCmsPage).not.toHaveBeenCalled();
  });

  it("reports when the draft is saved but publishing fails", async () => {
    (cmsV2.workflowCmsPage as any).mockRejectedValueOnce(new Error("workflow unavailable"));

    render(<CmsBuilderPage />);
    await waitFor(() => {
      expect(screen.getByTestId("puck-editor-mock")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith("Borrador guardado, pero la publicación falló");
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
