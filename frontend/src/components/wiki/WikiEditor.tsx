"use client";

import React, { useEffect, useRef, useState, useMemo } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Placeholder from '@tiptap/extension-placeholder';
import TaskList from '@tiptap/extension-task-list';
import TaskItem from '@tiptap/extension-task-item';
import { motion, AnimatePresence } from 'framer-motion';
import { Cloud, CloudOff, Loader2, Sparkles, BookOpen } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { WikiLinkExtension } from './WikiLinkExtension';

interface WikiEditorProps {
    initialContent: string;
    onSave: (content: string) => Promise<void>;
    onContentChange?: () => void;
    placeholder?: string;
}

export default function WikiEditor({
    initialContent,
    onSave,
    onContentChange,
    placeholder = "Escribe algo increíble... (Usa [[ para vincular documentos wiki)"
}: WikiEditorProps) {
    const { token } = useAuth();
    const [status, setStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
    const [lastSaved, setLastSaved] = useState<Date | null>(null);
    const lastSavedContentRef = useRef(initialContent);

    const extensions = useMemo(() => [
        StarterKit,
        Placeholder.configure({ placeholder }),
        TaskList,
        TaskItem.configure({ nested: true }),
        WikiLinkExtension.configure({
            token: token || null,
        } as any),
    ], [placeholder, token]);

    const editor = useEditor({
        extensions,
        content: initialContent,
        editorProps: {
            attributes: {
                class: 'prose prose-slate dark:prose-invert max-w-none focus:outline-none min-h-48 text-sm leading-relaxed',
            },
        },
        onUpdate: () => {
            onContentChange?.();
        },
    });

    // Sync content when initialContent changes (navigating between docs)
    useEffect(() => {
        if (editor && initialContent) {
            const currentHtml = editor.getHTML();
            if (currentHtml !== initialContent) {
                editor.commands.setContent(initialContent);
                lastSavedContentRef.current = initialContent;
            }
        }
    }, [editor, initialContent]);

    // Autosave cada 2 segundos — compara con lastSavedContentRef, no con initialContent
    useEffect(() => {
        if (!editor) return;

        const interval = setInterval(async () => {
            const currentHtml = editor.getHTML();
            if (currentHtml !== lastSavedContentRef.current && status !== 'saving') {
                setStatus('saving');
                try {
                    await onSave(currentHtml);
                    lastSavedContentRef.current = currentHtml;
                    setStatus('saved');
                    setLastSaved(new Date());
                    setTimeout(() => setStatus('idle'), 2000);
                } catch (error) {
                    setStatus('error');
                }
            }
        }, 2000);

        return () => clearInterval(interval);
    }, [editor, onSave, status]);

    // Ctrl+S / Cmd+S para guardado manual
    useEffect(() => {
        if (!editor) return;

        const handleKeyDown = (e: KeyboardEvent) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 's') {
                e.preventDefault();
                const currentHtml = editor.getHTML();
                if (currentHtml !== lastSavedContentRef.current) {
                    setStatus('saving');
                    onSave(currentHtml)
                        .then(() => {
                            lastSavedContentRef.current = currentHtml;
                            setStatus('saved');
                            setLastSaved(new Date());
                            setTimeout(() => setStatus('idle'), 2000);
                        })
                        .catch(() => setStatus('error'));
                }
            }
        };

        document.addEventListener('keydown', handleKeyDown);
        return () => document.removeEventListener('keydown', handleKeyDown);
    }, [editor, onSave]);

    return (
        <div className="relative w-full max-w-4xl mx-auto py-1.5 px-3">
            {/* Quick Wiki Link hint badge */}
            <div className="mb-4 flex items-center justify-between p-2 rounded-lg bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))]/70 dark:border-white/5 text-[11px] text-[hsl(var(--text-secondary))]">
                <div className="flex items-center gap-1.5">
                    <Sparkles size={13} className="text-[hsl(var(--primary))]" />
                    <span>Consejo de Conocimiento: Escribe <code className="bg-[hsl(var(--surface-2))] dark:bg-white/10 px-1 py-0.5 rounded font-mono font-bold text-[hsl(var(--primary))]">[[</code> para buscar o enlazar otros documentos de la base ministerial.</span>
                </div>
                <div className="flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider text-[hsl(var(--primary))]">
                    <BookOpen size={11} /> Red Obsidian
                </div>
            </div>

            {/* Status Indicator (Floating) */}
            <div className="fixed bottom-8 left-1/2 -translate-x-1/2 z-50">
                <AnimatePresence>
                    {status !== 'idle' && (
                        <motion.div
                            initial={{ y: 20, opacity: 0 }}
                            animate={{ y: 0, opacity: 1 }}
                            exit={{ y: 20, opacity: 0 }}
                            className="bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] dark:border-white/10 px-4 py-2 rounded-full shadow-2xl flex items-center gap-3"
                        >
                            {status === 'saving' && (
                                <>
                                    <Loader2 size={14} className="animate-spin text-[hsl(var(--primary))]" />
                                    <span className="text-xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Guardando...</span>
                                </>
                            )}
                            {status === 'saved' && (
                                <>
                                    <Cloud size={14} className="text-[hsl(var(--success))]" />
                                    <span className="text-xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Guardado</span>
                                </>
                            )}
                            {status === 'error' && (
                                <>
                                    <CloudOff size={14} className="text-[hsl(var(--danger))]" />
                                    <span className="text-xs font-bold uppercase tracking-wide text-[hsl(var(--danger))]">Error al guardar</span>
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
                    <div className="size-2 rounded-full bg-[hsl(var(--success))]" />
                    <span className="text-2xs font-semibold uppercase tracking-wide">Editor Activo (Bidireccional)</span>
                </div>
                {lastSaved && (
                    <span className="text-2xs font-bold uppercase tracking-wide">
                        Última edición: {lastSaved.toLocaleTimeString()}
                    </span>
                )}
            </div>
        </div>
    );
}
