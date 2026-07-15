import { describe, expect, it } from 'vitest';

import { PROJECTS_LIST_ROUTE, getProjectMetricHref } from '@/app/plataforma/projects/projectsLinks';

describe('project metric links', () => {
    it('uses the projects list anchor route as canonical destination', () => {
        expect(PROJECTS_LIST_ROUTE).toBe('/plataforma/projects?view=list#projects-list');
    });

    it('sends project metrics to the projects list route', () => {
        expect(getProjectMetricHref('8 proyectos')).toBe(PROJECTS_LIST_ROUTE);
        expect(getProjectMetricHref('Proyectos Activos')).toBe(PROJECTS_LIST_ROUTE);
    });

    it('keeps task and activity cards on their own destinations', () => {
        expect(getProjectMetricHref('Tareas Pendientes')).toBe('/plataforma/projects/tasks?view=list&scope=all');
        expect(getProjectMetricHref('Tareas Vencidas')).toBe('/plataforma/projects/tasks?status=overdue&scope=all&view=list');
        expect(getProjectMetricHref('Actividad Reciente')).toBe('/plataforma/projects/general?view=list');
    });
});
