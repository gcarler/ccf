import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useDebounce } from './useDebounce';

describe('useDebounce', () => {
    beforeEach(() => {
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it('returns the initial value immediately', () => {
        const { result } = renderHook(() => useDebounce('initial', 200));
        expect(result.current).toBe('initial');
    });

    it('updates the debounced value after the specified delay', () => {
        const { rerender, result } = renderHook(
            ({ value, delay }: { value: string; delay: number }) => useDebounce(value, delay),
            { initialProps: { value: 'first', delay: 200 } }
        );

        expect(result.current).toBe('first');

        rerender({ value: 'second', delay: 200 });
        expect(result.current).toBe('first');

        act(() => {
            vi.advanceTimersByTime(200);
        });

        expect(result.current).toBe('second');
    });

    it('resets the timer when the value changes before the delay', () => {
        const { rerender, result } = renderHook(
            ({ value, delay }: { value: string; delay: number }) => useDebounce(value, delay),
            { initialProps: { value: 'a', delay: 200 } }
        );

        rerender({ value: 'b', delay: 200 });
        act(() => {
            vi.advanceTimersByTime(150);
        });
        expect(result.current).toBe('a');

        rerender({ value: 'c', delay: 200 });
        act(() => {
            vi.advanceTimersByTime(200);
        });
        expect(result.current).toBe('c');
    });
});
