import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { axe } from 'jest-axe';
import { filterMotionProps } from '@/test-utils/filter-motion-props';
import StatusPicker from './StatusPicker';
import type { StatusOption } from './StatusPicker';

vi.mock('framer-motion', () => ({
    motion: {
        div: ({ children, ...props }: React.HTMLAttributes<HTMLDivElement> & Record<string, unknown>) => <div {...filterMotionProps(props)}>{children}</div>,
    },
    AnimatePresence: ({ children }: { children?: React.ReactNode }) => <>{children}</>,
}));

const options: StatusOption[] = [
    { label: 'Pendiente', value: 'todo', color: 'bg-[hsl(var(--muted-foreground))]', text: 'text-[hsl(var(--muted-foreground))]', bg: 'bg-[hsl(var(--surface-2))]' },
    { label: 'En Progreso', value: 'in_progress', color: 'bg-[hsl(var(--info))]', text: 'text-[hsl(var(--info))]', bg: 'bg-[hsl(var(--info)/0.1)]' },
    { label: 'Completado', value: 'completed', color: 'bg-[hsl(var(--success))]', text: 'text-[hsl(var(--success))]', bg: 'bg-[hsl(var(--success)/0.1)]' },
];

describe('StatusPicker', () => {
    it('renders with the current value label', () => {
        render(<StatusPicker currentValue="todo" options={options} onSelect={vi.fn()} />);
        expect(screen.getByText('Pendiente')).toBeInTheDocument();
    });

    it('opens dropdown on click and shows all options', () => {
        render(<StatusPicker currentValue="todo" options={options} onSelect={vi.fn()} />);
        fireEvent.click(screen.getByText('Pendiente'));
        expect(screen.getByText('En Progreso')).toBeInTheDocument();
        expect(screen.getByText('Completado')).toBeInTheDocument();
    });

    it('calls onSelect when an option is clicked', () => {
        const onSelect = vi.fn();
        render(<StatusPicker currentValue="todo" options={options} onSelect={onSelect} />);
        fireEvent.click(screen.getByText('Pendiente'));
        fireEvent.click(screen.getByText('Completado'));
        expect(onSelect).toHaveBeenCalledWith('completed');
    });

    it('has no accessibility violations', async () => {
        const { container } = render(<StatusPicker currentValue="todo" options={options} onSelect={vi.fn()} />);
        const results = await axe(container);
        expect(results.violations).toHaveLength(0);
    });
});
