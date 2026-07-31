import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
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

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders sent messages by default', async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce(sentMessages);

    render(<ChatAdminPage />);

    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith(
        '/chat/my-messages',
        expect.objectContaining({ query: { limit: '50', offset: '0' } })
      )
    );
    expect(screen.getByText('Centro de mensajes')).toBeInTheDocument();
    expect(screen.getByText('Nos vemos en el seguimiento.')).toBeInTheDocument();
    expect(screen.getByText('Carlos Rueda')).toBeInTheDocument();
    expect(screen.getByText('liderazgo.pdf')).toBeInTheDocument();
  });

  it('switches to the mentions tab and fetches mentions', async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce(sentMessages).mockResolvedValueOnce(mentions);

    render(<ChatAdminPage />);
    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith(
        '/chat/my-messages',
        expect.objectContaining({ query: { limit: '50', offset: '0' } })
      )
    );

    fireEvent.click(screen.getByRole('button', { name: /Menciones/i }));

    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith(
        '/chat/mentions',
        expect.objectContaining({ query: { limit: '50', offset: '0' } })
      )
    );
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

  it('loads more items when the load more button is clicked', async () => {
    const firstPage = Array.from({ length: 50 }, (_, i) => ({
      ...sentMessages[0],
      id: `msg-${i}`,
      content: `Mensaje ${i}`,
    }));
    const secondPage = [
      {
        ...sentMessages[0],
        id: 'msg-51',
        content: 'Mensaje 51',
      },
    ];

    vi.mocked(apiFetch)
      .mockResolvedValueOnce(firstPage)
      .mockResolvedValueOnce(secondPage);

    render(<ChatAdminPage />);
    await waitFor(() => expect(screen.getByText('Mensaje 0')).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: /Cargar más/i }));

    await waitFor(() =>
      expect(apiFetch).toHaveBeenLastCalledWith(
        '/chat/my-messages',
        expect.objectContaining({ query: { limit: '50', offset: '50' } })
      )
    );
    expect(screen.getByText('Mensaje 51')).toBeInTheDocument();
  });

  it('renders attachment icons for different types', async () => {
    const withAttachments: ChatAdminMessageItem[] = [
      {
        ...sentMessages[0],
        id: 'msg-img',
        attachment_url: '/img.png',
        attachment_type: 'image',
        attachment_name: 'foto.png',
      },
      {
        ...sentMessages[0],
        id: 'msg-vid',
        attachment_url: '/vid.mp4',
        attachment_type: 'video',
        attachment_name: 'video.mp4',
      },
      {
        ...sentMessages[0],
        id: 'msg-aud',
        attachment_url: '/aud.mp3',
        attachment_type: 'audio',
        attachment_name: 'audio.mp3',
      },
    ];
    vi.mocked(apiFetch).mockResolvedValueOnce(withAttachments);

    render(<ChatAdminPage />);
    await waitFor(() => expect(screen.getByText('foto.png')).toBeInTheDocument());
    expect(screen.getByText('video.mp4')).toBeInTheDocument();
    expect(screen.getByText('audio.mp3')).toBeInTheDocument();
  });

  it('shows the mentions empty state when no mentions exist', async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce(sentMessages).mockResolvedValueOnce([]);

    render(<ChatAdminPage />);
    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith(
        '/chat/my-messages',
        expect.objectContaining({ query: { limit: '50', offset: '0' } })
      )
    );

    fireEvent.click(screen.getByRole('button', { name: /Menciones/i }));

    await waitFor(() =>
      expect(screen.getByText('Aún no te han mencionado')).toBeInTheDocument()
    );
    expect(
      screen.getByText('Cuando alguien te mencione con @, verás el mensaje aquí.')
    ).toBeInTheDocument();
  });

  it('formats recent messages as "Ahora"', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const now = new Date('2026-07-16T08:58:30Z').getTime();
    vi.setSystemTime(new Date(now));
    vi.mocked(apiFetch).mockResolvedValueOnce([
      { ...sentMessages[0], created_at: new Date(now - 5000).toISOString() },
    ]);

    render(<ChatAdminPage />);
    await waitFor(() => expect(screen.getByText('Ahora')).toBeInTheDocument());
  });

  it('formats messages from minutes ago', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const now = new Date('2026-07-16T09:28:00Z').getTime();
    vi.setSystemTime(new Date(now));
    vi.mocked(apiFetch).mockResolvedValueOnce([
      { ...sentMessages[0], created_at: new Date(now - 30 * 60000).toISOString() },
    ]);

    render(<ChatAdminPage />);
    await waitFor(() => expect(screen.getByText('Hace 30 min')).toBeInTheDocument());
  });

  it('formats messages from hours ago', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const now = new Date('2026-07-16T14:00:00Z').getTime();
    vi.setSystemTime(new Date(now));
    vi.mocked(apiFetch).mockResolvedValueOnce([
      { ...sentMessages[0], created_at: new Date(now - 5 * 3600000).toISOString() },
    ]);

    render(<ChatAdminPage />);
    await waitFor(() => expect(screen.getByText('Hace 5 h')).toBeInTheDocument());
  });

  it('formats messages from yesterday', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const now = new Date('2026-07-17T15:00:00Z').getTime();
    vi.setSystemTime(new Date(now));
    vi.mocked(apiFetch).mockResolvedValueOnce([
      { ...sentMessages[0], created_at: new Date(now - 30 * 3600000).toISOString() },
    ]);

    render(<ChatAdminPage />);
    await waitFor(() => expect(screen.getByText('Ayer')).toBeInTheDocument());
  });

  it('formats invalid dates as "Sin fecha"', async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce([
      { ...sentMessages[0], id: 'msg-invalid', created_at: 'not-a-date' },
    ]);

    render(<ChatAdminPage />);
    await waitFor(() => expect(screen.getByText('Sin fecha')).toBeInTheDocument());
  });

  it('does not fetch when there is no token', async () => {
    vi.mocked(useAuth).mockReturnValue({ token: null } as unknown as ReturnType<typeof useAuth>);

    render(<ChatAdminPage />);
    await waitFor(() => expect(screen.getByText('Centro de mensajes')).toBeInTheDocument());
    expect(apiFetch).not.toHaveBeenCalled();
  });

  it('renders mention count on messages with mentions', async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce(sentMessages).mockResolvedValueOnce(mentions);

    render(<ChatAdminPage />);
    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith(
        '/chat/my-messages',
        expect.objectContaining({ query: { limit: '50', offset: '0' } })
      )
    );

    fireEvent.click(screen.getByRole('button', { name: /Menciones/i }));

    await waitFor(() => expect(screen.getByText('1 mención')).toBeInTheDocument());
  });

  it('renders plural mention count', async () => {
    const multiMentions: ChatAdminMessageItem[] = [
      {
        ...mentions[0],
        id: 'msg-multi',
        mentions: ['me', 'other'],
      },
    ];
    vi.mocked(apiFetch).mockResolvedValueOnce(sentMessages).mockResolvedValueOnce(multiMentions);

    render(<ChatAdminPage />);
    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith(
        '/chat/my-messages',
        expect.objectContaining({ query: { limit: '50', offset: '0' } })
      )
    );

    fireEvent.click(screen.getByRole('button', { name: /Menciones/i }));

    await waitFor(() => expect(screen.getByText('2 menciones')).toBeInTheDocument());
  });

  it('shows generic attachment label when name is missing', async () => {
    const msgNoName: ChatAdminMessageItem[] = [
      {
        ...sentMessages[0],
        id: 'msg-noname',
        attachment_url: '/file.pdf',
        attachment_type: 'pdf',
      },
    ];
    vi.mocked(apiFetch).mockResolvedValueOnce(msgNoName);

    render(<ChatAdminPage />);
    await waitFor(() => expect(screen.getByText('Adjunto')).toBeInTheDocument());
  });

  it('shows fallback error message for non-Error rejections', async () => {
    vi.mocked(apiFetch).mockRejectedValueOnce('string error');

    render(<ChatAdminPage />);
    await waitFor(() =>
      expect(screen.getByText('Error al cargar mensajes')).toBeInTheDocument()
    );
  });

  it('refetches on refresh button click', async () => {
    vi.mocked(apiFetch).mockResolvedValue(sentMessages);

    render(<ChatAdminPage />);
    await waitFor(() => expect(screen.getByText(/Nos vemos/)).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: /Actualizar/i }));

    await waitFor(() => expect(apiFetch).toHaveBeenCalledTimes(2));
    expect(apiFetch).toHaveBeenLastCalledWith(
      '/chat/my-messages',
      expect.objectContaining({ query: { limit: '50', offset: '0' } })
    );
  });

  it('recovers from error via retry button', async () => {
    vi.mocked(apiFetch)
      .mockRejectedValueOnce(new Error('Network error'))
      .mockResolvedValueOnce(sentMessages);

    render(<ChatAdminPage />);
    await waitFor(() => expect(screen.getByText('Network error')).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: /Reintentar/i }));

    await waitFor(() => expect(screen.getByText(/Nos vemos/)).toBeInTheDocument());
    expect(screen.queryByText('Network error')).not.toBeInTheDocument();
  });
});
