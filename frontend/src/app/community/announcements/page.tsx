"use client";

import React from 'react';
import { motion } from 'framer-motion';
import { Megaphone, Sparkles, Pin } from 'lucide-react';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';

interface AnnouncementItem {
    id: number;
    title: string;
    excerpt: string;
    date: string;
    category: string;
    isPinned?: boolean;
}

export default function AnnouncementsPage() {
    const { token } = useAuth();
    const [announcements, setAnnouncements] = React.useState<AnnouncementItem[]>([
        {
            id: 1,
            title: "Congreso de Jóvenes: 'Inquebrantables'",
            excerpt: "Prepárate para un fin de semana transformador. Inscripciones abiertas en el lobby.",
            date: "Hace 2 horas",
            category: "Eventos",
            isPinned: true
        },
        {
            id: 2,
            title: "Nueva Serie de Predicas: 'Caminando por Fe'",
            excerpt: "Acompáñanos este domingo para el inicio de nuestra nueva serie enfocada en la vida de Abraham.",
            date: "Hace 5 horas",
            category: "General",
            isPinned: false
        },
        {
            id: 3,
            title: "Oportunidad de Voluntariado: Media & Producción",
            excerpt: "¿Te apasiona la tecnología? Únete a nuestro equipo de producción para los servicios dominicales.",
            date: "Ayer",
            category: "Servicio",
            isPinned: false
        }
    ]);

    React.useEffect(() => {
        const load = async () => {
            try {
                const rows = await apiFetch<any[]>('/cms/announcements', { token: token || undefined, cache: 'no-store' });
                if (!Array.isArray(rows) || rows.length === 0) return;
                setAnnouncements(
                    rows.map((item, index) => ({
                        id: Number(item.id || index + 1),
                        title: item.title || 'Anuncio',
                        excerpt: item.content || item.excerpt || '',
                        date: (item.published_at || item.created_at) ? new Date(item.published_at || item.created_at).toLocaleDateString('es-MX') : 'Reciente',
                        category: item.category || 'General',
                        isPinned: Boolean(item.is_featured || item.featured || item.is_pinned)
                    }))
                );
            } catch {
                // fallback local data
            }
        };
        load();
    }, [token]);

    return (
        <div className="max-w-4xl mx-auto space-y-10 pb-20 animate-in fade-in duration-700">
            <header className="space-y-2">
                <div className="flex items-center gap-2 text-[hsl(var(--primary))] font-black uppercase tracking-[0.3em] text-[10px]">
                    <div className="size-2 rounded-full bg-current shadow-[0_0_10px_currentColor]"></div>
                    Comunicación Oficial
                </div>
                <h1 className="text-4xl font-black text-[hsl(var(--text-primary))] tracking-tighter">Anuncios</h1>
                <p className="text-[hsl(var(--text-secondary))] font-medium">Mantente al tanto de las últimas noticias y actualizaciones de nuestra comunidad.</p>
            </header>

            <div className="space-y-6">
                {announcements.map((item, idx) => (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: idx * 0.1 }}
                        key={item.id}
                        className="relative bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-[2.5rem] p-8 hover:border-[hsl(var(--primary)/0.3)] hover:shadow-xl hover:shadow-primary/5 transition-all group overflow-hidden"
                    >
                        {item.isPinned && (
                            <div className="absolute top-6 right-8 text-[hsl(var(--primary))] opacity-50">
                                <Pin size={18} strokeWidth={2.5} />
                            </div>
                        )}

                        <div className="flex items-start gap-6">
                            <div className="size-14 rounded-2xl bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] flex items-center justify-center text-[hsl(var(--primary))] group-hover:scale-110 transition-transform">
                                <Megaphone size={24} strokeWidth={2.5} />
                            </div>

                            <div className="flex-1 space-y-3">
                                <div className="flex items-center gap-3">
                                    <span className="text-[10px] font-black uppercase tracking-widest px-3 py-1 rounded-full bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))]">
                                        {item.category}
                                    </span>
                                    <span className="text-[10px] font-bold text-[hsl(var(--text-secondary)/0.6)] uppercase tracking-tight">
                                        {item.date}
                                    </span>
                                </div>
                                <h3 className="text-xl font-black text-[hsl(var(--text-primary))] tracking-tight group-hover:text-[hsl(var(--primary))] transition-colors">
                                    {item.title}
                                </h3>
                                <p className="text-[hsl(var(--text-secondary))] text-sm leading-relaxed font-medium">
                                    {item.excerpt}
                                </p>
                            </div>
                        </div>
                    </motion.div>
                ))}
            </div>

            {/* Empty State / More Info */}
            <div className="bg-[hsl(var(--surface-3))] rounded-[3rem] p-12 text-center border-2 border-dashed border-[hsl(var(--border))]">
                <div className="size-16 rounded-[1.5rem] bg-[hsl(var(--surface-1))] flex items-center justify-center text-[hsl(var(--text-secondary)/0.3)] mx-auto mb-6">
                    <Sparkles size={32} />
                </div>
                <h4 className="text-lg font-black text-[hsl(var(--text-primary))] tracking-tight mb-2">¿Tienes algo que anunciar?</h4>
                <p className="text-[hsl(var(--text-secondary))] text-sm font-medium max-w-xs mx-auto mb-8">
                    Si eres líder de ministerio y tienes una actualización importante, contacta al equipo de comunicaciones.
                </p>
                <button className="px-8 h-12 bg-[hsl(var(--text-primary))] text-[hsl(var(--surface-1))] rounded-2xl font-black uppercase tracking-widest text-[10px] hover:opacity-90 transition-all">
                    Contactar Equipo
                </button>
            </div>
        </div>
    );
}

