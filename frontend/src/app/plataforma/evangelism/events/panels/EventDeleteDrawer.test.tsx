import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import EventDeleteDrawer from './EventDeleteDrawer';

interface MockDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  subtitle?: string;
  actions?: React.ReactNode;
  children?: React.ReactNode;
}

// Mock WorkspaceDrawer para renderizar su contenido sin framer-motion/AnimatePresence
vi.mock('@/components/WorkspaceDrawer', () => ({
  default: ({ isOpen, onClose, title, subtitle, actions, children }: MockDrawerProps) =>
    isOpen ? (
      <div data-testid="workspace-drawer">
        <header>
          <h2>{title}</h2>
          <p>{subtitle}</p>
          <button onClick={onClose}>cerrar-icon</button>
        </header>
        <div data-testid="actions">{actions}</div>
        <div data-testid="content">{children}</div>
      </div>
    ) : null,
}));

vi.mock('@/components/ErrorBoundary', () => ({
  default: ({ children }: { children?: React.ReactNode }) => <>{children}</>,
}));

beforeEach(() => {
  vi.clearAllMocks();
});

type DeleteProps = React.ComponentProps<typeof EventDeleteDrawer>;
function makeProps(over: Partial<DeleteProps> = {}): DeleteProps {
  return {
    deletingId: 'ev-1',
    deletingLoadingId: null,
    onDelete: vi.fn(),
    onClose: vi.fn(),
    ...over,
  };
}

describe('EventDeleteDrawer', () => {
  it('no renderiza cuando deletingId es null', () => {
    render(<EventDeleteDrawer {...makeProps({ deletingId: null })} />);
    expect(screen.queryByTestId('workspace-drawer')).toBeNull();
  });

  it('renderiza el drawer cuando hay deletingId', () => {
    render(<EventDeleteDrawer {...makeProps()} />);
    expect(screen.getByText('¿Eliminar evento?')).toBeInTheDocument();
    expect(screen.getByText(/acción destructiva/i)).toBeInTheDocument();
    expect(screen.getByText(/historial del evento/i)).toBeInTheDocument();
  });

  it('el botón Cancelar dispara onClose', () => {
    const props = makeProps();
    render(<EventDeleteDrawer {...props} />);
    fireEvent.click(screen.getByText('Cancelar'));
    expect(props.onClose).toHaveBeenCalledTimes(1);
  });

  it('el botón Eliminar dispara onDelete con el deletingId', () => {
    const props = makeProps();
    render(<EventDeleteDrawer {...props} />);
    // Botón Eliminar: contiene texto " Eliminar" + icono Trash2
    const delBtn = screen.getByRole('button', { name: /eliminar/i });
    fireEvent.click(delBtn);
    expect(props.onDelete).toHaveBeenCalledWith('ev-1');
    expect(props.onDelete).toHaveBeenCalledTimes(1);
  });

  it('onDelete es no-op cuando deletingId es null (guarda de seguridad)', () => {
    const props = makeProps({ deletingId: null });
    // No renderiza el drawer → no hay botón; nada que cliquear
    render(<EventDeleteDrawer {...props} />);
    expect(screen.queryByRole('button', { name: /eliminar/i })).toBeNull();
    expect(props.onDelete).not.toHaveBeenCalled();
  });

  it('deshabilita botones mientras deletingLoadingId coincide', () => {
    render(<EventDeleteDrawer {...makeProps({ deletingLoadingId: 'ev-1' })} />);
    expect(screen.getByText('Cancelar')).toBeDisabled();
    expect(screen.getByRole('button', { name: /eliminar/i })).toBeDisabled();
  });

  it('el botón cerrar (X) del drawer invoca onClose', () => {
    const props = makeProps();
    render(<EventDeleteDrawer {...props} />);
    fireEvent.click(screen.getByText('cerrar-icon'));
    expect(props.onClose).toHaveBeenCalled();
  });
});
