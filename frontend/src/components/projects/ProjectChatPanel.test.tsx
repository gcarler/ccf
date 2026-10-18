import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { axe } from 'jest-axe';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const mocks = vi.hoisted(() => ({ apiFetch: vi.fn(), toastError: vi.fn() }));
const messages = [
  {
    id: 'message-1',
    sender_id: 'user-1',
    sender_name: 'Ada',
    content: 'Actualización del proyecto',
    created_at: '2026-10-01T10:00:00Z',
    is_read: false,
  },
];
const pmiMessages = [
  { ...messages[0], id: 'decision-1', content: '[DECISIÓN PMI] Se aprueba el alcance de fase.' },
  { ...messages[0], id: 'issue-1', content: '[INCIDENTE / BLOQUEO] bloqueo: falta el acceso de pruebas.' },
  { ...messages[0], id: 'action-1', content: '[ACCIÓN / COMPROMISO] preparar cronograma revisado.' },
  { ...messages[0], id: 'milestone-1', content: '[AVANCE / HITO] Entregable validado.' },
  { ...messages[0], id: 'unclassified-1', content: 'Actualización sin etiqueta PMI.' },
];

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({ token: 'token', user: { id: 'user-1' }, loading: false }),
}));
vi.mock('@/lib/http', () => ({
  apiFetch: mocks.apiFetch,
}));
vi.mock('@/hooks/useWorkspaceSocket', () => ({ useWorkspaceSocket: () => ({ status: 'idle' }) }));
vi.mock('sonner', () => ({ toast: { error: mocks.toastError } }));

import ProjectChatPanel from './ProjectChatPanel';

describe('ProjectChatPanel action access', () => {
  beforeEach(() => {
    mocks.apiFetch.mockReset().mockImplementation((path: string, options?: { method?: string }) => {
      if (options?.method === 'DELETE') return Promise.resolve({ ok: true });
      if (path.endsWith('/messages')) return Promise.resolve(messages);
      return Promise.resolve([]);
    });
    mocks.toastError.mockClear();
  });

  it('labels the delete action and keeps it available on touch and keyboard focus', async () => {
    Object.defineProperty(HTMLElement.prototype, 'scrollTo', {
      configurable: true,
      value: vi.fn(),
    });
    const { container } = render(<ProjectChatPanel projectId="project-1" />);

    const deleteButton = await screen.findByRole('button', { name: 'Eliminar mi mensaje: Actualización del proyecto' });
    expect(deleteButton).toHaveClass('opacity-100', 'md:group-focus-within:opacity-100');
    expect(screen.getByRole('textbox', { name: 'Escribir mensaje en el chat del proyecto' })).toBeInTheDocument();
    expect((await axe(container)).violations).toEqual([]);
  });

  it('cancels message deletion without sending DELETE and confirms it explicitly', async () => {
    render(<ProjectChatPanel projectId="project-1" />);
    fireEvent.click(await screen.findByRole('button', { name: 'Eliminar mi mensaje: Actualización del proyecto' }));
    expect(await screen.findByRole('complementary', { name: 'Eliminar mensaje' })).toHaveTextContent('Actualización del proyecto');
    expect(mocks.apiFetch.mock.calls.some(([, options]) => options?.method === 'DELETE')).toBe(false);

    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }));
    await waitFor(() => expect(screen.queryByRole('complementary', { name: 'Eliminar mensaje' })).not.toBeInTheDocument());
    expect(mocks.apiFetch.mock.calls.some(([, options]) => options?.method === 'DELETE')).toBe(false);

    fireEvent.click(screen.getByRole('button', { name: 'Eliminar mi mensaje: Actualización del proyecto' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Eliminar mensaje' }));
    await waitFor(() => expect(mocks.apiFetch).toHaveBeenCalledWith(
      '/projects/project-1/messages/message-1',
      expect.objectContaining({ method: 'DELETE', token: 'token' }),
    ));
    await waitFor(() => expect(screen.getByText('No hay mensajes aún')).toBeInTheDocument());
  });

  it('keeps the message visible and confirmation open after a failed delete', async () => {
    mocks.apiFetch.mockImplementation((path: string, options?: { method?: string }) => {
      if (options?.method === 'DELETE') return Promise.reject(new Error('offline'));
      if (path.endsWith('/messages')) return Promise.resolve(messages);
      return Promise.resolve([]);
    });
    render(<ProjectChatPanel projectId="project-1" />);
    fireEvent.click(await screen.findByRole('button', { name: 'Eliminar mi mensaje: Actualización del proyecto' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Eliminar mensaje' }));

    await waitFor(() => expect(mocks.toastError).toHaveBeenCalledWith('Failed to delete message'));
    expect(screen.getByText('Actualización del proyecto')).toBeInTheDocument();
    expect(screen.getByRole('complementary', { name: 'Eliminar mensaje' })).toBeInTheDocument();
  });

  it('shows mention suggestions when typing @ and inserts mention on selection', async () => {
    const mockCandidates = [
      { id: 'user-2', nombre_completo: 'Carlos Gomez' },
      { id: 'user-3', nombre_completo: 'Ana Maria' },
    ];
    mocks.apiFetch.mockImplementation((path: string, options?: { method?: string; body?: string }) => {
      if (options?.method === 'POST') {
        const body = JSON.parse(options.body || '{}');
        return Promise.resolve({
          id: 'new-msg',
          sender_id: 'user-1',
          sender_name: 'Ada',
          content: body.content,
          mentions: body.mentions,
          created_at: '2026-10-01T10:05:00Z',
        });
      }
      if (path.includes('/projects/assignee-candidates')) return Promise.resolve(mockCandidates);
      if (path.endsWith('/messages')) return Promise.resolve(messages);
      return Promise.resolve([]);
    });

    render(<ProjectChatPanel projectId="project-1" />);
    const textarea = await screen.findByRole('textbox', { name: 'Escribir mensaje en el chat del proyecto' });

    // Focus and click @ button
    const atButton = screen.getByRole('button', { name: 'Mencionar usuario con @' });
    expect(atButton).toBeInTheDocument();
    fireEvent.click(atButton);

    // Should insert @ and show candidate suggestions
    await waitFor(() => {
      expect(screen.getByRole('listbox', { name: 'Sugerencias de mención' })).toBeInTheDocument();
    });
    expect(screen.getByText('Carlos Gomez')).toBeInTheDocument();
    expect(screen.getByText('Ana Maria')).toBeInTheDocument();

    // Select Carlos Gomez
    fireEvent.click(screen.getByRole('option', { name: /Carlos Gomez/ }));

    // Textarea should now have @Carlos Gomez and suggestion list is closed
    expect(textarea).toHaveValue('@Carlos Gomez ');
    await waitFor(() => {
      expect(screen.queryByRole('listbox', { name: 'Sugerencias de mención' })).not.toBeInTheDocument();
    });

    // Send the message
    const sendButton = screen.getByRole('button', { name: 'Enviar mensaje' });
    fireEvent.click(sendButton);

    await waitFor(() => {
      expect(mocks.apiFetch).toHaveBeenCalledWith(
        '/projects/project-1/messages',
        expect.objectContaining({
          method: 'POST',
          body: {
            content: '@Carlos Gomez',
            mentions: ['user-2'],
          },
        }),
      );
    });
  });

  it('supports keyboard navigation (ArrowDown, Enter) to select mention', async () => {
    const mockCandidates = [
      { id: 'user-2', nombre_completo: 'Carlos Gomez' },
      { id: 'user-3', nombre_completo: 'Camila Perez' },
    ];
    mocks.apiFetch.mockImplementation((path: string) => {
      if (path.includes('/projects/assignee-candidates')) return Promise.resolve(mockCandidates);
      if (path.endsWith('/messages')) return Promise.resolve(messages);
      return Promise.resolve([]);
    });

    render(<ProjectChatPanel projectId="project-1" />);
    const textarea = await screen.findByRole('textbox', { name: 'Escribir mensaje en el chat del proyecto' });

    // Type @Ca
    fireEvent.change(textarea, { target: { value: 'Hola @Ca' } });

    await waitFor(() => {
      expect(screen.getByRole('listbox', { name: 'Sugerencias de mención' })).toBeInTheDocument();
    });

    // Initial item is Camila Perez (alphabetical first). ArrowDown moves to Carlos Gomez.
    fireEvent.keyDown(textarea, { key: 'ArrowDown' });
    // Press Enter to select Carlos Gomez
    fireEvent.keyDown(textarea, { key: 'Enter' });

    expect(textarea).toHaveValue('Hola @Carlos Gomez ');
    await waitFor(() => {
      expect(screen.queryByRole('listbox', { name: 'Sugerencias de mención' })).not.toBeInTheDocument();
    });
  });

  it('counts PMI communication categories, displays semantic badges, and filters visible messages', async () => {
    mocks.apiFetch.mockImplementation((path: string) => {
      if (path.endsWith('/messages')) return Promise.resolve(pmiMessages);
      return Promise.resolve([]);
    });

    render(<ProjectChatPanel projectId="project-1" />);

    expect(await screen.findByTestId('chat-pmi-comms-summary')).toHaveTextContent('5 mensajes');
    expect(screen.getByTestId('chat-pmi-count-decision')).toHaveTextContent('1');
    expect(screen.getByTestId('chat-pmi-count-issue')).toHaveTextContent('1');
    expect(screen.getByTestId('chat-pmi-count-action')).toHaveTextContent('1');
    expect(screen.getByTestId('chat-pmi-count-milestone')).toHaveTextContent('1');
    expect(screen.getByTestId('chat-pmi-message-badge-decision-1')).toHaveTextContent('Decisión PMI');
    expect(screen.getByTestId('chat-pmi-message-badge-issue-1')).toHaveTextContent('Incidente / Bloqueo');
    expect(screen.getByTestId('chat-pmi-message-badge-action-1')).toHaveTextContent('Acción / Compromiso');
    expect(screen.getByTestId('chat-pmi-message-badge-milestone-1')).toHaveTextContent('Avance / Hito');

    fireEvent.click(screen.getByTestId('chat-pmi-filter-issue'));
    expect(screen.getByText('[INCIDENTE / BLOQUEO] bloqueo: falta el acceso de pruebas.')).toBeInTheDocument();
    expect(screen.queryByText('[DECISIÓN PMI] Se aprueba el alcance de fase.')).not.toBeInTheDocument();
    expect(screen.queryByText('Actualización sin etiqueta PMI.')).not.toBeInTheDocument();

    fireEvent.click(screen.getByTestId('chat-pmi-filter-all'));
    expect(screen.getByText('[DECISIÓN PMI] Se aprueba el alcance de fase.')).toBeInTheDocument();
    expect(screen.getByText('Actualización sin etiqueta PMI.')).toBeInTheDocument();
  });

  it('inserts, replaces, and toggles PMI prefixes without losing the message draft', async () => {
    render(<ProjectChatPanel projectId="project-1" />);
    const input = await screen.findByRole('textbox', { name: 'Escribir mensaje en el chat del proyecto' });
    fireEvent.change(input, { target: { value: 'Revisar el entregable' } });

    fireEvent.click(screen.getByTestId('chat-pmi-tag-decision'));
    expect(input).toHaveValue('[DECISIÓN PMI] Revisar el entregable');
    fireEvent.click(screen.getByTestId('chat-pmi-tag-issue'));
    expect(input).toHaveValue('[INCIDENTE / BLOQUEO] Revisar el entregable');
    fireEvent.click(screen.getByTestId('chat-pmi-tag-action'));
    expect(input).toHaveValue('[ACCIÓN / COMPROMISO] Revisar el entregable');
    fireEvent.click(screen.getByTestId('chat-pmi-tag-milestone'));
    expect(input).toHaveValue('[AVANCE / HITO] Revisar el entregable');
    fireEvent.click(screen.getByTestId('chat-pmi-tag-milestone'));
    expect(input).toHaveValue('Revisar el entregable');
  });
});

