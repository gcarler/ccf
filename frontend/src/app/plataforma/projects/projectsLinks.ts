export const PROJECTS_LIST_ANCHOR = 'projects-list';

export function getProjectMetricHref(label: string): string {
    const normalized = label.toLowerCase();

    if (normalized.includes('proyecto') || normalized.includes('project')) {
        return `/plataforma/projects?view=list#${PROJECTS_LIST_ANCHOR}`;
    }

    if (normalized.includes('tarea')) {
        return '/plataforma/projects/tasks?view=list';
    }

    if (normalized.includes('actividad') || normalized.includes('activity')) {
        return '/plataforma/projects/general?view=list';
    }

    if (normalized.includes('atrasad') || normalized.includes('delayed')) {
        return '/plataforma/projects/tasks?status=overdue&view=list';
    }

    return '/plataforma/projects?view=list';
}
