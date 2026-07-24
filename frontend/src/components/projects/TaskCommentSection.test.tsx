import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import TaskCommentSection from './TaskCommentSection';
import type { ProjectTaskRecord } from '@/types/projects';

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
      { id: 'c1', author_name: 'Juan', content: 'Hola', created_at: '2026-01-01T10:00:00Z' },
      { id: 'c2', author_name: 'Ana', content: 'Listo', created_at: '2026-01-01T11:00:00Z' },
    ] as any);
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

  it('calls apiFetch on send', async () => {
    mockApiFetch.mockResolvedValueOnce([]);
    mockApiFetch.mockResolvedValueOnce({
      id: 'c3', author_name: 'Tú', content: 'Test msg', created_at: '2026-01-01T12:00:00Z',
    });
    render(<TaskCommentSection task={task} token="test-token" onDeleteComment={vi.fn()} />);
    await screen.findByText(/Sin comentarios aún/);

    const input = screen.getByPlaceholderText(/Menciona @Dzin/);
    fireEvent.change(input, { target: { value: 'Test msg' } });
    fireEvent.keyDown(input, { key: 'Enter' });

    await waitFor(() => {
      expect(mockApiFetch).toHaveBeenCalledWith(
        '/projects/p1/comments',
        expect.objectContaining({ method: 'POST' }),
      );
    });
  });
});
