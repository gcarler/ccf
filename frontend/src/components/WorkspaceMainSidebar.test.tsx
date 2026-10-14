import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import WorkspaceMainSidebar from './WorkspaceMainSidebar';
import { SidebarLayerProvider, useSidebarLayers } from '@/context/SidebarLayerContext';

const navigationState = vi.hoisted(() => ({ pathname: '/plataforma/crm' }));

vi.mock('next/navigation', () => ({ usePathname: () => navigationState.pathname }));
vi.mock('next/link', () => ({ default: ({ href, children, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) => <a href={href} {...props}>{children}</a> }));
vi.mock('@/design', () => ({ DSTooltip: ({ children }: { children: React.ReactNode }) => <>{children}</> }));

function StackControls() {
    const { sidebarStack, pushSidebarPanel } = useSidebarLayers();
    return (
        <div>
            <span data-testid="stack-size">{sidebarStack.length}</span>
            <button type="button" onClick={() => pushSidebarPanel({ id: 'nested', content: <p>Panel nested</p> })}>
                Abrir panel anidado
            </button>
        </div>
    );
}

describe('WorkspaceMainSidebar module stack reset', () => {
    beforeEach(() => {
        navigationState.pathname = '/plataforma/crm';
    });

    it('resets drill-down when the third pathname segment changes modules', () => {
        const { rerender } = render(
            <SidebarLayerProvider>
                <StackControls />
                <WorkspaceMainSidebar sections={[]} isCollapsed={false} />
            </SidebarLayerProvider>,
        );

        fireEvent.click(screen.getByRole('button', { name: 'Abrir panel anidado' }));
        expect(screen.getByTestId('stack-size')).toHaveTextContent('1');

        navigationState.pathname = '/plataforma/projects/tasks';
        rerender(
            <SidebarLayerProvider>
                <StackControls />
                <WorkspaceMainSidebar sections={[]} isCollapsed={false} />
            </SidebarLayerProvider>,
        );

        expect(screen.getByTestId('stack-size')).toHaveTextContent('0');
    });
});
