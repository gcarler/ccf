/**
 * Re-export formatDate from the shared format module for backward compatibility.
 * Existing importers use `es-PE` locale, which is preserved via the options
 * parameter at the call site in ProjectsTableView.tsx.
 */
export { formatDate } from "@/lib/format";

export function normalizeSearchText(text: string): string {
    return text
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .toLowerCase()
        .trim();
}

/**
 * Priorización de candidatos para menciones con @:
 * - Filtra: requiere que TODOS los tokens de la búsqueda estén presentes en el nombre.
 * - Tier 0: primer nombre o nombre completo inicia con el término/primer token (ej: @l -> Lady, Laura, Luis).
 * - Tier 1: apellido o palabra secundaria inicia con el término/primer token (ej: @l -> Ana López, Juan Luis).
 * - Tier 2: coincidencia parcial (ej: @l -> Mila Ferrer).
 * Dentro de cada tier se conserva el orden alfabético.
 */
export function sortMentionCandidates<T extends { name: string }>(candidates: T[], queryRaw: string): T[] {
    const term = normalizeSearchText(queryRaw);
    if (!term) return candidates;
    const tokens = term.split(/\s+/).filter(Boolean);
    if (tokens.length === 0) return candidates;

    const filtered = candidates.filter((c) => {
        const norm = normalizeSearchText(c.name);
        return tokens.every((tok) => norm.includes(tok));
    });

    const rank = (c: T) => {
        const full = normalizeSearchText(c.name);
        if (full.startsWith(term) || (tokens.length > 0 && full.startsWith(tokens[0]))) return 0;
        const words = full.split(/\s+/);
        if (words.some((w, idx) => idx > 0 && w.startsWith(tokens[0]))) return 1;
        return 2;
    };

    return filtered.sort((a, b) => {
        const ra = rank(a);
        const rb = rank(b);
        if (ra !== rb) return ra - rb;
        return a.name.localeCompare(b.name, "es", { sensitivity: "base" });
    });
}