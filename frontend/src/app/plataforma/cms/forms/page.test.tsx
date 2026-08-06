import React from "react";
import { render, screen, act, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import CmsFormsManagement from "./page";

const mockUseAuth = vi.fn();
vi.mock("@/context/AuthContext", () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock("@/lib/cms/v2", () => ({
  listCmsSites: vi.fn().mockResolvedValue([{ id: "s1", site_key: "ccf", name: "CCF Main" }]),
  listCmsForms: vi.fn(),
  createCmsForm: vi.fn(),
  putCmsForm: vi.fn(),
  patchCmsForm: vi.fn(),
  deleteCmsForm: vi.fn(),
  listCmsFormSubmissions: vi.fn(),
}));

import { listCmsForms, listCmsFormSubmissions } from "@/lib/cms/v2";

describe("CmsFormsManagement Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({
      token: "test-token",
      user: { role: "admin" },
    });
  });

  it("renders page title and empty state when no forms exist", async () => {
    vi.mocked(listCmsForms).mockResolvedValue([]);

    render(<CmsFormsManagement />);

    expect(screen.getByText(/Módulo de Formularios de Contacto/i)).toBeInTheDocument();
    expect(screen.getByText(/Formularios \(0\)/i)).toBeInTheDocument();

    await act(async () => {
      await Promise.resolve();
    });

    expect(screen.getByText(/No hay formularios registrados/i)).toBeInTheDocument();
  });

  it("renders form cards and toggles to Respuestas tab when forms exist", async () => {
    vi.mocked(listCmsForms).mockResolvedValue([
      {
        id: "form-1",
        site_id: "s1",
        name: "Contacto Principal",
        description: "Formulario de información general",
        fields: [{ id: "f1", label: "Nombre", type: "text", required: true }],
        submit_button_text: "Enviar",
        success_message: "¡Gracias por tu mensaje!",
        notify_emails: ["admin@ccf.org"],
        is_active: true,
        submission_count: 5,
        created_at: "2026-07-30T00:00:00Z",
        updated_at: "2026-07-30T00:00:00Z",
      },
    ]);

    vi.mocked(listCmsFormSubmissions).mockResolvedValue({
      page: 1,
      page_size: 20,
      total: 1,
      items: [
        {
          id: "sub-1",
          form_id: "form-1",
          data: { Nombre: "Carlos Ruiz" },
          submitted_at: "2026-07-30T10:00:00Z",
          ip_address: "127.0.0.1",
        },
      ],
    });

    render(<CmsFormsManagement />);

    await act(async () => {
      await Promise.resolve();
    });

    expect(screen.getByText("Contacto Principal")).toBeInTheDocument();
    expect(screen.getByText(/5 respuestas/i)).toBeInTheDocument();

    // Click "Respuestas" tab
    const respuestasTab = screen.getByRole("button", { name: /^Respuestas$/i });
    fireEvent.click(respuestasTab);

    await act(async () => {
      await Promise.resolve();
    });

    expect(screen.getByText(/Carlos Ruiz/i)).toBeInTheDocument();
  });

  it("abre el constructor, muestra el catálogo de tipos y la vista previa", async () => {
    vi.mocked(listCmsForms).mockResolvedValue([]);
    vi.mocked(listCmsFormSubmissions).mockResolvedValue({
      page: 1, page_size: 20, total: 0, items: [],
    });

    render(<CmsFormsManagement />);
    await act(async () => { await Promise.resolve(); });

    // Abrir el drawer "Nuevo Formulario"
    fireEvent.click(screen.getByRole("button", { name: /Nuevo Formulario/i }));
    expect(screen.getByText(/Información General/i)).toBeInTheDocument();

    // El catálogo de tipos expone los 19 tipos (incluye Seleccionar múltiple y Saltar página).
    expect(screen.getByRole("button", { name: /\+ Selección múltiple/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /\+ Salto de página/i })).toBeInTheDocument();

    // Cambiar a la pestaña "Vista previa"
    fireEvent.click(screen.getByRole("button", { name: /Vista previa/i }));
    // El renderer preview muestra los 3 campos por defecto (Nombre / Correo / Mensaje).
    expect(screen.getByText(/Nombre completo/i)).toBeInTheDocument();
    expect(screen.getByText(/Correo electrónico/i)).toBeInTheDocument();
  });
});
