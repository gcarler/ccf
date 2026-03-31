"use client";

import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    X, CheckSquare, FileText, Bell, LayoutDashboard, 
    Plus, Hash, ChevronRight, Sparkles, Target, 
    Flag, User, Calendar, Loader2, Search, Command,
    Wand2, Globe, Layers, Zap
} from 'lucide-react';
import * as Dialog from '@radix-ui/react-dialog';
import clsx from 'clsx';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { toast } from 'sonner';
import type { ProjectRecord } from '@/types/projects';

type CreationType = 'task' | 'doc' | 'reminder' | 'whiteboard' | 'panel';

interface Props {
    isOpen: boolean;
    onClose: () => void;
    initialType?: CreationType;
}

export default function UniversalCreationModal({ isOpen, onClose, initialType = 'task' }: Props) {
    const { token } = useAuth();
    const [type, setType] = useState<CreationType>(initialType);
    const [projects, setProjects] = useState<ProjectRecord[]>([]);
    const [loading, setLoading] = useState(false);
    const [isAiGenerating, setIsAiGenerating] = useState(false);
    
    // Form States
    const [title, setTitle] = useState('');
    const [description, setDescription] = useState('');
    const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);
    const [priority, setPriority] = useState('normal');

    const titleRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        if (isOpen) {
            setType(initialType);
            fetchProjects();
            setTimeout(() => titleRef.current?.focus(), 150);
        }
    }, [isOpen, initialType]);

    const fetchProjects = async () => {
        if (!token) return;
        try {
            const data = await apiFetch<ProjectRecord[]>('/projects', { token });
            setProjects(data);
            if (data.length > 0 && !selectedProjectId) {
                const elFaro = data.find(p => p.id === 6);
                setSelectedProjectId(elFaro ? elFaro.id : data[0].id);
            }
        } catch (err) { console.error(err); }
    };

    const handleAiGenerate = async () => {
        if (!title.trim()) {
            toast.error("Escribe un título para que la IA tenga contexto.");
            return;
        }
        setIsAiGenerating(true);
        try {
            const data = await apiFetch<{response: string}>('/system/ai/generate', {
                method: 'POST',
                token,
                body: { 
                    prompt: `Genera una descripción profesional para esta tarea ministerial: ${title}`,
                    context: `Tipo: ${type}, Prioridad: ${priority}`
                }
            });
            setDescription(data.response);
            toast.success("IA: Sugerencia generada");
        } catch (err) {
            toast.error("IA local no disponible");
        } finally {
            setIsAiGenerating(false);
        }
    };

    const handleSubmit = async (e?: React.FormEvent) => {
        if (e) e.preventDefault();
        if (!title.trim() || !selectedProjectId) return;
        
        setLoading(true);
        try {
            if (type === 'task') {
                await apiFetch(`/projects/${selectedProjectId}/tasks`, {
                    method: 'POST',
                    token,
                    body: { title: title.trim(), description, status: 'todo', priority }
                });
                toast.success(`Misión lanzada exitosamente`);
                resetAndClose();
            } else {
                toast.info(`La creación de ${type} estará disponible pronto.`);
            }
        } catch (err) {
            toast.error('Error al sincronizar creación.');
        } finally {
            setLoading(false);
        }
    };

    const resetAndClose = () => {
        setTitle('');
        setDescription('');
        onClose();
    };

    return (
        <Dialog.Root open={isOpen} onOpenChange={(open) => !open && onClose()}>
            <AnimatePresence>
                {isOpen && (
                    <Dialog.Portal forceMount>
                        <Dialog.Overlay asChild>
                            <motion.div 
                                initial={{ opacity: 0 }} 
                                animate={{ opacity: 1 }} 
                                exit={{ opacity: 0 }} 
                                className="fixed inset-0 z-[9000] bg-slate-900/20 backdrop-blur-[2px]" 
                            />
                        </Dialog.Overlay>
                        <Dialog.Content asChild>
                            <motion.div 
                                initial={{ x: '100%' }} 
                                animate={{ x: 0 }} 
                                exit={{ x: '100%' }}
                                transition={{ type: 'spring', damping: 25, stiffness: 200 }}
                                className="fixed right-0 top-0 z-[9001] h-screen w-full max-w-[850px] bg-white dark:bg-[#1e1f21] shadow-2xl border-l border-slate-200 dark:border-white/5 flex overflow-hidden font-display"
                            >
                                <Dialog.Title className="sr-only">Centro de Lanzamiento</Dialog.Title>
                                
                                <div className="flex w-full h-full">
                                    {/* Sidebar Interno del Drawer: Herramientas (Estética Original) */}
                                    <aside className="w-64 bg-slate-50 dark:bg-black/20 border-r border-slate-100 dark:border-white/5 p-8 flex flex-col gap-3 shrink-0">
                                        <div className="mb-8 px-2 flex items-center gap-2 text-blue-600">
                                            <Zap size={16} />
                                            <h3 className="text-[10px] font-black uppercase tracking-[0.3em]">Operaciones</h3>
                                        </div>
                                        
                                        <TypeTab active={type === 'task'} onClick={() => setType('task')} icon={CheckSquare} label="Nueva Tarea" color="text-blue-600" />
                                        <TypeTab active={type === 'doc'} onClick={() => setType('doc')} icon={FileText} label="Documento" color="text-emerald-600" />
                                        <TypeTab active={type === 'whiteboard'} onClick={() => setType('whiteboard')} icon={LayoutDashboard} label="Pizarra" color="text-orange-600" />
                                        <TypeTab active={type === 'reminder'} onClick={() => setType('reminder')} icon={Bell} label="Recordatorio" color="text-rose-600" />

                                        <div className="mt-auto relative group cursor-pointer" onClick={handleAiGenerate}>
                                            <div className="absolute -inset-1 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-3xl blur opacity-20 group-hover:opacity-50 transition-opacity" />
                                            <div className="relative p-5 bg-white dark:bg-black/40 rounded-3xl border border-blue-600/10 text-center">
                                                {isAiGenerating ? <Loader2 size={24} className="animate-spin text-blue-600 mx-auto" /> : <Sparkles size={24} className="text-blue-600 mx-auto mb-2" />}
                                                <span className="text-[10px] font-black uppercase tracking-widest text-blue-600 leading-none">Optimus IA</span>
                                                <p className="text-[9px] font-bold text-slate-500 mt-2 uppercase tracking-tighter">Redactar con Llama 3</p>
                                            </div>
                                        </div>
                                    </aside>

                                    {/* Form Content */}
                                    <main className="flex-1 flex flex-col min-w-0 bg-white dark:bg-transparent">
                                        <header className="h-16 border-b border-slate-100 dark:border-white/5 flex items-center px-10 justify-between bg-slate-50/30">
                                            <div className="flex items-center gap-3">
                                                <Dialog.Close asChild>
                                                    <button className="p-2 hover:bg-slate-200 dark:hover:bg-white/10 rounded-xl transition-all text-slate-400">
                                                        <ChevronRight size={20} className="rotate-180" />
                                                    </button>
                                                </Dialog.Close>
                                                <div className="h-6 w-[1px] bg-slate-200 dark:bg-white/10 mx-1" />
                                                <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">Ventana de Creación</span>
                                            </div>
                                            <Dialog.Close asChild>
                                                <button className="p-2 text-slate-400 hover:bg-slate-100 dark:hover:bg-white/5 rounded-full transition-all">
                                                    <X size={20} />
                                                </button>
                                            </Dialog.Close>
                                        </header>

                                        <form onSubmit={handleSubmit} className="flex-1 flex flex-col p-12 overflow-y-auto scrollbar-hide">
                                            <div className="space-y-12">
                                                {/* Title & Description Bento */}
                                                <div className="space-y-6">
                                                    <input 
                                                        ref={titleRef}
                                                        value={title}
                                                        onChange={(e) => setTitle(e.target.value)}
                                                        placeholder={`¿Cuál es la nueva misión?`}
                                                        className="w-full bg-transparent text-5xl font-black outline-none placeholder:text-slate-100 dark:placeholder:text-slate-800 tracking-tight"
                                                    />
                                                    <textarea 
                                                        value={description}
                                                        onChange={(e) => setDescription(e.target.value)}
                                                        placeholder="Establece los objetivos estratégicos..."
                                                        className="w-full bg-transparent text-lg font-medium outline-none placeholder:text-slate-200 resize-none min-h-[150px] leading-relaxed"
                                                    />
                                                </div>

                                                {type === 'task' && (
                                                    <div className="grid grid-cols-1 gap-10 pt-10 border-t border-slate-100 dark:border-white/5">
                                                        {/* Project Selection */}
                                                        <div className="space-y-4">
                                                            <label className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-400">Proyecto Destino</label>
                                                            <div className="grid grid-cols-2 gap-3">
                                                                {projects.slice(0, 4).map(p => (
                                                                    <button 
                                                                        key={p.id}
                                                                        type="button"
                                                                        onClick={() => setSelectedProjectId(p.id)}
                                                                        className={clsx(
                                                                            "flex items-center gap-3 p-4 rounded-[1.5rem] border transition-all text-left",
                                                                            selectedProjectId === p.id 
                                                                                ? "bg-blue-600 border-blue-600 text-white shadow-xl shadow-blue-500/20" 
                                                                                : "bg-slate-50 dark:bg-white/5 border-slate-100 dark:border-white/10 text-slate-600 dark:text-slate-300 hover:border-blue-500/50"
                                                                        )}
                                                                    >
                                                                        <div className="size-8 rounded-lg bg-white/20 flex items-center justify-center font-black text-[10px]">
                                                                            {p.title.substring(0, 1)}
                                                                        </div>
                                                                        <span className="text-[12px] font-bold truncate">{p.title}</span>
                                                                    </button>
                                                                ))}
                                                            </div>
                                                        </div>

                                                        {/* Priority & Delivery */}
                                                        <div className="flex gap-10">
                                                            <div className="flex-1 space-y-4">
                                                                <label className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-400">Urgencia</label>
                                                                <div className="flex gap-2 p-1 bg-slate-50 dark:bg-black/20 rounded-2xl border border-slate-100 dark:border-white/5">
                                                                    {['low', 'normal', 'high'].map(p => (
                                                                        <button
                                                                            key={p}
                                                                            type="button"
                                                                            onClick={() => setPriority(p)}
                                                                            className={clsx(
                                                                                "flex-1 py-3 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all",
                                                                                priority === p 
                                                                                    ? "bg-white dark:bg-white/10 text-slate-900 dark:text-white shadow-sm ring-1 ring-slate-200 dark:ring-white/10" 
                                                                                    : "text-slate-400 hover:text-slate-600"
                                                                            )}
                                                                        >
                                                                            {p}
                                                                        </button>
                                                                    ))}
                                                                </div>
                                                            </div>
                                                            <div className="flex-1 space-y-4">
                                                                <label className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-400">Fecha Meta</label>
                                                                <button type="button" className="w-full flex items-center justify-between px-6 py-4 bg-slate-50 dark:bg-black/20 border border-slate-100 dark:border-white/5 rounded-2xl text-[11px] font-bold text-slate-500">
                                                                    <span>Seleccionar...</span>
                                                                    <Calendar size={16} />
                                                                </button>
                                                            </div>
                                                        </div>
                                                    </div>
                                                )}
                                            </div>

                                            <div className="mt-auto pt-12 flex items-center justify-between border-t border-slate-100 dark:border-white/5">
                                                <div className="flex gap-3">
                                                    <ActionButton icon={User} label="Asignar" />
                                                    <ActionButton icon={Hash} label="Etiquetas" />
                                                </div>
                                                <button 
                                                    type="submit"
                                                    disabled={loading || isAiGenerating || !title.trim()}
                                                    className="px-12 py-5 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-[2rem] text-[11px] font-black uppercase tracking-[0.4em] shadow-2xl hover:scale-[1.02] active:scale-95 transition-all flex items-center gap-4 disabled:opacity-50"
                                                >
                                                    {loading ? <Loader2 size={18} className="animate-spin" /> : <Plus size={18} />} 
                                                    Lanzar {type === 'task' ? 'Misión' : type}
                                                </button>
                                            </div>
                                        </form>
                                    </main>
                                </div>
                            </motion.div>
                        </Dialog.Content>
                    </Dialog.Portal>
                )}
            </AnimatePresence>
        </Dialog.Root>
    );
}

function TypeTab({ active, onClick, icon: Icon, label, color }: any) {
    return (
        <button
            onClick={onClick}
            className={clsx(
                "flex items-center gap-4 px-5 py-4 rounded-[1.5rem] transition-all group relative overflow-hidden",
                active ? "bg-white dark:bg-white/10 shadow-xl border border-slate-100 dark:border-white/5" : "hover:bg-white/50 dark:hover:bg-white/5"
            )}
        >
            {active && <motion.div layoutId="activeCreationTab" className="absolute left-0 top-4 bottom-4 w-1 bg-blue-600 rounded-full" />}
            <Icon size={20} className={clsx("transition-transform group-hover:scale-110", active ? color : "text-slate-400 group-hover:text-slate-600")} />
            <span className={clsx("text-[13px] font-black tracking-tight uppercase", active ? "text-slate-900 dark:text-white" : "text-slate-500")}>{label}</span>
        </button>
    );
}

function ActionButton({ icon: Icon, label }: any) {
    return (
        <button type="button" className="flex items-center gap-2 px-4 py-2.5 bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-2xl text-[10px] font-black uppercase tracking-widest text-slate-500 hover:bg-slate-100 transition-all">
            <Icon size={14} /> {label}
        </button>
    );
}
