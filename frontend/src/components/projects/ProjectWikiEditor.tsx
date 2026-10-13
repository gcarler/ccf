"use client";

import { useEffect, useState, useCallback, useRef } from 'react';
import clsx from 'clsx';
import { useEditor, EditorContent, ReactRenderer } from '@tiptap/react';
import { Extension, type Editor, type Range } from '@tiptap/core';
import StarterKit from '@tiptap/starter-kit';
import Placeholder from '@tiptap/extension-placeholder';
import TaskList from '@tiptap/extension-task-list';
import TaskItem from '@tiptap/extension-task-item';
import Suggestion, { type SuggestionProps, type SuggestionKeyDownProps } from '@tiptap/suggestion';
import tippy, { type Instance as TippyInstance } from 'tippy.js';
import {
    Bold, Italic, Heading1, Heading2,
    List, ListOrdered, CheckSquare, Quote, Undo, Redo,
    Cloud, Loader2, Minus, Save
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { CommandsList } from './wiki/CommandsList';
import { toast } from "sonner";
import { DSButton } from '@/design';

interface Props {
    project_id: string;
    initialContent?: string;
}

export default function ProjectWikiEditor({ project_id, initialContent = '' }: Props) {
    const { token, loading: authLoading } = useAuth();
    const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
    const [content, setContent] = useState(initialContent);
    const [loadError, setLoadError] = useState<string | null>(null);
    const contentRef = useRef(initialContent);
    const lastSavedContentRef = useRef(initialContent);
    const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const saveStatusTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const saveQueueRef = useRef<Promise<void>>(Promise.resolve());
    const pendingSavesRef = useRef(new Map<string, Promise<void>>());

    const saveContent = useCallback((newContent: string, manual = false) => {
        const enqueueSave = () => {
            const operation = saveQueueRef.current.catch(() => undefined).then(async () => {
                if (!manual && newContent === lastSavedContentRef.current) return;
                if (!token) {
                    setSaveStatus('error');
                    setLoadError('Debes iniciar sesión para guardar la wiki.');
                    return;
                }
                setSaveStatus('saving');
                try {
                    await apiFetch(`/projects/${project_id}/wiki`, {
                        method: 'POST', token, body: { content: newContent }
                    });
                    lastSavedContentRef.current = newContent;
                    setLoadError(null);
                    setSaveStatus('saved');
                    if (manual) toast.success('Wiki guardada con éxito');
                    if (saveStatusTimerRef.current) clearTimeout(saveStatusTimerRef.current);
                    saveStatusTimerRef.current = setTimeout(() => setSaveStatus('idle'), 3000);
                } catch {
                    setSaveStatus('error');
                    setLoadError('No se pudo guardar la wiki del proyecto.');
                }
            });
            saveQueueRef.current = operation;
            pendingSavesRef.current.set(newContent, operation);
            void operation.then(() => {
                if (pendingSavesRef.current.get(newContent) === operation) pendingSavesRef.current.delete(newContent);
            });
            return operation;
        };

        const pendingSave = pendingSavesRef.current.get(newContent);
        if (pendingSave) {
            if (!manual) return pendingSave;
            return pendingSave.then(() => {
                if (lastSavedContentRef.current === newContent) {
                    toast.success('Wiki guardada con éxito');
                    return;
                }
                return enqueueSave();
            });
        }
        return enqueueSave();
    }, [project_id, token]);

    useEffect(() => {
        if (content === lastSavedContentRef.current) return;
        saveTimerRef.current = setTimeout(() => {
            saveTimerRef.current = null;
            void saveContent(content);
        }, 2000);
        return () => {
            if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
            saveTimerRef.current = null;
        };
    }, [content, saveContent]);

    useEffect(() => () => {
        if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
        if (saveStatusTimerRef.current) clearTimeout(saveStatusTimerRef.current);
    }, []);

    const editor = useEditor({
        extensions: [
            StarterKit,
            TaskList,
            TaskItem.configure({ nested: true }),
            Placeholder.configure({
                placeholder: 'Escribe aquí... (Presiona / para insertar comandos)',
            }),
            Extension.create({
                name: 'slashCommands',
                addOptions() {
                    return {
                        suggestion: {
                            char: '/',
                            command: ({ editor, range, props }: { editor: Editor; range: Range; props: { command: (opts: { editor: Editor; range: Range }) => void } }) => {
                                props.command({ editor, range });
                            },
                        },
                    };
                },
                addProseMirrorPlugins() {
                    return [
                        Suggestion({
                            editor: this.editor,
                            char: '/',
                            command: ({ editor, range, props }: { editor: Editor; range: Range; props: { command: (opts: { editor: Editor; range: Range }) => void } }) => {
                                props.command({ editor, range });
                            },
                            items: ({ query }: { query: string }) => {
                                return [
                                    { title: 'Encabezado 1', description: 'Título grande', icon: Heading1, command: ({ editor, range }: { editor: Editor; range: Range }) => editor.chain().focus().deleteRange(range).setNode('heading', { level: 1 }).run() },
                                    { title: 'Encabezado 2', description: 'Subtítulo mediano', icon: Heading2, command: ({ editor, range }: { editor: Editor; range: Range }) => editor.chain().focus().deleteRange(range).setNode('heading', { level: 2 }).run() },
                                    { title: 'Lista de Tareas', description: 'Checklist interactivo', icon: CheckSquare, command: ({ editor, range }: { editor: Editor; range: Range }) => editor.chain().focus().deleteRange(range).toggleTaskList().run() },
                                    { title: 'Lista con Viñetas', description: 'Lista simple', icon: List, command: ({ editor, range }: { editor: Editor; range: Range }) => editor.chain().focus().deleteRange(range).toggleBulletList().run() },
                                    { title: 'Cita', description: 'Resaltar texto ministerial', icon: Quote, command: ({ editor, range }: { editor: Editor; range: Range }) => editor.chain().focus().deleteRange(range).toggleBlockquote().run() },
                                    { title: 'Divisor', description: 'Separador horizontal', icon: Minus, command: ({ editor, range }: { editor: Editor; range: Range }) => editor.chain().focus().deleteRange(range).setHorizontalRule().run() },
                                ].filter(item => item.title.toLowerCase().startsWith(query.toLowerCase()));
                            },
                            render: () => {
                                let component: ReactRenderer;
                                let popup: TippyInstance[];

                                return {
                                    onStart: (props: SuggestionProps) => {
                                        component = new ReactRenderer(CommandsList, {
                                            props,
                                            editor: props.editor,
                                        });

                                        if (!props.clientRect) return;

                                        popup = tippy('body', {
                                            getReferenceClientRect: props.clientRect as () => DOMRect,
                                            appendTo: () => document.body,
                                            content: component.element,
                                            showOnCreate: true,
                                            interactive: true,
                                            trigger: 'manual',
                                            placement: 'bottom-start',
                                        });
                                    },
                                    onUpdate(props: SuggestionProps) {
                                        component.updateProps(props);
                                        if (!props.clientRect) return;
                                        popup[0].setProps({
                                            getReferenceClientRect: props.clientRect as () => DOMRect,
                                        });
                                    },
                                    onKeyDown(props: SuggestionKeyDownProps) {
                                        if (props.event.key === 'Escape') {
                                            popup[0].hide();
                                            return true;
                                        }
                                        return (component.ref as { onKeyDown?: (props: SuggestionKeyDownProps) => boolean } | undefined)?.onKeyDown?.(props) ?? false;
                                    },
                                    onExit() {
                                        popup[0].destroy();
                                        component.destroy();
                                    },
                                };
                            },
                        }),
                    ];
                },
            }),
        ],
        content: initialContent,
        immediatelyRender: false,
        editorProps: { attributes: { class: 'prose max-w-none focus:outline-none min-h-48' } },
        onUpdate: ({ editor }) => {
            const nextContent = editor.getHTML();
            contentRef.current = nextContent;
            setContent(nextContent);
        }
    });

    useEffect(() => {
        const load = async () => {
            if (authLoading) return;
            if (!token) {
                setLoadError('Debes iniciar sesión para abrir la wiki del proyecto.');
                return;
            }
            try {
                setLoadError(null);
                const data = await apiFetch<{content: string}>(`/projects/${project_id}/wiki`, { token });
                if (data && typeof data.content === 'string' && contentRef.current === initialContent) {
                    lastSavedContentRef.current = data.content;
                    contentRef.current = data.content;
                    setContent(data.content);
                    editor?.commands.setContent(data.content);
                }
            } catch (err) {
                setLoadError('No se pudo cargar la wiki del proyecto.');
                toast.error("Error inesperado");
            }
        };
        load();
    }, [authLoading, editor, initialContent, project_id, token]);

    if (!editor) return null;

    return (
        <div className="flex flex-col h-full bg-[hsl(var(--surface-1))] rounded-lg border border-[hsl(var(--border))] shadow-xl overflow-hidden font-display relative">
            <div className="flex flex-wrap items-center gap-1 p-2 border-b border-[hsl(var(--border))] bg-[hsl(var(--surface-1))]">
                <MenuButton label="Negrita" onClick={() => editor.chain().focus().toggleBold().run()} isActive={editor.isActive('bold')} icon={Bold} />
                <MenuButton label="Cursiva" onClick={() => editor.chain().focus().toggleItalic().run()} isActive={editor.isActive('italic')} icon={Italic} />
                <MenuButton label="Encabezado 1" onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()} isActive={editor.isActive('heading', { level: 1 })} icon={Heading1} />
                <MenuButton label="Encabezado 2" onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()} isActive={editor.isActive('heading', { level: 2 })} icon={Heading2} />
                <div className="w-[1px] h-5 bg-[hsl(var(--border))] mx-1" />
                <MenuButton label="Lista con viñetas" onClick={() => editor.chain().focus().toggleBulletList().run()} isActive={editor.isActive('bulletList')} icon={List} />
                <MenuButton label="Lista numerada" onClick={() => editor.chain().focus().toggleOrderedList().run()} isActive={editor.isActive('orderedList')} icon={ListOrdered} />
                <MenuButton label="Lista de tareas" onClick={() => editor.chain().focus().toggleTaskList().run()} isActive={editor.isActive('taskList')} icon={CheckSquare} />
                <MenuButton label="Cita" onClick={() => editor.chain().focus().toggleBlockquote().run()} isActive={editor.isActive('blockquote')} icon={Quote} />
                <MenuButton label="Separador horizontal" onClick={() => editor.chain().focus().setHorizontalRule().run()} isActive={editor.isActive('horizontalRule')} icon={Minus} />
                <div className="ml-auto flex items-center gap-3 px-2">
                    <div className="flex items-center gap-1.5">
                        {saveStatus === 'saving' && <><Loader2 size={12} className="animate-spin text-[hsl(var(--primary))]" /> <span className="text-2xs font-bold uppercase text-[hsl(var(--primary))]">Guardando</span></>}
                        {saveStatus === 'saved' && <><Cloud size={12} className="text-[hsl(var(--success))]" /> <span className="text-2xs font-bold uppercase text-[hsl(var(--success))]">Sincronizado</span></>}
                    </div>
                    <DSButton
                        type="button"
                        onClick={() => {
                            if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
                            saveTimerRef.current = null;
                            void saveContent(contentRef.current, true);
                        }}
                        className="inline-flex items-center gap-1.5"
                        aria-label="Guardar cambios de la wiki"
                    >
                        <Save size={14} aria-hidden="true" />
                        Guardar cambios
                    </DSButton>
                    <div className="flex items-center gap-0.5 border-l border-[hsl(var(--border))] pl-2">
                        <MenuButton label="Deshacer" onClick={() => editor.chain().focus().undo().run()} disabled={!editor.can().undo()} icon={Undo} />
                        <MenuButton label="Rehacer" onClick={() => editor.chain().focus().redo().run()} disabled={!editor.can().redo()} icon={Redo} />
                    </div>
                </div>
            </div>
            {loadError && (
                <div className="mx-4 mt-3 rounded-md border border-[hsl(var(--warning)/0.3)] bg-[hsl(var(--warning)/0.1)] p-3 text-[hsl(var(--warning))]">
                    <p className="text-xs font-bold uppercase tracking-wide">{loadError}</p>
                </div>
            )}
            <div className="flex-1 overflow-y-auto scrollbar-thin p-4 bg-transparent">
                <div className="max-w-4xl mx-auto"><EditorContent editor={editor} /></div>
            </div>
            <style jsx global>{`
                .is-editor-empty:first-child::before { color: hsl(var(--muted-foreground)); content: attr(data-placeholder); float: left; height: 0; pointer-events: none; }
                ul[data-type="taskList"] { list-style: none; padding: 0; }
                ul[data-type="taskList"] li { display: flex; align-items: flex-start; gap: 0.75rem; margin-bottom: 0.5rem; }
                ul[data-type="taskList"] input[type="checkbox"] { width: 1.25rem; height: 1.25rem; margin-top: 0.2rem; cursor: pointer; border-radius: 0.5rem; border: 2px solid hsl(var(--border)); }
            `}</style>
        </div>
    );
}

function MenuButton({ onClick, isActive, disabled, icon: Icon, label }: { onClick: () => void; isActive?: boolean; disabled?: boolean; icon: LucideIcon; label: string }) {
    return (
        <DSButton
            type="button"
            onClick={onClick}
            disabled={disabled}
            aria-label={label}
            aria-pressed={Boolean(isActive)}
            variant="ghost"
            className={clsx(
                'p-2 rounded-md transition-all focus-visible:ring-2 focus-visible:ring-offset-2',
                isActive
                    ? 'bg-[hsl(var(--surface-2))] text-[hsl(var(--primary))] shadow-sm ring-1 ring-[hsl(var(--border))]'
                    : 'text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] hover:text-[hsl(var(--text-primary))]',
                disabled && 'opacity-20'
            )}
        >
            <Icon size={16} aria-hidden="true" />
        </DSButton>
    );
}
