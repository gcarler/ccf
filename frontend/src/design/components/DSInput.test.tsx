import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { axe } from 'jest-axe';
import { DSInput } from './DSInput';

describe('DSInput', () => {
  it('renders without label', () => {
    render(<DSInput placeholder="Enter text" />);
    expect(screen.getByPlaceholderText('Enter text')).toBeInTheDocument();
  });

  it('renders with label', () => {
    render(<DSInput label="Email" />);
    expect(screen.getByLabelText('Email')).toBeInTheDocument();
  });

  it('shows error message', () => {
    render(<DSInput label="Email" error="Email is required" />);
    expect(screen.getByRole('alert')).toHaveTextContent('Email is required');
  });

  it('shows helper text when no error', () => {
    render(<DSInput label="Email" helperText="We'll never share your email" />);
    expect(screen.getByText("We'll never share your email")).toBeInTheDocument();
  });

  it('does not show helper text when error is present', () => {
    render(
      <DSInput 
        label="Email" 
        error="Error" 
        helperText="Helper text" 
      />
    );
    expect(screen.getByRole('alert')).toHaveTextContent('Error');
    expect(screen.queryByText('Helper text')).not.toBeInTheDocument();
  });

  it('applies error styling', () => {
    render(<DSInput error="Error" />);
    const input = screen.getByRole('textbox');
    expect(input.className).toContain('border-[hsl(var(--danger))]');
  });

  it('is disabled when disabled prop is true', () => {
    render(<DSInput disabled />);
    expect(screen.getByRole('textbox')).toBeDisabled();
  });

  it('is disabled when loading', () => {
    render(<DSInput loading />);
    expect(screen.getByRole('textbox')).toBeDisabled();
  });

  it('shows loading spinner', () => {
    const { container } = render(<DSInput loading />);
    expect(container.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('calls onChange when value changes', () => {
    const handleChange = vi.fn();
    render(<DSInput onChange={handleChange} />);
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'test' } });
    expect(handleChange).toHaveBeenCalledTimes(1);
  });

  it('applies custom className', () => {
    render(<DSInput className="custom-class" />);
    const input = screen.getByRole('textbox');
    expect(input.className).toContain('custom-class');
  });

  it('generates id from label', () => {
    render(<DSInput label="Email Address" />);
    const input = screen.getByRole('textbox');
    expect(input.id).toBe('email-address');
  });

  it('uses custom id when provided', () => {
    render(<DSInput id="custom-id" />);
    const input = screen.getByRole('textbox');
    expect(input.id).toBe('custom-id');
  });

  it('renders with icon', () => {
    const TestIcon = () => <span data-testid="icon">Icon</span>;
    render(<DSInput icon={TestIcon} />);
    expect(screen.getByTestId('icon')).toBeInTheDocument();
  });

  it('forwards ref to the input element', () => {
    const ref = React.createRef<HTMLInputElement>();
    render(<DSInput ref={ref} />);
    expect(ref.current).toBeInstanceOf(HTMLInputElement);
    expect(ref.current?.tagName).toBe('INPUT');
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<DSInput label="Name" />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
