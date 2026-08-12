export type CmsRole = "admin" | "coordinador" | "docente" | "pastor" | "estudiante" | "aspirante" | string;

function normalize(role: string | null | undefined): CmsRole {
  return String(role || "").toLowerCase().trim();
}

// El backend expone los roles del Kernel en español (ADMINISTRADOR, GESTOR,
// EDITOR, LECTOR) y AuthContext los normaliza a lowercase, así que además de
// los roles legacy en inglés se aceptan las formas completas en español.
// Mapeo de política CMS: ADMINISTRADOR/GESTOR editan y publican contenido;
// EDITOR solo edita (no publica ni gestiona sitios); LECTOR queda fuera
// (solo lectura). Gestionar SITES es acción administrativa de plataforma:
// GESTOR publica contenido pero NO gestiona sitios (el backend devuelve 403).
const EDIT_ROLES = ["admin", "administrador", "gestor", "editor", "coordinador", "docente", "pastor"];
const PUBLISH_ROLES = ["admin", "administrador", "gestor", "coordinador", "pastor"];
const SITE_MANAGE_ROLES = ["admin", "administrador", "coordinador", "pastor"];

export function canEditCms(role: string | null | undefined): boolean {
  return EDIT_ROLES.includes(normalize(role));
}

export function canPublishCms(role: string | null | undefined): boolean {
  return PUBLISH_ROLES.includes(normalize(role));
}

export function canManageSites(role: string | null | undefined): boolean {
  return SITE_MANAGE_ROLES.includes(normalize(role));
}
