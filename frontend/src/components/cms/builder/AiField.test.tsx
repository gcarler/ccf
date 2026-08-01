/* eslint-disable @typescript-eslint/no-explicit-any */
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
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

vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({
    token: "mocked-auth-token",
    user: { role: "admin" },
  }),
}));

describe("AiField", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders label, text input, prompt bar, and default suggestion chips", () => {
    const onChange = vi.fn();
    render(<AiField label="Título de la Sección" value="Mi Título" onChange={onChange} fieldType="title" />);

    expect(screen.getByText("Título de la Sección")).toBeInTheDocument();
    
    const input = screen.getByDisplayValue("Mi Título") as HTMLInputElement;
    expect(input).toBeInTheDocument();
    expect(input.tagName).toBe("INPUT");

    expect(screen.getByText("Redactar con IA")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Tema para la IA...")).toBeInTheDocument();

    DEFAULT_PROMPT_SUGGESTIONS.title.forEach((suggestion) => {
      expect(screen.getByText(`+ ${suggestion}`)).toBeInTheDocument();
    });
  });

  it("renders textarea when isTextArea prop is true", () => {
    const onChange = vi.fn();
    render(
      <AiField
        label="Descripción Principal"
        value="Texto largo inicial"
        onChange={onChange}
        isTextArea
        fieldType="description"
      />
    );

    const textarea = screen.getByDisplayValue("Texto largo inicial") as HTMLTextAreaElement;
    expect(textarea).toBeInTheDocument();
    expect(textarea.tagName).toBe("TEXTAREA");
  });

  it("calls onChange when user types directly into input or textarea", () => {
    const onChange = vi.fn();
    render(<AiField label="Título" value="" onChange={onChange} />);

    const input = screen.getByPlaceholderText("Escribe aquí...");
    fireEvent.change(input, { target: { value: "Nuevo Título Manual" } });

    expect(onChange).toHaveBeenCalledTimes(1);
    expect(onChange).toHaveBeenCalledWith("Nuevo Título Manual");
  });

  it("executes /system/ai/generate API call and updates value when prompt is submitted", async () => {
    const onChange = vi.fn();
    (apiFetch as any).mockResolvedValueOnce({
      response: "### **Título:** Misión Institucional Pro",
    });

    render(<AiField label="Título" value="" onChange={onChange} token="test-custom-token" />);

    const promptInput = screen.getByPlaceholderText("Tema para la IA...");
    fireEvent.change(promptInput, { target: { value: "Visión 2026" } });

    const generateBtn = screen.getByRole("button", { name: /Redactar IA/i });
    fireEvent.click(generateBtn);

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith("/system/ai/generate", {
        method: "POST",
        token: "test-custom-token",
        body: {
          prompt: 'Genera un título llamativo sobre el siguiente tema: "Visión 2026". Devuelve directamente el texto sugerido sin saludos ni explicaciones.',
          context: "Sección de página web. Rol: Redactor Creativo. Campo: Título.",
        },
      });
    });

    expect(onChange).toHaveBeenCalledWith("Misión Institucional Pro");
    expect(toast.success).toHaveBeenCalledWith("Contenido generado por la IA");
  });

  it("executes /system/ai/generate when clicking a quick-suggestion chip", async () => {
    const onChange = vi.fn();
    (apiFetch as any).mockResolvedValueOnce({
      response: "Un llamado a la acción transformador",
    });

    render(<AiField label="Botón CTA" value="" onChange={onChange} fieldType="cta" />);

    const chip = screen.getByText("+ Llamado a la acción");
    fireEvent.click(chip);

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith("/system/ai/generate", expect.objectContaining({
        method: "POST",
        token: "mocked-auth-token",
      }));
    });

    expect(onChange).toHaveBeenCalledWith("Un llamado a la action transformador".replace("action", "acción"));
    expect(toast.success).toHaveBeenCalledWith("Contenido generado por la IA");
  });

  it("displays toast error on API failure without calling onChange", async () => {
    const onChange = vi.fn();
    (apiFetch as any).mockRejectedValueOnce(new Error("Network Error"));

    render(<AiField label="Título" value="" onChange={onChange} />);

    const promptInput = screen.getByPlaceholderText("Tema para la IA...");
    fireEvent.change(promptInput, { target: { value: "Error Test" } });

    const generateBtn = screen.getByRole("button", { name: /Redactar IA/i });
    fireEvent.click(generateBtn);

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith("Error al conectar con la IA de la plataforma");
    });

    expect(onChange).not.toHaveBeenCalled();
  });

  it("renders disabled state and loading indicator while generating", async () => {
    const onChange = vi.fn();
    let resolveApi: any;
    const apiPromise = new Promise((resolve) => {
      resolveApi = resolve;
    });
    (apiFetch as any).mockReturnValueOnce(apiPromise);

    render(<AiField label="Título" value="Original" onChange={onChange} />);

    const promptInput = screen.getByPlaceholderText("Tema para la IA...");
    fireEvent.change(promptInput, { target: { value: "Loading Test" } });

    const generateBtn = screen.getByRole("button", { name: /Redactar IA/i });
    fireEvent.click(generateBtn);

    expect(screen.getByText("Redactando...")).toBeInTheDocument();

    resolveApi({ response: "Nuevo Texto Generado" });

    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith("Nuevo Texto Generado");
    });
  });
});
