import { describe, expect, it } from 'vitest';
import {
  PROJECTS_LIST_ROUTE,
  getProjectGovernanceHref,
  getProjectMetricHref,
} from './projectsLinks';

describe('projectsLinks', () => {
  it('routes project metric labels to canonical platform URLs', () => {
    expect(getProjectMetricHref('Proyectos Activos')).toBe(PROJECTS_LIST_ROUTE);
    expect(getProjectMetricHref('Tareas Atrasadas')).toBe(
      '/plataforma/projects/tasks?status=overdue&scope=all&view=list',
    );
    expect(getProjectMetricHref('Mis Tareas')).toBe(
      '/plataforma/projects/tasks?view=list&scope=all',
    );
    expect(getProjectMetricHref('Actividad Reciente')).toBe(
      '/plataforma/projects/general?view=list',
    );
    expect(getProjectMetricHref('Riesgos Críticos')).toBe(
      '/plataforma/projects?view=table',
    );
    expect(getProjectMetricHref('Otro Indicador')).toBe(PROJECTS_LIST_ROUTE);
  });

  it('builds project governance URLs for indicators, wbs, board, and gantt', () => {
    expect(getProjectGovernanceHref('proj-1')).toBe('/plataforma/projects/proj-1/indicators');
    expect(getProjectGovernanceHref('proj-1', 'wbs')).toBe('/plataforma/projects/proj-1?view=list');
    expect(getProjectGovernanceHref('proj-1', 'board')).toBe('/plataforma/projects/proj-1?view=board');
    expect(getProjectGovernanceHref('proj 2', 'gantt')).toBe('/plataforma/projects/proj%202?view=gantt');
  });
});
