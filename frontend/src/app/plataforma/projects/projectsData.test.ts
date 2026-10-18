import { beforeEach, describe, expect, it, vi } from 'vitest';

const { cookiesMock, serverApiFetchMock } = vi.hoisted(() => ({
  cookiesMock: vi.fn(),
  serverApiFetchMock: vi.fn(),
}));

vi.mock('next/headers', () => ({
  cookies: cookiesMock,
}));

vi.mock('@/lib/serverApi', () => ({
  serverApiFetch: serverApiFetchMock,
}));

import { fetchProjects } from './projectsData';

describe('fetchProjects (SSR)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns empty array when mesh_access cookie is missing', async () => {
    cookiesMock.mockResolvedValueOnce({ has: () => false });

    const result = await fetchProjects();
    expect(result).toEqual([]);
    expect(serverApiFetchMock).not.toHaveBeenCalled();
  });

  it('returns project items when mesh_access cookie is present and API succeeds', async () => {
    cookiesMock.mockResolvedValueOnce({ has: (name: string) => name === 'mesh_access' });
    serverApiFetchMock.mockResolvedValueOnce({
      items: [{ id: 'proj-1', title: 'Proyecto SSR' }],
      total: 1,
      skip: 0,
      limit: 50,
    });

    const result = await fetchProjects();
    expect(result).toEqual([{ id: 'proj-1', title: 'Proyecto SSR' }]);
    expect(serverApiFetchMock).toHaveBeenCalledWith('/projects/summary-page?offset=0&limit=50');
  });

  it('returns empty array when serverApiFetch throws an error', async () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    cookiesMock.mockResolvedValueOnce({ has: () => true });
    serverApiFetchMock.mockRejectedValueOnce(new Error('network error'));

    const result = await fetchProjects();
    expect(result).toEqual([]);
    consoleSpy.mockRestore();
  });
});
