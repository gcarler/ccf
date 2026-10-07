import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useState } from 'react';
import { apiFetch } from '@/lib/http';
import type { ProjectTaskRecord } from '@/types/projects';
import TaskDetailPanel from './TaskDetailPanel';

vi.mock('@/context/AuthContext', () => ({
    useAuth: () => ({ token: 'test-token', loading: false }),
}));

vi.mock('@/lib/http', () => ({ apiFetch: vi.fn().mockResolvedValue([]) }));

const task: ProjectTaskRecord = {
    id: 'task-integration',
    project_id: 'project-integration',
    title: 'Preparar encuentro',
    description: 'Organizar los materiales del encuentro.',
    status: 'todo',
    priority: 'medium',
    labels: [],
    attachments: [{ id: 'attachment-integration', task_id: 'task-integration', filename: 'plan.pdf', file_url: '/files/plan.pdf', file_size: 1200 }],
    supplies: [{ id: 'supply-integration', task_id: 'task-integration', item_name: 'Cuaderno', quantity: 1, status: 'pending' }],
    subtasks: [],
};

describe('TaskDetailPanel integrated accessibility', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders all real sections and passes axe with the actual task content', async () => {
        const user = userEvent.setup();
        function Harness() {
            const [isOpen, setIsOpen] = useState(true);
            return isOpen
                ? <TaskDetailPanel task={task} onClose={() => setIsOpen(false)} />
                : <p>Panel cerrado</p>;
        }

        const { container } = render(<Harness />);

        const detailPanel = screen.getByRole('complementary', { name: 'Detalle de tarea' });
        expect(detailPanel).toBeInTheDocument();
        expect(screen.getByText('Persona asignada')).toBeInTheDocument();
        expect(screen.getByRole('heading', { name: 'Archivos 1' })).toBeInTheDocument();
        expect(screen.getByRole('heading', { name: 'Insumos 1' })).toBeInTheDocument();
        expect(screen.getByRole('heading', { name: 'Tiempo Dedicado' })).toBeInTheDocument();
        expect(screen.getByRole('heading', { name: 'Actividades 0' })).toBeInTheDocument();
        expect(screen.getByText('Actividad')).toBeInTheDocument();

        await waitFor(() => expect(apiFetch).toHaveBeenCalled());
        expect(await screen.findByText(/Sin comentarios aún/)).toBeInTheDocument();
        expect((await axe(container)).violations).toEqual([]);

        await user.click(screen.getByRole('button', { name: 'Registrar horas' }));
        expect(screen.getByRole('textbox', { name: 'Descripción de lo realizado' })).toBeInTheDocument();
        expect((await axe(container)).violations).toEqual([]);

        const assigneeTrigger = screen.getByRole('button', { name: 'Sin asignar' });
        await user.click(assigneeTrigger);
        expect(await screen.findByRole('listbox')).toBeInTheDocument();
        expect((await axe(container)).violations).toEqual([]);

        await user.keyboard('{Escape}');
        expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
        expect(detailPanel).toBeInTheDocument();
        expect(assigneeTrigger).toHaveFocus();

        await user.click(screen.getByRole('button', { name: 'Eliminar insumo: Cuaderno' }));
        await screen.findByRole('complementary', { name: 'Eliminar insumo' });
        expect(screen.getByText(/¿Seguro que deseas eliminar “Cuaderno”\?/)).toBeInTheDocument();
        expect(vi.mocked(apiFetch).mock.calls.some(([, options]) => options?.method === 'DELETE')).toBe(false);
        expect((await axe(container)).violations).toEqual([]);

        await user.keyboard('{Escape}');
        await waitFor(() => {
            expect(screen.queryByRole('complementary', { name: 'Eliminar insumo' })).not.toBeInTheDocument();
        });
        expect(detailPanel).toBeInTheDocument();
        expect(screen.getByRole('heading', { name: 'Insumos 1' })).toBeInTheDocument();
        expect(vi.mocked(apiFetch).mock.calls.some(([, options]) => options?.method === 'DELETE')).toBe(false);

        await user.click(screen.getByRole('button', { name: 'Eliminar insumo: Cuaderno' }));
        await screen.findByRole('complementary', { name: 'Eliminar insumo' });

        await user.click(screen.getByRole('button', { name: 'Eliminar' }));
        await waitFor(() => {
            expect(apiFetch).toHaveBeenCalledWith(
                '/projects/project-integration/tasks/task-integration/supplies/supply-integration',
                expect.objectContaining({ method: 'DELETE' }),
            );
            expect(screen.getByRole('heading', { name: 'Insumos 0' })).toBeInTheDocument();
        });
        await waitFor(() => {
            expect(screen.queryByRole('complementary', { name: 'Eliminar insumo' })).not.toBeInTheDocument();
        });

        await user.keyboard('{Escape}');
        await waitFor(() => expect(screen.getByText('Panel cerrado')).toBeInTheDocument());
        expect(detailPanel).not.toBeInTheDocument();
    });

    it('retains the supply and announces a rejected DELETE after confirmation', async () => {
        const user = userEvent.setup();
        render(<TaskDetailPanel task={task} onClose={vi.fn()} />);

        await screen.findByText(/Sin comentarios aún/);
        vi.mocked(apiFetch).mockRejectedValueOnce(new Error('offline'));

        await user.click(screen.getByRole('button', { name: 'Eliminar insumo: Cuaderno' }));
        await user.click(await screen.findByRole('button', { name: 'Eliminar' }));

        expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo eliminar el insumo.');
        expect(screen.getByRole('heading', { name: 'Insumos 1' })).toBeInTheDocument();
        expect(screen.getByRole('complementary', { name: 'Eliminar insumo' })).toBeInTheDocument();
        expect(apiFetch).toHaveBeenCalledWith(
            '/projects/project-integration/tasks/task-integration/supplies/supply-integration',
            expect.objectContaining({ method: 'DELETE' }),
        );
    });

    it('requires drawer confirmation before deleting an attachment or the task', async () => {
        const user = userEvent.setup();
        const onDelete = vi.fn();
        function Harness() {
            const [isOpen, setIsOpen] = useState(true);
            const [currentTask, setCurrentTask] = useState(task);
            return isOpen
                ? <TaskDetailPanel task={currentTask} onUpdate={setCurrentTask} onDelete={onDelete} onClose={() => setIsOpen(false)} />
                : <p>Panel cerrado</p>;
        }

        render(<Harness />);
        expect(screen.getByRole('heading', { name: 'Archivos 1' })).toBeInTheDocument();
        await screen.findByText(/Sin comentarios aún/);

        await user.click(screen.getByRole('button', { name: 'Eliminar archivo plan.pdf' }));
        await screen.findByRole('complementary', { name: 'Eliminar archivo adjunto' });
        expect(vi.mocked(apiFetch).mock.calls.some(([, options]) => options?.method === 'DELETE')).toBe(false);
        await user.keyboard('{Escape}');
        await waitFor(() => {
            expect(screen.queryByRole('complementary', { name: 'Eliminar archivo adjunto' })).not.toBeInTheDocument();
        });
        expect(screen.getByRole('heading', { name: 'Archivos 1' })).toBeInTheDocument();

        await user.click(screen.getByRole('button', { name: 'Eliminar archivo plan.pdf' }));
        await screen.findByRole('complementary', { name: 'Eliminar archivo adjunto' });
        await user.click(screen.getByRole('button', { name: 'Eliminar' }));
        await waitFor(() => {
            expect(apiFetch).toHaveBeenCalledWith(
                '/projects/project-integration/tasks/task-integration/attachments/attachment-integration',
                expect.objectContaining({ method: 'DELETE' }),
            );
            expect(screen.getByRole('heading', { name: 'Archivos 0' })).toBeInTheDocument();
        });

        await user.click(screen.getByRole('button', { name: 'Eliminar tarea' }));
        await screen.findByRole('complementary', { name: 'Eliminar tarea' });
        expect(onDelete).not.toHaveBeenCalled();
        expect(vi.mocked(apiFetch).mock.calls.some(([path, options]) => options?.method === 'DELETE' && path.endsWith('/task-integration'))).toBe(false);
        await user.keyboard('{Escape}');
        await waitFor(() => {
            expect(screen.queryByRole('complementary', { name: 'Eliminar tarea' })).not.toBeInTheDocument();
        });
        expect(screen.getByRole('complementary', { name: 'Detalle de tarea' })).toBeInTheDocument();

        await user.click(screen.getByRole('button', { name: 'Eliminar tarea' }));
        await screen.findByRole('complementary', { name: 'Eliminar tarea' });
        await user.click(screen.getByRole('button', { name: 'Eliminar' }));
        await waitFor(() => expect(screen.getByText('Panel cerrado')).toBeInTheDocument());
        expect(onDelete).toHaveBeenCalledWith('task-integration');
    });

    it('requires drawer confirmation before deleting an activity and cancellation preserves it', async () => {
        const user = userEvent.setup();
        const taskWithActivity = { ...task, subtasks: [{ id: 'activity-1', project_id: task.project_id, title: 'Preparar materiales', status: 'todo', priority: 'medium' }] };
        render(<TaskDetailPanel task={taskWithActivity} onClose={vi.fn()} />);
        await screen.findByText(/Sin comentarios aún/);

        await user.click(screen.getByRole('button', { name: 'Eliminar actividad: Preparar materiales' }));
        expect(await screen.findByRole('complementary', { name: 'Eliminar actividad' })).toBeInTheDocument();
        expect(screen.getByRole('complementary', { name: 'Eliminar actividad' })).toHaveTextContent('Preparar materiales');
        expect(vi.mocked(apiFetch).mock.calls.some(([, options]) => options?.method === 'DELETE')).toBe(false);

        await user.keyboard('{Escape}');
        await waitFor(() => expect(screen.queryByRole('complementary', { name: 'Eliminar actividad' })).not.toBeInTheDocument());
        expect(screen.getByRole('button', { name: 'Eliminar actividad: Preparar materiales' })).toBeInTheDocument();
        expect(vi.mocked(apiFetch).mock.calls.some(([, options]) => options?.method === 'DELETE')).toBe(false);
    });

    it('keeps an activity visible and confirmation open when deletion fails', async () => {
        const user = userEvent.setup();
        const taskWithActivity = { ...task, subtasks: [{ id: 'activity-1', project_id: task.project_id, title: 'Preparar materiales', status: 'todo', priority: 'medium' }] };
        vi.mocked(apiFetch).mockImplementation((_path, options) =>
            options?.method === 'DELETE' ? Promise.reject(new Error('offline')) : Promise.resolve([]),
        );
        render(<TaskDetailPanel task={taskWithActivity} onClose={vi.fn()} />);
        await screen.findByText(/Sin comentarios aún/);

        await user.click(screen.getByRole('button', { name: 'Eliminar actividad: Preparar materiales' }));
        await user.click(await screen.findByRole('button', { name: 'Eliminar' }));

        expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo eliminar la actividad.');
        expect(screen.getByRole('button', { name: 'Eliminar actividad: Preparar materiales' })).toBeInTheDocument();
        expect(screen.getByRole('complementary', { name: 'Eliminar actividad' })).toBeInTheDocument();
    });

    it('keeps attachment deletion confirmation open after a failed request', async () => {
        const user = userEvent.setup();
        render(<TaskDetailPanel task={task} onClose={vi.fn()} />);
        await screen.findByText(/Sin comentarios aún/);
        vi.mocked(apiFetch).mockRejectedValueOnce(new Error('offline'));

        await user.click(screen.getByRole('button', { name: 'Eliminar archivo plan.pdf' }));
        await user.click(await screen.findByRole('button', { name: 'Eliminar' }));

        expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo eliminar el archivo adjunto.');
        expect(screen.getByRole('heading', { name: 'Archivos 1' })).toBeInTheDocument();
        expect(screen.getByRole('complementary', { name: 'Eliminar archivo adjunto' })).toBeInTheDocument();
    });

    it('keeps task deletion confirmation open after a failed request', async () => {
        const user = userEvent.setup();
        render(<TaskDetailPanel task={task} onClose={vi.fn()} />);
        await screen.findByText(/Sin comentarios aún/);
        vi.mocked(apiFetch).mockRejectedValueOnce(new Error('offline'));

        await user.click(screen.getByRole('button', { name: 'Eliminar tarea' }));
        await user.click(await screen.findByRole('button', { name: 'Eliminar' }));

        expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo eliminar la tarea.');
        expect(screen.getByRole('complementary', { name: 'Detalle de tarea' })).toBeInTheDocument();
        expect(screen.getByRole('complementary', { name: 'Eliminar tarea' })).toBeInTheDocument();
    });

    it('keeps comment deletion confirmation open after a failed request', async () => {
        const user = userEvent.setup();
        vi.mocked(apiFetch).mockImplementation((path: string) => path === '/projects/comments?task_id=task-integration'
            ? Promise.resolve([{
                id: 'comment-1',
                project_id: 'project-integration',
                author_id: 'user-1',
                author_name: 'Ada',
                content: 'Comentario a revisar',
                created_at: '2026-10-01T10:00:00Z',
                updated_at: '2026-10-01T10:00:00Z',
                is_resolved: false,
            }])
            : Promise.resolve([]));
        render(<TaskDetailPanel task={task} onClose={vi.fn()} />);
        await screen.findByText('Comentario a revisar');
        vi.mocked(apiFetch).mockRejectedValueOnce(new Error('offline'));

        await user.click(screen.getByRole('button', { name: 'Eliminar comentario de Ada' }));
        await user.click(await screen.findByRole('button', { name: 'Eliminar' }));

        expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo eliminar el comentario.');
        expect(screen.getByText('Comentario a revisar')).toBeInTheDocument();
        expect(screen.getByRole('complementary', { name: 'Eliminar comentario' })).toBeInTheDocument();
    });
});
