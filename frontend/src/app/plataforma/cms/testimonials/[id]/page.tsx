"use client";

import React, { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import OptimizedImage from "@/components/ui/OptimizedImage";
import {
    Layout,
    Quote,
    CheckCircle2,
    Archive,
    RotateCcw,
    Headphones,
    ImageIcon,
    PlayCircle,
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

interface TestimonialData {
  id: string;
  created_at?: string;
  author_name?: string;
  author?: { username?: string };
  author_persona_id?: string;
  content?: string;
  media_type?: string;
  image_url?: string;
  media_url?: string;
  video_url?: string;
  podcast_url?: string;
  is_featured?: boolean;
  status?: string;
  category?: string;
  rating?: number;
  author_role?: string;
  show_on_home?: boolean;
  is_approved?: boolean;
  emotion?: string;
}

function getTestimonialMediaUrl(testimonial: TestimonialData | null): string {
    if (!testimonial) return '';
    if (testimonial.media_type === 'image') return testimonial.image_url || testimonial.media_url || '';
    if (testimonial.media_type === 'video') return testimonial.video_url || testimonial.media_url || '';
    if (testimonial.media_type === 'podcast') return testimonial.podcast_url || testimonial.media_url || '';
    return testimonial.media_url || testimonial.image_url || testimonial.video_url || testimonial.podcast_url || '';
}

export default function CmsTestimonialDetailPage() {
    const params = useParams();
    const id = params?.id as string;
    const { token } = useAuth();
    
    const [testimonial, setTestimonial] = useState<TestimonialData | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!token || !id) return;
        const loadTestimonial = async () => {
            try {
                setLoading(true);
                const data = await apiFetch<TestimonialData>(`/admin/testimonials/${id}`, { token }).catch(() => null);
                const authorPersonaId = data?.author_persona_id ? String(data.author_persona_id) : null;
                const normalized = data ? {
                    ...data,
                    author_name: data.author?.username || (authorPersonaId ? `Persona ${authorPersonaId.slice(0, 8)}` : 'Anonimo'),
                    author_role: 'Persona de la comunidad',
                    status: data.status || (data.is_approved ? 'approved' : 'pending'),
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
            if (newStatus === 'archived') {
                await apiFetch(`/admin/testimonials/${id}`, { method: 'DELETE', token });
                setTestimonial({ ...testimonial, is_approved: false, show_on_home: false, status: 'archived' });
            } else {
                const updated = await apiFetch<any>(`/admin/testimonials/${id}`, {
                    method: 'PATCH',
                    token,
                    body: { status: newStatus },
                });
                setTestimonial({
                    ...testimonial,
                    ...updated,
                    status: updated.status || newStatus,
                });
            }
            toast.success(`Testimonio ${newStatus === 'approved' ? 'aprobado' : newStatus === 'archived' ? 'archivado' : 'restaurado'}`);
        } catch (err) {
            toast.error('Error al actualizar estado');
        }
    };

    if (loading) return <div className="p-4 text-center animate-pulse font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Verificando Testimonio...</div>;
    if (!testimonial) return <div className="p-4 text-center font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Testimonio no encontrado.</div>;

    const mediaUrl = getTestimonialMediaUrl(testimonial);

    return (
        <div className="flex flex-col h-full bg-[#f8fafc] dark:bg-[#0b0d11] overflow-hidden">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: 'CMS', icon: Layout, href: '/plataforma/cms' },
                    { label: 'Testimonios', icon: Quote, href: '/plataforma/cms/testimonials' },
                    { label: testimonial.author_name, icon: User },
                ]}
            />

            <main className="flex-1 overflow-y-auto p-4 lg:p-4">
 <div className="w-full space-y-3">
                    <header className="flex flex-col md:flex-row md:items-end justify-between gap-3">
                        <div className="space-y-4">
                            <div className="flex items-center gap-3">
                                <DSBadge tone="blue" label={testimonial.category.toUpperCase()} />
                                <DSBadge tone={testimonial.status === 'approved' ? 'emerald' : testimonial.status === 'archived' ? 'slate' : 'amber'} label={testimonial.status.toUpperCase()} />
                            </div>
                            <h1 className="text-xl font-semibold text-[hsl(var(--text-primary))] dark:text-white tracking-tight leading-none uppercase">
                                Moderación de Testimonio
                            </h1>
                        </div>
                        <div className="flex items-center gap-3">
                            <button 
                                onClick={() => handleAction(testimonial.status === 'archived' ? 'pending' : 'archived')}
                                className="px-3 py-2 border border-[hsl(var(--border))] dark:border-white/10 text-[hsl(var(--text-secondary))] rounded-md text-[10px] font-semibold uppercase tracking-wide hover:bg-rose-500 hover:text-white hover:border-rose-500 transition-all flex items-center gap-2"
                            >
                                {testimonial.status === 'archived' ? <RotateCcw size={14} /> : <Archive size={14} />}
                                {testimonial.status === 'archived' ? 'Restaurar' : 'Archivar'}
                            </button>
                            <button 
                                onClick={() => handleAction('approved')}
                                disabled={testimonial.status === 'archived'}
                                className="px-3 py-2 bg-emerald-600 text-white rounded-md text-[10px] font-semibold uppercase tracking-wide shadow-lg shadow-emerald-500/20 hover:scale-105 transition-all flex items-center gap-2"
                            >
                                <CheckCircle2 size={14} /> Aprobar para Web
                            </button>
                        </div>
                    </header>

                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
                        <div className="lg:col-span-2 space-y-3">
                            {mediaUrl && (
                                <DSCard>
                                    <div className="mb-4 flex items-center gap-2">
                                        {testimonial.media_type === 'video' ? <PlayCircle size={16} className="text-rose-500" /> : testimonial.media_type === 'podcast' ? <Headphones size={16} className="text-amber-500" /> : <ImageIcon size={16} className="text-[hsl(var(--primary))]" />}
                                        <h3 className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                                            Media asociada
                                        </h3>
                                    </div>
                                    <div className="overflow-hidden rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--bg-muted))] dark:border-white/10">
                                        {testimonial.media_type === 'image' ? (
                                            <OptimizedImage src={mediaUrl} alt="" fill sizes="(max-width: 768px) 100vw, 600px" className="max-h-[420px] w-full object-contain" />
                                        ) : testimonial.media_type === 'video' ? (
                                            <video controls className="w-full bg-black">
                                                <source src={mediaUrl} />
                                            </video>
                                        ) : (
                                            <div className="space-y-4 bg-[hsl(var(--bg-primary))] p-3 dark:bg-white/5">
                                                <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Podcast / audio testimonial</p>
                                                <audio controls src={mediaUrl} className="w-full" />
                                            </div>
                                        )}
                                    </div>
                                </DSCard>
                            )}

                            <DSCard>
                                <div className="space-y-3 relative">
                                    <Quote size={48} className="absolute -top-4 -left-4 text-blue-500/10 -z-0" />
                                    <div className="flex items-center gap-1 mb-2">
                                        {[1, 2, 3, 4, 5].map(star => (
                                            <Star key={star} size={16} className={clsx(star <= testimonial.rating ? 'text-amber-400 fill-amber-400' : 'text-[hsl(var(--text-secondary))]')} />
                                        ))}
                                    </div>
                                    <p className="text-xl font-medium text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] italic leading-relaxed relative z-10">
                                        &quot;{testimonial.content}&quot;
                                    </p>
                                </div>
                            </DSCard>

                            <DSCard>
                                <h3 className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-3">Información del Autor</h3>
                                <div className="flex items-center gap-3">
                                    <div className="size-8 rounded-lg bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center text-[hsl(var(--text-secondary))]">
                                        <User size={32} />
                                    </div>
                                    <div>
                                        <h4 className="text-lg font-semibold text-[hsl(var(--text-primary))] dark:text-white uppercase tracking-tight">{testimonial.author_name}</h4>
                                        <p className="text-xs font-bold text-[hsl(var(--primary))] uppercase tracking-wide">{testimonial.author_role}</p>
                                    </div>
                                </div>
                            </DSCard>
                        </div>

                        <aside className="space-y-3">
                            <DSCard>
                                <h3 className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-3">Detalles de Envío</h3>
                                <div className="space-y-4">
                                    <div className="space-y-1">
                                        <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Fecha de Recepción</p>
                                        <p className="text-xs font-bold flex items-center gap-2">
                                            <Calendar size={14} /> {new Date(testimonial.created_at).toLocaleString()}
                                        </p>
                                    </div>
                                    <div className="space-y-1">
                                        <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Origen</p>
                                        <p className="text-xs font-bold flex items-center gap-2">
                                            <MessageSquare size={14} /> Formulario Comunidad
                                        </p>
                                    </div>
                                    <div className="h-px bg-[hsl(var(--surface-2))] dark:bg-white/5" />
                                    <div className="flex items-center gap-2 text-[10px] font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">
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
