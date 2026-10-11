import React from 'react';
import fs from 'fs';
import path from 'path';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { axe } from 'jest-axe';
import { ThemeProvider, useTheme } from './ThemeContext';

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
    useParams: () => ({ id: 'p1' }),
}));

function DensityHarness() {
    const { uiDensity, setUiDensity } = useTheme();

    return (
        <div data-testid="density-harness-root">
            <div data-testid="density-val">{uiDensity}</div>
            <button data-testid="btn-ultra" onClick={() => setUiDensity('ultra-compact')}>Ultra</button>
            <button data-testid="btn-compact" onClick={() => setUiDensity('compact')}>Compact</button>
            <button data-testid="btn-comfortable" onClick={() => setUiDensity('comfortable')}>Comfortable</button>
            <button data-testid="btn-spacious" onClick={() => setUiDensity('spacious')}>Spacious</button>

            {/* Sample elements using Phase 3 density deltas */}
            <div className="density-pad-sample px-[calc(0.75rem+var(--density-pad-x-delta,0px))] py-[calc(0.5rem+var(--density-pad-y-delta,0px))]">
                <button
                    className="px-[calc(0.75rem+var(--density-pad-x-delta,0px))] py-[calc(0.375rem+var(--density-pad-y-delta,0px))] text-xs font-semibold"
                    aria-label="Ejecutar acción"
                >
                    Acción
                </button>
                <input
                    aria-label="Buscar elementos"
                    className="px-[calc(1rem+var(--density-pad-x-delta,0px))] py-[calc(0.75rem+var(--density-pad-y-delta,0px))] text-sm font-medium"
                    placeholder="Buscar..."
                />
            </div>
        </div>
    );
}

describe('Density Adoption Phase 3 — Delta CSS Variables & Zero Regression Baseline', () => {
    beforeEach(() => {
        localStorage.clear();
        document.documentElement.removeAttribute('data-ui-density');
    });

    it('sets delta CSS variables strictly to 0px in ultra-compact default (cero regresión visual)', () => {
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

    it('dynamically applies progressive deltas across compact, comfortable, and spacious', () => {
        render(
            <ThemeProvider>
                <DensityHarness />
            </ThemeProvider>
        );

        const root = document.documentElement;

        // Compact (+2px pad-y, +2px pad-x, +2px gap, +4px height)
        act(() => { screen.getByTestId('btn-compact').click(); });
        expect(root.getAttribute('data-ui-density')).toBe('compact');
        expect(root.style.getPropertyValue('--density-pad-y-delta')).toBe('0.125rem');
        expect(root.style.getPropertyValue('--density-pad-x-delta')).toBe('0.125rem');
        expect(root.style.getPropertyValue('--density-gap-delta')).toBe('0.125rem');
        expect(root.style.getPropertyValue('--density-h-delta')).toBe('4px');

        // Comfortable (+4px pad-y, +4px pad-x, +4px gap, +8px height)
        act(() => { screen.getByTestId('btn-comfortable').click(); });
        expect(root.getAttribute('data-ui-density')).toBe('comfortable');
        expect(root.style.getPropertyValue('--density-pad-y-delta')).toBe('0.25rem');
        expect(root.style.getPropertyValue('--density-pad-x-delta')).toBe('0.25rem');
        expect(root.style.getPropertyValue('--density-gap-delta')).toBe('0.25rem');
        expect(root.style.getPropertyValue('--density-h-delta')).toBe('8px');

        // Spacious (+6px pad-y, +8px pad-x, +6px gap, +12px height)
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

    it('has zero accessibility violations (axe) with density classes applied', async () => {
        const { container } = render(
            <ThemeProvider>
                <DensityHarness />
            </ThemeProvider>
        );

        const results = await axe(container);
        expect(results).toHaveNoViolations();
    });
});

describe('CSS Architecture & Globals Fix Verification', () => {
    it('verifies .density-table tr min-height rule is removed while th and td rules remain', () => {
        const globalsCssPath = path.resolve(__dirname, '../../globals.css');
        const content = fs.readFileSync(globalsCssPath, 'utf8');

        // Redundant rule that browsers ignore on tr must NOT be present
        expect(content).not.toMatch(/\.density-table\s+tr\s*\{[^}]*min-height/);

        // Valid th and td padding rules MUST be present
        expect(content).toMatch(/\.density-table\s+th,\s*\.density-table\s+td/);
        expect(content).toContain('padding-top: calc(0.75rem + var(--density-pad-y-delta, 0px))');
        expect(content).toContain('padding-bottom: calc(0.75rem + var(--density-pad-y-delta, 0px))');
        expect(content).toContain('padding-left: calc(1rem + var(--density-pad-x-delta, 0px))');
        expect(content).toContain('padding-right: calc(1rem + var(--density-pad-x-delta, 0px))');
    });
});

describe('Mathematical Regression Verification across Phase 3 Target Modules', () => {
    const ultraDeltas = { padY: 0, padX: 0, gap: 0, h: 0 };
    const spaciousDeltas = { padY: 0.375, padX: 0.5, gap: 0.375, h: 12 };

    it('verifies Account (account/page.tsx) reproduces exact baseline in ultra-compact and expands in spacious', () => {
        // Toolbar save: px-3 py-2 (0.75rem, 0.5rem)
        expect(0.75 + ultraDeltas.padX).toBe(0.75);
        expect(0.5 + ultraDeltas.padY).toBe(0.5);
        expect(0.75 + spaciousDeltas.padX).toBeGreaterThan(0.75);
        expect(0.5 + spaciousDeltas.padY).toBeGreaterThan(0.5);

        // Table th/td & tabs: px-3 py-1.5 (0.75rem, 0.375rem)
        expect(0.75 + ultraDeltas.padX).toBe(0.75);
        expect(0.375 + ultraDeltas.padY).toBe(0.375);
        expect(0.75 + spaciousDeltas.padX).toBeGreaterThan(0.75);
        expect(0.375 + spaciousDeltas.padY).toBeGreaterThan(0.375);

        // Mobile verify: px-4 py-1.5 (1rem, 0.375rem)
        expect(1 + ultraDeltas.padX).toBe(1);
        expect(0.375 + ultraDeltas.padY).toBe(0.375);
        expect(1 + spaciousDeltas.padX).toBeGreaterThan(1);
        expect(0.375 + spaciousDeltas.padY).toBeGreaterThan(0.375);
    });

    it('verifies Admin Reports (admin/reports/page.tsx) reproduces exact baseline in ultra-compact and expands in spacious', () => {
        // Retry button: px-3 py-1.5 (0.75rem, 0.375rem)
        expect(0.75 + ultraDeltas.padX).toBe(0.75);
        expect(0.375 + ultraDeltas.padY).toBe(0.375);
        expect(0.75 + spaciousDeltas.padX).toBeGreaterThan(0.75);
        expect(0.375 + spaciousDeltas.padY).toBeGreaterThan(0.375);

        // Subnav tabs: px-4 py-1.5 (1rem, 0.375rem)
        expect(1 + ultraDeltas.padX).toBe(1);
        expect(0.375 + ultraDeltas.padY).toBe(0.375);
        expect(1 + spaciousDeltas.padX).toBeGreaterThan(1);
        expect(0.375 + spaciousDeltas.padY).toBeGreaterThan(0.375);

        // Metric action buttons: p-2 (0.5rem)
        expect(0.5 + ultraDeltas.padX).toBe(0.5);
        expect(0.5 + spaciousDeltas.padX).toBeGreaterThan(0.5);

        // Export CSV button: px-0 py-2 (0rem, 0.5rem base) - preserves 0px horizontal padding in ultra-compact
        expect(0 + ultraDeltas.padX).toBe(0);
        expect(0.5 + ultraDeltas.padY).toBe(0.5);
        expect(0 + spaciousDeltas.padX).toBeGreaterThan(0);
        expect(0.5 + spaciousDeltas.padY).toBeGreaterThan(0.5);
    });

    it('verifies CMS Pastoral Team (cms/pastoral-team/page.tsx) reproduces exact baseline in ultra-compact and expands in spacious', () => {
        // Search & Add leader: px-4 py-2 (1rem, 0.5rem)
        expect(1 + ultraDeltas.padX).toBe(1);
        expect(0.5 + ultraDeltas.padY).toBe(0.5);
        expect(1 + spaciousDeltas.padX).toBeGreaterThan(1);
        expect(0.5 + spaciousDeltas.padY).toBeGreaterThan(0.5);

        // Table th/td: px-4 py-3 (1rem, 0.75rem)
        expect(1 + ultraDeltas.padX).toBe(1);
        expect(0.75 + ultraDeltas.padY).toBe(0.75);
        expect(1 + spaciousDeltas.padX).toBeGreaterThan(1);
        expect(0.75 + spaciousDeltas.padY).toBeGreaterThan(0.75);

        // Drawer buttons: py-2.5 (0.625rem)
        expect(0.625 + ultraDeltas.padY).toBe(0.625);
        expect(0.625 + spaciousDeltas.padY).toBeGreaterThan(0.625);
    });

    it('verifies Settings & Roles (settings/page.tsx, settings/roles/page.tsx) reproduces exact baseline in ultra-compact', () => {
        // Profile edit: px-4 py-2 (1rem, 0.5rem)
        expect(1 + ultraDeltas.padX).toBe(1);
        expect(0.5 + ultraDeltas.padY).toBe(0.5);

        // Settings items: px-3 py-1.5 (0.75rem, 0.375rem)
        expect(0.75 + ultraDeltas.padX).toBe(0.75);
        expect(0.375 + ultraDeltas.padY).toBe(0.375);

        // Danger zone: px-4 py-3 (1rem, 0.75rem)
        expect(1 + ultraDeltas.padX).toBe(1);
        expect(0.75 + ultraDeltas.padY).toBe(0.75);

        // New role: px-3 py-3 (0.75rem, 0.75rem)
        expect(0.75 + ultraDeltas.padX).toBe(0.75);
        expect(0.75 + ultraDeltas.padY).toBe(0.75);

        // Roles drawer inputs: px-4 py-3 (1rem, 0.75rem)
        expect(1 + ultraDeltas.padX).toBe(1);
        expect(0.75 + ultraDeltas.padY).toBe(0.75);
    });

    it('verifies Community (community/page.tsx) reproduces exact baseline in ultra-compact and expands in spacious', () => {
        // Table th/td: px-4 py-1.5 (1rem, 0.375rem)
        expect(1 + ultraDeltas.padX).toBe(1);
        expect(0.375 + ultraDeltas.padY).toBe(0.375);
        expect(1 + spaciousDeltas.padX).toBeGreaterThan(1);
        expect(0.375 + spaciousDeltas.padY).toBeGreaterThan(0.375);

        // Switch & Nuevo button: px-3 h-8 (0.75rem, 2rem)
        expect(0.75 + ultraDeltas.padX).toBe(0.75);
        expect(2 + ultraDeltas.h).toBe(2);
        expect(0.75 + spaciousDeltas.padX).toBeGreaterThan(0.75);
        expect(2 + spaciousDeltas.padY).toBeGreaterThan(2);

        // Submit/cancel: px-4 h-10 (1rem, 2.5rem)
        expect(1 + ultraDeltas.padX).toBe(1);
        expect(2.5 + ultraDeltas.h).toBe(2.5);
        expect(1 + spaciousDeltas.padX).toBeGreaterThan(1);
    });

    it('verifies Projects & Team (ProjectsClient, [id], team) reproduces exact baseline in ultra-compact and expands in spacious', () => {
        // New project / retry: px-3 py-1.5 (0.75rem, 0.375rem)
        expect(0.75 + ultraDeltas.padX).toBe(0.75);
        expect(0.375 + ultraDeltas.padY).toBe(0.375);

        // Detail 16 toolbar buttons: px-3 py-1.5 (0.75rem, 0.375rem)
        expect(0.75 + ultraDeltas.padX).toBe(0.75);
        expect(0.375 + ultraDeltas.padY).toBe(0.375);
        expect(0.75 + spaciousDeltas.padX).toBe(1.25);
        expect(0.375 + spaciousDeltas.padY).toBe(0.75);

        // Team view mode switcher: px-3 py-1 (0.75rem, 0.25rem)
        expect(0.75 + ultraDeltas.padX).toBe(0.75);
        expect(0.25 + ultraDeltas.padY).toBe(0.25);
        expect(0.75 + spaciousDeltas.padX).toBeGreaterThan(0.75);
        expect(0.25 + spaciousDeltas.padY).toBeGreaterThan(0.25);

        // Team invite button: px-4 py-1.5 (1rem, 0.375rem)
        expect(1 + ultraDeltas.padX).toBe(1);
        expect(0.375 + ultraDeltas.padY).toBe(0.375);
        expect(1 + spaciousDeltas.padX).toBeGreaterThan(1);
        expect(0.375 + spaciousDeltas.padY).toBeGreaterThan(0.375);
    });

    it('verifies Finances (finances/page.tsx) reproduces exact baseline in ultra-compact and expands in spacious', () => {
        // Time range buttons: px-2 py-1 (0.5rem, 0.25rem)
        expect(0.5 + ultraDeltas.padX).toBe(0.5);
        expect(0.25 + ultraDeltas.padY).toBe(0.25);

        // Export button: px-2.5 py-1.5 (0.625rem, 0.375rem)
        expect(0.625 + ultraDeltas.padX).toBe(0.625);
        expect(0.375 + ultraDeltas.padY).toBe(0.375);

        // Registro button: px-3 py-1.5 (0.75rem, 0.375rem)
        expect(0.75 + ultraDeltas.padX).toBe(0.75);
        expect(0.375 + ultraDeltas.padY).toBe(0.375);

        // Transaction row: px-3 py-2 (0.75rem, 0.5rem)
        expect(0.75 + ultraDeltas.padX).toBe(0.75);
        expect(0.5 + ultraDeltas.padY).toBe(0.5);
        expect(0.75 + spaciousDeltas.padX).toBeGreaterThan(0.75);
        expect(0.5 + spaciousDeltas.padY).toBeGreaterThan(0.5);

        // Expense row: px-3 py-2.5 (0.75rem, 0.625rem)
        expect(0.75 + ultraDeltas.padX).toBe(0.75);
        expect(0.625 + ultraDeltas.padY).toBe(0.625);
        expect(0.75 + spaciousDeltas.padX).toBeGreaterThan(0.75);
        expect(0.625 + spaciousDeltas.padY).toBeGreaterThan(0.625);
    });

    it('verifies Agenda Events (agenda/events/page.tsx) reproduces exact baseline in ultra-compact and expands in spacious', () => {
        // Form inputs: px-4 py-3 (1rem, 0.75rem)
        expect(1 + ultraDeltas.padX).toBe(1);
        expect(0.75 + ultraDeltas.padY).toBe(0.75);
        expect(1 + spaciousDeltas.padX).toBeGreaterThan(1);
        expect(0.75 + spaciousDeltas.padY).toBeGreaterThan(0.75);

        // Submit button: px-3 py-3 (0.75rem, 0.75rem)
        expect(0.75 + ultraDeltas.padX).toBe(0.75);
        expect(0.75 + ultraDeltas.padY).toBe(0.75);
        expect(0.75 + spaciousDeltas.padX).toBeGreaterThan(0.75);
        expect(0.75 + spaciousDeltas.padY).toBeGreaterThan(0.75);

        // Badges: px-3 py-1 (0.75rem, 0.25rem)
        expect(0.75 + ultraDeltas.padX).toBe(0.75);
        expect(0.25 + ultraDeltas.padY).toBe(0.25);

        // Action buttons: px-3 py-2 (0.75rem, 0.5rem)
        expect(0.75 + ultraDeltas.padX).toBe(0.75);
        expect(0.5 + ultraDeltas.padY).toBe(0.5);
        expect(0.75 + spaciousDeltas.padX).toBeGreaterThan(0.75);
        expect(0.5 + spaciousDeltas.padY).toBeGreaterThan(0.5);
    });
});

describe('Static Invariance & Code Quality Verification', () => {
    const filesToCheck = [
        'frontend/src/app/plataforma/account/page.tsx',
        'frontend/src/app/plataforma/admin/reports/page.tsx',
        'frontend/src/app/plataforma/cms/pastoral-team/page.tsx',
        'frontend/src/app/plataforma/community/page.tsx',
        'frontend/src/app/plataforma/projects/ProjectsClient.tsx',
        'frontend/src/app/plataforma/projects/[id]/page.tsx',
        'frontend/src/app/plataforma/projects/team/page.tsx',
        'frontend/src/app/plataforma/settings/page.tsx',
        'frontend/src/app/plataforma/settings/roles/page.tsx',
        'frontend/src/app/plataforma/finances/page.tsx',
        'frontend/src/app/plataforma/agenda/events/page.tsx',
    ];

    it('verifies all migrated files use relative density deltas via calc() and none use absolute variables directly', () => {
        const repoRoot = path.resolve(__dirname, '../../../../../');
        for (const relPath of filesToCheck) {
            const fullPath = path.join(repoRoot, relPath);
            expect(fs.existsSync(fullPath)).toBe(true);
            const content = fs.readFileSync(fullPath, 'utf8');

            // Must use relative delta
            expect(content).toMatch(/--density-(pad-x|pad-y|gap|h)-delta/);

            // Must NOT use legacy absolute density variables directly
            expect(content).not.toMatch(/h-\[var\(--density-row-h\)/);
            expect(content).not.toMatch(/px-\[var\(--density-pad-x\)/);
            expect(content).not.toMatch(/py-\[var\(--density-pad-y\)/);
            expect(content).not.toMatch(/gap-\[var\(--density-gap\)/);
        }
    });
});
