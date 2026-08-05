import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { axe } from 'jest-axe';
import { MessageInput } from './MessageInput';
import type { DirectMessageItem } from '@/types/directMessages';
import { apiFetch } from '@/lib/http';

vi.mock('@/lib/http', () => ({
  apiFetch: vi.fn(),
}));

const mockOnSend = vi.fn().mockResolvedValue({ error: null });
const mockOnClearReply = vi.fn();

function renderInput(props: Partial<React.ComponentProps<typeof MessageInput>> = {}) {
  return render(
    <MessageInput
      token="test-token"
      disabled={false}
      sending={false}
      replyTo={null}
      onClearReply={mockOnClearReply}
      onSend={mockOnSend}
      {...props}
    />
  );
}

describe('MessageInput', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mockOnSend.mockClear();
    mockOnClearReply.mockClear();
    vi.mocked(apiFetch).mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders textarea and send button', () => {
    renderInput();
    expect(screen.getByLabelText('Escribe un mensaje')).toBeInTheDocument();
    expect(screen.getByLabelText('Enviar mensaje')).toBeInTheDocument();
  });

  it('calls onSend with content when enter is pressed', () => {
    renderInput();
    const textarea = screen.getByLabelText('Escribe un mensaje');
    fireEvent.change(textarea, { target: { value: 'Hola equipo' } });
    fireEvent.keyDown(textarea, { key: 'Enter', code: 'Enter' });
    expect(mockOnSend).toHaveBeenCalledWith('Hola equipo', expect.objectContaining({ mentions: [] }));
  });

  it('shows reply preview and calls onClearReply when closing', () => {
    const replyTo: DirectMessageItem = {
      id: 'r1',
      sender_id: 's1',
      sender_name: 'Pedro',
      content: 'Mensaje previo',
      created_at: '2026-07-30T10:00:00Z',
      is_read: true,
    };
    renderInput({ replyTo });
    expect(screen.getByText(/Respondiendo a Pedro/)).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText('Cerrar respuesta'));
    expect(mockOnClearReply).toHaveBeenCalled();
  });

  it('searches users when typing @ and shows dropdown', async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce([
      { id: 'u1', username: 'juanperez', email: 'juan@example.com' },
    ]);
    renderInput();
    const textarea = screen.getByLabelText('Escribe un mensaje') as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: 'Hola @juan' } });
    await act(async () => {
      vi.runAllTimers();
    });
    expect(apiFetch).toHaveBeenCalledWith(expect.stringContaining('/chat/users/search'), expect.any(Object));
    expect(screen.getByText('juanperez')).toBeInTheDocument();
  });

  it('shows attachment preview when a file is selected', () => {
    renderInput();
    const file = new File(['hello'], 'hello.txt', { type: 'text/plain' });
    const input = screen.getByTestId('file-input');
    fireEvent.change(input, { target: { files: [file] } });
    expect(screen.getByText('hello.txt')).toBeInTheDocument();
  });

  it('does not call onSend when disabled', () => {
    renderInput({ disabled: true });
    const textarea = screen.getByLabelText('Escribe un mensaje');
    fireEvent.change(textarea, { target: { value: 'No enviar' } });
    fireEvent.keyDown(textarea, { key: 'Enter', code: 'Enter' });
    expect(mockOnSend).not.toHaveBeenCalled();
  });

  it('has no accessibility violations', async () => {
    vi.useRealTimers();
    const { container } = renderInput();
    expect(await axe(container)).toHaveNoViolations();
  });
});
