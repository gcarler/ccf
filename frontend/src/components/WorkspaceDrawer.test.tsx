import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { axe } from 'jest-axe';
import { describe, expect, it, vi } from 'vitest';
import WorkspaceDrawer from './WorkspaceDrawer';

function renderDrawer(overrides: Partial<React.ComponentProps<typeof WorkspaceDrawer>> = {}) {
    const props: React.ComponentProps<typeof WorkspaceDrawer> = {
        isOpen: true,
        onClose: vi.fn(),
        title: 'Registro de Asistencia',
        subtitle: 'Aniversario 40 Años 2026',
        children: <p>Contenido del drawer</p>,
        ...overrides,
    };
    return render(<WorkspaceDrawer {...props} />);
}

describe('WorkspaceDrawer', () => {
    it('renders the expand control between close and title', () => {
        renderDrawer();

        const close = screen.getByRole('button', { name: 'Cerrar' });
        const expand = screen.getByRole('button', { name: 'Expandir panel' });
        const title = screen.getByRole('heading', { name: 'Registro de Asistencia' });

        expect(close.compareDocumentPosition(expand) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
        expect(expand.compareDocumentPosition(title) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    });

    it('expands and contracts without changing the drawer contract', () => {
        renderDrawer();
        const drawer = screen.getByRole('complementary', { name: 'Registro de Asistencia' });
        const expand = screen.getByRole('button', { name: 'Expandir panel' });

        expect(drawer).not.toHaveClass('inset-0');
        fireEvent.click(expand);
        expect(screen.getByRole('button', { name: 'Contraer panel' })).toBeInTheDocument();
        expect(drawer).toHaveClass('inset-x-0', 'top-10', 'bottom-0');
        expect(drawer).not.toHaveClass('inset-0', 'h-dvh');

        fireEvent.click(screen.getByRole('button', { name: 'Contraer panel' }));
        expect(screen.getByRole('button', { name: 'Expandir panel' })).toBeInTheDocument();
        expect(drawer).not.toHaveClass('inset-0');
    });

    it('resets expanded state after closing and reopening', () => {
        const onClose = vi.fn();
        const view = renderDrawer({ onClose });
        fireEvent.click(screen.getByRole('button', { name: 'Expandir panel' }));
        fireEvent.click(screen.getByRole('button', { name: 'Cerrar' }));
        expect(onClose).toHaveBeenCalledTimes(1);

        view.rerender(
            <WorkspaceDrawer
                isOpen={false}
                onClose={onClose}
                title="Registro de Asistencia"
                subtitle="Aniversario 40 Años 2026"
            >
                <p>Contenido del drawer</p>
            </WorkspaceDrawer>
        );
        view.rerender(
            <WorkspaceDrawer
                isOpen
                onClose={onClose}
                title="Registro de Asistencia"
                subtitle="Aniversario 40 Años 2026"
            >
                <p>Contenido del drawer</p>
            </WorkspaceDrawer>
        );

        expect(screen.getByRole('button', { name: 'Expandir panel' })).toBeInTheDocument();
    });

    it('has no accessibility violations', async () => {
        const { container } = renderDrawer();
        const results = await axe(container);
        expect(results.violations).toHaveLength(0);
    });
});
