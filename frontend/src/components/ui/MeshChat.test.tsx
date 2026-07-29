import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { axe } from 'jest-axe';
import MeshChat from './MeshChat';
import { apiFetch } from '@/lib/http';

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({
    token: 'test-token',
    user: { username: 'Pastor Juan' },
  }),
}));

vi.mock('@/lib/http', () => ({
  apiFetch: vi.fn(),
}));

describe('MeshChat component', () => {
  it('does not render content when isOpen is false', () => {
    const { container } = render(<MeshChat isOpen={false} onClose={vi.fn()} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders bot welcome message when open', () => {
    render(<MeshChat isOpen={true} onClose={vi.fn()} />);

    expect(screen.getByText('Optimus Brain')).toBeInTheDocument();
    expect(screen.getByText(/Hola Pastor Juan/i)).toBeInTheDocument();
  });

  it('sends user message and displays bot answer', async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce({
      answer: 'Respuesta de la inteligencia MESH',
      sources: ['doc-1'],
    });

    render(<MeshChat isOpen={true} onClose={vi.fn()} />);

    const input = screen.getByPlaceholderText('Preguntar a Optimus...');
    fireEvent.change(input, { target: { value: '¿Cómo va la asistencia?' } });

    const form = input.closest('form')!;
    fireEvent.submit(form);

    expect(screen.getByText('¿Cómo va la asistencia?')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('Respuesta de la inteligencia MESH')).toBeInTheDocument();
      expect(screen.getByText('Source: doc-1')).toBeInTheDocument();
    });
  });

  it('has no accessibility violations when open', async () => {
    const { container } = render(<MeshChat isOpen onClose={vi.fn()} />);
    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });
});
