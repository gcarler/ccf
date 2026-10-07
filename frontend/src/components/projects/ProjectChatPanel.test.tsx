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
});
