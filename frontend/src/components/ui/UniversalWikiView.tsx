"use client";

import React, { useCallback, useEffect, useState, useRef } from 'react';
import { useEditor, EditorContent, type Editor } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Placeholder from '@tiptap/extension-placeholder';
import Image from '@tiptap/extension-image';
import Underline from '@tiptap/extension-underline';
import TaskList from '@tiptap/extension-task-list';
import TaskItem from '@tiptap/extension-task-item';
import clsx from 'clsx';
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
    Heading1,
    Heading2,
    Heading3,
    Pilcrow,
    Bold,
    Italic,
    Underline as UnderlineIcon,
    Code,
    List,
    ListOrdered,
    CheckSquare,
    Quote,
    Image as ImageIcon,
    X,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { useWikiDocument } from '@/hooks/useWikiDocument';
import { WIKI_PROSE_CLASS, WIKI_PROSE_CSS } from '@/components/wiki/wikiProse';
import { getCmsMediaUrl } from '@/lib/cms/media';
import { toast } from 'sonner';

interface WikiProps {
    moduleName: string;
    storageKey?: string;
    onSave?: (content: string) => void;
}

function toWikiKey(moduleName: string) {
    return `wiki_${moduleName.toLowerCase().replace(/\s+/g, '_').replace(/[^\w-]/g, '')}`;
}

function ToolbarButton({ onClick, isActive, disabled, icon: Icon, label }: {
    onClick: () => void;
    isActive?: boolean;
    disabled?: boolean;
    icon: LucideIcon;
    label: string;
}) {
    return (
        <button
            type="button"
            onClick={onClick}
            disabled={disabled}
            aria-label={label}
            aria-pressed={Boolean(isActive)}
            className={clsx(
                'p-2 rounded-md focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[hsl(var(--primary))] transition-all',
                isActive
                    ? 'bg-[hsl(var(--surface-2))] text-[hsl(var(--primary))] ring-1 ring-[hsl(var(--border))]'
                    : 'text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] hover:text-[hsl(var(--text-primary))]',
                disabled && 'opacity-30 cursor-not-allowed'
            )}
        >
            <Icon size={16} aria-hidden />
        </button>
    );
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
    const [imagePanelOpen, setImagePanelOpen] = useState(false);
    const [imageUrl, setImageUrl] = useState('');
    const imagePanelOpenRef = useRef<() => void>(() => {});
    const openImagePanel = useCallback(() => {
        setImagePanelOpen(true);
    }, []);
    imagePanelOpenRef.current = openImagePanel;

    const editor: Editor | null = useEditor({
        extensions: [
            // Subrayado vía @tiptap/extension-underline extendido; el que trae
            // StarterKit se desactiva para no duplicar la extensión.
            StarterKit.configure({ underline: false }),
            Underline,
            Image.configure({ allowBase64: false }),
            Placeholder.configure({ placeholder: "Comienza a redactar la documentación oficial para este espacio de trabajo..." }),
            TaskList,
            TaskItem.configure({ nested: true }),
        ],
        content: content || '',
        editorProps: {
            attributes: {
                class: `${WIKI_PROSE_CLASS} max-w-none focus:outline-none min-h-48 text-sm leading-relaxed`,
            },
        },
        onUpdate: ({ editor: ed }) => {
            setContent(ed.getHTML());
        },
    });

    useEffect(() => {
        if (editor && content && !editor.isDestroyed && editor.getHTML() !== content) {
            editor.commands.setContent(content, { emitUpdate: false });
        }
    }, [editor, content]);

    const handleSave = useCallback(async () => {
        const freshContent = editor ? editor.getHTML() : content;
        if (editor) {
            setContent(freshContent);
        }
        try {
            await saveNow();
            onSave?.(freshContent);
        } catch {
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

    const insertImageFromUrl = useCallback(() => {
        const raw = imageUrl.trim();
        if (!raw || !editor) return;
        editor.chain().focus().setImage({ src: getCmsMediaUrl(raw), alt: 'imagen de wiki' }).run();
        setImagePanelOpen(false);
        setImageUrl('');
        toast.success('Imagen insertada en la wiki');
    }, [imageUrl, editor]);

    return (
        <div className="flex min-h-[400px] flex-1 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-1))] rounded-lg border border-[hsl(var(--border))] dark:border-[hsl(var(--border))] overflow-hidden shadow-sm">
            <aside className="w-80 border-r border-[hsl(var(--border))] dark:border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] dark:bg-[hsl(var(--surface-1))] flex flex-col">
                <div className="p-4 border-b border-[hsl(var(--border))] dark:border-[hsl(var(--border))] flex items-center gap-4">
                    <div className="size-10 rounded-lg bg-[hsl(var(--primary))] flex items-center justify-center text-white shadow-lg shadow-[hsl(var(--primary)/0.2)]">
                        <BookOpen size={20} />
                    </div>
                    <div>
                        <h4 className="text-xs font-semibold uppercase tracking-wide text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-primary))]">Wiki {moduleName}</h4>
                        <p className="text-2xs font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">{moduleName}</p>
                    </div>
                </div>

                <div className="p-4 space-y-2 flex-1 overflow-y-auto">
                    <div className="p-4 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-2))] border border-[hsl(var(--info)/0.2)] dark:border-[hsl(var(--info)/0.2)] rounded-lg shadow-sm">
                        <div className="flex items-center gap-3 text-[hsl(var(--primary))] mb-1">
                            <FileText size={16} />
                            <span className="text-xs font-semibold uppercase tracking-wide">General</span>
                        </div>
                        <p className="text-2xs text-[hsl(var(--text-secondary))] font-medium">Protocolos y estandares del modulo {moduleName}.</p>
                    </div>

                    {[{ id: 1, label: "Protocolos" }, { id: 2, label: "Guías" }, { id: 3, label: "Recursos" }].map((item) => (
                        <div
                            key={item.id}
                            role="button"
                            tabIndex={0}
                            aria-label={`Ir a ${item.label}`}
                            className="p-4 flex items-center justify-between group hover:bg-[hsl(var(--surface-3))]/50 dark:hover:bg-[hsl(var(--surface-2))] rounded-lg transition-all cursor-pointer"
                            onClick={() => {/* future: navigate to section */}}
                            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); /* future */ } }}
                        >
                            <div className="flex items-center gap-3">
                                <FileText size={16} className="text-[hsl(var(--text-secondary))] group-hover:text-[hsl(var(--primary))]" />
                                <span className="text-xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] group-hover:text-[hsl(var(--text-primary))] dark:group-hover:text-white">{item.label}</span>
                            </div>
                            <ChevronRight size={14} className="text-[hsl(var(--text-secondary))] group-hover:text-[hsl(var(--primary))]" />
                        </div>
                    ))}
                </div>

                <div className="p-3 border-t border-[hsl(var(--border))] dark:border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]/50 dark:bg-[hsl(var(--surface-1))]">
                    <button
                        aria-label="Vincular recursos"
                        className="w-full py-1.5 bg-[hsl(var(--bg-muted))] dark:bg-[hsl(var(--surface-2))] text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-primary))] rounded-lg text-2xs font-semibold uppercase tracking-wide flex items-center justify-center gap-2 hover:opacity-80 transition-all"
                        onClick={() => {/* future: open resource linker */}}
                    >
                        <Link2 size={14} /> Vincular Recursos
                    </button>
                </div>
            </aside>

            <main className="flex-1 flex flex-col bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-1))]">
                <header className="px-4 py-2 border-b border-[hsl(var(--border))] dark:border-[hsl(var(--border))] flex items-center justify-between gap-2 flex-wrap">
                    <div className="flex items-center gap-4">
                        <ShieldCheck size={18} className="text-[hsl(var(--primary))]" />
                        <h2 className="text-xl font-bold italic tracking-tighter text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-primary))] uppercase leading-none">Wiki {moduleName}</h2>
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
                            className="px-3 py-2 bg-[hsl(var(--surface-2))] dark:bg-[hsl(var(--surface-2))] text-[hsl(var(--foreground))] rounded-lg text-2xs font-semibold uppercase tracking-wide flex items-center gap-2 hover:opacity-80 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsl(var(--ring))]"
                        >
                            <Eye size={14} />
                            {viewMode === 'edit' ? 'Vista previa' : 'Editar'}
                        </button>
                        <button
                            aria-label="Exportar"
                            title="Exportar documento"
                            onClick={handleExportHtml}
                            className="px-3 py-2 bg-[hsl(var(--surface-2))] dark:bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] rounded-lg text-2xs font-semibold uppercase tracking-wide flex items-center gap-2 hover:opacity-80 transition-all"
                        >
                            <Download size={14} />
                            Exportar
                        </button>
                        <button
                            onClick={handleSave}
                            disabled={isSaving}
                            className="px-4 py-3 bg-[hsl(var(--primary))] text-white rounded-lg text-2xs font-semibold uppercase tracking-wide flex items-center gap-3 shadow-xl shadow-[hsl(var(--primary)/0.2)] hover:scale-105 active:scale-95 transition-all disabled:opacity-50"
                        >
                            {isSaving ? <Sparkles size={14} className="animate-spin" /> : <Save size={14} />}
                            {isSaving ? 'Sincronizando...' : 'Guardar Wiki'}
                        </button>
                    </div>
                </header>

                {viewMode === 'edit' && (
                    <div
                        data-testid="wiki-format-toolbar"
                        role="toolbar"
                        aria-label="Herramientas de la wiki"
                        className="px-4 py-1.5 border-b border-[hsl(var(--border))] dark:border-[hsl(var(--border))] flex flex-wrap items-center gap-1 bg-[hsl(var(--surface-1))] dark:bg-[hsl(var(--surface-1))]"
                    >
                        <ToolbarButton label="Encabezado 1" onClick={() => editor?.chain().focus().toggleHeading({ level: 1 }).run()} isActive={Boolean(editor?.isActive('heading', { level: 1 }))} icon={Heading1} />
                        <ToolbarButton label="Encabezado 2" onClick={() => editor?.chain().focus().toggleHeading({ level: 2 }).run()} isActive={Boolean(editor?.isActive('heading', { level: 2 }))} icon={Heading2} />
                        <ToolbarButton label="Encabezado 3" onClick={() => editor?.chain().focus().toggleHeading({ level: 3 }).run()} isActive={Boolean(editor?.isActive('heading', { level: 3 }))} icon={Heading3} />
                        <ToolbarButton label="Párrafo" onClick={() => editor?.chain().focus().setParagraph().run()} isActive={Boolean(editor?.isActive('paragraph') && !editor?.isActive('heading'))} icon={Pilcrow} />
                        <div className="w-[1px] h-5 bg-[hsl(var(--border))] mx-1" />
                        <ToolbarButton label="Negrita" onClick={() => editor?.chain().focus().toggleBold().run()} isActive={Boolean(editor?.isActive('bold'))} icon={Bold} />
                        <ToolbarButton label="Cursiva" onClick={() => editor?.chain().focus().toggleItalic().run()} isActive={Boolean(editor?.isActive('italic'))} icon={Italic} />
                        <ToolbarButton label="Subrayado" onClick={() => editor?.chain().focus().toggleUnderline().run()} isActive={Boolean(editor?.isActive('underline'))} icon={UnderlineIcon} />
                        <ToolbarButton label="Código" onClick={() => editor?.chain().focus().toggleCode().run()} isActive={Boolean(editor?.isActive('code'))} icon={Code} />
                        <div className="w-[1px] h-5 bg-[hsl(var(--border))] mx-1" />
                        <ToolbarButton label="Lista con viñetas" onClick={() => editor?.chain().focus().toggleBulletList().run()} isActive={Boolean(editor?.isActive('bulletList'))} icon={List} />
                        <ToolbarButton label="Lista numerada" onClick={() => editor?.chain().focus().toggleOrderedList().run()} isActive={Boolean(editor?.isActive('orderedList'))} icon={ListOrdered} />
                        <ToolbarButton label="Lista de tareas" onClick={() => editor?.chain().focus().toggleTaskList().run()} isActive={Boolean(editor?.isActive('taskList'))} icon={CheckSquare} />
                        <div className="w-[1px] h-5 bg-[hsl(var(--border))] mx-1" />
                        <ToolbarButton label="Cita" onClick={() => editor?.chain().focus().toggleBlockquote().run()} isActive={Boolean(editor?.isActive('blockquote'))} icon={Quote} />
                        <ToolbarButton label="Insertar imagen" onClick={openImagePanel} isActive={imagePanelOpen} icon={ImageIcon} />
                    </div>
                )}

                {imagePanelOpen && viewMode === 'edit' && (
                    <div
                        data-testid="wiki-image-panel"
                        role="group"
                        aria-label="Insertar imagen en la wiki"
                        className="mx-4 mt-2 flex flex-wrap items-center gap-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-2"
                    >
                        <ImageIcon size={16} className="text-[hsl(var(--primary))] shrink-0" aria-hidden />
                        <input
                            type="url"
                            value={imageUrl}
                            onChange={(e) => setImageUrl(e.currentTarget.value)}
                            onKeyDown={(e) => { if (e.key === 'Enter' && imageUrl.trim()) { e.preventDefault(); insertImageFromUrl(); } }}
                            placeholder="https://… o /static/…"
                            aria-label="URL de la imagen"
                            className="min-w-0 flex-1 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-2.5 py-1.5 text-sm text-[hsl(var(--foreground))] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[hsl(var(--primary))]"
                        />
                        <button
                            type="button"
                            onClick={insertImageFromUrl}
                            disabled={!imageUrl.trim()}
                            aria-label="Añadir imagen por URL"
                            className="px-3 py-2 rounded-md bg-[hsl(var(--surface-1))] text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--foreground))] border border-[hsl(var(--border))] hover:bg-[hsl(var(--surface-3))]/40 disabled:opacity-40 transition-all"
                        >
                            Añadir por URL
                        </button>
                        <ToolbarButton label="Cerrar panel de imagen" onClick={() => { setImagePanelOpen(false); setImageUrl(''); }} icon={X} />
                    </div>
                )}

                <div className="flex-1 p-4 relative overflow-y-auto">
                    <div className="absolute top-10 right-10 opacity-5 pointer-events-none">
                        <Zap size={200} fill="currentColor" className="text-[hsl(var(--primary))]" aria-hidden="true" focusable="false" />
                    </div>
                    {isLoading ? (
                        <div className="flex h-full items-center justify-center gap-2 text-sm font-bold text-[hsl(var(--text-secondary))]">
                            <Loader2 size={16} className="animate-spin" />
                            Cargando wiki compartida...
                        </div>
                    ) : viewMode === 'preview' ? (
                        <div
                            className={`${WIKI_PROSE_CLASS} max-w-none text-lg`}
                            data-testid="wiki-preview"
                            dangerouslySetInnerHTML={{ __html: editor?.getHTML() || content }}
                        />
                    ) : (
                        <EditorContent editor={editor} />
                    )}
                    {error && (
                        <p className="absolute bottom-4 left-10 rounded-full bg-danger-soft px-3 py-1 text-2xs font-semibold uppercase tracking-wide text-danger-text">
                            {error}
                        </p>
                    )}
                </div>

                <footer className="p-3 border-t border-[hsl(var(--border))] dark:border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] dark:bg-transparent flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="flex items-center gap-2">
                            <Clock size={14} className="text-[hsl(var(--text-secondary))]" />
                            <span className="text-2xs font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Persistencia compartida</span>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        <button aria-label="Eliminar contenido" title="Limpiar contenido" className="p-3 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--danger))] transition-colors" onClick={handleClear}><Trash2 size={18} /></button>
                        <button aria-label="Exportar como texto" title="Exportar como texto plano" className="p-3 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-colors" onClick={handleExportText}><Download size={18} /></button>
                        <button aria-label="Más opciones" title="Más opciones" className="p-3 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-colors" onClick={() => {/* future: options menu */}}><MoreHorizontal size={18} /></button>
                    </div>
                </footer>
            </main>

            <style jsx global>{`
                ${WIKI_PROSE_CSS}
            `}</style>
        </div>
    );
}
