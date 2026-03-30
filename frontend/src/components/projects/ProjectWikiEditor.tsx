"use client";

import React, { useEffect, useState, useCallback } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Placeholder from '@tiptap/extension-placeholder';
import TaskList from '@tiptap/extension-task-list';
import TaskItem from '@tiptap/extension-task-item';
import { 
    Bold, Italic, Strikethrough, Heading1, Heading2, 
    List, ListOrdered, CheckSquare, Quote, Undo, Redo,
    CloudCheck, CloudUpload, Loader2
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { toast } from 'sonner';

interface Props {
    project_id: number;
    initialContent?: string;
}

export default function ProjectWikiEditor({ project_id, initialContent = '' }: Props) {
    const { token } = useAuth();
    const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
    const [content, setContent] = useState(initialContent);

    // Fetch initial content from API if not provided via props
    useEffect(() => {
        const load = async () => {
            try {
                const data = await apiFetch<{content: string}>(`/projects/${project_id}/wiki`, { token });
                if (data && data.content) editor?.commands.setContent(data.content);
            } catch (err) { console.error(err); }
        };
        if (token) load();
    }, [project_id, token]);

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
            toast.error("Error al auto-guardar la Wiki");
        }
    }, [project_id, token]);

    // Debounce timer logic
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
                placeholder: 'Escribe aquí el manual, guion o notas del proyecto...',
            }),
        ],
        content: initialContent,
        editorProps: {
            attributes: {
                class: 'prose dark:prose-invert max-w-none focus:outline-none min-h-[500px]',
            },
        },
        onUpdate: ({ editor }) => {
            setContent(editor.getHTML());
        }
    });

    if (!editor) return null;

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] rounded-[3rem] border border-slate-200 dark:border-white/10 shadow-xl overflow-hidden font-display relative">
            {/* Toolbar Pro */}
            <div className="flex flex-wrap items-center gap-1 p-4 border-b border-slate-100 dark:border-white/5 bg-slate-50 dark:bg-black/20">
                <MenuButton onClick={() => editor.chain().focus().toggleBold().run()} isActive={editor.isActive('bold')} icon={Bold} />
                <MenuButton onClick={() => editor.chain().focus().toggleItalic().run()} isActive={editor.isActive('italic')} icon={Italic} />
                <MenuButton onClick={() => editor.chain().focus().toggleStrike().run()} isActive={editor.isActive('strike')} icon={Strikethrough} />
                
                <div className="w-[1px] h-6 bg-slate-200 dark:bg-white/10 mx-2" />
                
                <MenuButton onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()} isActive={editor.isActive('heading', { level: 1 })} icon={Heading1} />
                <MenuButton onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()} isActive={editor.isActive('heading', { level: 2 })} icon={Heading2} />
                
                <div className="w-[1px] h-6 bg-slate-200 dark:bg-white/10 mx-2" />
                
                <MenuButton onClick={() => editor.chain().focus().toggleBulletList().run()} isActive={editor.isActive('bulletList')} icon={List} />
                <MenuButton onClick={() => editor.chain().focus().toggleOrderedList().run()} isActive={editor.isActive('orderedList')} icon={ListOrdered} />
                <MenuButton onClick={() => editor.chain().focus().toggleTaskList().run()} isActive={editor.isActive('taskList')} icon={CheckSquare} />
                
                <div className="ml-auto flex items-center gap-4 px-4">
                    <div className="flex items-center gap-2">
                        {saveStatus === 'saving' && <><Loader2 size={14} className="animate-spin text-blue-500" /> <span className="text-[10px] font-black uppercase text-blue-500">Guardando...</span></>}
                        {saveStatus === 'saved' && <><CloudCheck size={14} className="text-emerald-500" /> <span className="text-[10px] font-black uppercase text-emerald-500">Sincronizado</span></>}
                        {saveStatus === 'error' && <><CloudUpload size={14} className="text-rose-500" /> <span className="text-[10px] font-black uppercase text-rose-500">Error</span></>}
                    </div>
                    <div className="flex items-center gap-1 border-l border-slate-200 dark:border-white/10 pl-4">
                        <MenuButton onClick={() => editor.chain().focus().undo().run()} disabled={!editor.can().undo()} icon={Undo} />
                        <MenuButton onClick={() => editor.chain().focus().redo().run()} disabled={!editor.can().redo()} icon={Redo} />
                    </div>
                </div>
            </div>

            {/* Editor Area */}
            <div className="flex-1 overflow-y-auto scrollbar-thin p-12 bg-white dark:bg-transparent">
                <div className="max-w-4xl mx-auto">
                    <EditorContent editor={editor} />
                </div>
            </div>
            
            <style jsx global>{`
                .is-editor-empty:first-child::before {
                    color: #94a3b8;
                    content: attr(data-placeholder);
                    float: left;
                    height: 0;
                    pointer-events: none;
                }
                ul[data-type="taskList"] { list-style: none; padding: 0; }
                ul[data-type="taskList"] li { display: flex; align-items: flex-start; gap: 0.75rem; margin-bottom: 0.5rem; }
                ul[data-type="taskList"] input[type="checkbox"] { width: 1.25rem; height: 1.25rem; margin-top: 0.2rem; cursor: pointer; border-radius: 0.5rem; border: 2px solid #e2e8f0; transition: all 0.2s; }
                ul[data-type="taskList"] input[type="checkbox"]:checked { background-color: #2563eb; border-color: #2563eb; }
            `}</style>
        </div>
    );
}

function MenuButton({ onClick, isActive, disabled, icon: Icon }: any) {
    return (
        <button
            onClick={onClick}
            disabled={disabled}
            className={`p-2.5 rounded-xl transition-all ${
                isActive 
                    ? 'bg-white dark:bg-white/10 text-blue-600 shadow-sm ring-1 ring-slate-200 dark:ring-white/10' 
                    : 'text-slate-500 hover:bg-white dark:hover:bg-white/5 hover:text-slate-900 dark:hover:text-white'
            } ${disabled ? 'opacity-20 cursor-not-allowed' : ''}`}
        >
            <Icon size={18} />
        </button>
    );
}
