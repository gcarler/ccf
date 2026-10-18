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

        expect(screen.getByRole('textbox', { name: 'Título de la actividad' })).toBeInTheDocument();
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

        fireEvent.change(screen.getByRole('textbox', { name: 'Título de la actividad' }), {
            target: { value: 'Nueva tarea con EDT' },
        });

        const compSelect = screen.getByRole('combobox', { name: 'Componente (EDT)' });
        fireEvent.change(compSelect, { target: { value: 'comp-1' } });

        fireEvent.click(screen.getByRole('button', { name: 'Crear Actividad' }));

        await waitFor(() => {
            expect(onSubmit).toHaveBeenCalledWith(
                expect.objectContaining({
                    title: 'Nueva tarea con EDT',
                    component_id: 'comp-1',
                })
            );
        });
    });

    it('allows creating an EDT component inline without closing the drawer', async () => {
        mockApiFetch.mockImplementation((url: string, opts?: { method?: string }) => {
            if (url.includes('/components-breakdown')) {
                return Promise.resolve({
                    components: [
                        { id: 'comp-1', code: 'EDT-1.0', name: 'Arquitectura' },
                    ],
                });
            }
            if (url.includes('/components') && opts?.method === 'POST') {
                return Promise.resolve({
                    id: 'comp-new',
                    code: 'EDT-2.0',
                    name: 'Nuevo Modulo',
                });
            }
            return Promise.resolve({});
        });

        render(
            <TaskCreationDrawer
                isOpen
                projectId="proj-1"
                onClose={vi.fn()}
                onSubmit={vi.fn()}
            />
        );

        await waitFor(() => {
            expect(screen.getByText('+ Nuevo componente')).toBeInTheDocument();
        });

        fireEvent.click(screen.getByText('+ Nuevo componente'));
        expect(screen.getByTestId('inline-edt-form')).toBeInTheDocument();

        fireEvent.change(screen.getByLabelText('Nombre del Componente'), {
            target: { value: 'Nuevo Modulo' },
        });

        fireEvent.click(screen.getByRole('button', { name: 'Guardar' }));

        await waitFor(() => {
            expect(mockApiFetch).toHaveBeenCalledWith(
                '/projects/proj-1/components',
                expect.objectContaining({
                    method: 'POST',
                    body: expect.objectContaining({
                        name: 'Nuevo Modulo',
                    }),
                })
            );
        });
    });

    it('has no axe accessibility violations while open', async () => {
        const { container } = render(<TaskCreationDrawer isOpen onClose={vi.fn()} onSubmit={vi.fn()} />);
        const results = await axe(container);

        expect(results.violations).toEqual([]);
    });

    it('updates PMI WBS readiness score reactively as fields are populated', async () => {
        render(
            <TaskCreationDrawer
                isOpen
                projectId="proj-1"
                onClose={vi.fn()}
                onSubmit={vi.fn()}
            />
        );

        await waitFor(() => {
            expect(screen.getByText('EDT-1.0 · Arquitectura')).toBeInTheDocument();
        });

        expect(screen.getByTestId('task-creation-pmi-readiness')).toHaveTextContent('Definición Parcial');
        expect(screen.getByTestId('task-creation-pmi-score')).toHaveTextContent('0/4 Criterios WBS');

        fireEvent.change(screen.getByRole('textbox', { name: 'Título de la actividad' }), {
            target: { value: 'Configurar Red Redundante' },
        });
        expect(screen.getByTestId('task-creation-pmi-score')).toHaveTextContent('1/4 Criterios WBS');

        fireEvent.change(screen.getByRole('textbox', { name: 'Descripción (Opcional)' }), {
            target: { value: 'Criterio de aceptación verificable de más de quince caracteres.' },
        });
        expect(screen.getByTestId('task-creation-pmi-score')).toHaveTextContent('2/4 Criterios WBS');

        fireEvent.change(screen.getByRole('combobox', { name: 'Componente (EDT)' }), {
            target: { value: 'comp-1' },
        });
        expect(screen.getByTestId('task-creation-pmi-score')).toHaveTextContent('3/4 Criterios WBS');
    });

    it('inserts structured PMI WBS / DoD templates into description on 1-click', () => {
        render(<TaskCreationDrawer isOpen onClose={vi.fn()} onSubmit={vi.fn()} />);

        const descField = screen.getByRole('textbox', { name: 'Descripción (Opcional)' }) as HTMLTextAreaElement;
        expect(descField.value).toBe('');

        fireEvent.click(screen.getByTestId('task-template-wbs'));
        expect(descField.value).toContain('Entregable Verificable');
        expect(descField.value.length).toBeGreaterThanOrEqual(40);

        fireEvent.click(screen.getByTestId('task-template-dod'));
        expect(descField.value).toContain('Checklist Definition of Done (DoD)');
    });
});
