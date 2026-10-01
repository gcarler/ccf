import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import RoomConflictAlert, { RoomConflictInfo } from './RoomConflictAlert';

describe('RoomConflictAlert component', () => {
  it('does not render when conflict is null', () => {
    const { container } = render(<RoomConflictAlert conflict={null} />);
    expect(container.firstChild).toBeNull();
  });

  it('does not render when conflict.conflict is false', () => {
    const conflict: RoomConflictInfo = {
      conflict: false,
    };
    const { container } = render(<RoomConflictAlert conflict={conflict} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders conflict alert with default message when message is missing', () => {
    const conflict: RoomConflictInfo = {
      conflict: true,
    };
    render(<RoomConflictAlert conflict={conflict} />);
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('Conflicto de reserva física')).toBeInTheDocument();
    expect(screen.getByText('Ocupado')).toBeInTheDocument();
    expect(
      screen.getByText('El salón o espacio seleccionado ya se encuentra reservado en el horario propuesto.')
    ).toBeInTheDocument();
  });

  it('renders conflict details including title and message', () => {
    const conflict: RoomConflictInfo = {
      conflict: true,
      conflict_event_id: '123e4567-e89b-12d3-a456-426614174000',
      conflict_event_title: 'Servicio Dominical',
      conflict_start: '2026-10-04T10:00:00Z',
      conflict_end: '2026-10-04T12:00:00Z',
      message: 'Conflicto de reserva: el espacio ya está reservado por el evento Servicio Dominical',
    };

    render(<RoomConflictAlert conflict={conflict} />);

    expect(screen.getByText(conflict.message!)).toBeInTheDocument();
    expect(screen.getByText('Servicio Dominical')).toBeInTheDocument();
    expect(screen.getByText(/Evento en conflicto:/)).toBeInTheDocument();
  });

  it('calls onSelectAlternative when the action button is clicked', () => {
    const onSelectMock = vi.fn();
    const conflict: RoomConflictInfo = {
      conflict: true,
      conflict_event_title: 'Ensayo de Alabanza',
    };

    render(
      <RoomConflictAlert
        conflict={conflict}
        onSelectAlternative={onSelectMock}
      />
    );

    const btn = screen.getByText('Cambiar espacio o fecha');
    fireEvent.click(btn);
    expect(onSelectMock).toHaveBeenCalledTimes(1);
  });

  it('calls onDismiss when Entendido button is clicked', () => {
    const onDismissMock = vi.fn();
    const conflict: RoomConflictInfo = {
      conflict: true,
      conflict_event_title: 'Reunión de Jóvenes',
    };

    render(
      <RoomConflictAlert
        conflict={conflict}
        onDismiss={onDismissMock}
      />
    );

    const btn = screen.getByText('Entendido');
    fireEvent.click(btn);
    expect(onDismissMock).toHaveBeenCalledTimes(1);
  });

  it('calls onDismiss when close icon button is clicked', () => {
    const onDismissMock = vi.fn();
    const conflict: RoomConflictInfo = {
      conflict: true,
    };

    render(
      <RoomConflictAlert
        conflict={conflict}
        onDismiss={onDismissMock}
      />
    );

    const closeBtn = screen.getByLabelText('Cerrar alerta de conflicto');
    fireEvent.click(closeBtn);
    expect(onDismissMock).toHaveBeenCalledTimes(1);
  });
});
