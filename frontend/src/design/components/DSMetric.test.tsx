import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { DSMetric } from './DSMetric';

describe('DSMetric', () => {
  it('renders label and value', () => {
    render(<DSMetric label="Users" value="1,234" />);
    expect(screen.getByText('Users')).toBeInTheDocument();
    expect(screen.getByText('1,234')).toBeInTheDocument();
  });

  it('renders trend when provided', () => {
    render(<DSMetric label="Users" value="1,234" trend="+12%" />);
    expect(screen.getByText('+12%')).toBeInTheDocument();
  });

  it('does not render trend when not provided', () => {
    render(<DSMetric label="Users" value="1,234" />);
    expect(screen.queryByText('+12%')).not.toBeInTheDocument();
  });

  it('applies blue tone styling to trend', () => {
    render(<DSMetric label="Users" value="1,234" trend="+12%" tone="blue" />);
    const trend = screen.getByText('+12%');
    expect(trend.className).toContain('bg-[hsl(var(--info-muted))]');
  });

  it('applies emerald tone styling to trend', () => {
    render(<DSMetric label="Users" value="1,234" trend="+12%" tone="emerald" />);
    const trend = screen.getByText('+12%');
    expect(trend.className).toContain('bg-[hsl(var(--success-muted))]');
  });

  it('applies amber tone styling to trend', () => {
    render(<DSMetric label="Users" value="1,234" trend="+12%" tone="amber" />);
    const trend = screen.getByText('+12%');
    expect(trend.className).toContain('bg-[hsl(var(--warning-muted))]');
  });

  it('renders icon when provided', () => {
    const TestIcon = () => <span data-testid="icon">Icon</span>;
    render(<DSMetric label="Users" value="1,234" icon={TestIcon} />);
    expect(screen.getByTestId('icon')).toBeInTheDocument();
  });

  it('does not render icon when not provided', () => {
    render(<DSMetric label="Users" value="1,234" />);
    expect(screen.queryByTestId('icon')).not.toBeInTheDocument();
  });

  it('has correct structure', () => {
    render(<DSMetric label="Users" value="1,234" trend="+5" />);
    expect(screen.getByText('Users')).toBeInTheDocument();
    expect(screen.getByText('1,234')).toBeInTheDocument();
    expect(screen.getByText('+5')).toBeInTheDocument();
  });
});
