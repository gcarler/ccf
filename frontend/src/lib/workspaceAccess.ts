"use client";

type ModuleLevel = "read" | "edit" | "manage" | "study";

type AccessRule =
  | { prefix: string; kind: "module"; module: string; minLevel?: ModuleLevel }
  | { prefix: string; kind: "permission"; permission: string }
  | { prefix: string; kind: "authenticated" };

type AccessContext = {
  hasModuleAccess: (module: string, minLevel?: string) => boolean;
  hasPermission: (permission: string) => boolean;
};

const WORKSPACE_ACCESS_RULES: AccessRule[] = [
  { prefix: "/plataforma/admin", kind: "permission", permission: "system:config" },
  { prefix: "/plataforma/academy", kind: "module", module: "academy", minLevel: "read" },
  { prefix: "/plataforma/crm", kind: "module", module: "crm", minLevel: "read" },
  { prefix: "/plataforma/evangelism", kind: "module", module: "evangelism", minLevel: "read" },
  { prefix: "/plataforma/community", kind: "module", module: "community", minLevel: "read" },
  { prefix: "/plataforma/groups", kind: "module", module: "community", minLevel: "read" },
  { prefix: "/plataforma/finances", kind: "module", module: "finance", minLevel: "read" },
  { prefix: "/plataforma/contabilidad", kind: "module", module: "finance", minLevel: "read" },
  { prefix: "/plataforma/facturacion", kind: "module", module: "finance", minLevel: "read" },
  { prefix: "/plataforma/gastos", kind: "module", module: "finance", minLevel: "read" },
  { prefix: "/plataforma/cms", kind: "module", module: "cms", minLevel: "read" },
  { prefix: "/plataforma/wiki", kind: "module", module: "cms", minLevel: "read" },
  { prefix: "/plataforma/spiritual-life", kind: "module", module: "spiritual_life", minLevel: "read" },
  { prefix: "/plataforma/calendar", kind: "module", module: "spiritual_life", minLevel: "read" },
  { prefix: "/plataforma/agenda", kind: "module", module: "spiritual_life", minLevel: "read" },
  { prefix: "/plataforma/inbox", kind: "module", module: "messaging", minLevel: "read" },
  { prefix: "/plataforma/messages", kind: "module", module: "messaging", minLevel: "read" },
  { prefix: "/plataforma/projects", kind: "module", module: "projects", minLevel: "read" },
  { prefix: "/plataforma/tasks", kind: "module", module: "projects", minLevel: "read" },
  { prefix: "/plataforma/support", kind: "authenticated" },
  { prefix: "/plataforma/account", kind: "authenticated" },
  { prefix: "/plataforma/settings", kind: "authenticated" },
  { prefix: "/plataforma/theme", kind: "authenticated" },
  { prefix: "/plataforma/graph", kind: "authenticated" },
  { prefix: "/plataforma/documentos", kind: "authenticated" },
  { prefix: "/plataforma", kind: "authenticated" },
];

function normalizeWorkspaceHref(href: string): string {
  const trimmed = String(href || "").trim();
  if (!trimmed) return "";
  return trimmed.split("#", 1)[0].split("?", 1)[0] || "";
}

function pathMatchesPrefix(path: string, prefix: string): boolean {
  return path === prefix || path.startsWith(`${prefix}/`);
}

export function canAccessWorkspaceHref(href: string, access: AccessContext): boolean {
  const path = normalizeWorkspaceHref(href);
  if (!path.startsWith("/plataforma")) return true;

  const rule = WORKSPACE_ACCESS_RULES.find((candidate) => pathMatchesPrefix(path, candidate.prefix));
  if (!rule) return true;

  if (rule.kind === "authenticated") return true;
  if (rule.kind === "permission") return access.hasPermission(rule.permission);
  return access.hasModuleAccess(rule.module, rule.minLevel ?? "read");
}

export function filterWorkspaceSectionsByAccess<T extends { items?: Array<{ href?: string }> }>(
  sections: T[] | undefined,
  access: AccessContext,
): T[] | undefined {
  if (!Array.isArray(sections)) return sections;
  return sections
    .map((section) => {
      const items = Array.isArray(section.items)
        ? section.items.filter((item) => canAccessWorkspaceHref(String(item?.href || ""), access))
        : section.items;
      return { ...section, items } as T;
    })
    .filter((section) => !Array.isArray(section.items) || section.items.length > 0) as T[];
}
