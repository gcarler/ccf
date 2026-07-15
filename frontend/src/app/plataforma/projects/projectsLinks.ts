export const PROJECTS_LIST_ANCHOR = 'projects-list';
export const PROJECTS_LIST_ROUTE = '/plataforma/projects/list';

export function getProjectMetricHref(label: string): string {
    const normalized = label.toLowerCase();

    if (normalized.includes('proyecto') || normalized.includes('project')) {
        return PROJECTS_LIST_ROUTE;
    }

    if (normalized.includes('atrasad') || normalized.includes('vencid') || normalized.includes('delayed')) {
        return '/plataforma/projects/tasks?status=overdue&scope=all&view=list';
    }

    if (normalized.includes('tarea')) {
        return '/plataforma/projects/tasks?view=list&scope=all';
    }

    if (normalized.includes('actividad') || normalized.includes('activity')) {
        return '/plataforma/projects/general?view=list';
    }

    return PROJECTS_LIST_ROUTE;
}
