"use client";

import React from 'react';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import { LayoutDashboard, Sparkles, Wand2, Plus } from 'lucide-react';
import { motion } from 'framer-motion';

export default function WhiteboardPage() {
    return (
        <WorkspaceLayout sidebarTitle="Herramientas / Pizarra">
            <div className="h-full flex flex-col items-center justify-center p-10 bg-slate-50 dark:bg-[#141517] font-display">
                <motion.div 
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="max-w-2xl text-center space-y-8"
                >
                    <div className="size-24 rounded-[2rem] bg-blue-600 flex items-center justify-center text-white mx-auto shadow-2xl shadow-blue-500/20">
                        <LayoutDashboard size={48} />
                    </div>
                    
                    <div className="space-y-4">
                        <h1 className="text-4xl font-black text-slate-900 dark:text-white tracking-tight">Lienzo Creativo Ministerial</h1>
                        <p className="text-lg text-slate-500 dark:text-slate-400 font-medium">
                            La herramienta de Pizarra Infinita está siendo integrada con el motor de IA para permitir cocreación en tiempo real.
                        </p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-left">
                        <FeatureCard icon={Sparkles} title="Cocreación Real-time" desc="Dibuja y diseña con tu equipo simultáneamente." />
                        <FeatureCard icon={Wand2} title="Diagramas con IA" desc="Convierte tus ideas en flujos de trabajo automáticamente." />
                    </div>

                    <button className="px-8 py-4 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-2xl text-xs font-black uppercase tracking-[0.2em] shadow-xl hover:opacity-90 transition-all">
                        Notificarme al Lanzamiento
                    </button>
                </motion.div>
            </div>
        </WorkspaceLayout>
    );
}

function FeatureCard({ icon: Icon, title, desc }: any) {
    return (
        <div className="p-6 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-3xl space-y-2">
            <Icon className="text-blue-600" size={20} />
            <h4 className="font-black text-sm text-slate-800 dark:text-white uppercase tracking-wider">{title}</h4>
            <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">{desc}</p>
        </div>
    );
}
