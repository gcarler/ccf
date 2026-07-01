import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { DSToolbarChip } from './DSToolbarChip';
import { Home } from 'lucide-react';

describe('DSToolbarChip', () => {
    it('renders with label', () => {
        render(<DSToolbarChip label="Filter" />);
        expect(screen.getByText('Filter')).toBeInTheDocument();
    });

    it('applies soft variant by default', () => {
        render(<DSToolbarChip label="Filter" />);
        const chip = screen.getByRole('button');
        expect(chip.className).toContain('border-[hsl(var(--border))]');
    });

    it('applies solid variant when active', () => {
        render(<DSToolbarChip label="Filter" active />);
        const chip = screen.getByRole('button');
        expect(chip.className).toContain('text-white');
    });

    it('applies outline variant', () => {
        render(<DSToolbarChip label="Filter" variant="outline" />);
        const chip = screen.getByRole('button');
        expect(chip.className).toContain('border-white/20');
    });

    it('calls onClick when clicked', () => {
        const handleClick = vi.fn();
        render(<DSToolbarChip label="Filter" onClick={handleClick} />);
        fireEvent.click(screen.getByRole('button'));
        expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it('renders with icon', () => {
        render(<DSToolbarChip label="Filter" icon={Home} />);
        const svg = document.querySelector('svg');
        expect(svg).toBeInTheDocument();
    });

    it('applies sm size', () => {
        render(<DSToolbarChip label="Filter" size="sm" />);
        const chip = screen.getByRole('button');
        expect(chip.className).toContain('px-2');
    });

    it('applies md size', () => {
        render(<DSToolbarChip label="Filter" size="md" />);
        const chip = screen.getByRole('button');
        expect(chip.className).toContain('px-2.5');
    });

    it('applies dark tone', () => {
        render(<DSToolbarChip label="Filter" tone="dark" />);
        const chip = screen.getByRole('button');
        expect(chip).toHaveAttribute('class');
    });

    it('applies custom className', () => {
        render(<DSToolbarChip label="Filter" className="custom-class" />);
        const chip = screen.getByRole('button');
        expect(chip.className).toContain('custom-class');
    });
});
