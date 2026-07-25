import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import UniversalGanttView, { type GanttItem } from './UniversalGanttView';

const today = new Date();
const toIso = (offset: number) => {
    const d = new Date(today);
    d.setDate(d.getDate() + offset);
    return d.toISOString().slice(0, 10);
};

const mockItems: GanttItem[] = [
    {
        id: 'gantt-1',
        title: 'Tarea Gantt 1',
        subtitle: 'Fase inicial',
        start_date: toIso(0),
        end_date: toIso(5),
        color: 'blue',
        progress: 50,
    },
    {
        id: 'gantt-2',
        title: 'Tarea Gantt 2',
        start_date: toIso(2),
        end_date: toIso(7),
        color: 'emerald',
        progress: 25,
    },
];

describe('UniversalGanttView', () => {
    it('renders the module name and items', () => {
        render(<UniversalGanttView items={mockItems} moduleName="Cronograma de prueba" />);

        expect(screen.getByText('Cronograma de prueba')).toBeInTheDocument();
        expect(screen.getByText('Tarea Gantt 1')).toBeInTheDocument();
        expect(screen.getByText('Tarea Gantt 2')).toBeInTheDocument();
    });

    it('shows empty state when no items are provided', () => {
        render(<UniversalGanttView items={[]} />);

        expect(screen.getByText('No se detectan secuencias temporales activas')).toBeInTheDocument();
    });

    it('calls onItemClick when a bar is clicked', async () => {
        const onItemClick = vi.fn();
        render(<UniversalGanttView items={mockItems} onItemClick={onItemClick} />);

        const bar = screen.getByTestId('gantt-bar-gantt-1');
        await userEvent.click(bar);

        expect(onItemClick).toHaveBeenCalledWith(expect.objectContaining({ id: 'gantt-1' }));
    });

    it('calls onOptimize when optimize button is clicked', async () => {
        const onOptimize = vi.fn();
        render(<UniversalGanttView items={mockItems} onOptimize={onOptimize} />);

        const button = screen.getByRole('button', { name: /Optimus Brain/i });
        await userEvent.click(button);

        expect(onOptimize).toHaveBeenCalledTimes(1);
    });

    it('allows switching zoom levels', async () => {
        render(<UniversalGanttView items={mockItems} />);

        const dayButton = screen.getByRole('button', { name: /Día/i });
        const weekButton = screen.getByRole('button', { name: /Semana/i });
        const monthButton = screen.getByRole('button', { name: /Mes/i });

        // Week is the default active zoom
        expect(weekButton).toHaveAttribute('aria-pressed', 'true');

        await userEvent.click(dayButton);
        expect(dayButton).toHaveAttribute('aria-pressed', 'true');

        await userEvent.click(monthButton);
        expect(monthButton).toHaveAttribute('aria-pressed', 'true');
    });
});
