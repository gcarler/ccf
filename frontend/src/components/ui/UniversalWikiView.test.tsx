import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { axe } from 'jest-axe';
import UniversalWikiView from './UniversalWikiView';

const harness = vi.hoisted(() => ({
    active: new Set<string>(),
    imageSrcs: [] as string[],
    revision: 0,
    options: null as { onUpdate?: (args: { editor: { getHTML: () => string } }) => void } | null,
}));

vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

vi.mock('@/hooks/useWikiDocument', async () => {
    const { useState } = await import('react') as typeof import('react');
    return {
        useWikiDocument: () => {
            const [content, setContent] = useState('<p>Contenido inicial de la wiki</p>');
            return {
                content,
                setContent,
                isLoading: false,
                isSaving: false,
                lastSaved: new Date('2026-07-28T12:00:00Z'),
                error: null,
                saveNow: vi.fn(),
            };
        },
    };
});

vi.mock('@tiptap/react', () => {
    const toggle = (key: string) => {
        if (harness.active.has(key)) harness.active.delete(key);
        else harness.active.add(key);
    };
    const currentHtml = () =>
        harness.revision === 0
            ? '<p>Contenido inicial de la wiki</p>'
            : `<p>Contenido revisión ${harness.revision}</p>`;
    const emitUpdate = () => {
        harness.revision += 1;
        harness.options?.onUpdate?.({ editor: { getHTML: currentHtml } });
    };
    harness.options = null as {
        onUpdate?: (args: { editor: { getHTML: () => string } }) => void;
    } | null;
    const chain: Record<string, unknown> = new Proxy({}, {
        get: (_target, method: string) => (...args: unknown[]) => {
            if (method === 'run') { emitUpdate(); return true; }
            if (method === 'toggleHeading') toggle(`heading-${(args[0] as { level: number }).level}`);
            else if (method === 'toggleBulletList') toggle('bulletList');
            else if (method === 'toggleOrderedList') toggle('orderedList');
            else if (method === 'toggleTaskList') toggle('taskList');
            else if (method === 'toggleBlockquote') toggle('blockquote');
            else if (method === 'toggleBold') toggle('bold');
            else if (method === 'toggleItalic') toggle('italic');
            else if (method === 'toggleUnderline') toggle('underline');
            else if (method === 'toggleCode') toggle('code');
            else if (method === 'setParagraph') toggle('paragraph');
            else if (method === 'setImage') harness.imageSrcs.push((args[0] as { src: string }).src);
            else if (method === 'setHorizontalRule') toggle('horizontalRule');
            return chain;
        },
    });
    const editor = {
        getHTML: currentHtml,
        getText: () => 'Contenido inicial de la wiki',
        isDestroyed: false,
        isActive: (name: string, attributes?: { level?: number }) =>
            harness.active.has(name === 'heading' ? `heading-${attributes?.level}` : name),
        chain: () => chain,
        commands: {
            clearContent: vi.fn(),
            setContent: vi.fn(),
        },
    };
    harness.options = null;
    const useEditor = (options: { onUpdate?: (args: { editor: { getHTML: () => string } }) => void }) => {
        if (harness.options === null) harness.options = options;
        return editor;
    };
    return {
        useEditor,
        EditorContent: () => <div data-testid="tiptap-editor">Editor TipTap Mock</div>,
    };
});

beforeEach(() => {
    harness.active.clear();
    harness.imageSrcs = [];
    harness.revision = 0;
    harness.options = null;
});

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

    it('expone la barra de herramientas con tipografia completa, subrayado y listas', () => {
        render(<UniversalWikiView moduleName="Proyectos" />);
        const toolbar = screen.getByRole('toolbar', { name: 'Herramientas de la wiki' });
        expect(toolbar).toBeInTheDocument();

        const toolbarActions = [
            ['Encabezado 1', 'heading-1'],
            ['Encabezado 2', 'heading-2'],
            ['Encabezado 3', 'heading-3'],
            ['Párrafo', 'paragraph'],
            ['Negrita', 'bold'],
            ['Cursiva', 'italic'],
            ['Subrayado', 'underline'],
            ['Código', 'code'],
            ['Lista con viñetas', 'bulletList'],
            ['Lista numerada', 'orderedList'],
            ['Lista de tareas', 'taskList'],
            ['Cita', 'blockquote'],
        ];
        for (const [label, key] of toolbarActions) {
            const button = screen.getByRole('button', { name: label });
            expect(button).toHaveAttribute('aria-pressed', 'false');
            fireEvent.click(button);
            expect(button).toHaveAttribute('aria-pressed', 'true');
            expect(harness.active.has(key)).toBe(true);
        }
    });

    it('inserta imagenes por URL desde el panel y normaliza rutas estaticas', async () => {
        render(<UniversalWikiView moduleName="Proyectos" />);

        fireEvent.click(screen.getByRole('button', { name: 'Insertar imagen' }));
        expect(screen.getByTestId('wiki-image-panel')).toBeInTheDocument();

        fireEvent.change(screen.getByLabelText('URL de la imagen'), { target: { value: '/static/proyectos/wiki/foto.png' } });
        fireEvent.click(screen.getByRole('button', { name: 'Añadir imagen por URL' }));

        await waitFor(() => expect(harness.imageSrcs).toEqual(['/api/static/proyectos/wiki/foto.png']));
        expect(screen.queryByTestId('wiki-image-panel')).toBeNull();
    });

    it('oculta la barra de herramientas en modo vista previa', () => {
        render(<UniversalWikiView moduleName="Proyectos" />);

        fireEvent.click(screen.getByRole('button', { name: /Vista previa/i }));
        expect(screen.queryByRole('toolbar', { name: 'Herramientas de la wiki' })).toBeNull();
        expect(screen.getByTestId('wiki-preview')).toBeInTheDocument();
    });

    it('has no accessibility violations', async () => {
        const { container } = render(<UniversalWikiView moduleName="Proyectos" />);
        const results = await axe(container);
        expect(results.violations).toHaveLength(0);
    });
});
