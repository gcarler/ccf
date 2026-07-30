import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { axe } from 'jest-axe';
import { MessageList } from './MessageList';
import type { DirectMessageItem } from '@/types/directMessages';

function makeMessage(id: string, senderId: string, content: string): DirectMessageItem {
  return {
    id,
    sender_id: senderId,
    sender_name: `User ${senderId}`,
    content,
    created_at: '2026-07-30T10:00:00Z',
    is_read: true,
  };
}

describe('MessageList', () => {
  it('renders empty state when no messages', () => {
    render(
      <MessageList
        messages={[]}
        loading={false}
        currentUserId="u1"
        onLoadOlder={vi.fn()}
        onReply={vi.fn()}
      />
    );
    expect(screen.getByText('Sin mensajes aún')).toBeInTheDocument();
    expect(screen.getByText('Sé el primero en escribir')).toBeInTheDocument();
  });

  it('renders loading state', () => {
    render(
      <MessageList
        messages={[]}
        loading={true}
        currentUserId="u1"
        onLoadOlder={vi.fn()}
        onReply={vi.fn()}
      />
    );
    expect(screen.getByText('Cargando mensajes...')).toBeInTheDocument();
  });

  it('renders messages and groups consecutive messages from the same sender', () => {
    const messages: DirectMessageItem[] = [
      makeMessage('m1', 'u1', 'Hola'),
      makeMessage('m2', 'u1', '¿Cómo están?'),
      makeMessage('m3', 'u2', 'Bien'),
    ];
    render(
      <MessageList
        messages={messages}
        loading={false}
        currentUserId="u1"
        onLoadOlder={vi.fn()}
        onReply={vi.fn()}
      />
    );
    expect(screen.getByText('Hola')).toBeInTheDocument();
    expect(screen.getByText('¿Cómo están?')).toBeInTheDocument();
    expect(screen.getByText('Bien')).toBeInTheDocument();
    expect(screen.getByText('User u2')).toBeInTheDocument();
  });

  it('calls onLoadOlder when scrolling near the top', () => {
    const onLoadOlder = vi.fn();
    const { container } = render(
      <MessageList
        messages={[makeMessage('m1', 'u2', 'Hola')]}
        loading={false}
        currentUserId="u1"
        onLoadOlder={onLoadOlder}
        onReply={vi.fn()}
        hasMore={true}
      />
    );
    const scrollContainer = container.firstChild as HTMLElement;
    Object.defineProperty(scrollContainer, 'scrollTop', { writable: true, configurable: true, value: 0 });
    Object.defineProperty(scrollContainer, 'scrollHeight', { writable: true, configurable: true, value: 500 });
    Object.defineProperty(scrollContainer, 'clientHeight', { writable: true, configurable: true, value: 500 });
    fireEvent.scroll(scrollContainer);
    expect(onLoadOlder).toHaveBeenCalled();
  });

  it('does not call onLoadOlder when hasMore is false', () => {
    const onLoadOlder = vi.fn();
    const { container } = render(
      <MessageList
        messages={[makeMessage('m1', 'u2', 'Hola')]}
        loading={false}
        currentUserId="u1"
        onLoadOlder={onLoadOlder}
        onReply={vi.fn()}
        hasMore={false}
      />
    );
    const scrollContainer = container.firstChild as HTMLElement;
    Object.defineProperty(scrollContainer, 'scrollTop', { writable: true, configurable: true, value: 0 });
    fireEvent.scroll(scrollContainer);
    expect(onLoadOlder).not.toHaveBeenCalled();
  });

  it('has no accessibility violations', async () => {
    vi.useRealTimers();
    const messages: DirectMessageItem[] = [
      makeMessage('m1', 'u2', 'Hola'),
      makeMessage('m2', 'u1', '¿Cómo estás?'),
    ];
    const { container } = render(
      <MessageList
        messages={messages}
        loading={false}
        currentUserId="u1"
        onLoadOlder={vi.fn()}
        onReply={vi.fn()}
      />
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
