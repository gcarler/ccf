import { renderHook, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import * as http from "@/lib/http";
import { SITE_NAME } from "@/lib/site-config";
import { useSiteBranding } from "./site-branding";

vi.mock("@/components/public/PublicBootstrapProvider", () => ({
  usePublicBootstrap: vi.fn(),
}));

import { usePublicBootstrap } from "@/components/public/PublicBootstrapProvider";

const useBootstrapMock = vi.mocked(usePublicBootstrap);
const apiFetchSpy = vi.spyOn(http, "apiFetch");

beforeEach(() => {
  vi.clearAllMocks();
  apiFetchSpy.mockReset();
  useBootstrapMock.mockReturnValue({ theme: null } as never);
});

afterEach(() => {
  vi.clearAllMocks();
});

const render = () => renderHook(() => useSiteBranding());

describe("site-branding — valores por defecto (sin bootstrap)", () => {
  it("fallback SITE_NAME + logoUrl vacío cuando bootstrap.theme null", () => {
    useBootstrapMock.mockReturnValue({ theme: null } as never);
    const { result } = render();
    expect(result.current.logoUrl).toBe("");
    expect(result.current.logoName).toBe(SITE_NAME);
  });
  it("sin await sleep: efecto corre apiFetch (silent=true) a /cms/v2/public/sites/ccf/theme", () => {
    apiFetchSpy.mockResolvedValueOnce({ tokens_json: {} });
    render();
    expect(apiFetchSpy).toHaveBeenCalledWith(
      `/cms/v2/public/sites/ccf/theme`,
      { silent: true },
    );
  });
});

describe("site-branding — bootstrap theme presentes", () => {
  it("usa tokens_json de bootstrap si ya tengo --site-logo-url y --site-logo-name", () => {
    useBootstrapMock.mockReturnValue({
      theme: {
        tokens_json: {
          "--site-logo-url": "/imgs/logo.png",
          "--site-logo-name": "Comunidad Demo",
        },
      },
    } as never);
    apiFetchSpy.mockResolvedValueOnce({ tokens_json: {} });
    const { result } = render();
    expect(result.current.logoUrl).toBe("/imgs/logo.png");
    expect(result.current.logoName).toBe("Comunidad Demo");
  });
  it("falta --site-logo-name → fallback SITE_NAME", () => {
    useBootstrapMock.mockReturnValue({
      theme: { tokens_json: { "--site-logo-url": "/x.png" } },
    } as never);
    const { result } = render();
    expect(result.current.logoUrl).toBe("/x.png");
    expect(result.current.logoName).toBe(SITE_NAME);
  });
  it("falta --site-logo-url → fallback string vacío", () => {
    useBootstrapMock.mockReturnValue({
      theme: { tokens_json: { "--site-logo-name": "Brand" } },
    } as never);
    const { result } = render();
    expect(result.current.logoUrl).toBe("");
    expect(result.current.logoName).toBe("Brand");
  });
  it("fallback explícito al usar hook con fallback argument", () => {
    useBootstrapMock.mockReturnValue({
      theme: { tokens_json: {} },
    } as never);
    apiFetchSpy.mockResolvedValueOnce({ tokens_json: {} });
    const { result } = renderHook(() =>
      useSiteBranding({ logoUrl: "/fallback.png", logoName: "FallbackName" }),
    );
    expect(result.current.logoUrl).toBe("/fallback.png");
    expect(result.current.logoName).toBe("FallbackName");
  });
  it("cuando bootstrap tiene tokens, NO llama a apiFetch", () => {
    useBootstrapMock.mockReturnValue({
      theme: { tokens_json: { "--site-logo-url": "/x.png" } },
    } as never);
    render();
    expect(apiFetchSpy).not.toHaveBeenCalled();
  });
});

describe("site-branding — apiFetch trayendo tokens (efecto)", () => {
  it("tras apiFetch resolve con tokens, branding se actualiza", async () => {
    useBootstrapMock.mockReturnValue({ theme: null } as never);
    apiFetchSpy.mockResolvedValueOnce({
      tokens_json: {
        "--site-logo-url": "/api-logo.png",
        "--site-logo-name": "ApiBrand",
      },
    });
    const { result } = render();
    expect(result.current.logoUrl).toBe("");
    await waitFor(() => {
      expect(result.current.logoUrl).toBe("/api-logo.png");
      expect(result.current.logoName).toBe("ApiBrand");
    });
  });
  it("tokens_json vacío del API → cae a fallback/SITE_NAME", async () => {
    useBootstrapMock.mockReturnValue({ theme: null } as never);
    apiFetchSpy.mockResolvedValueOnce({ tokens_json: {} });
    const { result } = renderHook(() =>
      useSiteBranding({ logoUrl: "/fb.png", logoName: "FB" }),
    );
    await waitFor(() => {
      expect(result.current.logoUrl).toBe("/fb.png");
      expect(result.current.logoName).toBe("FB");
    });
  });
  it("apiFetch falla (reject) → cae a fallback/SITE_NAME", async () => {
    useBootstrapMock.mockReturnValue({ theme: null } as never);
    apiFetchSpy.mockRejectedValueOnce(new Error("net"));
    const { result } = render();
    await waitFor(() => {
      expect(result.current.logoUrl).toBe("");
      expect(result.current.logoName).toBe(SITE_NAME);
    });
  });
  it("apiFetch devuelve null/undefined → cae a fallback/SITE_NAME", async () => {
    useBootstrapMock.mockReturnValue({ theme: null } as never);
    apiFetchSpy.mockResolvedValueOnce(null as never);
    const { result } = render();
    await waitFor(() => {
      expect(result.current.logoUrl).toBe("");
      expect(result.current.logoName).toBe(SITE_NAME);
    });
  });
});
