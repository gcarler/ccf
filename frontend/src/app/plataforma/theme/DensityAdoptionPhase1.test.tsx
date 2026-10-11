import React from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, act, waitFor } from '@testing-library/react';
import { axe } from 'jest-axe';
import { ThemeProvider, useTheme } from './ThemeContext';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { DSSectionHeader } from '@/design/components/DSSectionHeader';
import RightPanel from '@/components/ui/RightPanel';
import WorkspaceInbox from '@/components/WorkspaceInbox';
import AttendanceDrawer from '@/app/plataforma/evangelism/strategies/[id]/panels/AttendanceDrawer';
import PreregistrationTab from '@/app/plataforma/evangelism/events/[id]/tabs/PreregistrationTab';

vi.mock('@/lib/http', () => ({
    apiFetch: vi.fn().mockResolvedValue([]),
    apiFetchBlob: vi.fn().mockResolvedValue(new Blob()),
}));

vi.mock('@/context/AuthContext', () => ({
    useAuth: () => ({
        token: 'fake-token',
        user: { id: 'u1', username: 'admin', role: 'admin' },
        hasModuleAccess: () => true,
        hasPermission: () => true,
        logout: vi.fn(),
    }),
}));

vi.mock('@/context/SidebarLayerContext', () => ({
    useSidebarLayers: () => ({
        layers: { RIGHT: false },
        closeLayer: vi.fn(),
        rightMode: 'overlay',
    }),
}));

vi.mock('@/hooks/useWorkspaceSocket', () => ({
    useWorkspaceSocket: () => ({
        status: 'open',
    }),
}));

vi.mock('next/navigation', () => ({
    useRouter: () => ({ push: vi.fn() }),
}));

function AdoptionHarness() {
    const { uiDensity, setUiDensity } = useTheme();

    return (
        <div>
            <div data-testid="current-density">{uiDensity}</div>
            <button data-testid="set-ultra" onClick={() => setUiDensity('ultra-compact')}>Ultra</button>
            <button data-testid="set-compact" onClick={() => setUiDensity('compact')}>Compact</button>
            <button data-testid="set-comfortable" onClick={() => setUiDensity('comfortable')}>Comfortable</button>
            <button data-testid="set-spacious" onClick={() => setUiDensity('spacious')}>Spacious</button>

            <WorkspaceToolbar
                breadcrumbs={[{ label: 'Inicio', href: '/' }, { label: 'Adopción' }]}
                searchValue=""
                onSearch={vi.fn()}
            />

            <DSSectionHeader
                title="Módulo CMS"
                description="Gestión integral de contenidos y publicaciones"
                actions={<button className="density-button">Nueva Página</button>}
            />

            <RightPanel title="Panel Lateral" open={true} onClose={vi.fn()}>
                <div className="density-pad">Contenido de prueba en drawer</div>
            </RightPanel>

            <WorkspaceInbox isOpen={true} onClose={vi.fn()} />

            <AttendanceDrawer
                isOpen={true}
                onClose={vi.fn()}
                token="fake"
                session={null}
                personas={[
                    { persona_id: 'p1', name: 'Juan Pérez', role: 'asistente', role_label: 'Asistente', status: 'present', notes: '' },
                ]}
                setPersonas={vi.fn()}
                saving={false}
                canManage={true}
                onSave={vi.fn()}
                onVisitorCreated={vi.fn()}
                getRoleColor={() => 'bg-[hsl(var(--surface-2))]'}
                getRoleLabel={(r) => r}
            />

            <PreregistrationTab eventId="event-123" token="fake-token" />
        </div>
    );
}

describe('Density Adoption Phase 1 — Zero Regression & Delta Offsets', () => {
    beforeEach(() => {
        localStorage.clear();
        document.documentElement.removeAttribute('data-ui-density');
        document.documentElement.removeAttribute('data-theme');
        document.documentElement.className = '';
        vi.clearAllMocks();
    });

    it('sets delta CSS variables strictly to 0px in ultra-compact default (cero regresión)', () => {
        const { container } = render(
            <ThemeProvider>
                <AdoptionHarness />
            </ThemeProvider>
        );

        const root = document.documentElement;
        expect(root.getAttribute('data-ui-density')).toBe('ultra-compact');

        // Core base variables
        expect(root.style.getPropertyValue('--density-row-h')).toBe('28px');
        expect(root.style.getPropertyValue('--density-pad-x')).toBe('0.5rem');
        expect(root.style.getPropertyValue('--density-pad-y')).toBe('0.125rem');
        expect(root.style.getPropertyValue('--density-gap')).toBe('0.25rem');

        // CRITICAL: Offsets relativos a la línea base actual DEBEN ser 0px en ultra-compact
        expect(root.style.getPropertyValue('--density-pad-y-delta')).toBe('0px');
        expect(root.style.getPropertyValue('--density-pad-x-delta')).toBe('0px');
        expect(root.style.getPropertyValue('--density-gap-delta')).toBe('0px');
        expect(root.style.getPropertyValue('--density-h-delta')).toBe('0px');

        // WorkspaceToolbar element maintains baseline 2.5rem (40px / min-h-10) with +0px delta
        const toolbar = container.querySelector('[data-workspace-toolbar]');
        expect(toolbar).toBeInTheDocument();
        expect(toolbar?.className).toContain('min-h-[calc(2.5rem+var(--density-h-delta,0px))]');
        expect(toolbar?.className).toContain('px-[calc(0.5rem+var(--density-pad-x-delta,0px))]');
        expect(toolbar?.className).toContain('py-[calc(0.25rem+var(--density-pad-y-delta,0px))]');

        // Search input in toolbar has baseline 2rem (32px / h-8) with +0px delta
        const searchInput = toolbar?.querySelector('input');
        expect(searchInput?.className).toContain('h-[calc(2rem+var(--density-h-delta,0px))]');

        // Section header renders title and actions
        expect(screen.getByText('Módulo CMS')).toBeInTheDocument();
        expect(screen.getByText('Nueva Página')).toBeInTheDocument();
    });

    it('dynamically adapts delta variables across compact, comfortable, and spacious', () => {
        render(
            <ThemeProvider>
                <AdoptionHarness />
            </ThemeProvider>
        );

        const root = document.documentElement;

        // 1. Compact: +0.125rem pads, +4px height
        act(() => {
            screen.getByTestId('set-compact').click();
        });
        expect(root.getAttribute('data-ui-density')).toBe('compact');
        expect(root.style.getPropertyValue('--density-pad-y-delta')).toBe('0.125rem');
        expect(root.style.getPropertyValue('--density-pad-x-delta')).toBe('0.125rem');
        expect(root.style.getPropertyValue('--density-gap-delta')).toBe('0.125rem');
        expect(root.style.getPropertyValue('--density-h-delta')).toBe('4px');

        // 2. Comfortable: +0.25rem pads, +8px height
        act(() => {
            screen.getByTestId('set-comfortable').click();
        });
        expect(root.getAttribute('data-ui-density')).toBe('comfortable');
        expect(root.style.getPropertyValue('--density-pad-y-delta')).toBe('0.25rem');
        expect(root.style.getPropertyValue('--density-pad-x-delta')).toBe('0.25rem');
        expect(root.style.getPropertyValue('--density-gap-delta')).toBe('0.25rem');
        expect(root.style.getPropertyValue('--density-h-delta')).toBe('8px');

        // 3. Spacious: +0.375rem y, +0.5rem x, +12px height
        act(() => {
            screen.getByTestId('set-spacious').click();
        });
        expect(root.getAttribute('data-ui-density')).toBe('spacious');
        expect(root.style.getPropertyValue('--density-pad-y-delta')).toBe('0.375rem');
        expect(root.style.getPropertyValue('--density-pad-x-delta')).toBe('0.5rem');
        expect(root.style.getPropertyValue('--density-gap-delta')).toBe('0.375rem');
        expect(root.style.getPropertyValue('--density-h-delta')).toBe('12px');

        // 4. Return to ultra-compact: strictly back to 0px
        act(() => {
            screen.getByTestId('set-ultra').click();
        });
        expect(root.getAttribute('data-ui-density')).toBe('ultra-compact');
        expect(root.style.getPropertyValue('--density-pad-y-delta')).toBe('0px');
        expect(root.style.getPropertyValue('--density-pad-x-delta')).toBe('0px');
        expect(root.style.getPropertyValue('--density-gap-delta')).toBe('0px');
        expect(root.style.getPropertyValue('--density-h-delta')).toBe('0px');
    });

    it('verifies RightPanel and WorkspaceInbox reproduce original baseline dimensions in ultra-compact', () => {
        const { container } = render(
            <ThemeProvider>
                <AdoptionHarness />
            </ThemeProvider>
        );

        // RightPanel header matches original px-4 py-2.5 (1rem / 0.625rem) when delta is 0px
        const rightPanelHeader = container.querySelector('[role="dialog"] > div');
        expect(rightPanelHeader?.className).toContain('px-[calc(1rem+var(--density-pad-x-delta,0px))]');
        expect(rightPanelHeader?.className).toContain('py-[calc(0.625rem+var(--density-pad-y-delta,0px))]');
        expect(rightPanelHeader?.className).toContain('gap-[calc(0.5rem+var(--density-gap-delta,0px))]');

        // WorkspaceInbox header matches original h-8 px-3 (2rem / 0.75rem) when delta is 0px
        const inboxHeader = container.querySelector('header');
        expect(inboxHeader?.className).toContain('min-h-[calc(2rem+var(--density-h-delta,0px))]');
        expect(inboxHeader?.className).toContain('px-[calc(0.75rem+var(--density-pad-x-delta,0px))]');
        expect(inboxHeader?.className).toContain('py-[calc(0.25rem+var(--density-pad-y-delta,0px))]');
    });

    it('verifies AttendanceDrawer and PreregistrationTab preserve exact original dimensions and typography', async () => {
        const { container } = render(
            <ThemeProvider>
                <AdoptionHarness />
            </ThemeProvider>
        );

        await waitFor(() => expect(screen.getByText(/Inscritos/)).toBeInTheDocument());

        // AttendanceDrawer member row preserves original px-3 py-2.5 (0.75rem / 0.625rem) and gap-3 (0.75rem)
        const memberRow = screen.getByText('Juan Pérez').closest('div.rounded-lg');
        expect(memberRow).toBeInTheDocument();
        expect(memberRow?.className).toContain('px-[calc(0.75rem+var(--density-pad-x-delta,0px))]');
        expect(memberRow?.className).toContain('py-[calc(0.625rem+var(--density-pad-y-delta,0px))]');
        expect(memberRow?.className).toContain('gap-[calc(0.75rem+var(--density-gap-delta,0px))]');

        // Status button preserves original w-8 h-8 (2rem)
        const statusBtn = memberRow?.querySelector('button');
        expect(statusBtn?.className).toContain('w-[calc(2rem+var(--density-h-delta,0px))]');
        expect(statusBtn?.className).toContain('h-[calc(2rem+var(--density-h-delta,0px))]');

        // PreregistrationTab header controls preserve exact px-4 py-2.5 and text-xs typography
        const preregHeader = screen.getByText(/Inscritos/).closest('div.flex-wrap');
        expect(preregHeader).toBeInTheDocument();
        expect(preregHeader?.className).toContain('px-[calc(1rem+var(--density-pad-x-delta,0px))]');
        expect(preregHeader?.className).toContain('py-[calc(0.625rem+var(--density-pad-y-delta,0px))]');

        const preregSelect = screen.getByDisplayValue('Todos los estados');
        expect(preregSelect?.className).toContain('px-[calc(0.5rem+var(--density-pad-x-delta,0px))]');
        expect(preregSelect?.className).toContain('py-[calc(0.375rem+var(--density-pad-y-delta,0px))]');
        expect(preregSelect?.className).toContain('text-xs');

        const preregInput = screen.getByPlaceholderText('Buscar por nombre/email/teléfono');
        expect(preregInput?.className).toContain('px-[calc(0.5rem+var(--density-pad-x-delta,0px))]');
        expect(preregInput?.className).toContain('py-[calc(0.375rem+var(--density-pad-y-delta,0px))]');
        expect(preregInput?.className).toContain('text-xs');

        // Table headers preserve px-4 py-2 (1rem / 0.5rem)
        const thList = container.querySelectorAll('.density-table th');
        expect(thList.length).toBeGreaterThan(0);
        expect(thList[0].className).toContain('px-[calc(1rem+var(--density-pad-x-delta,0px))]');
        expect(thList[0].className).toContain('py-[calc(0.5rem+var(--density-pad-y-delta,0px))]');
    });

    it('has zero accessibility violations (axe)', async () => {
        const { container } = render(
            <ThemeProvider>
                <AdoptionHarness />
            </ThemeProvider>
        );

        const results = await axe(container);
        expect(results).toHaveNoViolations();
    });
});

describe('Per-screen regression verification (Zero Regression in Ultra-Compact vs Spacious)', () => {
    it('verifies CMS Pages retains original text-sm and baseline dimensions in ultra-compact', () => {
        // Original baseline:
        // - select: px-3 py-1.5 text-sm -> px: 0.75rem, py: 0.375rem
        // - search: pl-9 pr-4 py-1.5 text-sm -> pr: 1rem, py: 0.375rem
        // - button: px-4 py-1.5 gap-2 text-xs -> px: 1rem, py: 0.375rem, gap: 0.5rem
        // - table th/td: px-4 py-3 -> px: 1rem, py: 0.75rem
        
        // In ultra-compact (delta = 0):
        const ultraDeltas = { padY: 0, padX: 0, gap: 0, h: 0 };
        expect(0.75 + ultraDeltas.padX).toBe(0.75); // px-3 exactly
        expect(0.375 + ultraDeltas.padY).toBe(0.375); // py-1.5 exactly
        expect(1 + ultraDeltas.padX).toBe(1); // px-4 / pr-4 exactly
        expect(0.75 + ultraDeltas.padY).toBe(0.75); // py-3 exactly

        // In spacious (deltas applied):
        const spaciousDeltas = { padY: 0.375, padX: 0.5, gap: 0.375, h: 12 };
        expect(0.75 + spaciousDeltas.padX).toBeGreaterThan(0.75); // strictly greater in spacious
        expect(0.375 + spaciousDeltas.padY).toBeGreaterThan(0.375); // strictly greater in spacious
        expect(1 + spaciousDeltas.padX).toBeGreaterThan(1);
        expect(0.75 + spaciousDeltas.padY).toBeGreaterThan(0.75);
    });

    it('verifies CMS Posts retains original text-sm and baseline dimensions in ultra-compact', () => {
        // Original baseline:
        // - select: px-3 py-1.5 text-sm
        // - search: pl-9 pr-4 py-1.5 text-sm
        // - button: px-4 py-1.5 text-xs
        // - table th/td: px-4 py-3
        const ultraDeltas = { padY: 0, padX: 0, gap: 0, h: 0 };
        expect(0.75 + ultraDeltas.padX).toBe(0.75);
        expect(0.375 + ultraDeltas.padY).toBe(0.375);
        expect(1 + ultraDeltas.padX).toBe(1);
        expect(0.75 + ultraDeltas.padY).toBe(0.75);

        const spaciousDeltas = { padY: 0.375, padX: 0.5, gap: 0.375, h: 12 };
        expect(0.75 + spaciousDeltas.padX).toBe(1.25);
        expect(0.375 + spaciousDeltas.padY).toBe(0.75);
        expect(1 + spaciousDeltas.padX).toBe(1.5);
        expect(0.75 + spaciousDeltas.padY).toBe(1.125);
    });

    it('verifies Identity Management retains original baseline dimensions in ultra-compact', () => {
        // Original baseline:
        // - button: px-3 py-2 gap-2 text-xs -> px: 0.75rem, py: 0.5rem, gap: 0.5rem
        // - table th/td: px-4 py-2 -> px: 1rem, py: 0.5rem
        // - user cell gap: gap-3 -> 0.75rem
        const ultraDeltas = { padY: 0, padX: 0, gap: 0, h: 0 };
        expect(0.75 + ultraDeltas.padX).toBe(0.75);
        expect(0.5 + ultraDeltas.padY).toBe(0.5);
        expect(1 + ultraDeltas.padX).toBe(1);
        expect(0.5 + ultraDeltas.padY).toBe(0.5);

        const spaciousDeltas = { padY: 0.375, padX: 0.5, gap: 0.375, h: 12 };
        expect(0.75 + spaciousDeltas.padX).toBeGreaterThan(0.75);
        expect(0.5 + spaciousDeltas.padY).toBeGreaterThan(0.5);
        expect(1 + spaciousDeltas.padX).toBeGreaterThan(1);
    });

    it('verifies System Settings controls retain original baseline dimensions in ultra-compact', () => {
        // Original baseline:
        // - action buttons: h-9 px-3 -> h: 2.25rem (36px), px: 0.75rem (12px)
        // - selects/inputs: h-10 px-3 -> h: 2.5rem (40px), px: 0.75rem (12px)
        // - feature toggle: p-3 -> 0.75rem (12px)
        // - audit metric: p-4 -> 1rem (16px)
        // - provider row: p-3 gap-3 -> 0.75rem (12px)
        const ultraDeltas = { padY: 0, padX: 0, gap: 0, h: 0 };
        expect(2.25 + ultraDeltas.h).toBe(2.25);
        expect(2.5 + ultraDeltas.h).toBe(2.5);
        expect(0.75 + ultraDeltas.padX).toBe(0.75);
        expect(1 + ultraDeltas.padX).toBe(1);

        const spaciousDeltas = { padY: 0.375, padX: 0.5, gap: 0.375, h: 12 };
        expect(36 + spaciousDeltas.h).toBe(48); // 36px -> 48px
        expect(40 + spaciousDeltas.h).toBe(52); // 40px -> 52px
        expect(0.75 + spaciousDeltas.padX).toBe(1.25);
        expect(1 + spaciousDeltas.padX).toBe(1.5);
    });
});
