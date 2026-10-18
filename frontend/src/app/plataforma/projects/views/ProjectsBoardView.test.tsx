import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

vi.mock('@/context/AuthContext', () => ({
    useAuth: () => ({ user: { id: 'u1', role: 'admin' }, hasPermission: () => true, loading: false }),
    useOptionalAuth: () => ({ user: { id: 'u1', role: 'admin' }, hasPermission: () => true, loading: false }),
}));
vi.mock('@/lib/http', () => ({ apiFetch: vi.fn().mockResolvedValue([]) }));
import ProjectsBoardView from './ProjectsBoardView';
import { createMockProject } from '@/test-utils/factories';

const projects = [
    createMockProject({
        id: 'p1',
        title: 'Proyecto activo',
        description: 'En marcha',
        status: 'active',
        color: '#2563eb',
        owner_id: 'u1',
        created_at: '2025-06-15T10:00:00Z',
        tasks: [],
    }),
    createMockProject({
        id: 'p2',
        title: 'Proyecto completado',
        description: 'Finalizado',
        status: 'completed',
        color: '#16a34a',
        owner_id: 'u2',
        created_at: '2025-06-16T10:00:00Z',
        tasks: [],
    }),
];

describe('ProjectsBoardView', () => {
    it('groups projects by status into columns', () => {
        render(<ProjectsBoardView projects={projects} onUpdate={vi.fn()} onDelete={vi.fn()} />);
        expect(screen.getByText('active')).toBeInTheDocument();
        expect(screen.getByText('completed')).toBeInTheDocument();
        expect(screen.getByText('Proyecto activo')).toBeInTheDocument();
        expect(screen.getByText('Proyecto completado')).toBeInTheDocument();
    });

    it('shows empty column placeholder when no projects in a required column', () => {
        render(<ProjectsBoardView projects={[]} onUpdate={vi.fn()} onDelete={vi.fn()} />);
        expect(screen.getAllByText('Vacío').length).toBeGreaterThanOrEqual(1);
    });

    it('renders PMI stage-gate header, optimal WIP status, and column metrics', () => {
        const pmiProjects = [
            createMockProject({
                id: 'p1',
                title: 'Proyecto 1',
                status: 'active',
                task_count: 8,
                progress_percent: 60,
            }),
            createMockProject({
                id: 'p2',
                title: 'Proyecto 2',
                status: 'active',
                task_count: 4,
                progress_percent: 40,
            }),
        ];

        render(<ProjectsBoardView projects={pmiProjects} onUpdate={vi.fn()} onDelete={vi.fn()} />);

        expect(screen.getByTestId('projects-board-pmi-header')).toHaveTextContent(
            'Stage-Gate Portafolio PMI: 2 proyectos'
        );
        expect(screen.getByTestId('projects-board-wip-status')).toHaveTextContent(
            'Flujo WIP Óptimo (≤5 activos)'
        );
        expect(screen.getByTestId('board-column-active')).toHaveTextContent(
            'Ejecución Activa · PMI §4.3'
        );
        expect(screen.getByTestId('board-column-metrics-active')).toHaveTextContent(
            '12 paquetes WBS'
        );
        expect(screen.getByTestId('board-column-metrics-active')).toHaveTextContent('50% prom.');
    });

    it('triggers WIP overload warning when more than 5 projects are active', () => {
        const overloadedProjects = Array.from({ length: 6 }, (_, idx) =>
            createMockProject({
                id: `p-${idx + 1}`,
                title: `Proyecto Activo ${idx + 1}`,
                status: 'active',
            })
        );

        render(
            <ProjectsBoardView
                projects={overloadedProjects}
                onUpdate={vi.fn()}
                onDelete={vi.fn()}
            />
        );

        expect(screen.getByTestId('projects-board-wip-status')).toHaveTextContent(
            'Sobrecarga WIP (>5 activos)'
        );
    });
});

