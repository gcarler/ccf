import { describe, it, expect, vi } from "vitest";

import {
  canAccessWorkspaceHref,
  filterWorkspaceSectionsByAccess,
} from "./workspaceAccess";

type AccessMock = {
  hasPermission: ReturnType<typeof vi.fn> & ((p: string) => boolean);
  hasModuleAccess: ReturnType<typeof vi.fn> & ((m: string, l?: string) => boolean);
};

function ctx({
  perm,
  mod,
}: {
  perm?: (p: string) => boolean;
  mod?: (m: string, level?: string) => boolean;
} = {}): AccessMock {
  return {
    hasPermission: vi.fn(perm ?? ((_p: string): boolean => true)) as AccessMock["hasPermission"],
    hasModuleAccess: vi.fn(mod ?? ((_m: string): boolean => true)) as AccessMock["hasModuleAccess"],
  };
}

describe("workspaceAccess — canAccessWorkspaceHref (rutas fuera de plataforma)", () => {
  it("permite rutas no-/plataforma", () => {
    const access = ctx();
    expect(canAccessWorkspaceHref("/", access)).toBe(true);
    expect(canAccessWorkspaceHref("/login", access)).toBe(true);
    expect(canAccessWorkspaceHref("/predicas", access)).toBe(true);
    expect(access.hasPermission).not.toHaveBeenCalled();
    expect(access.hasModuleAccess).not.toHaveBeenCalled();
  });
  it("permite /plataforma/* cuando access правилo authenticated", () => {
    const access = ctx();
    expect(canAccessWorkspaceHref("/plataforma", access)).toBe(true);
    expect(canAccessWorkspaceHref("/plataforma/account", access)).toBe(true);
    expect(canAccessWorkspaceHref("/plataforma/account/perfil", access)).toBe(true);
    expect(access.hasPermission).not.toHaveBeenCalled();
    expect(access.hasModuleAccess).not.toHaveBeenCalled();
  });
  it("ruta /plataforma no listada → permite (authenticated default)", () => {
    const access = ctx();
    expect(canAccessWorkspaceHref("/plataforma/raruta", access)).toBe(true);
  });
});

describe("workspaceAccess — normalizeHref", () => {
  it("trim, elimina # y ?, respeta vacío", () => {
    const access = ctx({ perm: () => false, mod: () => false });
    expect(canAccessWorkspaceHref(" /plataforma/admin ", access)).toBe(false);
    expect(canAccessWorkspaceHref("/plataforma/admin#tab-2", access)).toBe(false);
    expect(canAccessWorkspaceHref("/plataforma/admin?foo=1", access)).toBe(false);
    expect(canAccessWorkspaceHref("/plataforma/admin?foo=1#tab", access)).toBe(false);
    expect(canAccessWorkspaceHref("", access)).toBe(true);
    expect(canAccessWorkspaceHref("   ", access)).toBe(true);
  });
});

describe("workspaceAccess — rule kind = permission", () => {
  it("admin con permiso → true", () => {
    const access = ctx({ perm: (p: string) => p === "system:config" });
    expect(canAccessWorkspaceHref("/plataforma/admin", access)).toBe(true);
    expect(access.hasPermission).toHaveBeenCalledWith("system:config");
    expect(access.hasModuleAccess).not.toHaveBeenCalled();
  });
  it("admin sin permiso → false", () => {
    const access = ctx({ perm: () => false });
    expect(canAccessWorkspaceHref("/plataforma/admin", access)).toBe(false);
  });
});

describe("workspaceAccess — rule kind = module", () => {
  const MOD_CASES = [
    ["/plataforma/academy", "academy"],
    ["/plataforma/crm", "crm"],
    ["/plataforma/evangelism", "evangelism"],
    ["/plataforma/community", "community"],
    ["/plataforma/groups", "community"],
    ["/plataforma/finances", "finance"],
    ["/plataforma/contabilidad", "finance"],
    ["/plataforma/facturacion", "finance"],
    ["/plataforma/gastos", "finance"],
    ["/plataforma/cms", "cms"],
    ["/plataforma/wiki", "cms"],
    ["/plataforma/spiritual-life", "spiritual_life"],
    ["/plataforma/calendar", "spiritual_life"],
    ["/plataforma/agenda", "spiritual_life"],
    ["/plataforma/inbox", "messaging"],
    ["/plataforma/messages", "messaging"],
    ["/plataforma/projects", "projects"],
    ["/plataforma/tasks", "projects"],
  ] as const;

  it.each(MOD_CASES)("con acceso al módulo → true (%s → %s)", (href, mod) => {
    const access = ctx({ mod: (m: string) => m === mod });
    expect(canAccessWorkspaceHref(href, access)).toBe(true);
    expect(access.hasModuleAccess).toHaveBeenCalledWith(mod, "read");
  });

  it.each(MOD_CASES)("sin acceso al módulo → false (%s → %s)", (href, _mod) => {
    const access = ctx({ mod: () => false });
    expect(canAccessWorkspaceHref(href, access)).toBe(false);
  });

  it("subrutas aplican misma regla (prefix match)", () => {
    const access = ctx({ mod: (m: string) => m === "crm" });
    expect(canAccessWorkspaceHref("/plataforma/crm/contacts", access)).toBe(true);
    expect(canAccessWorkspaceHref("/plataforma/crm-duplicate", access)).toBe(true);
    expect(canAccessWorkspaceHref("/plataforma/crms", access)).toBe(true);
  });

  it("minLevel personalizado se pasa (defensivo)", () => {
    const access = ctx({ mod: () => true });
    canAccessWorkspaceHref("/plataforma/academy", access);
    expect(access.hasModuleAccess).toHaveBeenCalledWith("academy", "read");
  });
});

describe("workspaceAccess — prefijos overlapped (más específico primero)", () => {
  it("/plataforma/admin hereda permiso, no el module admin", () => {
    const access = ctx({ perm: () => true, mod: () => false });
    expect(canAccessWorkspaceHref("/plataforma/admin", access)).toBe(true);
  });
  it("/plataforma/account va a authenticated, no permiso", () => {
    const access = ctx({ perm: () => false, mod: () => false });
    expect(canAccessWorkspaceHref("/plataforma/account", access)).toBe(true);
  });
});

describe("workspaceAccess — filterWorkspaceSectionsByAccess", () => {
  const access = ctx({ perm: () => true, mod: (m: string) => m !== "crm" });

  it("filtra items no-accesibles de cada sección", () => {
    const sections = [
      {
        id: "s1",
        items: [
          { label: "Home", href: "/" },
          { label: "CRM", href: "/plataforma/crm" },
          { label: "Academy", href: "/plataforma/academy" },
          { label: "Account", href: "/plataforma/account" },
        ],
      },
    ];
    const out = filterWorkspaceSectionsByAccess(sections, access)!;
    expect(out[0].items?.map((i) => i.label)).toEqual(["Home", "Academy", "Account"]);
  });

  it("elimina secciones que quedan vacías", () => {
    const sections = [
      {
        id: "s1",
        items: [{ label: "CRM", href: "/plataforma/crm" }],
      },
      { id: "s2", items: [{ label: "Home", href: "/" }] },
      { id: "s3", items: [{ label: "Academy", href: "/plataforma/academy" }] },
    ];
    const out = filterWorkspaceSectionsByAccess(sections, access)!;
    expect(out.map((s) => s.id)).toEqual(["s2", "s3"]);
  });

  it("pasa undefined → undefined (noop)", () => {
    expect(filterWorkspaceSectionsByAccess(undefined, access)).toBeUndefined();
  });

  it("sección sin items → passed through (sin filtrar)", () => {
    const sections = [{ id: "s1" }] as Array<{ id: string; items?: { href?: string }[] }>;
    const out = filterWorkspaceSectionsByAccess(sections, access)!;
    expect(out).toEqual([{ id: "s1" }]);
  });

  it("items undefined → sección si items es undefined", () => {
    const sections = [{ id: "s1", items: undefined }] as Array<{
      id: string;
      items?: { href?: string }[];
    }>;
    const out = filterWorkspaceSectionsByAccess(sections, access)!;
    expect(out.map((s) => s.id)).toEqual(["s1"]);
  });
});
