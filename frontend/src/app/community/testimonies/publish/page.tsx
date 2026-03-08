"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { ArrowLeft, Send, Camera, EyeOff, Globe } from 'lucide-react';
import { useToast } from '@/context/ToastContext';

export default function PublishTestimony() {
    const { isAuthenticated } = useAuth();
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
        if (!testimonyText.trim()) return;

        setIsSubmitting(true);
        // Simulate API call
        setTimeout(() => {
            setIsSubmitting(false);
            addToast('¡Gracias por compartir tu historia!', 'success');

            router.push('/community/testimonies');
        }, 1200);
    };

    return (
        <div className="min-h-screen bg-slate-950 font-display text-slate-100 selection:bg-primary/30 relative overflow-x-hidden flex flex-col">
            {/* Ambient Backgrounds */}
            <div className="fixed inset-0 z-0 bg-slate-950 pointer-events-none">
                <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-[radial-gradient(circle_at_top_right,_var(--tw-gradient-stops))] from-primary/10 via-slate-950 to-slate-950 opacity-60 blur-3xl mix-blend-screen"></div>
            </div>

            <div className="relative z-10 max-w-4xl mx-auto flex flex-col h-screen w-full">
                {/* Header Section */}
                <header className="sticky top-0 z-50 bg-slate-950/80 backdrop-blur-xl px-6 py-4 border-b border-white/5 flex items-center justify-between">
                    <button onClick={() => router.back()} className="text-slate-300 flex size-10 items-center justify-center rounded-full hover:bg-white/10 transition-colors pointer-events-auto cursor-pointer">
                        <ArrowLeft size={20} />
                    </button>
                    <h2 className="text-white text-lg font-bold leading-tight tracking-tight flex-1 text-center pr-10">Publicar Testimonio</h2>
                </header>

                <main className="flex-1 px-6 flex flex-col pt-6 pb-24 overflow-y-auto hide-scrollbar z-10">
                    <form onSubmit={handleSubmit} className="flex flex-col h-full animate-in fade-in slide-in-from-bottom-8 duration-700">
                        <div className="mb-8">
                            <h1 className="text-white text-3xl font-black tracking-tight leading-tight">Cuéntanos tu historia</h1>
                            <p className="text-slate-400 mt-2 text-sm font-medium">Tu fe puede inspirar a otros hoy.</p>
                        </div>

                        {/* Testimony Text Area */}
                        <section className="mb-8">
                            <div className="bg-slate-900/50 backdrop-blur-xl border border-white/10 rounded-3xl p-5 min-h-[220px] flex flex-col shadow-inner focus-within:ring-2 focus-within:ring-primary/50 focus-within:border-primary/50 transition-all">
                                <textarea
                                    value={testimonyText}
                                    onChange={(e) => setTestimonyText(e.target.value)}
                                    className="w-full bg-transparent border-none focus:ring-0 text-white placeholder-slate-500 resize-none flex-1 text-base leading-relaxed"
                                    placeholder="Escribe tu testimonio aquí... ¿Qué hizo Dios en tu vida?"
                                    required
                                />
                            </div>
                        </section>

                        {/* Category Selector */}
                        <section className="mb-8 flex flex-col gap-4">
                            <h3 className="text-primary text-[10px] uppercase font-black tracking-widest flex items-center gap-2">
                                <div className="size-1.5 rounded-full bg-primary"></div>
                                Categoría
                            </h3>
                            <div className="flex flex-wrap gap-3">
                                {categories.map(category => (
                                    <button
                                        key={category}
                                        type="button"
                                        onClick={() => setSelectedCategory(category)}
                                        className={`flex h-11 shrink-0 items-center justify-center rounded-2xl px-6 transition-all text-xs font-bold uppercase tracking-widest whitespace-nowrap border ${selectedCategory === category
                                            ? 'bg-primary text-white shadow-lg shadow-primary/30 border-primary/50'
                                            : 'bg-slate-900/50 text-slate-400 hover:text-white border-white/5 hover:border-white/20'
                                            }`}
                                    >
                                        {category}
                                    </button>
                                ))}
                            </div>
                        </section>

                        {/* Media Upload Area */}
                        <section className="mb-8 flex flex-col gap-4">
                            <h3 className="text-primary text-[10px] uppercase font-black tracking-widest flex items-center gap-2">
                                <div className="size-1.5 rounded-full bg-primary"></div>
                                Multimedia (Opcional)
                            </h3>
                            <div className="border-2 border-dashed border-white/20 hover:border-primary/50 rounded-[2rem] p-10 flex flex-col items-center justify-center bg-slate-900/30 hover:bg-slate-900/60 transition-colors cursor-pointer group backdrop-blur-xl">
                                <div className="size-14 rounded-full bg-primary/10 flex items-center justify-center text-primary mb-4 shadow-sm group-hover:scale-110 group-hover:bg-primary group-hover:text-white border border-primary/20 transition-all">
                                    <Camera size={28} />
                                </div>
                                <p className="text-white font-bold text-sm">Añadir Foto o Video</p>
                                <p className="text-slate-500 text-xs mt-1.5 font-medium uppercase tracking-widest">Sube archivos hasta 50MB</p>
                            </div>
                        </section>

                        {/* Visibility Toggle */}
                        <section className="space-y-4 mb-10 flex-1">
                            <h3 className="text-primary text-[10px] uppercase font-black tracking-widest flex items-center gap-2 mb-4">
                                <div className="size-1.5 rounded-full bg-primary"></div>
                                Privacidad
                            </h3>
                            <div className={`flex items-center justify-between p-5 rounded-3xl transition-all border ${isAnonymous ? 'bg-primary/10 border-primary/30' : 'bg-slate-900/50 border-white/5'}`}>
                                <div className="flex items-start gap-4">
                                    <div className={`p-2.5 rounded-xl shrink-0 transition-colors ${isAnonymous ? 'bg-primary/20 text-primary' : 'bg-white/5 text-slate-400'}`}>
                                        <EyeOff size={20} />
                                    </div>
                                    <div className="flex flex-col pt-0.5">
                                        <span className={`font-bold text-sm transition-colors ${isAnonymous ? 'text-primary' : 'text-white'}`}>Publicar como Anónimo</span>
                                        <span className="text-slate-500 text-[11px] font-medium leading-tight mt-1">Tu nombre no será visible en el muro.</span>
                                    </div>
                                </div>
                                <label className="relative inline-flex items-center cursor-pointer shrink-0">
                                    <input type="checkbox" className="sr-only peer" checked={isAnonymous} onChange={() => setIsAnonymous(!isAnonymous)} />
                                    <div className="w-11 h-6 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary border border-white/10"></div>
                                </label>
                            </div>
                        </section>

                        {/* Bottom Actions */}
                        <button
                            type="submit"
                            disabled={isSubmitting || !testimonyText.trim()}
                            className="w-full bg-primary hover:bg-primary-600 disabled:opacity-50 disabled:bg-primary text-white py-4 rounded-2xl font-black uppercase tracking-widest text-sm shadow-xl shadow-primary/30 flex items-center justify-center gap-3 active:scale-[0.98] transition-all"
                        >
                            <span>{isSubmitting ? 'Publicando...' : 'Publicar Testimonio'}</span>
                            {!isSubmitting && <Send size={18} className="translate-x-[2px] translate-y-[-2px]" />}
                        </button>
                    </form>
                </main>
            </div>
        </div>
    );
}
