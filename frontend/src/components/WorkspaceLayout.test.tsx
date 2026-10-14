import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
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

vi.mock('next/link', () => ({
    default: ({ href, children, onClick, prefetch: _prefetch, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement> & { href: string; prefetch?: boolean }) => (
        <a href={href} onClick={(event) => { onClick?.(event); event.preventDefault(); }} {...props}>{children}</a>
    ),
}));
vi.mock('@/design', () => ({
    DSTooltip: ({ children }: { children: React.ReactNode }) => <>{children}</>,
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
    const { layers, openLayer, closeLayer } = useSidebarLayers();
    return (
        <div>
            <span data-testid="layer-s1-status">{layers.S1 ? 'open' : 'closed'}</span>
            <span data-testid="layer-s2-status">{layers.S2 ? 'open' : 'closed'}</span>
            <span data-testid="layer-right-status">{layers.RIGHT ? 'open' : 'closed'}</span>
            <button type="button" onClick={() => openLayer('RIGHT')}>Open RIGHT layer</button>
            <button type="button" onClick={() => closeLayer('S2')}>Close S2 layer</button>
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

    it('ignores a persisted projects focus mode and restores a mini S2 width on entry', () => {
        navigationState.pathname = '/plataforma/projects';
        localStorage.setItem('workspace:focus:projects', '1');
        localStorage.setItem('workspace:s2:projects', 'hidden');
        localStorage.setItem('s2Width', '64');

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
        expect(localStorage.getItem('workspace:focus:projects')).toBe('0');
        expect(localStorage.getItem('workspace:s2:projects')).toBe('visible');
        expect(localStorage.getItem('s2Width')).toBe('280');
    });

    it.each(['not-a-number', '481'])('restores an invalid projects S2 width (%s) to its default', (savedWidth) => {
        navigationState.pathname = '/plataforma/projects';
        localStorage.setItem('s2Width', savedWidth);

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

        expect(localStorage.getItem('s2Width')).toBe('280');
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

    it('opens S2 on every Projects route transition from a closed module and keeps same-route manual close', async () => {
        const user = userEvent.setup();
        navigationState.pathname = '/plataforma/crm';
        localStorage.setItem('workspace:s2:crm', 'hidden');
        localStorage.setItem('s2Width', '64');
        const props = {
            sidebarTitle: 'Proyectos',
            sidebarSections: [{ title: 'General', items: [{ id: 'all', label: 'Todos', href: '/plataforma/projects' }] }],
        };
        const { rerender } = render(
            <SidebarLayerProvider>
                <WorkspaceLayout {...props}><LayerStatusConsumer /><div>Contenido</div></WorkspaceLayout>
            </SidebarLayerProvider>,
        );
        expect(screen.getByTestId('layer-s2-status')).toHaveTextContent('closed');

        navigationState.pathname = '/plataforma/projects/tasks';
        rerender(
            <SidebarLayerProvider>
                <WorkspaceLayout {...props}><LayerStatusConsumer /><div>Contenido</div></WorkspaceLayout>
            </SidebarLayerProvider>,
        );
        expect(screen.getByTestId('layer-s1-status')).toHaveTextContent('open');
        expect(screen.getByTestId('layer-s2-status')).toHaveTextContent('open');
        expect(localStorage.getItem('workspace:s2:projects')).toBe('visible');
        expect(localStorage.getItem('workspace:focus:projects')).toBe('0');
        expect(localStorage.getItem('s2Width')).toBe('280');

        await user.click(screen.getByRole('button', { name: 'Close S2 layer' }));
        expect(screen.getByTestId('layer-s2-status')).toHaveTextContent('closed');
        rerender(
            <SidebarLayerProvider>
                <WorkspaceLayout {...props}><LayerStatusConsumer /><div>Contenido</div></WorkspaceLayout>
            </SidebarLayerProvider>,
        );
        expect(screen.getByTestId('layer-s2-status')).toHaveTextContent('closed');

        navigationState.pathname = '/plataforma/projects/project-a';
        rerender(
            <SidebarLayerProvider>
                <WorkspaceLayout {...props}><LayerStatusConsumer /><div>Contenido</div></WorkspaceLayout>
            </SidebarLayerProvider>,
        );
        expect(screen.getByTestId('layer-s2-status')).toHaveTextContent('open');
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

    it('keeps S2 open when Escape is pressed with no RIGHT drawer open', () => {
        render(
            <SidebarLayerProvider>
                <LayerStatusConsumer />
            </SidebarLayerProvider>
        );

        fireEvent.keyDown(document, { key: 'Escape' });

        expect(screen.getByTestId('layer-s2-status')).toHaveTextContent('open');
        expect(screen.getByTestId('layer-right-status')).toHaveTextContent('closed');
    });

    it('closes only RIGHT on Escape and leaves S2 open', async () => {
        const user = userEvent.setup();
        render(
            <SidebarLayerProvider>
                <LayerStatusConsumer />
            </SidebarLayerProvider>
        );
        await user.click(screen.getByRole('button', { name: 'Open RIGHT layer' }));
        expect(screen.getByTestId('layer-right-status')).toHaveTextContent('open');

        fireEvent.keyDown(document, { key: 'Escape' });

        expect(screen.getByTestId('layer-right-status')).toHaveTextContent('closed');
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
        localStorage.setItem('s2Width', '64');
        await user.click(screen.getByRole('button', { name: 'Cerrar S2 Manual' }));
        expect(screen.getByTestId('wrapper-s2-status')).toHaveTextContent('closed');

        // Click Proyectos in WorkspaceMiniSidebar
        const projectsNav = screen.getByRole('link', { name: 'Proyectos' });
        fireEvent.click(projectsNav);

        // S2 should now be opened reactively
        expect(screen.getByTestId('wrapper-s2-status')).toHaveTextContent('open');
        expect(localStorage.getItem('workspace:s2:projects')).toBe('visible');
        expect(localStorage.getItem('workspace:focus:projects')).toBe('0');
    });

    it('restores the actual S2 width when Proyectos is selected from the mini sidebar', async () => {
        const user = userEvent.setup();
        navigationState.pathname = '/plataforma/crm';
        localStorage.setItem('workspace:s2:crm', 'hidden');
        localStorage.setItem('s2Width', '64');

        render(
            <SidebarLayerProvider>
                <WorkspaceLayout sidebarTitle="CRM" sidebarSections={[]}>
                    <LayerStatusConsumer />
                    <div>Contenido</div>
                </WorkspaceLayout>
            </SidebarLayerProvider>,
        );

        await user.click(screen.getByRole('link', { name: 'Proyectos' }));

        expect(screen.getByTestId('layer-s1-status')).toHaveTextContent('open');
        expect(screen.getByTestId('layer-s2-status')).toHaveTextContent('open');
        expect(localStorage.getItem('workspace:s2:projects')).toBe('visible');
        expect(localStorage.getItem('workspace:focus:projects')).toBe('0');
        expect(localStorage.getItem('s2Width')).toBe('280');
    });
});
