import { render, screen } from '@testing-library/react';
import { axe } from 'jest-axe';
import { describe, it, expect, vi } from 'vitest';
import { PanelResizeHandle } from './PanelResizeHandle';

describe('PanelResizeHandle accessibility', () => {
  it('exposes an accessible keyboard separator with current bounds', async () => {
    const { container } = render(
      <main>
        <PanelResizeHandle
          resize={{
            width: 600,
            minWidth: 300,
            maxWidth: 1000,
            desktop: true,
            dragging: false,
            style: {},
            onPointerDown: vi.fn(),
            onKeyDown: vi.fn(),
            reset: vi.fn(),
          }}
        />
      </main>
    );
    expect(screen.getByRole('separator')).toHaveAttribute('tabindex', '0');
    expect(screen.getByRole('separator')).toHaveAttribute(
      'aria-valuenow',
      '600'
    );
    expect((await axe(container)).violations).toEqual([]);
  });
});
