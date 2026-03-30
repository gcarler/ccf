"use client";

import React, { useEffect, useMemo, useState, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import AdminHero from '@/components/admin/AdminHero';
import CommunityToolbarChip from '@/components/community/ToolbarChip';
import TestimonialForm from '@/components/TestimonialForm';
import { Heart, MessageCircle, Calendar, CheckCircle2, XCircle, Link as LinkIcon } from 'lucide-react';

interface Testimonial {
    id: number;
    content: string;
    emotion: string;
    created_at: string;
    author_id: number;
    published?: boolean;
    is_approved?: boolean;
}

const emotionFilters = ['Todos', 'Sanidad', 'Provisión', 'Restauración', 'Fe'];

export default function CmsTestimonialsPage() {
    const { user, token, isAuthenticated } = useAuth();
    const [testimonials, setTestimonials] = useState<Testimonial[]>([]);
    const [filter, setFilter] = useState('Todos');
    const [loading, setLoading] = useState(true);
    const [showForm, setShowForm] = useState(false);

    const fetchTestimonials = useCallback(async () => {
        if (!token) {
            setLoading(false);
            return;
        }
        setLoading(true);
        try {
            const data = await apiFetch<Testimonial[]>('/cms/testimonials', { token, cache: 'no-store' });
            setTestimonials(
                Array.isArray(data)
                    ? data.map((row) => ({ ...row, published: row.published ?? row.is_approved ?? false }))
                    : []
            );
        } catch (error) {
            console.error('cms testimonials fetch', error);
            setTestimonials([]);
        } finally {
            setLoading(false);
        }
    }, [token]);

    useEffect(() => {
        fetchTestimonials();
    }, [fetchTestimonials]);

    const filtered = useMemo(() => {
        if (filter === 'Todos') return testimonials;
        return testimonials.filter((item) => item.emotion?.toLowerCase() === filter.toLowerCase());
    }, [testimonials, filter]);

    const handleTogglePublish = async (testimonial: Testimonial) => {
        if (!token) return;
        const nextPublished = !testimonial.published;
        setTestimonials((prev) => prev.map((item) => (item.id === testimonial.id ? { ...item, published: nextPublished } : item)));
        try {
            await apiFetch(`/admin/testimonials/${testimonial.id}`, {
                method: 'PATCH',
                token,
                body: { is_approved: nextPublished }
            });
        } catch {
            setTestimonials((prev) => prev.map((item) => (item.id === testimonial.id ? { ...item, published: testimonial.published } : item)));
        }
    };

    if (!isAuthenticated) {
        return (
            <div className="max-w-3xl mx-auto py-24 text-center space-y-3">
                <h1 className="text-3xl font-black">Inicia sesión</h1>
                <p className="text-slate-500">Necesitas una sesión válida para administrar los testimonios.</p>
            </div>
        );
    }

    return (
        <div className="space-y-8 px-4 py-8">
            <AdminHero
                eyebrow="Testimonios"
                title="Gestión de testimonios"
                description="Aprueba historias, categoriza emociones y prepara contenido curado para el sitio público."
                tags={['Sanidad', 'Provisión', 'Restauración']}
                watchers={['Equipo Comunicación', 'Optimus Brain']}
                primaryAction={{ label: showForm ? 'Cerrar formulario' : 'Agregar testimonio', icon: MessageCircle, onClick: () => setShowForm((prev) => !prev) }}
                secondaryAction={{ label: 'Abrir muro público', icon: LinkIcon, onClick: () => window.open('/testimonios', '_blank') }}
            />

            {showForm && (
                <div className="rounded-[2.5rem] border border-slate-200 dark:border-white/5 bg-white dark:bg-[#111418] p-6">
                    <TestimonialForm userId={user?.id || 0} token={token || ''} onSubmitted={() => { setShowForm(false); fetchTestimonials(); }} />
                </div>
            )}

            <div className="rounded-[2.5rem] border border-slate-200 dark:border-white/5 bg-white dark:bg-[#111418] shadow-xl">
                <div className="flex flex-wrap items-center gap-2 p-6 border-b border-slate-100 dark:border-white/5">
                    {emotionFilters.map((option) => (
                        <CommunityToolbarChip
                            key={option}
                            label={option}
                            active={filter === option}
                            variant={filter === option ? 'solid' : 'outline'}
                            onClick={() => setFilter(option)}
                        />
                    ))}
                </div>

                {loading ? (
                    <p className="px-6 py-10 text-sm text-slate-500">Cargando testimonios...</p>
                ) : filtered.length === 0 ? (
                    <div className="px-6 py-16 text-center text-slate-400 space-y-3">
                        <Heart className="w-10 h-10 mx-auto text-slate-300" />
                        <p className="font-bold">No hay historias en esta categoría.</p>
                    </div>
                ) : (
                    <div className="px-6 py-8 space-y-4">
                        {filtered.map((testimony) => (
                            <article key={testimony.id} className="border border-slate-100 dark:border-white/10 rounded-[2rem] p-5 hover:border-primary/30 transition-colors">
                                <div className="flex items-center justify-between mb-4">
                                    <div className="flex flex-col">
                                        <p className="text-[10px] font-bold uppercase tracking-[0.35em] text-primary flex items-center gap-2">
                                            <Heart size={14} /> {testimony.emotion || 'Sin categoría'}
                                        </p>
                                        <p className="text-[11px] text-slate-400 uppercase tracking-[0.3em] flex items-center gap-2">
                                            <Calendar size={12} /> {new Date(testimony.created_at).toLocaleDateString('es-MX')}
                                        </p>
                                    </div>
                                    <button
                                        onClick={() => handleTogglePublish(testimony)}
                                        className={`inline-flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.35em] px-3 py-1.5 rounded-full border transition-colors ${
                                            testimony.published
                                                ? 'text-emerald-500 border-emerald-200 bg-emerald-50'
                                                : 'text-amber-500 border-amber-200 bg-amber-50'
                                        }`}
                                    >
                                        {testimony.published ? <CheckCircle2 size={12} /> : <XCircle size={12} />}
                                        {testimony.published ? 'Publicado' : 'Borrador'}
                                    </button>
                                </div>
                                <p className="text-slate-700 dark:text-slate-200 text-sm leading-relaxed">{testimony.content}</p>
                            </article>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
