import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { ProjectTaskRecord } from '@/types/projects';
import TaskDetailPanel from './TaskDetailPanel';

const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
    useRouter: () => ({ push: mockPush }),
}));

vi.mock('@/context/AuthContext', () => ({
    useAuth: () => ({ token: 'test-token', loading: false }),
}));

const mockApiFetch = vi.fn();
vi.mock('@/lib/http', () => ({
    apiFetch: (...args: unknown[]) => mockApiFetch(...args),
}));

vi.mock('@/components/ConfirmActionDrawer', () => ({ default: () => null }));
vi.mock('./TaskMetaFields', () => ({ default: () => <div data-testid="meta-fields" /> }));
vi.mock('./TaskAttachmentSection', () => ({ default: () => null }));
vi.mock('./TaskSupplySection', () => ({ default: () => null }));
vi.mock('./TaskActivitySection', () => ({ default: () => null }));
vi.mock('./TaskCommentSection', () => ({ default: () => null }));
vi.mock('./TaskTimeTrackingSection', () => ({ default: () => null }));
vi.mock('./TaskDimensionsSection', () => ({ default: () => null }));

const mockTaskWithComp: ProjectTaskRecord = {
    id: 'task-100',
    project_id: 'project-100',
    title: 'Configurar servidores Cloud',
    status: 'todo',
    priority: 'high',
    component_id: 'comp-infra',
};

const mockTaskGeneral: ProjectTaskRecord = {
    id: 'task-200',
    project_id: 'project-100',
    title: 'Tarea General de Coordinación',
    status: 'in_progress',
    priority: 'medium',
    component_id: null,
};

describe('TaskDetailPanel - Ver Ruta y Navegación Jerárquica', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockApiFetch.mockResolvedValue({
            components: [
                { id: 'comp-infra', code: 'EDT-1.0', name: 'Infraestructura Cloud' },
            ],
        });
    });

    it('abre la sección interactiva TaskRouteTree y llama a onVerRutaClick al pulsar "Ver Ruta"', async () => {
        const onVerRutaClick = vi.fn();
        const onClose = vi.fn();

        render(
            <TaskDetailPanel
                task={mockTaskWithComp}
                projectTitle="Mega Templo CCF"
                onClose={onClose}
                onVerRutaClick={onVerRutaClick}
            />
        );

        // Al inicio la sección de ruta está cerrada
        expect(screen.queryByText('Visualizar EDT completo en el lienzo')).not.toBeInTheDocument();

        // Pulsar Ver Ruta
        const verRutaBtn = screen.getByRole('button', { name: 'Ver ruta jerárquica de la actividad' });
        fireEvent.click(verRutaBtn);

        // Debe invocar onVerRutaClick para cambiar el fondo a vista workflow inmediatamente
        expect(onVerRutaClick).toHaveBeenCalledTimes(1);

        // Debe mostrar TaskRouteTree con la jerarquía completa
        await waitFor(() => {
            expect(screen.getByText('Ruta de la actividad')).toBeInTheDocument();
        });
        expect(screen.getAllByText('Espacio de Proyectos').length).toBeGreaterThanOrEqual(1);
        expect(screen.getAllByText('Mega Templo CCF').length).toBeGreaterThanOrEqual(1);
        expect(screen.getAllByText('EDT-1.0 · Infraestructura Cloud').length).toBeGreaterThanOrEqual(1);
        expect(screen.getAllByText('Pendiente').length).toBeGreaterThanOrEqual(1);
        expect(screen.getAllByText('Configurar servidores Cloud').length).toBeGreaterThanOrEqual(1);

        // Botón para ver ruta completa en lienzo presente
        const canvasBtn = screen.getByRole('button', { name: 'Ver ruta completa en el lienzo' });
        expect(canvasBtn).toBeInTheDocument();

        // Clic en ver ruta completa en el lienzo invoca onVerRutaClick y cierra el panel lateral
        fireEvent.click(canvasBtn);
        expect(onVerRutaClick).toHaveBeenCalledTimes(2);
        expect(onClose).toHaveBeenCalledTimes(1);
    });

    it('muestra "Componente General" si la tarea no tiene component_id asignado', async () => {
        const onVerRutaClick = vi.fn();
        render(
            <TaskDetailPanel
                task={mockTaskGeneral}
                projectTitle="Mega Templo CCF"
                onClose={vi.fn()}
                onVerRutaClick={onVerRutaClick}
            />
        );

        fireEvent.click(screen.getByRole('button', { name: 'Ver ruta jerárquica de la actividad' }));

        await waitFor(() => {
            expect(screen.getByText('Componente General')).toBeInTheDocument();
        });
    });

    it('ejecuta fallback con router.push cuando onVerRutaClick no fue provisto', async () => {
        render(
            <TaskDetailPanel
                task={mockTaskWithComp}
                projectTitle="Mega Templo CCF"
                onClose={vi.fn()}
            />
        );

        const verRutaBtn = screen.getByRole('button', { name: 'Ver ruta jerárquica de la actividad' });
        fireEvent.click(verRutaBtn);

        expect(mockPush).toHaveBeenCalledWith('/plataforma/projects/project-100?view=workflow');
    });

    it('permite cerrar el panel y cambiar a vista workflow al hacer clic en el nombre del proyecto en el header', async () => {
        const onVerRutaClick = vi.fn();
        const onClose = vi.fn();

        render(
            <TaskDetailPanel
                task={mockTaskWithComp}
                projectTitle="Mega Templo CCF"
                onClose={onClose}
                onVerRutaClick={onVerRutaClick}
            />
        );

        const projectBtn = screen.getByRole('button', { name: 'Ir al proyecto: Mega Templo CCF' });
        fireEvent.click(projectBtn);

        expect(onVerRutaClick).toHaveBeenCalledTimes(1);
        expect(onClose).toHaveBeenCalledTimes(1);
    });
});
