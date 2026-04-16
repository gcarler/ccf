"use client";

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { 
    Heart, 
    MessageCircle, 
    Calendar, 
    CheckCircle2, 
    XCircle, 
    ChevronLeft, 
    MoreHorizontal, 
    Shield, 
    Trash2, 
    Edit3, 
    History, 
    Bot, 
    Sparkles,
    User,
    Activity,
    Quote,
    Share2
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import CrmShell from '@/components/crm/CrmShell';
import AdminHero from '@/components/admin/AdminHero';
import clsx from 'clsx';
import { motion, AnimatePresence } from 'framer-motion';

const EMOTION_OPTIONS = ['Sanidad', 'Provisión', 'Restauración', 'Fe', 'Familia', 'Finanzas', 'Otro'];

export default function TestimonialDetailPage() {
    const { id } = useParams();
    const router = useRouter();
    const { token } = useAuth();
    const { addToast } = useToast();

    const [testimonial, setTestimonial] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('moderacion');
    const [isSaving, setIsSaving] = useState(false);

    const fetchTestimonial = useCallback(async () => {
        if (!token || !id) return;
        setLoading(true);
        try {
            // Usually we fetch all and find, or there's a specific endpoint
            const data = await apiFetch<any[]>(`/cms/testimonials`, { token });
            const found = data.find(t => t.id.toString() === id);
            
            if (found) {
                setTestimonial({
                    ...found,
                    published: found.published ?? found.is_approved ?? false,
                    logs: [
                        { id: 1, action: 'Recibido vía Web', date: 'Hace 3 días', user: 'Faro Bot' },
                        { id: 2, action: 'Asignado a Moderación', date: 'Hace 2 días', user: 'Sistema' }
                    ]
                });
            } else {
                addToast('Testimonio no encontrado', 'error');
            }
        } catch (err) {
            addToast('Error al cargar el testimonio', 'error');
        } finally {
            setLoading(false);
        }
    }, [token, id, addToast]);

    useEffect(() => { fetchTestimonial(); }, [fetchTestimonial]);

    const handleUpdate = async (updates: any) => {
        setIsSaving(true);
        try {
            const nextPublished = updates.published !== undefined ? updates.published : testimonial.published;
            const nextEmotion = updates.emotion || testimonial.emotion;
            const nextContent = updates.content || testimonial.content;

            await apiFetch(`/admin/testimonials/${id}`, {
                method: 'PATCH',
                token,
                body: { 
                    is_approved: nextPublished,
                    emotion: nextEmotion,
                    content: nextContent
                }
            });

            setTestimonial((prev: any) => ({ 
                ...prev, 
                ...updates,
                published: nextPublished
            }));
            addToast('Testimonio actualizado', 'success');
        } catch {
            addToast('Error al actualizar testimonio', 'error');
        } finally {
            setIsSaving(false);
        }
    };

    if (loading) return (
        <CrmShell breadcrumbs={[{ label: 'CMS', icon: Heart }, { label: 'Testimonios', icon: MessageCircle }, { label: 'Cargando...' }]}>
            <div className="flex flex-col items-center justify-center h-full space-y-4">
                <Heart size={48} className="text-rose-500 animate-pulse opacity-20" />
                <p className="text-[10px] font-black text-slate-400 tracking-[0.4em] uppercase">Validando Testimonio...</p>
            </div>
        </CrmShell>
    );

    if (!testimonial) return (
        <CrmShell breadcrumbs={[{ label: 'CMS', icon: Heart }, { label: 'Testimonios', icon: MessageCircle }, { label: 'Error' }]}>
            <div className="p-12 text-center">
                <h1 className="text-2xl font-black italic uppercase">Registro Extraviado</h1>
                <p className="text-slate-500 mt-2">No se encontró el testimonio bajo este identificador.</p>
                <button onClick={() => router.push('/cms/testimonials')} className="mt-6 px-8 py-3 bg-rose-600 text-white rounded-2xl text-[10px] font-black uppercase tracking-widest">Regresar al Panel</button>
            </div>
        </CrmShell>
    );

    return (
        <CrmShell
            breadcrumbs={[
                { label: 'CCF', icon: Heart },
                { label: 'CMS Moderation', icon: Shield },
                { label: 'Testimonios', icon: MessageCircle },
                { label: 'Expediente', icon: Activity }
            ]}
        >
            <div className="flex flex-col h-full bg-[#fbf9f9] dark:bg-[#0d0c0c]">
                
                {/* ─── Hero / Navigation ─── */}
                <div className="px-6 py-4">
                    <button 
                        onClick={() => router.push('/cms/testimonials')}
                        className="flex items-center gap-1.5 text-slate-400 hover:text-rose-600 transition-colors text-[10px] font-black uppercase tracking-widest mb-4"
                    >
                        <ChevronLeft size={14} /> Gestión de Testimonios
                    </button>

                    <AdminHero 
                        eyebrow={`ID: #${id} · FECHA: ${new Date(testimonial.created_at).toLocaleDateString()}`}
                        title="Verificación de Testimonio"
                        description="Revisa el contenido, ajusta la categoría emocional y aprueba la publicación en el muro de fe."
                        tags={[testimonial.emotion || 'Sin Categoría', testimonial.published ? 'Publicado' : 'Pendiente']}
                        watchers={['Comunicación', 'Pastoral']}
                        primaryAction={{ 
                            label: testimonial.published ? 'Retirar de Publicación' : 'Aprobar Historia', 
                            icon: testimonial.published ? XCircle : CheckCircle2, 
                            onClick: () => handleUpdate({ published: !testimonial.published }) 
                        }}
                        secondaryAction={{
                            label: 'Compartir en RRSS',
                            icon: Share2,
                            onClick: () => addToast('Preparando asset para redes sociales...', 'info')
                        }}
                    />
                </div>

                {/* ─── Tabs & Content ─── */}
                <div className="flex-1 px-6 pb-6 overflow-y-auto">
                    <div className="max-w-7xl mx-auto space-y-6">
                        
                        <div className="flex items-center gap-8 border-b border-slate-200 dark:border-white/5 mb-6">
                            {[
                                { id: 'moderacion', label: 'Curación de Contenido', icon: Edit3 },
                                { id: 'logs', label: 'Historial de Moderación', icon: History },
                                { id: 'impacto', label: 'Ecosistema de Impacto', icon: Sparkles },
                            ].map(tab => (
                                <button
                                    key={tab.id}
                                    onClick={() => setActiveTab(tab.id)}
                                    className={clsx(
                                        "flex items-center gap-2 py-4 text-[11px] font-black uppercase tracking-widest transition-all relative",
                                        activeTab === tab.id ? "text-rose-600" : "text-slate-400 hover:text-slate-600"
                                    )}
                                >
                                    <tab.icon size={14} />
                                    {tab.label}
                                    {activeTab === tab.id && (
                                        <motion.div layoutId="test-tab-underline" className="absolute bottom-0 left-0 right-0 h-0.5 bg-rose-600" />
                                    )}
                                </button>
                            ))}
                        </div>

                        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                            
                            {/* Main Content Column */}
                            <div className="lg:col-span-8 space-y-6">
                                <AnimatePresence mode="wait">
                                    {activeTab === 'moderacion' && (
                                        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="space-y-6">
                                            
                                            {/* Content Area */}
                                            <div className="bg-white dark:bg-white/5 p-8 rounded-[3rem] border border-slate-200 dark:border-white/10 shadow-sm space-y-6">
                                                <div className="flex items-center justify-between">
                                                    <h3 className="text-[11px] font-black uppercase tracking-widest text-slate-400 flex items-center gap-2">
                                                        <Quote size={14} className="text-rose-500" /> Historia Escrita
                                                    </h3>
                                                    <p className="text-[10px] font-bold text-slate-400">{testimonial.content.length} caracteres</p>
                                                </div>
                                                
                                                <textarea 
                                                    value={testimonial.content}
                                                    onChange={(e) => setTestimonial({ ...testimonial, content: e.target.value })}
                                                    rows={8}
                                                    className="w-full px-6 py-6 rounded-[2rem] bg-slate-50 dark:bg-black/20 border border-slate-100 dark:border-white/5 outline-none focus:ring-2 focus:ring-rose-500/20 text-lg font-medium leading-relaxed italic"
                                                />

                                                <button 
                                                    onClick={() => handleUpdate({ content: testimonial.content })}
                                                    disabled={isSaving}
                                                    className="w-full py-4 bg-slate-900 text-white dark:bg-white dark:text-black rounded-2xl text-[11px] font-black uppercase tracking-widest flex items-center justify-center gap-2"
                                                >
                                                    {isSaving ? 'Guardando...' : 'Aplicar Edición de Curación'}
                                                </button>
                                            </div>

                                            {/* Tags and Metadata */}
                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                                <div className="p-6 bg-white dark:bg-white/5 rounded-3xl border border-slate-200 dark:border-white/10 shadow-sm space-y-4">
                                                    <h4 className="text-[10px] font-black uppercase tracking-widest text-slate-400">Autoría</h4>
                                                    <div className="flex items-center gap-4">
                                                        <div className="size-12 rounded-2xl bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-400">
                                                            <User size={24} />
                                                        </div>
                                                        <div>
                                                            <p className="text-sm font-black">Usuario ID: {testimonial.author_id}</p>
                                                            <p className="text-[10px] text-slate-400 font-bold uppercase">Miembro de Comunidad</p>
                                                        </div>
                                                    </div>
                                                </div>
                                                <div className="p-6 bg-white dark:bg-white/5 rounded-3xl border border-slate-200 dark:border-white/10 shadow-sm space-y-4">
                                                    <h4 className="text-[10px] font-black uppercase tracking-widest text-slate-400">Categoría Emocional</h4>
                                                    <div className="flex flex-wrap gap-2">
                                                        {EMOTION_OPTIONS.map(opt => (
                                                            <button
                                                                key={opt}
                                                                onClick={() => handleUpdate({ emotion: opt })}
                                                                className={clsx(
                                                                    "px-3 py-1.5 rounded-xl text-[10px] font-black uppercase tracking-widest border transition-all",
                                                                    testimonial.emotion === opt 
                                                                        ? "bg-rose-50 border-rose-200 text-rose-600"
                                                                        : "bg-transparent border-slate-200 dark:border-white/10 text-slate-400 hover:border-rose-400/30"
                                                                )}
                                                            >
                                                                {opt}
                                                            </button>
                                                        ))}
                                                    </div>
                                                </div>
                                            </div>
                                        </motion.div>
                                    )}

                                    {activeTab === 'logs' && (
                                        <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="space-y-4">
                                            <div className="relative pl-8 space-y-8 before:absolute before:left-3 before:top-2 before:bottom-2 before:w-px before:bg-slate-200 dark:before:bg-white/10">
                                                {(testimonial.logs || []).map((log: any) => (
                                                    <div key={log.id} className="relative">
                                                        <div className="absolute -left-[25px] top-1 size-4 rounded-full border-4 border-slate-50 dark:border-[#0d0c0c] bg-rose-600" />
                                                        <div className="bg-white dark:bg-white/5 p-5 rounded-3xl border border-slate-200 dark:border-white/10 shadow-sm">
                                                            <div className="flex items-center justify-between mb-2">
                                                                <span className="text-[10px] font-black uppercase tracking-widest text-rose-600">{log.action}</span>
                                                                <span className="text-[10px] font-bold text-slate-400">{log.date}</span>
                                                            </div>
                                                            <p className="text-xs text-slate-500 font-bold uppercase tracking-widest">por {log.user}</p>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </motion.div>
                                    )}
                                </AnimatePresence>
                            </div>

                            {/* Sidebar Column */}
                            <div className="lg:col-span-4 space-y-6">
                                
                                {/* Status Toggle Card */}
                                <div className="p-8 bg-white dark:bg-white/5 rounded-[3rem] border border-slate-200 dark:border-white/10 shadow-sm space-y-6 text-center">
                                    <div className={clsx(
                                        "size-20 mx-auto rounded-full flex items-center justify-center transition-all duration-500",
                                        testimonial.published ? "bg-emerald-500 text-white shadow-xl shadow-emerald-500/20" : "bg-amber-100 text-amber-600"
                                    )}>
                                        {testimonial.published ? <CheckCircle2 size={32} /> : <XCircle size={32} />}
                                    </div>
                                    <div>
                                        <h4 className="text-xl font-black uppercase italic tracking-tighter">
                                            {testimonial.published ? 'Historia Publicada' : 'Pendiente de Aprobación'}
                                        </h4>
                                        <p className="text-xs text-slate-500 font-medium mt-1">
                                            {testimonial.published 
                                                ? 'Visible para todos los miembros de la red.' 
                                                : 'En espera de ser curada para muro de noticias.'}
                                        </p>
                                    </div>
                                    <button 
                                        onClick={() => handleUpdate({ published: !testimonial.published })}
                                        className={clsx(
                                            "w-full py-4 rounded-2xl text-[11px] font-black uppercase tracking-widest transition-all",
                                            testimonial.published 
                                                ? "bg-rose-50 text-rose-600 border border-current hover:bg-rose-100" 
                                                : "bg-emerald-600 text-white shadow-xl shadow-emerald-600/20 hover:bg-emerald-700"
                                        )}
                                    >
                                        {testimonial.published ? 'Retirar del Sitio' : 'Autorizar Publicación'}
                                    </button>
                                </div>

                                {/* Insight Card */}
                                <div className="p-8 bg-gradient-to-br from-indigo-900 to-indigo-700 text-white rounded-[3rem] shadow-2xl relative overflow-hidden group">
                                    <Bot size={100} className="absolute -bottom-4 -right-4 opacity-10 rotate-12 transition-transform group-hover:scale-110" />
                                    <h3 className="text-[11px] font-black uppercase tracking-[0.4em] text-indigo-200 mb-4 flex items-center gap-2">
                                        <Bot size={14} /> Optimus Brain
                                    </h3>
                                    <p className="text-sm font-medium leading-relaxed italic opacity-90">
                                        "Este testimonio tiene un alto índice de 'Sentimiento Positivo'. Es un excelente candidato para el boletín mensual de la academia."
                                    </p>
                                    <button className="mt-6 w-full py-3 bg-white/10 hover:bg-white/20 rounded-2xl text-[10px] font-black uppercase tracking-widest border border-white/20 transition-all">
                                        Agendar al Boletín
                                    </button>
                                </div>

                                <div className="p-4 flex items-center justify-center gap-4 text-slate-400">
                                    <button className="p-2 hover:text-rose-600 transition-colors"><Trash2 size={18} /></button>
                                    <div className="w-px h-4 bg-slate-200 dark:bg-white/10" />
                                    <button className="p-2 hover:text-blue-600 transition-colors"><Edit3 size={18} /></button>
                                </div>

                            </div>

                        </div>
                    </div>
                </div>
            </div>
        </CrmShell>
    );
}
