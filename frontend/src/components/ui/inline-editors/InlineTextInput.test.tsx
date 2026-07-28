import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { InlineTextInput } from './InlineTextInput';

describe('InlineTextInput component', () => {
  it('renders read-only button state initially', () => {
    render(
      <InlineTextInput
        value="Texto Original"
        onChange={vi.fn()}
        ariaLabel="Editar nombre"
      />
    );

    expect(screen.getByText('Texto Original')).toBeInTheDocument();
  });

  it('switches to input mode on click and saves on Enter', () => {
    const onChangeMock = vi.fn();

    render(
      <InlineTextInput
        value="Texto Original"
        onChange={onChangeMock}
        placeholder="Ingrese texto..."
      />
    );

    fireEvent.click(screen.getByText('Texto Original'));

    const input = screen.getByPlaceholderText('Ingrese texto...');
    expect(input).toHaveValue('Texto Original');

    fireEvent.change(input, { target: { value: 'Texto Actualizado' } });
    fireEvent.keyDown(input, { key: 'Enter' });

    expect(onChangeMock).toHaveBeenCalledWith('Texto Actualizado');
  });

  it('cancels edit on Escape key', () => {
    const onChangeMock = vi.fn();

    render(
      <InlineTextInput
        value="Texto Original"
        onChange={onChangeMock}
      />
    );

    fireEvent.click(screen.getByText('Texto Original'));

    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: 'Texto Cancelado' } });
    fireEvent.keyDown(input, { key: 'Escape' });

    expect(onChangeMock).not.toHaveBeenCalled();
    expect(screen.getByText('Texto Original')).toBeInTheDocument();
  });
});
