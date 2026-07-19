/**
 * Constantes compartidas del módulo CourseCatalog (ACAD-TKT-043 refactor).
 * Antes vivían inline en ``CourseCatalog.tsx``.
 */
import type { AccessLevel } from "./types";

export const ACCESS_LABEL: Record<AccessLevel, string> = {
    open: "Abierto",
    persona: "Congregantes",
    advanced: "Formadores",
};

export const ACCESS_COLOR: Record<AccessLevel, string> = {
    open: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    persona: "bg-blue-500/10 text-[hsl(var(--primary))] border-blue-500/20",
    advanced: "bg-amber-500/10 text-amber-400 border-amber-500/20",
};

export const COURSE_CATALOG_AVAILABLE_VIEWS = [
    "grid",
    "list",
    "table",
    "board",
    "kanban",
    "calendar",
    "gantt",
    "wiki",
] as const;
