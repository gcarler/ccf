import React from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const harness = vi.hoisted(() => ({
    options: null as { content?: string; onUpdate?: (args: { editor: { getHTML: () => string } }) => void } | null,
    html: '',
    active: new Set<string>(),
    revision: 0,
    images: [] as Array<{ src?: string; alt?: string }>,
}));

vi.mock('@tiptap/react', async (importOriginal) => {
    const actual = await importOriginal<typeof import('@tiptap/react')>();
    const toggle = (name: string, key = name) => {
        if (harness.active.has(key)) harness.active.delete(key);
        else harness.active.add(key);
    };
    const emitUpdate = (nextHtml?: string) => {
        harness.revision += 1;
        harness.html = nextHtml ?? `<p>toolbar-${harness.revision}</p>`;
        harness.options?.onUpdate?.({ editor: { getHTML: () => harness.html } });
    };
    const chain = new Proxy({}, {
        get: (_target, property: string) => (...args: unknown[]) => {
            if (property === 'run') return true;
            if (property === 'focus') return chain;
            if (property === 'toggleHeading') toggle('heading', `heading-${(args[0] as { level: number }).level}`);
            if (property === 'toggleBulletList') toggle('bulletList');
            if (property === 'toggleOrderedList') toggle('orderedList');
            if (property === 'toggleBlockquote') toggle('blockquote');
            if (property === 'setHorizontalRule') toggle('horizontalRule');
            if (property === 'toggleBold') toggle('bold');
            if (property === 'toggleItalic') toggle('italic');
            if (property === 'toggleTaskList') toggle('taskList');
            if (property === 'toggleUnderline') toggle('underline');
            if (property === 'toggleCode') toggle('code');
            if (property === 'setParagraph') toggle('paragraph');
            if (property === 'setImage') {
                toggle('image');
                harness.images.push((args as unknown as [{ src?: string; alt?: string }])[0] ?? {});
            }
            if (property === 'insertContent') {
                emitUpdate(`${harness.html}${String(args[0] ?? '')}`);
            } else {
                emitUpdate();
            }
            return chain;
        },
    });
    const editor = {
        getHTML: () => harness.html,
        chain: () => chain,
        isActive: (name: string, attributes?: { level?: number }) =>
            harness.active.has(name === 'heading' ? `heading-${attributes?.level}` : name),
        can: () => ({ undo: () => true, redo: () => true }),
        commands: {
            setContent: (content: string) => { harness.html = content; },
        },
    };
    return {
        ...actual,
        useEditor: (options: typeof harness.options) => {
            if (harness.options === null && options?.content !== undefined) harness.html = options.content;
            harness.options = options;
            return editor;
        },
        EditorContent: () => React.createElement('div', {
            'data-testid': 'wiki-content',
            contentEditable: true,
            suppressContentEditableWarning: true,
            dangerouslySetInnerHTML: { __html: harness.html },
            onInput: (event: React.FormEvent<HTMLDivElement>) => {
                harness.html = event.currentTarget.innerHTML;
                harness.options?.onUpdate?.({ editor: { getHTML: () => harness.html } });
            },
        }),
    };
});

vi.mock('@/context/AuthContext', () => ({ useAuth: () => ({ token: 'test-token', loading: false }) }));
vi.mock('@/lib/http', () => ({ apiFetch: vi.fn() }));
vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

import ProjectWikiEditor from './ProjectWikiEditor';
import { apiFetch } from '@/lib/http';
import { toast } from 'sonner';

const apiFetchMock = vi.mocked(apiFetch);

function deferred<T>() {
    let resolve!: (value: T) => void;
    const promise = new Promise<T>((done) => { resolve = done; });
    return { promise, resolve };
}

beforeEach(() => {
    vi.clearAllMocks();
    harness.options = null;
    harness.html = '';
    harness.active.clear();
    harness.revision = 0;
    harness.images = [];
    apiFetchMock.mockResolvedValue({ content: '<p>Inicial</p>' } as never);
});

afterEach(() => {
    vi.useRealTimers();
});

describe('ProjectWikiEditor', () => {
    it('expone la barra de formato con etiquetas y estados activos accesibles', async () => {
        render(<ProjectWikiEditor project_id="project-1" />);
        await screen.findByRole('button', { name: 'Guardar cambios de la wiki' });

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
            ['Separador horizontal', 'horizontalRule'],
        ];
        for (const [label, activeKey] of toolbarActions) {
            const button = screen.getByRole('button', { name: label });
            expect(button).toHaveAttribute('aria-pressed', 'false');
            fireEvent.click(button);
            expect(button).toHaveAttribute('aria-pressed', 'true');
            expect(harness.active.has(activeKey)).toBe(true);
        }
    });

    it('abre el panel de imagen e inserta una imagen por URL', async () => {
        render(<ProjectWikiEditor project_id="project-1" />);
        await screen.findByText('Inicial');

        expect(screen.queryByTestId('wiki-image-panel')).toBeNull();
        fireEvent.click(screen.getByRole('button', { name: 'Insertar imagen' }));
        expect(screen.getByTestId('wiki-image-panel')).toBeInTheDocument();

        fireEvent.change(screen.getByLabelText('URL de la imagen'), { target: { value: 'https://ejemplo.org/plan.png' } });
        fireEvent.click(screen.getByRole('button', { name: 'Añadir imagen por URL' }));

        await waitFor(() => expect(harness.images).toHaveLength(1));
        expect(harness.images[0]).toEqual({ src: 'https://ejemplo.org/plan.png', alt: 'imagen de wiki' });
        expect(screen.queryByTestId('wiki-image-panel')).toBeNull();
    });

    it('sube la imagen a POST /projects/{id}/wiki/images y la inserta con URL normalizada', async () => {
        render(<ProjectWikiEditor project_id="project-1" />);
        await screen.findByText('Inicial');

        apiFetchMock.mockResolvedValueOnce({ url: '/static/projects/wiki/plan.png' } as never);
        fireEvent.click(screen.getByRole('button', { name: 'Insertar imagen' }));
        const file = new File(['píxeles'], 'plan.png', { type: 'image/png' });
        fireEvent.change(screen.getByLabelText('Cargar imagen desde archivo'), { target: { files: [file] } });

        await waitFor(() => expect(harness.images).toHaveLength(1));
        expect(apiFetchMock).toHaveBeenCalledWith('/projects/project-1/wiki/images', { method: 'POST', token: 'test-token', body: expect.any(FormData) });
        expect(harness.images[0]).toEqual({ src: '/api/static/projects/wiki/plan.png', alt: 'plan.png' });
        expect(screen.queryByTestId('wiki-image-panel')).toBeNull();
    });

    it('guarda manualmente el borrador e impide un POST automático duplicado', async () => {
        const post = deferred<{ content: string }>();
        apiFetchMock.mockResolvedValueOnce({ content: '<p>Inicial</p>' } as never);
        apiFetchMock.mockReturnValueOnce(post.promise as never);
        render(<ProjectWikiEditor project_id="project-1" />);
        await screen.findByText('Inicial');

        const editor = screen.getByTestId('wiki-content');
        fireEvent.input(editor, { target: { innerHTML: '<p>Borrador manual</p>' } });
        fireEvent.click(screen.getByRole('button', { name: 'Guardar cambios de la wiki' }));

        await waitFor(() => expect(apiFetchMock).toHaveBeenCalledTimes(2));
        expect(apiFetchMock).toHaveBeenLastCalledWith('/projects/project-1/wiki', {
            method: 'POST', token: 'test-token', body: { content: '<p>Borrador manual</p>' },
        });
        expect(toast.success).not.toHaveBeenCalled();

        await act(async () => { post.resolve({ content: '<p>Borrador manual</p>' }); });
        await waitFor(() => expect(toast.success).toHaveBeenCalledWith('Wiki guardada con éxito'));
        await new Promise((resolve) => setTimeout(resolve, 2100));
        expect(apiFetchMock).toHaveBeenCalledTimes(2);
    });

    it('mantiene el autoguardado a los dos segundos', async () => {
        render(<ProjectWikiEditor project_id="project-1" />);
        await screen.findByText('Inicial');

        fireEvent.input(screen.getByTestId('wiki-content'), { target: { innerHTML: '<p>Auto</p>' } });
        await waitFor(() => expect(apiFetchMock).toHaveBeenCalledTimes(2), { timeout: 3000 });
        expect(apiFetchMock).toHaveBeenLastCalledWith('/projects/project-1/wiki', {
            method: 'POST', token: 'test-token', body: { content: '<p>Auto</p>' },
        });
    });

    it('diagnostica los tres artefactos PMI desde el contenido actual de la wiki', async () => {
        apiFetchMock.mockResolvedValueOnce({
            content: '<h2>Lecciones Aprendidas</h2><p>Causa raíz documentada.</p><p>Decisiones y supuestos registrados.</p>',
        } as never);

        render(<ProjectWikiEditor project_id="project-1" />);

        const banner = await screen.findByTestId('wiki-pmi-knowledge-banner');
        await waitFor(() => expect(banner).toHaveTextContent('2/3'));
        expect(banner).toHaveTextContent('Lecciones Aprendidas');
        expect(banner).toHaveTextContent('Bitácora de Decisiones y Supuestos');
        expect(banner).toHaveTextContent('Revisión de Fase / Retrospectiva');
    });

    it('inserta las tres plantillas estructuradas y sincroniza el HTML para autoguardado', async () => {
        render(<ProjectWikiEditor project_id="project-1" />);
        await screen.findByText('Inicial');

        const openTemplates = () => fireEvent.click(screen.getByTestId('wiki-pmi-templates-toggle'));
        openTemplates();
        expect(screen.getByTestId('wiki-pmi-templates-panel')).toBeInTheDocument();
        fireEvent.click(screen.getByTestId('wiki-pmi-tpl-lessons'));
        expect(harness.html).toContain('<h2>Lecciones Aprendidas</h2><ul>');
        await waitFor(() => expect(screen.getByTestId('wiki-pmi-knowledge-banner')).toHaveTextContent('1/3'));

        openTemplates();
        fireEvent.click(screen.getByTestId('wiki-pmi-tpl-decisions'));
        expect(harness.html).toContain('<h2>Bitácora de Decisiones y Supuestos</h2><ul>');
        await waitFor(() => expect(screen.getByTestId('wiki-pmi-knowledge-banner')).toHaveTextContent('2/3'));

        openTemplates();
        fireEvent.click(screen.getByTestId('wiki-pmi-tpl-retro'));
        expect(harness.html).toContain('<h2>Revisión de Fase / Retrospectiva</h2><ul>');
        expect(harness.html.match(/<li><p>/g)).toHaveLength(15);
        await waitFor(() => expect(screen.getByTestId('wiki-pmi-knowledge-banner')).toHaveTextContent('3/3'));

        await waitFor(() => expect(apiFetchMock).toHaveBeenCalledWith('/projects/project-1/wiki', {
            method: 'POST', token: 'test-token', body: { content: harness.html },
        }), { timeout: 3000 });
    });
});
