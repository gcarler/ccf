import React from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { apiFetch } from '@/lib/http';
import {
    ThemeProvider,
    useTheme,
    useAppearance,
    UI_SCALE_OPTIONS,
    ACCENT_PALETTES,
} from './ThemeContext';

vi.mock('@/lib/http', () => ({
    apiFetch: vi.fn().mockResolvedValue({}),
}));

function ConsumerComponent() {
    const {
        theme,
        toggleTheme,
        setTheme,
        uiScale,
        setUiScale,
        scaleFactor,
        uiDensity,
        setUiDensity,
        currentDensity,
        accent,
        setAccent,
        resetToDefaults,
        isSyncing,
    } = useTheme();

    return (
        <div>
            <div data-testid="theme-val">{theme}</div>
            <div data-testid="scale-val">{uiScale}</div>
            <div data-testid="scale-factor">{scaleFactor}</div>
            <div data-testid="density-val">{uiDensity}</div>
            <div data-testid="density-label">{currentDensity.label}</div>
            <div data-testid="accent-val">{accent}</div>
            <div data-testid="sync-val">{isSyncing ? 'syncing' : 'idle'}</div>

            <button data-testid="toggle-theme" onClick={toggleTheme}>Toggle</button>
            <button data-testid="set-night" onClick={() => setTheme('night')}>Night</button>
            <button data-testid="set-day" onClick={() => setTheme('day')}>Day</button>
            <button data-testid="set-compact" onClick={() => setUiScale('compact')}>Compact</button>
            <button data-testid="set-large" onClick={() => setUiScale('large')}>Large</button>
            <button data-testid="set-spacious" onClick={() => setUiDensity('spacious')}>Spacious</button>
            <button data-testid="set-comfortable" onClick={() => setUiDensity('comfortable')}>Comfortable</button>
            <button data-testid="set-emerald" onClick={() => setAccent('emerald')}>Emerald</button>
            <button data-testid="set-burgundy" onClick={() => setAccent('burgundy')}>Burgundy</button>
            <button data-testid="reset-btn" onClick={resetToDefaults}>Reset</button>
        </div>
    );
}

describe('ThemeContext & AppearanceContext', () => {
    beforeEach(() => {
        localStorage.clear();
        document.documentElement.removeAttribute('data-theme');
        document.documentElement.removeAttribute('data-ui-scale');
        document.documentElement.removeAttribute('data-ui-density');
        document.documentElement.removeAttribute('data-accent');
        document.documentElement.className = '';
        vi.clearAllMocks();
        vi.mocked(apiFetch).mockReset().mockResolvedValue({});
    });

    it('loads remote preferences without writing them back until the user changes a setting', async () => {
        vi.useFakeTimers();
        vi.mocked(apiFetch).mockResolvedValue({ settings: { theme_mode: 'night' } });
        try {
            render(<ThemeProvider><ConsumerComponent /></ThemeProvider>);
            await act(async () => { await vi.advanceTimersByTimeAsync(1000); });
            expect(screen.getByTestId('theme-val')).toHaveTextContent('night');
            expect(apiFetch).toHaveBeenCalledTimes(1);
            expect(apiFetch).toHaveBeenCalledWith('/v3/auth/preferences', { silent: true });

            act(() => { screen.getByTestId('set-day').click(); });
            await act(async () => { await vi.advanceTimersByTimeAsync(600); });
            expect(apiFetch).toHaveBeenLastCalledWith('/v3/auth/preferences', expect.objectContaining({
                method: 'PUT', body: { settings: expect.objectContaining({ theme_mode: 'day' }) },
            }));
            expect(apiFetch).toHaveBeenCalledTimes(2);
        } finally {
            vi.useRealTimers();
        }
    });

    it('preserves a user change when the initial remote profile arrives later', async () => {
        vi.useFakeTimers();
        let resolveProfile: (value: unknown) => void = () => undefined;
        vi.mocked(apiFetch).mockImplementationOnce(() => new Promise(resolve => { resolveProfile = resolve; }));
        try {
            render(<ThemeProvider><ConsumerComponent /></ThemeProvider>);
            act(() => { screen.getByTestId('set-night').click(); });
            await act(async () => { resolveProfile({ settings: { theme_mode: 'day' } }); });
            expect(screen.getByTestId('theme-val')).toHaveTextContent('night');
            await act(async () => { await vi.advanceTimersByTimeAsync(600); });
            expect(apiFetch).toHaveBeenLastCalledWith('/v3/auth/preferences', expect.objectContaining({
                method: 'PUT', body: { settings: expect.objectContaining({ theme_mode: 'night' }) },
            }));
        } finally {
            vi.useRealTimers();
        }
    });

    it('initializes with default values and injects them to root html element', () => {
        render(
            <ThemeProvider>
                <ConsumerComponent />
            </ThemeProvider>
        );

        expect(screen.getByTestId('theme-val').textContent).toBe('day');
        expect(screen.getByTestId('scale-val').textContent).toBe('normal');
        expect(screen.getByTestId('density-val').textContent).toBe('ultra-compact');
        expect(screen.getByTestId('scale-factor').textContent).toBe('1');
        expect(screen.getByTestId('accent-val').textContent).toBe('ccf-blue');

        const root = document.documentElement;
        expect(root.getAttribute('data-theme')).toBe('day');
        expect(root.getAttribute('data-ui-scale')).toBe('normal');
        expect(root.getAttribute('data-ui-density')).toBe('ultra-compact');
        expect(root.getAttribute('data-accent')).toBe('ccf-blue');
        expect(root.style.getPropertyValue('--ui-scale')).toBe('1');
        expect(root.style.getPropertyValue('--density-row-h')).toBe('28px');
        expect(root.style.getPropertyValue('--density-pad-x')).toBe('0.5rem');
        expect(root.style.getPropertyValue('--density-pad-y')).toBe('0.125rem');
        expect(root.style.getPropertyValue('--density-gap')).toBe('0.25rem');
        expect(root.style.getPropertyValue('--primary')).toBe(ACCENT_PALETTES['ccf-blue'].day.primary);
    });

    it('allows toggling and explicitly setting day/night themes', () => {
        render(
            <ThemeProvider>
                <ConsumerComponent />
            </ThemeProvider>
        );

        const toggleBtn = screen.getByTestId('toggle-theme');
        act(() => {
            toggleBtn.click();
        });

        expect(screen.getByTestId('theme-val').textContent).toBe('night');
        expect(document.documentElement.classList.contains('dark')).toBe(true);
        expect(document.documentElement.getAttribute('data-theme')).toBe('night');
        expect(localStorage.getItem('theme-mode')).toBe('night');

        const setDayBtn = screen.getByTestId('set-day');
        act(() => {
            setDayBtn.click();
        });

        expect(screen.getByTestId('theme-val').textContent).toBe('day');
        expect(document.documentElement.classList.contains('dark')).toBe(false);
    });

    it('updates uiScale, scaleFactor, and font-size on root document element', () => {
        render(
            <ThemeProvider>
                <ConsumerComponent />
            </ThemeProvider>
        );

        const compactBtn = screen.getByTestId('set-compact');
        act(() => {
            compactBtn.click();
        });

        expect(screen.getByTestId('scale-val').textContent).toBe('compact');
        expect(screen.getByTestId('scale-factor').textContent).toBe('0.9');
        expect(document.documentElement.style.getPropertyValue('--ui-scale')).toBe('0.9');
        expect(document.documentElement.style.fontSize).toBe('90%');
        expect(localStorage.getItem('theme-scale')).toBe('compact');

        const largeBtn = screen.getByTestId('set-large');
        act(() => {
            largeBtn.click();
        });

        expect(screen.getByTestId('scale-val').textContent).toBe('large');
        expect(screen.getByTestId('scale-factor').textContent).toBe('1.25');
        expect(document.documentElement.style.getPropertyValue('--ui-scale')).toBe('1.25');
        expect(document.documentElement.style.fontSize).toBe('125%');
    });

    it('updates ministerial accent and sets matching primary tokens', () => {
        render(
            <ThemeProvider>
                <ConsumerComponent />
            </ThemeProvider>
        );

        const emeraldBtn = screen.getByTestId('set-emerald');
        act(() => {
            emeraldBtn.click();
        });

        expect(screen.getByTestId('accent-val').textContent).toBe('emerald');
        expect(document.documentElement.getAttribute('data-accent')).toBe('emerald');
        expect(document.documentElement.style.getPropertyValue('--primary')).toBe(ACCENT_PALETTES.emerald.day.primary);
        expect(document.documentElement.style.getPropertyValue('--primary-foreground')).toBe(ACCENT_PALETTES.emerald.day.primaryForeground);
        expect(localStorage.getItem('theme-accent')).toBe('emerald');

        const burgundyBtn = screen.getByTestId('set-burgundy');
        act(() => {
            burgundyBtn.click();
        });

        expect(screen.getByTestId('accent-val').textContent).toBe('burgundy');
        expect(document.documentElement.getAttribute('data-accent')).toBe('burgundy');
    });

    it('updates uiDensity and applies corresponding CSS density variables to root document element', () => {
        render(
            <ThemeProvider>
                <ConsumerComponent />
            </ThemeProvider>
        );

        const spaciousBtn = screen.getByTestId('set-spacious');
        act(() => {
            spaciousBtn.click();
        });

        expect(screen.getByTestId('density-val').textContent).toBe('spacious');
        expect(document.documentElement.getAttribute('data-ui-density')).toBe('spacious');
        expect(document.documentElement.style.getPropertyValue('--density-row-h')).toBe('52px');
        expect(document.documentElement.style.getPropertyValue('--density-pad-x')).toBe('1.25rem');
        expect(document.documentElement.style.getPropertyValue('--density-pad-y')).toBe('0.875rem');
        expect(document.documentElement.style.getPropertyValue('--density-gap')).toBe('1rem');
        expect(localStorage.getItem('theme-density')).toBe('spacious');
    });

    it('restores initial values on resetToDefaults', () => {
        render(
            <ThemeProvider>
                <ConsumerComponent />
            </ThemeProvider>
        );

        act(() => {
            screen.getByTestId('set-night').click();
            screen.getByTestId('set-large').click();
            screen.getByTestId('set-spacious').click();
            screen.getByTestId('set-emerald').click();
        });

        expect(screen.getByTestId('theme-val').textContent).toBe('night');
        expect(screen.getByTestId('scale-val').textContent).toBe('large');
        expect(screen.getByTestId('density-val').textContent).toBe('spacious');
        expect(screen.getByTestId('accent-val').textContent).toBe('emerald');

        act(() => {
            screen.getByTestId('reset-btn').click();
        });

        expect(screen.getByTestId('theme-val').textContent).toBe('day');
        expect(screen.getByTestId('scale-val').textContent).toBe('normal');
        expect(screen.getByTestId('density-val').textContent).toBe('ultra-compact');
        expect(screen.getByTestId('accent-val').textContent).toBe('ccf-blue');
        expect(document.documentElement.getAttribute('data-ui-density')).toBe('ultra-compact');
        expect(document.documentElement.style.getPropertyValue('--density-row-h')).toBe('28px');
    });

    it('verifies that all 6 ministerial accents meet WCAG AA contrast requirements (>= 4.5:1)', () => {
        const accentKeys = Object.keys(ACCENT_PALETTES) as (keyof typeof ACCENT_PALETTES)[];
        expect(accentKeys).toHaveLength(6);

        accentKeys.forEach((key) => {
            const pal = ACCENT_PALETTES[key];
            expect(pal.wcagDayRatio).toBeGreaterThanOrEqual(4.5);
            expect(pal.wcagNightRatio).toBeGreaterThanOrEqual(4.5);
        });
    });

    it('verifies all 4 UI scale options exist and have correct factors', () => {
        expect(UI_SCALE_OPTIONS.compact.scale).toBe(0.9);
        expect(UI_SCALE_OPTIONS.normal.scale).toBe(1.0);
        expect(UI_SCALE_OPTIONS.comfortable.scale).toBe(1.15);
        expect(UI_SCALE_OPTIONS.large.scale).toBe(1.25);
    });

    it('useAppearance hook functions as an exact alias for useTheme', () => {
        function AppearanceConsumer() {
            const { theme, uiScale, accent } = useAppearance();
            return (
                <div data-testid="app-info">
                    {theme}-{uiScale}-{accent}
                </div>
            );
        }

        render(
            <ThemeProvider>
                <AppearanceConsumer />
            </ThemeProvider>
        );

        expect(screen.getByTestId('app-info').textContent).toBe('day-normal-ccf-blue');
    });
});
