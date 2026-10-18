import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { PmiHealthBadge, ProjectStatusBadge } from './badges';

describe('ProjectStatusBadge semantic theme tokens', () => {
  it.each([
    ['on_hold', 'En Pausa', '--surface-2'],
    ['archived', 'Archivado', '--surface-3'],
  ])('uses semantic surface and border tokens for %s', (status, label, surfaceToken) => {
    render(<ProjectStatusBadge value={status} />);
    const badge = screen.getByText(label);
    expect(badge.className).toContain(`hsl(var(${surfaceToken}))`);
    expect(badge.className).toContain('hsl(var(--border))');
    expect(badge.className).not.toMatch(/(?:bg|border)-white\//);
  });
});

describe('PmiHealthBadge índice compuesto PMI (CPI/SPI)', () => {
  it('evalúa los 3 umbrales del índice compuesto con tokens semánticos', () => {
    // Óptimo: ambos >= 0.95 (incluidos null/undefined evaluados como 1)
    const { unmount: unmountOptimal } = render(<PmiHealthBadge cpi={1.1} spi={0.98} />);
    let badge = screen.getByTestId('pmi-health-badge');
    expect(badge).toHaveTextContent('Optimo PMI');
    expect(badge.className).toContain('text-[hsl(var(--success))]');
    unmountOptimal();

    // Crítico: cualquiera < 0.85
    const { unmount: unmountCritical } = render(<PmiHealthBadge cpi={0.7} spi={1.0} />);
    badge = screen.getByTestId('pmi-health-badge');
    expect(badge).toHaveTextContent('Critico PMI');
    expect(badge.className).toContain('text-[hsl(var(--destructive))]');
    unmountCritical();

    // En Vigilancia: entre 0.85 y 0.95
    const { unmount: unmountWatch } = render(<PmiHealthBadge cpi={0.9} spi={0.92} />);
    badge = screen.getByTestId('pmi-health-badge');
    expect(badge).toHaveTextContent('En Vigilancia PMI');
    expect(badge.className).toContain('text-[hsl(var(--warning))]');
    unmountWatch();

    // Sin índices (null/undefined → 1) ⇒ Óptimo
    render(<PmiHealthBadge />);
    expect(screen.getByTestId('pmi-health-badge')).toHaveTextContent('Optimo PMI');
  });
});
