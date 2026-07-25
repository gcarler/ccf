import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import ProjectsCalendarView from './ProjectsCalendarView';
import type { ProjectRecord } from '@/types/projects';

vi.mock('@/components/ui/UniversalCalendarView', () => ({
    default: ({ events, title, onEventClick }: { events: Array<{ id: string; title: string }>; title: string; onEventClick?: (event: { id: string; title: string }) => void }) => (
        <div data-testid="calendar">
            <h2>{title}</h2>
            <ul>
                {events.map((event) => (
                    <li key={event.id}>
                        <button onClick={() => onEventClick?.(event)}>{event.title}</button>
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
    {
        id: 'p2',
        title: 'Retiro Pastoral',
        description: 'Planificación del retiro',
        status: 'completed',
        color: '#8b5cf6',
        owner_id: 'u2',
        created_at: '2025-06-16T10:00:00Z',
        updated_at: '2025-06-16T10:00:00Z',
        tasks: [],
    } as ProjectRecord,
];

describe('ProjectsCalendarView', () => {
    it('renders calendar events from projects', () => {
        render(<ProjectsCalendarView projects={projects} />);
        expect(screen.getByText('Calendario de proyectos')).toBeInTheDocument();
        expect(screen.getByText('Campamento Juventud')).toBeInTheDocument();
        expect(screen.getByText('Retiro Pastoral')).toBeInTheDocument();
    });

    it('calls onEventClick when an event is clicked', () => {
        const onEventClick = vi.fn();
        render(<ProjectsCalendarView projects={projects} onEventClick={onEventClick} />);
        screen.getByText('Campamento Juventud').click();
        expect(onEventClick).toHaveBeenCalledWith(expect.objectContaining({ id: 'p1', title: 'Campamento Juventud' }));
    });
});
