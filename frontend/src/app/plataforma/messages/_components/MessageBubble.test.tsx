import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { axe } from 'jest-axe';
import { MessageBubble } from './MessageBubble';
import type { DirectMessageItem } from '@/types/directMessages';

function makeMessage(overrides: Partial<DirectMessageItem> = {}): DirectMessageItem {
  return {
    id: 'msg-1',
    sender_id: 'sender-1',
    sender_name: 'Ana García',
    content: 'Hola @everyone',
    created_at: '2026-07-30T10:00:00Z',
    is_read: false,
    ...overrides,
  };
}

describe('MessageBubble', () => {
  it('renders own message on the right side', () => {
    const message = makeMessage();
    render(<MessageBubble message={message} isOwn showSender={false} onReply={vi.fn()} />);
    expect(screen.getByText((text) => text.includes('@everyone'))).toBeInTheDocument();
    expect(document.querySelector('.justify-end')).toBeInTheDocument();
  });

  it('renders foreign message with sender name and avatar', () => {
    const message = makeMessage();
    render(<MessageBubble message={message} isOwn={false} showSender onReply={vi.fn()} />);
    expect(screen.getByText('Ana García')).toBeInTheDocument();
    expect(document.querySelector('.justify-start')).toBeInTheDocument();
  });

  it('highlights mentions in content', () => {
    const message = makeMessage({ content: 'Hola @juan y @maria' });
    render(<MessageBubble message={message} isOwn={false} showSender={false} onReply={vi.fn()} />);
    const mentions = screen.getAllByText(/@\S+/);
    expect(mentions.length).toBeGreaterThanOrEqual(2);
  });

  it('renders image attachment', () => {
    const message = makeMessage({
      attachment_url: 'https://example.com/file.png',
      attachment_type: 'image',
      attachment_name: 'file.png',
    });
    const { container } = render(<MessageBubble message={message} isOwn showSender={false} onReply={vi.fn()} />);
    expect(container.querySelector('img')).toBeInTheDocument();
  });

  it('renders file attachment as a link', () => {
    const message = makeMessage({
      attachment_url: 'https://example.com/doc.pdf',
      attachment_type: 'pdf',
      attachment_name: 'doc.pdf',
    });
    render(<MessageBubble message={message} isOwn showSender={false} onReply={vi.fn()} />);
    expect(screen.getByText('doc.pdf')).toBeInTheDocument();
  });

  it('renders reply preview', () => {
    const message = makeMessage({
      reply_preview: { id: 'r1', sender_name: 'Pedro', content: 'Mensaje original' },
    });
    render(<MessageBubble message={message} isOwn showSender={false} onReply={vi.fn()} />);
    expect(screen.getByText(/Pedro:/)).toBeInTheDocument();
    expect(screen.getByText('Mensaje original')).toBeInTheDocument();
  });

  it('calls onReply when reply button is clicked', () => {
    const onReply = vi.fn();
    const message = makeMessage();
    render(<MessageBubble message={message} isOwn={false} showSender={false} onReply={onReply} />);
    const button = screen.getByLabelText('Responder');
    fireEvent.click(button);
    expect(onReply).toHaveBeenCalledWith(message);
  });

  it('shows double check for read own messages', () => {
    const message = makeMessage({ is_read: true });
    render(<MessageBubble message={message} isOwn showSender={false} onReply={vi.fn()} />);
    expect(screen.getByText(/✓/)).toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    vi.useRealTimers();
    const message = makeMessage({
      reply_preview: { id: 'r1', sender_name: 'Pedro', content: 'Original' },
    });
    const { container } = render(
      <MessageBubble message={message} isOwn={false} showSender onReply={vi.fn()} />
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
