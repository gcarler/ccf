"use client";

import React, { useEffect, useState } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Placeholder from '@tiptap/extension-placeholder';
import TaskList from '@tiptap/extension-task-list';
import TaskItem from '@tiptap/extension-task-item';
import { motion, AnimatePresence } from 'framer-motion';
import { Cloud, CloudOff, Loader2 } from 'lucide-react';

interface WikiEditorProps {
    initialContent: string;
    onSave: (content: string) => Promise<void>;
    placeholder?: string;
}

export default function WikiEditor({ 
    initialContent, 
    onSave, 
    placeholder = "Escribe algo increíble..." 
}: WikiEditorProps) {
    const [status, setStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
    const [lastSaved, setLastSaved] = useState<Date | null>(null);

    const editor = useEditor({
        extensions: [
            StarterKit,
            Placeholder.configure({ placeholder }),
            TaskList,
            TaskItem.configure({ nested: true }),
        ],
        content: initialContent,
        editorProps: {
            attributes: {
                class: 'prose prose-slate dark:prose-invert max-w-none focus:outline-none min-h-48 text-sm leading-relaxed',
            },
        },
    });

    // REGLA CRÍTICA: Autosave cada 2 segundos
    useEffect(() => {
        if (!editor) return;

        const interval = setInterval(async () => {
            if (editor.getHTML() !== initialContent && status !== 'saving') {
                setStatus('saving');
                try {
                    await onSave(editor.getHTML());
                    setStatus('saved');
                    setLastSaved(new Date());
                    setTimeout(() => setStatus('idle'), 2000);
                } catch (error) {
                    setStatus('error');
                }
            }
        }, 2000);

        return () => clearInterval(interval);
    }, [editor, onSave, initialContent, status]);

    return (
        <div className="relative w-full max-w-4xl mx-auto py-1.5 px-3">
            {/* Status Indicator (Floating) */}
            <div className="fixed bottom-8 left-1/2 -translate-x-1/2 z-50">
                <AnimatePresence>
                    {status !== 'idle' && (
                        <motion.div
                            initial={{ y: 20, opacity: 0 }}
                            animate={{ y: 0, opacity: 1 }}
                            exit={{ y: 20, opacity: 0 }}
                            className="bg-[hsl(var(--bg-primary))] dark:bg-[#1E1F21] border border-[hsl(var(--border))] dark:border-white/10 px-4 py-2 rounded-full shadow-2xl flex items-center gap-3"
                        >
                            {status === 'saving' && (
                                <>
                                    <Loader2 size={14} className="animate-spin text-[hsl(var(--primary))]" />
                                    <span className="text-[11px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Guardando...</span>
                                </>
                            )}
                            {status === 'saved' && (
                                <>
                                    <Cloud size={14} className="text-emerald-500" />
                                    <span className="text-[11px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Guardado</span>
                                </>
                            )}
                            {status === 'error' && (
                                <>
                                    <CloudOff size={14} className="text-rose-500" />
                                    <span className="text-[11px] font-bold uppercase tracking-wide text-rose-500">Error al guardar</span>
                                </>
                            )}
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>

            {/* Editor Area */}
            <EditorContent editor={editor} />

            {/* Footer Metadata */}
            <div className="mt-3 pt-8 border-t border-[hsl(var(--border))] dark:border-white/5 flex items-center justify-between text-[hsl(var(--text-secondary))]">
                <div className="flex items-center gap-2">
                    <div className="size-2 rounded-full bg-emerald-500" />
                    <span className="text-[10px] font-semibold uppercase tracking-wide">Editor Activo</span>
                </div>
                {lastSaved && (
                    <span className="text-[10px] font-bold uppercase tracking-wide">
                        Última edición: {lastSaved.toLocaleTimeString()}
                    </span>
                )}
            </div>
        </div>
    );
}
