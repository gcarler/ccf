import { beforeEach, describe, expect, it, vi } from 'vitest';

const { apiFetchMock } = vi.hoisted(() => ({ apiFetchMock: vi.fn() }));
vi.mock('@/lib/http', () => ({ apiFetch: apiFetchMock }));

import {
  getAllAssignedProjectTasks,
  getAllProjectSummaries,
  getAllProjects,
  summarizeProjectPortfolioPage,
  type PortfolioSummaryAggregation,
} from './api';
import type { ProjectSummaryPageResponse, ProjectSummaryRecord } from '@/types/projects';

describe('getAllProjects', () => {
  beforeEach(() => apiFetchMock.mockReset());

  it('loads all pages in order and preserves cache policy', async () => {
    apiFetchMock
      .mockResolvedValueOnce({ items: [{ id: 'p1' }], total: 2, skip: 0, limit: 100 })
      .mockResolvedValueOnce({ items: [{ id: 'p2' }], total: 2, skip: 1, limit: 100 });

    await expect(getAllProjects('token', { cache: 'no-store' })).resolves.toEqual([
      { id: 'p1' },
      { id: 'p2' },
    ]);
    expect(apiFetchMock).toHaveBeenNthCalledWith(1, '/projects/page', {
      token: 'token',
      cache: 'no-store',
      query: { offset: 0, limit: 100 },
    });
    expect(apiFetchMock).toHaveBeenNthCalledWith(2, '/projects/page', {
      token: 'token',
      cache: 'no-store',
      query: { offset: 1, limit: 100 },
    });
  });

  it('returns an empty result for an empty collection', async () => {
    apiFetchMock.mockResolvedValueOnce({ items: [], total: 0, skip: 0, limit: 100 });
    await expect(getAllProjects('token')).resolves.toEqual([]);
  });

  it('rejects an incomplete page instead of silently truncating results', async () => {
    apiFetchMock.mockResolvedValueOnce({ items: [], total: 3, skip: 0, limit: 100 });
    await expect(getAllProjects('token')).rejects.toThrow('Invalid or incomplete projects page response');
  });

  it('reuses the SSR summary page and requests only the remaining collection pages', async () => {
    const firstPageItems = Array.from({ length: 100 }, (_, index) => ({
      id: `p${index + 1}`,
      title: `Project ${index + 1}`,
    })) as ProjectSummaryPageResponse['items'];
    apiFetchMock.mockResolvedValueOnce({
      items: [{ id: 'p101', title: 'Project 101' }],
      total: 101,
      skip: 100,
      limit: 100,
    });

    const projects = await getAllProjectSummaries('token', {
      initialPage: { items: firstPageItems, total: 101, skip: 0, limit: 100 },
    });

    expect(projects).toHaveLength(101);
    expect(projects.at(-1)?.id).toBe('p101');
    expect(apiFetchMock).toHaveBeenCalledTimes(1);
    expect(apiFetchMock).toHaveBeenCalledWith('/projects/summary-page', {
      token: 'token',
      cache: undefined,
      signal: undefined,
      query: { offset: 100, limit: 100 },
    });
  });

  it('rejects summary pages if the total changes mid-pagination', async () => {
    apiFetchMock
      .mockResolvedValueOnce({ items: [{ id: 'p1' }], total: 2, skip: 0, limit: 100 })
      .mockResolvedValueOnce({ items: [{ id: 'p2' }], total: 3, skip: 1, limit: 100 });

    await expect(getAllProjectSummaries('token')).rejects.toThrow(
      'Invalid or incomplete project summaries page response',
    );
  });

  it('loads all assigned-task pages through the bounded endpoint', async () => {
    apiFetchMock
      .mockResolvedValueOnce({ items: [{ id: 't1' }], total: 2, skip: 0, limit: 100 })
      .mockResolvedValueOnce({ items: [{ id: 't2' }], total: 2, skip: 1, limit: 100 });

    await expect(getAllAssignedProjectTasks('token', { cache: 'no-store' })).resolves.toEqual([
      { id: 't1' },
      { id: 't2' },
    ]);
    expect(apiFetchMock).toHaveBeenNthCalledWith(1, '/projects/tasks/page', {
      token: 'token',
      cache: 'no-store',
      query: { offset: 0, limit: 100 },
    });
  });

  it('rejects pages whose server offset does not match the requested page', async () => {
    apiFetchMock.mockResolvedValueOnce({ items: [{ id: 't1' }], total: 1, skip: 10, limit: 100 });
    await expect(getAllAssignedProjectTasks('token')).rejects.toThrow(
      'Invalid or incomplete project tasks page response',
    );
  });
});

describe('summarizeProjectPortfolioPage — agregador PMI §6', () => {
  const baseSummary: Omit<ProjectSummaryRecord, 'task_count' | 'completed_task_count' | 'in_progress_task_count' | 'progress_percent' | 'health_status'> = {
    id: 'p1',
    title: 'Proyecto Alpha',
    status: 'active',
    created_at: '2026-01-01T00:00:00Z',
  };

  it('devuelve todos los agregados en cero para un arreglo vacío', () => {
    expect(summarizeProjectPortfolioPage([])).toEqual<PortfolioSummaryAggregation>({
      totalProjects: 0,
      activeCount: 0,
      completedCount: 0,
      onHoldCount: 0,
      delayedCount: 0,
      avgProgress: 0,
      totalTasks: 0,
      completedTasks: 0,
    });
  });

  it('agrega lote mixto: conteos por estado, progreso promedio y sumas de tareas', () => {
    const summaries = [
      { ...baseSummary, id: 'a', status: 'active', progress_percent: 40, task_count: 10, completed_task_count: 4, in_progress_task_count: 3, health_status: 'on_track' },
      { ...baseSummary, id: 'b', status: 'active', progress_percent: 60, task_count: 4, completed_task_count: 3, in_progress_task_count: 1, health_status: 'on_track' },
      { ...baseSummary, id: 'c', status: 'completed', progress_percent: 100, task_count: 6, completed_task_count: 6, in_progress_task_count: 0, health_status: 'completed' },
      { ...baseSummary, id: 'd', status: 'on_hold', progress_percent: 20, task_count: 5, completed_task_count: 1, in_progress_task_count: 0, health_status: 'at_risk' },
      { ...baseSummary, id: 'e', status: 'delayed', progress_percent: 130, task_count: 2, completed_task_count: 0, in_progress_task_count: 1, health_status: 'off_track' },
    ] as ProjectSummaryRecord[];

    expect(summarizeProjectPortfolioPage(summaries)).toEqual({
      totalProjects: 5,
      activeCount: 2,
      completedCount: 1,
      onHoldCount: 1,
      delayedCount: 1,
      // clamp del 130% a 100 → (40+60+100+20+100)/5 = 64%
      avgProgress: 64,
      totalTasks: 27,
      completedTasks: 14,
    });
  });

  it('es resiliente con progress/contadores nullish (wire format progress_pct)', () => {
    const flexible = baseSummary as unknown;
    const summaries = [
      { ...(flexible as object), id: 'n1', status: 'active' } as ProjectSummaryRecord,
      { ...(flexible as object), id: 'n2', status: 'active', progress_percent: 80, task_count: null as unknown as number, completed_task_count: null as unknown as number, in_progress_task_count: 0, health_status: 'on_track' } as ProjectSummaryRecord,
    ];

    expect(summarizeProjectPortfolioPage(summaries)).toEqual({
      totalProjects: 2,
      activeCount: 2,
      completedCount: 0,
      onHoldCount: 0,
      delayedCount: 0,
      // progress ausente → 0 y 80 promediado
      avgProgress: 40,
      totalTasks: 0,
      completedTasks: 0,
    });
  });
});
