export type CmsRole = "admin" | "coordinador" | "docente" | "pastor" | "estudiante" | "aspirante" | string;

function normalize(role: string | null | undefined): CmsRole {
  return String(role || "").toLowerCase().trim();
}

export function canEditCms(role: string | null | undefined): boolean {
  return ["admin", "coordinador", "docente", "pastor"].includes(normalize(role));
}

export function canPublishCms(role: string | null | undefined): boolean {
  return ["admin", "coordinador", "pastor"].includes(normalize(role));
}

export function canManageSites(role: string | null | undefined): boolean {
  return ["admin", "coordinador", "pastor"].includes(normalize(role));
}
