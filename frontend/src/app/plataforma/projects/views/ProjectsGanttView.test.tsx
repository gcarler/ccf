import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import ProjectsGanttView from './ProjectsGanttView';
import type { ProjectRecord } from '@/types/projects';

vi.mock('@/components/ui/UniversalGanttView', () => ({
    default: ({ items, moduleName, onItemClick }: { items: Array<{ id: string; title: string }>; moduleName: string; onItemClick?: (item: { id: string; title: string }) => void }) => (
        <div data-testid="gantt">
            <h2>{moduleName}</h2>
            <ul>
                {items.map((item) => (
                    <li key={item.id}>
                        <button onClick={() => onItemClick?.(item)}>{item.title}</button>
                    </li>
                ))}
            </ul>
        </div>
    ),
}));

const projects: ProjectRecord[] = [
    {
        id: 'p1',
        title: 'Campamento Juventud',
        description: 'Organización del campamento',
        status: 'active',
        color: '#2563eb',
        owner_id: 'u1',
        created_at: '2025-06-15T10:00:00Z',
        updated_at: '2025-06-15T10:00:00Z',
        tasks: [],
    } as ProjectRecord,
];

describe('ProjectsGanttView', () => {
    it('renders gantt items from projects', () => {
        render(<ProjectsGanttView projects={projects} />);
        expect(screen.getByText('Portfolio')).toBeInTheDocument();
        expect(screen.getByText('Campamento Juventud')).toBeInTheDocument();
    });

    it('calls onItemClick when an item is clicked', () => {
        const onItemClick = vi.fn();
        render(<ProjectsGanttView projects={projects} onItemClick={onItemClick} />);
        screen.getByText('Campamento Juventud').click();
        expect(onItemClick).toHaveBeenCalledWith(expect.objectContaining({ id: 'p1', title: 'Campamento Juventud' }));
    });
});
