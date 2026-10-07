import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import ConfirmDeleteDrawer from './ConfirmDeleteDrawer';

vi.mock('@/components/ui/RightPanel', () => ({
  RightPanel: ({ open, children }: React.PropsWithChildren<{ open: boolean }>) => open
    ? <aside role="complementary" aria-label="Confirmación de eliminación">{children}</aside>
    : null,
}));

describe('ConfirmDeleteDrawer retry behavior', () => {
  it('keeps the drawer open after a rejected deletion and closes after a successful retry', async () => {
    const onConfirm = vi.fn().mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce(undefined);
    const onClose = vi.fn();
    render(
      <ConfirmDeleteDrawer
        open
        onClose={onClose}
        onConfirm={onConfirm}
        description="Se eliminará el hito del proyecto."
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: 'Eliminar' }));
    await waitFor(() => expect(onConfirm).toHaveBeenCalledTimes(1));
    expect(onClose).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: 'Eliminar' })).toBeEnabled();

    fireEvent.click(screen.getByRole('button', { name: 'Eliminar' }));
    await waitFor(() => expect(onClose).toHaveBeenCalledTimes(1));
    expect(onConfirm).toHaveBeenCalledTimes(2);
  });
});
