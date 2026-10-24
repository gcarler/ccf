import { useRef } from 'react';
import { act, fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useResizablePanel } from './useResizablePanel';
import { PanelResizeHandle } from '@/components/ui/PanelResizeHandle';

function Harness({ enabled = true }: { enabled?: boolean }) {
  const panelRef = useRef<HTMLDivElement>(null);
  const resize = useResizablePanel({
    storageKey: 'test:panel',
    defaultWidth: 600,
    panelRef,
    enabled,
  });
  return (
    <div ref={panelRef} data-testid="panel" style={resize.style}>
      <PanelResizeHandle resize={resize} />
    </div>
  );
}

beforeEach(() => {
  localStorage.clear();
  Object.defineProperty(window, 'innerWidth', { value: 1440, writable: true });
  vi.stubGlobal('PointerEvent', MouseEvent);
});

describe('persistent panel resizing', () => {
  it('resizes by dragging beyond the handle, saves on release and restores on reopening', () => {
    const first = render(<Harness />);
    fireEvent.pointerDown(screen.getByRole('separator'), {
      clientX: 840,
      button: 0,
    });
    fireEvent.pointerMove(window, { clientX: 720 });
    expect(screen.getByTestId('panel')).toHaveStyle({ width: '720px' });
    fireEvent.pointerUp(window);
    expect(localStorage.getItem('test:panel')).toBe('720');
    first.unmount();
    render(<Harness />);
    expect(screen.getByTestId('panel')).toHaveStyle({ width: '720px' });
  });

  it('supports keyboard limits, accelerated steps and double click reset', () => {
    render(<Harness />);
    const separator = screen.getByRole('separator');
    fireEvent.keyDown(separator, { key: 'ArrowLeft', shiftKey: true });
    expect(separator).toHaveAttribute('aria-valuenow', '680');
    fireEvent.keyDown(separator, { key: 'Home' });
    expect(separator).toHaveAttribute('aria-valuenow', '300');
    fireEvent.keyDown(separator, { key: 'End' });
    expect(separator).toHaveAttribute('aria-valuenow', '1392');
    fireEvent.doubleClick(separator);
    expect(separator).toHaveAttribute('aria-valuenow', '600');
  });

  it('preserves the chosen width during maximization and mobile viewport changes', () => {
    localStorage.setItem('test:panel', '800');
    const view = render(<Harness />);
    view.rerender(<Harness enabled={false} />);
    view.rerender(<Harness />);
    expect(screen.getByTestId('panel')).toHaveStyle({ width: '800px' });
    act(() => {
      window.innerWidth = 390;
      window.dispatchEvent(new Event('resize'));
    });
    expect(screen.getByTestId('panel')).toHaveStyle({ width: '100%' });
    expect(screen.queryByRole('separator')).not.toBeInTheDocument();
    act(() => {
      window.innerWidth = 1440;
      window.dispatchEvent(new Event('resize'));
    });
    expect(screen.getByTestId('panel')).toHaveStyle({ width: '800px' });
  });

  it('cleans up cancelled and interrupted drags, including unmount', () => {
    const view = render(<Harness />);
    fireEvent.pointerDown(screen.getByRole('separator'), {
      clientX: 700,
      button: 0,
    });
    fireEvent.pointerCancel(window);
    expect(document.body.style.cursor).toBe('');
    fireEvent.pointerDown(screen.getByRole('separator'), {
      clientX: 700,
      button: 0,
    });
    view.unmount();
    expect(document.body.style.userSelect).toBe('');
    expect(document.body.style.cursor).toBe('');
  });

  it('ignores corrupt stored values and remains usable when persistence is unavailable', () => {
    localStorage.setItem('test:panel', 'Infinity');
    const save = vi
      .spyOn(Storage.prototype, 'setItem')
      .mockImplementation(() => {
        throw new Error('blocked');
      });
    render(<Harness />);
    fireEvent.keyDown(screen.getByRole('separator'), { key: 'ArrowRight' });
    expect(screen.getByTestId('panel')).toHaveStyle({ width: '576px' });
    save.mockRestore();
  });
});
