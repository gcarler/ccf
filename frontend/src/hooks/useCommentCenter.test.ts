import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const { apiFetchMock } = vi.hoisted(() => ({
  apiFetchMock: vi.fn(),
}));

vi.mock('@/lib/http', () => ({
  apiFetch: apiFetchMock,
}));

import { useCommentCenter, type CommentCenterItem } from './useCommentCenter';

const sampleComments: CommentCenterItem[] = [
  {
    id: 'c-1',
    project_id: 'proj-1',
    task_id: 'task-1',
    author_id: 'u-1',
    author_name: 'Nora',
    content: 'Observación abierta con adjunto',
    is_resolved: false,
    created_at: '2026-10-03T12:00:00Z',
    updated_at: '2026-10-03T12:00:00Z',
    attachments: [{ url: '/f.pdf', type: 'application/pdf', name: 'f.pdf', size: 120 }],
    mentions: [],
    module_type: 'project',
    context_title: 'Proyecto 1',
  },
  {
    id: 'c-2',
    project_id: 'proj-1',
    task_id: null,
    author_id: 'u-2',
    author_name: 'Carlos',
    content: 'Observación resuelta sin adjunto',
    is_resolved: true,
    created_at: '2026-10-03T13:00:00Z',
    updated_at: '2026-10-03T13:00:00Z',
    attachments: [],
    mentions: ['u-1'],
    module_type: 'project',
    context_title: 'Proyecto 1',
  },
];

describe('useCommentCenter', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches comments by tab and typeFilter, computes PMI summary, and supports refresh()', async () => {
    apiFetchMock.mockResolvedValue(sampleComments);

    const { result, rerender } = renderHook(
      ({ tab, typeFilter }: { tab: 'created' | 'mentions'; typeFilter: 'all' | 'project' }) =>
        useCommentCenter({ tab, typeFilter, limit: 25 }),
      { initialProps: { tab: 'created', typeFilter: 'all' } },
    );

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(apiFetchMock).toHaveBeenCalledWith('/comments/me/created', {
      query: { limit: '25' },
    });
    expect(result.current.items).toHaveLength(2);
    expect(result.current.summary).toEqual({
      total: 2,
      unresolved: 1,
      resolved: 1,
      withAttachments: 1,
    });

    rerender({ tab: 'mentions', typeFilter: 'project' });
    await waitFor(() =>
      expect(apiFetchMock).toHaveBeenCalledWith('/comments/me/mentions', {
        query: { limit: '25', type: 'project' },
      }),
    );

    await act(async () => {
      await result.current.refresh();
    });
    expect(apiFetchMock).toHaveBeenCalledTimes(3);
  });

  it('handles API errors by setting error message and resetting items to empty array', async () => {
    apiFetchMock.mockRejectedValueOnce(new Error('Fallo de red'));

    const { result } = renderHook(() =>
      useCommentCenter({ tab: 'created', typeFilter: 'all' }),
    );

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBe('Fallo de red');
    expect(result.current.items).toEqual([]);
    expect(result.current.summary).toEqual({
      total: 0,
      unresolved: 0,
      resolved: 0,
      withAttachments: 0,
    });
  });
});
