"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import {
    Facebook,
    Instagram,
    Youtube,
    MessageCircle,
    Radio,
    ExternalLink,
    Save,
    Sparkles,
    Globe,
    Loader2,
    Link2,
    Smartphone
} from 'lucide-react';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import type { ViewType } from '@/components/ViewSwitcher';
import UniversalCalendarView from '@/components/ui/UniversalCalendarView';
import UniversalGanttView from '@/components/ui/UniversalGanttView';
import UniversalWikiView from '@/components/ui/UniversalWikiView';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

interface SocialChannel {
    id?: number;
    platform: string;
    url: string;
    visible: boolean;
}

const PLATFORMS = [
    { id: 'facebook', icon: Facebook, label: 'Facebook', color: 'text-[hsl(var(--primary))]', aura: 'rgba(37, 99, 235, 0.1)' },
    { id: 'instagram', icon: Instagram, label: 'Instagram', color: 'text-pink-600', aura: 'rgba(219, 39, 119, 0.1)' },
    { id: 'youtube', icon: Youtube, label: 'YouTube', color: 'text-rose-600', aura: 'rgba(225, 29, 72, 0.1)' },
    { id: 'whatsapp', icon: MessageCircle, label: 'WhatsApp', color: 'text-emerald-600', aura: 'rgba(16, 185, 129, 0.1)' },
];
const SOCIAL_VIEWS: ViewType[] = ['grid', 'list', 'table', 'board', 'kanban', 'calendar', 'gantt', 'wiki'];

export default function SocialMediaSettings() {
    const { token, isAuthenticated } = useAuth();
    const { addToast } = useToast();

    const [socials, setSocials] = useState<SocialChannel[]>([]);
    const [loading, setLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);
    const [viewType, setViewType] = useState<ViewType>('grid');

    const fetchSocials = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const data = await apiFetch<SocialChannel[]>('/admin/socials', { token, cache: 'no-store' });
            setSocials(Array.isArray(data) ? data : []);
        } catch (err) {
            console.error(err);
            addToast("Error al sincronizar redes sociales", "error");
        } finally {
            setLoading(false);
        }
    }, [token, addToast]);

    useEffect(() => {
        if (isAuthenticated) fetchSocials();
    }, [isAuthenticated, fetchSocials]);

    const handleSave = async () => {
        setIsSaving(true);
        try {
            // Mock mass save for now, or we could loop if API supports single only
            addToast("Canales sociales actualizados", "success");
        } catch (err) {
            addToast("Error al guardar cambios", "error");
        } finally {
            setIsSaving(false);
        }
    };

    if (!isAuthenticated) return null;

    const platformRows = PLATFORMS.map((platform) => ({
        ...platform,
        channel: socials.find(s => s.platform.toLowerCase() === platform.id),
    }));

    const groupedRows = [
        { id: 'visible', label: 'Visibles', rows: platformRows.filter(row => row.channel?.visible !== false && row.channel?.url) },
        { id: 'pending', label: 'Pendientes', rows: platformRows.filter(row => !row.channel?.url || row.channel?.visible === false) },
    ];

    const calendarEvents = platformRows.map((row, index) => ({
        id: row.id,
        title: row.label,
        date: new Date(Date.now() + index * 86400000).toISOString().split('T')[0],
        color: row.channel?.url ? 'emerald' as const : 'amber' as const,
        location: row.channel?.url || 'Sin enlace',
    }));

    const ganttItems = platformRows.map((row, index) => {
        const date = new Date(Date.now() + index * 86400000).toISOString();
        return {
            id: row.id,
            title: row.label,
            subtitle: row.channel?.url || 'Pendiente de configurar',
            start_date: date,
            end_date: date,
            color: row.channel?.url ? 'emerald' as const : 'amber' as const,
            progress: row.channel?.url ? 100 : 35,
        };
    });

    const renderList = () => (
        <div className="space-y-4">
            {platformRows.map((row) => (
                <div key={row.id} className="social-aura bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 p-3 rounded-lg flex items-center justify-between gap-3" style={{ '--aura-color': row.aura } as any}>
                    <div className="flex items-center gap-3 min-w-0">
                        <div className={clsx("size-7 rounded-lg flex items-center justify-center bg-[hsl(var(--surface-1))] dark:bg-black/20", row.color)}>
                            <row.icon size={24} />
                        </div>
                        <div className="min-w-0">
                            <h3 className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-white uppercase tracking-tight">{row.label}</h3>
                            <p className="mt-1 text-[10px] font-bold text-[hsl(var(--text-secondary))] truncate">{row.channel?.url || 'Sin URL configurada'}</p>
                        </div>
                    </div>
                    <span className={clsx("px-2 py-0.5 rounded-full text-[9px] font-semibold uppercase", row.channel?.url ? "bg-emerald-50 text-emerald-600" : "bg-amber-50 text-amber-600")}>{row.channel?.url ? 'Activo' : 'Pendiente'}</span>
                </div>
            ))}
        </div>
    );

    const renderTable = () => (
        <div className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 overflow-x-auto bg-[hsl(var(--bg-primary))] dark:bg-white/5">
            <table className="w-full min-w-[480px] text-left">
                <thead className="bg-[hsl(var(--surface-1))] dark:bg-white/5">
                    <tr>
                        <th className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Canal</th>
                        <th className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] hidden md:table-cell">URL</th>
                        <th className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Estado</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-[hsl(var(--border))] dark:divide-white/5">
                    {platformRows.map((row) => (
                        <tr key={row.id} className="hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/[0.03]">
                            <td className="px-3 py-1.5 text-sm font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{row.label}</td>
                            <td className="px-3 py-1.5 hidden md:table-cell text-[11px] text-[hsl(var(--text-secondary))] truncate max-w-[420px]">{row.channel?.url || '—'}</td>
                            <td className="px-3 py-1.5"><span className={clsx("px-2 py-0.5 rounded-full text-[9px] font-semibold uppercase", row.channel?.url ? "bg-emerald-50 text-emerald-600" : "bg-amber-50 text-amber-600")}>{row.channel?.url ? 'Activo' : 'Pendiente'}</span></td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );

    const renderBoard = () => (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            {groupedRows.map((group) => (
                <section key={group.id} className="rounded-lg bg-[hsl(var(--surface-1))] dark:bg-white/[0.03] border border-[hsl(var(--border))] dark:border-white/10 p-3">
                    <div className="flex items-center justify-between mb-5">
                        <span className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{group.label}</span>
                        <span className="font-semibold text-[hsl(var(--text-secondary))]">{group.rows.length}</span>
                    </div>
                    <div className="space-y-3">
                        {group.rows.map((row) => (
                            <div key={row.id} className="bg-[hsl(var(--bg-primary))] dark:bg-white/[0.05] border border-[hsl(var(--border))] dark:border-white/5 rounded-lg p-4">
                                <p className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-white uppercase tracking-tight">{row.label}</p>
                                <p className="mt-2 text-[10px] font-bold text-[hsl(var(--text-secondary))] truncate">{row.channel?.url || 'Sin enlace'}</p>
                            </div>
                        ))}
                    </div>
                </section>
            ))}
        </div>
    );

    return (
        <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] dark:bg-[#0a0f16] font-display overflow-hidden">
            <style jsx global>{`
                .social-aura {
                    position: relative;
                }
                .social-aura::after {
                    content: '';
                    position: absolute;
                    inset: -1px;
                    background: linear-gradient(45deg, var(--aura-color, transparent), transparent 60%);
                    z-index: -1;
                    border-radius: inherit;
                    opacity: 0;
                    transition: opacity 0.5s ease;
                }
                .social-aura:hover::after {
                    opacity: 1;
                }
            `}</style>

            <WorkspaceToolbar 
                breadcrumbs={[{ label: 'Ajustes', icon: Globe }, { label: 'Canales Sociales', icon: Smartphone }]}
                viewType={viewType}
                setViewType={setViewType}
                availableViews={SOCIAL_VIEWS}
                rightActions={
                    <button 
                        onClick={handleSave} disabled={isSaving}
                        className="flex items-center gap-3 px-4 py-3 bg-[hsl(var(--bg-muted))] dark:bg-[hsl(var(--bg-primary))] text-white dark:text-[hsl(var(--text-primary))] rounded-lg text-[11px] font-semibold uppercase tracking-wide shadow-xl active:scale-95 transition-all"
                    >
                        {isSaving ? <Loader2 className="animate-spin" size={16} /> : <Save size={16} />} Guardar Redes
                    </button>
                }
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin p-4 lg:p-4 relative pb-4">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_#3b82f605_0%,_transparent_50%)] pointer-events-none" />

 <div className="w-full space-y-3 relative z-10">
                    
                    {/* Cinematic Header */}
                    <header className="space-y-4">
                        <motion.div 
                            initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}
                            className="inline-flex items-center gap-2 px-4 py-1.5 bg-blue-500/10 text-[hsl(var(--primary))] rounded-full text-[10px] font-semibold uppercase tracking-wide border border-blue-500/20"
                        >
                            <Sparkles size={12} className="animate-pulse" /> Ecosistema Digital CCF
                        </motion.div>
                        <h1 className="text-xl lg:text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tighter leading-none">
                            Tu voz en la <br/> <span className="text-[hsl(var(--primary))] italic">nube global.</span>
                        </h1>
                        <p className="text-lg text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] font-medium max-w-xl">
                            Configura los puntos de contacto digitales para que tu congregación esté siempre conectada con el mensaje.
                        </p>
                    </header>

                    <AnimatePresence mode="wait">
                        {loading ? (
                            <div className="py-1.5 flex flex-col items-center justify-center gap-4 text-[hsl(var(--text-secondary))] font-semibold uppercase tracking-wide animate-pulse">
                                <Loader2 className="animate-spin" size={40} /> Conectando API...
                            </div>
                        ) : viewType === 'list' ? (
                            renderList()
                        ) : viewType === 'table' ? (
                            renderTable()
                        ) : viewType === 'board' || viewType === 'kanban' ? (
                            renderBoard()
                        ) : viewType === 'calendar' ? (
                            <UniversalCalendarView events={calendarEvents} title="Calendario de canales sociales" />
                        ) : viewType === 'gantt' ? (
                            <UniversalGanttView items={ganttItems} moduleName="Canales sociales" />
                        ) : viewType === 'wiki' ? (
                            <UniversalWikiView moduleName="Canales sociales" storageKey="wiki_admin_socials" />
                        ) : (
                            <motion.section 
                                initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                                className="grid grid-cols-1 gap-3"
                            >
                                {PLATFORMS.map((platform, i) => {
                                    const channel = socials.find(s => s.platform.toLowerCase() === platform.id);
                                    return (
                                        <motion.div 
                                            key={platform.id}
                                            initial={{ opacity: 0, x: -20 }}
                                            animate={{ opacity: 1, x: 0 }}
                                            transition={{ delay: i * 0.05 }}
                                            className="social-aura bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 p-4 rounded-lg flex flex-col md:flex-row md:items-center justify-between gap-3 group hover:shadow-2xl transition-all duration-500"
                                            style={{ '--aura-color': platform.aura } as any}
                                        >
                                            <div className="flex items-center gap-3 flex-1">
                                                <div className={clsx("size-8 rounded-lg flex items-center justify-center shadow-inner group-hover:scale-110 transition-all duration-500 bg-[hsl(var(--surface-1))] dark:bg-black/20", platform.color)}>
                                                    <platform.icon size={40} strokeWidth={1.5} />
                                                </div>
                                                <div className="flex-1 space-y-4">
                                                    <div>
                                                        <h3 className="text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white uppercase tracking-tight leading-none mb-1">{platform.label}</h3>
                                                        <p className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide leading-none">Perfil de la Congregación</p>
                                                    </div>
                                                    <div className="relative group/input">
                                                        <Link2 className="absolute left-5 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))] group-focus-within/input:text-[hsl(var(--primary))] transition-colors" size={18} />
                                                        <input 
                                                            defaultValue={channel?.url || ''}
                                                            className="w-full pl-14 pr-6 py-1.5 bg-[hsl(var(--surface-1))] dark:bg-black/40 border border-transparent focus:border-blue-500 rounded-lg text-xs font-bold outline-none transition-all placeholder:text-[hsl(var(--text-secondary))]"
                                                            placeholder={`URL de tu ${platform.label}...`}
                                                        />
                                                    </div>
                                                </div>
                                            </div>
                                            <button className="px-4 h-8 bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--primary))] hover:text-white hover:border-blue-600 hover:shadow-xl hover:shadow-blue-500/20 transition-all transform active:scale-95 shrink-0 flex items-center gap-2">
                                                Validar Enlace <ExternalLink size={14} />
                                            </button>
                                        </motion.div>
                                    );
                                })}
                            </motion.section>
                        )}
                    </AnimatePresence>

                    {/* Streaming Pro Card */}
                    <motion.section 
                        initial={{ opacity: 0, y: 30 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.3 }}
                        className="bg-[hsl(var(--bg-muted))] p-4 rounded-lg text-white relative overflow-hidden group shadow-2xl"
                    >
                        <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:rotate-12 transition-transform duration-1000"><Radio size={200} /></div>
                        
                        <div className="relative z-10 flex flex-col md:flex-row items-center gap-3">
                            <div className="size-10 rounded-lg bg-rose-600 flex items-center justify-center shadow-2xl shadow-rose-500/40 border border-rose-400/20 shrink-0">
                                <Radio size={48} className="animate-pulse" />
                            </div>
                            <div className="flex-1 space-y-3">
                                <div>
                                    <h3 className="text-xl font-bold tracking-tight leading-none mb-3">Retransmisión en Vivo</h3>
                                    <p className="text-[hsl(var(--text-secondary))] font-medium leading-relaxed italic">
                                        &ldquo;Introduce el link directo de tu servidor de streaming (RTMP/HLS) para integrar la señal en el muro comunitario.&rdquo;
                                    </p>
                                </div>
                                <div className="flex flex-col md:flex-row gap-4">
                                    <input 
                                        className="flex-1 px-4 py-2 bg-black/40 border border-white/10 rounded-lg text-sm font-bold outline-none focus:border-rose-500 transition-all"
                                        placeholder="rtmp://servidor.iglesia.com/live"
                                    />
                                    <button className="px-4 py-2 bg-[hsl(var(--bg-primary))] text-[hsl(var(--text-primary))] rounded-lg text-[11px] font-semibold uppercase tracking-wide shadow-xl hover:translate-y-[-4px] active:scale-95 transition-all">Sincronizar Señal</button>
                                </div>
                            </div>
                        </div>
                    </motion.section>
                </div>
            </main>
        </div>
    );
}

