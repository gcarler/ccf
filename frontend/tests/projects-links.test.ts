import { describe, expect, it } from 'vitest';

import { PROJECTS_LIST_ANCHOR, getProjectMetricHref } from '@/app/plataforma/projects/projectsLinks';

describe('project metric links', () => {
    it('sends project metrics to the projects list anchor', () => {
        expect(getProjectMetricHref('8 proyectos')).toBe(`/plataforma/projects?view=list#${PROJECTS_LIST_ANCHOR}`);
        expect(getProjectMetricHref('Proyectos Activos')).toBe(`/plataforma/projects?view=list#${PROJECTS_LIST_ANCHOR}`);
    });

    it('keeps task and activity cards on their own destinations', () => {
        expect(getProjectMetricHref('Tareas Pendientes')).toBe('/plataforma/projects/tasks?view=list&scope=all');
        expect(getProjectMetricHref('Tareas Vencidas')).toBe('/plataforma/projects/tasks?status=overdue&scope=all&view=list');
        expect(getProjectMetricHref('Actividad Reciente')).toBe('/plataforma/projects/general?view=list');
    });
});
