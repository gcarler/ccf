"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { ArrowLeft, Send, Lock, Globe } from 'lucide-react';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';

import { motion } from 'framer-motion';

export default function PrayerRequestForm() {
    const { isAuthenticated, token, user } = useAuth();
    const router = useRouter();
    const { addToast } = useToast();

    const [selectedCategory, setSelectedCategory] = useState('Salud');
    const [requestText, setRequestText] = useState('');
    const [isAnonymous, setIsAnonymous] = useState(false);
    const [isConfidential, setIsConfidential] = useState(false);
    const [isSubmitting, setIsSubmitting] = useState(false);

    if (!isAuthenticated) return null;

    const categories = ['Salud', 'Finanzas', 'Familia', 'Fortaleza', 'Otros'];

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!requestText.trim()) return;

        if (!token) {
            addToast('Debes iniciar sesión para enviar una petición.', 'error');
            return;
        }

        setIsSubmitting(true);
        try {
            await apiFetch('/prayer/', {
                method: 'POST',
                token,
                body: {
                    name: user?.username || 'Anónimo',
                    request: requestText,
                    category: selectedCategory,
                    is_anonymous: isAnonymous,
                    user_id: user?.id
                },
            });
            addToast('Tu petición de oración ha sido compartida.', 'success');
            router.push('/community/prayer');
        } catch (error) {
            console.error('prayer request error', error);
            addToast('No pudimos registrar tu petición.', 'error');
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
                        Interacción
                    </div>
                    <h1 className="text-3xl font-black text-[hsl(var(--text-primary))] tracking-tighter">Pedir Oración</h1>
                </div>
            </header>

            <form onSubmit={handleSubmit} className="space-y-10">
                {/* Hero / Instruction */}
                <div className="bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-[2.5rem] p-8 md:p-10 shadow-sm">
                    <h2 className="text-2xl font-black text-[hsl(var(--text-primary))] tracking-tight mb-2">¿En qué podemos orar por ti?</h2>
                    <p className="text-[hsl(var(--text-secondary))] text-sm font-medium">Tu congregación está aquí para apoyarte en intercesión.</p>
                </div>

                {/* Category Selector */}
                <section className="space-y-6">
                    <h4 className="text-[hsl(var(--primary))] text-[10px] uppercase font-black tracking-[0.2em] flex items-center gap-2">
                        <div className="size-1.5 rounded-full bg-current"></div>
                        Motivo de Oración
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

                {/* Text Area */}
                <section className="space-y-6">
                    <h4 className="text-[hsl(var(--primary))] text-[10px] uppercase font-black tracking-[0.2em] flex items-center gap-2">
                        <div className="size-1.5 rounded-full bg-current"></div>
                        Tu Petición
                    </h4>
                    <div className="relative group">
                        <div className="absolute -inset-0.5 bg-gradient-to-br from-[hsl(var(--primary))] to-transparent opacity-0 group-focus-within:opacity-20 transition-opacity rounded-[2rem] blur-xl"></div>
                        <div className="relative bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] group-focus-within:border-[hsl(var(--primary))] rounded-[2rem] p-6 shadow-inner transition-all">
                            <textarea
                                value={requestText}
                                onChange={(e) => setRequestText(e.target.value)}
                                className="w-full bg-transparent border-none focus:ring-0 text-[hsl(var(--text-primary))] placeholder-[hsl(var(--text-secondary)/0.5)] resize-none h-40 text-base leading-relaxed font-medium"
                                placeholder="Escribe tu petición aquí..."
                                required
                            />
                        </div>
                    </div>
                </section>

                {/* Privacy Options */}
                <section className="space-y-4">
                    <h4 className="text-[hsl(var(--primary))] text-[10px] uppercase font-black tracking-[0.2em] flex items-center gap-2 mb-6">
                        <div className="size-1.5 rounded-full bg-current"></div>
                        Privacidad & Seguridad
                    </h4>

                    <div className={`flex items-center justify-between p-6 rounded-3xl transition-all border ${isAnonymous ? 'bg-[hsl(var(--primary)/0.05)] border-[hsl(var(--primary)/0.3)] shadow-lg' : 'bg-[hsl(var(--surface-2))] border-[hsl(var(--border))]'}`}>
                        <div className="flex items-start gap-4">
                            <div className={`p-3 rounded-2xl shrink-0 transition-colors ${isAnonymous ? 'bg-[hsl(var(--primary))] text-white shadow-lg' : 'bg-[hsl(var(--surface-3))] text-[hsl(var(--text-secondary))]'}`}>
                                <Globe size={20} strokeWidth={2.5} />
                            </div>
                            <div className="flex flex-col pt-1">
                                <span className={`font-black text-sm uppercase tracking-tight transition-colors ${isAnonymous ? 'text-[hsl(var(--primary))]' : 'text-[hsl(var(--text-primary))]'}`}>Publicar como Anónimo</span>
                                <span className="text-[hsl(var(--text-secondary))] text-[11px] font-medium mt-1">Tu identidad no será visible en el muro público.</span>
                            </div>
                        </div>
                        <label className="relative inline-flex items-center cursor-pointer shrink-0">
                            <input type="checkbox" className="sr-only peer" checked={isAnonymous} onChange={() => setIsAnonymous(!isAnonymous)} />
                            <div className="w-12 h-6 bg-[hsl(var(--surface-3))] peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[4px] after:left-[4px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-[hsl(var(--primary))] border border-[hsl(var(--border))]"></div>
                        </label>
                    </div>

                    <div className={`flex items-center justify-between p-6 rounded-3xl transition-all border ${isConfidential ? 'bg-rose-500/5 border-rose-500/20 shadow-lg' : 'bg-[hsl(var(--surface-2))] border-[hsl(var(--border))]'}`}>
                        <div className="flex items-start gap-4">
                            <div className={`p-3 rounded-2xl shrink-0 transition-colors ${isConfidential ? 'bg-rose-500 text-white shadow-lg' : 'bg-[hsl(var(--surface-3))] text-[hsl(var(--text-secondary))]'}`}>
                                <Lock size={20} strokeWidth={2.5} />
                            </div>
                            <div className="flex flex-col pt-1">
                                <span className={`font-black text-sm uppercase tracking-tight transition-colors ${isConfidential ? 'text-rose-500' : 'text-[hsl(var(--text-primary))]'}`}>Confidencial</span>
                                <span className="text-[hsl(var(--text-secondary))] text-[11px] font-medium mt-1">Solo los pastores podrán ver esta petición.</span>
                            </div>
                        </div>
                        <label className="relative inline-flex items-center cursor-pointer shrink-0">
                            <input type="checkbox" className="sr-only peer" checked={isConfidential} onChange={() => setIsConfidential(!isConfidential)} />
                            <div className="w-12 h-6 bg-[hsl(var(--surface-3))] peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[4px] after:left-[4px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-rose-500 border border-[hsl(var(--border))]"></div>
                        </label>
                    </div>
                </section>

                {/* Submit Action */}
                <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    type="submit"
                    disabled={isSubmitting || !requestText.trim()}
                    className="w-full h-16 bg-[hsl(var(--text-primary))] text-[hsl(var(--bg-primary))] rounded-[2rem] font-black uppercase tracking-[0.2em] text-xs shadow-2xl hover:opacity-90 disabled:opacity-50 transition-all flex items-center justify-center gap-3"
                >
                    {isSubmitting ? (
                        <div className="flex items-center gap-2">
                            <div className="size-4 rounded-full border-2 border-current border-t-transparent animate-spin"></div>
                            Enviando...
                        </div>
                    ) : (
                        <>
                            <span>Enviar Petición</span>
                            <Send size={18} strokeWidth={2.5} />
                        </>
                    )}
                </motion.button>
            </form>
        </div>
    );
}

