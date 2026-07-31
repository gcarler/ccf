/* eslint-disable @typescript-eslint/no-explicit-any */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, act, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import MessagesPage from './page';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { useConversations } from './_hooks/useConversations';
import { useChatThread } from './_hooks/useChatThread';
import { useUserSearch } from './_hooks/useUserSearch';
import { apiFetch } from '@/lib/http';
import type { ConversationRead, DirectMessageItem } from '@/types/directMessages';

vi.mock('@/components/WorkspaceLayout', () => ({
    default: ({ children, customSidebar }: { children: React.ReactNode; customSidebar: React.ReactNode }) => (
        <div data-testid="workspace-layout">
            {customSidebar}
            {children}
        </div>
    ),
}));

vi.mock('@/context/AuthContext', () => ({ useAuth: vi.fn() }));
vi.mock('@/context/ToastContext', () => ({ useToast: vi.fn() }));
vi.mock('./_hooks/useConversations', () => ({ useConversations: vi.fn() }));
vi.mock('./_hooks/useChatThread', () => ({ useChatThread: vi.fn() }));
vi.mock('./_hooks/useUserSearch', () => ({ useUserSearch: vi.fn() }));
vi.mock('@/lib/http', () => ({ apiFetch: vi.fn() }));

interface SidebarProps {
    onNewConv: () => void;
    onSelectConv: (conv: ConversationRead) => void;
    filter: string;
    onFilterChange: (value: string) => void;
}

vi.mock('./_components/ConversationSidebar', () => ({
    ConversationSidebar: ({ onNewConv, onSelectConv, filter, onFilterChange }: SidebarProps) => (
        <div data-testid="conversation-sidebar">
            <button data-testid="sidebar-new-conv" onClick={onNewConv}>Nueva conversación</button>
            <button
                data-testid="sidebar-select-conv"
                onClick={() =>
                    onSelectConv({
                        id: 'conv-1',
                        participants: [
                            { persona_id: 'u1', username: 'ana', last_read_at: null },
                            { persona_id: 'me', username: 'yo', last_read_at: null },
                        ],
                        last_message_content: 'Hola',
                        last_message_at: '2026-07-30T10:00:00Z',
                        last_sender_id: 'u1',
                        unread_count: 0,
                        created_at: '2026-07-30T10:00:00Z',
                    })
                }
            >
                Seleccionar
            </button>
            <input
                data-testid="sidebar-filter-input"
                value={filter}
                onChange={(e) => onFilterChange(e.target.value)}
            />
        </div>
    ),
}));

interface InputProps {
    onSend: (content: string, opts: { mentions: string[] }) => Promise<{ error: 'upload' | 'send' | null }>;
}

vi.mock('./_components/MessageInput', () => ({
    MessageInput: ({ onSend }: InputProps) => (
        <button data-testid="message-input" onClick={() => onSend('Hola', { mentions: [] })}>
            Enviar mensaje
        </button>
    ),
}));

vi.mock('./_components/MessageList', () => ({
    MessageList: () => <div data-testid="message-list" />,
}));

interface DrawerProps {
    isOpen: boolean;
    onCreate: (participantId: string) => void;
}

vi.mock('./_components/NewConversationDrawer', () => ({
    NewConversationDrawer: ({ isOpen, onCreate }: DrawerProps) =>
        isOpen ? (
            <div data-testid="new-conv-drawer">
                <button data-testid="drawer-create" onClick={() => onCreate('user-99')}>
                    Crear conversación
                </button>
            </div>
        ) : null,
}));

const mockAddToast = vi.fn();
const mockRemoveToast = vi.fn();
const mockAddConversation = vi.fn();
const mockSetFilter = vi.fn();
const mockUpdateConversationFromMessage = vi.fn();
const mockResetSearch = vi.fn();
const mockSetQuery = vi.fn();
const mockSetError = vi.fn();
const mockSendMessage = vi.fn();

const sampleConversation: ConversationRead = {
    id: 'conv-1',
    participants: [
        { persona_id: 'u1', username: 'ana', last_read_at: null },
        { persona_id: 'me', username: 'yo', last_read_at: null },
    ],
    last_message_content: 'Hola',
    last_message_at: '2026-07-30T10:00:00Z',
    last_sender_id: 'u1',
    unread_count: 0,
    created_at: '2026-07-30T10:00:00Z',
};


const sampleMessage: DirectMessageItem = {
    id: 'm1',
    sender_id: 'u1',
    sender_name: 'Ana',
    content: 'Hola',
    created_at: '2026-07-30T10:00:00Z',
    is_read: false,
};

function renderPage() {
    return render(<MessagesPage />);
}

const defaultChatThreadReturn = {
    messages: [] as DirectMessageItem[],
    loading: false,
    sending: false,
    replyTo: null,
    setReplyTo: vi.fn(),
    loadOlderMessages: vi.fn(),
    sendMessage: mockSendMessage,
    wsStatus: 'open' as const,
    hasMoreOlder: false,
};

const defaultUserSearchReturn = {
    query: '',
    setQuery: mockSetQuery,
    results: [] as { id: string; username: string; email: string; avatar_url: string | null }[],
    loading: false,
    error: null as string | null,
    setError: mockSetError,
    reset: mockResetSearch,
};

function setupDefaultMocks() {
    vi.mocked(useAuth).mockReturnValue({ token: 'fake-token', user: { id: 'me' } } as any);
    vi.mocked(useToast).mockReturnValue({ addToast: mockAddToast, removeToast: mockRemoveToast } as any);

    vi.mocked(useConversations).mockReturnValue({
        conversations: [sampleConversation],
        filteredConversations: [sampleConversation],
        loading: false,
        filter: '',
        setFilter: mockSetFilter,
        addConversation: mockAddConversation,
        updateConversationFromMessage: mockUpdateConversationFromMessage,
        getOtherParticipant: vi.fn().mockReturnValue({ username: 'ana' }),
        totalUnread: 0,
    } as any);

    vi.mocked(useUserSearch).mockReturnValue(defaultUserSearchReturn as any);
    vi.mocked(useChatThread).mockReturnValue(defaultChatThreadReturn as any);
}

describe('MessagesPage', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        setupDefaultMocks();
    });

    it('renders the empty state when no conversation is selected', () => {
        vi.mocked(useConversations).mockReturnValue({
            conversations: [],
            filteredConversations: [],
            loading: false,
            filter: '',
            setFilter: mockSetFilter,
            addConversation: mockAddConversation,
            updateConversationFromMessage: mockUpdateConversationFromMessage,
            getOtherParticipant: vi.fn().mockReturnValue({ username: 'ana' }),
            totalUnread: 0,
        } as any);

        renderPage();

        expect(screen.getByText('Selecciona una conversación')).toBeInTheDocument();
        expect(screen.getByLabelText('Crear nueva conversación')).toBeInTheDocument();
    });

    it('opens the new conversation drawer from the empty state', async () => {
        vi.mocked(useConversations).mockReturnValue({
            conversations: [],
            filteredConversations: [],
            loading: false,
            filter: '',
            setFilter: mockSetFilter,
            addConversation: mockAddConversation,
            updateConversationFromMessage: mockUpdateConversationFromMessage,
            getOtherParticipant: vi.fn().mockReturnValue({ username: 'ana' }),
            totalUnread: 0,
        } as any);

        renderPage();

        await userEvent.click(screen.getByLabelText('Crear nueva conversación'));

        expect(screen.getByTestId('new-conv-drawer')).toBeInTheDocument();
        expect(mockResetSearch).toHaveBeenCalled();
    });

    it('opens the new conversation drawer and resets the user search', async () => {
        renderPage();

        await userEvent.click(screen.getByTestId('sidebar-new-conv'));

        expect(screen.getByTestId('new-conv-drawer')).toBeInTheDocument();
        expect(mockResetSearch).toHaveBeenCalled();
    });

    it('creates a conversation and sets it as active when the drawer is submitted', async () => {
        vi.mocked(apiFetch).mockResolvedValueOnce({ ...sampleConversation, id: 'conv-new' });

        renderPage();

        await userEvent.click(screen.getByTestId('sidebar-new-conv'));
        await userEvent.click(screen.getByTestId('drawer-create'));

        await waitFor(() =>
            expect(apiFetch).toHaveBeenCalledWith(
                '/chat/conversations',
                expect.objectContaining({
                    method: 'POST',
                    token: 'fake-token',
                    body: { participant_ids: ['user-99'] },
                })
            )
        );
        expect(mockAddConversation).toHaveBeenCalledWith(expect.objectContaining({ id: 'conv-new' }));
        expect(mockResetSearch).toHaveBeenCalled();
        expect(screen.getByTestId('message-list')).toBeInTheDocument();
    });

    it('does not create a conversation when the user token is missing', async () => {
        vi.mocked(useAuth).mockReturnValue({ token: null, user: { id: 'me' } } as any);

        renderPage();

        await userEvent.click(screen.getByTestId('sidebar-new-conv'));
        await userEvent.click(screen.getByTestId('drawer-create'));

        expect(apiFetch).not.toHaveBeenCalled();
    });

    it('shows a toast error when creating a conversation fails', async () => {
        vi.mocked(apiFetch).mockRejectedValueOnce(new Error('Network error'));

        renderPage();

        await userEvent.click(screen.getByTestId('sidebar-new-conv'));
        await userEvent.click(screen.getByTestId('drawer-create'));

        await waitFor(() =>
            expect(mockAddToast).toHaveBeenCalledWith('Error al crear la conversación', 'error')
        );
    });

    it('selects a conversation and renders the thread header', async () => {
        renderPage();

        await userEvent.click(screen.getByTestId('sidebar-select-conv'));

        expect(screen.getByTestId('message-list')).toBeInTheDocument();
        expect(screen.getByLabelText('Volver a conversaciones')).toBeInTheDocument();
        expect(screen.getByText('ana')).toBeInTheDocument();
        expect(screen.getByText('Activo')).toBeInTheDocument();
    });

    it('renders the error status in the thread header when the socket is in error', async () => {
        vi.mocked(useChatThread).mockReturnValue({ ...defaultChatThreadReturn, wsStatus: 'error' } as any);

        renderPage();

        await userEvent.click(screen.getByTestId('sidebar-select-conv'));

        expect(screen.getByText('Desconectado')).toBeInTheDocument();
    });

    it('renders the connecting status in the thread header when the socket is connecting', async () => {
        vi.mocked(useChatThread).mockReturnValue({ ...defaultChatThreadReturn, wsStatus: 'connecting' } as any);

        renderPage();

        await userEvent.click(screen.getByTestId('sidebar-select-conv'));

        expect(screen.getByText('Conectando...')).toBeInTheDocument();
    });

    it('marks an incoming websocket message as active when it belongs to the selected conversation', async () => {
        let capturedOnMessage: ((conversationId: string, message: DirectMessageItem) => void) | undefined;

        vi.mocked(useChatThread).mockImplementation((options) => {
            capturedOnMessage = options.onMessage;
            return defaultChatThreadReturn as any;
        });

        renderPage();

        await userEvent.click(screen.getByTestId('sidebar-select-conv'));

        act(() => capturedOnMessage?.(sampleConversation.id, sampleMessage));

        expect(mockUpdateConversationFromMessage).toHaveBeenCalledWith(
            sampleConversation.id,
            sampleMessage,
            true
        );
    });

    it('returns to the empty state when the back button is clicked', async () => {
        renderPage();

        await userEvent.click(screen.getByTestId('sidebar-select-conv'));
        expect(screen.getByTestId('message-list')).toBeInTheDocument();

        await userEvent.click(screen.getByLabelText('Volver a conversaciones'));
        expect(screen.getByText('Selecciona una conversación')).toBeInTheDocument();
    });

    it('sends a message through the active conversation', async () => {
        mockSendMessage.mockResolvedValueOnce({ error: null });

        renderPage();

        await userEvent.click(screen.getByTestId('sidebar-select-conv'));
        await userEvent.click(screen.getByTestId('message-input'));

        await waitFor(() => expect(mockSendMessage).toHaveBeenCalledWith('Hola', { mentions: [] }));
    });

    it('shows a toast when sending a message returns a send error', async () => {
        mockSendMessage.mockResolvedValueOnce({ error: 'send' });

        renderPage();

        await userEvent.click(screen.getByTestId('sidebar-select-conv'));
        await userEvent.click(screen.getByTestId('message-input'));

        await waitFor(() =>
            expect(mockAddToast).toHaveBeenCalledWith('Error al enviar mensaje', 'error')
        );
    });

    it('shows a toast when sending a message returns an upload error', async () => {
        mockSendMessage.mockResolvedValueOnce({ error: 'upload' });

        renderPage();

        await userEvent.click(screen.getByTestId('sidebar-select-conv'));
        await userEvent.click(screen.getByTestId('message-input'));

        await waitFor(() =>
            expect(mockAddToast).toHaveBeenCalledWith('Error al subir archivo', 'error')
        );
    });

    it('does not call sendMessage when there is no active conversation', async () => {
        // The default mock does not select a conversation; clicking the input should not call sendMessage.
        renderPage();

        expect(screen.queryByTestId('message-input')).not.toBeInTheDocument();
        expect(mockSendMessage).not.toHaveBeenCalled();
    });

    it('forwards filter changes to useConversations', async () => {
        renderPage();

        const input = screen.getByTestId('sidebar-filter-input');
        fireEvent.change(input, { target: { value: 'ana' } });

        expect(mockSetFilter).toHaveBeenCalledWith('ana');
    });

    it('updates the conversation list when a websocket message arrives', () => {
        let capturedOnMessage: ((conversationId: string, message: DirectMessageItem) => void) | undefined;

        vi.mocked(useChatThread).mockImplementation((options) => {
            capturedOnMessage = options.onMessage;
            return defaultChatThreadReturn as any;
        });

        renderPage();

        capturedOnMessage?.('conv-1', sampleMessage);

        expect(mockUpdateConversationFromMessage).toHaveBeenCalledWith(
            'conv-1',
            sampleMessage,
            false
        );
    });
});
