"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { apiFetch } from '@/lib/http';
import { 
    GraduationCap, 
    Save, 
    X, 
    Plus, 
    BookOpen, 
    Type, 
    FileText, 
    ShieldCheck, 
    ArrowLeft,
    Clock,
    Award
} from 'lucide-react';
import { toast } from 'sonner';
import clsx from 'clsx';

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

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!token) return;
        
        try {
            setLoading(true);
            await apiFetch('/academy/admin/courses', {
                method: 'POST',
                token,
                body: JSON.stringify(formData)
            });
            toast.success('Curso creado exitosamente');
            router.push('/academy/coordination');
        } catch (err) {
            console.error(err);
            toast.error('Error al crear el curso');
        } finally {
            setLoading(false);
        }
    };

    if (!isAuthenticated) return null;

    return (
        <div className="flex flex-col h-full bg-[#f8fafc] dark:bg-[#0b0d11] overflow-hidden">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: 'Academia', icon: GraduationCap, href: '/academy' },
                    { label: 'Coordinación', icon: ShieldCheck, href: '/academy/coordination' },
                    { label: 'Nuevo Curso', icon: Plus },
                ]}
                viewType="grid"
                setViewType={() => {}}
                leftActions={
                    <button onClick={() => router.back()} className="p-2 hover:bg-slate-100 dark:hover:bg-white/5 rounded-xl transition-all">
                        <ArrowLeft size={18} className="text-slate-500" />
                    </button>
                }
            />

            <main className="flex-1 overflow-y-auto p-6 lg:p-12">
                <div className="max-w-4xl mx-auto space-y-10">
                    <header>
                        <h1 className="text-4xl font-black text-slate-900 dark:text-white tracking-tighter">Crear Nuevo Programa</h1>
                        <p className="text-slate-500 mt-2">Define los parámetros básicos para el nuevo curso o diplomado.</p>
                    </header>

                    <form onSubmit={handleSubmit} className="space-y-8">
                        {/* Basic Info */}
                        <div className="bg-white dark:bg-[#15171c] rounded-[2.5rem] border border-slate-200 dark:border-white/5 p-8 lg:p-10 shadow-xl shadow-slate-200/10 dark:shadow-none space-y-8">
                            <div className="flex items-center gap-3 text-blue-600">
                                <FileText size={20} />
                                <h2 className="text-lg font-black uppercase tracking-widest">Información General</h2>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div className="space-y-2">
                                    <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 ml-4">Código del Curso</label>
                                    <input 
                                        required
                                        type="text" 
                                        placeholder="Ej: FARO-01"
                                        value={formData.code}
                                        onChange={(e) => setFormData({...formData, code: e.target.value})}
                                        className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/5 rounded-2xl px-5 py-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500/20 transition-all"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 ml-4">Título del Programa</label>
                                    <input 
                                        required
                                        type="text" 
                                        placeholder="Ej: Fundamentos de la Fe"
                                        value={formData.title}
                                        onChange={(e) => setFormData({...formData, title: e.target.value})}
                                        className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/5 rounded-2xl px-5 py-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500/20 transition-all"
                                    />
                                </div>
                                <div className="md:col-span-2 space-y-2">
                                    <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 ml-4">Descripción</label>
                                    <textarea 
                                        rows={4}
                                        placeholder="Describe de qué trata este programa..."
                                        value={formData.description}
                                        onChange={(e) => setFormData({...formData, description: e.target.value})}
                                        className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/5 rounded-2xl px-5 py-4 text-sm font-medium outline-none focus:ring-2 focus:ring-blue-500/20 transition-all resize-none"
                                    />
                                </div>
                            </div>
                        </div>

                        {/* Configuration */}
                        <div className="bg-white dark:bg-[#15171c] rounded-[2.5rem] border border-slate-200 dark:border-white/5 p-8 lg:p-10 shadow-xl shadow-slate-200/10 dark:shadow-none space-y-8">
                            <div className="flex items-center gap-3 text-purple-600">
                                <Clock size={20} />
                                <h2 className="text-lg font-black uppercase tracking-widest">Parámetros de Entrega</h2>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                                <div className="space-y-2">
                                    <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 ml-4">Modalidad</label>
                                    <select 
                                        value={formData.modality}
                                        onChange={(e) => setFormData({...formData, modality: e.target.value})}
                                        className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/5 rounded-2xl px-5 py-4 text-sm font-bold outline-none"
                                    >
                                        <option value="formal">Academia Formal</option>
                                        <option value="non_formal">Capacitación Libre</option>
                                    </select>
                                </div>
                                <div className="space-y-2">
                                    <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 ml-4">Duración (Horas)</label>
                                    <input 
                                        type="number" 
                                        value={formData.duration_hours}
                                        onChange={(e) => setFormData({...formData, duration_hours: parseInt(e.target.value)})}
                                        className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/5 rounded-2xl px-5 py-4 text-sm font-bold outline-none"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 ml-4">Tipo de Certificado</label>
                                    <input 
                                        type="text" 
                                        placeholder="Ej: Diplomado"
                                        value={formData.certificate_type}
                                        onChange={(e) => setFormData({...formData, certificate_type: e.target.value})}
                                        className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/5 rounded-2xl px-5 py-4 text-sm font-bold outline-none"
                                    />
                                </div>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4">
                                <div className="flex items-center justify-between p-4 rounded-2xl bg-slate-50 dark:bg-black/20 border border-slate-100 dark:border-white/5">
                                    <div>
                                        <p className="text-sm font-bold text-slate-800 dark:text-white">Publicar Inmediatamente</p>
                                        <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Visible en el catálogo</p>
                                    </div>
                                    <input 
                                        type="checkbox" 
                                        checked={formData.is_published}
                                        onChange={(e) => setFormData({...formData, is_published: e.target.checked})}
                                        className="size-6 rounded-lg accent-blue-600"
                                    />
                                </div>
                                <div className="flex items-center justify-between p-4 rounded-2xl bg-slate-50 dark:bg-black/20 border border-slate-100 dark:border-white/5">
                                    <div>
                                        <p className="text-sm font-bold text-slate-800 dark:text-white">Autogestionado</p>
                                        <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Sin fechas fijas de cohorte</p>
                                    </div>
                                    <input 
                                        type="checkbox" 
                                        checked={formData.is_self_paced}
                                        onChange={(e) => setFormData({...formData, is_self_paced: e.target.checked})}
                                        className="size-6 rounded-lg accent-blue-600"
                                    />
                                </div>
                            </div>
                        </div>

                        <div className="flex items-center justify-end gap-4 pt-4">
                            <button 
                                type="button"
                                onClick={() => router.back()}
                                className="px-8 py-4 text-[11px] font-black uppercase tracking-[0.2em] text-slate-400 hover:text-slate-600 transition-all"
                            >
                                Cancelar
                            </button>
                            <button 
                                type="submit"
                                disabled={loading}
                                className="px-10 py-5 bg-blue-600 text-white rounded-[2rem] font-black text-xs uppercase tracking-[0.2em] shadow-xl shadow-blue-500/20 hover:scale-105 active:scale-95 transition-all flex items-center gap-3 disabled:opacity-50 disabled:cursor-wait"
                            >
                                {loading ? 'Guardando...' : 'Crear Programa'}
                                <Save size={18} />
                            </button>
                        </div>
                    </form>
                </div>
            </main>
        </div>
    );
}
