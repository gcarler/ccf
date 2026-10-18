export const PROJECTS_LIST_ANCHOR = 'projects-dashboard';
export const PROJECTS_LIST_ROUTE = '/plataforma/projects?view=list#projects-dashboard';

export function getProjectMetricHref(label: string): string {
    const normalized = label.toLowerCase();

    if (
        normalized.includes('riesgo') ||
        normalized.includes('risk') ||
        normalized.includes('crític') ||
        normalized.includes('critic')
    ) {
        return '/plataforma/projects?view=table';
    }

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

export function getProjectGovernanceHref(
    projectId: string,
    section: 'indicators' | 'wbs' | 'board' | 'gantt' = 'indicators',
): string {
    const encodedId = encodeURIComponent(projectId);
    if (section === 'indicators') {
        return `/plataforma/projects/${encodedId}/indicators`;
    }
    if (section === 'wbs') {
        return `/plataforma/projects/${encodedId}?view=list`;
    }
    return `/plataforma/projects/${encodedId}?view=${section}`;
}

