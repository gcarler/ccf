import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import ProjectsCalendarView from './ProjectsCalendarView';
import { createMockProject } from '@/test-utils/factories';

vi.mock('@/components/ui/UniversalCalendarView', () => ({
    default: ({ events, title, onEventClick }: { events: Array<{ id: string; title: string; date: string }>; title: string; onEventClick?: (event: { id: string; title: string }) => void }) => (
        <div data-testid="calendar">
            <h2>{title}</h2>
            <ul>
                {events.map((event) => (
                    <li key={event.id} data-date={event.date}>
                        <button onClick={() => onEventClick?.(event)}>{event.title}</button>
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
        updated_at: '2025-06-16T10:00:00Z',
        start_date: null,
        target_date: null,
        tasks: [],
    }),
    createMockProject({
        id: 'p3',
        title: 'Encuentro de equipos',
        status: 'active',
        created_at: '2025-06-17T10:00:00Z',
        updated_at: '2025-06-20T10:00:00Z',
        start_date: '2025-07-10T00:00:00Z',
        target_date: null,
        tasks: [],
    }),
];

describe('ProjectsCalendarView', () => {
    it('renders calendar events from projects', () => {
        render(<ProjectsCalendarView projects={projects} />);
        expect(screen.getByText('Calendario de proyectos')).toBeInTheDocument();
        expect(screen.getByText('Campamento Juventud · Entrega')).toBeInTheDocument();
        expect(screen.queryByText('Retiro Pastoral · Inicio')).not.toBeInTheDocument();
        expect(screen.getByText('Campamento Juventud · Entrega').closest('li')).toHaveAttribute('data-date', '2025-08-15');
        expect(screen.getByText('Encuentro de equipos · Inicio').closest('li')).toHaveAttribute('data-date', '2025-07-10');
    });

    it('calls onEventClick when an event is clicked', () => {
        const onEventClick = vi.fn();
        render(<ProjectsCalendarView projects={projects} onEventClick={onEventClick} />);
        screen.getByText('Campamento Juventud · Entrega').click();
        expect(onEventClick).toHaveBeenCalledWith(expect.objectContaining({ id: 'p1', title: 'Campamento Juventud · Entrega' }));
    });
});
