import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

vi.mock('@/components/ErrorBoundary', () => ({
  default: ({ moduleName }: { moduleName: string }) => (
    <section role="alert" data-testid="error-boundary">
      Falló el módulo {moduleName}
    </section>
  ),
}));

import ProjectsLoading from './loading';
import ProjectsError from './error';

describe('ProjectsLoading — esqueleto del portafolio PMI', () => {
  it('expone el contenedor raíz con testid, role status y aria-label PMI', () => {
    render(<ProjectsLoading />);

    const skeleton = screen.getByTestId('projects-portfolio-loading-skeleton');
    expect(skeleton).toBeInTheDocument();
    expect(skeleton).toHaveAttribute('role', 'status');
    expect(skeleton).toHaveAttribute('aria-label', 'Cargando portafolio de proyectos PMI');
    expect(skeleton.className).toContain('bg-[hsl(var(--background))]');
    expect(skeleton.querySelectorAll('div').length).toBeGreaterThan(0);
  });

  it('no agrega contraste con colores Tailwind hardcodeados', () => {
    const { container } = render(<ProjectsLoading />);
    const html = container.innerHTML;
    expect(html).not.toMatch(/(?:bg|text|border)-(?:white|black|red|blue|gray|green)-\d{2,3}/);
    expect(html).toContain('bg-[hsl(var(--surface-1))]');
    expect(html).toContain('bg-[hsl(var(--surface-2))]');
  });
});

describe('ProjectsError — default export de error.tsx', () => {
  it('renderiza el ErrorBoundary del módulo Proyectos', () => {
    render(<ProjectsError />);

    const boundary = screen.getByTestId('error-boundary');
    expect(boundary).toBeInTheDocument();
    expect(boundary).toHaveAttribute('role', 'alert');
    expect(boundary).toHaveTextContent('Falló el módulo Proyectos');
  });
});
