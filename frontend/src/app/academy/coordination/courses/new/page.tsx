"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import type { ViewType } from '@/components/ViewSwitcher';
import { apiFetch } from '@/lib/http';
import { 
    GraduationCap, 
    Save, 
    Plus, 
    FileText, 
    ShieldCheck, 
    ArrowLeft,
    Clock,
} from 'lucide-react';
import { toast } from 'sonner';
import clsx from 'clsx';
import { motion } from 'framer-motion';

export default function NewCoursePage() {
    const router = useRouter();
    const { token, isAuthenticated } = useAuth();
    
    const [formData, setFormData] = useState({
        code: '',
        title: '',
        description: '',
        modality: 'non_formal',
        duration_hours: 0,
        certificate_type: 'Participación',
        is_published: true,
        is_self_paced: true
    });
    
    const [loading, setLoading] = useState(false);
    const [viewType, setViewType] = useState<ViewType>('grid');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!token) return;
        
        try {
            setLoading(true);
            await new Promise(r => setTimeout(r, 800)); // Delay estético
            await apiFetch('/academy/admin/courses', {
                method: 'POST',
                token,
                body: JSON.stringify(formData)
            });
            toast.success('¡Programa creado con éxito!');
            router.push('/academy/coordination');
        } catch (err) {
            console.error(err);
            toast.error('Error al crear el curso');
        } finally {
            setLoading(false);
        }
    };

    if (!isAuthenticated) return null;

    const containerVariants = {
        hidden: { opacity: 0, y: 20 },
        show: { opacity: 1, y: 0, transition: { staggerChildren: 0.1 } }
    };

    return (
        <div className="flex flex-col h-full bg-[#f8fafc] dark:bg-[#1E1F21] overflow-hidden relative">
            {/* Background elements */}
            <div className="absolute top-0 right-0 w-[500px] h-48 bg-blue-600/5 rounded-full blur-[100px] pointer-events-none" />
            
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: 'Academia', icon: GraduationCap, href: '/academy' },
                    { label: 'Coordinación', icon: ShieldCheck, href: '/academy/coordination' },
                    { label: 'Nuevo Programa', icon: Plus },
                ]}
                viewType={viewType}
                setViewType={setViewType}
                availableViews={['grid', 'list', 'table']}
                leftActions={
                    <button onClick={() => router.back()} className="p-2.5 hover:bg-white dark:hover:bg-white/5 rounded-md transition-all border border-transparent hover:border-slate-200 dark:hover:border-white/10 shadow-sm">
                        <ArrowLeft size={18} className="text-slate-500" />
                    </button>
                }
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin p-4 lg:p-4 relative z-10">
                {viewType === 'list' && (
                    <div className="max-w-4xl mx-auto space-y-2">
                        {[
                            ['Código', formData.code || 'Pendiente'],
                            ['Nombre', formData.title || 'Pendiente'],
                            ['Modalidad', formData.modality],
                            ['Duración', `${formData.duration_hours} horas`],
                            ['Certificación', formData.certificate_type],
                        ].map(([label, value]) => (
                            <article key={label} className="rounded-md border border-slate-200 bg-white p-4 dark:border-white/10 dark:bg-white/5">
                                <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">{label}</p>
                                <h3 className="mt-2 text-sm font-semibold text-slate-900 dark:text-white">{value}</h3>
                            </article>
                        ))}
                    </div>
                )}

                {viewType === 'table' && (
                    <div className="max-w-4xl mx-auto overflow-hidden rounded-md border border-slate-200 bg-white dark:border-white/10 dark:bg-white/5">
                        <table className="w-full text-left">
                            <thead className="bg-slate-50 dark:bg-white/5 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                                <tr><th className="px-4 py-2">Campo</th><th className="px-4 py-2">Valor actual</th></tr>
                            </thead>
                            <tbody>
                                {[
                                    ['Código', formData.code || 'Pendiente'],
                                    ['Nombre', formData.title || 'Pendiente'],
                                    ['Descripción', formData.description || 'Pendiente'],
                                    ['Modalidad', formData.modality],
                                    ['Duración', `${formData.duration_hours} horas`],
                                    ['Certificación', formData.certificate_type],
                                ].map(([label, value]) => (
                                    <tr key={label} className="border-t border-slate-100 dark:border-white/5">
                                        <td className="px-4 py-2 font-bold text-slate-900 dark:text-white">{label}</td>
                                        <td className="px-4 py-2 text-slate-500">{value}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}

                {viewType === 'grid' && (
                <motion.div 
                    variants={containerVariants} initial="hidden" animate="show"
                    className="max-w-4xl mx-auto space-y-3"
                >
                    <header className="space-y-4">
                        <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-blue-600/10 rounded-full text-[10px] font-semibold uppercase tracking-wide text-blue-600">
                            <Plus size={14} strokeWidth={3} /> Laboratorio de Contenido
                        </div>
                        <h1 className="text-xl lg:text-xl font-black text-slate-900 dark:text-white tracking-tighter leading-none">Diseña un <br /><span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-blue-400">Nuevo Futuro.</span></h1>
                        <p className="text-slate-500 text-sm font-medium max-w-2xl leading-relaxed">Configura los cimientos de una nueva experiencia educativa para la comunidad CCF.</p>
                    </header>

                    <form onSubmit={handleSubmit} className="space-y-4">
                        {/* Basic Info */}
                        <motion.div variants={{hidden: {opacity:0}, show: {opacity:1}}} className="bg-white dark:bg-[#15171c] rounded-lg border border-slate-200 dark:border-white/5 p-3 lg:p-4 shadow-2xl shadow-slate-200/20 dark:shadow-none space-y-4 group transition-all hover:border-blue-500/20">
                            <div className="flex items-center gap-4 text-blue-600">
                                <div className="size-9 rounded-lg bg-blue-50 dark:bg-blue-500/10 flex items-center justify-center shadow-inner">
                                    <FileText size={24} strokeWidth={2.5} />
                                </div>
                                <h2 className="text-base font-semibold uppercase tracking-wide">Identidad del Programa</h2>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="space-y-3">
                                    <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 ml-4">Código Identificador</label>
                                    <input 
                                        required type="text" placeholder="Ej: FARO-01" value={formData.code}
                                        onChange={(e) => setFormData({...formData, code: e.target.value})}
                                        className="w-full bg-slate-50 dark:bg-black/20 border-2 border-transparent dark:border-white/5 rounded-lg px-4 py-2 text-sm font-bold outline-none focus:border-blue-500/50 focus:ring-4 focus:ring-blue-500/5 transition-all"
                                    />
                                </div>
                                <div className="space-y-3">
                                    <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 ml-4">Nombre Público</label>
                                    <input 
                                        required type="text" placeholder="Ej: Fundamentos de la Fe" value={formData.title}
                                        onChange={(e) => setFormData({...formData, title: e.target.value})}
                                        className="w-full bg-slate-50 dark:bg-black/20 border-2 border-transparent dark:border-white/5 rounded-lg px-4 py-2 text-sm font-bold outline-none focus:border-blue-500/50 focus:ring-4 focus:ring-blue-500/5 transition-all"
                                    />
                                </div>
                                <div className="md:col-span-2 space-y-3">
                                    <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 ml-4">Narrativa del Curso</label>
                                    <textarea 
                                        rows={4} placeholder="Describe el impacto y los objetivos de este programa..." value={formData.description}
                                        onChange={(e) => setFormData({...formData, description: e.target.value})}
                                        className="w-full bg-slate-50 dark:bg-black/20 border-2 border-transparent dark:border-white/5 rounded-md px-4 py-2 text-sm font-medium outline-none focus:border-blue-500/50 focus:ring-4 focus:ring-blue-500/5 transition-all resize-none leading-relaxed"
                                    />
                                </div>
                            </div>
                        </motion.div>

                        {/* Configuration */}
                        <motion.div variants={{hidden: {opacity:0}, show: {opacity:1}}} className="bg-white dark:bg-[#15171c] rounded-lg border border-slate-200 dark:border-white/5 p-3 lg:p-4 shadow-2xl shadow-slate-200/20 dark:shadow-none space-y-4 group transition-all hover:border-sky-500/20">
                            <div className="flex items-center gap-4 text-sky-600">
                                <div className="size-9 rounded-lg bg-sky-50 dark:bg-sky-500/10 flex items-center justify-center shadow-inner">
                                    <Clock size={24} strokeWidth={2.5} />
                                </div>
                                <h2 className="text-base font-semibold uppercase tracking-wide">Reglas de Negocio</h2>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                <div className="space-y-3">
                                    <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 ml-4">Modalidad Académica</label>
                                    <select 
                                        value={formData.modality}
                                        onChange={(e) => setFormData({...formData, modality: e.target.value})}
                                        className="w-full bg-slate-50 dark:bg-black/20 border-2 border-transparent dark:border-white/5 rounded-lg px-4 py-2 text-sm font-bold outline-none appearance-none cursor-pointer focus:border-sky-500/50 transition-all"
                                    >
                                        <option value="formal">Academia Formal</option>
                                        <option value="non_formal">Capacitación Libre</option>
                                    </select>
                                </div>
                                <div className="space-y-3">
                                    <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 ml-4">Esfuerzo Estimado (Hrs)</label>
                                    <input 
                                        type="number" value={formData.duration_hours}
                                        onChange={(e) => setFormData({...formData, duration_hours: parseInt(e.target.value)})}
                                        className="w-full bg-slate-50 dark:bg-black/20 border-2 border-transparent dark:border-white/5 rounded-lg px-4 py-2 text-sm font-bold outline-none focus:border-sky-500/50 transition-all"
                                    />
                                </div>
                                <div className="space-y-3">
                                    <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 ml-4">Título a Otorgar</label>
                                    <input 
                                        type="text" placeholder="Ej: Diplomado" value={formData.certificate_type}
                                        onChange={(e) => setFormData({...formData, certificate_type: e.target.value})}
                                        className="w-full bg-slate-50 dark:bg-black/20 border-2 border-transparent dark:border-white/5 rounded-lg px-4 py-2 text-sm font-bold outline-none focus:border-sky-500/50 transition-all"
                                    />
                                </div>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4">
                                <label className="flex items-center justify-between p-4 rounded-md bg-slate-50 dark:bg-black/20 border-2 border-transparent cursor-pointer hover:border-blue-500/20 transition-all group/toggle">
                                    <div className="space-y-1">
                                        <p className="text-sm font-semibold text-slate-800 dark:text-white leading-none">Publicar ahora</p>
                                        <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Hacer visible en el catálogo global</p>
                                    </div>
                                    <input 
                                        type="checkbox" checked={formData.is_published}
                                        onChange={(e) => setFormData({...formData, is_published: e.target.checked})}
                                        className="size-8 rounded-md accent-blue-600 transition-transform active:scale-90"
                                    />
                                </label>
                                <label className="flex items-center justify-between p-4 rounded-md bg-slate-50 dark:bg-black/20 border-2 border-transparent cursor-pointer hover:border-sky-500/20 transition-all group/toggle">
                                    <div className="space-y-1">
                                        <p className="text-sm font-semibold text-slate-800 dark:text-white leading-none">Autogestionado</p>
                                        <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Sin restricciones de fecha o cohorte</p>
                                    </div>
                                    <input 
                                        type="checkbox" checked={formData.is_self_paced}
                                        onChange={(e) => setFormData({...formData, is_self_paced: e.target.checked})}
                                        className="size-8 rounded-md accent-sky-600 transition-transform active:scale-90"
                                    />
                                </label>
                            </div>
                        </motion.div>

                        <div className="flex flex-col sm:flex-row items-center justify-end gap-4 pt-6">
                            <button 
                                type="button" onClick={() => router.back()}
                                className="w-full sm:w-auto px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-slate-400 hover:text-slate-800 dark:hover:text-white transition-all"
                            >
                                Descartar Cambios
                            </button>
                            <button 
                                type="submit" disabled={loading}
                                className="w-full sm:w-auto px-4 py-2 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-md font-black text-xs uppercase tracking-wide shadow-2xl hover:scale-105 active:scale-95 transition-all flex items-center justify-center gap-4 disabled:opacity-50 disabled:cursor-wait group"
                            >
                                {loading ? 'Sincronizando...' : 'Lanzar Programa'}
                                <Save size={20} className={clsx(!loading && "group-hover:translate-y-[-2px] transition-transform")} />
                            </button>
                        </div>
                    </form>
                </motion.div>
                )}
            </main>
        </div>
    );
}

