import React from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const harness = vi.hoisted(() => ({
    options: null as { content?: string; onUpdate?: (args: { editor: { getHTML: () => string } }) => void } | null,
    html: '',
    active: new Set<string>(),
    revision: 0,
}));

vi.mock('@tiptap/react', async (importOriginal) => {
    const actual = await importOriginal<typeof import('@tiptap/react')>();
    const toggle = (name: string, key = name) => {
        if (harness.active.has(key)) harness.active.delete(key);
        else harness.active.add(key);
    };
    const emitUpdate = () => {
        harness.revision += 1;
        harness.html = `<p>toolbar-${harness.revision}</p>`;
        harness.options?.onUpdate?.({ editor: { getHTML: () => harness.html } });
    };
    const chain = new Proxy({}, {
        get: (_target, property: string) => (...args: unknown[]) => {
            if (property === 'run') return true;
            if (property === 'toggleHeading') toggle('heading', `heading-${(args[0] as { level: number }).level}`);
            if (property === 'toggleBulletList') toggle('bulletList');
            if (property === 'toggleOrderedList') toggle('orderedList');
            if (property === 'toggleBlockquote') toggle('blockquote');
            if (property === 'setHorizontalRule') toggle('horizontalRule');
            if (property === 'toggleBold') toggle('bold');
            if (property === 'toggleItalic') toggle('italic');
            if (property === 'toggleTaskList') toggle('taskList');
            emitUpdate();
            return chain;
        },
    });
    const editor = {
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
            ['Lista con viñetas', 'bulletList'],
            ['Lista numerada', 'orderedList'],
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
});
