"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { 
    ChevronLeft, 
    Save, 
    Layers, 
    BookOpen, 
    Zap, 
    Award, 
    FileText, 
    ImageIcon, 
    Settings,
    Target
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import AdminShell from '@/components/admin/AdminShell';
import AdminHero from '@/components/admin/AdminHero';

export default function NewCoursePage() {
    const router = useRouter();
    const { token } = useAuth();
    const { addToast } = useToast();
    const [loading, setLoading] = useState(false);
    const [formData, setFormData] = useState({
        title: '',
        code: '',
        description: '',
        modality: 'no_formal',
        xp_per_lesson: 10,
        passing_score: 70
    });

    const handleSave = async () => {
        if (!formData.title || !formData.code) {
            addToast('El título y código son obligatorios', 'warning');
            return;
        }
        setLoading(true);
        try {
            await apiFetch('/academy/admin/courses', {
                method: 'POST',
                token,
                body: formData
            });
            addToast('Curso creado con éxito', 'success');
            router.push('/plataforma/admin/content/list');
        } catch (err) {
            addToast('Error al crear el curso', 'error');
        } finally {
            setLoading(false);
        }
    };

    return (
        <AdminShell
            breadcrumbs={[
                { label: 'Gestión de Contenido', icon: Layers },
                { label: 'Nuevo Curso', icon: BookOpen }
            ]}
        >
            <AdminHero
                eyebrow="Academy Content"
                title="Diseñar Nueva Formación"
                description="Define la estructura, metas y recompensas para el nuevo programa académico. Configura el sistema de XP para incentivar el progreso."
                tags={['Curriculum v2', 'Gamified', 'Internal']}
                watchers={['Cuerpo Académico', 'Coordinación']}
                primaryAction={{ label: loading ? 'Guardando...' : 'Publicar Curso', icon: Save, onClick: handleSave }}
                secondaryAction={{ label: 'Cancelar', icon: ChevronLeft, onClick: () => router.back() }}
            />

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 pb-4">
                {/* Main Form Area */}
                <div className="lg:col-span-8 space-y-3">
                    <section className="bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg p-4 shadow-xl space-y-3 relative overflow-hidden">
                        <div className="absolute top-0 right-0 -mr-16 -mt-16 size-10 bg-blue-600/5 rounded-full blur-[100px]" />
                        
                        <div className="relative z-10 space-y-3">
                            <div className="flex items-center gap-3">
                                <FileText size={20} className="text-[hsl(var(--primary))]" />
                                <h3 className="text-lg font-bold tracking-tight uppercase tracking-wide">Información General</h3>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                <div className="space-y-2">
                                    <label className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide px-4">Nombre del Curso</label>
                                    <input 
                                        value={formData.title} onChange={e => setFormData({...formData, title: e.target.value})}
                                        placeholder="Ej: Fundamentos de la Fe"
                                        className="w-full bg-[hsl(var(--surface-1))] dark:bg-black/20 border border-[hsl(var(--border))] dark:border-white/5 rounded-lg py-1.5 px-3 text-sm font-semibold outline-none focus:ring-4 focus:ring-blue-500/10 transition-all"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <label className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide px-4">Código Único (ID)</label>
                                    <input 
                                        value={formData.code} onChange={e => setFormData({...formData, code: e.target.value.toUpperCase()})}
                                        placeholder="Ej: FUND-01"
                                        className="w-full bg-[hsl(var(--surface-1))] dark:bg-black/20 border border-[hsl(var(--border))] dark:border-white/5 rounded-lg py-1.5 px-3 text-sm font-semibold outline-none focus:ring-4 focus:ring-blue-500/10 transition-all uppercase"
                                    />
                                </div>
                            </div>

                            <div className="space-y-2">
                                <label className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide px-4">Descripción Pastoral</label>
                                <textarea 
                                    value={formData.description} onChange={e => setFormData({...formData, description: e.target.value})}
                                    placeholder="Describe el propósito espiritual y académico del curso..."
                                    className="w-full h-40 bg-[hsl(var(--surface-1))] dark:bg-black/20 border border-[hsl(var(--border))] dark:border-white/5 rounded-lg p-3 text-sm font-medium outline-none focus:ring-4 focus:ring-blue-500/10 transition-all resize-none"
                                />
                            </div>
                        </div>
                    </section>

                    <section className="bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg p-4 shadow-xl space-y-3">
                        <div className="flex items-center gap-3">
                            <Target size={20} className="text-[hsl(var(--primary))]" />
                            <h3 className="text-lg font-bold tracking-tight uppercase tracking-wide">Configuración Académica</h3>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                            <div className="space-y-2">
                                <label className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide px-4">Modalidad</label>
                                <select 
                                    value={formData.modality} onChange={e => setFormData({...formData, modality: e.target.value})}
                                    className="w-full bg-[hsl(var(--surface-1))] dark:bg-black/20 border border-[hsl(var(--border))] dark:border-white/5 rounded-lg py-1.5 px-3 text-sm font-semibold outline-none appearance-none"
                                >
                                    <option value="formal">Formal</option>
                                    <option value="no_formal">No Formal</option>
                                </select>
                            </div>
                            <div className="space-y-2">
                                <label className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide px-4">XP por Lección</label>
                                <input 
                                    type="number" value={formData.xp_per_lesson} onChange={e => setFormData({...formData, xp_per_lesson: parseInt(e.target.value)})}
                                    className="w-full bg-[hsl(var(--surface-1))] dark:bg-black/20 border border-[hsl(var(--border))] dark:border-white/5 rounded-lg py-1.5 px-3 text-sm font-semibold outline-none"
                                />
                            </div>
                            <div className="space-y-2">
                                <label className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide px-4">Nota de Aprobación</label>
                                <input 
                                    type="number" value={formData.passing_score} onChange={e => setFormData({...formData, passing_score: parseInt(e.target.value)})}
                                    className="w-full bg-[hsl(var(--surface-1))] dark:bg-black/20 border border-[hsl(var(--border))] dark:border-white/5 rounded-lg py-1.5 px-3 text-sm font-semibold outline-none"
                                />
                            </div>
                        </div>
                    </section>
                </div>

                {/* Sidebar Preview */}
                <aside className="lg:col-span-4 space-y-3">
                    <section className="p-4 bg-[hsl(var(--bg-muted))] rounded-lg text-white shadow-2xl space-y-3 relative overflow-hidden group">
                        <div className="absolute top-0 right-0 -mr-10 -mt-3 size-10 bg-blue-600/20 rounded-full blur-3xl" />
                        <div className="relative z-10 space-y-3">
                            <h4 className="text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--primary))]">Previsualización</h4>
                            <div className="aspect-video rounded-lg bg-white/5 border border-white/10 flex flex-col items-center justify-center gap-4 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-all cursor-pointer group">
                                <ImageIcon size={40} strokeWidth={1} className="group-hover:scale-110 transition-transform" />
                                <span className="text-[9px] font-semibold uppercase">Subir Miniatura</span>
                            </div>
                            <div>
                                <h5 className="text-xl font-semibold uppercase tracking-tight truncate">{formData.title || 'Nombre del Curso'}</h5>
                                <p className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide mt-1">{formData.code || 'ID-XXX'} • {formData.modality}</p>
                            </div>
                            <div className="flex gap-3">
                                <div className="px-3 py-1.5 bg-[hsl(var(--primary))] rounded-md text-[9px] font-semibold uppercase tracking-wide flex items-center gap-2"><Zap size={12} fill="currentColor" /> {formData.xp_per_lesson} XP</div>
                                <div className="px-3 py-1.5 bg-white/10 rounded-md text-[9px] font-semibold uppercase tracking-wide flex items-center gap-2"><Award size={12} /> Graduable</div>
                            </div>
                        </div>
                    </section>

                    <section className="bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg p-4 shadow-xl space-y-3">
                        <div className="flex items-center justify-between">
                            <h4 className="text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Resumen de Metas</h4>
                            <Settings size={18} className="text-[hsl(var(--text-secondary))]" />
                        </div>
                        <div className="space-y-3">
                            <GoalRow label="Evaluaciones Requeridas" value="1" />
                            <GoalRow label="Asistencia Mínima" value="80%" />
                            <GoalRow label="Puntaje de Corte" value={`${formData.passing_score}%`} />
                        </div>
                    </section>
                </aside>
            </div>
        </AdminShell>
    );
}

function GoalRow({ label, value }: any) {
    return (
        <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-[hsl(var(--text-secondary))] uppercase">{label}</span>
            <span className="font-semibold text-[hsl(var(--text-primary))] dark:text-white uppercase">{value}</span>
        </div>
    );
}

