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
});
