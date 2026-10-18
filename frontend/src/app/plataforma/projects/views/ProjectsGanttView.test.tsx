import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import ProjectsGanttView from './ProjectsGanttView';
import { createMockProject, createMockTask } from '@/test-utils/factories';

vi.mock('@/components/ui/UniversalGanttView', () => ({
    default: ({ items, moduleName, onItemClick }: { items: Array<{ id: string; title: string; start_date: string; end_date: string; progress: number }>; moduleName: string; onItemClick?: (item: { id: string; title: string }) => void }) => (
        <div data-testid="gantt">
            <h2>{moduleName}</h2>
            <ul>
                {items.map((item) => (
                    <li key={item.id} data-start={item.start_date} data-end={item.end_date} data-progress={item.progress}>
                        <button onClick={() => onItemClick?.(item)}>{item.title}</button>
                    </li>
                ))}
            </ul>
        </div>
    ),
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
        updated_at: '2025-06-15T10:00:00Z',
        start_date: '2025-07-01T00:00:00Z',
        target_date: '2025-08-15T00:00:00Z',
        progress_percent: 42,
        tasks: [],
    }),
];

describe('ProjectsGanttView', () => {
    it('renders gantt items from projects', () => {
        render(<ProjectsGanttView projects={projects} />);
        expect(screen.getByText('Portfolio')).toBeInTheDocument();
        expect(screen.getByText('Campamento Juventud')).toBeInTheDocument();
        const item = screen.getByText('Campamento Juventud').closest('li');
        expect(item).toHaveAttribute('data-start', '2025-07-01');
        expect(item).toHaveAttribute('data-end', '2025-08-15');
        expect(item).toHaveAttribute('data-progress', '42');
    });

    it('uses a stable creation-date fallback without treating updates as schedule changes', () => {
        const project = {
            ...projects[0],
            start_date: null,
            target_date: null,
            updated_at: '2026-01-01T10:00:00Z',
        };
        render(<ProjectsGanttView projects={[project]} />);
        const item = screen.getByText('Campamento Juventud').closest('li');
        expect(item).toHaveAttribute('data-start', '2025-06-15');
        expect(item).toHaveAttribute('data-end', '2025-06-15');
    });

    it('calls onItemClick when an item is clicked', () => {
        const onItemClick = vi.fn();
        render(<ProjectsGanttView projects={projects} onItemClick={onItemClick} />);
        screen.getByText('Campamento Juventud').click();
        expect(onItemClick).toHaveBeenCalledWith(expect.objectContaining({ id: 'p1', title: 'Campamento Juventud' }));
    });

    it('computes 0/50/100 PMI progress and renders schedule baseline diagnostics', () => {
        const pmiProjects = [
            createMockProject({
                id: 'p-wbs',
                title: 'Proyecto con paquetes WBS',
                status: 'active',
                start_date: '2026-01-01',
                target_date: null,
                tasks: [
                    createMockTask({ id: 't1', status: 'completed' }),
                    createMockTask({ id: 't2', status: 'in_progress' }),
                    createMockTask({ id: 't3', status: 'todo' }),
                ],
            }),
        ];

        render(<ProjectsGanttView projects={pmiProjects} />);

        const item = screen.getByText('Proyecto con paquetes WBS').closest('li');
        // (100 + 50 + 0) / 3 = 50%
        expect(item).toHaveAttribute('data-progress', '50');
        expect(screen.getByTestId('projects-gantt-pmi-header')).toHaveTextContent(
            'Avance PMI (0/50/100): 50%'
        );
        expect(screen.getByTestId('projects-gantt-baseline-status')).toHaveTextContent(
            '1 sin fecha fin objetivo'
        );
    });
});

