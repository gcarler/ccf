// Sub-rutas globales bajo /plataforma/projects que NO son un UUID de proyecto.
// Mantener sincronizado con `frontend/src/app/plataforma/projects/*/page.tsx`.
//
// Se usa en `ProjectsLayoutClient` para distinguir el slug de una sub-ruta
// (ej. 'tasks', 'inbox') del UUID real de un proyecto cuando se decide
// si el layout debe cargar el detalle de un proyecto o la lista global.
export const GLOBAL_PROJECT_ROUTES: ReadonlySet<string> = new Set([
    'list',
    'tasks',
    'inbox',
    'general',
    'comments',
    'team',
    'responses',
    'more',
    'automations',
    'welcome',
]);

/**
 * PMI — guarda de ruteo: true si el segmento pertenece a las sub-rutas
 * globales del portafolio (no es un UUID de proyecto). El segmento se
 * normaliza a minúsculas sin espacios.
 */
export function isGlobalProjectRoute(segment: string | null | undefined): boolean {
    const normalized = (segment ?? '').trim().toLowerCase();
    if (!normalized) return false;
    return GLOBAL_PROJECT_ROUTES.has(normalized);
}

/**
 * PMI — guarda de ruteo: true si el segmento identifica una entidad de
 * proyecto (contenido no vacío y que no es una sub-ruta global).
 */
export function isProjectEntityRoute(segment: string | null | undefined): boolean {
    const normalized = (segment ?? '').trim();
    if (!normalized) return false;
    return !GLOBAL_PROJECT_ROUTES.has(normalized.toLowerCase());
}
