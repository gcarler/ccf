import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ConfirmActionDrawer from './ConfirmActionDrawer';

describe('ConfirmActionDrawer component', () => {
  it('does not render when action is null', () => {
    const { container } = render(
      <ConfirmActionDrawer action={null} onClose={vi.fn()} />
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders title, description and confirm button when action is provided', () => {
    const onConfirmMock = vi.fn();
    const onCloseMock = vi.fn();

    render(
      <ConfirmActionDrawer
        action={{
          title: 'Eliminar Elemento',
          description: '¿Estás seguro de eliminar este elemento?',
          confirmLabel: 'Sí, Eliminar',
          destructive: true,
          onConfirm: onConfirmMock,
        }}
        onClose={onCloseMock}
      />
    );

    expect(screen.getByText('Eliminar Elemento')).toBeInTheDocument();
    expect(screen.getByText('¿Estás seguro de eliminar este elemento?')).toBeInTheDocument();
    expect(screen.getByText('Sí, Eliminar')).toBeInTheDocument();
  });

  it('calls onClose when cancel button is clicked', () => {
    const onCloseMock = vi.fn();

    render(
      <ConfirmActionDrawer
        action={{
          title: 'Accion',
          description: 'Descripcion',
          onConfirm: vi.fn(),
        }}
        onClose={onCloseMock}
      />
    );

    fireEvent.click(screen.getByText('Cancelar'));
    expect(onCloseMock).toHaveBeenCalledTimes(1);
  });
});
