import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useUserSearch } from './useUserSearch';
import { apiFetch } from '@/lib/http';

vi.mock('@/lib/http', () => ({ apiFetch: vi.fn() }));

describe('useUserSearch', () => {
    beforeEach(() => {
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.useRealTimers();
        vi.clearAllMocks();
    });

    it('does not search while query is below minLength', async () => {
        const { result } = renderHook(() => useUserSearch({ token: 'token' }));
        act(() => result.current.setQuery('a'));
        act(() => vi.advanceTimersByTime(500));
        expect(apiFetch).not.toHaveBeenCalled();
    });

    it('debounces search and returns results', async () => {
        const users = [{ id: 'u1', username: 'ana', email: 'ana@test', avatar_url: null }];
        (apiFetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(users);

        const { result } = renderHook(() => useUserSearch({ token: 'token', debounceMs: 300 }));
        act(() => result.current.setQuery('ana'));
        expect(result.current.loading).toBe(false);

        act(() => vi.advanceTimersByTime(300));
        await act(async () => { await Promise.resolve(); });

        expect(result.current.results).toEqual(users);
        expect(result.current.loading).toBe(false);
    });

    it('resets state correctly', async () => {
        const { result } = renderHook(() => useUserSearch({ token: 'token' }));
        act(() => result.current.setQuery('query'));
        act(() => result.current.reset());
        expect(result.current.query).toBe('');
        expect(result.current.results).toEqual([]);
        expect(result.current.error).toBeNull();
    });

    it('shows loading state while a search is in flight', async () => {
        let resolveSearch: (value: unknown) => void = () => {};
        (apiFetch as unknown as ReturnType<typeof vi.fn>).mockImplementation(() => new Promise((resolve) => { resolveSearch = resolve; }));

        const { result } = renderHook(() => useUserSearch({ token: 'token', debounceMs: 300 }));
        act(() => result.current.setQuery('ana'));
        act(() => vi.advanceTimersByTime(300));
        expect(result.current.loading).toBe(true);

        act(() => resolveSearch([{ id: 'u1', username: 'ana', email: 'ana@test', avatar_url: null }]));
        await act(async () => { await Promise.resolve(); });
        expect(result.current.loading).toBe(false);
    });

    it('handles search errors', async () => {
        (apiFetch as unknown as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('fail'));
        const { result } = renderHook(() => useUserSearch({ token: 'token', debounceMs: 300 }));
        act(() => result.current.setQuery('ana'));
        act(() => vi.advanceTimersByTime(300));
        await act(async () => { await Promise.resolve(); });
        expect(result.current.error).toBe('Error al buscar usuarios');
        expect(result.current.results).toEqual([]);
    });

    it('shows "no results" error when response is empty', async () => {
        (apiFetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([]);
        const { result } = renderHook(() => useUserSearch({ token: 'token', debounceMs: 300 }));
        act(() => result.current.setQuery('zzz'));
        act(() => vi.advanceTimersByTime(300));
        await act(async () => { await Promise.resolve(); });
        expect(result.current.error).toBe('No se encontraron usuarios');
    });

    it('respects custom minLength', async () => {
        (apiFetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([]);
        const { result } = renderHook(() => useUserSearch({ token: 'token', debounceMs: 300, minLength: 3 }));
        act(() => result.current.setQuery('an'));
        act(() => vi.advanceTimersByTime(300));
        await act(async () => { await Promise.resolve(); });
        expect(apiFetch).not.toHaveBeenCalled();
    });

    it('does not search when token is null', async () => {
        (apiFetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([]);
        const { result } = renderHook(() => useUserSearch({ token: null, debounceMs: 300 }));
        act(() => result.current.setQuery('ana'));
        act(() => vi.advanceTimersByTime(300));
        await act(async () => { await Promise.resolve(); });
        expect(apiFetch).not.toHaveBeenCalled();
    });
});
