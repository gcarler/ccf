"use client";

import React, { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { 
    Layout, 
    Quote, 
    CheckCircle2,
    XCircle,
    User,
    Calendar,
    Star,
    MessageSquare,
    Shield
} from 'lucide-react';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { DSCard } from '@/design/components/DSCard';
import { DSBadge } from '@/design/components/DSBadge';
import { toast } from 'sonner';
import clsx from 'clsx';

export default function CmsTestimonialDetailPage() {
    const params = useParams();
    const id = params?.id as string;
    const { token } = useAuth();
    
    const [testimonial, setTestimonial] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!token || !id) return;
        const loadTestimonial = async () => {
            try {
                setLoading(true);
                const data = await apiFetch<any>(`/admin/testimonials/${id}`, { token }).catch(() => null);
                const normalized = data ? {
                    ...data,
                    author_name: data.author?.username || (data.author_id ? `Miembro #${data.author_id}` : 'Anonimo'),
                    author_role: 'Miembro de la comunidad',
                    status: data.is_approved ? 'approved' : 'pending',
                    rating: 5,
                    category: data.emotion || 'Testimonio',
                } : null;
                setTestimonial(normalized);
            } catch (err) {
                toast.error('Error al cargar detalle del testimonio');
            } finally {
                setLoading(false);
            }
        };
        loadTestimonial();
    }, [id, token]);

    const handleAction = async (newStatus: string) => {
        try {
            const isApproved = newStatus === 'approved';
            const updated = await apiFetch<any>(`/admin/testimonials/${id}`, {
                method: 'PATCH',
                token,
                body: { is_approved: isApproved },
            });
            setTestimonial({
                ...testimonial,
                ...updated,
                status: isApproved ? 'approved' : 'pending',
            });
            toast.success(`Testimonio ${newStatus === 'approved' ? 'aprobado' : 'rechazado'}`);
        } catch (err) {
            toast.error('Error al actualizar estado');
        }
    };

    if (loading) return <div className="p-20 text-center animate-pulse font-black uppercase tracking-widest text-slate-400">Verificando Testimonio...</div>;
    if (!testimonial) return <div className="p-20 text-center font-black uppercase tracking-widest text-slate-400">Testimonio no encontrado.</div>;

    return (
        <div className="flex flex-col h-full bg-[#f8fafc] dark:bg-[#0b0d11] overflow-hidden">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: 'CMS', icon: Layout, href: '/cms' },
                    { label: 'Testimonios', icon: Quote, href: '/cms/testimonials' },
                    { label: testimonial.author_name, icon: User },
                ]}
            />

            <main className="flex-1 overflow-y-auto p-8 lg:p-12">
                <div className="max-w-4xl mx-auto space-y-8">
                    <header className="flex flex-col md:flex-row md:items-end justify-between gap-6">
                        <div className="space-y-4">
                            <div className="flex items-center gap-3">
                                <DSBadge tone="violet" label={testimonial.category.toUpperCase()} />
                                <DSBadge tone={testimonial.status === 'approved' ? 'emerald' : 'amber'} label={testimonial.status.toUpperCase()} />
                            </div>
                            <h1 className="text-4xl font-black text-slate-900 dark:text-white tracking-tight leading-none uppercase">
                                Moderación de Testimonio
                            </h1>
                        </div>
                        <div className="flex items-center gap-3">
                            <button 
                                onClick={() => handleAction('rejected')}
                                className="px-6 py-2 border border-slate-200 dark:border-white/10 text-slate-500 rounded-xl text-[10px] font-black uppercase tracking-widest hover:bg-rose-500 hover:text-white hover:border-rose-500 transition-all flex items-center gap-2"
                            >
                                <XCircle size={14} /> Rechazar
                            </button>
                            <button 
                                onClick={() => handleAction('approved')}
                                className="px-6 py-2 bg-emerald-600 text-white rounded-xl text-[10px] font-black uppercase tracking-widest shadow-lg shadow-emerald-500/20 hover:scale-105 transition-all flex items-center gap-2"
                            >
                                <CheckCircle2 size={14} /> Aprobar para Web
                            </button>
                        </div>
                    </header>

                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                        <div className="lg:col-span-2 space-y-8">
                            <DSCard>
                                <div className="space-y-6 relative">
                                    <Quote size={48} className="absolute -top-4 -left-4 text-blue-500/10 -z-0" />
                                    <div className="flex items-center gap-1 mb-2">
                                        {[1, 2, 3, 4, 5].map(star => (
                                            <Star key={star} size={16} className={clsx(star <= testimonial.rating ? 'text-amber-400 fill-amber-400' : 'text-slate-200')} />
                                        ))}
                                    </div>
                                    <p className="text-xl font-medium text-slate-700 dark:text-slate-200 italic leading-relaxed relative z-10">
                                        &quot;{testimonial.content}&quot;
                                    </p>
                                </div>
                            </DSCard>

                            <DSCard>
                                <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-6">Información del Autor</h3>
                                <div className="flex items-center gap-6">
                                    <div className="size-16 rounded-3xl bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-400">
                                        <User size={32} />
                                    </div>
                                    <div>
                                        <h4 className="text-lg font-black text-slate-900 dark:text-white uppercase tracking-tight">{testimonial.author_name}</h4>
                                        <p className="text-xs font-bold text-blue-600 uppercase tracking-widest">{testimonial.author_role}</p>
                                    </div>
                                </div>
                            </DSCard>
                        </div>

                        <aside className="space-y-6">
                            <DSCard>
                                <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-6">Detalles de Envío</h3>
                                <div className="space-y-4">
                                    <div className="space-y-1">
                                        <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Fecha de Recepción</p>
                                        <p className="text-xs font-bold flex items-center gap-2">
                                            <Calendar size={14} /> {new Date(testimonial.created_at).toLocaleString()}
                                        </p>
                                    </div>
                                    <div className="space-y-1">
                                        <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Origen</p>
                                        <p className="text-xs font-bold flex items-center gap-2">
                                            <MessageSquare size={14} /> Formulario Comunidad
                                        </p>
                                    </div>
                                    <div className="h-px bg-slate-100 dark:bg-white/5" />
                                    <div className="flex items-center gap-2 text-[10px] font-black text-slate-400 uppercase tracking-widest">
                                        <Shield size={12} /> ID: {testimonial.id}
                                    </div>
                                </div>
                            </DSCard>
                        </aside>
                    </div>
                </div>
            </main>
        </div>
    );
}
