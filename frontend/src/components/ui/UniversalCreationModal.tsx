"use client";

import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    X, CheckSquare, FileText, Bell, LayoutDashboard, 
    Plus, Hash, ChevronRight, Sparkles, Target, 
    Flag, User, Calendar, Loader2, Search, Command
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
    const [projectSearch, setProjectSearch] = useState('');
    
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
                // Priorizar el proyecto ID 6 (El Faro) si existe
                const elFaro = data.find(p => p.id === 6);
                setSelectedProjectId(elFaro ? elFaro.id : data[0].id);
            }
        } catch (err) { console.error(err); }
    };

    const filteredProjects = projects.filter(p => 
        p.title.toLowerCase().includes(projectSearch.toLowerCase())
    );

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
                toast.success(`Tarea "${title}" creada con éxito`);
                resetAndClose();
            } else {
                toast.info(`La creación de ${type} se habilitará en la Fase 2.`);
            }
        } catch (err) {
            toast.error('Fallo técnico al crear el elemento.');
        } finally {
            setLoading(false);
        }
    };

    const resetAndClose = () => {
        setTitle('');
        setDescription('');
        onClose();
    };

    // Shortcut: Ctrl + Enter para enviar
    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
            handleSubmit();
        }
    };

    return (
        <Dialog.Root open={isOpen} onOpenChange={(open) => !open && onClose()}>
            <Dialog.Portal>
                <Dialog.Overlay className="fixed inset-0 z-[9000] bg-slate-900/60 backdrop-blur-md animate-in fade-in duration-300" />
                <Dialog.Content 
                    onKeyDown={handleKeyDown}
                    className="fixed left-1/2 top-1/2 z-[9001] w-full max-w-[800px] -translate-x-1/2 -translate-y-1/2 rounded-[3rem] bg-white dark:bg-[#1e1f21] shadow-[0_32px_64px_-12px_rgba(0,0,0,0.5)] border border-white/10 overflow-hidden animate-in zoom-in-95 duration-200 font-display"
                >
                    <Dialog.Title className="sr-only">Centro de Creación CCF</Dialog.Title>
                    
                    <div className="flex h-[600px]">
                        {/* Sidebar: Unificado con estética Pro */}
                        <aside className="w-64 bg-slate-50 dark:bg-black/20 border-r border-slate-100 dark:border-white/5 p-8 flex flex-col gap-3">
                            <div className="mb-8 px-2 flex items-center gap-2 text-blue-600">
                                <Command size={16} />
                                <h3 className="text-[10px] font-black uppercase tracking-[0.3em]">Operaciones</h3>
                            </div>
                            
                            <TypeTab active={type === 'task'} onClick={() => setType('task')} icon={CheckSquare} label="Nueva Tarea" color="text-blue-600" />
                            <TypeTab active={type === 'doc'} onClick={() => setType('doc')} icon={FileText} label="Documento" color="text-emerald-600" />
                            <TypeTab active={type === 'whiteboard'} onClick={() => setType('whiteboard')} icon={LayoutDashboard} label="Pizarra" color="text-orange-600" />
                            <TypeTab active={type === 'reminder'} onClick={() => setType('reminder')} icon={Bell} label="Recordatorio" color="text-rose-600" />

                            <div className="mt-auto relative group">
                                <div className="absolute -inset-1 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-2xl blur opacity-20 group-hover:opacity-40 transition-opacity" />
                                <div className="relative p-5 bg-white dark:bg-black/40 rounded-2xl border border-blue-600/10">
                                    <div className="flex items-center gap-2 mb-2">
                                        <Sparkles size={14} className="text-blue-600" />
                                        <span className="text-[9px] font-black uppercase tracking-widest text-blue-600">Optimus AI</span>
                                    </div>
                                    <p className="text-[10px] font-bold text-slate-500 leading-relaxed italic">Presiona Ctrl+Enter para crear al instante.</p>
                                </div>
                            </div>
                        </aside>

                        {/* Form: Grado Ministerial */}
                        <main className="flex-1 flex flex-col min-w-0 bg-white dark:bg-transparent">
                            <header className="h-16 border-b border-slate-100 dark:border-white/5 flex items-center px-10 justify-between">
                                <div className="flex items-center gap-3">
                                    <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">Creando en</span>
                                    <ChevronRight size={12} className="text-slate-300" />
                                    <div className="flex items-center gap-2 px-3 py-1 bg-blue-50 dark:bg-blue-900/20 rounded-full border border-blue-100 dark:border-blue-800">
                                        <div className="size-1.5 rounded-full bg-blue-600 animate-pulse" />
                                        <span className="text-[10px] font-black text-blue-600 uppercase tracking-widest">Workspace Principal</span>
                                    </div>
                                </div>
                                <Dialog.Close asChild>
                                    <button className="p-2 hover:bg-slate-100 dark:hover:bg-white/5 rounded-full transition-all hover:rotate-90 text-slate-400">
                                        <X size={20} />
                                    </button>
                                </Dialog.Close>
                            </header>

                            <form onSubmit={handleSubmit} className="flex-1 flex flex-col p-10 overflow-y-auto scrollbar-hide">
                                <div className="space-y-8">
                                    <div className="space-y-4">
                                        <input 
                                            ref={titleRef}
                                            value={title}
                                            onChange={(e) => setTitle(e.target.value)}
                                            placeholder={`¿Cuál es la nueva ${type === 'task' ? 'misión' : type}?`}
                                            className="w-full bg-transparent text-3xl font-black outline-none placeholder:text-slate-200 dark:placeholder:text-slate-800 tracking-tight"
                                        />
                                        <textarea 
                                            value={description}
                                            onChange={(e) => setDescription(e.target.value)}
                                            placeholder="Detalla los objetivos o añade contexto para el equipo..."
                                            className="w-full bg-transparent text-base font-medium outline-none placeholder:text-slate-300 resize-none min-h-[100px] leading-relaxed"
                                        />
                                    </div>

                                    {type === 'task' && (
                                        <div className="grid grid-cols-1 gap-6 pt-8 border-t border-slate-100 dark:border-white/5">
                                            {/* Selector de Proyecto con búsqueda sutil */}
                                            <div className="space-y-3">
                                                <label className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400 flex items-center gap-2">
                                                    <Target size={14} /> Proyecto de Destino
                                                </label>
                                                <div className="relative group">
                                                    <Search size={14} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-blue-600 transition-colors" />
                                                    <select 
                                                        value={selectedProjectId || ''}
                                                        onChange={(e) => setSelectedProjectId(Number(e.target.value))}
                                                        className="w-full bg-slate-50 dark:bg-black/40 border border-slate-200 dark:border-white/10 rounded-2xl pl-10 pr-4 py-4 text-sm font-black outline-none focus:ring-4 focus:ring-blue-500/10 transition-all appearance-none cursor-pointer"
                                                    >
                                                        {projects.map(p => (
                                                            <option key={p.id} value={p.id}>{p.title}</option>
                                                        ))}
                                                    </select>
                                                </div>
                                            </div>

                                            <div className="flex gap-6">
                                                <div className="flex-1 space-y-3">
                                                    <label className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">Prioridad</label>
                                                    <div className="flex gap-2 p-1 bg-slate-50 dark:bg-black/20 rounded-2xl border border-slate-100 dark:border-white/5">
                                                        {['low', 'normal', 'high'].map(p => (
                                                            <button
                                                                key={p}
                                                                type="button"
                                                                onClick={() => setPriority(p)}
                                                                className={clsx(
                                                                    "flex-1 py-2.5 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all",
                                                                    priority === p 
                                                                        ? "bg-white dark:bg-white/10 text-slate-900 dark:text-white shadow-sm ring-1 ring-slate-200 dark:ring-white/10" 
                                                                        : "text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                                                                )}
                                                            >
                                                                {p === 'high' ? 'Alta' : p === 'normal' ? 'Normal' : 'Baja'}
                                                            </button>
                                                        ))}
                                                    </div>
                                                </div>
                                                <div className="flex-1 space-y-3">
                                                    <label className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">Entrega Estimada</label>
                                                    <button type="button" className="w-full flex items-center justify-between px-5 py-3.5 bg-slate-50 dark:bg-black/20 border border-slate-100 dark:border-white/5 rounded-2xl text-[11px] font-bold text-slate-500">
                                                        <span>Seleccionar fecha...</span>
                                                        <Calendar size={14} />
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                </div>

                                <div className="mt-auto pt-10 flex items-center justify-between border-t border-slate-100 dark:border-white/5">
                                    <div className="flex gap-3">
                                        <button type="button" className="flex items-center gap-2 px-4 py-2.5 bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-2xl text-[10px] font-black uppercase tracking-widest text-slate-500 hover:bg-slate-100 transition-all">
                                            <User size={14} /> Asignar
                                        </button>
                                        <button type="button" className="flex items-center gap-2 px-4 py-2.5 bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-2xl text-[10px] font-black uppercase tracking-widest text-slate-500 hover:bg-slate-100 transition-all">
                                            <Hash size={14} /> Etiquetas
                                        </button>
                                    </div>
                                    <button 
                                        type="submit"
                                        disabled={loading || !title.trim()}
                                        className="px-10 py-4 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-[1.5rem] text-[11px] font-black uppercase tracking-[0.3em] shadow-2xl hover:scale-[1.05] active:scale-95 transition-all flex items-center gap-4 disabled:opacity-50"
                                    >
                                        {loading ? <Loader2 size={16} className="animate-spin" /> : <Plus size={16} />} 
                                        Lanzar {type === 'task' ? 'Tarea' : type}
                                    </button>
                                </div>
                            </form>
                        </main>
                    </div>
                </Dialog.Content>
            </Dialog.Portal>
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
            <span className={clsx("text-sm font-black tracking-tight", active ? "text-slate-900 dark:text-white" : "text-slate-500")}>{label}</span>
        </button>
    );
}
