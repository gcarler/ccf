import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { DSCard } from './DSCard';

describe('DSCard', () => {
  it('renders children', () => {
    render(<DSCard>Card content</DSCard>);
    expect(screen.getByText('Card content')).toBeInTheDocument();
  });

  it('applies light theme by default', () => {
    const { container } = render(<DSCard>Content</DSCard>);
    const card = container.firstChild as HTMLElement;
    expect(card.className).toContain('bg-[hsl(var(--bg-primary))]');
  });

  it('applies dark theme', () => {
    const { container } = render(<DSCard tone="dark">Content</DSCard>);
    const card = container.firstChild as HTMLElement;
    expect(card.className).toContain('bg-[hsl(var(--bg-primary))]/5');
  });

  it('applies glass theme', () => {
    const { container } = render(<DSCard tone="glass">Content</DSCard>);
    const card = container.firstChild as HTMLElement;
    expect(card.className).toContain('bg-white/10');
  });

  it('applies medium padding by default', () => {
    const { container } = render(<DSCard>Content</DSCard>);
    const card = container.firstChild as HTMLElement;
    expect(card.className).toContain('p-3');
  });

  it('applies small padding', () => {
    const { container } = render(<DSCard padding="sm">Content</DSCard>);
    const card = container.firstChild as HTMLElement;
    expect(card.className).toContain('p-2');
  });

  it('applies custom className', () => {
    const { container } = render(<DSCard className="custom-class">Content</DSCard>);
    const card = container.firstChild as HTMLElement;
    expect(card.className).toContain('custom-class');
  });

  it('applies rounded corners', () => {
    const { container } = render(<DSCard>Content</DSCard>);
    const card = container.firstChild as HTMLElement;
    expect(card.className).toContain('rounded-lg');
  });

  it('applies shadow', () => {
    const { container } = render(<DSCard>Content</DSCard>);
    const card = container.firstChild as HTMLElement;
    expect(card.className).toContain('shadow-sm');
  });
});
