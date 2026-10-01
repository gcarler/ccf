import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import TwoFactorDrawer from "./TwoFactorDrawer";

vi.mock("@/lib/http", () => ({
  apiFetch: vi.fn(),
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

import { apiFetch } from "@/lib/http";

describe("TwoFactorDrawer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("does not render when closed", () => {
    render(<TwoFactorDrawer isOpen={false} onClose={() => {}} />);
    expect(screen.queryByText(/Autenticación de Dos Factores/i)).not.toBeInTheDocument();
  });

  it("renders setup call-to-action when 2FA is inactive", async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce({
      is_mfa_enabled: false,
      has_secret: false,
      backup_codes_count: 0,
    });

    render(<TwoFactorDrawer isOpen={true} onClose={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText(/2FA No Activado/i)).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: /Configurar 2FA Ahora/i })).toBeInTheDocument();
  });

  it("initiates setup flow when clicking configure button", async () => {
    vi.mocked(apiFetch)
      .mockResolvedValueOnce({
        is_mfa_enabled: false,
        has_secret: false,
        backup_codes_count: 0,
      })
      .mockResolvedValueOnce({
        secret: "HXDMVJECJJWSRB3HWIZR4IFUGFTMXBOZ",
        otpauth_uri: "otpauth://totp/CCF:admin@ccf.org?secret=HXDMVJECJJWSRB3HWIZR4IFUGFTMXBOZ",
        is_mfa_enabled: false,
        backup_codes: ["12345678", "87654321"],
      });

    render(<TwoFactorDrawer isOpen={true} onClose={() => {}} />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Configurar 2FA Ahora/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /Configurar 2FA Ahora/i }));

    await waitFor(() => {
      expect(screen.getByText("HXDMVJECJJWSRB3HWIZR4IFUGFTMXBOZ")).toBeInTheDocument();
      expect(screen.getByText(/2. Ingresa el Código de Verificación/i)).toBeInTheDocument();
    });
  });

  it("renders active state and backup codes count when 2FA is enabled", async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce({
      is_mfa_enabled: true,
      has_secret: true,
      backup_codes_count: 8,
    });

    render(<TwoFactorDrawer isOpen={true} onClose={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText(/2FA Activo y Protegido/i)).toBeInTheDocument();
      expect(screen.getByText(/8 disponibles/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/Zona de Desactivación/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Desactivar Protección 2FA/i })).toBeInTheDocument();
  });
});
