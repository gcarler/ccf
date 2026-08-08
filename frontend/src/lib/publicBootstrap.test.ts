import { describe, it, expect, beforeEach, afterEach } from "vitest";
import {
  readPublicBootstrap,
  readBootstrappedMenu,
  readBootstrappedTheme,
  readBootstrappedFooterPage,
  serializePublicBootstrap,
  type PublicBootstrapState,
} from "./publicBootstrap";
import type { CmsPublicMenu, CmsPublicPage, CmsTheme } from "@/types/cms-v2";

const mockTheme: Pick<CmsTheme, "name" | "tokens_json"> = {
  name: "Demo",
  tokens_json: { "--site-primary": "#000" },
};
const mockMenu: CmsPublicMenu = { id: "m1", label: "Main", items: [] } as unknown as CmsPublicMenu;
const mockPage: CmsPublicPage = { id: "p1", slug: "footer", title: "Footer" } as unknown as CmsPublicPage;

const mockState: PublicBootstrapState = {
  theme: mockTheme,
  menus: { main: mockMenu, secondary: null },
  pages: { home: mockPage, about: null },
  footerPage: mockPage,
};

let origGet: PropertyDescriptor | undefined;

beforeEach(() => {
  origGet = Object.getOwnPropertyDescriptor(window, "__CCF_PUBLIC_BOOTSTRAP__");
});

afterEach(() => {
  if (origGet) {
    Object.defineProperty(window, "__CCF_PUBLIC_BOOTSTRAP__", origGet);
  } else {
    delete (window as { __CCF_PUBLIC_BOOTSTRAP__?: unknown }).__CCF_PUBLIC_BOOTSTRAP__;
  }
});

function setBootstrap(v: unknown) {
  Object.defineProperty(window, "__CCF_PUBLIC_BOOTSTRAP__", {
    configurable: true,
    value: v,
  });
}

describe("publicBootstrap — readPublicBootstrap", () => {
  it("no existe en window → null", () => {
    delete (window as { __CCF_PUBLIC_BOOTSTRAP__?: unknown }).__CCF_PUBLIC_BOOTSTRAP__;
    expect(readPublicBootstrap()).toBeNull();
  });
  it("existe → retorna el estado", () => {
    setBootstrap(mockState);
    expect(readPublicBootstrap()).toBe(mockState);
  });
  it("existe pero es undefined → null (|| null)", () => {
    setBootstrap(undefined);
    expect(readPublicBootstrap()).toBeNull();
  });
});

describe("publicBootstrap — readBootstrappedMenu", () => {
  it("menu existente → CmsPublicMenu", () => {
    setBootstrap(mockState);
    expect(readBootstrappedMenu("main")).toBe(mockMenu);
  });
  it("menu null explícito → null", () => {
    setBootstrap(mockState);
    expect(readBootstrappedMenu("secondary")).toBeNull();
  });
  it("menu inexistente → null", () => {
    setBootstrap(mockState);
    expect(readBootstrappedMenu("no-key")).toBeNull();
  });
  it("sin bootstrap → null", () => {
    delete (window as { __CCF_PUBLIC_BOOTSTRAP__?: unknown }).__CCF_PUBLIC_BOOTSTRAP__;
    expect(readBootstrappedMenu("main")).toBeNull();
  });
});

describe("publicBootstrap — readBootstrappedTheme", () => {
  it("bootstrap tiene theme → retorna", () => {
    setBootstrap(mockState);
    expect(readBootstrappedTheme()).toBe(mockTheme);
  });
  it("bootstrap con theme null → null", () => {
    setBootstrap({ ...mockState, theme: null });
    expect(readBootstrappedTheme()).toBeNull();
  });
  it("sin bootstrap → null", () => {
    delete (window as { __CCF_PUBLIC_BOOTSTRAP__?: unknown }).__CCF_PUBLIC_BOOTSTRAP__;
    expect(readBootstrappedTheme()).toBeNull();
  });
});

describe("publicBootstrap — readBootstrappedFooterPage", () => {
  it("footerPage presente → retorna", () => {
    setBootstrap(mockState);
    expect(readBootstrappedFooterPage()).toBe(mockPage);
  });
  it("footerPage null → null", () => {
    setBootstrap({ ...mockState, footerPage: null });
    expect(readBootstrappedFooterPage()).toBeNull();
  });
  it("sin footerPage undefined → null", () => {
    setBootstrap({ theme: null });
    expect(readBootstrappedFooterPage()).toBeNull();
  });
});

describe("publicBootstrap — serializePublicBootstrap", () => {
  it("serializa JSON válido y escapea < para evitar </script> HTML injection", () => {
    const state: PublicBootstrapState = {
      theme: { name: "T<c", tokens_json: { x: "</script>" } },
    };
    const out = serializePublicBootstrap(state);
    expect(out).not.toContain("<");
    expect(out).toContain("\\u003c");
    // Reparseo debería devolver el original (con escapes resueltos).
    const parsed = JSON.parse(out.replace(/\\u003c/g, "<"));
    expect(parsed.theme.name).toBe("T<c");
    expect(parsed.theme.tokens_json.x).toBe("</script>");
  });
  it("estado vacío → JSON válido", () => {
    expect(JSON.parse(serializePublicBootstrap({} as PublicBootstrapState))).toEqual({});
  });
  it("estado con null/menus → serializa sin lanzar", () => {
    const out = serializePublicBootstrap(mockState);
    expect(typeof out).toBe("string");
    expect(out.startsWith("{")).toBe(true);
  });
});
