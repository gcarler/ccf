import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

vi.mock('@/context/AuthContext', () => ({
    useAuth: () => ({ user: { id: 'u1', role: 'admin' }, hasPermission: () => true, loading: false }),
    useOptionalAuth: () => ({ user: { id: 'u1', role: 'admin' }, hasPermission: () => true, loading: false }),
}));
vi.mock('@/lib/http', () => ({ apiFetch: vi.fn().mockResolvedValue([]) }));
import ProjectsGridView from './ProjectsGridView';
import { createMockProject } from '@/test-utils/factories';

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
        status: 'planning',
        color: '#8b5cf6',
        owner_id: 'u2',
        created_at: '2025-06-16T10:00:00Z',
        tasks: [],
    }),
];

describe('ProjectsGridView', () => {
    it('renders a grid with project titles', () => {
        render(<ProjectsGridView projects={projects} onUpdate={vi.fn()} />);
        expect(screen.getByText('Campamento Juventud')).toBeInTheDocument();
        expect(screen.getByText('Retiro Pastoral')).toBeInTheDocument();
    });

    it('calls onUpdate when inline editing a project title', () => {
        const onUpdate = vi.fn();
        render(<ProjectsGridView projects={projects} onUpdate={onUpdate} />);
        const title = screen.getByText('Campamento Juventud');
        fireEvent.click(title);
        const input = screen.getByDisplayValue('Campamento Juventud');
        fireEvent.change(input, { target: { value: 'Campamento Juventud 2026' } });
        fireEvent.blur(input);
        expect(onUpdate).toHaveBeenCalledWith('p1', { title: 'Campamento Juventud 2026' });
    });

    it('calls onDelete when delete is clicked', () => {
        const onDelete = vi.fn();
        render(<ProjectsGridView projects={projects} onUpdate={vi.fn()} onDelete={onDelete} />);
        const buttons = screen.getAllByTitle('Eliminar proyecto');
        fireEvent.click(buttons[0]);
        expect(onDelete).toHaveBeenCalledWith('p1');
    });

    it('renders PMI executive governance header and filters attention-required projects', () => {
        const gridProjects = [
            createMockProject({
                id: 'p-ok',
                title: 'Proyecto Saludable Con PM',
                status: 'active',
                owner_id: 'u1',
                health_status: 'on_track',
            }),
            createMockProject({
                id: 'p-risk',
                title: 'Proyecto En Riesgo Sin PM',
                status: 'active',
                owner_id: null,
                health_status: 'at_risk',
            }),
        ];

        render(<ProjectsGridView projects={gridProjects} onUpdate={vi.fn()} />);

        const header = screen.getByTestId('projects-grid-pmi-header');
        expect(header).toHaveTextContent('Capacidad Portafolio: 2 proyecto(s)');
        expect(header).toHaveTextContent('En Ruta: 1');
        expect(header).toHaveTextContent('En Riesgo / Críticos: 1');
        expect(header).toHaveTextContent('1/2 con PM');

        fireEvent.click(screen.getByTestId('projects-grid-filter-attention'));
        expect(screen.queryByText('Proyecto Saludable Con PM')).not.toBeInTheDocument();
        expect(screen.getByText('Proyecto En Riesgo Sin PM')).toBeInTheDocument();

        fireEvent.click(screen.getByTestId('projects-grid-filter-attention'));
        expect(screen.getByText('Proyecto Saludable Con PM')).toBeInTheDocument();
        expect(screen.getByText('Proyecto En Riesgo Sin PM')).toBeInTheDocument();
    });
});

