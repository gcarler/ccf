import React from "react";
import { render, screen, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import CmsNewsletterManagement from "./page";

const mockUseAuth = vi.fn();
vi.mock("@/context/AuthContext", () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock("@/lib/cms/v2", () => ({
  listCmsSites: vi.fn().mockResolvedValue([{ id: "s1", site_key: "ccf", name: "CCF Main" }]),
  listCmsNewsletters: vi.fn(),
  listCmsSubscribers: vi.fn(),
  createCmsNewsletter: vi.fn(),
  patchCmsNewsletter: vi.fn(),
  deleteCmsNewsletter: vi.fn(),
  sendCmsNewsletter: vi.fn(),
  createCmsSubscriber: vi.fn(),
  patchCmsSubscriber: vi.fn(),
  deleteCmsSubscriber: vi.fn(),
  importCmsSubscribers: vi.fn(),
}));

import { listCmsNewsletters, listCmsSubscribers } from "@/lib/cms/v2";

describe("CmsNewsletterManagement", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({
      token: "test-token",
      user: { role: "admin" },
    });
  });

  it("renders page header and empty campaign state when no campaigns exist", async () => {
    vi.mocked(listCmsNewsletters).mockResolvedValue([]);
    vi.mocked(listCmsSubscribers).mockResolvedValue([]);

    render(<CmsNewsletterManagement />);

    expect(screen.getByText(/Newsletter & Email Marketing/i)).toBeInTheDocument();

    await act(async () => {
      await Promise.resolve();
    });

    expect(screen.getByText(/No se encontraron campañas/i)).toBeInTheDocument();
  });

  it("renders newsletters list when items exist", async () => {
    vi.mocked(listCmsNewsletters).mockResolvedValue([
      {
        id: "n1",
        site_id: "s1",
        name: "Boletín Semanal",
        subject: "Noticias CCF",
        content_html: "<p>Contenido</p>",
        status: "draft",
        scheduled_at: null,
        sent_at: null,
        recipient_count: 0,
        created_at: "2026-07-30T00:00:00Z",
        updated_at: "2026-07-30T00:00:00Z",
      },
    ]);
    vi.mocked(listCmsSubscribers).mockResolvedValue([]);

    render(<CmsNewsletterManagement />);

    await act(async () => {
      await Promise.resolve();
    });

    expect(screen.getByText("Boletín Semanal")).toBeInTheDocument();
    expect(screen.getByText(/Noticias CCF/i)).toBeInTheDocument();
  });

  it("renders subscribers list when switching to subscribers tab", async () => {
    vi.mocked(listCmsNewsletters).mockResolvedValue([]);
    vi.mocked(listCmsSubscribers).mockResolvedValue([
      {
        id: "sub1",
        site_id: "s1",
        email: "juan@ejemplo.com",
        name: "Juan Pérez",
        is_active: true,
        subscribed_at: "2026-07-30T00:00:00Z",
        unsubscribed_at: null,
        source: "manual",
      },
    ]);

    render(<CmsNewsletterManagement />);

    await act(async () => {
      await Promise.resolve();
    });

    const subscribersTabButton = screen.getByRole("button", { name: /Suscriptores/i });
    act(() => {
      subscribersTabButton.click();
    });

    expect(screen.getByText("juan@ejemplo.com")).toBeInTheDocument();
    expect(screen.getByText("Juan Pérez")).toBeInTheDocument();
  });
});
