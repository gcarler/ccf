import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import StatusPicker from './StatusPicker';
import type { StatusOption } from './StatusPicker';

vi.mock('framer-motion', () => ({
    motion: {
        div: ({ children, ...props }: any) => <div {...filterMotionProps(props)}>{children}</div>,
    },
    AnimatePresence: ({ children }: any) => <>{children}</>,
}));

function filterMotionProps(props: Record<string, any>): Record<string, any> {
    const skip = new Set(['initial', 'animate', 'exit', 'transition', 'whileHover', 'whileTap', 'layout']);
    const out: Record<string, any> = {};
    for (const [k, v] of Object.entries(props)) {
        if (!skip.has(k)) out[k] = v;
    }
    return out;
}

const options: StatusOption[] = [
    { label: 'Pendiente', value: 'todo', color: 'bg-gray-400', text: 'text-gray-600', bg: 'bg-gray-100' },
    { label: 'En Progreso', value: 'in_progress', color: 'bg-blue-500', text: 'text-blue-600', bg: 'bg-blue-50' },
    { label: 'Completado', value: 'completed', color: 'bg-green-500', text: 'text-green-600', bg: 'bg-green-50' },
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
});
