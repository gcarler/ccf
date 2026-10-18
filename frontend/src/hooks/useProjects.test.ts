import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const { apiFetchMock, authToken } = vi.hoisted(() => ({
  apiFetchMock: vi.fn(),
  authToken: { current: 'test-token' as string | null },
}));

vi.mock('@/lib/http', () => ({ apiFetch: apiFetchMock }));
vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({ token: authToken.current, loading: false }),
}));

import { useProjects, type UpdateProjectPayload } from './useProjects';

const projectRecord = {
  id: 'p1',
  title: 'Proyecto Alpha',
  status: 'active',
  created_at: '2026-01-01T00:00:00Z',
};

describe('useProjects', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    authToken.current = 'test-token';
  });

  it('updateProject envía PATCH con el payload de gobernanza PMI y devuelve el registro', async () => {
    apiFetchMock.mockResolvedValueOnce({ ...projectRecord, status: 'completed' });
    const { result } = renderHook(() => useProjects());

    const payload: UpdateProjectPayload = {
      status: 'completed',
      health_status: 'on_track',
      progress_mode: 'auto_tasks',
      start_date: '2026-01-10T00:00:00Z',
      due_date: '2026-12-31T00:00:00Z',
      budget_allocated: 5000,
      budget_executed: 1200,
    };

    const updated = await act(async () => result.current.updateProject('p1', payload));

    expect(updated).toEqual({ ...projectRecord, status: 'completed' });
    expect(apiFetchMock).toHaveBeenCalledWith(
      '/projects/p1',
      expect.objectContaining({ method: 'PATCH', token: 'test-token', body: payload }),
    );
    expect(result.current.error).toBeNull();
  });

  it('deleteProject invoca DELETE y reporta éxito', async () => {
    apiFetchMock.mockResolvedValueOnce(undefined);
    const { result } = renderHook(() => useProjects());

    const ok = await act(async () => result.current.deleteProject('p1'));

    expect(ok).toBe(true);
    expect(apiFetchMock).toHaveBeenCalledWith(
      '/projects/p1',
      expect.objectContaining({ method: 'DELETE', token: 'test-token' }),
    );
  });

  it('completeProject fija status completed vía updateProject (PMI §4.7)', async () => {
    apiFetchMock.mockResolvedValueOnce({ ...projectRecord, status: 'completed' });
    const { result } = renderHook(() => useProjects());

    await act(async () => result.current.completeProject('p1'));

    expect(apiFetchMock).toHaveBeenCalledWith(
      '/projects/p1',
      expect.objectContaining({
        method: 'PATCH',
        token: 'test-token',
        body: { status: 'completed' },
      }),
    );
  });

  it('archiveProject fija status archived vía updateProject (PMI §4.7, soft)', async () => {
    apiFetchMock.mockResolvedValueOnce({ ...projectRecord, status: 'archived' });
    const { result } = renderHook(() => useProjects());

    await act(async () => result.current.archiveProject('p1'));

    expect(apiFetchMock).toHaveBeenCalledWith(
      '/projects/p1',
      expect.objectContaining({
        method: 'PATCH',
        token: 'test-token',
        body: { status: 'archived' },
      }),
    );
  });

  it('updateProject registra error cuando la API falla y devuelve null', async () => {
    apiFetchMock.mockRejectedValueOnce(new Error('boom'));
    const { result } = renderHook(() => useProjects());

    const updated = await act(async () => result.current.updateProject('p1', { title: 'X' }));

    expect(updated).toBeNull();
    expect(result.current.error).toBe('No se pudo actualizar el proyecto.');
  });

  it('deleteProject registra error cuando la API falla y devuelve false', async () => {
    apiFetchMock.mockRejectedValueOnce(new Error('boom'));
    const { result } = renderHook(() => useProjects());

    const ok = await act(async () => result.current.deleteProject('p1'));

    expect(ok).toBe(false);
    expect(result.current.error).toBe('No se pudo eliminar el proyecto.');
  });

  it('demandas sin token quedan bloqueadas con mensaje de sesión y sin llamada HTTP', async () => {
    authToken.current = null;
    const { result } = renderHook(() => useProjects());

    await act(async () => {
      expect(await result.current.updateProject('p1', { title: 'X' })).toBeNull();
      expect(await result.current.deleteProject('p1')).toBe(false);
      expect(await result.current.completeProject('p1')).toBeNull();
      expect(await result.current.archiveProject('p1')).toBeNull();
    });

    expect(apiFetchMock).not.toHaveBeenCalled();
    await waitFor(() => {
      expect(result.current.error).toContain('iniciar sesión');
    });
  });
});
