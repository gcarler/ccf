import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import ProjectsTableView from './ProjectsTableView';
import { createMockProject } from '@/test-utils/factories';

const { pushMock } = vi.hoisted(() => ({ pushMock: vi.fn() }));

vi.mock('next/navigation', () => ({
    useRouter: () => ({ push: pushMock }),
}));

const projects = [
    createMockProject({
        id: 'p1',
        title: 'Campamento Juventud',
        description: 'Organización del campamento',
        status: 'active',
        color: '#2563eb',
        owner_id: 'u1',
        created_at: '2025-06-15T10:00:00Z',
        tasks: [],
    }),
    createMockProject({
        id: 'p2',
        title: 'Retiro Pastoral',
        description: 'Planificación del retiro',
        status: 'completed',
        color: '#8b5cf6',
        owner_id: 'u2',
        created_at: '2025-06-16T10:00:00Z',
        tasks: [],
    }),
];

describe('ProjectsTableView', () => {
    it('keeps inline editing separate from an accessible detail action', () => {
        pushMock.mockClear();
        render(<ProjectsTableView projects={projects} onUpdate={vi.fn()} />);

        fireEvent.click(screen.getByText('Campamento Juventud'));
        expect(pushMock).not.toHaveBeenCalled();

        fireEvent.click(screen.getByRole('button', { name: 'Abrir proyecto Campamento Juventud' }));
        expect(pushMock).toHaveBeenCalledWith('/plataforma/projects/p1?view=list');
    });

    it('renders project titles and status pickers', () => {
        render(<ProjectsTableView projects={projects} onUpdate={vi.fn()} />);
        expect(screen.getByText('Campamento Juventud')).toBeInTheDocument();
        expect(screen.getByText('Retiro Pastoral')).toBeInTheDocument();
    });

    it('calls onUpdate when title is edited', () => {
        pushMock.mockClear();
        const onUpdate = vi.fn();
        render(<ProjectsTableView projects={projects} onUpdate={onUpdate} />);
        const title = screen.getByText('Campamento Juventud');
        fireEvent.click(title);
        const input = screen.getByDisplayValue('Campamento Juventud');
        fireEvent.change(input, { target: { value: 'Campamento 2026' } });
        fireEvent.blur(input);
        expect(onUpdate).toHaveBeenCalledWith('p1', { title: 'Campamento 2026' });
        expect(pushMock).not.toHaveBeenCalled();
    });

    it('renders owner picker for each project row', () => {
        render(<ProjectsTableView projects={projects} onUpdate={vi.fn()} />);
        const pickers = screen.getAllByRole('button', { name: 'Selector de persona asignada' });
        expect(pickers.length).toBe(projects.length);
    });

    it('renders PMI §6 portfolio governance banner and RAG health column per project', () => {
        const pmiProjects = [
            createMockProject({
                id: 'p-healthy',
                title: 'Proyecto En Ruta',
                status: 'active',
                owner_id: 'u1',
                progress_percent: 60,
                task_count: 5,
                health_status: 'on_track',
            }),
            createMockProject({
                id: 'p-risk',
                title: 'Proyecto En Riesgo',
                status: 'active',
                owner_id: null,
                progress_percent: 20,
                task_count: 7,
                health_status: 'at_risk',
            }),
        ];

        render(<ProjectsTableView projects={pmiProjects} onUpdate={vi.fn()} />);

        const banner = screen.getByTestId('projects-table-pmi-portfolio-banner');
        expect(banner).toBeInTheDocument();
        expect(banner).toHaveTextContent('2 proyecto(s)');
        expect(banner).toHaveTextContent('Avance PMI (0/50/100): 40%');
        expect(banner).toHaveTextContent('En Ruta: 1');
        expect(banner).toHaveTextContent('En Riesgo / Críticos: 1');
        expect(banner).toHaveTextContent('Capacidad WBS: 12 tareas');

        expect(screen.getByTestId('project-table-health-p-healthy')).toHaveTextContent('En Ruta');
        expect(screen.getByTestId('project-table-health-p-healthy')).toHaveTextContent('60%');
        expect(screen.getByTestId('project-table-health-p-risk')).toHaveTextContent('En Riesgo');
        expect(screen.getByTestId('project-table-health-p-risk')).toHaveTextContent('20%');
    });

    it('filters portfolio rows by at-risk/critical health and missing sponsor/PM', () => {
        const filterProjects = [
            createMockProject({
                id: 'p-ok',
                title: 'Proyecto Saludable Con PM',
                status: 'active',
                owner_id: 'u1',
                health_status: 'on_track',
            }),
            createMockProject({
                id: 'p-crit',
                title: 'Proyecto Crítico Con PM',
                status: 'active',
                owner_id: 'u2',
                health_status: 'off_track',
            }),
            createMockProject({
                id: 'p-orphan',
                title: 'Proyecto Sin Sponsor',
                status: 'planning',
                owner_id: null,
                health_status: 'on_track',
            }),
        ];

        render(<ProjectsTableView projects={filterProjects} onUpdate={vi.fn()} />);

        expect(screen.getByText('Proyecto Saludable Con PM')).toBeInTheDocument();
        expect(screen.getByText('Proyecto Crítico Con PM')).toBeInTheDocument();
        expect(screen.getByText('Proyecto Sin Sponsor')).toBeInTheDocument();

        fireEvent.click(screen.getByTestId('projects-table-filter-at-risk'));
        expect(screen.queryByText('Proyecto Saludable Con PM')).not.toBeInTheDocument();
        expect(screen.getByText('Proyecto Crítico Con PM')).toBeInTheDocument();
        expect(screen.queryByText('Proyecto Sin Sponsor')).not.toBeInTheDocument();

        fireEvent.click(screen.getByTestId('projects-table-filter-no-owner'));
        expect(screen.queryByText('Proyecto Saludable Con PM')).not.toBeInTheDocument();
        expect(screen.queryByText('Proyecto Crítico Con PM')).not.toBeInTheDocument();
        expect(screen.getByText('Proyecto Sin Sponsor')).toBeInTheDocument();

        fireEvent.click(screen.getByTestId('projects-table-filter-all'));
        expect(screen.getByText('Proyecto Saludable Con PM')).toBeInTheDocument();
        expect(screen.getByText('Proyecto Crítico Con PM')).toBeInTheDocument();
        expect(screen.getByText('Proyecto Sin Sponsor')).toBeInTheDocument();
    });
});

