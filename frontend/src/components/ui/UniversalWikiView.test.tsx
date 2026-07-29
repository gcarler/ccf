import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { axe } from 'jest-axe';
import UniversalWikiView from './UniversalWikiView';

vi.mock('@/hooks/useWikiDocument', () => ({
  useWikiDocument: () => ({
    content: '<p>Contenido inicial de la wiki</p>',
    setContent: vi.fn(),
    isLoading: false,
    isSaving: false,
    lastSaved: new Date('2026-07-28T12:00:00Z'),
    error: null,
    saveNow: vi.fn(),
  }),
}));

vi.mock('@tiptap/react', () => ({
  useEditor: () => ({
    getHTML: () => '<p>Contenido inicial de la wiki</p>',
    getText: () => 'Contenido inicial de la wiki',
    commands: {
      clearContent: vi.fn(),
    },
  }),
  EditorContent: () => <div data-testid="tiptap-editor">Editor TipTap Mock</div>,
}));

describe('UniversalWikiView component', () => {
  it('renders wiki title and sidebar links', () => {
    render(<UniversalWikiView moduleName="Proyectos" />);

    expect(screen.getAllByText(/Wiki Proyectos/i).length).toBeGreaterThan(0);
    expect(screen.getByText('Protocolos')).toBeInTheDocument();
    expect(screen.getByText('Guías')).toBeInTheDocument();
  });

  it('toggles preview mode on eye button click', () => {
    render(<UniversalWikiView moduleName="Proyectos" />);

    const previewBtn = screen.getByRole('button', { name: /Vista previa/i });
    fireEvent.click(previewBtn);

    expect(screen.getByText('Contenido inicial de la wiki')).toBeInTheDocument();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<UniversalWikiView moduleName="Proyectos" />);
    const results = await axe(container);
    expect(results.violations).toHaveLength(0);
  });
});
