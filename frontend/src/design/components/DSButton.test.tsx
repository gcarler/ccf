import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { DSButton } from './DSButton';

describe('DSButton', () => {
  it('renders with children', () => {
    render(<DSButton>Click me</DSButton>);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });

  it('applies primary variant by default', () => {
    render(<DSButton>Button</DSButton>);
    const button = screen.getByRole('button');
    expect(button.className).toContain('shadow-sm');
  });

  it('applies secondary variant', () => {
    render(<DSButton variant="secondary">Button</DSButton>);
    const button = screen.getByRole('button');
    expect(button.className).toContain('border-white/20');
  });

  it('applies ghost variant', () => {
    render(<DSButton variant="ghost">Button</DSButton>);
    const button = screen.getByRole('button');
    expect(button.className).toContain('border-white/30');
  });

  it('shows loading state', () => {
    render(<DSButton loading>Loading</DSButton>);
    expect(screen.getByText('Cargando...')).toBeInTheDocument();
  });

  it('is disabled when loading', () => {
    render(<DSButton loading>Button</DSButton>);
    const button = screen.getByRole('button');
    expect(button).toBeDisabled();
  });

  it('is disabled when disabled prop is true', () => {
    render(<DSButton disabled>Button</DSButton>);
    const button = screen.getByRole('button');
    expect(button).toBeDisabled();
  });

  it('calls onClick when clicked', () => {
    const handleClick = vi.fn();
    render(<DSButton onClick={handleClick}>Button</DSButton>);
    fireEvent.click(screen.getByRole('button'));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('does not call onClick when disabled', () => {
    const handleClick = vi.fn();
    render(<DSButton onClick={handleClick} disabled>Button</DSButton>);
    fireEvent.click(screen.getByRole('button'));
    expect(handleClick).not.toHaveBeenCalled();
  });

  it('does not call onClick when loading', () => {
    const handleClick = vi.fn();
    render(<DSButton onClick={handleClick} loading>Button</DSButton>);
    fireEvent.click(screen.getByRole('button'));
    expect(handleClick).not.toHaveBeenCalled();
  });

  it('applies custom className', () => {
    render(<DSButton className="custom-class">Button</DSButton>);
    const button = screen.getByRole('button');
    expect(button.className).toContain('custom-class');
  });

  it('passes additional props', () => {
    render(<DSButton data-testid="custom-button">Button</DSButton>);
    expect(screen.getByTestId('custom-button')).toBeInTheDocument();
  });
});
