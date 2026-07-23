"use client";

import React, { useCallback, useState } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Placeholder from '@tiptap/extension-placeholder';
import TaskList from '@tiptap/extension-task-list';
import TaskItem from '@tiptap/extension-task-item';
import {
    BookOpen,
    Save,
    Trash2,
    ChevronRight,
    MoreHorizontal,
    Sparkles,
    FileText,
    Zap,
    Link2,
    Clock,
    ShieldCheck,
    Loader2,
    Download,
    Eye,
} from 'lucide-react';
import { useWikiDocument } from '@/hooks/useWikiDocument';

interface WikiProps {
    moduleName: string;
    storageKey?: string;
    onSave?: (content: string) => void;
}

function toWikiKey(moduleName: string) {
    return `wiki_${moduleName.toLowerCase().replace(/\s+/g, '_').replace(/[^\w-]/g, '')}`;
}

export default function UniversalWikiView({ moduleName, storageKey, onSave }: WikiProps) {
    const pageKey = storageKey || toWikiKey(moduleName);
    const {
        content,
        setContent,
        isLoading,
        isSaving,
        lastSaved,
        error,
        saveNow,
    } = useWikiDocument(pageKey, { title: `${moduleName} Wiki` });

    const [viewMode, setViewMode] = useState<'edit' | 'preview'>('edit');
    const editor = useEditor({
        extensions: [
            StarterKit,
            Placeholder.configure({ placeholder: "Comienza a redactar la documentacion oficial para este espacio de trabajo..." }),
            TaskList,
            TaskItem.configure({ nested: true }),
        ],
        content: content || '',
        editorProps: {
            attributes: {
                class: 'prose prose-slate dark:prose-invert max-w-none focus:outline-none min-h-48 text-sm leading-relaxed',
            },
        },
        onUpdate: ({ editor: ed }) => {
            setContent(ed.getHTML());
        },
    });

    const handleSave = useCallback(async () => {
        // Sync editor content before saving
        if (editor) {
            setContent(editor.getHTML());
        }
        try {
            await saveNow();
            onSave?.(content);
        } catch {
            // error handled in hook
        }
    }, [editor, saveNow, onSave, content, setContent]);

    const handleClear = useCallback(() => {
        if (editor) {
            editor.commands.clearContent();
        }
        setContent("");
        saveNow();
    }, [editor, setContent, saveNow]);

    const handleExportHtml = useCallback(() => {
        const html = editor?.getHTML() || content;
        const blob = new Blob([html], { type: 'text/html' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${moduleName.toLowerCase().replace(/\s+/g, '-')}-wiki.html`;
        a.click();
        URL.revokeObjectURL(url);
    }, [editor, content, moduleName]);

    const handleExportText = useCallback(() => {
        const text = editor?.getText() || content.replace(/<[^>]+>/g, '');
        const blob = new Blob([text], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${moduleName.toLowerCase().replace(/\s+/g, '-')}-wiki.txt`;
        a.click();
        URL.revokeObjectURL(url);
    }, [editor, content, moduleName]);

    return (
        <div className="flex min-h-[400px] flex-1 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-1))] rounded-lg border border-[hsl(var(--border))] dark:border-white/5 overflow-hidden shadow-sm">
            <aside className="w-80 border-r border-[hsl(var(--border))] dark:border-white/5 bg-[hsl(var(--surface-1))] dark:bg-white/[0.02] flex flex-col">
                <div className="p-4 border-b border-[hsl(var(--border))] dark:border-white/5 flex items-center gap-4">
                    <div className="size-10 rounded-lg bg-[hsl(var(--primary))] flex items-center justify-center text-white shadow-lg shadow-[hsl(var(--primary)/0.2)]">
                        <BookOpen size={20} />
                    </div>
                    <div>
                        <h4 className="text-xs font-semibold uppercase tracking-wide text-[hsl(var(--text-primary))] dark:text-white">Wiki {moduleName}</h4>
                        <p className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">{moduleName}</p>
                    </div>
                </div>

                <div className="p-4 space-y-2 flex-1 overflow-y-auto">
                    <div className="p-4 bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--info)/0.2)] dark:border-[hsl(var(--info)/0.2)] rounded-lg shadow-sm">
                        <div className="flex items-center gap-3 text-[hsl(var(--primary))] mb-1">
                            <FileText size={16} />
                            <span className="text-[11px] font-semibold uppercase tracking-wide">General</span>
                        </div>
                        <p className="text-[10px] text-[hsl(var(--text-secondary))] font-medium">Protocolos y estandares del modulo {moduleName}.</p>
                    </div>

                    {[{ id: 1, label: "Protocolos" }, { id: 2, label: "Guías" }, { id: 3, label: "Recursos" }].map((item) => (
                        <div
                            key={item.id}
                            role="button"
                            tabIndex={0}
                            aria-label={`Ir a ${item.label}`}
                            className="p-4 flex items-center justify-between group hover:bg-[hsl(var(--surface-3))]/50 dark:hover:bg-white/5 rounded-lg transition-all cursor-pointer"
                            onClick={() => {/* future: navigate to section */}}
                            onKeyDown={(e) => { if (e.key === 'Enter') {/* future */} }}
                        >
                            <div className="flex items-center gap-3">
                                <FileText size={16} className="text-[hsl(var(--text-secondary))] group-hover:text-[hsl(var(--primary))]" />
                                <span className="text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] group-hover:text-[hsl(var(--text-primary))] dark:group-hover:text-white">{item.label}</span>
                            </div>
                            <ChevronRight size={14} className="text-[hsl(var(--text-secondary))] group-hover:text-[hsl(var(--primary))]" />
                        </div>
                    ))}
                </div>

                <div className="p-3 border-t border-[hsl(var(--border))] dark:border-white/5 bg-[hsl(var(--surface-2))]/50 dark:bg-black/20">
                    <button
                        aria-label="Vincular recursos"
                        className="w-full py-1.5 bg-[hsl(var(--bg-muted))] dark:bg-white/5 text-white rounded-lg text-[10px] font-semibold uppercase tracking-wide flex items-center justify-center gap-2 hover:opacity-80 transition-all"
                        onClick={() => {/* future: open resource linker */}}
                    >
                        <Link2 size={14} /> Vincular Recursos
                    </button>
                </div>
            </aside>

            <main className="flex-1 flex flex-col bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-1))]">
                <header className="px-4 py-2 border-b border-[hsl(var(--border))] dark:border-white/5 flex items-center justify-between gap-2 flex-wrap">
                    <div className="flex items-center gap-4">
                        <ShieldCheck size={18} className="text-[hsl(var(--primary))]" />
                        <h2 className="text-xl font-bold italic tracking-tighter text-[hsl(var(--text-primary))] dark:text-white uppercase leading-none">Wiki {moduleName}</h2>
                    </div>
                    <div className="flex items-center gap-3">
                        {lastSaved && (
                            <div className="flex items-center gap-2">
                                <div className="size-1.5 rounded-full bg-[hsl(var(--success))]" />
                                <span className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide italic">Guardado a las {lastSaved.toLocaleTimeString()}</span>
                            </div>
                        )}
                        <button
                            aria-label="Vista previa"
                            title={viewMode === 'edit' ? 'Vista previa' : 'Editar'}
                            onClick={() => setViewMode(m => m === 'edit' ? 'preview' : 'edit')}
                            className="px-3 py-2 bg-[hsl(var(--surface-2))] dark:bg-white/5 text-[hsl(var(--text-secondary))] rounded-lg text-[10px] font-semibold uppercase tracking-wide flex items-center gap-2 hover:opacity-80 transition-all"
                        >
                            <Eye size={14} />
                            {viewMode === 'edit' ? 'Vista previa' : 'Editar'}
                        </button>
                        <button
                            aria-label="Exportar"
                            title="Exportar documento"
                            onClick={handleExportHtml}
                            className="px-3 py-2 bg-[hsl(var(--surface-2))] dark:bg-white/5 text-[hsl(var(--text-secondary))] rounded-lg text-[10px] font-semibold uppercase tracking-wide flex items-center gap-2 hover:opacity-80 transition-all"
                        >
                            <Download size={14} />
                            Exportar
                        </button>
                        <button
                            onClick={handleSave}
                            disabled={isSaving}
                            className="px-4 py-3 bg-[hsl(var(--primary))] text-white rounded-lg text-[10px] font-semibold uppercase tracking-wide flex items-center gap-3 shadow-xl shadow-[hsl(var(--primary)/0.2)] hover:scale-105 active:scale-95 transition-all disabled:opacity-50"
                        >
                            {isSaving ? <Sparkles size={14} className="animate-spin" /> : <Save size={14} />}
                            {isSaving ? 'Sincronizando...' : 'Guardar Wiki'}
                        </button>
                    </div>
                </header>

                <div className="flex-1 p-4 relative overflow-y-auto">
                    <div className="absolute top-10 right-10 opacity-5 pointer-events-none">
                        <Zap size={200} fill="currentColor" className="text-[hsl(var(--primary))]" />
                    </div>
                    {isLoading ? (
                        <div className="flex h-full items-center justify-center gap-2 text-sm font-bold text-[hsl(var(--text-secondary))]">
                            <Loader2 size={16} className="animate-spin" />
                            Cargando wiki compartida...
                        </div>
                    ) : viewMode === 'preview' ? (
                        <div
                            className="prose prose-slate dark:prose-invert max-w-none text-lg"
                            dangerouslySetInnerHTML={{ __html: editor?.getHTML() || content }}
                        />
                    ) : (
                        <EditorContent editor={editor} />
                    )}
                    {error && (
                        <p className="absolute bottom-4 left-10 rounded-full bg-danger-soft px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-danger-text">
                            {error}
                        </p>
                    )}
                </div>

                <footer className="p-3 border-t border-[hsl(var(--border))] dark:border-white/5 bg-[hsl(var(--surface-1))] dark:bg-transparent flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="flex items-center gap-2">
                            <Clock size={14} className="text-[hsl(var(--text-secondary))]" />
                            <span className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Persistencia compartida</span>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        <button aria-label="Eliminar contenido" title="Limpiar contenido" className="p-3 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--danger))] transition-colors" onClick={handleClear}><Trash2 size={18} /></button>
                        <button aria-label="Exportar como texto" title="Exportar como texto plano" className="p-3 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-colors" onClick={handleExportText}><Download size={18} /></button>
                        <button aria-label="Más opciones" title="Más opciones" className="p-3 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-colors" onClick={() => {/* future: options menu */}}><MoreHorizontal size={18} /></button>
                    </div>
                </footer>
            </main>
        </div>
    );
}
