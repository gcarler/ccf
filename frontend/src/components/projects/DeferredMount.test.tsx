import { fireEvent, render, screen } from '@testing-library/react';
import { useState } from 'react';
import { describe, expect, it } from 'vitest';
import { DeferredMount } from './DeferredMount';

describe('DeferredMount', () => {
  it('waits for first open and stays mounted afterward for close lifecycle', async () => {
    const Panel = ({ open }: { open: boolean }) => (
      <div data-testid="panel" data-open={String(open)}>Panel</div>
    );
    const Harness = () => {
      const [open, setOpen] = useState(false);
      return (
        <>
          <button onClick={() => setOpen((value) => !value)}>Toggle</button>
          <DeferredMount open={open}><Panel open={open} /></DeferredMount>
        </>
      );
    };

    render(<Harness />);
    expect(screen.queryByTestId('panel')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Toggle' }));
    expect(await screen.findByTestId('panel')).toHaveAttribute('data-open', 'true');

    fireEvent.click(screen.getByRole('button', { name: 'Toggle' }));
    expect(screen.getByTestId('panel')).toHaveAttribute('data-open', 'false');
  });
});
