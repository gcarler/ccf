import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import UniversalCalendarView, { type CalendarEvent } from './UniversalCalendarView';

const today = new Date();
const toKey = (d: Date) => d.toISOString().slice(0, 10);

const mockEvents: CalendarEvent[] = [
    {
        id: 'ev-1',
        title: 'Evento Hoy',
        date: toKey(today),
        color: 'blue',
    },
    {
        id: 'ev-2',
        title: 'Evento Mañana',
        date: toKey(new Date(today.getFullYear(), today.getMonth(), today.getDate() + 1)),
        color: 'emerald',
    },
];

describe('UniversalCalendarView', () => {
    it('renders the title and current month', () => {
        render(<UniversalCalendarView events={mockEvents} title="Calendario de prueba" />);

        expect(screen.getByRole('heading', { name: 'Calendario de prueba' })).toBeInTheDocument();
        expect(screen.getByText(today.toLocaleString('es-ES', { month: 'long', year: 'numeric' }))).toBeInTheDocument();
    });

    it('renders event titles', () => {
        render(<UniversalCalendarView events={mockEvents} />);

        expect(screen.getByText('Evento Hoy')).toBeInTheDocument();
        expect(screen.getByText('Evento Mañana')).toBeInTheDocument();
    });

    it('navigates to previous and next month', async () => {
        render(<UniversalCalendarView events={[]} />);

        const originalMonth = today.toLocaleString('es-ES', { month: 'long', year: 'numeric' });
        expect(screen.getByText(originalMonth)).toBeInTheDocument();

        const prevButton = screen.getByRole('button', { name: /Mes anterior/i });
        const nextButton = screen.getByRole('button', { name: /Mes siguiente/i });

        await userEvent.click(prevButton);
        // Wait for the month to change away from the current month
        await waitFor(() => {
            expect(screen.queryByText(originalMonth)).not.toBeInTheDocument();
        });

        await userEvent.click(nextButton);
        // After moving prev then next, we should be back to the current month
        await waitFor(() => {
            expect(screen.getByText(originalMonth)).toBeInTheDocument();
        });
    });

    it('calls onEventClick when an event is clicked', async () => {
        const onEventClick = vi.fn();
        render(<UniversalCalendarView events={mockEvents} onEventClick={onEventClick} />);

        const eventButton = screen.getByText('Evento Hoy');
        await userEvent.click(eventButton);

        expect(onEventClick).toHaveBeenCalledWith(expect.objectContaining({ id: 'ev-1' }));
    });

    it('calls onDateClick when a day cell is clicked', async () => {
        const onDateClick = vi.fn();
        render(<UniversalCalendarView events={[]} onDateClick={onDateClick} />);

        // Click on the current day cell using its data-testid
        const dayCell = screen.getByTestId(`calendar-day-${today.getDate()}`);
        await userEvent.click(dayCell);    expect(onDateClick).toHaveBeenCalledWith(expect.any(Date));
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<UniversalCalendarView events={mockEvents} title="Calendario" />);
    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });
});
