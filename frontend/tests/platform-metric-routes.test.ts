import { describe, expect, it } from 'vitest';

import { getPlatformMetricHref, getPlatformTaskHref } from '@/app/plataforma/metricRoutes';
import { PROJECTS_LIST_ROUTE } from '@/app/plataforma/projects/projectsLinks';

describe('platform metric routes', () => {
    it('routes platform metrics to their concrete destinations', () => {
        expect(getPlatformMetricHref('Personas')).toBe('/plataforma/crm/personas');
        expect(getPlatformMetricHref('Proyectos')).toBe(PROJECTS_LIST_ROUTE);
        expect(getPlatformMetricHref('8 proyectos')).toBe(PROJECTS_LIST_ROUTE);
        expect(getPlatformMetricHref('Pendientes')).toBe('/plataforma/tasks');
        expect(getPlatformMetricHref('Testimonios')).toBe('/plataforma/admin/testimonials');
        expect(getPlatformMetricHref('4 activos')).toBeNull();
    });

    it('builds task detail routes from task ids', () => {
        expect(getPlatformTaskHref('123')).toBe('/plataforma/tasks/123');
        expect(getPlatformTaskHref('task-abc')).toBe('/plataforma/tasks/task-abc');
    });
});
