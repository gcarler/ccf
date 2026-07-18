"use client";

import WikiEditor from '@/components/wiki/WikiEditor';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import { motion } from 'framer-motion';
import { BookOpen, ChevronLeft, History, MoreHorizontal, Share2, AlertCircle, Eye, Download } from 'lucide-react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { useEffect, useState, useRef, useCallback } from 'react';
import sanitize from 'sanitize-html';

interface WikiDoc {
    id: string;
    page_key: string;
    title: string;
    content: string;
    version: number;
    updated_at: string;
}

export default function WikiDocEditPage() {
    const params = useParams();
    const searchParams = useSearchParams();
    const page_key = params ? (params.page_key as string) : null;
    const isReadonly = searchParams?.get('view') === 'read';
    const router = useRouter();
    const { token } = useAuth();
    const { addToast } = useToast();
    const [doc, setDoc] = useState<WikiDoc | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const hasUnsavedRef = useRef(false);

    const fetchDoc = useCallback(async (signal?: AbortSignal) => {
        if (!token || !page_key) {
            if (!token) setLoading(false);
            return;
        }
        setError(null);
        setLoading(true);
        try {
            const data = await apiFetch<WikiDoc>(`/wiki/pages/${page_key}`, { token, signal });
            setDoc(data);
        } catch (err: any) {
            if (err?.name === 'AbortError') return;
            console.error("Error fetching doc:", err);
            addToast('No se pudo cargar el documento. Intenta de nuevo.', 'error');
            setError("No se pudo cargar el documento. Intenta de nuevo.");
        } finally {
            setLoading(false);
        }
    }, [token, page_key, addToast]);

    useEffect(() => {
        const controller = new AbortController();
        fetchDoc(controller.signal);
        return () => controller.abort();
    }, [fetchDoc]);

    // beforeunload warning for unsaved changes
    useEffect(() => {
        if (isReadonly) return;
        const handler = (e: BeforeUnloadEvent) => {
            if (hasUnsavedRef.current) {
                e.preventDefault();
                e.returnValue = '';
            }
        };
        window.addEventListener('beforeunload', handler);
        return () => window.removeEventListener('beforeunload', handler);
    }, [isReadonly]);

    const handleSave = useCallback(async (newContent: string) => {
        if (!token || !page_key) return;
        await apiFetch(`/wiki/pages/${page_key}`, {
            method: 'PATCH',
            token,
            body: { content: newContent }
        });
        hasUnsavedRef.current = false;
    }, [token, page_key]);

    const handleContentChange = useCallback(() => {
        hasUnsavedRef.current = true;
    }, []);

    const handleExportHtml = useCallback(() => {
        if (!doc) return;
        const blob = new Blob([doc.content], { type: 'text/html' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${doc.page_key}.html`;
        a.click();
        URL.revokeObjectURL(url);
    }, [doc]);

    if (loading) return (
        <div className="flex-1 flex items-center justify-center bg-[hsl(var(--bg-primary))] dark:bg-[#141517]">
            <motion.div 
                animate={{ rotate: 360 }}
                transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
                className="size-8 border-2 border-[hsl(var(--primary))] border-t-transparent rounded-full"
            />
        </div>
    );

    if (error) return (
        <div className="flex-1 flex items-center justify-center bg-[hsl(var(--bg-primary))] dark:bg-[#141517]">
            <div className="text-center space-y-4">
                <AlertCircle size={32} className="text-rose-500 mx-auto" />
                <p className="font-bold text-sm text-rose-500">{error}</p>
            </div>
        </div>
    );

    if (!doc) return (
        <div className="flex-1 flex items-center justify-center bg-[hsl(var(--bg-primary))] dark:bg-[#141517]">
            <div className="text-center space-y-4">
                <BookOpen size={32} className="text-[hsl(var(--text-secondary))] mx-auto" />
                <p className="font-bold text-sm text-[hsl(var(--text-secondary))]">Documento no encontrado</p>
            </div>
        </div>
    );

    const sidebarSections = [
        {
            title: 'Wiki',
            items: [
                { id: 'wiki-home', label: 'Inicio', href: '/plataforma/wiki', icon: BookOpen },
            ]
        }
    ];

    return (
        <WorkspaceLayout sidebarTitle="Wiki" sidebarSections={sidebarSections}>
            <div className="flex-1 flex flex-col bg-[hsl(var(--bg-primary))] dark:bg-[#141517] overflow-hidden">
            <header className="h-8 px-3 border-b border-[hsl(var(--border))] dark:border-white/5 flex items-center justify-between shrink-0 bg-white/80 dark:bg-[#141517]/80 backdrop-blur-md sticky top-0 z-10">
                <div className="flex items-center gap-4">
                    <button 
                        onClick={() => router.push('/plataforma/wiki')}
                        className="p-2 hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 rounded-md text-[hsl(var(--text-secondary))] transition-all"
                        aria-label="Volver al listado"
                    >
                        <ChevronLeft size={20} />
                    </button>
                    <div className="w-[1px] h-4 bg-[hsl(var(--surface-3))] dark:bg-white/10" />
                    <h1 className="text-[13px] font-bold text-[hsl(var(--text-primary))] dark:text-white truncate max-w-[300px]">
                        {doc.title}
                        {isReadonly && <span className="ml-2 text-[10px] text-[hsl(var(--text-secondary))] font-normal">(solo lectura)</span>}
                    </h1>
                </div>

                <div className="flex items-center gap-2">
                    {!isReadonly && (
                        <button
                            title="Historial de versiones"
                            aria-label="Historial de versiones"
                            className="p-2 hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 rounded-md text-[hsl(var(--text-secondary))]"
                            onClick={() => router.push(`/plataforma/wiki/docs/${page_key}?tab=versions`)}
                        >
                            <History size={18} />
                        </button>
                    )}
                    <button
                        title="Copiar enlace"
                        aria-label="Copiar enlace del documento"
                        className="p-2 hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 rounded-md text-[hsl(var(--text-secondary))]"
                        onClick={() => navigator.clipboard.writeText(window.location.href).catch(() => {})}
                    >
                        <Share2 size={18} />
                    </button>
                    <button
                        title="Exportar HTML"
                        aria-label="Exportar como HTML"
                        className="p-2 hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 rounded-md text-[hsl(var(--text-secondary))]"
                        onClick={handleExportHtml}
                    >
                        <Download size={18} />
                    </button>
                    {!isReadonly && (
                        <button
                            title="Cambiar a vista lectura"
                            aria-label="Vista lectura"
                            className="p-2 hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 rounded-md text-[hsl(var(--text-secondary))]"
                            onClick={() => router.push(`/plataforma/wiki/docs/${page_key}?view=read`)}
                        >
                            <Eye size={18} />
                        </button>
                    )}
                    {isReadonly && (
                        <button
                            title="Editar documento"
                            aria-label="Editar documento"
                            className="p-2 hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 rounded-md text-[hsl(var(--text-secondary))]"
                            onClick={() => router.push(`/plataforma/wiki/docs/${page_key}`)}
                        >
                            <BookOpen size={18} />
                        </button>
                    )}
                    <button
                        title="Más opciones"
                        aria-label="Más opciones"
                        className="p-2 hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 rounded-md text-[hsl(var(--text-secondary))]"
                        onClick={() => {/* future: dropdown menu */}}
                    >
                        <MoreHorizontal size={18} />
                    </button>
                </div>
            </header>

            <div className="flex-1 overflow-y-auto custom-scrollbar">
                {isReadonly ? (
                    <div className="max-w-4xl mx-auto py-8 px-6">
                        <div
                            className="prose prose-slate dark:prose-invert max-w-none"
                            dangerouslySetInnerHTML={{ __html: sanitize(doc.content || '') }}
                        />
                    </div>
                ) : (
                    <WikiEditor 
                        initialContent={doc.content || ""} 
                        onSave={handleSave}
                        onContentChange={handleContentChange}
                        placeholder="Comienza la base de conocimiento..."
                    />
                )}
            </div>
        </div>
        </WorkspaceLayout>
    );
}
