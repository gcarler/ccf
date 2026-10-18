import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const { apiFetchMock } = vi.hoisted(() => ({
  apiFetchMock: vi.fn(),
}));

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({ token: 'test-token' }),
}));

vi.mock('@/lib/http', async () => {
  const actual = await vi.importActual<typeof import('@/lib/http')>('@/lib/http');
  return {
    ...actual,
    apiFetch: apiFetchMock,
  };
});

import { ApiError } from '@/lib/http';
import { useWikiDocument } from './useWikiDocument';

describe('useWikiDocument', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('loads existing wiki document and sanitizes HTML content', async () => {
    apiFetchMock.mockResolvedValueOnce({
      title: 'Wiki OPA',
      content: '<p>Lección aprendida</p><script>alert(1)</script>',
    });

    const { result } = renderHook(() =>
      useWikiDocument('wiki_project_1', { title: 'Wiki OPA' }),
    );

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.content).toBe('<p>Lección aprendida</p>');
    expect(result.current.error).toBeNull();
    expect(localStorage.getItem('wiki_project_1')).toBe('<p>Lección aprendida</p>');

    // Saving an existing document uses PATCH
    apiFetchMock.mockResolvedValueOnce({});
    act(() => {
      result.current.setContent('<p>Actualizado</p>');
    });
    await act(async () => {
      await result.current.saveNow();
    });

    expect(apiFetchMock).toHaveBeenCalledWith('/wiki/pages/wiki_project_1', {
      method: 'PATCH',
      token: 'test-token',
      body: { content: '<p>Actualizado</p>' },
    });
    expect(result.current.lastSaved).toBeInstanceOf(Date);
  });

  it('treats 404 ApiError as a new document without error, and uses POST on saveNow with 409 PATCH fallback', async () => {
    apiFetchMock.mockRejectedValueOnce(new ApiError('Not found', 404));

    const { result } = renderHook(() =>
      useWikiDocument('wiki_new_key', { title: 'Nueva Wiki' }),
    );

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.error).toBeNull();

    // Simulate 409 conflict on POST followed by successful PATCH fallback
    apiFetchMock
      .mockRejectedValueOnce(new ApiError('Conflict', 409))
      .mockResolvedValueOnce({});

    act(() => {
      result.current.setContent('<p>Contenido inicial</p>');
    });
    await act(async () => {
      await result.current.saveNow();
    });

    expect(apiFetchMock).toHaveBeenCalledWith('/wiki/pages/wiki_new_key', {
      method: 'POST',
      token: 'test-token',
      body: { content: '<p>Contenido inicial</p>' },
    });
    expect(apiFetchMock).toHaveBeenCalledWith('/wiki/pages/wiki_new_key', {
      method: 'PATCH',
      token: 'test-token',
      body: { content: '<p>Contenido inicial</p>' },
    });
    expect(result.current.error).toBeNull();
  });
});
