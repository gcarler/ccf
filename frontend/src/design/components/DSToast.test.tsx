import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { DSToast, toast } from './DSToast';

describe('DSToast', () => {
  beforeEach(() => {
    // Clear all toasts before each test
    toast.getToasts().forEach((t) => toast.dismiss(t.id));
  });

  it('renders success toast', () => {
    render(<DSToast type="success" message="Success message" />);
    expect(screen.getByText('Success message')).toBeInTheDocument();
  });

  it('renders error toast', () => {
    render(<DSToast type="error" message="Error message" />);
    expect(screen.getByText('Error message')).toBeInTheDocument();
  });

  it('renders warning toast', () => {
    render(<DSToast type="warning" message="Warning message" />);
    expect(screen.getByText('Warning message')).toBeInTheDocument();
  });

  it('renders info toast', () => {
    render(<DSToast type="info" message="Info message" />);
    expect(screen.getByText('Info message')).toBeInTheDocument();
  });

  it('calls onClose when close button is clicked', () => {
    const handleClose = vi.fn();
    render(<DSToast type="success" message="Message" onClose={handleClose} />);
    
    fireEvent.click(screen.getByLabelText('Cerrar'));
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it('does not render close button when onClose is not provided', () => {
    render(<DSToast type="success" message="Message" />);
    expect(screen.queryByLabelText('Cerrar')).not.toBeInTheDocument();
  });

  it('renders action button when provided', () => {
    const handleAction = vi.fn();
    render(
      <DSToast 
        type="success" 
        message="Message" 
        action={{ label: 'Undo', onClick: handleAction }}
      />
    );
    
    expect(screen.getByText('Undo')).toBeInTheDocument();
    fireEvent.click(screen.getByText('Undo'));
    expect(handleAction).toHaveBeenCalledTimes(1);
  });

  it('has correct aria attributes', () => {
    render(<DSToast type="success" message="Message" />);
    const toastEl = screen.getByRole('alert');
    expect(toastEl).toHaveAttribute('aria-live', 'polite');
  });
});

describe('toast function', () => {
  beforeEach(() => {
    // Clear all toasts before each test
    toast.getToasts().forEach((t) => toast.dismiss(t.id));
  });

  it('creates success toast', () => {
    const id = toast.success('Success');
    expect(id).toBeGreaterThan(0);
    expect(toast.getToasts()).toHaveLength(1);
  });

  it('creates error toast', () => {
    const id = toast.error('Error');
    expect(id).toBeGreaterThan(0);
    expect(toast.getToasts()).toHaveLength(1);
  });

  it('creates warning toast', () => {
    const id = toast.warning('Warning');
    expect(id).toBeGreaterThan(0);
    expect(toast.getToasts()).toHaveLength(1);
  });

  it('creates info toast', () => {
    const id = toast.info('Info');
    expect(id).toBeGreaterThan(0);
    expect(toast.getToasts()).toHaveLength(1);
  });

  it('dismisses toast', () => {
    const id = toast.success('Message');
    expect(toast.getToasts()).toHaveLength(1);
    toast.dismiss(id);
    expect(toast.getToasts()).toHaveLength(0);
  });

  it('subscribes to toast changes', () => {
    const subscriber = vi.fn();
    const unsubscribe = toast.subscribe(subscriber);
    
    toast.success('Message');
    expect(subscriber).toHaveBeenCalled();
    
    unsubscribe();
  });

  it('auto-dismisses after duration', async () => {
    vi.useFakeTimers();
    
    toast.success('Message', 1000);
    expect(toast.getToasts()).toHaveLength(1);
    
    vi.advanceTimersByTime(1000);
    expect(toast.getToasts()).toHaveLength(0);
    
    vi.useRealTimers();
  });
});
