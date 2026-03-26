"use client";

import React from 'react';
import { motion } from 'framer-motion';
import { Search, MapPin, Compass, Sparkles, Plus } from 'lucide-react';

export default function DiscoverPage() {
    return (
        <div className="max-w-4xl mx-auto space-y-12 py-10 animate-in fade-in duration-700">
            <header className="text-center space-y-4">
                <div className="flex items-center justify-center gap-2 text-[hsl(var(--primary))] font-black uppercase tracking-[0.3em] text-[10px]">
                    <div className="size-2 rounded-full bg-current shadow-[0_0_10px_currentColor]"></div>
                    Explorar Comunidad
                </div>
                <h1 className="text-5xl font-black text-[hsl(var(--text-primary))] tracking-tighter">Descubrir</h1>
                <p className="text-[hsl(var(--text-secondary))] font-medium max-w-lg mx-auto italic">
                    &quot;Mirad cuán bueno y cuán delicioso es habitar los hermanos juntos en armonía.&quot; - Salmos 133:1
                </p>
            </header>

            <div className="relative group">
                <div className="absolute -inset-1 bg-gradient-to-r from-[hsl(var(--primary))] to-transparent opacity-10 blur-2xl rounded-[3rem]"></div>
                <div className="relative bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-[3rem] p-12 overflow-hidden shadow-sm">
                    <div className="absolute top-0 right-0 w-64 h-64 bg-[hsl(var(--primary)/0.03)] rounded-full blur-3xl"></div>
                    
                    <div className="flex flex-col items-center text-center space-y-8 relative z-10">
                        <div className="size-24 rounded-[2rem] bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] flex items-center justify-center text-[hsl(var(--primary))] shadow-sm">
                            <Compass size={48} strokeWidth={1} className="animate-pulse" />
                        </div>
                        
                        <div className="space-y-2">
                            <h3 className="text-2xl font-black text-[hsl(var(--text-primary))] tracking-tight">Mapa de Conexión</h3>
                            <p className="text-[hsl(var(--text-secondary))] text-sm font-medium max-w-sm">
                                Pronto podrás ver todos nuestros puntos de reunión y grupos en un mapa interactivo.
                            </p>
                        </div>

                        <div className="flex items-center gap-4">
                            <div className="h-12 px-6 rounded-2xl bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] flex items-center gap-2 text-[hsl(var(--text-secondary))] text-[10px] font-black uppercase tracking-widest">
                                <MapPin size={14} className="text-[hsl(var(--primary))]" />
                                Geolocalización activa
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div className="bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-[2.5rem] p-8 space-y-4 hover:border-[hsl(var(--primary)/0.3)] transition-all cursor-pointer group">
                    <div className="size-12 rounded-xl bg-[hsl(var(--primary)/0.1)] flex items-center justify-center text-[hsl(var(--primary))] group-hover:scale-110 transition-transform">
                        <Sparkles size={24} />
                    </div>
                    <h4 className="text-lg font-black text-[hsl(var(--text-primary))] tracking-tight">Intereses</h4>
                    <p className="text-xs text-[hsl(var(--text-secondary))] leading-relaxed font-medium">Contesta un breve test para recomendarte grupos según tus pasiones y etapa de vida.</p>
                </div>
                
                <div className="bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-[2.5rem] p-8 space-y-4 hover:border-[hsl(var(--primary)/0.3)] transition-all cursor-pointer group">
                    <div className="size-12 rounded-xl bg-[hsl(var(--primary)/0.1)] flex items-center justify-center text-[hsl(var(--primary))] group-hover:scale-110 transition-transform">
                        <Plus size={24} />
                    </div>
                    <h4 className="text-lg font-black text-[hsl(var(--text-primary))] tracking-tight">Referir un Grupo</h4>
                    <p className="text-xs text-[hsl(var(--text-secondary))] leading-relaxed font-medium">¿Conoces un grupo nuevo o quieres abrir uno en tu casa? Envíanos los detalles.</p>
                </div>
            </div>
        </div>
    );
}
