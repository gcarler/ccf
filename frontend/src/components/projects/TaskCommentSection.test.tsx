import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { axe } from 'jest-axe';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import TaskCommentSection from './TaskCommentSection';
import type { ProjectTaskRecord, ProjectCommentItem } from '@/types/projects';

vi.mock('@/lib/http', () => ({
  apiFetch: vi.fn(),
}));

vi.mock('@/context/AuthContext', () => ({
  useAuth: () => ({ token: 'test-token', user: null, loading: false, isAuthenticated: true }),
}));

import { apiFetch } from '@/lib/http';
const mockApiFetch = vi.mocked(apiFetch);

const task: ProjectTaskRecord = {
  id: 't1',
  project_id: 'p1',
  title: 'Test task',
  status: 'todo',
  priority: 'medium',
};

describe('TaskCommentSection', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders comments loaded from api', async () => {
    mockApiFetch.mockResolvedValueOnce([
      { id: 'c1', project_id: 'p1', author_id: 'u1', author_name: 'Juan', content: 'Hola', created_at: '2026-01-01T10:00:00Z', updated_at: '2026-01-01T10:00:00Z', is_resolved: false },
      { id: 'c2', project_id: 'p1', author_id: 'u2', author_name: 'Ana', content: 'Listo', created_at: '2026-01-01T11:00:00Z', updated_at: '2026-01-01T11:00:00Z', is_resolved: false },
    ] as ProjectCommentItem[]);
    render(<TaskCommentSection task={task} token="test-token" onDeleteComment={vi.fn()} />);
    expect(await screen.findByText('Juan')).toBeInTheDocument();
    expect(screen.getByText('Ana')).toBeInTheDocument();
    expect(screen.getByText('Hola')).toBeInTheDocument();
    expect(screen.getByText('Listo')).toBeInTheDocument();
  });

  it('renders empty state message when no comments', async () => {
    mockApiFetch.mockResolvedValueOnce([]);
    render(<TaskCommentSection task={task} token="test-token" onDeleteComment={vi.fn()} />);
    expect(await screen.findByText(/Sin comentarios aún/)).toBeInTheDocument();
  });

  it('exposes named comment actions on touch and keyboard focus without axe violations', async () => {
    mockApiFetch.mockResolvedValueOnce([
      { id: 'c1', project_id: 'p1', author_id: 'u1', author_name: 'Juan', content: 'Hola', created_at: '2026-01-01T10:00:00Z', updated_at: '2026-01-01T10:00:00Z', is_resolved: false, is_pinned: false },
    ] as ProjectCommentItem[]);
    const { container } = render(<TaskCommentSection task={task} token="test-token" onDeleteComment={vi.fn()} />);

    await screen.findByText('Juan');
    const pinButton = screen.getByRole('button', { name: 'Fijar comentario de Juan' });
    const deleteButton = screen.getByRole('button', { name: 'Eliminar comentario de Juan' });
    expect(pinButton).toHaveClass('opacity-100', 'md:group-focus-within:opacity-100');
    expect(deleteButton).toHaveClass('opacity-100', 'md:group-focus-within:opacity-100');
    expect((await axe(container)).violations).toEqual([]);
  });

  it('calls apiFetch on send', async () => {
    mockApiFetch.mockResolvedValueOnce([]);
    mockApiFetch.mockResolvedValueOnce({
      id: 'c3', author_name: 'Tú', content: 'Test msg', created_at: '2026-01-01T12:00:00Z',
    });
    const { container } = render(<TaskCommentSection task={task} token="test-token" onDeleteComment={vi.fn()} />);
    await screen.findByText(/Sin comentarios aún/);

    const input = screen.getByPlaceholderText(/Menciona @Dzin/);
    fireEvent.change(input, { target: { value: 'Test msg' } });
    const sendButton = screen.getByRole('button', { name: 'Enviar comentario' });
    expect((await axe(container)).violations).toEqual([]);
    fireEvent.click(sendButton);

    await waitFor(() => {
      expect(mockApiFetch).toHaveBeenCalledWith(
        '/projects/p1/comments',
        expect.objectContaining({ method: 'POST' }),
      );
    });
  });

  it('autocompletes mentions with @ and includes canonical ID in mentions payload', async () => {
    mockApiFetch.mockImplementation(async (url: string) => {
      if (url.includes('/projects/comments')) {
        return [];
      }
      if (url.includes('/projects/assignee-candidates') || url.includes('/crm/personas')) {
        return [
          { id: 'usr-laury-123', nombre_completo: 'Laury Gomez' },
          { id: 'usr-ana-456', nombre_completo: 'Ana Lopez' },
        ];
      }
      if (url === '/projects/p1/comments') {
        return {
          id: 'c-new',
          author_name: 'Tú',
          content: 'Hola @Laury Gomez buen trabajo',
          mentions: ['usr-laury-123'],
          created_at: '2026-01-01T12:00:00Z',
        };
      }
      return [];
    });

    render(<TaskCommentSection task={task} token="test-token" onDeleteComment={vi.fn()} />);
    await screen.findByText(/Sin comentarios aún/);

    const input = screen.getByPlaceholderText(/Menciona @Dzin/);
    fireEvent.change(input, { target: { value: 'Hola @laury' } });

    // Autocomplete dropdown appears with matching user
    const candidateOption = await screen.findByRole('option', { name: /Laury Gomez/i });
    expect(candidateOption).toBeInTheDocument();

    // Select candidate
    fireEvent.click(candidateOption);

    // Input text updated with mention
    expect(input).toHaveValue('Hola @Laury Gomez ');

    // Send comment
    const sendButton = screen.getByRole('button', { name: 'Enviar comentario' });
    fireEvent.click(sendButton);

    await waitFor(() => {
      expect(mockApiFetch).toHaveBeenCalledWith(
        '/projects/p1/comments',
        expect.objectContaining({
          method: 'POST',
          body: expect.objectContaining({
            task_id: 't1',
            mentions: ['usr-laury-123'],
          }),
        }),
      );
    });
  });
});
