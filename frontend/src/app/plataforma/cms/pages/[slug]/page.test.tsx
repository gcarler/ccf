import React from "react";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import CmsPageDetailPage from "./page";

const routerMock = vi.hoisted(() => ({
  replace: vi.fn(),
  push: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useParams: () => ({ slug: "inicio" }),
  useRouter: () => routerMock,
}));

const authMock = vi.hoisted(() => ({ token: "test-token" as string | null, user: null }));
vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({ token: authMock.token, user: authMock.user }),
}));

vi.mock("@/lib/site-config", () => ({ SITE_KEY: "ccf" }));

const apiFetchMock = vi.hoisted(() => vi.fn());
vi.mock("@/lib/http", () => ({ apiFetch: apiFetchMock }));

vi.mock("sonner", () => ({ toast: { error: vi.fn(), success: vi.fn() } }));

const pageData = {
  id: "p1",
  slug: "inicio",
  title: "Página de Inicio",
  status: "published",
  site_key: "ccf",
  updated_at: "2026-01-01T00:00:00Z",
  sections_count: 4,
};

describe("CmsPageDetailPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiFetchMock.mockReset();
    authMock.token = "test-token";
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("muestra el skeleton mientras carga", () => {
    apiFetchMock.mockReturnValue(new Promise(() => {}));
    const { container } = render(<CmsPageDetailPage />);
    // El skeleton no tiene texto: son bloques con animate-pulse.
    expect(container.querySelector(".animate-pulse")).not.toBeNull();
    expect(screen.queryByText("Página de Inicio")).toBeNull();
  });

  it("renderiza los datos de la página publicada", async () => {
    apiFetchMock.mockResolvedValueOnce(pageData);
    render(<CmsPageDetailPage />);

    expect(await screen.findByText("Página de Inicio")).toBeInTheDocument();
    expect(screen.getByText("Publicado")).toBeInTheDocument();
    expect(screen.getByText("/inicio")).toBeInTheDocument();
    expect(screen.getByText("ccf")).toBeInTheDocument();
    expect(screen.getByText("4 secciones")).toBeInTheDocument();
    expect(apiFetchMock).toHaveBeenCalledWith("/cms/pages/inicio", { token: "test-token" });
  });

  it("usa un fallback draft si la API falla", async () => {
    apiFetchMock.mockRejectedValueOnce(new Error("boom"));
    render(<CmsPageDetailPage />);
    expect(await screen.findByText("Página")).toBeInTheDocument();
    expect(screen.getByText("Borrador")).toBeInTheDocument();
  });

  it("sin token: no llama a la API ni dispara el countdown", async () => {
    authMock.token = null;
    apiFetchMock.mockResolvedValueOnce(pageData);
    render(<CmsPageDetailPage />);
    await act(async () => { await Promise.resolve(); });
    expect(apiFetchMock).not.toHaveBeenCalled();
    expect(routerMock.replace).not.toHaveBeenCalled();
  });

  it("el botón 'Abrir en el Builder ahora' navega al builder de inmediato", async () => {
    apiFetchMock.mockResolvedValueOnce(pageData);
    render(<CmsPageDetailPage />);
    fireEvent.click(await screen.findByRole("button", { name: /Abrir en el Builder ahora/i }));
    expect(routerMock.replace).toHaveBeenCalledWith("/plataforma/cms/builder?site=ccf&page=inicio");
  });

  it("el botón 'Volver a páginas' navega al listado", async () => {
    apiFetchMock.mockResolvedValueOnce(pageData);
    render(<CmsPageDetailPage />);
    fireEvent.click(await screen.findByRole("button", { name: /Volver a páginas/i }));
    expect(routerMock.push).toHaveBeenCalledWith("/plataforma/cms/pages");
  });

  it("redirige automáticamente al builder al terminar el countdown (3s)", async () => {
    vi.useFakeTimers();
    apiFetchMock.mockResolvedValueOnce(pageData);
    render(<CmsPageDetailPage />);

    await act(async () => { await Promise.resolve(); });
    expect(routerMock.replace).not.toHaveBeenCalled();

    // Avance paso a paso: cada tick de 1s dispara un setCountdown dentro de act.
    for (let i = 0; i < 3; i++) {
      await act(async () => {
        vi.advanceTimersByTime(1000);
        await Promise.resolve();
      });
    }

    expect(routerMock.replace).toHaveBeenCalledWith("/plataforma/cms/builder?site=ccf&page=inicio");
  });

  it("usa site_key y slug del payload (no del fallback) para el builder", async () => {
    vi.useFakeTimers();
    apiFetchMock.mockResolvedValueOnce({ ...pageData, site_key: "faro", slug: "otro" });
    render(<CmsPageDetailPage />);
    await act(async () => { await Promise.resolve(); });
    for (let i = 0; i < 3; i++) {
      await act(async () => {
        vi.advanceTimersByTime(1000);
        await Promise.resolve();
      });
    }
    expect(routerMock.replace).toHaveBeenCalledWith("/plataforma/cms/builder?site=faro&page=otro");
  });
});
