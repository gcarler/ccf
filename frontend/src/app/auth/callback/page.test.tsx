import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import AuthCallbackPage from "./page";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";

const push = vi.fn();
const login = vi.fn().mockResolvedValue(undefined);
const router = { push };

vi.mock("next/navigation", () => ({
  useRouter: () => router,
}));

vi.mock("@/context/AuthContext", () => ({
  useAuth: vi.fn(),
}));

vi.mock("@/lib/http", () => ({
  apiFetch: vi.fn(),
}));

describe("AuthCallbackPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useAuth).mockReturnValue({
      user: null,
      token: null,
      login,
      logout: vi.fn(),
      refresh: vi.fn().mockResolvedValue(undefined),
      isAuthenticated: false,
      loading: false,
      hasModuleAccess: vi.fn(() => false),
      hasPermission: vi.fn(() => false),
    });
    vi.mocked(apiFetch).mockResolvedValue({
      access_token: "access-token-from-cookie-refresh",
      refresh_token: "rotated-refresh-token",
    });
    window.history.replaceState({}, "", "/auth/callback");
  });

  it("obtiene la sesión desde cookies sin leer credenciales de la URL", async () => {
    window.history.replaceState({}, "", "/auth/callback?token=legacy-token");

    render(<AuthCallbackPage />);

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith("/v3/auth/refresh", {
        method: "POST",
        silent: true,
      });
    });
    await waitFor(() => {
      expect(login).toHaveBeenCalledWith("access-token-from-cookie-refresh", "rotated-refresh-token");
      expect(push).toHaveBeenCalledWith("/plataforma/messages");
      expect(screen.getByText("Autenticación exitosa. Redirigiendo...")).toBeInTheDocument();
    });
  });
});
