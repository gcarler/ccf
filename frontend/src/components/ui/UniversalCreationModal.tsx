"use client";

import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    X, CheckSquare, FileText, Bell, LayoutDashboard, 
    Plus, Hash, ChevronRight, Sparkles, Target, 
    Flag, User, Calendar, Loader2, Search, Command, AlignLeft
} from 'lucide-react';
import * as Dialog from '@radix-ui/react-dialog';
import clsx from 'clsx';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { toast } from 'sonner';
import type { ProjectRecord } from '@/types/projects';

type CreationType = 'task' | 'doc' | 'reminder' | 'whiteboard' | 'panel';

const TABS: { id: CreationType; label: string }[] = [
    { id: 'task',       label: 'Tarea'        },
    { id: 'doc',        label: 'Documento'    },
    { id: 'reminder',   label: 'Recordatorio' },
    { id: 'whiteboard', label: 'Pizarra'      },
    { id: 'panel',      label: 'Panel'        },
];

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
                toast.success(`Tarea lanzada exitosamente`);
                resetAndClose();
            } else {
                toast.info(`La creación de ${type} se habilitará en la Fase 2.`);
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
        <AnimatePresence>
            {isOpen && (
                <>
                    {/* Backdrop */}
                    <motion.div
                        key="ucm-backdrop"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={onClose}
                        className="fixed inset-0 z-[8999] bg-black/20 backdrop-blur-[2px]"
                    />

                    {/* Floating panel */}
                    <motion.div
                        key="ucm-panel"
                        initial={{ opacity: 0, scale: 0.96, y: 16 }}
                        animate={{ opacity: 1, scale: 1,    y: 0  }}
                        exit={{   opacity: 0, scale: 0.96, y:  8  }}
                        transition={{ type: 'spring', stiffness: 380, damping: 30 }}
                        className="fixed left-1/2 top-[10vh] -translate-x-1/2 z-[9000] w-full max-w-[680px] rounded-2xl bg-white dark:bg-[#1e1f21] shadow-2xl border border-slate-200 dark:border-white/10 overflow-hidden flex flex-col"
                        style={{ maxHeight: '80vh' }}
                    >
                        {/* Tab bar — text only, no icons */}
                        <header className="shrink-0 border-b border-slate-100 dark:border-white/5 bg-white dark:bg-[#1e1f21]">
                            <div className="flex items-center px-5 pt-1">
                                {TABS.map(tab => (
                                    <button
                                        key={tab.id}
                                        onClick={() => setType(tab.id)}
                                        className={clsx(
                                            'relative px-4 py-3 text-[13px] font-semibold transition-colors whitespace-nowrap',
                                            type === tab.id
                                                ? 'text-slate-900 dark:text-white'
                                                : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-300'
                                        )}
                                    >
                                        {tab.label}
                                        {type === tab.id && (
                                            <motion.div
                                                layoutId="ucm-underline"
                                                className="absolute bottom-0 inset-x-2 h-[2px] bg-slate-900 dark:bg-white rounded-full"
                                            />
                                        )}
                                    </button>
                                ))}
                                <button
                                    onClick={resetAndClose}
                                    className="ml-auto p-1.5 hover:bg-slate-100 dark:hover:bg-white/10 rounded-lg text-slate-400 transition-all hover:rotate-90 duration-200"
                                >
                                    <X size={16} />
                                </button>
                            </div>
                        </header>

                        {/* Content area */}
                        <div className="flex-1 overflow-y-auto">
                            <AnimatePresence mode="wait">
                                {type === 'task' && (
                                    <motion.div key="task" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                                        <form onSubmit={handleSubmit}>
                                            <div className="px-6 pt-4 pb-2 space-y-3">
                                                {/* Breadcrumb */}
                                                <div className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-400">
                                                    <select
                                                        value={selectedProjectId ?? ''}
                                                        onChange={e => setSelectedProjectId(Number(e.target.value))}
                                                        className="appearance-none px-2 py-0.5 bg-slate-100 dark:bg-white/8 rounded-md text-[11px] font-semibold text-slate-600 dark:text-slate-300 cursor-pointer outline-none hover:bg-slate-200 transition-colors"
                                                    >
                                                        <option value="">Proyecto...</option>
                                                        {projects.map(p => <option key={p.id} value={p.id}>{p.title}</option>)}
                                                    </select>
                                                    <ChevronRight size={12} className="text-slate-300" />
                                                    <span className="px-2 py-0.5 bg-slate-100 dark:bg-white/8 rounded-md">Tarea</span>
                                                </div>

                                                <input
                                                    ref={titleRef}
                                                    value={title}
                                                    onChange={e => setTitle(e.target.value)}
                                                    placeholder="Escribe el nombre de Tarea o pulsa «/» para ver comandos"
                                                    className="w-full bg-transparent text-[20px] font-semibold outline-none placeholder:text-slate-300 dark:placeholder:text-white/20 text-slate-800 dark:text-white leading-snug"
                                                />

                                                {!description ? (
                                                    <div className="flex items-center gap-4">
                                                        <button type="button" onClick={() => setDescription(' ')} className="flex items-center gap-1.5 text-[12px] text-slate-400 hover:text-slate-600 transition-colors">
                                                            <AlignLeft size={13} /> Añadir descripción
                                                        </button>
                                                        <button type="button" className="flex items-center gap-1.5 text-[12px] font-semibold text-purple-500 hover:text-purple-700 transition-colors">
                                                            <Sparkles size={13} /> Escribir con IA
                                                        </button>
                                                    </div>
                                                ) : (
                                                    <textarea
                                                        autoFocus={description === ' '}
                                                        value={description.trim()}
                                                        onChange={e => setDescription(e.target.value)}
                                                        placeholder="Descripción..."
                                                        rows={3}
                                                        className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/8 rounded-xl px-4 py-3 text-[13px] outline-none focus:ring-2 focus:ring-blue-500/20 text-slate-700 dark:text-slate-200 resize-none"
                                                    />
                                                )}

                                                {/* Pills row */}
                                                <div className="flex flex-wrap items-center gap-1.5 pt-1">
                                                    <span className="px-3 py-1.5 border border-slate-200 dark:border-white/10 rounded-full text-[10px] font-black uppercase tracking-wider text-slate-600 dark:text-slate-300 bg-slate-50 dark:bg-white/5">
                                                        PENDIENTE
                                                    </span>
                                                    <div className="relative">
                                                        <select value={priority} onChange={e => setPriority(e.target.value)}
                                                            className="appearance-none pl-6 pr-3 py-1.5 border border-slate-200 dark:border-white/10 rounded-full text-[11px] font-semibold text-slate-500 bg-white dark:bg-transparent cursor-pointer outline-none hover:bg-slate-50">
                                                            <option value="normal">Prioridad</option>
                                                            <option value="urgent">Urgente</option>
                                                            <option value="high">Alta</option>
                                                            <option value="low">Baja</option>
                                                        </select>
                                                        <Flag size={11} className="absolute left-2 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
                                                    </div>
                                                    <button type="button" className="flex items-center gap-1.5 pl-2.5 pr-3 py-1.5 border border-slate-200 dark:border-white/10 rounded-full text-[11px] font-semibold text-slate-500 hover:bg-slate-50 transition-colors">
                                                        <User size={11} /> Persona asignada
                                                    </button>
                                                    <button type="button" className="flex items-center gap-1.5 pl-2.5 pr-3 py-1.5 border border-slate-200 dark:border-white/10 rounded-full text-[11px] font-semibold text-slate-500 hover:bg-slate-50 transition-colors">
                                                        <Calendar size={11} /> Fecha límite
                                                    </button>
                                                    <button type="button" className="flex items-center gap-1.5 pl-2.5 pr-3 py-1.5 border border-slate-200 dark:border-white/10 rounded-full text-[11px] font-semibold text-slate-500 hover:bg-slate-50 transition-colors">
                                                        <Hash size={11} /> Etiquetas
                                                    </button>
                                                </div>

                                                {/* Campos */}
                                                <div className="pt-2">
                                                    <p className="text-[11px] font-black text-slate-400 uppercase tracking-widest mb-2">Campos</p>
                                                    <button type="button" className="flex items-center gap-1.5 text-[12px] font-semibold text-slate-400 hover:text-blue-600 transition-colors">
                                                        <Plus size={13} /> Crear un campo
                                                    </button>
                                                </div>
                                            </div>

                                            {/* Footer */}
                                            <footer className="px-6 py-3.5 border-t border-slate-100 dark:border-white/5 flex items-center justify-between bg-slate-50/50 dark:bg-black/10">
                                                <button type="button" className="flex items-center gap-1.5 px-3 py-1.5 border border-slate-200 dark:border-white/10 rounded-lg text-[11px] font-semibold text-slate-500 hover:bg-white dark:hover:bg-white/5 transition-colors">
                                                    <Sparkles size={13} /> Plantillas
                                                </button>
                                                <div className="flex items-center gap-2">
                                                    <button type="button" className="p-2 text-slate-400 hover:text-blue-600 transition-colors">
                                                        <Search size={15} />
                                                    </button>
                                                    <div className="flex rounded-xl overflow-hidden shadow-md">
                                                        <button
                                                            type="submit"
                                                            disabled={loading || !title.trim()}
                                                            className="bg-slate-900 dark:bg-white font-bold text-white dark:text-slate-900 px-5 py-2 text-[11px] uppercase tracking-widest flex items-center gap-2 disabled:opacity-40 hover:bg-slate-800 transition-colors"
                                                        >
                                                            {loading ? <Loader2 size={13} className="animate-spin" /> : 'Crear Tarea'}
                                                        </button>
                                                        <button type="button" className="bg-slate-900 dark:bg-white border-l border-white/10 dark:border-slate-200 px-2.5 text-white dark:text-slate-900 hover:bg-slate-800 transition-colors">
                                                            <ChevronRight size={13} className="rotate-90" />
                                                        </button>
                                                    </div>
                                                </div>
                                            </footer>
                                        </form>
                                    </motion.div>
                                )}
                                {type !== 'task' && (
                                    <motion.div key={type} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                                        className="px-6 py-8 flex flex-col gap-4 min-h-[280px]">
                                        <input
                                            ref={titleRef}
                                            value={title}
                                            onChange={e => setTitle(e.target.value)}
                                            placeholder={`Ponle un nombre a este ${type === 'doc' ? 'documento' : type === 'whiteboard' ? 'pizarra' : type === 'reminder' ? 'recordatorio' : 'panel'}...`}
                                            className="w-full bg-transparent text-[18px] font-semibold outline-none placeholder:text-slate-300 dark:placeholder:text-white/20 text-slate-800 dark:text-white"
                                        />
                                        <div className="mt-auto pt-4 border-t border-slate-100 dark:border-white/5 flex justify-between items-center">
                                            <span className="text-[11px] text-slate-400">La creación de {type} estará disponible próximamente.</span>
                                            <button onClick={resetAndClose} className="bg-slate-900 dark:bg-white font-bold text-white dark:text-slate-900 px-5 py-2 rounded-xl text-[11px] uppercase tracking-widest shadow-md hover:opacity-90 transition-all">
                                                Cerrar
                                            </button>
                                        </div>
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
}

function TypeTab({ active, onClick, icon: Icon, label, color }: any) {
    return (
        <button
            onClick={onClick}
            className={clsx(
                "flex items-center gap-4 px-5 py-4 rounded-2xl transition-all group relative overflow-hidden",
                active ? "bg-white dark:bg-white/10 shadow-xl border border-slate-100 dark:border-white/5" : "hover:bg-white/50 dark:hover:bg-white/5"
            )}
        >
            {active && <motion.div layoutId="activeCreationTab" className="absolute left-0 top-4 bottom-4 w-1 bg-blue-600 rounded-full" />}
            <Icon size={20} className={clsx("transition-transform group-hover:scale-110", active ? color : "text-slate-400 group-hover:text-slate-600")} />
            <span className={clsx("text-sm font-black tracking-tight", active ? "text-slate-900 dark:text-white" : "text-slate-500")}>{label}</span>
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
