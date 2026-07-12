"use client";

import React, { useEffect, useState, useCallback } from 'react';
import { useEditor, EditorContent, ReactRenderer } from '@tiptap/react';
import { Extension } from '@tiptap/core';
import StarterKit from '@tiptap/starter-kit';
import Placeholder from '@tiptap/extension-placeholder';
import TaskList from '@tiptap/extension-task-list';
import TaskItem from '@tiptap/extension-task-item';
import Suggestion from '@tiptap/suggestion';
import tippy from 'tippy.js';
import { 
    Bold, Italic, Heading1, Heading2, 
    List, CheckSquare, Quote, Undo, Redo,
    Cloud, Loader2, Minus
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { CommandsList } from './wiki/CommandsList';
import { toast } from "sonner";

interface Props {
    project_id: string;
    initialContent?: string;
}

export default function ProjectWikiEditor({ project_id, initialContent = '' }: Props) {
    const { token } = useAuth();
    const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
    const [content, setContent] = useState(initialContent);

    const saveContent = useCallback(async (newContent: string) => {
        if (!token) return;
        setSaveStatus('saving');
        try {
            await apiFetch(`/projects/${project_id}/wiki`, {
                method: 'POST',
                token,
                body: { content: newContent }
            });
            setSaveStatus('saved');
            setTimeout(() => setSaveStatus('idle'), 3000);
        } catch (err) {
            setSaveStatus('error');
        }
    }, [project_id, token]);

    useEffect(() => {
        if (content === initialContent) return;
        const timer = setTimeout(() => saveContent(content), 2000);
        return () => clearTimeout(timer);
    }, [content, saveContent, initialContent]);

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
                            command: ({ editor, range, props }: any) => {
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
                            command: ({ editor, range, props }: any) => {
                                props.command({ editor, range });
                            },
                            items: ({ query }: any) => {
                                return [
                                    { title: 'Encabezado 1', description: 'Título grande', icon: Heading1, command: ({ editor, range }: any) => editor.chain().focus().deleteRange(range).setNode('heading', { level: 1 }).run() },
                                    { title: 'Encabezado 2', description: 'Subtítulo mediano', icon: Heading2, command: ({ editor, range }: any) => editor.chain().focus().deleteRange(range).setNode('heading', { level: 2 }).run() },
                                    { title: 'Lista de Tareas', description: 'Checklist interactivo', icon: CheckSquare, command: ({ editor, range }: any) => editor.chain().focus().deleteRange(range).toggleTaskList().run() },
                                    { title: 'Lista con Viñetas', description: 'Lista simple', icon: List, command: ({ editor, range }: any) => editor.chain().focus().deleteRange(range).toggleBulletList().run() },
                                    { title: 'Cita', description: 'Resaltar texto ministerial', icon: Quote, command: ({ editor, range }: any) => editor.chain().focus().deleteRange(range).toggleBlockquote().run() },
                                    { title: 'Divisor', description: 'Separador horizontal', icon: Minus, command: ({ editor, range }: any) => editor.chain().focus().deleteRange(range).setHorizontalRule().run() },
                                ].filter(item => item.title.toLowerCase().startsWith(query.toLowerCase()));
                            },
                            render: () => {
                                let component: any;
                                let popup: any;

                                return {
                                    onStart: (props: any) => {
                                        component = new ReactRenderer(CommandsList, {
                                            props,
                                            editor: props.editor,
                                        });

                                        if (!props.clientRect) return;

                                        popup = tippy('body', {
                                            getReferenceClientRect: props.clientRect,
                                            appendTo: () => document.body,
                                            content: component.element,
                                            showOnCreate: true,
                                            interactive: true,
                                            trigger: 'manual',
                                            placement: 'bottom-start',
                                        });
                                    },
                                    onUpdate(props: any) {
                                        component.updateProps(props);
                                        if (!props.clientRect) return;
                                        popup[0].setProps({
                                            getReferenceClientRect: props.clientRect,
                                        });
                                    },
                                    onKeyDown(props: any) {
                                        if (props.event.key === 'Escape') {
                                            popup[0].hide();
                                            return true;
                                        }
                                        return component.ref?.onKeyDown(props);
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
        editorProps: { attributes: { class: 'prose dark:prose-invert max-w-none focus:outline-none min-h-48' } },
        onUpdate: ({ editor }) => setContent(editor.getHTML())
    });

    useEffect(() => {
        const load = async () => {
            if (!token) return;
            try {
                const data = await apiFetch<{content: string}>(`/projects/${project_id}/wiki`, { token });
                if (data && data.content) editor?.commands.setContent(data.content);
            } catch (err) { toast.error("Error inesperado"); }
        };
        load();
    }, [project_id, token, editor]);

    if (!editor) return null;

    return (
        <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-secondary))] rounded-lg border border-[hsl(var(--border))] dark:border-white/10 shadow-xl overflow-hidden font-display relative">
            <div className="flex flex-wrap items-center gap-1 p-2 border-b border-[hsl(var(--border))] dark:border-white/5 bg-[hsl(var(--surface-1))] dark:bg-black/20">
                <MenuButton onClick={() => editor.chain().focus().toggleBold().run()} isActive={editor.isActive('bold')} icon={Bold} />
                <MenuButton onClick={() => editor.chain().focus().toggleItalic().run()} isActive={editor.isActive('italic')} icon={Italic} />
                <div className="w-[1px] h-5 bg-[hsl(var(--surface-3))] dark:bg-white/10 mx-1" />
                <MenuButton onClick={() => editor.chain().focus().toggleTaskList().run()} isActive={editor.isActive('taskList')} icon={CheckSquare} />
                <div className="ml-auto flex items-center gap-3 px-2">
                    <div className="flex items-center gap-1.5">
                        {saveStatus === 'saving' && <><Loader2 size={12} className="animate-spin text-[hsl(var(--primary))]" /> <span className="text-[10px] font-bold uppercase text-[hsl(var(--primary))]">Guardando</span></>}
                        {saveStatus === 'saved' && <><Cloud size={12} className="text-emerald-500" /> <span className="text-[10px] font-bold uppercase text-emerald-500">Sincronizado</span></>}
                    </div>
                    <div className="flex items-center gap-0.5 border-l border-[hsl(var(--border))] dark:border-white/10 pl-2">
                        <MenuButton onClick={() => editor.chain().focus().undo().run()} disabled={!editor.can().undo()} icon={Undo} />
                        <MenuButton onClick={() => editor.chain().focus().redo().run()} disabled={!editor.can().redo()} icon={Redo} />
                    </div>
                </div>
            </div>
            <div className="flex-1 overflow-y-auto scrollbar-thin p-4 bg-[hsl(var(--bg-primary))] dark:bg-transparent">
                <div className="max-w-4xl mx-auto"><EditorContent editor={editor} /></div>
            </div>
            <style jsx global>{`
                .is-editor-empty:first-child::before { color: #94a3b8; content: attr(data-placeholder); float: left; height: 0; pointer-events: none; }
                ul[data-type="taskList"] { list-style: none; padding: 0; }
                ul[data-type="taskList"] li { display: flex; align-items: flex-start; gap: 0.75rem; margin-bottom: 0.5rem; }
                ul[data-type="taskList"] input[type="checkbox"] { width: 1.25rem; height: 1.25rem; margin-top: 0.2rem; cursor: pointer; border-radius: 0.5rem; border: 2px solid #e2e8f0; }
            `}</style>
        </div>
    );
}

function MenuButton({ onClick, isActive, disabled, icon: Icon }: any) {
    return (
        <button onClick={onClick} disabled={disabled} className={`p-2 rounded-md transition-all ${isActive ? 'bg-[hsl(var(--bg-primary))] dark:bg-white/10 text-[hsl(var(--primary))] shadow-sm ring-1 ring-[hsl(var(--border))] dark:ring-white/10' : 'text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--bg-primary))] dark:hover:bg-white/5 hover:text-[hsl(var(--text-primary))] dark:hover:text-white'} ${disabled ? 'opacity-20' : ''}`}><Icon size={16} /></button>
    );
}
