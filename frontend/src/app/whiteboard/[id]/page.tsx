"use client";

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { 
    LayoutDashboard, 
    Sparkles, 
    Wand2, 
    Plus, 
    Save, 
    ArrowLeft,
    Users,
    Share2,
    Download,
    Settings,
    History,
    Eraser,
    MousePointer2,
    Square,
    Circle,
    Type
} from 'lucide-react';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { useAuth } from '@/context/AuthContext';
import { toast } from 'sonner';
import clsx from 'clsx';
import { motion } from 'framer-motion';

export default function WhiteboardSessionPage() {
    const params = useParams();
    const id = params?.id as string;
    const router = useRouter();
    const { user } = useAuth();
    
    const [title, setTitle] = useState('Cargando lienzo...');
    const [tool, setTool] = useState<'select' | 'draw' | 'rect' | 'circle' | 'text'>('draw');

    useEffect(() => {
        // Mock loading session data
        if (id) {
            setTitle(id === '1' ? 'Plan Estratégico Faro 2026' : 'Lienzo Colaborativo');
        }
    }, [id]);

    return (
        <div className="flex flex-col h-full bg-[#f8fafc] dark:bg-[#0b0d11] overflow-hidden">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: 'CCF Tools', icon: LayoutDashboard, href: '/whiteboard' },
                    { label: title, icon: Sparkles },
                ]}
                rightActions={
                    <div className="flex items-center gap-3">
                        <div className="flex -space-x-2 mr-4">
                            {[1, 2, 3].map(i => (
                                <div key={i} className="size-8 rounded-full border-2 border-white dark:border-slate-900 bg-blue-500 flex items-center justify-center text-[10px] font-black text-white">
                                    {i === 1 ? 'JD' : i === 2 ? 'MA' : 'LP'}
                                </div>
                            ))}
                            <div className="size-8 rounded-full border-2 border-white dark:border-slate-900 bg-slate-200 dark:bg-white/10 flex items-center justify-center text-[10px] font-black text-slate-500">
                                +2
                            </div>
                        </div>
                        <button className="p-2 text-slate-400 hover:text-blue-600 transition-all">
                            <Share2 size={18} />
                        </button>
                        <button className="px-6 py-2 bg-blue-600 text-white rounded-xl text-[10px] font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:scale-105 transition-all flex items-center gap-2">
                            <Save size={14} /> Guardar
                        </button>
                    </div>
                }
            />

            <div className="flex-1 relative flex overflow-hidden">
                {/* Canvas Toolbar (Floating) */}
                <div className="absolute left-6 top-1/2 -translate-y-1/2 z-10 flex flex-col gap-2 p-2 bg-white/80 dark:bg-slate-900/80 backdrop-blur-xl border border-slate-200 dark:border-white/10 rounded-2xl shadow-2xl">
                    <ToolbarButton icon={MousePointer2} active={tool === 'select'} onClick={() => setTool('select')} label="Seleccionar" />
                    <ToolbarButton icon={Wand2} active={tool === 'draw'} onClick={() => setTool('draw')} label="Dibujo Libre" />
                    <ToolbarButton icon={Square} active={tool === 'rect'} onClick={() => setTool('rect')} label="Rectángulo" />
                    <ToolbarButton icon={Circle} active={tool === 'circle'} onClick={() => setTool('circle')} label="Círculo" />
                    <ToolbarButton icon={Type} active={tool === 'text'} onClick={() => setTool('text')} label="Texto" />
                    <div className="h-px bg-slate-100 dark:bg-white/5 mx-2 my-1" />
                    <ToolbarButton icon={Eraser} active={false} onClick={() => {}} label="Borrador" />
                </div>

                {/* Main Canvas Area */}
                <main className="flex-1 bg-white dark:bg-[#0f1114] bg-[radial-gradient(#e5e7eb_1px,transparent_1px)] dark:bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:32px_32px] cursor-crosshair relative">
                    {/* Placeholder for real canvas implementation */}
                    <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                        <div className="text-center space-y-4 opacity-20">
                            <Sparkles size={64} className="mx-auto" />
                            <p className="text-sm font-black uppercase tracking-[0.5em]">Lienzo Infinito Activado</p>
                        </div>
                    </div>

                    {/* Collaborative cursor mock */}
                    <motion.div 
                        animate={{ x: [100, 300, 200], y: [100, 150, 300] }}
                        transition={{ duration: 10, repeat: Infinity }}
                        className="absolute pointer-events-none flex flex-col items-start gap-1"
                    >
                        <MousePointer2 size={16} className="text-rose-500 fill-rose-500" />
                        <span className="px-2 py-0.5 bg-rose-500 text-white text-[9px] font-black rounded-full shadow-lg">Maria Garcia</span>
                    </motion.div>
                </main>

                {/* Side Panel (Contextual) */}
                <aside className="w-80 bg-white dark:bg-[#111418] border-l border-slate-200 dark:border-white/10 p-6 space-y-8 overflow-y-auto">
                    <section className="space-y-4">
                        <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400">Optimus Brain Assist</h3>
                        <div className="p-4 rounded-2xl bg-blue-500/10 border border-blue-500/20 space-y-3">
                            <p className="text-xs font-bold text-blue-600 leading-relaxed">
                                He detectado que estás diagramando un flujo de trabajo. ¿Quieres que genere las conexiones lógicas automáticamente?
                            </p>
                            <button className="w-full py-2 bg-blue-600 text-white rounded-xl text-[9px] font-black uppercase tracking-widest">
                                Generar Conexiones
                            </button>
                        </div>
                    </section>

                    <section className="space-y-4">
                        <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400">Capas e Historial</h3>
                        <div className="space-y-2">
                            {[1, 2, 3].map(i => (
                                <div key={i} className="flex items-center justify-between p-3 rounded-xl border border-slate-100 dark:border-white/5 text-xs font-medium text-slate-500">
                                    <div className="flex items-center gap-2">
                                        <History size={12} /> Trazo de Maria
                                    </div>
                                    <span className="text-[9px] opacity-50">Hace 2m</span>
                                </div>
                            ))}
                        </div>
                    </section>
                </aside>
            </div>
        </div>
    );
}

function ToolbarButton({ icon: Icon, active, onClick, label }: { icon: any, active: boolean, onClick: () => void, label: string }) {
    return (
        <button 
            onClick={onClick}
            title={label}
            className={clsx(
                'size-10 flex items-center justify-center rounded-xl transition-all group relative',
                active ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20' : 'text-slate-500 hover:bg-slate-100 dark:hover:bg-white/5'
            )}
        >
            <Icon size={20} />
            <span className="absolute left-full ml-4 px-2 py-1 bg-slate-900 text-white text-[9px] font-black uppercase tracking-widest rounded-lg opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity whitespace-nowrap z-50">
                {label}
            </span>
        </button>
    );
}
