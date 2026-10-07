import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ProjectStatusBadge } from './badges';

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
