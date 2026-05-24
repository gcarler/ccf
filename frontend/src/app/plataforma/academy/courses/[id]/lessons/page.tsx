"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import type { ViewType } from '@/components/ViewSwitcher';
import { apiFetch } from '@/lib/http';
import {
    GraduationCap, BookOpen, Plus, Pencil, Trash2, X, Save, Loader2,
    Video, FileText, Link as LinkIcon, ArrowLeft, GripVertical,
} from 'lucide-react';
import { toast } from 'sonner';
import clsx from 'clsx';
import { motion, AnimatePresence } from 'framer-motion';

const INPUT = "w-full bg-slate-50 dark:bg-black/20 border-2 border-transparent dark:border-white/5 rounded-lg px-4 py-1.5 text-sm font-bold outline-none focus:border-blue-500/50 focus:ring-4 focus:ring-blue-500/5 transition-all text-slate-900 dark:text-white";
const LABEL = "text-[10px] font-semibold uppercase tracking-wide text-slate-400";

const CONTENT_TYPE_META: Record<string, { label: string; icon: any; color: string; bg: string }> = {
    video:    { label: 'Video',    icon: Video,     color: 'text-rose-600',   bg: 'bg-rose-50 dark:bg-rose-500/10' },
    text:     { label: 'Texto',    icon: FileText,  color: 'text-blue-600',   bg: 'bg-blue-50 dark:bg-blue-500/10' },
    document: { label: 'Documento',icon: FileText,  color: 'text-indigo-600', bg: 'bg-indigo-50 dark:bg-indigo-500/10' },
    link:     { label: 'Enlace',   icon: LinkIcon,  color: 'text-emerald-600',bg: 'bg-emerald-50 dark:bg-emerald-500/10' },
};

interface Lesson {
    id: number;
    title: string;
    content?: string;
    content_type: string;
    media_url?: string;
    order_index: number;
}

const EMPTY_FORM = { title: '', content: '', content_type: 'text', media_url: '', order_index: 0 };

export default function LessonsPage() {
    const params = useParams();
    const courseId = params?.id as string;
    const router = useRouter();
    const { token } = useAuth();

    const [course, setCourse] = useState<any>(null);
    const [lessons, setLessons] = useState<Lesson[]>([]);
    const [loading, setLoading] = useState(true);
    const [viewType, setViewType] = useState<ViewType>('table');

    const [drawerOpen, setDrawerOpen] = useState(false);
    const [editing, setEditing] = useState<Lesson | null>(null);
    const [form, setForm] = useState(EMPTY_FORM);
    const [saving, setSaving] = useState(false);
    const [deleteId, setDeleteId] = useState<number | null>(null);

    const load = useCallback(async () => {
        if (!token || !courseId) return;
        try {
            setLoading(true);
            const [courseData, lessonsData] = await Promise.allSettled([
                apiFetch<any>(`/academy/courses/${courseId}`, { token }),
                apiFetch<Lesson[]>(`/academy/courses/${courseId}/lessons`, { token }),
            ]);
            if (courseData.status === 'fulfilled') setCourse(courseData.value);
            if (lessonsData.status === 'fulfilled') setLessons(lessonsData.value ?? []);
        } catch {
            toast.error('Error al cargar lecciones');
        } finally {
            setLoading(false);
        }
    }, [token, courseId]);

    useEffect(() => { load(); }, [load]);

    const openCreate = () => {
        setEditing(null);
        setForm({ ...EMPTY_FORM, order_index: lessons.length + 1 });
        setDrawerOpen(true);
    };

    const openEdit = (lesson: Lesson) => {
        setEditing(lesson);
        setForm({
            title: lesson.title,
            content: lesson.content ?? '',
            content_type: lesson.content_type,
            media_url: lesson.media_url ?? '',
            order_index: lesson.order_index,
        });
        setDrawerOpen(true);
    };

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!token) return;
        setSaving(true);
        try {
            if (editing) {
                await apiFetch(`/academy/admin/lessons/${editing.id}`, { method: 'PATCH', token, body: form });
                toast.success('Lección actualizada');
            } else {
                await apiFetch(`/academy/admin/courses/${courseId}/lessons`, { method: 'POST', token, body: form });
                toast.success('Lección creada');
            }
            setDrawerOpen(false);
            load();
        } catch {
            toast.error('Error al guardar la lección');
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async (id: number) => {
        if (!token) return;
        try {
            await apiFetch(`/academy/admin/lessons/${id}`, { method: 'DELETE', token });
            toast.success('Lección eliminada');
            setDeleteId(null);
            load();
        } catch {
            toast.error('Error al eliminar');
        }
    };

    const set = (field: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
        setForm(f => ({ ...f, [field]: e.target.type === 'number' ? Number(e.target.value) : e.target.value }));

    const sorted = [...lessons].sort((a, b) => a.order_index - b.order_index);

    return (
        <div className="flex flex-col h-full bg-[#f8fafc] dark:bg-[#1E1F21] overflow-hidden">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: 'Academia', icon: GraduationCap, href: '/plataforma/academy' },
                    { label: course?.title ?? 'Curso', icon: BookOpen, href: `/academy/courses/${courseId}` },
                    { label: 'Lecciones', icon: BookOpen },
                ]}
                viewType={viewType}
                setViewType={setViewType}
                availableViews={['table', 'list']}
                leftActions={
                    <button onClick={() => router.back()} className="p-2.5 hover:bg-white dark:hover:bg-white/5 rounded-md transition-all border border-transparent hover:border-slate-200 dark:hover:border-white/10">
                        <ArrowLeft size={18} className="text-slate-500" />
                    </button>
                }
                rightActions={
                    <button onClick={openCreate}
                        className="flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded-md text-[11px] font-semibold uppercase tracking-wide shadow-lg shadow-blue-500/20 hover:bg-blue-700 active:scale-95 transition-all">
                        <Plus size={16} strokeWidth={3} /> Nueva Lección
                    </button>
                }
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin p-4 lg:p-3 relative z-10">
                {loading ? (
                    <div className="flex justify-center items-center h-48">
                        <Loader2 className="animate-spin text-blue-600" size={32} />
                    </div>
                ) : sorted.length === 0 ? (
                    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                        className="flex flex-col items-center justify-center h-48 gap-4 text-center">
                        <div className="size-8 rounded-lg bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-400">
                            <BookOpen size={36} />
                        </div>
                        <div>
                            <h3 className="text-base font-bold text-slate-800 dark:text-white">Sin lecciones aún</h3>
                            <p className="text-sm text-slate-400 mt-1">Crea la primera lección de este curso.</p>
                        </div>
                        <button onClick={openCreate}
                            className="flex items-center gap-2 px-3 py-3 bg-blue-600 text-white rounded-md text-[11px] font-semibold uppercase tracking-wide shadow-lg shadow-blue-500/20 hover:bg-blue-700 active:scale-95 transition-all">
                            <Plus size={16} strokeWidth={3} /> Crear Lección
                        </button>
                    </motion.div>
                ) : viewType === 'table' ? (
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="bg-white dark:bg-[#15171c] rounded-lg border border-slate-200 dark:border-white/5 shadow-sm overflow-hidden">
                        <div className="overflow-x-auto">
                            <table className="w-full text-left min-w-[640px]">
                                <thead className="bg-slate-50 dark:bg-black/20">
                                    <tr>
                                        {['#', 'Título', 'Tipo', 'Recurso', 'Acciones'].map(h => (
                                            <th key={h} className="py-2.5 px-4 text-[10px] font-semibold uppercase tracking-wide text-slate-400 border-b border-slate-100 dark:border-white/5">
                                                {h}
                                            </th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody>
                                    {sorted.map((lesson, idx) => {
                                        const meta = CONTENT_TYPE_META[lesson.content_type] ?? CONTENT_TYPE_META.text;
                                        const Icon = meta.icon;
                                        return (
                                            <motion.tr key={lesson.id}
                                                initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
                                                transition={{ delay: idx * 0.04 }}
                                                className="hover:bg-slate-50 dark:hover:bg-white/[0.03] transition-colors border-b border-slate-100 dark:border-white/5 last:border-0 group">
                                                <td className="py-3 px-4">
                                                    <div className="flex items-center gap-2">
                                                        <GripVertical size={14} className="text-slate-300 dark:text-white/20" />
                                                        <span className="font-semibold text-slate-400">{lesson.order_index}</span>
                                                    </div>
                                                </td>
                                                <td className="py-3 px-4">
                                                    <p className="text-xs font-semibold text-slate-800 dark:text-white">{lesson.title}</p>
                                                    {lesson.content && (
                                                        <p className="text-[10px] text-slate-400 mt-0.5 max-w-xs truncate">{lesson.content}</p>
                                                    )}
                                                </td>
                                                <td className="py-3 px-4">
                                                    <span className={clsx("inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[10px] font-semibold uppercase tracking-wider", meta.bg, meta.color)}>
                                                        <Icon size={11} /> {meta.label}
                                                    </span>
                                                </td>
                                                <td className="py-3 px-4">
                                                    {lesson.media_url ? (
                                                        <a href={lesson.media_url} target="_blank" rel="noopener noreferrer"
                                                            className="text-[10px] text-blue-600 font-bold hover:underline flex items-center gap-1">
                                                            <LinkIcon size={11} /> Ver recurso
                                                        </a>
                                                    ) : (
                                                        <span className="text-[10px] text-slate-300 dark:text-white/20 font-bold">—</span>
                                                    )}
                                                </td>
                                                <td className="py-3 px-4">
                                                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                                        <button onClick={() => openEdit(lesson)}
                                                            className="p-2 hover:bg-blue-50 dark:hover:bg-blue-500/10 rounded-md text-slate-400 hover:text-blue-600 transition-all">
                                                            <Pencil size={14} />
                                                        </button>
                                                        {deleteId === lesson.id ? (
                                                            <div className="flex items-center gap-1">
                                                                <button onClick={() => handleDelete(lesson.id)}
                                                                    className="px-2 py-1 rounded-lg font-semibold bg-rose-100 dark:bg-rose-500/10 text-rose-600 hover:bg-rose-600 hover:text-white transition-all">
                                                                    Confirmar
                                                                </button>
                                                                <button onClick={() => setDeleteId(null)}
                                                                    className="p-1.5 hover:bg-slate-100 dark:hover:bg-white/5 rounded-lg text-slate-400">
                                                                    <X size={12} />
                                                                </button>
                                                            </div>
                                                        ) : (
                                                            <button onClick={() => setDeleteId(lesson.id)}
                                                                className="p-2 hover:bg-rose-50 dark:hover:bg-rose-500/10 rounded-md text-slate-400 hover:text-rose-600 transition-all">
                                                                <Trash2 size={14} />
                                                            </button>
                                                        )}
                                                    </div>
                                                </td>
                                            </motion.tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    </motion.div>
                ) : (
                    <div className="max-w-3xl mx-auto space-y-2">
                        {sorted.map((lesson, idx) => {
                            const meta = CONTENT_TYPE_META[lesson.content_type] ?? CONTENT_TYPE_META.text;
                            const Icon = meta.icon;
                            return (
                                <motion.div key={lesson.id}
                                    initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }}
                                    transition={{ delay: idx * 0.05 }}
                                    className="bg-white dark:bg-[#15171c] rounded-md border border-slate-200 dark:border-white/5 p-4 flex items-center gap-4 group hover:border-blue-500/20 transition-all shadow-sm">
                                    <div className={clsx("size-10 rounded-md flex items-center justify-center flex-shrink-0", meta.bg, meta.color)}>
                                        <Icon size={18} />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <p className="text-sm font-semibold text-slate-800 dark:text-white">{lesson.title}</p>
                                        <p className="text-[10px] text-slate-400 uppercase tracking-wide mt-0.5">{meta.label} · Lección {lesson.order_index}</p>
                                    </div>
                                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                        <button onClick={() => openEdit(lesson)} className="p-2 hover:bg-blue-50 dark:hover:bg-blue-500/10 rounded-md text-slate-400 hover:text-blue-600 transition-all">
                                            <Pencil size={14} />
                                        </button>
                                        {deleteId === lesson.id ? (
                                            <div className="flex items-center gap-1">
                                                <button onClick={() => handleDelete(lesson.id)} className="px-2 py-1 rounded-lg font-semibold bg-rose-100 dark:bg-rose-500/10 text-rose-600 hover:bg-rose-600 hover:text-white transition-all">Confirmar</button>
                                                <button onClick={() => setDeleteId(null)} className="p-1.5 hover:bg-slate-100 dark:hover:bg-white/5 rounded-lg text-slate-400"><X size={12} /></button>
                                            </div>
                                        ) : (
                                            <button onClick={() => setDeleteId(lesson.id)} className="p-2 hover:bg-rose-50 dark:hover:bg-rose-500/10 rounded-md text-slate-400 hover:text-rose-600 transition-all">
                                                <Trash2 size={14} />
                                            </button>
                                        )}
                                    </div>
                                </motion.div>
                            );
                        })}
                    </div>
                )}
            </main>

            {/* Drawer crear / editar */}
            <AnimatePresence>
                {drawerOpen && (
                    <>
                        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                            className="fixed inset-0 z-[90] bg-black/30 backdrop-blur-sm"
                            onClick={() => setDrawerOpen(false)} />
                        <motion.aside
                            initial={{ x: '100%', opacity: 0 }} animate={{ x: 0, opacity: 1 }}
                            exit={{ x: '100%', opacity: 0 }}
                            transition={{ type: 'spring', damping: 28, stiffness: 280 }}
                            className="fixed top-0 right-0 h-screen z-[100] w-full max-w-md bg-white dark:bg-[#1E1F21] shadow-2xl border-l border-slate-200 dark:border-white/10 flex flex-col">

                            {/* Header drawer */}
                            <div className="flex items-center justify-between px-3 py-1.5 border-b border-slate-100 dark:border-white/5 flex-shrink-0">
                                <div className="flex items-center gap-3">
                                    <div className="size-8 rounded-md bg-blue-50 dark:bg-blue-500/10 flex items-center justify-center text-blue-600">
                                        <BookOpen size={16} />
                                    </div>
                                    <div>
                                        <p className="text-[9px] font-semibold uppercase tracking-wide text-slate-400">
                                            {editing ? 'Editar' : 'Nueva'} Lección
                                        </p>
                                        <h3 className="text-sm font-semibold text-slate-900 dark:text-white truncate max-w-[200px]">
                                            {editing ? editing.title : 'Sin título'}
                                        </h3>
                                    </div>
                                </div>
                                <button onClick={() => setDrawerOpen(false)}
                                    className="p-2 hover:bg-slate-100 dark:hover:bg-white/5 rounded-md text-slate-400 transition-all">
                                    <X size={18} />
                                </button>
                            </div>

                            {/* Form */}
                            <form onSubmit={handleSave} className="flex-1 overflow-y-auto p-3 space-y-5">
                                <div className="space-y-2">
                                    <label className={LABEL}>Título *</label>
                                    <input required type="text" placeholder="Ej: Introducción al ministerio" value={form.title} onChange={set('title')} className={INPUT} />
                                </div>

                                <div className="space-y-2">
                                    <label className={LABEL}>Tipo de Contenido</label>
                                    <div className="grid grid-cols-2 gap-2">
                                        {Object.entries(CONTENT_TYPE_META).map(([key, meta]) => {
                                            const Icon = meta.icon;
                                            return (
                                                <button key={key} type="button"
                                                    onClick={() => setForm(f => ({ ...f, content_type: key }))}
                                                    className={clsx(
                                                        "flex items-center gap-2 px-3 py-3 rounded-md border text-[11px] font-semibold uppercase tracking-wide transition-all",
                                                        form.content_type === key
                                                            ? `${meta.bg} ${meta.color} border-transparent shadow-sm`
                                                            : "bg-slate-50 dark:bg-black/20 border-slate-200 dark:border-white/5 text-slate-400 hover:border-slate-300"
                                                    )}>
                                                    <Icon size={14} /> {meta.label}
                                                </button>
                                            );
                                        })}
                                    </div>
                                </div>

                                <div className="space-y-2">
                                    <label className={LABEL}>Descripción / Contenido</label>
                                    <textarea rows={5} placeholder="Descripción de la lección..." value={form.content} onChange={set('content')}
                                        className={clsx(INPUT, "resize-none py-1.5 leading-relaxed")} />
                                </div>

                                <div className="space-y-2">
                                    <label className={LABEL}>URL del Recurso</label>
                                    <input type="url" placeholder="https://..." value={form.media_url} onChange={set('media_url')} className={INPUT} />
                                </div>

                                <div className="space-y-2">
                                    <label className={LABEL}>Orden en el Curso</label>
                                    <input type="number" min={1} value={form.order_index} onChange={set('order_index')} className={INPUT} />
                                </div>
                            </form>

                            {/* Footer */}
                            <div className="flex items-center gap-3 px-3 py-1.5 border-t border-slate-100 dark:border-white/5 flex-shrink-0">
                                <button type="button" onClick={() => setDrawerOpen(false)}
                                    className="flex-1 py-3 text-[11px] font-semibold uppercase tracking-wide text-slate-400 hover:text-slate-700 dark:hover:text-white transition-all">
                                    Cancelar
                                </button>
                                <button onClick={handleSave} disabled={saving}
                                    className="flex-1 flex items-center justify-center gap-2 py-3 bg-blue-600 text-white rounded-md text-[11px] font-semibold uppercase tracking-wide shadow-lg shadow-blue-500/20 hover:bg-blue-700 active:scale-95 transition-all disabled:opacity-50">
                                    {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                                    {saving ? 'Guardando...' : (editing ? 'Actualizar' : 'Crear')}
                                </button>
                            </div>
                        </motion.aside>
                    </>
                )}
            </AnimatePresence>
        </div>
    );
}
