import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { apiFetch } from "@/lib/http";
import BrokenLinksPage from "./page";

vi.mock("@/lib/http", () => ({ apiFetch: vi.fn() }));

const apiFetchMock = vi.mocked(apiFetch);
vi.mock("@/lib/site-config", () => ({ SITE_KEY: "test-site" }));
vi.mock("sonner", () => ({ toast: { error: vi.fn() } }));

describe("BrokenLinksPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading state and then the empty state", async () => {
    apiFetchMock.mockResolvedValueOnce([]);
    render(<BrokenLinksPage />);

    expect(screen.getByText(/cargando/i)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText(/sin enlaces/i)).toBeInTheDocument());
  });

  it("renders broken links and the resolve button", async () => {
    apiFetchMock.mockResolvedValueOnce([
      { id: "1", source_url: "/a", target_url: "/b", status_code: 404, error_message: "Not found", is_broken: true, resolved_at: null, checked_at: "2024-01-01" },
    ]);
    render(<BrokenLinksPage />);

    await waitFor(() => expect(screen.getByText("/b")).toBeInTheDocument());
    expect(screen.getByText(/marcar resuelto/i)).toBeInTheDocument();
  });

  it("calls the API with resolved=true when the resolved tab is active", async () => {
    apiFetchMock.mockResolvedValueOnce([]);
    render(<BrokenLinksPage />);
    await waitFor(() => expect(screen.getByText(/sin enlaces/i)).toBeInTheDocument());

    apiFetchMock.mockResolvedValueOnce([]);
    fireEvent.click(screen.getByRole("button", { name: /resueltos/i }));

    await waitFor(() =>
      expect(apiFetchMock).toHaveBeenLastCalledWith(
        expect.stringContaining("resolved=true"),
        expect.anything(),
      ),
    );
  });

  it("calls resolve endpoint and reloads when resolving a link", async () => {
    apiFetchMock
      .mockResolvedValueOnce([
        { id: "1", source_url: "/a", target_url: "/b", status_code: 404, error_message: "Not found", is_broken: true, resolved_at: null, checked_at: "2024-01-01" },
      ])
      .mockResolvedValueOnce({})
      .mockResolvedValueOnce([]);

    render(<BrokenLinksPage />);
    await waitFor(() => expect(screen.getByText(/marcar resuelto/i)).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: /marcar resuelto/i }));

    await waitFor(() =>
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/cms/v2/broken-links/1/resolve",
        expect.objectContaining({ method: "POST" }),
      ),
    );
  });
});
