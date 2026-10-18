import React from 'react';
import { render as rtlRender, screen, fireEvent, waitFor } from '@testing-library/react';
import { axe } from 'jest-axe';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { SidebarLayerProvider } from '@/context/SidebarLayerContext';
import TaskCommentSection from './TaskCommentSection';
import type { ProjectTaskRecord, ProjectCommentItem } from '@/types/projects';

function render(ui: React.ReactElement, options?: Parameters<typeof rtlRender>[1]) {
  return rtlRender(ui, { wrapper: SidebarLayerProvider, ...options });
}

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

  it('triggers mention autocomplete when clicking the @ button', async () => {
    mockApiFetch.mockImplementation(async (url: string) => {
      if (url.includes('/projects/comments')) return [];
      if (url.includes('/projects/assignee-candidates') || url.includes('/crm/personas')) {
        return [
          { id: 'usr-carlos-1', nombre_completo: 'Carlos Gomez' },
        ];
      }
      return [];
    });

    render(<TaskCommentSection task={task} token="test-token" onDeleteComment={vi.fn()} />);
    await screen.findByText(/Sin comentarios aún/);

    const atButton = screen.getByRole('button', { name: 'Mencionar usuario con @' });
    fireEvent.click(atButton);

    const option = await screen.findByRole('option', { name: /Carlos Gomez/i });
    expect(option).toBeInTheDocument();
  });

  it('renders comment attachments with open link and preview button opening ProjectFileViewerDrawer', async () => {
    mockApiFetch.mockResolvedValueOnce([
      {
        id: 'c10',
        project_id: 'p1',
        author_id: 'u1',
        author_name: 'Carlos',
        content: 'Adjunto el entregable de la fase',
        created_at: '2026-01-01T10:00:00Z',
        updated_at: '2026-01-01T10:00:00Z',
        is_resolved: false,
        attachments: [
          {
            name: 'entregable.pdf',
            url: 'https://example.com/entregable.pdf',
            size: 2048,
            type: 'application/pdf',
          },
        ],
      },
    ] as ProjectCommentItem[]);

    const { container } = render(
      <TaskCommentSection task={task} token="test-token" onDeleteComment={vi.fn()} />
    );

    await screen.findByText('Carlos');
    expect(screen.getByText('entregable.pdf')).toBeInTheDocument();

    const openLink = screen.getByRole('link', {
      name: 'Abrir archivo entregable.pdf en una pestaña nueva',
    });
    expect(openLink).toHaveAttribute('href', 'https://example.com/entregable.pdf');
    expect(openLink).toHaveAttribute('target', '_blank');

    const previewButton = screen.getByRole('button', {
      name: 'Previsualizar archivo entregable.pdf',
    });
    expect(previewButton).toBeInTheDocument();

    // Verify accessibility before opening drawer
    expect((await axe(container)).violations).toEqual([]);

    // Click preview button to open in-app drawer
    fireEvent.click(previewButton);

    expect(
      await screen.findByRole('dialog', { name: 'Visor Universal Embebido' })
    ).toBeInTheDocument();
    const iframe = screen.getByTitle('entregable.pdf');
    expect(iframe).toHaveAttribute('src', 'https://example.com/entregable.pdf#toolbar=1&navpanes=0');
  });

  it('summarizes PMI work package comment counts, renders semantic badges, and filters by category', async () => {
    mockApiFetch.mockResolvedValueOnce([
      {
        id: 'c-blocker',
        project_id: 'p1',
        author_id: 'u1',
        author_name: 'Elena',
        content: '[BLOQUEO EDT] Dependencia externa pendiente de proveedor',
        created_at: '2026-01-01T10:00:00Z',
        updated_at: '2026-01-01T10:00:00Z',
        is_resolved: false,
        is_pinned: true,
      },
      {
        id: 'c-decision',
        project_id: 'p1',
        author_id: 'u2',
        author_name: 'Marco',
        content: '[DECISIÓN TÉCNICA] Se aprueba migración incremental por lote',
        created_at: '2026-01-01T11:00:00Z',
        updated_at: '2026-01-01T11:00:00Z',
        is_resolved: false,
        is_pinned: false,
      },
      {
        id: 'c-evidence',
        project_id: 'p1',
        author_id: 'u3',
        author_name: 'Lucia',
        content: '[EVIDENCIA DOD] Acta de validación firmada por sponsor',
        created_at: '2026-01-01T12:00:00Z',
        updated_at: '2026-01-01T12:00:00Z',
        is_resolved: false,
        is_pinned: false,
      },
    ] as ProjectCommentItem[]);

    render(<TaskCommentSection task={task} token="test-token" onDeleteComment={vi.fn()} />);

    await screen.findByText('Elena');
    expect(screen.getByTestId('task-comments-pmi-summary')).toBeInTheDocument();
    expect(screen.getByTestId('task-comments-pmi-count-blocker')).toHaveTextContent('1');
    expect(screen.getByTestId('task-comments-pmi-count-decision')).toHaveTextContent('1');
    expect(screen.getByTestId('task-comments-pmi-count-evidence')).toHaveTextContent('1');
    expect(screen.getByTestId('task-comments-pmi-count-pinned')).toHaveTextContent('1');

    expect(screen.getByTestId('task-comment-pmi-badge-blocker')).toHaveTextContent('Bloqueo / Impedimento');
    expect(screen.getByTestId('task-comment-pmi-badge-decision')).toHaveTextContent('Decisión Técnica');
    expect(screen.getByTestId('task-comment-pmi-badge-evidence')).toHaveTextContent('Evidencia DoD');

    const filterGroup = screen.getByTestId('task-comments-pmi-filter');
    fireEvent.click(screen.getByRole('button', { name: /Bloqueo \/ Impedimento \(1\)/i }));
    expect(screen.getByText(/Dependencia externa pendiente/)).toBeInTheDocument();
    expect(screen.queryByText(/Se aprueba migración incremental/)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /Decisión Técnica \(1\)/i }));
    expect(screen.getByText(/Se aprueba migración incremental/)).toBeInTheDocument();
    expect(screen.queryByText(/Dependencia externa pendiente/)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /Evidencia DoD \(1\)/i }));
    expect(screen.getByText(/Acta de validación firmada/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /Fijado \(1\)/i }));
    expect(screen.getByText(/Dependencia externa pendiente/)).toBeInTheDocument();
    expect(screen.queryByText(/Acta de validación firmada/)).not.toBeInTheDocument();

    expect(filterGroup).toBeInTheDocument();
  });

  it('inserts and switches 1-click PMI prefixes in the composer without duplicating prefixes', async () => {
    mockApiFetch.mockResolvedValueOnce([]);
    render(<TaskCommentSection task={task} token="test-token" onDeleteComment={vi.fn()} />);
    await screen.findByText(/Sin comentarios aún/);

    const input = screen.getByRole('textbox', { name: 'Escribe un comentario' });
    fireEvent.change(input, { target: { value: 'Revisión de entregable' } });

    const blockerTag = screen.getByTestId('task-comment-tag-blocker');
    const decisionTag = screen.getByTestId('task-comment-tag-decision');
    const evidenceTag = screen.getByTestId('task-comment-tag-evidence');

    fireEvent.click(blockerTag);
    expect(input).toHaveValue('[BLOQUEO EDT] Revisión de entregable');
    expect(blockerTag).toHaveAttribute('aria-pressed', 'true');

    // Switching to another tag replaces the prefix instead of duplicating it
    fireEvent.click(decisionTag);
    expect(input).toHaveValue('[DECISIÓN TÉCNICA] Revisión de entregable');
    expect(decisionTag).toHaveAttribute('aria-pressed', 'true');
    expect(blockerTag).toHaveAttribute('aria-pressed', 'false');

    fireEvent.click(evidenceTag);
    expect(input).toHaveValue('[EVIDENCIA DOD] Revisión de entregable');
    expect(evidenceTag).toHaveAttribute('aria-pressed', 'true');

    // Clicking the active tag again removes the prefix cleanly
    fireEvent.click(evidenceTag);
    expect(input).toHaveValue('Revisión de entregable');
    expect(evidenceTag).toHaveAttribute('aria-pressed', 'false');
  });
});


