"use client";

import React, { useEffect, useState, useMemo } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import type { ViewType } from '@/components/ViewSwitcher';
import { apiFetch } from '@/lib/http';
import {
    GraduationCap, Save, FileText, ShieldCheck, ArrowLeft, Clock, Loader2,
} from 'lucide-react';
import { toast } from 'sonner';
import clsx from 'clsx';
import { motion } from 'framer-motion';

const INPUT = "w-full bg-slate-50 dark:bg-black/20 border-2 border-transparent dark:border-white/5 rounded-lg px-3 py-1.5 text-sm font-bold outline-none focus:border-blue-500/50 focus:ring-4 focus:ring-blue-500/5 transition-all text-slate-900 dark:text-white";
const LABEL = "text-[10px] font-black uppercase tracking-wide text-slate-400 ml-4";

export default function EditCoursePage() {
    const params = useParams();
    const id = params?.id as string;
    const router = useRouter();
    const { token } = useAuth();

    const [form, setForm] = useState({
        code: '', title: '', description: '',
        modality: 'non_formal', duration_hours: 0,
        certificate_type: '', is_published: true, is_self_paced: true,
    });
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [viewType, setViewType] = useState<ViewType>('grid');

    useEffect(() => {
        if (!token || !id) return;
        apiFetch<any>(`/academy/courses/${id}`, { token })
            .then(data => setForm({
                code: data.code ?? '',
                title: data.title ?? '',
                description: data.description ?? '',
                modality: data.modality ?? 'non_formal',
                duration_hours: data.duration_hours ?? 0,
                certificate_type: data.certificate_type ?? '',
                is_published: data.is_published ?? true,
                is_self_paced: data.is_self_paced ?? true,
            }))
            .catch(() => toast.error('Error al cargar el curso'))
            .finally(() => setLoading(false));
    }, [id, token]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!token) return;
        setSaving(true);
        try {
            await apiFetch(`/academy/admin/courses/${id}`, {
                method: 'PATCH', token, body: form,
            });
            toast.success('Curso actualizado correctamente');
            router.push('/academy/coordination');
        } catch {
            toast.error('Error al guardar cambios');
        } finally {
            setSaving(false);
        }
    };

    const set = (field: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
        setForm(f => ({ ...f, [field]: e.target.type === 'number' ? Number(e.target.value) : e.target.value }));

    const containerVariants = {
        hidden: { opacity: 0, y: 20 },
        show: { opacity: 1, y: 0, transition: { staggerChildren: 0.08 } },
    };
    const itemVariants = { hidden: { opacity: 0, y: 10 }, show: { opacity: 1, y: 0 } };

    return (
        <div className="flex flex-col h-full bg-[#f8fafc] dark:bg-[#1E1F21] overflow-hidden relative">
            <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-blue-600/5 rounded-full blur-[100px] pointer-events-none" />

            <WorkspaceToolbar
                breadcrumbs={[
                    { label: 'Academia', icon: GraduationCap, href: '/academy' },
                    { label: 'Coordinacion', icon: ShieldCheck, href: '/academy/coordination' },
                    { label: 'Editar Curso', icon: FileText },
                ]}
                viewType={viewType}
                setViewType={setViewType}
                availableViews={['grid', 'list', 'table']}
                leftActions={
                    <button onClick={() => router.back()} className="p-2.5 hover:bg-white dark:hover:bg-white/5 rounded-lg transition-all border border-transparent hover:border-slate-200 dark:hover:border-white/10">
                        <ArrowLeft size={18} className="text-slate-500" />
                    </button>
                }
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin p-4 lg:p-4 relative z-10">
                {loading ? (
                    <div className="flex justify-center items-center h-64">
                        <Loader2 className="animate-spin text-blue-600" size={32} />
                    </div>
                ) : (
                    <motion.div variants={containerVariants} initial="hidden" animate="show" className="max-w-4xl mx-auto space-y-3">

                        <motion.header variants={itemVariants} className="space-y-3">
                            <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-amber-500/10 rounded-full text-[10px] font-black uppercase tracking-wide text-amber-600 dark:text-amber-400">
                                <FileText size={13} strokeWidth={3} /> Edicion de Contenido
                            </div>
                            <h1 className="text-lg lg:text-xl font-black text-slate-900 dark:text-white tracking-tighter leading-none">
                                Actualiza el <br />
                                <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-blue-400">Programa.</span>
                            </h1>
                        </motion.header>

                        <form onSubmit={handleSubmit} className="space-y-4">
                            <motion.div variants={itemVariants} className="bg-white dark:bg-[#15171c] rounded-lg border border-slate-200 dark:border-white/5 p-3 lg:p-4 shadow-sm space-y-3 hover:border-blue-500/20 transition-all">
                                <div className="flex items-center gap-4 text-blue-600">
                                    <div className="size-9 rounded-lg bg-blue-50 dark:bg-blue-500/10 flex items-center justify-center shadow-inner">
                                        <FileText size={22} strokeWidth={2.5} />
                                    </div>
                                    <h2 className="text-base font-black uppercase tracking-wide">Identidad del Programa</h2>
                                </div>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                    <div className="space-y-2">
                                        <label className={LABEL}>Codigo Identificador</label>
                                        <input type="text" required placeholder="Ej: FARO-01" value={form.code} onChange={set('code')} className={INPUT} />
                                    </div>
                                    <div className="space-y-2">
                                        <label className={LABEL}>Nombre Publico</label>
                                        <input type="text" required placeholder="Ej: Fundamentos de la Fe" value={form.title} onChange={set('title')} className={INPUT} />
                                    </div>
                                    <div className="md:col-span-2 space-y-2">
                                        <label className={LABEL}>Descripcion</label>
                                        <textarea rows={4} placeholder="Objetivos e impacto del programa..." value={form.description} onChange={set('description')}
                                            className={clsx(INPUT, "resize-none py-1.5 leading-relaxed")} />
                                    </div>
                                </div>
                            </motion.div>

                            <motion.div variants={itemVariants} className="bg-white dark:bg-[#15171c] rounded-lg border border-slate-200 dark:border-white/5 p-3 lg:p-4 shadow-sm space-y-3 hover:border-sky-500/20 transition-all">
                                <div className="flex items-center gap-4 text-sky-600">
                                    <div className="size-9 rounded-lg bg-sky-50 dark:bg-sky-500/10 flex items-center justify-center shadow-inner">
                                        <Clock size={22} strokeWidth={2.5} />
                                    </div>
                                    <h2 className="text-base font-black uppercase tracking-wide">Configuracion Academica</h2>
                                </div>
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                    <div className="space-y-2">
                                        <label className={LABEL}>Modalidad</label>
                                        <select value={form.modality} onChange={set('modality')}
                                            className={clsx(INPUT, "appearance-none cursor-pointer")}>
                                            <option value="formal">Academia Formal</option>
                                            <option value="non_formal">Capacitacion Libre</option>
                                        </select>
                                    </div>
                                    <div className="space-y-2">
                                        <label className={LABEL}>Duracion (horas)</label>
                                        <input type="number" min={0} value={form.duration_hours} onChange={set('duration_hours')} className={INPUT} />
                                    </div>
                                    <div className="space-y-2">
                                        <label className={LABEL}>Tipo de Certificado</label>
                                        <input type="text" placeholder="Ej: Diplomado" value={form.certificate_type} onChange={set('certificate_type')} className={INPUT} />
                                    </div>
                                </div>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
                                    {[
                                        { key: 'is_published', title: 'Publicado', desc: 'Visible en el catalogo global' },
                                        { key: 'is_self_paced', title: 'Autogestionado', desc: 'Sin restricciones de cohorte' },
                                    ].map(({ key, title, desc }) => (
                                        <label key={key} className="flex items-center justify-between p-3 rounded-lg bg-slate-50 dark:bg-black/20 border-2 border-transparent cursor-pointer hover:border-blue-500/20 transition-all">
                                            <div>
                                                <p className="text-sm font-black text-slate-800 dark:text-white">{title}</p>
                                                <p className={LABEL}>{desc}</p>
                                            </div>
                                            <input type="checkbox" checked={(form as any)[key]}
                                                onChange={e => setForm(f => ({ ...f, [key]: e.target.checked }))}
                                                className="size-8 rounded-lg accent-blue-600 transition-transform active:scale-90" />
                                        </label>
                                    ))}
                                </div>
                            </motion.div>

                            <div className="flex items-center justify-end gap-4 pt-4">
                                <button type="button" onClick={() => router.back()}
                                    className="px-3 py-1.5 text-[11px] font-black uppercase tracking-wide text-slate-400 hover:text-slate-800 dark:hover:text-white transition-all">
                                    Descartar
                                </button>
                                <button type="submit" disabled={saving}
                                    className="px-3 py-1.5 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-lg font-black text-xs uppercase tracking-wide shadow-2xl hover:scale-105 active:scale-95 transition-all flex items-center gap-3 disabled:opacity-50 disabled:cursor-wait group">
                                    {saving ? <Loader2 size={18} className="animate-spin" /> : <Save size={18} className="group-hover:-translate-y-0.5 transition-transform" />}
                                    {saving ? 'Guardando...' : 'Guardar Cambios'}
                                </button>
                            </div>
                        </form>
                    </motion.div>
                )}
            </main>
        </div>
    );
}
