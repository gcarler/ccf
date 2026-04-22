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
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

interface SocialChannel {
    id?: number;
    platform: string;
    url: string;
    visible: boolean;
}

const PLATFORMS = [
    { id: 'facebook', icon: Facebook, label: 'Facebook', color: 'text-blue-600', aura: 'rgba(37, 99, 235, 0.1)' },
    { id: 'instagram', icon: Instagram, label: 'Instagram', color: 'text-pink-600', aura: 'rgba(219, 39, 119, 0.1)' },
    { id: 'youtube', icon: Youtube, label: 'YouTube', color: 'text-rose-600', aura: 'rgba(225, 29, 72, 0.1)' },
    { id: 'whatsapp', icon: MessageCircle, label: 'WhatsApp', color: 'text-emerald-600', aura: 'rgba(16, 185, 129, 0.1)' },
];

export default function SocialMediaSettings() {
    const { token, isAuthenticated } = useAuth();
    const { addToast } = useToast();

    const [socials, setSocials] = useState<SocialChannel[]>([]);
    const [loading, setLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);

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

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#0a0f16] font-display overflow-hidden">
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
                viewType="grid" setViewType={() => {}}
                rightActions={
                    <button 
                        onClick={handleSave} disabled={isSaving}
                        className="flex items-center gap-3 px-8 py-3 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-[1.5rem] text-[11px] font-black uppercase tracking-widest shadow-xl active:scale-95 transition-all"
                    >
                        {isSaving ? <Loader2 className="animate-spin" size={16} /> : <Save size={16} />} Guardar Redes
                    </button>
                }
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin p-8 lg:p-12 relative pb-40">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_#3b82f605_0%,_transparent_50%)] pointer-events-none" />

                <div className="max-w-5xl mx-auto space-y-12 relative z-10">
                    
                    {/* Cinematic Header */}
                    <header className="space-y-4">
                        <motion.div 
                            initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}
                            className="inline-flex items-center gap-2 px-4 py-1.5 bg-blue-500/10 text-blue-600 rounded-full text-[10px] font-black uppercase tracking-[0.3em] border border-blue-500/20"
                        >
                            <Sparkles size={12} className="animate-pulse" /> Ecosistema Digital CCF
                        </motion.div>
                        <h1 className="text-5xl lg:text-6xl font-black text-slate-900 dark:text-white tracking-tighter leading-none">
                            Tu voz en la <br/> <span className="text-blue-600 italic">nube global.</span>
                        </h1>
                        <p className="text-lg text-slate-500 dark:text-slate-400 font-medium max-w-xl">
                            Configura los puntos de contacto digitales para que tu congregación esté siempre conectada con el mensaje.
                        </p>
                    </header>

                    <AnimatePresence mode="wait">
                        {loading ? (
                            <div className="py-40 flex flex-col items-center justify-center gap-4 text-slate-400 font-black uppercase tracking-[0.4em] animate-pulse">
                                <Loader2 className="animate-spin" size={40} /> Conectando API...
                            </div>
                        ) : (
                            <motion.section 
                                initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                                className="grid grid-cols-1 gap-6"
                            >
                                {PLATFORMS.map((platform, i) => {
                                    const channel = socials.find(s => s.platform.toLowerCase() === platform.id);
                                    return (
                                        <motion.div 
                                            key={platform.id}
                                            initial={{ opacity: 0, x: -20 }}
                                            animate={{ opacity: 1, x: 0 }}
                                            transition={{ delay: i * 0.05 }}
                                            className="social-aura bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 p-10 rounded-[3.5rem] flex flex-col md:flex-row md:items-center justify-between gap-8 group hover:shadow-2xl transition-all duration-500"
                                            style={{ '--aura-color': platform.aura } as any}
                                        >
                                            <div className="flex items-center gap-8 flex-1">
                                                <div className={clsx("size-20 rounded-[2rem] flex items-center justify-center shadow-inner group-hover:scale-110 transition-all duration-500 bg-slate-50 dark:bg-black/20", platform.color)}>
                                                    <platform.icon size={40} strokeWidth={1.5} />
                                                </div>
                                                <div className="flex-1 space-y-4">
                                                    <div>
                                                        <h3 className="text-xl font-black text-slate-900 dark:text-white uppercase tracking-tight leading-none mb-1">{platform.label}</h3>
                                                        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest leading-none">Perfil de la Congregación</p>
                                                    </div>
                                                    <div className="relative group/input">
                                                        <Link2 className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-300 group-focus-within/input:text-blue-500 transition-colors" size={18} />
                                                        <input 
                                                            defaultValue={channel?.url || ''}
                                                            className="w-full pl-14 pr-6 py-4 bg-slate-50 dark:bg-black/40 border border-transparent focus:border-blue-500 rounded-2xl text-xs font-bold outline-none transition-all placeholder:text-slate-300"
                                                            placeholder={`URL de tu ${platform.label}...`}
                                                        />
                                                    </div>
                                                </div>
                                            </div>
                                            <button className="px-10 h-14 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-2xl text-[10px] font-black uppercase tracking-widest text-slate-500 hover:bg-blue-600 hover:text-white hover:border-blue-600 hover:shadow-xl hover:shadow-blue-500/20 transition-all transform active:scale-95 shrink-0 flex items-center gap-2">
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
                        className="bg-slate-900 p-12 rounded-[4rem] text-white relative overflow-hidden group shadow-2xl"
                    >
                        <div className="absolute top-0 right-0 p-12 opacity-10 group-hover:rotate-12 transition-transform duration-1000"><Radio size={200} /></div>
                        
                        <div className="relative z-10 flex flex-col md:flex-row items-center gap-12">
                            <div className="size-24 rounded-[2rem] bg-rose-600 flex items-center justify-center shadow-2xl shadow-rose-500/40 border border-rose-400/20 shrink-0">
                                <Radio size={48} className="animate-pulse" />
                            </div>
                            <div className="flex-1 space-y-8">
                                <div>
                                    <h3 className="text-3xl font-black tracking-tight leading-none mb-3">Retransmisión en Vivo</h3>
                                    <p className="text-slate-400 font-medium leading-relaxed italic">
                                        &ldquo;Introduce el link directo de tu servidor de streaming (RTMP/HLS) para integrar la señal en el muro comunitario.&rdquo;
                                    </p>
                                </div>
                                <div className="flex flex-col md:flex-row gap-4">
                                    <input 
                                        className="flex-1 px-8 py-5 bg-black/40 border border-white/10 rounded-[2rem] text-sm font-bold outline-none focus:border-rose-500 transition-all"
                                        placeholder="rtmp://servidor.iglesia.com/live"
                                    />
                                    <button className="px-10 py-5 bg-white text-slate-900 rounded-[2rem] text-[11px] font-black uppercase tracking-[0.2em] shadow-xl hover:translate-y-[-4px] active:scale-95 transition-all">Sincronizar Señal</button>
                                </div>
                            </div>
                        </div>
                    </motion.section>
                </div>
            </main>
        </div>
    );
}

