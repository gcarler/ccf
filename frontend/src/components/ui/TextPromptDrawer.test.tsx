import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { axe } from 'jest-axe';
import TextPromptDrawer from './TextPromptDrawer';

describe('TextPromptDrawer component', () => {
  it('does not render content when isOpen is false', () => {
    render(
      <TextPromptDrawer
        isOpen={false}
        title="Editar Titulo"
        label="Nuevo Nombre"
        value=""
        onChange={vi.fn()}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
      />
    );

    expect(screen.queryByText('Editar Titulo')).not.toBeInTheDocument();
  });

  it('renders title, label, value and triggers onChange and onSubmit', () => {
    const onChangeMock = vi.fn();
    const onSubmitMock = vi.fn();
    const onCloseMock = vi.fn();

    render(
      <TextPromptDrawer
        isOpen={true}
        title="Editar Titulo"
        subtitle="Subtitle text"
        label="Nuevo Nombre"
        value="Texto inicial"
        onChange={onChangeMock}
        onClose={onCloseMock}
        onSubmit={onSubmitMock}
        placeholder="Escribe aqui..."
      />
    );

    expect(screen.getByText('Editar Titulo')).toBeInTheDocument();
    expect(screen.getByText('Subtitle text')).toBeInTheDocument();
    expect(screen.getByText('Nuevo Nombre')).toBeInTheDocument();

    const input = screen.getByPlaceholderText('Escribe aqui...');
    expect(input).toHaveValue('Texto inicial');

    fireEvent.change(input, { target: { value: 'Texto cambiado' } });
    expect(onChangeMock).toHaveBeenCalledWith('Texto cambiado');

    fireEvent.click(screen.getByText('Guardar'));
    expect(onSubmitMock).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByText('Cancelar'));
    expect(onCloseMock).toHaveBeenCalledTimes(1);
  });

  it('has no accessibility violations when open', async () => {
    const { container } = render(
      <TextPromptDrawer
        isOpen
        title="Editar"
        label="Nombre"
        value="Texto"
        onChange={vi.fn()}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
      />
    );
    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });
});
