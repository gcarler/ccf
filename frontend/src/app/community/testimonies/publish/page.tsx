"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { ArrowLeft, Send, Camera, EyeOff, Globe } from 'lucide-react';
import { useToast } from '@/context/ToastContext';

import { apiFetch } from '@/lib/http';
import { motion } from 'framer-motion';

export default function PublishTestimony() {
    const { isAuthenticated, user, token } = useAuth();
    const router = useRouter();
    const { addToast } = useToast();

    const [selectedCategory, setSelectedCategory] = useState('Sanidad');
    const [testimonyText, setTestimonyText] = useState('');
    const [isAnonymous, setIsAnonymous] = useState(false);
    const [isSubmitting, setIsSubmitting] = useState(false);

    if (!isAuthenticated) return null;

    const categories = ['Sanidad', 'Familia', 'Finanzas', 'Salvación', 'Milagro'];

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!testimonyText.trim() || !user) return;

        setIsSubmitting(true);
        try {
            await apiFetch('/cms/testimonials', {
                method: 'POST',
                token: token || undefined,
                body: {
                    author_id: user.id,
                    content: testimonyText,
                    emotion: selectedCategory,
                    is_approved: false // Default to unapproved for moderation
                }
            });

            addToast('¡Gracias por compartir tu historia! Será revisada por moderación.', 'success');
            router.push('/community/testimonies');
        } catch (err: any) {
            addToast(err?.detail?.message || 'Error al publicar el testimonio', 'error');
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="p-8 lg:p-12 space-y-12 max-w-3xl mx-auto animate-in fade-in duration-700">
            {/* Header Section */}
            <header className="flex items-center gap-6">
                <button 
                    onClick={() => router.back()} 
                    className="size-12 rounded-2xl bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] flex items-center justify-center text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] hover:border-[hsl(var(--primary)/0.3)] transition-all active:scale-90"
                >
                    <ArrowLeft size={20} />
                </button>
                <div className="space-y-0.5">
                    <div className="flex items-center gap-2 text-[hsl(var(--primary))] font-black uppercase tracking-[0.3em] text-[9px]">
                        <div className="size-1.5 rounded-full bg-current shadow-[0_0_8px_currentColor]"></div>
                        Inspiración
                    </div>
                    <h1 className="text-3xl font-black text-[hsl(var(--text-primary))] tracking-tighter">Publicar Milagro</h1>
                </div>
            </header>

            <form onSubmit={handleSubmit} className="space-y-10">
                {/* Hero / Instruction */}
                <div className="bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-[2.5rem] p-8 md:p-10 shadow-sm relative overflow-hidden">
                    <div className="absolute -right-4 -top-4 size-32 bg-[hsl(var(--primary)/0.05)] rounded-full blur-3xl"></div>
                    <h2 className="text-2xl font-black text-[hsl(var(--text-primary))] tracking-tight mb-2 relative z-10">Cuéntanos tu historia</h2>
                    <p className="text-[hsl(var(--text-secondary))] text-sm font-medium relative z-10">Tu fe es la evidencia de que Dios sigue obrando milagros hoy.</p>
                </div>

                {/* Text Area */}
                <section className="space-y-6">
                    <h4 className="text-[hsl(var(--primary))] text-[10px] uppercase font-black tracking-[0.2em] flex items-center gap-2">
                        <div className="size-1.5 rounded-full bg-current"></div>
                        Tu Testimonio
                    </h4>
                    <div className="relative group">
                        <div className="absolute -inset-1 bg-gradient-to-br from-[hsl(var(--primary))] to-transparent opacity-0 group-focus-within:opacity-10 transition-opacity rounded-[2rem] blur-xl"></div>
                        <div className="relative bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] group-focus-within:border-[hsl(var(--primary))] rounded-[2.5rem] p-8 shadow-inner transition-all">
                            <textarea
                                value={testimonyText}
                                onChange={(e) => setTestimonyText(e.target.value)}
                                className="w-full bg-transparent border-none focus:ring-0 text-[hsl(var(--text-primary))] placeholder-[hsl(var(--text-secondary)/0.5)] resize-none h-48 text-base leading-relaxed font-medium italic"
                                placeholder="Escribe tu testimonio aquí... ¿Qué hizo el Señor en tu vida?"
                                required
                            />
                        </div>
                    </div>
                </section>

                {/* Category Selector */}
                <section className="space-y-6">
                    <h4 className="text-[hsl(var(--primary))] text-[10px] uppercase font-black tracking-[0.2em] flex items-center gap-2">
                        <div className="size-1.5 rounded-full bg-current"></div>
                        Área del Milagro
                    </h4>
                    <div className="flex flex-wrap gap-3">
                        {categories.map(category => (
                            <button
                                key={category}
                                type="button"
                                onClick={() => setSelectedCategory(category)}
                                className={`h-11 px-6 rounded-2xl text-[11px] font-black uppercase tracking-widest transition-all border ${selectedCategory === category
                                    ? 'bg-[hsl(var(--primary))] text-white shadow-lg shadow-primary/30 border-transparent scale-105'
                                    : 'bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))] border-[hsl(var(--border))] hover:border-[hsl(var(--primary)/0.4)]'
                                    }`}
                            >
                                {category}
                            </button>
                        ))}
                    </div>
                </section>

                {/* Multimedia Upload */}
                <section className="space-y-6">
                    <h4 className="text-[hsl(var(--primary))] text-[10px] uppercase font-black tracking-[0.2em] flex items-center gap-2">
                        <div className="size-1.5 rounded-full bg-current"></div>
                        Multimedia (Opcional)
                    </h4>
                    <div className="border-2 border-dashed border-[hsl(var(--border))] hover:border-[hsl(var(--primary)/0.5)] rounded-[2.5rem] p-12 flex flex-col items-center justify-center bg-[hsl(var(--surface-2))] hover:bg-[hsl(var(--surface-3))] transition-all cursor-pointer group scale-in duration-500">
                        <div className="size-16 rounded-[1.5rem] bg-[hsl(var(--primary)/0.1)] flex items-center justify-center text-[hsl(var(--primary))] mb-6 group-hover:scale-110 group-hover:bg-[hsl(var(--primary))] group-hover:text-white transition-all shadow-sm">
                            <Camera size={28} strokeWidth={2.5} />
                        </div>
                        <p className="text-[hsl(var(--text-primary))] font-black text-sm uppercase tracking-tight">Añadir Evidencia</p>
                        <p className="text-[hsl(var(--text-secondary))] text-[10px] mt-2 font-black uppercase tracking-widest opacity-60">Foto o Video (Máx 50MB)</p>
                    </div>
                </section>

                {/* Privacy Visibility */}
                <section className="space-y-6">
                    <h4 className="text-[hsl(var(--primary))] text-[10px] uppercase font-black tracking-[0.2em] flex items-center gap-2 mb-6">
                        <div className="size-1.5 rounded-full bg-current"></div>
                        Visibilidad
                    </h4>
                    <div className={`flex items-center justify-between p-6 rounded-3xl transition-all border ${isAnonymous ? 'bg-[hsl(var(--primary)/0.05)] border-[hsl(var(--primary)/0.3)] shadow-lg' : 'bg-[hsl(var(--surface-2))] border-[hsl(var(--border))]'}`}>
                        <div className="flex items-start gap-4">
                            <div className={`p-3 rounded-2xl shrink-0 transition-colors ${isAnonymous ? 'bg-[hsl(var(--primary))] text-white shadow-lg' : 'bg-[hsl(var(--surface-3))] text-[hsl(var(--text-secondary))]'}`}>
                                <Globe size={20} strokeWidth={2.5} />
                            </div>
                            <div className="flex flex-col pt-1">
                                <span className={`font-black text-sm uppercase tracking-tight transition-colors ${isAnonymous ? 'text-[hsl(var(--primary))]' : 'text-[hsl(var(--text-primary))]'}`}>Publicar como Anónimo</span>
                                <span className="text-[hsl(var(--text-secondary))] text-[11px] font-medium mt-1">Tu nombre no aparecerá en el muro de milagros.</span>
                            </div>
                        </div>
                        <label className="relative inline-flex items-center cursor-pointer shrink-0">
                            <input type="checkbox" className="sr-only peer" checked={isAnonymous} onChange={() => setIsAnonymous(!isAnonymous)} />
                            <div className="w-12 h-6 bg-[hsl(var(--surface-3))] peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[4px] after:left-[4px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-[hsl(var(--primary))] border border-[hsl(var(--border))]"></div>
                        </label>
                    </div>
                </section>

                {/* Publish Action */}
                <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    type="submit"
                    disabled={isSubmitting || !testimonyText.trim()}
                    className="w-full h-16 bg-[hsl(var(--primary))] text-white rounded-[2rem] font-black uppercase tracking-[0.2em] text-xs shadow-2xl shadow-primary/30 hover:opacity-95 disabled:opacity-50 transition-all flex items-center justify-center gap-3"
                >
                    {isSubmitting ? (
                        <div className="flex items-center gap-2">
                            <div className="size-4 rounded-full border-2 border-white border-t-transparent animate-spin"></div>
                            Publicando...
                        </div>
                    ) : (
                        <>
                            <span>Publicar Testimonio</span>
                            <Send size={18} strokeWidth={2.5} />
                        </>
                    )}
                </motion.button>
            </form>
        </div>
    );
}
