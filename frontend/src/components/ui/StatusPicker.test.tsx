/* eslint-disable @typescript-eslint/no-explicit-any */
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { axe } from 'jest-axe';
import { filterMotionProps } from '@/test-utils/filter-motion-props';
import StatusPicker from './StatusPicker';
import type { StatusOption } from './StatusPicker';

vi.mock('framer-motion', () => ({
    motion: {
        div: ({ children, ...props }: any) => <div {...filterMotionProps(props)}>{children}</div>,
    },
    AnimatePresence: ({ children }: any) => <>{children}</>,
}));

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

    it('has no accessibility violations', async () => {
        const { container } = render(<StatusPicker currentValue="todo" options={options} onSelect={vi.fn()} />);
        const results = await axe(container);
        expect(results.violations).toHaveLength(0);
    });
});
