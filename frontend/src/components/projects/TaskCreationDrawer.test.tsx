import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { axe } from 'jest-axe';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import TaskCreationDrawer from './TaskCreationDrawer';

const mockApiFetch = vi.fn();
vi.mock('@/lib/http', () => ({
    apiFetch: (...args: unknown[]) => mockApiFetch(...args),
}));

vi.mock('@/context/AuthContext', () => ({
    useAuth: () => ({ token: 'test-token' }),
}));

describe('TaskCreationDrawer accessibility', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockApiFetch.mockResolvedValue({
            components: [
                { id: 'comp-1', code: 'EDT-1.0', name: 'Arquitectura' },
                { id: 'comp-2', code: 'EDT-2.0', name: 'Frontend' },
            ],
        });
    });

    it('associates form fields and labels priority/node selections', () => {
        render(<TaskCreationDrawer isOpen onClose={vi.fn()} onSubmit={vi.fn()} />);

        expect(screen.getByRole('textbox', { name: 'Título de la tarea' })).toBeInTheDocument();
        expect(screen.getByRole('textbox', { name: 'Descripción (Opcional)' })).toBeInTheDocument();
        expect(screen.getByRole('group', { name: 'Nivel de Prioridad' })).toBeInTheDocument();
        expect(screen.queryByRole('group', { name: 'Nodo Operativo' })).not.toBeInTheDocument();
        expect(screen.getByRole('group', { name: 'Asignar a' })).toBeInTheDocument();
        expect(screen.getByRole('combobox', { name: 'Componente (EDT)' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Media' })).toHaveAttribute('aria-pressed', 'true');
        expect(screen.queryByRole('button', { name: 'Sin nodo' })).not.toBeInTheDocument();
    });

    it('loads components for projectId and passes selected component_id upon submit', async () => {
        const onSubmit = vi.fn().mockResolvedValue(true);
        render(
            <TaskCreationDrawer
                isOpen
                projectId="proj-1"
                onClose={vi.fn()}
                onSubmit={onSubmit}
            />
        );

        await waitFor(() => {
            expect(screen.getByText('EDT-1.0 · Arquitectura')).toBeInTheDocument();
        });

        fireEvent.change(screen.getByRole('textbox', { name: 'Título de la tarea' }), {
            target: { value: 'Nueva tarea con EDT' },
        });

        const compSelect = screen.getByRole('combobox', { name: 'Componente (EDT)' });
        fireEvent.change(compSelect, { target: { value: 'comp-1' } });

        fireEvent.click(screen.getByRole('button', { name: 'Crear Tarea' }));

        await waitFor(() => {
            expect(onSubmit).toHaveBeenCalledWith(
                expect.objectContaining({
                    title: 'Nueva tarea con EDT',
                    component_id: 'comp-1',
                })
            );
        });
    });

    it('has no axe accessibility violations while open', async () => {
        const { container } = render(<TaskCreationDrawer isOpen onClose={vi.fn()} onSubmit={vi.fn()} />);
        const results = await axe(container);

        expect(results.violations).toEqual([]);
    });
});
