import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import CommentAdminPage from './page';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import type { ProjectCommentItem } from '@/types/projects';

vi.mock('@/context/AuthContext', () => ({ useAuth: vi.fn() }));
vi.mock('@/lib/http', () => ({ apiFetch: vi.fn() }));

const authoredComments: ProjectCommentItem[] = [
  {
    id: 'c-1',
    project_id: 'p-1',
    content: 'Gran trabajo en el proyecto.',
    author_id: 'me',
    author_name: 'pastor.e2e',
    is_resolved: false,
    created_at: '2026-07-16T08:58:00Z',
    updated_at: '2026-07-16T08:58:00Z',
    module_type: 'project',
    context_title: 'Retiro de jóvenes',
  },
  {
    id: 'c-2',
    project_id: 'p-2',
    task_id: 't-1',
    content: 'Revisar el cronograma de la actividad.',
    author_id: 'me',
    author_name: 'pastor.e2e',
    is_resolved: false,
    created_at: '2026-07-16T07:20:00Z',
    updated_at: '2026-07-16T07:20:00Z',
    module_type: 'activity',
    context_title: 'Taller de liderazgo',
  },
];

const mentions: ProjectCommentItem[] = [
  {
    id: 'c-3',
    project_id: 'p-1',
    content: '@pastor.e2e por favor revisa esto.',
    author_id: 'u-1',
    author_name: 'Ana Pérez',
    is_resolved: false,
    created_at: '2026-07-16T09:15:00Z',
    updated_at: '2026-07-16T09:15:00Z',
    module_type: 'project',
    context_title: 'Retiro de jóvenes',
    mentions: ['me'],
  },
];

function setupMocks() {
  vi.mocked(useAuth).mockReturnValue({ token: 'fake-token' } as unknown as ReturnType<typeof useAuth>);
}

describe('CommentAdminPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setupMocks();
  });

  it('renders authored comments by default', async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce(authoredComments);

    render(<CommentAdminPage />);

    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith(
        '/comments/me/created',
        expect.objectContaining({ query: { limit: '50', offset: '0' } })
      )
    );
    expect(screen.getByText('Centro de comentarios')).toBeInTheDocument();
    expect(screen.getByText('Gran trabajo en el proyecto.')).toBeInTheDocument();
    expect(screen.getByText('Retiro de jóvenes')).toBeInTheDocument();
    expect(screen.getByText('Taller de liderazgo')).toBeInTheDocument();
  });

  it('switches to the mentions tab and fetches mentions', async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce(authoredComments).mockResolvedValueOnce(mentions);

    render(<CommentAdminPage />);
    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith(
        '/comments/me/created',
        expect.objectContaining({ query: { limit: '50', offset: '0' } })
      )
    );

    fireEvent.click(screen.getByRole('tab', { name: /Menciones/i }));

    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith(
        '/comments/me/mentions',
        expect.objectContaining({ query: { limit: '50', offset: '0' } })
      )
    );
    expect(screen.getByText('@pastor.e2e por favor revisa esto.')).toBeInTheDocument();
    expect(screen.getByText('Ana Pérez')).toBeInTheDocument();
  });

  it('filters the list by search term', async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce(authoredComments);

    render(<CommentAdminPage />);
    await waitFor(() => expect(screen.getByText('Gran trabajo en el proyecto.')).toBeInTheDocument());

    fireEvent.change(screen.getByLabelText(/Buscar comentarios/i), { target: { value: 'Retiro' } });

    await waitFor(() => expect(screen.queryByText('Taller de liderazgo')).not.toBeInTheDocument(), {
      timeout: 1000,
    });
    expect(screen.getByText('Retiro de jóvenes')).toBeInTheDocument();
  });

  it('links project comments to the project page', async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce(authoredComments);

    render(<CommentAdminPage />);
    await waitFor(() => expect(screen.getByText('Gran trabajo en el proyecto.')).toBeInTheDocument());

    const link = screen.getByRole('link', { name: /Gran trabajo en el proyecto/i });
    expect(link).toHaveAttribute('href', '/plataforma/proyectos/p-1');
  });

  it('links activity comments to the project page with task query', async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce(authoredComments);

    render(<CommentAdminPage />);
    await waitFor(() => expect(screen.getByText('Revisar el cronograma de la actividad.')).toBeInTheDocument());

    const link = screen.getByRole('link', { name: /Revisar el cronograma de la actividad/i });
    expect(link).toHaveAttribute('href', '/plataforma/proyectos/p-2?task=t-1');
  });

  it('links agenda comments to the agenda page with event query', async () => {
    const agendaComment: ProjectCommentItem = {
      id: 'c-agenda',
      project_id: 'a-1',
      content: 'Revisar ubicación del evento.',
      author_id: 'me',
      author_name: 'pastor.e2e',
      is_resolved: false,
      created_at: '2026-07-16T08:58:00Z',
      updated_at: '2026-07-16T08:58:00Z',
      module_type: 'agenda',
      context_title: 'Concierto familiar',
    };
    vi.mocked(apiFetch).mockResolvedValueOnce([agendaComment]);

    render(<CommentAdminPage />);
    await waitFor(() => expect(screen.getByText('Revisar ubicación del evento.')).toBeInTheDocument());

    const link = screen.getByRole('link', { name: /Revisar ubicación del evento/i });
    expect(link).toHaveAttribute('href', '/plataforma/agenda?event=a-1');
  });

  it('filters by module type via select', async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce(authoredComments);

    render(<CommentAdminPage />);
    await waitFor(() => expect(screen.getByText('Gran trabajo en el proyecto.')).toBeInTheDocument());

    fireEvent.change(screen.getByLabelText(/Filtrar por módulo/i), { target: { value: 'project' } });

    await waitFor(() =>
      expect(apiFetch).toHaveBeenLastCalledWith(
        '/comments/me/created',
        expect.objectContaining({ query: { limit: '50', offset: '0', type: 'project' } })
      )
    );
  });

  it('renders empty state when there are no comments', async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce([]);

    render(<CommentAdminPage />);
    await waitFor(() => expect(screen.getByText('Aún no has comentado')).toBeInTheDocument());
  });

  it('shows an error state when the request fails', async () => {
    vi.mocked(apiFetch).mockRejectedValueOnce(new Error('Network error'));

    render(<CommentAdminPage />);
    await waitFor(() => expect(screen.getByText('Network error')).toBeInTheDocument());
  });

  it('loads more items when the load more button is clicked', async () => {
    const firstPage = Array.from({ length: 50 }, (_, i) => ({
      ...authoredComments[0],
      id: `c-${i}`,
      content: `Comentario ${i}`,
    }));
    const secondPage = [
      {
        ...authoredComments[0],
        id: 'c-51',
        content: 'Comentario 51',
      },
    ];

    vi.mocked(apiFetch).mockResolvedValueOnce(firstPage).mockResolvedValueOnce(secondPage);

    render(<CommentAdminPage />);
    await waitFor(() => expect(screen.getByText('Comentario 0')).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: /Cargar más/i }));

    await waitFor(() =>
      expect(apiFetch).toHaveBeenLastCalledWith(
        '/comments/me/created',
        expect.objectContaining({ query: { limit: '50', offset: '50' } })
      )
    );
    expect(screen.getByText('Comentario 51')).toBeInTheDocument();
  });
});
