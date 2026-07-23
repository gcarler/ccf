import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { DSCommandEntry } from './DSCommandEntry';
import { Home } from 'lucide-react';

describe('DSCommandEntry', () => {
    it('renders with label', () => {
        render(<DSCommandEntry label="Command" />);
        expect(screen.getByText('Command')).toBeInTheDocument();
    });

    it('renders with description', () => {
        render(<DSCommandEntry label="Command" description="Description" />);
        expect(screen.getByText('Description')).toBeInTheDocument();
    });

    it('renders with shortcut', () => {
        render(<DSCommandEntry label="Command" shortcut="G C" />);
        expect(screen.getByText('G C')).toBeInTheDocument();
    });

    it('applies active state', () => {
        const { container } = render(<DSCommandEntry label="Command" active />);
        const root = container.firstChild as HTMLElement;
        expect(root.className).toContain('border-[hsl(var(--primary)_/_0.4)]');
    });

    it('applies inactive state', () => {
        const { container } = render(<DSCommandEntry label="Command" />);
        const root = container.firstChild as HTMLElement;
        expect(root.className).toContain('border-[hsl(var(--border))]');
    });

    it('renders with icon', () => {
        render(<DSCommandEntry label="Command" icon={Home} />);
        const svg = document.querySelector('svg');
        expect(svg).toBeInTheDocument();
    });

    it('renders default icon when no icon provided', () => {
        const { container } = render(<DSCommandEntry label="Command" />);
        const svg = container.querySelector('svg');
        expect(svg).toBeInTheDocument();
    });

    it('applies custom className', () => {
        const { container } = render(<DSCommandEntry label="Command" className="custom-class" />);
        const root = container.firstChild as HTMLElement;
        expect(root.className).toContain('custom-class');
    });

    it('has cursor pointer', () => {
        const { container } = render(<DSCommandEntry label="Command" />);
        const root = container.firstChild as HTMLElement;
        expect(root.className).toContain('cursor-pointer');
    });

    it('renders shortcut with correct styling', () => {
        render(<DSCommandEntry label="Command" shortcut="G C" />);
        const shortcut = screen.getByText('G C');
        expect(shortcut.className).toContain('text-[9px]');
        expect(shortcut.className).toContain('uppercase');
    });
});
