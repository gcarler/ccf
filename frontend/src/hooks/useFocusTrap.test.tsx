import { useRef, useState } from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { useFocusTrap } from './useFocusTrap';

function FocusTrapHarness() {
  const [active, setActive] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  useFocusTrap(panelRef, {
    active,
    onEscape: () => setActive(false),
  });

  return (
    <>
      <button type="button" onClick={() => setActive(true)}>
        Abrir
      </button>
      {active && (
        <div ref={panelRef}>
          <button type="button">Primero</button>
          <button type="button">Último</button>
        </div>
      )}
    </>
  );
}

describe('useFocusTrap', () => {
  it('cycles keyboard focus and restores the opener after deactivation', async () => {
    const offsetParentSpy = vi
      .spyOn(HTMLElement.prototype, 'offsetParent', 'get')
      .mockImplementation(function (this: HTMLElement) {
        return this.parentElement;
      });

    try {
      render(<FocusTrapHarness />);
      const user = userEvent.setup();
      const opener = screen.getByRole('button', { name: 'Abrir' });
      await user.click(opener);

      const first = screen.getByRole('button', { name: 'Primero' });
      const last = screen.getByRole('button', { name: 'Último' });
      expect(first).toHaveFocus();

      await user.keyboard('{Shift>}{Tab}{/Shift}');
      expect(last).toHaveFocus();

      await user.keyboard('{Escape}');

      await waitFor(() => expect(opener).toHaveFocus());
      expect(
        screen.queryByRole('button', { name: 'Último' })
      ).not.toBeInTheDocument();
    } finally {
      offsetParentSpy.mockRestore();
    }
  });
});
