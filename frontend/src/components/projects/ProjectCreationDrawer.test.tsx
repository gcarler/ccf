import { render, screen } from '@testing-library/react';
import { axe } from 'jest-axe';
import { describe, expect, it, vi } from 'vitest';
import ProjectCreationDrawer from './ProjectCreationDrawer';

vi.mock('@/context/AuthContext', () => ({
    useAuth: () => ({ token: null }),
}));

describe('ProjectCreationDrawer accessibility', () => {
    it('associates labels with fields and names selectable controls', () => {
        render(<ProjectCreationDrawer isOpen onClose={vi.fn()} onSubmit={vi.fn()} />);

        expect(screen.getByRole('textbox', { name: 'Título del proyecto' })).toBeInTheDocument();
        expect(screen.getByRole('textbox', { name: 'Descripción (opcional)' })).toBeInTheDocument();
        expect(screen.getByRole('group', { name: 'Estado inicial' })).toBeInTheDocument();
        expect(screen.getByRole('group', { name: 'Color del proyecto' })).toBeInTheDocument();
        expect(screen.getByRole('group', { name: 'Asignar responsable' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Color Azul ministerial' })).toHaveAttribute('aria-pressed', 'true');
    });

    it('has no axe accessibility violations while open', async () => {
        const { container } = render(<ProjectCreationDrawer isOpen onClose={vi.fn()} onSubmit={vi.fn()} />);
        const results = await axe(container);

        expect(results.violations).toEqual([]);
    });
});
