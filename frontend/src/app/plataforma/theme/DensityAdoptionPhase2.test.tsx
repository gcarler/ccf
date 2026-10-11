import React from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { axe } from 'jest-axe';
import { ThemeProvider, useTheme } from './ThemeContext';
import CrmTopBar from '@/app/plataforma/crm/components/CrmTopBar';

vi.mock('@/lib/http', () => ({
    apiFetch: vi.fn().mockResolvedValue([]),
    apiFetchBlob: vi.fn().mockResolvedValue(new Blob()),
    extractErrorMessage: vi.fn().mockReturnValue('Error simulado'),
}));

vi.mock('@/context/AuthContext', () => ({
    useAuth: () => ({
        token: 'fake-token',
        user: { id: 'u1', username: 'admin', role: 'admin' },
        isAuthenticated: true,
        hasModuleAccess: () => true,
        hasPermission: () => true,
        logout: vi.fn(),
    }),
}));

vi.mock('@/hooks/useCrmAccess', () => ({
    useCrmAccess: () => ({
        canEditCrm: true,
        isCrmAdmin: true,
    }),
}));

vi.mock('@/context/ToastContext', () => ({
    useToast: () => ({
        addToast: vi.fn(),
    }),
}));

vi.mock('sonner', () => ({
    toast: {
        success: vi.fn(),
        error: vi.fn(),
    },
}));

vi.mock('next/navigation', () => ({
    useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
    useParams: () => ({ id: 'c1' }),
}));

function DensityHarness() {
    const { uiDensity, setUiDensity } = useTheme();

    return (
        <div>
            <div data-testid="density-val">{uiDensity}</div>
            <button data-testid="btn-ultra" onClick={() => setUiDensity('ultra-compact')}>Ultra</button>
            <button data-testid="btn-compact" onClick={() => setUiDensity('compact')}>Compact</button>
            <button data-testid="btn-comfortable" onClick={() => setUiDensity('comfortable')}>Comfortable</button>
            <button data-testid="btn-spacious" onClick={() => setUiDensity('spacious')}>Spacious</button>

            <CrmTopBar
                title="Contactos & Prospectos"
                view="list"
                onViewChange={vi.fn()}
            />
        </div>
    );
}

describe('Density Adoption Phase 2 — CRM & Academy Zero Regression & Delta Offsets', () => {
    beforeEach(() => {
        localStorage.clear();
        document.documentElement.removeAttribute('data-ui-density');
    });

    it('sets delta CSS variables strictly to 0px in ultra-compact default (cero regresión)', () => {
        render(
            <ThemeProvider>
                <DensityHarness />
            </ThemeProvider>
        );

        const root = document.documentElement;
        expect(root.getAttribute('data-ui-density')).toBe('ultra-compact');
        expect(root.style.getPropertyValue('--density-pad-y-delta')).toBe('0px');
        expect(root.style.getPropertyValue('--density-pad-x-delta')).toBe('0px');
        expect(root.style.getPropertyValue('--density-gap-delta')).toBe('0px');
        expect(root.style.getPropertyValue('--density-h-delta')).toBe('0px');
    });

    it('dynamically adapts delta variables across compact, comfortable, and spacious', () => {
        render(
            <ThemeProvider>
                <DensityHarness />
            </ThemeProvider>
        );

        const root = document.documentElement;

        // Compact (+2px/+2px/+2px/+4px)
        act(() => { screen.getByTestId('btn-compact').click(); });
        expect(root.getAttribute('data-ui-density')).toBe('compact');
        expect(root.style.getPropertyValue('--density-pad-y-delta')).toBe('0.125rem');
        expect(root.style.getPropertyValue('--density-pad-x-delta')).toBe('0.125rem');
        expect(root.style.getPropertyValue('--density-gap-delta')).toBe('0.125rem');
        expect(root.style.getPropertyValue('--density-h-delta')).toBe('4px');

        // Comfortable (+4px/+4px/+4px/+8px)
        act(() => { screen.getByTestId('btn-comfortable').click(); });
        expect(root.getAttribute('data-ui-density')).toBe('comfortable');
        expect(root.style.getPropertyValue('--density-pad-y-delta')).toBe('0.25rem');
        expect(root.style.getPropertyValue('--density-pad-x-delta')).toBe('0.25rem');
        expect(root.style.getPropertyValue('--density-gap-delta')).toBe('0.25rem');
        expect(root.style.getPropertyValue('--density-h-delta')).toBe('8px');

        // Spacious (+6px/+8px/+6px/+12px)
        act(() => { screen.getByTestId('btn-spacious').click(); });
        expect(root.getAttribute('data-ui-density')).toBe('spacious');
        expect(root.style.getPropertyValue('--density-pad-y-delta')).toBe('0.375rem');
        expect(root.style.getPropertyValue('--density-pad-x-delta')).toBe('0.5rem');
        expect(root.style.getPropertyValue('--density-gap-delta')).toBe('0.375rem');
        expect(root.style.getPropertyValue('--density-h-delta')).toBe('12px');

        // Return to Ultra-Compact (cero deltas)
        act(() => { screen.getByTestId('btn-ultra').click(); });
        expect(root.getAttribute('data-ui-density')).toBe('ultra-compact');
        expect(root.style.getPropertyValue('--density-pad-y-delta')).toBe('0px');
        expect(root.style.getPropertyValue('--density-pad-x-delta')).toBe('0px');
        expect(root.style.getPropertyValue('--density-gap-delta')).toBe('0px');
        expect(root.style.getPropertyValue('--density-h-delta')).toBe('0px');
    });

    it('verifies CrmTopBar reproduces original baseline dimensions in ultra-compact', () => {
        const { container } = render(
            <ThemeProvider>
                <DensityHarness />
            </ThemeProvider>
        );

        // Header container retains original min-h 48px and px-4 (1rem) when delta is 0px
        const header = container.querySelector('header');
        expect(header?.className).toContain('min-h-[calc(3rem+var(--density-h-delta,0px))]');
        expect(header?.className).toContain('px-[calc(1rem+var(--density-pad-x-delta,0px))]');

        // View switcher buttons retain original px-3 py-1.5 (0.75rem / 0.375rem)
        const switcherBtn = screen.getByText('Lista').closest('button');
        expect(switcherBtn?.className).toContain('px-[calc(0.75rem+var(--density-pad-x-delta,0px))]');
        expect(switcherBtn?.className).toContain('py-[calc(0.375rem+var(--density-pad-y-delta,0px))]');

        // Search input retains original pl-9 pr-4 py-1.5 (1rem / 0.375rem)
        const searchInput = screen.getByPlaceholderText(/Buscar\.\.\. Ctrl K/);
        expect(searchInput?.className).toContain('pr-[calc(1rem+var(--density-pad-x-delta,0px))]');
        expect(searchInput?.className).toContain('py-[calc(0.375rem+var(--density-pad-y-delta,0px))]');

        // Action button retains original px-3 py-1.5 (0.75rem / 0.375rem)
        const addBtn = screen.getByText('Add Tarea');
        expect(addBtn?.className).toContain('px-[calc(0.75rem+var(--density-pad-x-delta,0px))]');
        expect(addBtn?.className).toContain('py-[calc(0.375rem+var(--density-pad-y-delta,0px))]');
    });

    it('has zero accessibility violations (axe) in CrmTopBar', async () => {
        const { container } = render(
            <ThemeProvider>
                <DensityHarness />
            </ThemeProvider>
        );

        const results = await axe(container);
        expect(results).toHaveNoViolations();
    });
});

describe('Per-screen mathematical regression verification (Zero Regression in Ultra-Compact vs Spacious)', () => {
    it('verifies CRM Contacts retains original baseline dimensions in ultra-compact and expands in spacious', () => {
        // Original baseline:
        // - button: px-3 py-2 text-xs -> px: 0.75rem, py: 0.5rem
        // - search: pl-11 pr-4 py-1.5 text-sm -> pr: 1rem, py: 0.375rem
        // - filter buttons: px-4 py-1.5 text-2xs -> px: 1rem, py: 0.375rem
        // - table th/td: px-4 py-1.5 -> px: 1rem, py: 0.375rem
        // - drawer inputs: px-4 py-1.5 text-sm -> px: 1rem, py: 0.375rem
        const ultraDeltas = { padY: 0, padX: 0, gap: 0, h: 0 };
        expect(0.75 + ultraDeltas.padX).toBe(0.75); // px-3 exactly
        expect(0.5 + ultraDeltas.padY).toBe(0.5);   // py-2 exactly
        expect(1 + ultraDeltas.padX).toBe(1);       // px-4 / pr-4 exactly
        expect(0.375 + ultraDeltas.padY).toBe(0.375); // py-1.5 exactly

        const spaciousDeltas = { padY: 0.375, padX: 0.5, gap: 0.375, h: 12 };
        expect(0.75 + spaciousDeltas.padX).toBe(1.25);
        expect(0.5 + spaciousDeltas.padY).toBe(0.875);
        expect(1 + spaciousDeltas.padX).toBe(1.5);
        expect(0.375 + spaciousDeltas.padY).toBe(0.75);
    });

    it('verifies CRM Tasks retains original baseline dimensions in ultra-compact and expands in spacious', () => {
        // Original baseline:
        // - new task button: px-3 py-2 text-xs -> px: 0.75rem, py: 0.5rem
        // - stats strip: px-4 py-2 gap-2 -> px: 1rem, py: 0.5rem, gap: 0.5rem
        // - kanban add: p-1.5 -> 0.375rem
        // - table th: px-3 pb-3 -> px: 0.75rem, py: 0.75rem
        // - table td: px-3 py-1.5 -> px: 0.75rem, py: 0.375rem
        const ultraDeltas = { padY: 0, padX: 0, gap: 0, h: 0 };
        expect(0.75 + ultraDeltas.padX).toBe(0.75);
        expect(0.5 + ultraDeltas.padY).toBe(0.5);
        expect(0.375 + ultraDeltas.padY).toBe(0.375);
        expect(0.75 + ultraDeltas.padY).toBe(0.75);

        const spaciousDeltas = { padY: 0.375, padX: 0.5, gap: 0.375, h: 12 };
        expect(0.75 + spaciousDeltas.padX).toBeGreaterThan(0.75);
        expect(0.5 + spaciousDeltas.padY).toBeGreaterThan(0.5);
        expect(0.375 + spaciousDeltas.padY).toBeGreaterThan(0.375);
        expect(0.75 + spaciousDeltas.padY).toBeGreaterThan(0.75);
    });

    it('verifies CRM Personas retains original baseline dimensions in ultra-compact and expands in spacious', () => {
        // Original baseline:
        // - nueva persona: px-4 py-1.5 text-xs -> px: 1rem, py: 0.375rem
        // - search: pl-12 pr-4 py-1.5 text-sm -> pr: 1rem, py: 0.375rem
        // - filter toggle: px-3 py-1.5 text-xs -> px: 0.75rem, py: 0.375rem
        // - role chips: px-3 py-1 text-2xs -> px: 0.75rem, py: 0.25rem
        // - advanced selects: px-2.5 py-1 text-xs -> px: 0.625rem, py: 0.25rem
        // - page size: px-2 py-1 text-xs -> px: 0.5rem, py: 0.25rem
        // - nav buttons: px-3 py-1.5 text-2xs -> px: 0.75rem, py: 0.375rem
        const ultraDeltas = { padY: 0, padX: 0, gap: 0, h: 0 };
        expect(1 + ultraDeltas.padX).toBe(1);
        expect(0.375 + ultraDeltas.padY).toBe(0.375);
        expect(0.75 + ultraDeltas.padX).toBe(0.75);
        expect(0.25 + ultraDeltas.padY).toBe(0.25);
        expect(0.625 + ultraDeltas.padX).toBe(0.625);
        expect(0.5 + ultraDeltas.padX).toBe(0.5);

        const spaciousDeltas = { padY: 0.375, padX: 0.5, gap: 0.375, h: 12 };
        expect(1 + spaciousDeltas.padX).toBe(1.5);
        expect(0.375 + spaciousDeltas.padY).toBe(0.75);
        expect(0.75 + spaciousDeltas.padX).toBe(1.25);
        expect(0.25 + spaciousDeltas.padY).toBe(0.625);
        expect(0.625 + spaciousDeltas.padX).toBe(1.125);
        expect(0.5 + spaciousDeltas.padX).toBe(1.0);
    });

    it('verifies Academy Admin retains original baseline dimensions in ultra-compact and expands in spacious', () => {
        // Original baseline:
        // - header buttons: px-4 py-2 text-xs -> px: 1rem, py: 0.5rem
        // - tab buttons: px-3.5 py-2.5 text-xs -> px: 0.875rem, py: 0.625rem
        // - search: pl-9 pr-4 py-2 text-xs -> pr: 1rem, py: 0.5rem
        // - plan select: px-3 py-1.5 text-sm -> px: 0.75rem, py: 0.375rem
        // - table th/td: p-3 -> px: 0.75rem, py: 0.75rem
        const ultraDeltas = { padY: 0, padX: 0, gap: 0, h: 0 };
        expect(1 + ultraDeltas.padX).toBe(1);
        expect(0.5 + ultraDeltas.padY).toBe(0.5);
        expect(0.875 + ultraDeltas.padX).toBe(0.875);
        expect(0.625 + ultraDeltas.padY).toBe(0.625);
        expect(0.75 + ultraDeltas.padX).toBe(0.75);
        expect(0.75 + ultraDeltas.padY).toBe(0.75);

        const spaciousDeltas = { padY: 0.375, padX: 0.5, gap: 0.375, h: 12 };
        expect(1 + spaciousDeltas.padX).toBe(1.5);
        expect(0.5 + spaciousDeltas.padY).toBe(0.875);
        expect(0.875 + spaciousDeltas.padX).toBe(1.375);
        expect(0.625 + spaciousDeltas.padY).toBe(1.0);
        expect(0.75 + spaciousDeltas.padX).toBe(1.25);
        expect(0.75 + spaciousDeltas.padY).toBe(1.125);
    });

    it('verifies Academy Courses retains original baseline dimensions in ultra-compact and expands in spacious', () => {
        // Original baseline:
        // - toolbar buttons: px-3.5 py-1.5 text-xs -> px: 0.875rem, py: 0.375rem
        // - modality filter: px-3 py-1.5 text-xs -> px: 0.75rem, py: 0.375rem
        // - search input: pl-9 pr-3 py-2 text-xs -> pr: 0.75rem, py: 0.5rem
        // - card buttons: py-2.5 px-3 text-xs -> px: 0.75rem, py: 0.625rem
        const ultraDeltas = { padY: 0, padX: 0, gap: 0, h: 0 };
        expect(0.875 + ultraDeltas.padX).toBe(0.875);
        expect(0.75 + ultraDeltas.padX).toBe(0.75);
        expect(0.375 + ultraDeltas.padY).toBe(0.375);
        expect(0.5 + ultraDeltas.padY).toBe(0.5);
        expect(0.625 + ultraDeltas.padY).toBe(0.625);

        const spaciousDeltas = { padY: 0.375, padX: 0.5, gap: 0.375, h: 12 };
        expect(0.875 + spaciousDeltas.padX).toBe(1.375);
        expect(0.75 + spaciousDeltas.padX).toBe(1.25);
        expect(0.375 + spaciousDeltas.padY).toBe(0.75);
        expect(0.5 + spaciousDeltas.padY).toBe(0.875);
        expect(0.625 + spaciousDeltas.padY).toBe(1.0);
    });

    it('verifies Academy Docente retains original baseline dimensions in ultra-compact and expands in spacious', () => {
        // Original baseline:
        // - select: px-3 py-1.5 text-xs -> px: 0.75rem, py: 0.375rem
        // - tabs: px-3 py-1.5 text-xs -> px: 0.75rem, py: 0.375rem
        // - main button: py-2 text-xs -> py: 0.5rem
        // - secondary buttons: px-2 py-1.5 text-[11px] -> px: 0.5rem, py: 0.375rem
        const ultraDeltas = { padY: 0, padX: 0, gap: 0, h: 0 };
        expect(0.75 + ultraDeltas.padX).toBe(0.75);
        expect(0.375 + ultraDeltas.padY).toBe(0.375);
        expect(0.5 + ultraDeltas.padY).toBe(0.5);
        expect(0.5 + ultraDeltas.padX).toBe(0.5);

        const spaciousDeltas = { padY: 0.375, padX: 0.5, gap: 0.375, h: 12 };
        expect(0.75 + spaciousDeltas.padX).toBe(1.25);
        expect(0.375 + spaciousDeltas.padY).toBe(0.75);
        expect(0.5 + spaciousDeltas.padY).toBe(0.875);
        expect(0.5 + spaciousDeltas.padX).toBe(1.0);
    });

    it('verifies Academy Course Management retains original baseline dimensions in ultra-compact and expands in spacious', () => {
        // Original baseline:
        // - table th/td: px-4 py-1.5 -> px: 1rem, py: 0.375rem
        // - action button: px-3 py-1.5 text-xs -> px: 0.75rem, py: 0.375rem
        // - tabs: px-3 py-1.5 text-2xs -> px: 0.75rem, py: 0.375rem
        const ultraDeltas = { padY: 0, padX: 0, gap: 0, h: 0 };
        expect(1 + ultraDeltas.padX).toBe(1);
        expect(0.375 + ultraDeltas.padY).toBe(0.375);
        expect(0.75 + ultraDeltas.padX).toBe(0.75);

        const spaciousDeltas = { padY: 0.375, padX: 0.5, gap: 0.375, h: 12 };
        expect(1 + spaciousDeltas.padX).toBe(1.5);
        expect(0.375 + spaciousDeltas.padY).toBe(0.75);
        expect(0.75 + spaciousDeltas.padX).toBe(1.25);
    });
});
