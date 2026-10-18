import React from 'react';
import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMockProject, createMockTask } from '@/test-utils/factories';
import type { ProjectComponentDetail } from '@/types/projects';
import ProjectWorkflowView from './ProjectWorkflowView';

describe('ProjectWorkflowView', () => {
    const components: ProjectComponentDetail[] = [
        {
            id: 'comp-1',
            project_id: 'proj-1',
            code: 'COMP-01',
            name: 'Infraestructura & Datos',
            budget_allocated: 5000000,
            order_index: 0,
            color: '#3b82f6',
            status: 'active',
            created_at: '2026-01-01',
            tasks_count: 1,
            expenses_count: 0,
        },
        {
            id: 'comp-2',
            project_id: 'proj-1',
            code: 'COMP-02',
            name: 'Experiencia de Usuario',
            budget_allocated: 8000000,
            order_index: 1,
            color: '#10b981',
            status: 'active',
            created_at: '2026-01-01',
            tasks_count: 1,
            expenses_count: 0,
        },
    ];

    const project = createMockProject({
        id: 'proj-1',
        title: 'Campaña Anual CCF',
        status: 'active',
        budget_allocated: 13000000,
    });

    // Level 3: Actividad Principal
    const task1 = createMockTask({
        id: 't-1',
        project_id: 'proj-1',
        component_id: 'comp-1',
        title: 'Diseñar arquitectura de base de datos',
        status: 'todo',
        priority: 'high',
        assignee_id: 'usr-1234',
    });

    // Level 4: Subactividad (hijo de task1)
    const taskLevel4 = createMockTask({
        id: 't-lvl4',
        project_id: 'proj-1',
        parent_id: 't-1',
        title: 'Definir tablas y esquemas relacionales',
        status: 'in_progress',
        priority: 'urgent',
    });

    // Level 5: Tarea nivel 5 (hijo de taskLevel4)
    const taskLevel5 = createMockTask({
        id: 't-lvl5',
        project_id: 'proj-1',
        parent_id: 't-lvl4',
        title: 'Crear índices y claves foráneas',
        status: 'in_progress',
        priority: 'medium',
    });

    // Level 6: Tarea nivel 6 (hijo de taskLevel5)
    const taskLevel6 = createMockTask({
        id: 't-lvl6',
        project_id: 'proj-1',
        parent_id: 't-lvl5',
        title: 'Validación de rendimiento con pg_stat',
        status: 'done',
        priority: 'low',
    });

    // Actividad en el segundo componente
    const task2 = createMockTask({
        id: 't-2',
        project_id: 'proj-1',
        component_id: 'comp-2',
        title: 'Diseñar wireframes en Figma',
        status: 'in_progress',
        priority: 'high',
    });

    it('renders project root, components, and deep multi-level tasks (levels 1 to 6)', () => {
        render(
            <ProjectWorkflowView
                project={project}
                tasks={[task1, taskLevel4, taskLevel5, taskLevel6, task2]}
                components={components}
                onOpenTask={vi.fn()}
            />
        );

        // Nivel 1: Proyecto
        expect(screen.getByText('Campaña Anual CCF')).toBeInTheDocument();
        expect(screen.getByText('Nivel 1 · Proyecto')).toBeInTheDocument();

        // Nivel 2: Componentes EDT
        expect(screen.getByText('Infraestructura & Datos')).toBeInTheDocument();
        expect(screen.getByText('COMP-01')).toBeInTheDocument();
        expect(screen.getByText('Experiencia de Usuario')).toBeInTheDocument();
        expect(screen.getByText('COMP-02')).toBeInTheDocument();

        // Nivel 3: Actividad Principal
        expect(screen.getByText('Diseñar arquitectura de base de datos')).toBeInTheDocument();
        expect(screen.getByText('Diseñar wireframes en Figma')).toBeInTheDocument();

        // Nivel 4: Subactividad
        expect(screen.getByText('Definir tablas y esquemas relacionales')).toBeInTheDocument();

        // Nivel 5: Tarea
        expect(screen.getByText('Crear índices y claves foráneas')).toBeInTheDocument();

        // Nivel 6: Tarea profunda
        expect(screen.getByText('Validación de rendimiento con pg_stat')).toBeInTheDocument();

        // SVG connectors container
        expect(screen.getByTestId('workflow-svg-connectors')).toBeInTheDocument();
    });

    it('allows zoom in, zoom out, reset, and fit view via toolbar controls', async () => {
        const user = userEvent.setup();
        render(
            <ProjectWorkflowView
                project={project}
                tasks={[task1]}
                components={components}
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

        // Fit View
        const fitBtn = screen.getByRole('button', { name: 'Ajustar al lienzo' });
        await user.click(fitBtn);
        expect(zoomLabel).toBeInTheDocument();
    });

    it('invokes onOpenTask when clicking any activity node at any level', async () => {
        const user = userEvent.setup();
        const onOpenTask = vi.fn();

        render(
            <ProjectWorkflowView
                project={project}
                tasks={[task1, taskLevel4, taskLevel5, taskLevel6]}
                components={components}
                onOpenTask={onOpenTask}
            />
        );

        // Click Level 3
        const nodeLvl3 = screen.getByRole('button', { name: /Diseñar arquitectura de base de datos/i });
        await user.click(nodeLvl3);
        expect(onOpenTask).toHaveBeenCalledWith(task1);

        // Click Level 6
        const nodeLvl6 = screen.getByRole('button', { name: /Validación de rendimiento con pg_stat/i });
        await user.click(nodeLvl6);
        expect(onOpenTask).toHaveBeenCalledWith(taskLevel6);
    });

    it('invokes onOpenTask with keyboard Enter on a focused activity node', async () => {
        const user = userEvent.setup();
        const onOpenTask = vi.fn();

        render(
            <ProjectWorkflowView
                project={project}
                tasks={[taskLevel5]}
                components={components}
                onOpenTask={onOpenTask}
            />
        );

        const nodeLvl5 = screen.getByRole('button', { name: /Crear índices y claves foráneas/i });
        nodeLvl5.focus();
        await user.keyboard('{Enter}');

        expect(onOpenTask).toHaveBeenCalledWith(taskLevel5);
    });

    it('renders PMI flow metrics and identifies the component with the highest active load', () => {
        render(
            <ProjectWorkflowView
                project={project}
                tasks={[task1, taskLevel4, taskLevel5, taskLevel6, task2]}
                components={components}
                onOpenTask={vi.fn()}
            />
        );

        const hud = screen.getByTestId('workflow-pmi-flow-hud');
        expect(hud).toHaveTextContent('WIP activo');
        expect(hud).toHaveTextContent('3 tareas');
        expect(hud).toHaveTextContent('Límite WIP recomendado');
        expect(hud).toHaveTextContent('3 · 0 responsables × 2 (mín. 3)');
        expect(hud).toHaveTextContent('Dentro del límite WIP');
        expect(hud).toHaveTextContent('3 tareas');
        expect(hud).toHaveTextContent('20% done');
        expect(hud).toHaveTextContent('Infraestructura & Datos (2 activas/bloqueadas)');
    });

    it('shows the Little’s Law WIP alert when active work exceeds the recommended limit', () => {
        const activeTasks = Array.from({ length: 4 }, (_, index) => createMockTask({
            id: `active-${index}`,
            project_id: 'proj-1',
            component_id: 'comp-1',
            title: `Trabajo activo ${index + 1}`,
            status: 'in_progress',
            assignee_id: 'usr-active',
            priority: 'medium',
        }));

        render(
            <ProjectWorkflowView
                project={project}
                tasks={activeTasks}
                components={components}
                onOpenTask={vi.fn()}
            />
        );

        const hud = screen.getByTestId('workflow-pmi-flow-hud');
        expect(hud).toHaveTextContent('4 tareas');
        expect(hud).toHaveTextContent('3 · 1 responsables × 2 (mín. 3)');
        expect(hud).toHaveTextContent('Exceso WIP (Ley de Little)');
    });

    it('attenuates completed task nodes when the critical flow toggle is enabled', async () => {
        const user = userEvent.setup();
        render(
            <ProjectWorkflowView
                project={project}
                tasks={[task1, taskLevel4, taskLevel5, taskLevel6]}
                components={components}
                onOpenTask={vi.fn()}
            />
        );

        const completedNode = screen.getByTestId('workflow-node-node-task-t-lvl6');
        const filterButton = screen.getByTestId('workflow-filter-critical-btn');
        expect(filterButton).toHaveAttribute('aria-pressed', 'false');
        expect(completedNode).not.toHaveClass('opacity-35');

        await user.click(filterButton);

        expect(filterButton).toHaveAttribute('aria-pressed', 'true');
        expect(completedNode).toHaveClass('opacity-35');
    });

    it('renders empty state notice when project has no tasks', () => {
        render(
            <ProjectWorkflowView
                project={project}
                tasks={[]}
                components={components}
                onOpenTask={vi.fn()}
            />
        );

        expect(screen.getByText('Lienzo de Workflow Vacío')).toBeInTheDocument();
        expect(screen.getByText(/Aún no hay actividades en este proyecto/i)).toBeInTheDocument();
    });

    it('invokes onManageComponents when clicking the + Componentes (EDT) toolbar button', async () => {
        const user = userEvent.setup();
        const onManageComponents = vi.fn();

        render(
            <ProjectWorkflowView
                project={project}
                tasks={[task1]}
                components={components}
                onOpenTask={vi.fn()}
                onManageComponents={onManageComponents}
            />
        );

        const btn = screen.getByRole('button', { name: '+ Componentes (EDT)' });
        expect(btn).toBeInTheDocument();
        await user.click(btn);

        expect(onManageComponents).toHaveBeenCalledTimes(1);
    });

    it('invokes onManageComponents when clicking a Level 2 component node', async () => {
        const user = userEvent.setup();
        const onManageComponents = vi.fn();

        render(
            <ProjectWorkflowView
                project={project}
                tasks={[task1]}
                components={components}
                onOpenTask={vi.fn()}
                onManageComponents={onManageComponents}
            />
        );

        const compNode = screen.getByRole('button', { name: /Gestionar componentes: Infraestructura & Datos/i });
        expect(compNode).toBeInTheDocument();
        await user.click(compNode);

        expect(onManageComponents).toHaveBeenCalledTimes(1);
    });

    it('invokes onManageComponents when clicking a synthetic component node for unassigned tasks', async () => {
        const user = userEvent.setup();
        const onManageComponents = vi.fn();
        const unassignedTask = createMockTask({
            id: 't-unassigned',
            project_id: 'proj-1',
            title: 'Tarea sin componente asignado',
            component_id: undefined,
        });

        render(
            <ProjectWorkflowView
                project={project}
                tasks={[unassignedTask]}
                components={[]}
                onOpenTask={vi.fn()}
                onManageComponents={onManageComponents}
            />
        );

        const syntheticNode = screen.getByRole('button', { name: /Gestionar componentes: Componente General/i });
        expect(syntheticNode).toBeInTheDocument();
        expect(screen.getByText('+ Configurar EDT')).toBeInTheDocument();

        await user.click(syntheticNode);
        expect(onManageComponents).toHaveBeenCalledTimes(1);
    });
});
