import { describe, expect, it } from 'vitest';

import { getPlatformMetricHref } from '@/app/plataforma/metricRoutes';

describe('platform metric routes', () => {
    it('routes project metrics to the explicit projects list', () => {
        expect(getPlatformMetricHref('Proyectos')).toBe('/plataforma/projects/list');
        expect(getPlatformMetricHref('8 proyectos')).toBe('/plataforma/projects/list');
        expect(getPlatformMetricHref('4 activos')).toBeNull();
    });
});
