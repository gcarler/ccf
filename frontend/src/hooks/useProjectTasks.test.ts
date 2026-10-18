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

import { useProjectTasks, type UpdateTaskPayload } from './useProjectTasks';

const taskRecord = {
  id: 't1',
  project_id: 'p1',
  title: 'Paquete WBS 1.2',
  status: 'todo',
  priority: 'medium',
};

describe('useProjectTasks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    authToken.current = 'test-token';
  });

  it('fetchTasks carga las tareas del proyecto', async () => {
    apiFetchMock.mockResolvedValueOnce([taskRecord]);
    const { result } = renderHook(() => useProjectTasks());

    await act(async () => result.current.fetchTasks('p1'));

    expect(apiFetchMock).toHaveBeenCalledWith('/projects/p1/tasks', { token: 'test-token' });
    expect(result.current.tasks).toEqual([taskRecord]);
    expect(result.current.loading).toBe(false);
  });

  it('createTask hace POST con campos WBS PMI y agrega la tarea al estado', async () => {
    const created = { ...taskRecord, phase: 'fase-1', component_id: 'comp-9', estimated_hours: 8 };
    apiFetchMock.mockResolvedValueOnce(created);
    const { result } = renderHook(() => useProjectTasks());

    const newTask = await act(async () =>
      result.current.createTask('p1', {
        title: 'Paquete WBS 1.2',
        phase: 'fase-1',
        component_id: 'comp-9',
        estimated_hours: 8,
      }),
    );

    expect(newTask).toEqual(created);
    expect(apiFetchMock).toHaveBeenCalledWith(
      '/projects/p1/tasks',
      expect.objectContaining({
        method: 'POST',
        token: 'test-token',
        body: { title: 'Paquete WBS 1.2', phase: 'fase-1', component_id: 'comp-9', estimated_hours: 8 },
      }),
    );
    expect(result.current.tasks[0]).toEqual(created);
  });

  it('createTask reporta error cuando la API falla y devuelve null', async () => {
    apiFetchMock.mockRejectedValueOnce(new Error('boom'));
    const { result } = renderHook(() => useProjectTasks());

    const created = await act(async () => result.current.createTask('p1', { title: 'X' }));

    expect(created).toBeNull();
    expect(result.current.error).toBe('No se pudo crear la tarea.');
  });

  it('updateTask aplica cambios optimistas y sincroniza con la API (PATCH WBS)', async () => {
    apiFetchMock.mockResolvedValueOnce({ ...taskRecord, status: 'in_progress', estimated_hours: 12 });
    const { result } = renderHook(() => useProjectTasks());

    await act(async () => {
      result.current.setTasks([taskRecord]);
    });

    const payload: UpdateTaskPayload = { status: 'in_progress', phase: 'fase-2', estimated_hours: 12 };
    const updated = await act(async () => result.current.updateTask('t1', payload));

    expect(updated).toEqual({ ...taskRecord, status: 'in_progress', estimated_hours: 12 });
    expect(apiFetchMock).toHaveBeenCalledWith(
      '/projects/tasks/t1',
      expect.objectContaining({ method: 'PATCH', token: 'test-token', body: payload }),
    );
    expect(result.current.tasks[0].status).toBe('in_progress');
  });

  it('updateTask revierte el estado optimista cuando la API falla', async () => {
    apiFetchMock.mockRejectedValueOnce(new Error('boom'));
    const { result } = renderHook(() => useProjectTasks());

    await act(async () => {
      result.current.setTasks([{ ...taskRecord, title: 'Paquete WBS 1.2 original' }]);
    });

    const failed = await act(async () =>
      result.current.updateTask('t1', { title: 'Título roto' }, { optimistic: true }),
    );

    expect(failed).toBeNull();
    expect(result.current.tasks[0].title).toBe('Paquete WBS 1.2 original');
    expect(result.current.error).toBe('No se pudo actualizar la tarea.');
  });

  it('deleteTask hace DELETE al proyecto de la tarea y la quita del estado', async () => {
    apiFetchMock.mockResolvedValueOnce(undefined);
    const { result } = renderHook(() => useProjectTasks());

    await act(async () => {
      result.current.setTasks([taskRecord]);
    });

    const ok = await act(async () => result.current.deleteTask('t1'));

    expect(ok).toBe(true);
    expect(apiFetchMock).toHaveBeenCalledWith(
      '/projects/p1/tasks/t1',
      expect.objectContaining({ method: 'DELETE', token: 'test-token' }),
    );
    expect(result.current.tasks).toEqual([]);
  });

  it('moveTask delega en updateTask con el nuevo estado', async () => {
    apiFetchMock.mockResolvedValueOnce({ ...taskRecord, status: 'review' });
    const { result } = renderHook(() => useProjectTasks());

    await act(async () => {
      result.current.setTasks([taskRecord]);
    });

    const moved = await act(async () => result.current.moveTask('t1', 'review'));

    expect(moved).toEqual({ ...taskRecord, status: 'review' });
    expect(apiFetchMock).toHaveBeenCalledWith(
      '/projects/tasks/t1',
      expect.objectContaining({ method: 'PATCH', token: 'test-token', body: { status: 'review' } }),
    );
  });

  it('demandas sin token bloquean fetch/create/delete con mensaje de sesión y sin HTTP', async () => {
    authToken.current = null;
    const { result } = renderHook(() => useProjectTasks());

    await act(async () => {
      await result.current.fetchTasks('p1');
      expect(await result.current.createTask('p1', { title: 'X' })).toBeNull();
      expect(await result.current.deleteTask('t1')).toBe(false);
    });

    expect(apiFetchMock).not.toHaveBeenCalled();
    await waitFor(() => {
      expect(result.current.error).toContain('iniciar sesión');
    });
  });
});
