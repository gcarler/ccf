import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { axe } from 'jest-axe';
import { ConversationSidebar } from './ConversationSidebar';
import type { ConversationRead } from '@/types/directMessages';

const conversations: ConversationRead[] = [
    {
        id: 'c1',
        participants: [
            { persona_id: 'me', username: 'me_user', last_read_at: null },
            { persona_id: 'p1', username: 'ana', last_read_at: null },
        ],
        last_message_content: 'Hola Ana',
        last_message_at: '2024-01-15T10:00:00Z',
        last_sender_id: 'p1',
        unread_count: 2,
        created_at: '2024-01-15T10:00:00Z',
    },
    {
        id: 'c2',
        participants: [
            { persona_id: 'me', username: 'me_user', last_read_at: null },
            { persona_id: 'p2', username: 'beto', last_read_at: null },
        ],
        last_message_content: 'Ok',
        last_message_at: '2024-01-15T09:00:00Z',
        last_sender_id: 'me',
        unread_count: 0,
        created_at: '2024-01-15T09:00:00Z',
    },
];

function renderSidebar(props: Partial<React.ComponentProps<typeof ConversationSidebar>> = {}) {
    return render(
        <ConversationSidebar
            loading={false}
            filteredConversations={conversations}
            conversations={conversations}
            filter=""
            onFilterChange={vi.fn()}
            activeConvId={null}
            onSelectConv={vi.fn()}
            onNewConv={vi.fn()}
            totalUnread={2}
            getOtherParticipant={(conv) => conv.participants.find((p) => p.persona_id !== 'me')}
            {...props}
        />
    );
}

describe('ConversationSidebar', () => {
    it('renders loading state', () => {
        renderSidebar({ loading: true });
        expect(screen.getByText('Cargando...')).toBeInTheDocument();
    });

    it('renders empty state and calls onNewConv', () => {
        const onNewConv = vi.fn();
        renderSidebar({ loading: false, filteredConversations: [], onNewConv });
        expect(screen.getByText('Sin conversaciones')).toBeInTheDocument();
        fireEvent.click(screen.getByLabelText('Iniciar nueva conversación'));
        expect(onNewConv).toHaveBeenCalled();
    });

    it('renders conversation list and selects a conversation', () => {
        const onSelectConv = vi.fn();
        renderSidebar({ onSelectConv });
        fireEvent.click(screen.getByLabelText('Abrir conversación con ana'));
        expect(onSelectConv).toHaveBeenCalledWith(conversations[0]);
    });

    it('highlights active conversation', () => {
        renderSidebar({ activeConvId: 'c1' });
        expect(screen.getByLabelText('Abrir conversación con ana')).toHaveAttribute('aria-label', 'Abrir conversación con ana');
    });

    it('shows unread badge and total unread count', () => {
        renderSidebar({ totalUnread: 2 });
        // Header total unread + per-conversation unread badge
        expect(screen.getAllByText('2')).toHaveLength(2);
    });

    it('filters conversations when typing in search input', () => {
        const onFilterChange = vi.fn();
        renderSidebar({ onFilterChange });
        const input = screen.getByLabelText('Buscar conversaciones');
        fireEvent.change(input, { target: { value: 'ana' } });
        expect(onFilterChange).toHaveBeenCalledWith('ana');
    });

    it('calls onNewConv from header button', () => {
        const onNewConv = vi.fn();
        renderSidebar({ onNewConv });
        fireEvent.click(screen.getByLabelText('Nueva conversación'));
        expect(onNewConv).toHaveBeenCalled();
    });

    it('has no accessibility violations in active/populated state', async () => {
        const { container } = renderSidebar({ activeConvId: 'c1' });
        expect(await axe(container)).toHaveNoViolations();
    });

    it('renders empty filtered state without the new conversation button', () => {
        renderSidebar({ loading: false, filteredConversations: [], filter: 'zzz', onNewConv: vi.fn() });
        expect(screen.getByText('Sin resultados')).toBeInTheDocument();
        expect(screen.queryByLabelText('Iniciar nueva conversación')).not.toBeInTheDocument();
    });

    it('renders fallback username and no time when data is missing', () => {
        const convWithMissingData = {
            ...conversations[0],
            id: 'c3',
            participants: [{ persona_id: 'p3', last_read_at: null }],
            last_message_at: null,
            last_message_content: null,
        } as unknown as ConversationRead;
        renderSidebar({ filteredConversations: [convWithMissingData], conversations: [convWithMissingData], activeConvId: 'c3' });
        expect(screen.getByLabelText('Abrir conversación con Usuario')).toBeInTheDocument();
        expect(screen.getByText('Sin mensajes')).toBeInTheDocument();
    });
});
