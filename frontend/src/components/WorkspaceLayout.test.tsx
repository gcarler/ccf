import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import WorkspaceLayout from './WorkspaceLayout';
import WorkspaceMiniSidebar from './WorkspaceMiniSidebar';
import { SidebarLayerProvider, useSidebarLayers } from '@/context/SidebarLayerContext';

const navigationState = vi.hoisted(() => ({
    pathname: '/plataforma/projects',
    push: vi.fn(),
}));

vi.mock('next/navigation', () => ({
    usePathname: () => navigationState.pathname,
    useRouter: () => ({
        push: navigationState.push,
    }),
}));

vi.mock('@/context/AuthContext', () => ({
    useAuth: () => ({
        user: { id: 'usr-1', email: 'test@ccf.com', first_name: 'Carlos', role: 'admin' },
        isAuthenticated: true,
        loading: false,
        hasModuleAccess: () => true,
        hasPermission: () => true,
        logout: vi.fn(),
    }),
    useOptionalAuth: () => ({
        user: { id: 'usr-1', email: 'test@ccf.com', first_name: 'Carlos', role: 'admin' },
        isAuthenticated: true,
        loading: false,
        hasModuleAccess: () => true,
        hasPermission: () => true,
        logout: vi.fn(),
    }),
}));

vi.mock('@/context/CommandCenterContext', () => ({
    useRegisterCommands: vi.fn(),
}));

vi.mock('@/context/CreationContext', () => ({
    useCreation: () => ({
        isModalOpen: false,
        closeModal: vi.fn(),
        defaultType: 'task',
        openModal: vi.fn(),
    }),
}));

vi.mock('@/components/ui/UniversalCreationDrawer', () => ({ default: () => null }));
vi.mock('@/components/ui/AppearanceDrawer', () => ({ default: () => null }));
vi.mock('@/components/ui/ThemeToggle', () => ({ default: () => null }));
vi.mock('@/components/ui/MeshChat', () => ({ default: () => null }));
vi.mock('@/components/ui/NotificationBell', () => ({ default: () => null }));
vi.mock('@/components/WorkspaceInbox', () => ({ default: () => null }));

function LayerStatusConsumer() {
    const { layers } = useSidebarLayers();
    return (
        <div>
            <span data-testid="layer-s1-status">{layers.S1 ? 'open' : 'closed'}</span>
            <span data-testid="layer-s2-status">{layers.S2 ? 'open' : 'closed'}</span>
        </div>
    );
}

describe('WorkspaceLayout and WorkspaceMiniSidebar S2 behavior', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        localStorage.clear();
        navigationState.pathname = '/plataforma/projects';
    });

    it('opens S1 and S2 by default when entering the projects module', async () => {
        navigationState.pathname = '/plataforma/projects';

        render(
            <SidebarLayerProvider>
                <WorkspaceLayout
                    sidebarTitle="Proyectos"
                    sidebarSections={[{ title: 'General', items: [{ id: 'all', label: 'Todos', href: '/plataforma/projects' }] }]}
                >
                    <LayerStatusConsumer />
                    <div>Contenido de Proyectos</div>
                </WorkspaceLayout>
            </SidebarLayerProvider>
        );

        expect(screen.getByTestId('layer-s1-status')).toHaveTextContent('open');
        expect(screen.getByTestId('layer-s2-status')).toHaveTextContent('open');
    });

    it('guarantees S2 opens by default for projects even if localStorage had workspace:s2:projects = hidden', async () => {
        navigationState.pathname = '/plataforma/projects';
        localStorage.setItem('workspace:s2:projects', 'hidden');

        render(
            <SidebarLayerProvider>
                <WorkspaceLayout
                    sidebarTitle="Proyectos"
                    sidebarSections={[{ title: 'General', items: [{ id: 'all', label: 'Todos', href: '/plataforma/projects' }] }]}
                >
                    <LayerStatusConsumer />
                    <div>Contenido de Proyectos</div>
                </WorkspaceLayout>
            </SidebarLayerProvider>
        );

        expect(screen.getByTestId('layer-s2-status')).toHaveTextContent('open');
    });

    it('respects stored hidden state for other modules like crm', async () => {
        navigationState.pathname = '/plataforma/crm';
        localStorage.setItem('workspace:s2:crm', 'hidden');

        render(
            <SidebarLayerProvider>
                <WorkspaceLayout
                    sidebarTitle="Consolidación"
                    sidebarSections={[{ title: 'General', items: [{ id: 'all', label: 'Todos', href: '/plataforma/crm' }] }]}
                >
                    <LayerStatusConsumer />
                    <div>Contenido de CRM</div>
                </WorkspaceLayout>
            </SidebarLayerProvider>
        );

        expect(screen.getByTestId('layer-s2-status')).toHaveTextContent('closed');
    });

    it('allows manually collapsing and expanding S2 during the session without immediately overriding it', async () => {
        const user = userEvent.setup();
        navigationState.pathname = '/plataforma/projects';

        render(
            <SidebarLayerProvider>
                <WorkspaceLayout
                    sidebarTitle="Proyectos"
                    sidebarSections={[{ title: 'General', items: [{ id: 'all', label: 'Todos', href: '/plataforma/projects' }] }]}
                >
                    <LayerStatusConsumer />
                    <div>Contenido de Proyectos</div>
                </WorkspaceLayout>
            </SidebarLayerProvider>
        );

        expect(screen.getByTestId('layer-s2-status')).toHaveTextContent('open');

        // Toggle S2 via collapse button
        const toggleBtn = screen.getByRole('button', { name: /Colapsar sidebar|Contraer sidebar/i });
        await user.click(toggleBtn);

        // Now S2 is closed and remains closed while in the view
        expect(screen.getByTestId('layer-s2-status')).toHaveTextContent('closed');

        // Toggle back to expand
        const expandBtn = screen.getByRole('button', { name: /Expandir sidebar/i });
        await user.click(expandBtn);

        expect(screen.getByTestId('layer-s2-status')).toHaveTextContent('open');
    });

    it('reactively opens S2 when clicking the Proyectos navigation item in WorkspaceMiniSidebar', async () => {
        const user = userEvent.setup();

        function MiniSidebarWrapper() {
            const { layers, closeLayer } = useSidebarLayers();
            return (
                <div>
                    <span data-testid="wrapper-s2-status">{layers.S2 ? 'open' : 'closed'}</span>
                    <button type="button" onClick={() => closeLayer('S2')}>Cerrar S2 Manual</button>
                    <WorkspaceMiniSidebar onHide={vi.fn()} />
                </div>
            );
        }

        render(
            <SidebarLayerProvider>
                <MiniSidebarWrapper />
            </SidebarLayerProvider>
        );

        // Manually close S2
        await user.click(screen.getByRole('button', { name: 'Cerrar S2 Manual' }));
        expect(screen.getByTestId('wrapper-s2-status')).toHaveTextContent('closed');

        // Click Proyectos in WorkspaceMiniSidebar
        const projectsNav = screen.getByRole('link', { name: 'Proyectos' });
        fireEvent.click(projectsNav);

        // S2 should now be opened reactively
        expect(screen.getByTestId('wrapper-s2-status')).toHaveTextContent('open');
    });
});
