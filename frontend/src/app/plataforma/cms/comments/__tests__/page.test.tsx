import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import CmsCommentsManagementPage from "../page";
import * as cmsV2 from "@/lib/cms/v2";

vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({
    token: "mock-token",
    user: { role: "admin" },
  }),
}));

vi.mock("@/lib/cms/permissions", () => ({
  canEditCms: () => true,
}));

vi.mock("@/lib/cms/v2", () => ({
  listCmsPostComments: vi.fn(),
  patchCmsPostCommentStatus: vi.fn(),
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}));

describe("CmsCommentsManagementPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders page header and tabs with pending count", async () => {
    vi.mocked(cmsV2.listCmsPostComments).mockResolvedValueOnce({
      items: [
        {
          id: "comment-1",
          post_id: "post-1",
          parent_id: null,
          author_name: "Gabriel",
          author_email: "gabriel@example.com",
          content: "Comentario para moderar",
          status: "pending",
          post_title: "Reflexión Dominical",
          created_at: "2026-07-31T00:00:00Z",
          updated_at: "2026-07-31T00:00:00Z",
        },
      ],
      total: 1,
      skip: 0,
      limit: 100,
      pending_count: 5,
    });

    render(<CmsCommentsManagementPage />);

    await waitFor(() => {
      expect(screen.getByText("Moderación de Comentarios")).toBeInTheDocument();
      expect(screen.getByText("Pendientes")).toBeInTheDocument();
      expect(screen.getByText("5")).toBeInTheDocument();
      expect(screen.getByText("Gabriel")).toBeInTheDocument();
      expect(screen.getByText("gabriel@example.com")).toBeInTheDocument();
      expect(screen.getByText("Reflexión Dominical")).toBeInTheDocument();
      expect(screen.getByText("Comentario para moderar")).toBeInTheDocument();
    });
  });

  it("handles status updates when clicking action buttons", async () => {
    vi.mocked(cmsV2.listCmsPostComments).mockResolvedValue({
      items: [
        {
          id: "comment-1",
          post_id: "post-1",
          parent_id: null,
          author_name: "Gabriel",
          author_email: "gabriel@example.com",
          content: "Comentario para moderar",
          status: "pending",
          post_title: "Reflexión Dominical",
          created_at: "2026-07-31T00:00:00Z",
          updated_at: "2026-07-31T00:00:00Z",
        },
      ],
      total: 1,
      skip: 0,
      limit: 100,
      pending_count: 1,
    });

    vi.mocked(cmsV2.patchCmsPostCommentStatus).mockResolvedValueOnce({
      id: "comment-1",
      post_id: "post-1",
      parent_id: null,
      author_name: "Gabriel",
      author_email: "gabriel@example.com",
      content: "Comentario para moderar",
      status: "approved",
      created_at: "2026-07-31T00:00:00Z",
      updated_at: "2026-07-31T00:00:00Z",
    });

    render(<CmsCommentsManagementPage />);

    await waitFor(() => {
      expect(screen.getByText("Gabriel")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /aprobar comentario/i }));

    await waitFor(() => {
      expect(cmsV2.patchCmsPostCommentStatus).toHaveBeenCalledWith(
        "ccf",
        "comment-1",
        "approved",
        "mock-token"
      );
    });
  });
});
