import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { DSBadge } from './DSBadge';

describe('DSBadge', () => {
    it('renders with label', () => {
        render(<DSBadge label="Test" />);
        expect(screen.getByText('Test')).toBeInTheDocument();
    });

    it('applies slate tone by default', () => {
        render(<DSBadge label="Test" />);
        const badge = screen.getByText('Test');
        expect(badge.className).toContain('bg-[hsl(var(--bg-muted))]/70');
    });

    it('applies blue tone', () => {
        render(<DSBadge label="Test" tone="blue" />);
        const badge = screen.getByText('Test');
        expect(badge.className).toContain('bg-[hsl(var(--info-muted))]');
    });

    it('applies emerald tone', () => {
        render(<DSBadge label="Test" tone="emerald" />);
        const badge = screen.getByText('Test');
        expect(badge.className).toContain('bg-[hsl(var(--success-muted))]');
    });

    it('applies amber tone', () => {
        render(<DSBadge label="Test" tone="amber" />);
        const badge = screen.getByText('Test');
        expect(badge.className).toContain('bg-[hsl(var(--warning-muted))]');
    });

    it('applies custom className', () => {
        render(<DSBadge label="Test" className="custom-class" />);
        const badge = screen.getByText('Test');
        expect(badge.className).toContain('custom-class');
    });

    it('renders as inline element', () => {
        render(<DSBadge label="Test" />);
        const badge = screen.getByText('Test');
        expect(badge.tagName).toBe('SPAN');
    });

    it('has correct styling', () => {
        render(<DSBadge label="Test" />);
        const badge = screen.getByText('Test');
        expect(badge.className).toContain('text-[9px]');
        expect(badge.className).toContain('font-semibold');
        expect(badge.className).toContain('uppercase');
        expect(badge.className).toContain('rounded');
        expect(badge.className).toContain('font-sans');
    });
});
