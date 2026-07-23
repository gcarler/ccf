import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { axe } from 'jest-axe';
import EmptyState from './EmptyState';

describe('EmptyState', () => {
    it('renders title and description', () => {
        render(<EmptyState title="Sin datos" description="No hay registros aún." />);
        expect(screen.getByText('Sin datos')).toBeInTheDocument();
        expect(screen.getByText('No hay registros aún.')).toBeInTheDocument();
    });

    it('renders the default Ghost icon', () => {
        const { container } = render(<EmptyState title="Sin datos" description="" />);
        expect(container.querySelector('svg')).toBeInTheDocument();
    });

    it('renders custom action button and calls onAction', () => {
        const handleAction = vi.fn();
        render(<EmptyState title="Sin datos" description="" onAction={handleAction} actionLabel="Crear" />);
        const button = screen.getByRole('button', { name: 'Crear' });
        expect(button).toBeInTheDocument();
        fireEvent.click(button);
        expect(handleAction).toHaveBeenCalledTimes(1);
    });

    it('has no accessibility violations', async () => {
        const { container } = render(
            <EmptyState title="Sin datos" description="No hay registros." onAction={() => {}} actionLabel="Agregar" />
        );
        const results = await axe(container);
        expect(results.violations).toHaveLength(0);
    });
});
