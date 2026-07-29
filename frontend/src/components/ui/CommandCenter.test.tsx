import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { axe } from 'jest-axe';
import { CommandCenter } from './CommandCenter';

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
}));

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({
    token: 'fake-token',
  }),
}));

vi.mock('@/context/CommandCenterContext', () => ({
  useCommandCenter: () => ({
    commands: [],
  }),
}));

vi.mock('@/context/CreationContext', () => ({
  useCreation: () => ({
    openModal: vi.fn(),
  }),
}));

vi.mock('@/lib/http', () => ({
  apiFetch: vi.fn().mockResolvedValue({ items: [] }),
}));

describe('CommandCenter component', () => {
  it('opens command menu on Cmd+K / Ctrl+K keyboard shortcut', () => {
    render(<CommandCenter />);

    // Initially not visible
    expect(screen.queryByPlaceholderText(/Buscar proyectos/i)).not.toBeInTheDocument();

    // Trigger Ctrl+K
    fireEvent.keyDown(document, { key: 'k', ctrlKey: true });

    // Should open
    expect(screen.getByPlaceholderText(/Buscar proyectos/i)).toBeInTheDocument();
  });

  it('renders default navigation commands when open', () => {
    render(<CommandCenter />);

    fireEvent.keyDown(document, { key: 'k', ctrlKey: true });

    expect(screen.getByText('CRM Pastoral')).toBeInTheDocument();
    expect(screen.getByText('Gestión de Proyectos')).toBeInTheDocument();
    expect(screen.getByText('Academia CCF')).toBeInTheDocument();
  });

  it('has no accessibility violations when open', async () => {
    const { container } = render(<CommandCenter />);
    fireEvent.keyDown(document, { key: 'k', ctrlKey: true });
    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });
});
