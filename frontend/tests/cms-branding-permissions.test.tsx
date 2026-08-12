import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

// Rol mutable por test (vi.hoisted: accesible desde la factory del mock hoisted).
const { authMock } = vi.hoisted(() => ({
  authMock: { role: "estudiante" as string },
}));

vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({
    token: "test-token",
    user: { role: authMock.role },
  }),
}));

vi.mock("@/lib/site-branding", () => ({
  useSiteBranding: () => ({
    logoUrl: "",
    logoName: "",
  }),
}));

vi.mock("@/lib/cms/v2", () => ({
  listCmsThemes: vi.fn(),
  patchCmsTheme: vi.fn(),
}));

vi.mock("@/lib/http", () => ({
  apiFetch: vi.fn().mockResolvedValue({ items: [], total: 0 }),
}));

vi.mock("@/components/ui/OptimizedImage", () => ({
  default: (props: { alt?: string }) => <img alt={props.alt || "mock-image"} />,
}));

vi.mock("sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}));

import { apiFetch } from "@/lib/http";
import { listCmsThemes, patchCmsTheme } from "@/lib/cms/v2";
import { toast } from "sonner";
import type { CmsTheme } from "@/types/cms-v2";
import CmsBrandingPage from "../src/app/plataforma/cms/branding/page";

// Espejo de canEditCms (lib/cms/permissions.ts): roles Kernel (administrador,
// gestor, editor) + legacy (admin/coordinador/docente/pastor).
const EDITABLE_ROLES = ["admin", "administrador", "gestor", "editor", "coordinador", "docente", "pastor"];
const READ_ONLY_ROLES = ["estudiante", "aspirante", "visitante", "role-inexistente", ""];

const activeTheme: CmsTheme = {
  id: "theme-1",
  site_id: "site-1",
  name: "Default",
  tokens_json: { "--site-primary": "#7c3aed" },
  is_active: true,
  status: "active",
  version: 1,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

describe("CmsBrandingPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    authMock.role = "estudiante";
    vi.mocked(listCmsThemes).mockResolvedValue([activeTheme]);
    vi.mocked(patchCmsTheme).mockResolvedValue(activeTheme);
  });

  it.each(READ_ONLY_ROLES)("bloquea la edición para rol '%s'", (role) => {
    authMock.role = role;
    render(<CmsBrandingPage />);

    expect(screen.getByRole("button", { name: /guardar/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /subir imagen/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /media library/i })).toBeDisabled();
    expect(screen.getByText(/solo lectura/i)).toBeTruthy();
  });

  it.each(EDITABLE_ROLES)("habilita la edición para rol '%s'", (role) => {
    authMock.role = role;
    render(<CmsBrandingPage />);

    expect(screen.getByRole("button", { name: /guardar/i })).toBeEnabled();
    expect(screen.getByRole("button", { name: /subir imagen/i })).toBeEnabled();
    expect(screen.queryByText(/solo lectura/i)).toBeNull();
  });

  it("documenta el guard de UI: el botón Guardar disabled impide llegar al backend", () => {
    render(<CmsBrandingPage />);
    fireEvent.click(screen.getByRole("button", { name: /guardar/i }));

    expect(listCmsThemes).not.toHaveBeenCalled();
    expect(patchCmsTheme).not.toHaveBeenCalled();
  });

  it("bloquea el upload de logo sin permiso (guard real de handleUpload)", () => {
    authMock.role = "estudiante";
    const { container } = render(<CmsBrandingPage />);

    const fileInput = container.querySelector('input[type="file"]');
    expect(fileInput).not.toBeNull();
    fireEvent.change(fileInput as HTMLInputElement, {
      target: { files: [new File(["logo"], "logo.png", { type: "image/png" })] },
    });

    expect(vi.mocked(toast.error)).toHaveBeenCalledWith(
      "No tienes permisos para editar el branding"
    );
    expect(apiFetch).not.toHaveBeenCalled();
  });

  it("guarda el branding actualizando los tokens del tema activo cuando hay permiso", async () => {
    authMock.role = "admin";
    render(<CmsBrandingPage />);

    fireEvent.change(screen.getByPlaceholderText("El Faro"), {
      target: { value: "Comunidad El Faro" },
    });
    fireEvent.change(screen.getByPlaceholderText(/api\/static\/cms\/site_logo/), {
      target: { value: "/api/static/cms/site_logo/logo.png" },
    });

    fireEvent.click(screen.getByRole("button", { name: /guardar/i }));

    await waitFor(() => {
      expect(listCmsThemes).toHaveBeenCalledWith("ccf", "test-token");
      expect(patchCmsTheme).toHaveBeenCalledWith(
        "ccf",
        "theme-1",
        {
          tokens_json: expect.objectContaining({
            "--site-primary": "#7c3aed",
            "--site-logo-url": "/api/static/cms/site_logo/logo.png",
            "--site-logo-name": "Comunidad El Faro",
          }),
        },
        "test-token",
      );
    });
  });
});
