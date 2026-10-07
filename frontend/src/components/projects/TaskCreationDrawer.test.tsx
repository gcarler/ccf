import { render, screen } from '@testing-library/react';
import { axe } from 'jest-axe';
import { describe, expect, it, vi } from 'vitest';
import TaskCreationDrawer from './TaskCreationDrawer';

vi.mock('@/context/AuthContext', () => ({
    useAuth: () => ({ token: null }),
}));

describe('TaskCreationDrawer accessibility', () => {
    it('associates form fields and labels priority/node selections', () => {
        render(<TaskCreationDrawer isOpen onClose={vi.fn()} onSubmit={vi.fn()} />);

        expect(screen.getByRole('textbox', { name: 'Título de la tarea' })).toBeInTheDocument();
        expect(screen.getByRole('textbox', { name: 'Descripción (Opcional)' })).toBeInTheDocument();
        expect(screen.getByRole('group', { name: 'Nivel de Prioridad' })).toBeInTheDocument();
        expect(screen.getByRole('group', { name: 'Nodo Operativo' })).toBeInTheDocument();
        expect(screen.getByRole('group', { name: 'Asignar a' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Media' })).toHaveAttribute('aria-pressed', 'true');
        expect(screen.getByRole('button', { name: 'Sin nodo' })).toHaveAttribute('aria-pressed', 'true');
    });

    it('has no axe accessibility violations while open', async () => {
        const { container } = render(<TaskCreationDrawer isOpen onClose={vi.fn()} onSubmit={vi.fn()} />);
        const results = await axe(container);

        expect(results.violations).toEqual([]);
    });
});
