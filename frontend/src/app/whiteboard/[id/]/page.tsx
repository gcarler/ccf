"use client";

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { 
    LayoutDashboard, 
    Sparkles, 
    Plus, 
    ChevronLeft, 
    Users, 
    MousePointer2, 
    Type, 
    Square, 
    Circle, 
    Minus, 
    Wand2, 
    Smile, 
    Share2, 
    Download, 
    MoreHorizontal,
    Bot,
    Save,
    History,
    Layers,
    Grid3X3,
    Maximize2
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import CrmShell from '@/components/crm/CrmShell';
import AdminHero from '@/components/admin/AdminHero';
import clsx from 'clsx';
import { motion, AnimatePresence } from 'framer-motion';

export default function WhiteboardDetailPage() {
    const { id } = useParams();
    const router = useRouter();
    const { addToast } = useToast();

    const [board, setBoard] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [selectedTool, setSelectedTool] = useState('select');

    useEffect(() => {
        // Mocking load
        setTimeout(() => {
            setBoard({
                id,
                name: id === '1' ? 'Plan Estratégico Faro 2026' : 'Lienzo Colaborativo',
                updated: 'Hace 2 horas',
                members: [
                    { name: 'R', color: 'bg-emerald-500' },
                    { name: 'M', color: 'bg-blue-500' },
                    { name: 'J', color: 'bg-purple-500' },
                ]
            });
            setLoading(false);
        }, 800);
    }, [id]);

    if (loading) return (
        <CrmShell breadcrumbs={[{ label: 'Herramientas', icon: LayoutDashboard }, { label: 'Cargando Lienzo...' }]}>
            <div className="flex flex-col items-center justify-center h-full space-y-4">
                <Sparkles size={48} className="text-blue-500 animate-pulse opacity-20" />
                <p className="text-[10px] font-black text-slate-400 tracking-[0.4em] uppercase">Sincronizando Capas...</p>
            </div>
        </CrmShell>
    );

    return (
        <CrmShell
            breadcrumbs={[
                { label: 'CCF Tools', icon: LayoutDashboard },
                { label: 'Pizarras', icon: Sparkles },
                { label: board.name, icon: Square }
            ]}
        >
            <div className="flex flex-col h-full bg-[#f0f2f5] dark:bg-[#0b0c0d] relative overflow-hidden">
                
                {/* ─── Canvas Header ─── */}
                <div className="absolute top-6 left-6 right-6 z-20 flex items-center justify-between pointer-events-none">
                    <div className="flex items-center gap-4 pointer-events-auto">
                        <button 
                            onClick={() => router.push('/whiteboard')}
                            className="p-3 bg-white dark:bg-slate-900 rounded-2xl shadow-xl border border-slate-200 dark:border-white/10 text-slate-600 dark:text-slate-400 hover:text-blue-600 transition-all"
                        >
                            <ChevronLeft size={20} />
                        </button>
                        <div className="bg-white dark:bg-slate-900 px-6 py-3 rounded-2xl shadow-xl border border-slate-200 dark:border-white/10">
                            <h1 className="text-sm font-black uppercase tracking-tight text-slate-900 dark:text-white">{board.name}</h1>
                        </div>
                    </div>

                    <div className="flex items-center gap-3 pointer-events-auto">
                        <div className="flex -space-x-2 mr-4">
                            {board.members.map((m: any, i: number) => (
                                <div key={i} className={clsx("size-9 rounded-full border-2 border-white dark:border-slate-950 flex items-center justify-center text-[10px] font-black text-white shadow-lg", m.color)}>
                                    {m.name}
                                </div>
                            ))}
                            <button className="size-9 rounded-full bg-slate-200 dark:bg-white/10 border-2 border-white dark:border-slate-950 flex items-center justify-center text-[10px] text-slate-500"><Plus size={14} /></button>
                        </div>
                        <button className="p-3 bg-blue-600 text-white rounded-2xl shadow-xl shadow-blue-500/20 hover:scale-105 transition-all"><Share2 size={18} /></button>
                    </div>
                </div>

                {/* ─── Floating Toolbar ─── */}
                <div className="absolute left-6 top-1/2 -translate-y-1/2 z-20 flex flex-col gap-2 p-2 bg-white dark:bg-slate-900 rounded-[2rem] shadow-2xl border border-slate-200 dark:border-white/10">
                    {[
                        { id: 'select', icon: MousePointer2 },
                        { id: 'text', icon: Type },
                        { id: 'rect', icon: Square },
                        { id: 'circle', icon: Circle },
                        { id: 'line', icon: Minus },
                        { id: 'ia', icon: Wand2, color: 'text-purple-500' },
                    ].map(tool => (
                        <button
                            key={tool.id}
                            onClick={() => setSelectedTool(tool.id)}
                            className={clsx(
                                "p-4 rounded-2xl transition-all relative group",
                                selectedTool === tool.id 
                                    ? "bg-blue-50 dark:bg-blue-600/20 text-blue-600" 
                                    : tool.color || "text-slate-400 hover:bg-slate-50 dark:hover:bg-white/5"
                            )}
                        >
                            <tool.icon size={22} />
                            {selectedTool === tool.id && <motion.div layoutId="tool-dot" className="absolute right-1 top-1 size-1.5 rounded-full bg-blue-600" />}
                        </button>
                    ))}
                </div>

                {/* ─── Mock Infinite Canvas ─── */}
                <div className="flex-1 relative cursor-crosshair overflow-hidden group">
                    <div className="absolute inset-0 bg-[#f0f2f5] dark:bg-[#0b0c0d]" 
                         style={{ 
                            backgroundImage: `radial-gradient(#d1d5db 0.5px, transparent 0.5px)`, 
                            backgroundSize: '24px 24px',
                            opacity: 0.5
                         }} 
                    />
                    
                    {/* Simulated Content Nodes */}
                    <motion.div 
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="absolute left-[30%] top-[25%] p-8 bg-white dark:bg-slate-900 rounded-3xl shadow-2xl border-2 border-blue-500/20 w-[400px] space-y-4"
                    >
                        <div className="flex items-center gap-2 text-[10px] font-black text-blue-600 uppercase tracking-widest">
                            <History size={14} /> Historial de Cambios
                        </div>
                        <h2 className="text-xl font-black uppercase italic tracking-tighter">Estructura Faro 2026</h2>
                        <p className="text-sm text-slate-500 dark:text-slate-400 leading-relaxed font-medium">
                            Definición de las capas de la malla agéntica para la integración con el CMS v2 y el CRM pastoral.
                        </p>
                        <div className="flex gap-2">
                            <span className="px-3 py-1 bg-slate-100 dark:bg-white/5 rounded-lg text-[10px] font-bold">Arquitectura</span>
                            <span className="px-3 py-1 bg-slate-100 dark:bg-white/5 rounded-lg text-[10px] font-bold">IT</span>
                        </div>
                    </motion.div>

                    <motion.div 
                        initial={{ opacity: 0, scale: 0.8 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ delay: 0.3 }}
                        className="absolute left-[55%] top-[50%] size-64 bg-yellow-100 dark:bg-amber-900/20 border-2 border-amber-500/30 rounded-lg shadow-xl -rotate-6 p-6 flex flex-col justify-between"
                    >
                        <p className="text-sm font-handwriting text-amber-900 dark:text-amber-200 leading-relaxed">
                            "Recordar integrar el validador de JWT en el nodo de seguridad antes del despliegue oficial."
                        </p>
                        <p className="text-[10px] font-black uppercase text-amber-700 dark:text-amber-500 text-right">- Pastor Rodrigo</p>
                    </motion.div>

                    {/* Cursor Simulation */}
                    <motion.div 
                        animate={{ x: [400, 600, 550], y: [300, 200, 450] }}
                        transition={{ repeat: Infinity, duration: 8, ease: "easeInOut" }}
                        className="absolute z-30 pointer-events-none flex flex-col items-center"
                    >
                        <MousePointer2 className="text-emerald-500 fill-emerald-500" size={20} />
                        <span className="mt-1 px-2 py-0.5 bg-emerald-500 text-white text-[8px] font-black rounded-md shadow-lg">RODRIGO</span>
                    </motion.div>
                </div>

                {/* ─── Bottom Actions ─── */}
                <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-20 flex items-center gap-3">
                    <div className="bg-white dark:bg-slate-900 p-1.5 rounded-[1.5rem] shadow-2xl border border-slate-200 dark:border-white/10 flex items-center gap-1">
                        <ZoomButton icon={Minus} onClick={() => {}} />
                        <span className="px-3 text-[10px] font-black text-slate-500 uppercase tracking-widest">100%</span>
                        <ZoomButton icon={Plus} onClick={() => {}} />
                    </div>
                    <div className="bg-white dark:bg-slate-900 p-1.5 rounded-[1.5rem] shadow-2xl border border-slate-200 dark:border-white/10 flex items-center gap-1">
                        <ActionButton icon={Grid3X3} label="Grid" />
                        <ActionButton icon={Layers} label="Layers" />
                        <div className="w-px h-6 bg-slate-100 dark:bg-white/10 mx-1" />
                        <ActionButton icon={Save} label="Save" primary />
                    </div>
                </div>

                {/* ─── AI Assist Sidebar ─── */}
                <div className="absolute right-6 top-24 bottom-24 w-80 z-20 bg-white/90 dark:bg-slate-900/90 backdrop-blur-xl rounded-[3rem] shadow-2xl border border-slate-200 dark:border-white/10 p-8 flex flex-col">
                    <div className="flex items-center gap-3 text-purple-600 mb-6">
                        <Bot size={24} />
                        <h2 className="text-lg font-black tracking-tight uppercase tracking-tighter">Optimus Creative</h2>
                    </div>
                    
                    <div className="flex-1 space-y-6 overflow-y-auto scrollbar-thin">
                        <div className="p-5 bg-purple-50 dark:bg-purple-900/10 rounded-3xl border border-purple-100 dark:border-purple-500/20">
                            <p className="text-xs text-slate-500 dark:text-slate-400 font-medium italic">
                                "He notado que estás diseñando un flujo de trabajo. ¿Quieres que genere un diagrama de secuencia basado en tus notas?"
                            </p>
                        </div>
                        <div className="space-y-3">
                            <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Sugerencias Visuales</h3>
                            <div className="grid grid-cols-2 gap-2">
                                <button className="p-4 bg-slate-50 dark:bg-white/5 rounded-2xl text-[10px] font-bold hover:bg-purple-600 hover:text-white transition-all">Mind Map</button>
                                <button className="p-4 bg-slate-50 dark:bg-white/5 rounded-2xl text-[10px] font-bold hover:bg-purple-600 hover:text-white transition-all">Flowchart</button>
                            </div>
                        </div>
                    </div>
                    
                    <button className="mt-6 w-full py-4 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-2xl text-[10px] font-black uppercase tracking-widest shadow-xl flex items-center justify-center gap-2">
                        <Wand2 size={14} /> Aplicar Magia IA
                    </button>
                </div>

            </div>
        </CrmShell>
    );
}

function ZoomButton({ icon: Icon, onClick }: any) {
    return (
        <button onClick={onClick} className="p-2.5 hover:bg-slate-100 dark:hover:bg-white/5 rounded-xl text-slate-400 transition-all">
            <Icon size={14} />
        </button>
    );
}

function ActionButton({ icon: Icon, label, primary }: any) {
    return (
        <button className={clsx(
            "flex items-center gap-2 px-4 py-2.5 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all",
            primary ? "bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-xl" : "text-slate-500 hover:bg-slate-100 dark:hover:bg-white/5"
        )}>
            <Icon size={16} /> {label}
        </button>
    );
}
