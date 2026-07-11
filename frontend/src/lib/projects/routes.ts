// Sub-rutas globales bajo /plataforma/projects que NO son un UUID de proyecto.
// Mantener sincronizado con `frontend/src/app/plataforma/projects/*/page.tsx`.
//
// Se usa en `ProjectsLayoutClient` para distinguir el slug de una sub-ruta
// (ej. 'tasks', 'inbox') del UUID real de un proyecto cuando se decide
// si el layout debe cargar el detalle de un proyecto o la lista global.
export const GLOBAL_PROJECT_ROUTES: ReadonlySet<string> = new Set([
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
