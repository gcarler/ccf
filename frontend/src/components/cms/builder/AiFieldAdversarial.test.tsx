/* eslint-disable @typescript-eslint/no-explicit-any */
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import AiField, { DEFAULT_PROMPT_SUGGESTIONS } from "./AiField";
import { apiFetch } from "@/lib/http";
import { toast } from "sonner";

vi.mock("@/lib/http", () => ({
  apiFetch: vi.fn(),
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

// Mock useAuth returning null token by default unless overridden
let mockAuthToken: string | null = null;
vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({
    token: mockAuthToken,
    user: mockAuthToken ? { role: "admin" } : null,
  }),
}));

describe("AiField Adversarial & Edge Case Suite", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAuthToken = null;
    sessionStorage.clear();
  });

  afterEach(() => {
    sessionStorage.clear();
  });

  describe("1. Empty Prompt Handling", () => {
    it("does not call API or trigger toast when Redactar IA button is clicked with empty or whitespace prompt", async () => {
      const onChange = vi.fn();
      render(<AiField label="Title" value="" onChange={onChange} token="valid-token" />);

      const generateBtn = screen.getByRole("button", { name: /Redactar IA/i });
      expect(generateBtn).toBeDisabled();

      // Attempt click anyway
      fireEvent.click(generateBtn);
      expect(apiFetch).not.toHaveBeenCalled();
      expect(onChange).not.toHaveBeenCalled();
    });

    it("does not call API when Enter key is pressed in empty prompt input", async () => {
      const onChange = vi.fn();
      render(<AiField label="Title" value="" onChange={onChange} token="valid-token" />);

      const promptInput = screen.getByPlaceholderText("Tema para la IA...");
      fireEvent.change(promptInput, { target: { value: "   " } });
      fireEvent.keyDown(promptInput, { key: "Enter", code: "Enter" });

      expect(apiFetch).not.toHaveBeenCalled();
      expect(onChange).not.toHaveBeenCalled();
    });
  });

  describe("2. Token Resolution Priority (Prop > AuthContext > SessionStorage)", () => {
    it("uses explicit token prop when provided, ignoring AuthContext and SessionStorage", async () => {
      mockAuthToken = "auth-context-token";
      sessionStorage.setItem("ccf_token", "session-storage-token");
      const onChange = vi.fn();
      (apiFetch as any).mockResolvedValueOnce({ response: "Response Text" });

      render(<AiField label="Title" value="" onChange={onChange} token="explicit-prop-token" />);

      const promptInput = screen.getByPlaceholderText("Tema para la IA...");
      fireEvent.change(promptInput, { target: { value: "Test Token" } });
      const generateBtn = screen.getByRole("button", { name: /Redactar IA/i });
      fireEvent.click(generateBtn);

      await waitFor(() => {
        expect(apiFetch).toHaveBeenCalledWith("/system/ai/generate", expect.objectContaining({
          token: "explicit-prop-token",
        }));
      });
    });

    it("uses AuthContext token when token prop is undefined", async () => {
      mockAuthToken = "auth-context-token";
      sessionStorage.setItem("ccf_token", "session-storage-token");
      const onChange = vi.fn();
      (apiFetch as any).mockResolvedValueOnce({ response: "Response Text" });

      render(<AiField label="Title" value="" onChange={onChange} />);

      const promptInput = screen.getByPlaceholderText("Tema para la IA...");
      fireEvent.change(promptInput, { target: { value: "Test Token" } });
      const generateBtn = screen.getByRole("button", { name: /Redactar IA/i });
      fireEvent.click(generateBtn);

      await waitFor(() => {
        expect(apiFetch).toHaveBeenCalledWith("/system/ai/generate", expect.objectContaining({
          token: "auth-context-token",
        }));
      });
    });

    it("falls back to sessionStorage token when token prop and AuthContext are empty", async () => {
      mockAuthToken = null;
      sessionStorage.setItem("ccf_token", "session-storage-token");
      const onChange = vi.fn();
      (apiFetch as any).mockResolvedValueOnce({ response: "Response Text" });

      render(<AiField label="Title" value="" onChange={onChange} />);

      const promptInput = screen.getByPlaceholderText("Tema para la IA...");
      fireEvent.change(promptInput, { target: { value: "Test Token" } });
      const generateBtn = screen.getByRole("button", { name: /Redactar IA/i });
      fireEvent.click(generateBtn);

      await waitFor(() => {
        expect(apiFetch).toHaveBeenCalledWith("/system/ai/generate", expect.objectContaining({
          token: "session-storage-token",
        }));
      });
    });

    it("shows error toast when no token is available anywhere", async () => {
      mockAuthToken = null;
      sessionStorage.clear();
      const onChange = vi.fn();

      render(<AiField label="Title" value="" onChange={onChange} token={null} />);

      const promptInput = screen.getByPlaceholderText("Tema para la IA...");
      fireEvent.change(promptInput, { target: { value: "No Token Test" } });
      const generateBtn = screen.getByRole("button", { name: /Redactar IA/i });
      fireEvent.click(generateBtn);

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith("Error al conectar con la IA de la plataforma");
      });
      expect(apiFetch).not.toHaveBeenCalled();
      expect(onChange).not.toHaveBeenCalled();
    });
  });

  describe("3. Markdown Stripping & Cleaning Pipeline", () => {
    it("strips headers, bold prefixes, bullet points, and outer quotes", async () => {
      const onChange = vi.fn();
      mockAuthToken = "token-123";

      // Test markdown noise: ### Header, **Título:**, * bullets, quotes
      (apiFetch as any).mockResolvedValueOnce({
        response: '"### **Título:** Bienvenido a nuestra comunidad CCF"',
      });

      render(<AiField label="Title" value="" onChange={onChange} />);

      const chip = screen.getByText(`+ ${DEFAULT_PROMPT_SUGGESTIONS.general[0]}`);
      fireEvent.click(chip);

      await waitFor(() => {
        expect(onChange).toHaveBeenCalledWith("Bienvenido a nuestra comunidad CCF");
      });
    });

    it("handles multi-line markdown headers and list items cleanly", async () => {
      const onChange = vi.fn();
      mockAuthToken = "token-123";

      (apiFetch as any).mockResolvedValueOnce({
        response: "## **Cuerpo:**\n* Primer punto informativo\n* Segundo punto relevante",
      });

      render(<AiField label="Body" value="" onChange={onChange} isTextArea />);

      const chip = screen.getByText(`+ ${DEFAULT_PROMPT_SUGGESTIONS.general[0]}`);
      fireEvent.click(chip);

      await waitFor(() => {
        expect(onChange).toHaveBeenCalledWith("Primer punto informativo\nSegundo punto relevante");
      });
    });
  });

  describe("4. API Error Handling & Toasts", () => {
    it("triggers toast.error on API rejection", async () => {
      const onChange = vi.fn();
      mockAuthToken = "token-123";
      (apiFetch as any).mockRejectedValueOnce(new Error("500 Server Error"));

      render(<AiField label="Title" value="" onChange={onChange} />);

      const chip = screen.getByText(`+ ${DEFAULT_PROMPT_SUGGESTIONS.general[0]}`);
      fireEvent.click(chip);

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith("Error al conectar con la IA de la plataforma");
      });
      expect(onChange).not.toHaveBeenCalled();
    });

    it("triggers toast.error when API response object has no response property", async () => {
      const onChange = vi.fn();
      mockAuthToken = "token-123";
      (apiFetch as any).mockResolvedValueOnce(null);

      render(<AiField label="Title" value="" onChange={onChange} />);

      const chip = screen.getByText(`+ ${DEFAULT_PROMPT_SUGGESTIONS.general[0]}`);
      fireEvent.click(chip);

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith("Error al conectar con la IA de la plataforma");
      });
      expect(onChange).not.toHaveBeenCalled();
    });
  });

  describe("5. Multiline vs Single-line Behavior", () => {
    it("sends single-line prompt instruction for input (isTextArea=false)", async () => {
      const onChange = vi.fn();
      mockAuthToken = "token-123";
      (apiFetch as any).mockResolvedValueOnce({ response: "Título Genial" });

      render(<AiField label="Hero Title" value="" onChange={onChange} isTextArea={false} fieldType="title" />);

      const promptInput = screen.getByPlaceholderText("Tema para la IA...");
      fireEvent.change(promptInput, { target: { value: "Navidad" } });
      const generateBtn = screen.getByRole("button", { name: /Redactar IA/i });
      fireEvent.click(generateBtn);

      await waitFor(() => {
        expect(apiFetch).toHaveBeenCalledWith("/system/ai/generate", expect.objectContaining({
          body: expect.objectContaining({
            prompt: expect.stringContaining("título llamativo"),
          }),
        }));
      });
    });

    it("sends multi-line prompt instruction for textarea (isTextArea=true)", async () => {
      const onChange = vi.fn();
      mockAuthToken = "token-123";
      (apiFetch as any).mockResolvedValueOnce({ response: "Texto largo..." });

      render(<AiField label="Hero Body" value="" onChange={onChange} isTextArea={true} fieldType="body" />);

      const promptInput = screen.getByPlaceholderText("Tema para la IA...");
      fireEvent.change(promptInput, { target: { value: "Comunidad" } });
      const generateBtn = screen.getByRole("button", { name: /Redactar IA/i });
      fireEvent.click(generateBtn);

      await waitFor(() => {
        expect(apiFetch).toHaveBeenCalledWith("/system/ai/generate", expect.objectContaining({
          body: expect.objectContaining({
            prompt: expect.stringContaining("texto corto de 2 o 3 párrafos"),
          }),
        }));
      });
    });
  });
});
