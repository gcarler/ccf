import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { DSSelect } from './DSSelect';

const sampleOptions = [
    { value: 'opt1', label: 'Option 1' },
    { value: 'opt2', label: 'Option 2' },
    { value: 'opt3', label: 'Option 3' },
];

describe('DSSelect', () => {
    it('renders with options', () => {
        render(<DSSelect options={sampleOptions} />);
        const select = screen.getByRole('combobox');
        expect(select).toBeInTheDocument();
        expect(screen.getByText('Option 1')).toBeInTheDocument();
        expect(screen.getByText('Option 2')).toBeInTheDocument();
        expect(screen.getByText('Option 3')).toBeInTheDocument();
    });

    it('renders with label', () => {
        render(<DSSelect label="Country" options={sampleOptions} />);
        expect(screen.getByLabelText('Country')).toBeInTheDocument();
    });

    it('renders with placeholder', () => {
        render(<DSSelect placeholder="Select..." options={sampleOptions} />);
        expect(screen.getByText('Select...')).toBeInTheDocument();
    });

    it('shows error message', () => {
        render(<DSSelect error="Required" options={sampleOptions} />);
        expect(screen.getByRole('alert')).toHaveTextContent('Required');
    });

    it('shows helper text when no error', () => {
        render(<DSSelect helperText="Choose one" options={sampleOptions} />);
        expect(screen.getByText('Choose one')).toBeInTheDocument();
    });

    it('does not show helper text when error is present', () => {
        render(<DSSelect error="Error" helperText="Helper" options={sampleOptions} />);
        expect(screen.getByRole('alert')).toHaveTextContent('Error');
        expect(screen.queryByText('Helper')).not.toBeInTheDocument();
    });

    it('is disabled when disabled prop is true', () => {
        render(<DSSelect disabled options={sampleOptions} />);
        expect(screen.getByRole('combobox')).toBeDisabled();
    });

    it('calls onChange when selection changes', () => {
        const handleChange = vi.fn();
        render(<DSSelect onChange={handleChange} options={sampleOptions} />);
        fireEvent.change(screen.getByRole('combobox'), { target: { value: 'opt2' } });
        expect(handleChange).toHaveBeenCalledTimes(1);
    });

    it('applies error styling', () => {
        render(<DSSelect error="Error" options={sampleOptions} />);
        const select = screen.getByRole('combobox');
        expect(select.className).toContain('border-[hsl(var(--danger))]');
    });

    it('generates id from label', () => {
        render(<DSSelect label="Country" options={sampleOptions} />);
        const select = screen.getByRole('combobox');
        expect(select.id).toBe('country');
    });

    it('uses custom id when provided', () => {
        render(<DSSelect id="custom-id" options={sampleOptions} />);
        const select = screen.getByRole('combobox');
        expect(select.id).toBe('custom-id');
    });

    it('applies custom className', () => {
        render(<DSSelect className="custom-class" options={sampleOptions} />);
        const select = screen.getByRole('combobox');
        expect(select.className).toContain('custom-class');
    });

    it('renders disabled option', () => {
        render(
            <DSSelect 
                options={[
                    { value: 'opt1', label: 'Option 1' },
                    { value: 'opt2', label: 'Option 2', disabled: true },
                ]} 
            />
        );
        const options = screen.getAllByRole('option');
        expect(options[1]).toBeDisabled();
    });
});
