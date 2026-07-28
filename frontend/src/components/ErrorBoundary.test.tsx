import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import ErrorBoundary from './ErrorBoundary';

const ProblemChild = () => {
  throw new Error('Test Error');
};

describe('ErrorBoundary component', () => {
  it('renders children when there is no error', () => {
    render(
      <ErrorBoundary>
        <div>Content Normal</div>
      </ErrorBoundary>
    );

    expect(screen.getByText('Content Normal')).toBeInTheDocument();
  });

  it('renders default fallback UI when a child throws an error', () => {
    // Prevent console.error from polluting stdout during intended exception test
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    render(
      <ErrorBoundary moduleName="CRM">
        <ProblemChild />
      </ErrorBoundary>
    );

    expect(screen.getByText('Algo salió mal')).toBeInTheDocument();
    expect(screen.getByText(/CRM/i)).toBeInTheDocument();

    consoleSpy.mockRestore();
  });

  it('renders custom fallback prop when provided', () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    render(
      <ErrorBoundary fallback={<div>Custom Error UI</div>}>
        <ProblemChild />
      </ErrorBoundary>
    );

    expect(screen.getByText('Custom Error UI')).toBeInTheDocument();

    consoleSpy.mockRestore();
  });
});
