import { beforeEach, describe, expect, it, vi } from 'vitest';

const { apiFetchMock } = vi.hoisted(() => ({ apiFetchMock: vi.fn() }));
vi.mock('@/lib/http', () => ({ apiFetch: apiFetchMock }));

import { getAllAssignedProjectTasks, getAllProjectSummaries, getAllProjects } from './api';
import type { ProjectSummaryPageResponse } from '@/types/projects';

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
