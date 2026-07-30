"use client";

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { DSCard, DSBadge } from '@/design';
import { toast } from 'sonner';
import {
    User,
    Calendar,
    Star,
    ArrowLeft,
    CheckCircle2,
    Archive,
} from 'lucide-react';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import clsx from 'clsx';

interface TestimonialData {
  id: string;
  slug?: string;
  created_at?: string;
  author_name?: string;
  author?: { username?: string };
  author_persona_id?: string | null;
  content?: string;
  media_type?: string;
  image_url?: string | null;
  media_url?: string | null;
  video_url?: string | null;
  podcast_url?: string | null;
  is_featured?: boolean;
  status?: string;
  category?: string;
  rating?: number;
  author_role?: string;
  show_on_home?: boolean;
  is_approved?: boolean;
  emotion?: string;
}

export default function CmsTestimonialDetailByIdPage() {
    const params = useParams();
    const router = useRouter();
    const id = params?.id as string;
    const { token } = useAuth();

    const [testimonial, setTestimonial] = useState<TestimonialData | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!token || !id) return;
        const load = async () => {
            try {
                setLoading(true);
                const data = await apiFetch<TestimonialData>(
                    `/cms/testimonials/${id}`,
                    { headers: { Authorization: `Bearer ${token}` } }
                ).catch(() => null);
                setTestimonial(data);
            } catch {
                toast.error('No se pudo cargar el testimonio');
            } finally {
                setLoading(false);
            }
        };
        load();
    }, [id, token]);

    const handleApprove = async () => {
        if (!testimonial || !token) return;
        try {
            await apiFetch(`/cms/testimonials/${testimonial.id}`, {
                method: 'PATCH',
                headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: 'published' }),
            });
            setTestimonial(t => t ? { ...t, status: 'published' } : t);
            toast.success('Testimonio aprobado');
        } catch {
            toast.error('Error al aprobar');
        }
    };

    const handleArchive = async () => {
        if (!testimonial || !token) return;
        try {
            await apiFetch(`/cms/testimonials/${testimonial.id}`, {
                method: 'PATCH',
                headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: 'archived' }),
            });
            toast.success('Testimonio archivado');
            router.push('/plataforma/cms/testimonials');
        } catch {
            toast.error('Error al archivar');
        }
    };

    return (
        <div className="flex h-full flex-col">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: 'CMS', href: '/plataforma/cms' },
                    { label: 'Testimonios', href: '/plataforma/cms/testimonials' },
                    { label: testimonial?.author_name || id },
                ]}
            />
            <main className="flex-1 overflow-auto p-6">
                {loading ? (
                    <div className="flex h-40 items-center justify-center text-sm text-[hsl(var(--text-secondary))]">
                        Cargando…
                    </div>
                ) : !testimonial ? (
                    <div className="flex h-40 flex-col items-center justify-center gap-3">
                        <p className="text-sm text-[hsl(var(--text-secondary))]">Testimonio no encontrado.</p>
                        <button
                            onClick={() => router.back()}
                            className="flex items-center gap-1 text-xs text-[hsl(var(--primary))] hover:underline"
                        >
                            <ArrowLeft size={14} /> Volver
                        </button>
                    </div>
                ) : (
                    <DSCard className="max-w-2xl space-y-5 p-6">
                        <div className="flex items-start justify-between gap-4">
                            <div className="flex items-center gap-3">
                                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[hsl(var(--primary)/0.12)]">
                                    <User size={18} className="text-[hsl(var(--primary))]" />
                                </div>
                                <div>
                                    <p className="font-semibold text-[hsl(var(--text-primary))]">{testimonial.author_name || '—'}</p>
                                    <p className="text-xs text-[hsl(var(--text-secondary))]">{testimonial.author_role || ''}</p>
                                    {testimonial.author_persona_id && (
                                        <p className="mt-0.5 font-mono text-[10px] text-[hsl(var(--text-secondary))] opacity-60">
                                            persona: {String(testimonial.author_persona_id)}
                                        </p>
                                    )}
                                </div>
                            </div>
                            <DSBadge tone={testimonial.status === 'published' ? 'emerald' : testimonial.status === 'archived' ? 'slate' : 'amber'} label={testimonial.status || 'pending'} />
                        </div>

                        {(testimonial.rating ?? 0) > 0 && (
                            <div className="flex gap-1">
                                {Array.from({ length: 5 }).map((_, i) => (
                                    <Star
                                        key={i}
                                        size={16}
                                        className={clsx(i < (testimonial.rating ?? 0) ? 'fill-amber-400 text-amber-400' : 'text-[hsl(var(--surface-2))]')}
                                    />
                                ))}
                            </div>
                        )}

                        <blockquote className="rounded-lg border-l-4 border-[hsl(var(--primary))] bg-[hsl(var(--surface-1))] px-4 py-3 text-sm italic text-[hsl(var(--text-primary))]">
                            {testimonial.content || 'Sin contenido.'}
                        </blockquote>

                        <div className="flex items-center gap-2 text-xs text-[hsl(var(--text-secondary))]">
                            <Calendar size={13} />
                            {testimonial.created_at ? new Date(testimonial.created_at).toLocaleDateString('es') : '—'}
                        </div>

                        <div className="flex gap-2 pt-2">
                            {testimonial.status !== 'published' && (
                                <button
                                    onClick={handleApprove}
                                    className="flex items-center gap-1.5 rounded-lg bg-[hsl(var(--success))] px-3 py-1.5 text-xs font-semibold text-white transition-opacity hover:opacity-90"
                                >
                                    <CheckCircle2 size={14} /> Aprobar
                                </button>
                            )}
                            {testimonial.status !== 'archived' && (
                                <button
                                    onClick={handleArchive}
                                    className="flex items-center gap-1.5 rounded-lg border border-[hsl(var(--border))] px-3 py-1.5 text-xs font-semibold text-[hsl(var(--text-secondary))] transition-colors hover:bg-[hsl(var(--surface-1))]"
                                >
                                    <Archive size={14} /> Archivar
                                </button>
                            )}
                            <button
                                onClick={() => router.back()}
                                className="flex items-center gap-1.5 rounded-lg border border-[hsl(var(--border))] px-3 py-1.5 text-xs font-semibold text-[hsl(var(--text-secondary))] transition-colors hover:bg-[hsl(var(--surface-1))]"
                            >
                                <ArrowLeft size={14} /> Volver
                            </button>
                        </div>
                    </DSCard>
                )}
            </main>
        </div>
    );
}
