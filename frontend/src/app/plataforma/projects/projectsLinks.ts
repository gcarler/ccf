export const PROJECTS_LIST_ANCHOR = 'projects-list';

export function getProjectMetricHref(label: string): string {
    const normalized = label.toLowerCase();

    if (normalized.includes('proyecto') || normalized.includes('project')) {
        return `/plataforma/projects?view=list#${PROJECTS_LIST_ANCHOR}`;
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

    return '/plataforma/projects?view=list';
}
