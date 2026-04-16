"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import CrmShell from '@/components/crm/CrmShell';
import AdminHero from '@/components/admin/AdminHero';
import { 
    LayoutDashboard, 
    Sparkles, 
    Wand2, 
    Plus, 
    FileText, 
    Clock, 
    Users, 
    ChevronRight,
    Search
} from 'lucide-react';
import { motion } from 'framer-motion';

const MOCK_BOARDS = [
    { id: 1, name: 'Plan Estratégico Faro 2026', owner: 'Pastor Rodrigo', updated: 'Hace 2 horas', members: 5 },
    { id: 2, name: 'Brainstorming Campaña Jóvenes', owner: 'Equipo Creativo', updated: 'Ayer', members: 12 },
    { id: 3, name: 'Arquitectura de Datos Malla', owner: 'IT Dept', updated: 'Hace 3 días', members: 3 },
];

export default function WhiteboardPage() {
    const router = useRouter();
    const [query, setQuery] = useState('');

    return (
        <CrmShell
            breadcrumbs={[
                { label: 'CCF Tools', icon: LayoutDashboard },
                { label: 'Lienzo Colaborativo', icon: Sparkles }
            ]}
        >
            <div className="space-y-8 px-8 py-8">
                <AdminHero 
                    eyebrow="PRODUCTIVIDAD"
                    title="Pizarras Infinitas"
                    description="Espacios de cocreación en tiempo real integrados con Optimus Brain para diagramación asistida."
                    tags={['Beta', 'Colaborativo', 'IA Assist']}
                    watchers={['Equipo Estratégico', 'Diseño']}
                    primaryAction={{ label: 'Nueva Pizarra', icon: Plus, onClick: () => {} }}
                />

                <div className="max-w-7xl mx-auto space-y-6">
                    <div className="relative max-w-md">
                        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                        <input 
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            placeholder="Buscar en tus lienzos..."
                            className="w-full bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-2xl py-3 pl-12 pr-4 text-sm outline-none focus:ring-4 focus:ring-blue-500/10 transition-all"
                        />
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {MOCK_BOARDS.map((board) => (
                            <motion.div
                                key={board.id}
                                whileHover={{ y: -4 }}
                                onClick={() => router.push(`/whiteboard/${board.id}`)}
                                className="bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[2.5rem] p-8 shadow-sm hover:shadow-xl hover:border-blue-500/30 transition-all cursor-pointer group"
                            >
                                <div className="flex items-center justify-between mb-6">
                                    <div className="size-14 rounded-2xl bg-blue-50 dark:bg-blue-600/10 text-blue-600 flex items-center justify-center group-hover:bg-blue-600 group-hover:text-white transition-all">
                                        <LayoutDashboard size={28} />
                                    </div>
                                    <ChevronRight className="text-slate-300 group-hover:text-blue-500 transition-colors" />
                                </div>

                                <h3 className="text-lg font-black text-slate-900 dark:text-white mb-2 leading-tight uppercase tracking-tight">{board.name}</h3>
                                
                                <div className="space-y-3 pt-4 border-t border-slate-100 dark:border-white/5">
                                    <div className="flex items-center gap-2 text-[10px] font-black text-slate-400 uppercase tracking-widest">
                                        <Clock size={12} /> Actualizado {board.updated}
                                    </div>
                                    <div className="flex items-center gap-2 text-[10px] font-black text-blue-500 uppercase tracking-widest">
                                        <Users size={12} /> {board.members} integrantes activos
                                    </div>
                                </div>
                            </motion.div>
                        ))}

                        <div className="border-2 border-dashed border-slate-200 dark:border-white/10 rounded-[2.5rem] flex flex-col items-center justify-center p-8 text-center space-y-4 hover:bg-slate-50 dark:hover:bg-white/5 transition-all cursor-pointer">
                            <Plus className="text-slate-300" size={32} />
                            <p className="text-xs font-black uppercase tracking-widest text-slate-400">Crear lienzo en blanco</p>
                        </div>
                    </div>
                </div>
            </div>
        </CrmShell>
    );
}

