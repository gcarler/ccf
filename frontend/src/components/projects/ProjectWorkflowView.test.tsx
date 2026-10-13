import React from 'react';
import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMockProject, createMockTask } from '@/test-utils/factories';
import type { PhaseDef } from '@/context/ProjectUpdateContext';
import ProjectWorkflowView from './ProjectWorkflowView';

describe('ProjectWorkflowView', () => {
    const phases: PhaseDef[] = [
        { slug: 'backlog', name: 'Planificación', color: '#64748b', order_index: 0 },
        { slug: 'in_progress', name: 'En Desarrollo', color: '#f59e0b', order_index: 1 },
        { slug: 'done', name: 'Completado', color: '#10b981', order_index: 2 },
    ];

    const project = createMockProject({
        id: 'proj-1',
        title: 'Campaña Anual CCF',
        status: 'active',
    });

    const task1 = createMockTask({
        id: 't-1',
        project_id: 'proj-1',
        title: 'Diseñar arquitectura',
        status: 'backlog',
        priority: 'high',
        assignee_id: 'usr-1234',
    });

    const task2 = createMockTask({
        id: 't-2',
        project_id: 'proj-1',
        title: 'Construir prototipo',
        status: 'in_progress',
        priority: 'urgent',
        assignee_id: 'usr-5678',
    });

    const subtask1 = createMockTask({
        id: 'sub-1',
        project_id: 'proj-1',
        parent_id: 't-1',
        title: 'Diagramas de secuencia',
        status: 'backlog',
        priority: 'medium',
    });

    it('renders project root, phase nodes, activity nodes, and subtask nodes', () => {
        render(
            <ProjectWorkflowView
                project={project}
                tasks={[task1, task2, subtask1]}
                phases={phases}
                onOpenTask={vi.fn()}
            />
        );

        // Nivel 1: Proyecto
        expect(screen.getByText('Campaña Anual CCF')).toBeInTheDocument();
        expect(screen.getByText('Proyecto')).toBeInTheDocument();

        // Nivel 2: Fases / Componentes
        expect(screen.getByText('Planificación')).toBeInTheDocument();
        expect(screen.getByText('En Desarrollo')).toBeInTheDocument();

        // Nivel 3: Actividades
        expect(screen.getByText('Diseñar arquitectura')).toBeInTheDocument();
        expect(screen.getByText('Construir prototipo')).toBeInTheDocument();

        // Nivel 4: Subactividades
        expect(screen.getByText('Diagramas de secuencia')).toBeInTheDocument();

        // SVG connectors container
        expect(screen.getByTestId('workflow-svg-connectors')).toBeInTheDocument();
    });

    it('allows zoom in, zoom out, and reset via toolbar controls', async () => {
        const user = userEvent.setup();
        render(
            <ProjectWorkflowView
                project={project}
                tasks={[task1]}
                phases={phases}
                onOpenTask={vi.fn()}
            />
        );

        const zoomLabel = screen.getByTestId('workflow-zoom-level');
        expect(zoomLabel).toHaveTextContent('100%');

        // Zoom In
        const zoomInBtn = screen.getByRole('button', { name: 'Acercar' });
        await user.click(zoomInBtn);
        expect(zoomLabel).toHaveTextContent('115%');

        // Zoom Out
        const zoomOutBtn = screen.getByRole('button', { name: 'Alejar' });
        await user.click(zoomOutBtn);
        expect(zoomLabel).toHaveTextContent('100%');

        // Zoom Out further
        await user.click(zoomOutBtn);
        expect(zoomLabel).toHaveTextContent('85%');

        // Reset Zoom
        const resetBtn = screen.getByRole('button', { name: 'Restablecer vista' });
        await user.click(resetBtn);
        expect(zoomLabel).toHaveTextContent('100%');
    });

    it('invokes onOpenTask when clicking an activity or subtask node', async () => {
        const user = userEvent.setup();
        const onOpenTask = vi.fn();

        render(
            <ProjectWorkflowView
                project={project}
                tasks={[task1, subtask1]}
                phases={phases}
                onOpenTask={onOpenTask}
            />
        );

        const activityBtn = screen.getByRole('button', { name: 'Actividad: Diseñar arquitectura' });
        await user.click(activityBtn);

        expect(onOpenTask).toHaveBeenCalledTimes(1);
        expect(onOpenTask).toHaveBeenCalledWith(task1);

        const subtaskBtn = screen.getByRole('button', { name: 'Subactividad: Diagramas de secuencia' });
        await user.click(subtaskBtn);

        expect(onOpenTask).toHaveBeenCalledTimes(2);
        expect(onOpenTask).toHaveBeenCalledWith(subtask1);
    });

    it('invokes onOpenTask when pressing Enter on a focused node', async () => {
        const user = userEvent.setup();
        const onOpenTask = vi.fn();

        render(
            <ProjectWorkflowView
                project={project}
                tasks={[task2]}
                phases={phases}
                onOpenTask={onOpenTask}
            />
        );

        const activityBtn = screen.getByRole('button', { name: 'Actividad: Construir prototipo' });
        activityBtn.focus();
        await user.keyboard('{Enter}');

        expect(onOpenTask).toHaveBeenCalledWith(task2);
    });

    it('renders empty state notice when project has no tasks', () => {
        render(
            <ProjectWorkflowView
                project={project}
                tasks={[]}
                phases={phases}
                onOpenTask={vi.fn()}
            />
        );

        expect(screen.getByText('Lienzo de Workflow Vacío')).toBeInTheDocument();
        expect(screen.getByText(/Aún no hay actividades en este proyecto/i)).toBeInTheDocument();
    });
});
