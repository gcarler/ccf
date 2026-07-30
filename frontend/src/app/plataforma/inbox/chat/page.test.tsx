import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import ChatAdminPage from './page';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import type { ChatAdminMessageItem } from '@/types/directMessages';

vi.mock('@/context/AuthContext', () => ({ useAuth: vi.fn() }));
vi.mock('@/lib/http', () => ({ apiFetch: vi.fn() }));

const sentMessages: ChatAdminMessageItem[] = [
  {
    id: 'msg-1',
    conversation_id: 'conv-1',
    conversation_name: 'Abigail Monsalve',
    sender_id: 'me',
    sender_name: 'pastor.e2e',
    content: 'Nos vemos en el seguimiento.',
    created_at: '2026-07-16T08:58:00Z',
    is_read: true,
  },
  {
    id: 'msg-2',
    conversation_id: 'conv-2',
    conversation_name: 'Carlos Rueda',
    sender_id: 'me',
    sender_name: 'pastor.e2e',
    content: 'Te compartí el recurso.',
    created_at: '2026-07-16T07:20:00Z',
    is_read: true,
    attachment_url: '/file.pdf',
    attachment_type: 'pdf',
    attachment_name: 'liderazgo.pdf',
    attachment_size: 1024,
  },
];

const mentions: ChatAdminMessageItem[] = [
  {
    id: 'msg-3',
    conversation_id: 'conv-1',
    conversation_name: 'Abigail Monsalve',
    sender_id: 'u1',
    sender_name: 'Abigail Monsalve',
    content: '@pastor.e2e ¿ya quedó lista la reunión?',
    created_at: '2026-07-16T09:15:00Z',
    is_read: false,
    mentions: ['me'],
  },
];

function setupMocks() {
  vi.mocked(useAuth).mockReturnValue({ token: 'fake-token' } as unknown as ReturnType<typeof useAuth>);
}

describe('ChatAdminPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setupMocks();
  });

  it('renders sent messages by default', async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce(sentMessages);

    render(<ChatAdminPage />);

    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith('/chat/my-messages', expect.any(Object)));
    expect(screen.getByText('Centro de mensajes')).toBeInTheDocument();
    expect(screen.getByText('Nos vemos en el seguimiento.')).toBeInTheDocument();
    expect(screen.getByText('Carlos Rueda')).toBeInTheDocument();
    expect(screen.getByText('liderazgo.pdf')).toBeInTheDocument();
  });

  it('switches to the mentions tab and fetches mentions', async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce(sentMessages).mockResolvedValueOnce(mentions);

    render(<ChatAdminPage />);
    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith('/chat/my-messages', expect.any(Object)));

    fireEvent.click(screen.getByRole('button', { name: /Menciones/i }));

    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith('/chat/mentions', expect.any(Object)));
    expect(screen.getByText('@pastor.e2e ¿ya quedó lista la reunión?')).toBeInTheDocument();
    expect(screen.getByText('Nuevo')).toBeInTheDocument();
  });

  it('filters the list by search term', async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce(sentMessages);

    render(<ChatAdminPage />);
    await waitFor(() => expect(screen.getByText('Carlos Rueda')).toBeInTheDocument());

    fireEvent.change(screen.getByPlaceholderText(/Buscar/i), { target: { value: 'Carlos' } });

    expect(screen.getByText('Carlos Rueda')).toBeInTheDocument();
    expect(screen.queryByText('Abigail Monsalve')).not.toBeInTheDocument();
  });

  it('links each item to the chat conversation', async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce(sentMessages);

    render(<ChatAdminPage />);
    await waitFor(() => expect(screen.getByText('Nos vemos en el seguimiento.')).toBeInTheDocument());

    const link = screen.getByRole('link', { name: /Nos vemos en el seguimiento/i });
    expect(link).toHaveAttribute('href', '/plataforma/messages?conv=conv-1');
  });

  it('shows an error state when the request fails', async () => {
    vi.mocked(apiFetch).mockRejectedValueOnce(new Error('Network error'));

    render(<ChatAdminPage />);
    await waitFor(() => expect(screen.getByText('Network error')).toBeInTheDocument());
  });
});
