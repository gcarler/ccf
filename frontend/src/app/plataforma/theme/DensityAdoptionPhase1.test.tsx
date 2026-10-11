import React from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { axe } from 'jest-axe';
import { ThemeProvider, useTheme } from './ThemeContext';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { DSSectionHeader } from '@/design/components/DSSectionHeader';
import RightPanel from '@/components/ui/RightPanel';
import WorkspaceInbox from '@/components/WorkspaceInbox';
import AttendanceDrawer from '@/app/plataforma/evangelism/strategies/[id]/panels/AttendanceDrawer';

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
                    { persona_id: 'p1', name: 'Juan Pérez', role: 'miembro', role_label: 'Miembro', status: 'present', notes: '' },
                ]}
                setPersonas={vi.fn()}
                saving={false}
                canManage={true}
                onSave={vi.fn()}
                onVisitorCreated={vi.fn()}
                getRoleColor={() => 'bg-[hsl(var(--surface-2))]'}
                getRoleLabel={(r) => r}
            />
        </div>
    );
}

describe('Density Adoption Phase 1 — Shell and Core Modules', () => {
    beforeEach(() => {
        localStorage.clear();
        document.documentElement.removeAttribute('data-ui-density');
        document.documentElement.removeAttribute('data-theme');
        document.documentElement.className = '';
        vi.clearAllMocks();
    });

    it('renders global shell and adoption harness in ultra-compact default density', () => {
        const { container } = render(
            <ThemeProvider>
                <AdoptionHarness />
            </ThemeProvider>
        );

        const root = document.documentElement;
        expect(root.getAttribute('data-ui-density')).toBe('ultra-compact');
        expect(root.style.getPropertyValue('--density-row-h')).toBe('28px');
        expect(root.style.getPropertyValue('--density-pad-x')).toBe('0.5rem');
        expect(root.style.getPropertyValue('--density-pad-y')).toBe('0.125rem');
        expect(root.style.getPropertyValue('--density-gap')).toBe('0.25rem');

        // WorkspaceToolbar element exists with data-workspace-toolbar
        const toolbar = container.querySelector('[data-workspace-toolbar]');
        expect(toolbar).toBeInTheDocument();
        expect(toolbar?.className).toContain('min-h-[calc(var(--density-row-h,32px)+8px)]');

        // Section header renders title and actions
        expect(screen.getByText('Módulo CMS')).toBeInTheDocument();
        expect(screen.getByText('Nueva Página')).toBeInTheDocument();
    });

    it('dynamically adapts CSS variables when cycling through compact, comfortable, and spacious', () => {
        render(
            <ThemeProvider>
                <AdoptionHarness />
            </ThemeProvider>
        );

        const root = document.documentElement;

        // 1. Compact
        act(() => {
            screen.getByTestId('set-compact').click();
        });
        expect(root.getAttribute('data-ui-density')).toBe('compact');
        expect(root.style.getPropertyValue('--density-row-h')).toBe('36px');
        expect(root.style.getPropertyValue('--density-pad-x')).toBe('0.75rem');
        expect(root.style.getPropertyValue('--density-pad-y')).toBe('0.375rem');
        expect(root.style.getPropertyValue('--density-gap')).toBe('0.5rem');

        // 2. Comfortable
        act(() => {
            screen.getByTestId('set-comfortable').click();
        });
        expect(root.getAttribute('data-ui-density')).toBe('comfortable');
        expect(root.style.getPropertyValue('--density-row-h')).toBe('44px');
        expect(root.style.getPropertyValue('--density-pad-x')).toBe('1rem');
        expect(root.style.getPropertyValue('--density-pad-y')).toBe('0.625rem');
        expect(root.style.getPropertyValue('--density-gap')).toBe('0.75rem');

        // 3. Spacious
        act(() => {
            screen.getByTestId('set-spacious').click();
        });
        expect(root.getAttribute('data-ui-density')).toBe('spacious');
        expect(root.style.getPropertyValue('--density-row-h')).toBe('52px');
        expect(root.style.getPropertyValue('--density-pad-x')).toBe('1.25rem');
        expect(root.style.getPropertyValue('--density-pad-y')).toBe('0.875rem');
        expect(root.style.getPropertyValue('--density-gap')).toBe('1rem');

        // 4. Return to ultra-compact
        act(() => {
            screen.getByTestId('set-ultra').click();
        });
        expect(root.getAttribute('data-ui-density')).toBe('ultra-compact');
        expect(root.style.getPropertyValue('--density-row-h')).toBe('28px');
    });

    it('RightPanel and WorkspaceInbox contain density responsive classes', () => {
        const { container } = render(
            <ThemeProvider>
                <AdoptionHarness />
            </ThemeProvider>
        );

        // RightPanel header has density row height and padding
        const rightPanelHeader = container.querySelector('[role="dialog"] > div');
        expect(rightPanelHeader?.className).toContain('min-h-[var(--density-row-h,2.25rem)]');

        // WorkspaceInbox header has density row height
        const inboxHeader = container.querySelector('header');
        expect(inboxHeader?.className).toContain('min-h-[calc(var(--density-row-h,32px)+4px)]');
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
