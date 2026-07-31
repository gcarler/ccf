import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { PostComments } from "../PostComments";
import * as cmsV2 from "@/lib/cms/v2";

vi.mock("@/lib/cms/v2", () => ({
  getPublicPostComments: vi.fn(),
  createPublicPostComment: vi.fn(),
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}));

describe("PostComments Component", () => {
  const mockPostId = "post-123-uuid";

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders header badge and comments list", async () => {
    const mockComments = [
      {
        id: "c1",
        post_id: mockPostId,
        parent_id: null,
        author_name: "Juan",
        content: "Excelente post",
        created_at: "2026-07-31T00:00:00Z",
        replies: [
          {
            id: "r1",
            post_id: mockPostId,
            parent_id: "c1",
            author_name: "Pedro",
            content: "Totalmente de acuerdo",
            created_at: "2026-07-31T00:10:00Z",
            replies: [],
          },
        ],
      },
    ];

    vi.mocked(cmsV2.getPublicPostComments).mockResolvedValueOnce(mockComments);

    render(<PostComments postId={mockPostId} />);

    await waitFor(() => {
      expect(screen.getByTestId("comments-count-badge")).toHaveTextContent("2");
      expect(screen.getByText("Juan")).toBeInTheDocument();
      expect(screen.getByText("Excelente post")).toBeInTheDocument();
      expect(screen.getByText("Pedro")).toBeInTheDocument();
      expect(screen.getByText("Totalmente de acuerdo")).toBeInTheDocument();
    });
  });

  it("submits a new top-level comment", async () => {
    vi.mocked(cmsV2.getPublicPostComments).mockResolvedValueOnce([]);
    vi.mocked(cmsV2.createPublicPostComment).mockResolvedValueOnce({
      id: "new-c",
      post_id: mockPostId,
      parent_id: null,
      author_name: "Maria",
      author_email: "maria@example.com",
      content: "Nuevo comentario",
      status: "pending",
      created_at: "2026-07-31T00:00:00Z",
      updated_at: "2026-07-31T00:00:00Z",
    });

    render(<PostComments postId={mockPostId} />);

    await waitFor(() => {
      expect(screen.getByText("Deja un comentario")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByPlaceholderText("Tu nombre"), {
      target: { value: "Maria" },
    });
    fireEvent.change(screen.getByPlaceholderText("tu@email.com"), {
      target: { value: "maria@example.com" },
    });
    fireEvent.change(screen.getByPlaceholderText("Escribe tu comentario aquí..."), {
      target: { value: "Nuevo comentario" },
    });

    fireEvent.click(screen.getByRole("button", { name: /enviar comentario/i }));

    await waitFor(() => {
      expect(cmsV2.createPublicPostComment).toHaveBeenCalledWith(mockPostId, {
        author_name: "Maria",
        author_email: "maria@example.com",
        content: "Nuevo comentario",
      });
    });
  });

  it("opens inline reply form and submits a nested reply", async () => {
    const mockComments = [
      {
        id: "c1",
        post_id: mockPostId,
        parent_id: null,
        author_name: "Juan",
        content: "Excelente post",
        created_at: "2026-07-31T00:00:00Z",
        replies: [],
      },
    ];

    vi.mocked(cmsV2.getPublicPostComments).mockResolvedValueOnce(mockComments);
    vi.mocked(cmsV2.createPublicPostComment).mockResolvedValueOnce({
      id: "reply-1",
      post_id: mockPostId,
      parent_id: "c1",
      author_name: "Carlos",
      author_email: "carlos@example.com",
      content: "Mi respuesta",
      status: "pending",
      created_at: "2026-07-31T00:00:00Z",
      updated_at: "2026-07-31T00:00:00Z",
    });

    render(<PostComments postId={mockPostId} />);

    await waitFor(() => {
      expect(screen.getByText("Juan")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /responder/i }));

    expect(screen.getByTestId("inline-reply-form")).toBeInTheDocument();

    const inlineForm = screen.getByTestId("inline-reply-form");
    const nameInput = inlineForm.querySelector('input[placeholder="Tu nombre"]') as HTMLInputElement;
    const emailInput = inlineForm.querySelector('input[placeholder="Tu correo"]') as HTMLInputElement;
    const contentTextarea = inlineForm.querySelector('textarea[placeholder="Escribe tu respuesta..."]') as HTMLTextAreaElement;

    fireEvent.change(nameInput, { target: { value: "Carlos" } });
    fireEvent.change(emailInput, { target: { value: "carlos@example.com" } });
    fireEvent.change(contentTextarea, { target: { value: "Mi respuesta" } });

    fireEvent.click(screen.getByRole("button", { name: /enviar respuesta/i }));

    await waitFor(() => {
      expect(cmsV2.createPublicPostComment).toHaveBeenCalledWith(mockPostId, {
        author_name: "Carlos",
        author_email: "carlos@example.com",
        content: "Mi respuesta",
        parent_id: "c1",
      });
    });
  });
});
