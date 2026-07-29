import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { apiFetch } from "@/lib/http";
import SessionsPage from "./page";

vi.mock("@/lib/http", () => ({ apiFetch: vi.fn() }));

const apiFetchMock = vi.mocked(apiFetch);
vi.mock("sonner", () => ({ toast: { error: vi.fn() } }));

describe("SessionsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading state and then the empty state", async () => {
    apiFetchMock.mockResolvedValueOnce([]);
    render(<SessionsPage />);

    expect(screen.getByText(/cargando/i)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText(/sin sesiones/i)).toBeInTheDocument());
  });

  it("renders active sessions and the revoke button", async () => {
    apiFetchMock.mockResolvedValueOnce([
      { id: "1", browser: "Chrome", os: "Windows", is_mobile: false, ip_address: "127.0.0.1", last_activity_at: "2024-01-01", created_at: "2024-01-01" },
    ]);
    render(<SessionsPage />);

    await waitFor(() => expect(screen.getByText(/chrome en windows/i)).toBeInTheDocument());
    expect(screen.getByTitle(/revocar/i)).toBeInTheDocument();
  });

  it("revokes a single session and reloads", async () => {
    apiFetchMock.mockResolvedValueOnce([
      { id: "1", browser: "Chrome", os: "Windows", is_mobile: false, ip_address: "127.0.0.1", last_activity_at: "2024-01-01", created_at: "2024-01-01" },
    ]);
    render(<SessionsPage />);
    await waitFor(() => expect(screen.getByTitle(/revocar/i)).toBeInTheDocument());

    apiFetchMock.mockResolvedValueOnce({}).mockResolvedValueOnce([]);
    fireEvent.click(screen.getByTitle(/revocar/i));

    fireEvent.click(screen.getByRole("button", { name: /confirmar revocación/i }));

    await waitFor(() =>
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/cms/v2/sessions/1/revoke",
        expect.objectContaining({ method: "POST" }),
      ),
    );
  });

  it("revokes all sessions when more than one exists", async () => {
    apiFetchMock.mockResolvedValueOnce([
      { id: "1", browser: "Chrome", os: "Windows", is_mobile: false, ip_address: "127.0.0.1", last_activity_at: "2024-01-01", created_at: "2024-01-01" },
      { id: "2", browser: "Safari", os: "iOS", is_mobile: true, ip_address: "127.0.0.2", last_activity_at: "2024-01-01", created_at: "2024-01-01" },
    ]);
    render(<SessionsPage />);
    await waitFor(() => expect(screen.getByText(/revocar todas/i)).toBeInTheDocument());

    apiFetchMock.mockResolvedValueOnce({}).mockResolvedValueOnce([]);
    fireEvent.click(screen.getByText(/revocar todas/i));

    fireEvent.click(screen.getByRole("button", { name: /confirmar revocación/i }));

    await waitFor(() =>
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/cms/v2/sessions/revoke-all",
        expect.objectContaining({ method: "POST" }),
      ),
    );
  });
});
