import { fireEvent, render, screen } from '@testing-library/react';
import { axe } from 'jest-axe';
import { describe, expect, it, vi } from 'vitest';
import ProjectsLoadError from './ProjectsLoadError';

describe('ProjectsLoadError', () => {
  it('exposes an accessible retry action only when recovery is available', async () => {
    const onRetry = vi.fn();
    const { container, rerender } = render(
      <ProjectsLoadError message="No se pudo cargar el inbox." onRetry={onRetry} />,
    );

    const alert = screen.getByRole('alert');
    expect(alert).toHaveTextContent('No se pudo cargar el inbox.');
    expect(alert).toHaveClass('text-[hsl(var(--warning-text))]');
    expect(alert).toHaveClass('bg-[hsl(var(--warning-muted))]');
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }));
    expect(onRetry).toHaveBeenCalledOnce();
    expect(screen.getByRole('button', { name: 'Reintentar' })).toHaveClass('text-[hsl(var(--text-primary))]');
    expect((await axe(container)).violations).toEqual([]);

    rerender(<ProjectsLoadError message="Inicia sesión para continuar." />);
    expect(screen.queryByRole('button', { name: 'Reintentar' })).not.toBeInTheDocument();
  });

  it('announces and disables a retry while that retry is running', () => {
    render(<ProjectsLoadError message="Reintentando." onRetry={vi.fn()} retrying />);

    expect(screen.getByRole('button', { name: 'Reintentando…' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Reintentando…' })).toHaveAttribute('aria-busy', 'true');
  });
});
