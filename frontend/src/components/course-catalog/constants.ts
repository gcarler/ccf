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
    open: "bg-[hsl(var(--success))]/10 text-[hsl(var(--success))] border-[hsl(var(--success)/100%)]/20",
    persona: "bg-[hsl(var(--info))]/10 text-[hsl(var(--primary))] border-[hsl(var(--info)/100%)]/20",
    advanced: "bg-[hsl(var(--warning))]/10 text-[hsl(var(--warning))] border-[hsl(var(--warning)/100%)]/20",
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
