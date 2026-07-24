import React from 'react';
import { render } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { axe } from 'jest-axe';
import { DSSkeleton } from './DSSkeleton';

describe('DSSkeleton', () => {
    it('renders', () => {
        const { container } = render(<DSSkeleton />);
        expect(container.firstChild).toBeInTheDocument();
    });

    it('applies md rounded by default', () => {
        const { container } = render(<DSSkeleton />);
        const skeleton = container.firstChild as HTMLElement;
        expect(skeleton.className).toContain('rounded-md');
    });

    it('applies sm rounded', () => {
        const { container } = render(<DSSkeleton rounded="sm" />);
        const skeleton = container.firstChild as HTMLElement;
        expect(skeleton.className).toContain('rounded');
        expect(skeleton.className).not.toContain('rounded-md');
    });

    it('applies lg rounded', () => {
        const { container } = render(<DSSkeleton rounded="lg" />);
        const skeleton = container.firstChild as HTMLElement;
        expect(skeleton.className).toContain('rounded-lg');
    });

    it('applies xl rounded', () => {
        const { container } = render(<DSSkeleton rounded="xl" />);
        const skeleton = container.firstChild as HTMLElement;
        expect(skeleton.className).toContain('rounded-xl');
    });

    it('applies pill rounded', () => {
        const { container } = render(<DSSkeleton rounded="pill" />);
        const skeleton = container.firstChild as HTMLElement;
        expect(skeleton.className).toContain('rounded-full');
    });

    it('does not apply border radius when rounded is none', () => {
        const { container } = render(<DSSkeleton rounded="none" />);
        const skeleton = container.firstChild as HTMLElement;
        expect(skeleton.className).not.toContain('rounded');
    });

    it('applies custom className', () => {
        const { container } = render(<DSSkeleton className="custom-class" />);
        const skeleton = container.firstChild as HTMLElement;
        expect(skeleton.className).toContain('custom-class');
    });

    it('applies custom className for sizing', () => {
        const { container } = render(<DSSkeleton className="w-[100px]" />);
        const skeleton = container.firstChild as HTMLElement;
        expect(skeleton.className).toContain('w-[100px]');
    });

    it('has shimmer animation', () => {
        const { container } = render(<DSSkeleton />);
        const shimmer = container.querySelector('[class*="animate"]');
        expect(shimmer).toBeInTheDocument();
    });

    it('has no accessibility violations', async () => {
        const { container } = render(<DSSkeleton />);
        expect(await axe(container)).toHaveNoViolations();
    });
});
