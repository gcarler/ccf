"use client";
import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { DSCard } from '@/design';
import { toast } from 'sonner';
import { User, Calendar, ArrowLeft, CheckCircle2, Archive } from 'lucide-react';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';

interface TestimonialData {
  id: string;
  slug?: string;
  created_at?: string;
  author_name?: string;
  author_persona_id?: string | null;
  content?: string;
  status?: string;
  rating?: number;
  author_role?: string;
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
        apiFetch<TestimonialData>(`/cms/testimonials/${id}`, {
            headers: { Authorization: `Bearer ${token}` },
        }).then(d => setTestimonial(d)).catch(() => null).finally(() => setLoading(false));
    }, [id, token]);

    const patch = async (status: string) => {
        if (!testimonial || !token) return;
        try {
            await apiFetch(`/cms/testimonials/${testimonial.id}`, {
                method: 'PATCH',
                headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ status }),
            });
            if (status === 'archived') { router.push('/plataforma/cms/testimonials'); return; }
            setTestimonial(t => t ? { ...t, status } : t);
            toast.success('Estado actualizado');
        } catch { toast.error('Error al actualizar'); }
    };

    return (
        <div className="flex h-full flex-col">
            <WorkspaceToolbar breadcrumbs={[
                { label: 'CMS', href: '/plataforma/cms' },
                { label: 'Testimonios', href: '/plataforma/cms/testimonials' },
                { label: testimonial?.author_name || id },
            ]} />
            <main className="flex-1 overflow-auto p-6">
                {loading ? (
                    <p className="text-sm text-[hsl(var(--text-secondary))]">Cargando…</p>
                ) : !testimonial ? (
                    <div className="space-y-3">
                        <p className="text-sm text-[hsl(var(--text-secondary))]">Testimonio no encontrado.</p>
                        <button onClick={() => router.back()} className="flex items-center gap-1 text-xs text-[hsl(var(--primary))] hover:underline">
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
                                        <p className="font-mono text-[10px] text-[hsl(var(--text-secondary))] opacity-60">
                                            persona: {String(testimonial.author_persona_id)}
                                        </p>
                                    )}
                                </div>
                            </div>
                            <span className={"inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold " + (testimonial.status === 'published' ? 'bg-green-100 text-green-800' : testimonial.status === 'archived' ? 'bg-gray-100 text-gray-600' : 'bg-amber-100 text-amber-800')}>
                                {testimonial.status || 'pending'}
                            </span>
                        </div>
                        <blockquote className="rounded-lg border-l-4 border-[hsl(var(--primary))] bg-[hsl(var(--surface-1))] px-4 py-3 text-sm italic">
                            {testimonial.content || 'Sin contenido.'}
                        </blockquote>
                        <div className="flex items-center gap-2 text-xs text-[hsl(var(--text-secondary))]">
                            <Calendar size={13} />
                            {testimonial.created_at ? new Date(testimonial.created_at).toLocaleDateString('es') : '—'}
                        </div>
                        <div className="flex gap-2">
                            {testimonial.status !== 'published' && (
                                <button onClick={() => patch('published')} className="flex items-center gap-1.5 rounded-lg bg-[hsl(var(--success))] px-3 py-1.5 text-xs font-semibold text-white hover:opacity-90">
                                    <CheckCircle2 size={14} /> Aprobar
                                </button>
                            )}
                            {testimonial.status !== 'archived' && (
                                <button onClick={() => patch('archived')} className="flex items-center gap-1.5 rounded-lg border border-[hsl(var(--border))] px-3 py-1.5 text-xs font-semibold hover:bg-[hsl(var(--surface-1))]">
                                    <Archive size={14} /> Archivar
                                </button>
                            )}
                            <button onClick={() => router.back()} className="flex items-center gap-1.5 rounded-lg border border-[hsl(var(--border))] px-3 py-1.5 text-xs font-semibold hover:bg-[hsl(var(--surface-1))]">
                                <ArrowLeft size={14} /> Volver
                            </button>
                        </div>
                    </DSCard>
                )}
            </main>
        </div>
    );
}
