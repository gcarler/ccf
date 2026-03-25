"use client";

import React, { useState } from 'react';
import { 
    Calendar as CalendarIcon, 
    MoreHorizontal,
    Flag,
    Tags,
    User,
    Calendar,
    ChevronDown,
    Paperclip,
    Bell,
    Wand2,
    X,
    FileText,
    LayoutDashboard,
    LayoutList,
    KanbanSquare,
    ChevronRight,
    CheckCircle2,
    Folder,
    Plus,
    Type,
    Clock,
    StickyNote
, Hash, Circle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import * as Dialog from '@radix-ui/react-dialog';
import { toast } from 'sonner';

type CreationType = 'task' | 'doc' | 'reminder' | 'whiteboard' | 'panel';

interface Props {
    isOpen: boolean;
    onClose: () => void;
    onSubmit?: (payload: { type: CreationType; title: string; description: string }) => void;
}

export default function UniversalCreationModal({ isOpen, onClose, onSubmit }: Props) {
    const [type, setType] = useState<CreationType>('task');
    const [title, setTitle] = useState('');
    const [description, setDescription] = useState('');

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!title.trim()) return;
        
        toast.success(`${type === 'task' ? 'Tarea' : type.toUpperCase()} creado correctamente`);
        onSubmit?.({ type, title, description });
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
                                initial={{ opacity: 0, scale: 0.95, y: 20 }}
                                animate={{ opacity: 1, scale: 1, y: 0 }}
                                exit={{ opacity: 0, scale: 0.95, y: 20 }}
                                className="fixed left-1/2 top-[10vh] z-[9001] w-full max-w-[750px] -translate-x-1/2 rounded-2xl bg-white dark:bg-[#1e1f21] shadow-[var(--shadow-floating)] border border-slate-200 dark:border-white/10 outline-none flex flex-col overflow-hidden"
                            >
                                {/* Top Navigation Tabs - ClickUp Style */}
                                <div className="flex items-center justify-between px-2 pt-2 border-b border-slate-100 dark:border-white/5 bg-slate-50/50 dark:bg-white/5">
                                    <div className="flex items-center gap-1">
                                        <Tab active={type === 'task'} onClick={() => setType('task')} icon={LayoutList} label="Tarea" />
                                        <Tab active={type === 'doc'} onClick={() => setType('doc')} icon={FileText} label="Documento" />
                                        <Tab active={type === 'reminder'} onClick={() => setType('reminder')} icon={Bell} label="Recordatorio" />
                                        <Tab active={type === 'whiteboard'} onClick={() => setType('whiteboard')} icon={LayoutDashboard} label="Pizarra" />
                                        <Tab active={type === 'panel'} onClick={() => setType('panel')} icon={KanbanSquare} label="Panel" />
                                    </div>
                                    <div className="flex items-center gap-1 pr-2">
                                        <Dialog.Close asChild>
                                            <button className="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-200 dark:hover:bg-white/10 rounded-lg transition-colors"><X size={18} /></button>
                                        </Dialog.Close>
                                    </div>
                                </div>

                                <form onSubmit={handleSubmit} className="flex flex-col flex-1">
                                    {/* Breadcrumb Context */}
                                    <div className="px-6 py-4 flex items-center gap-2">
                                        <LocationBadge label="Espacio del equipo" icon={Folder} />
                                        <ChevronRight size={12} className="text-slate-300" />
                                        <LocationBadge label="Proyectos" icon={Hash} />
                                        <ChevronRight size={12} className="text-slate-300" />
                                        <LocationBadge label="General" icon={Type} />
                                    </div>

                                    {/* Main Input Area */}
                                    <div className="px-6 pb-6 space-y-4">
                                        <div className="relative">
                                            <input 
                                                autoFocus
                                                value={title}
                                                onChange={(e) => setTitle(e.target.value)}
                                                placeholder={
                                                    type === 'task' ? "Escribe el nombre de Tarea o pulsa «/» para ver comandos" :
                                                    type === 'doc' ? "Título del documento..." : "Escribe aquí..."
                                                }
                                                className="w-full text-[20px] font-black text-slate-800 dark:text-white bg-transparent outline-none placeholder:text-slate-400/50 py-2 tracking-tight"
                                            />
                                        </div>

                                        <div className="flex items-center gap-4">
                                            <button type="button" className="flex items-center gap-2 text-[12px] font-bold text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors">
                                                <StickyNote size={14} /> Añadir descripción
                                            </button>
                                            <button type="button" className="flex items-center gap-2 text-[12px] font-black text-purple-600 dark:text-purple-400 hover:opacity-80 transition-opacity">
                                                <Wand2 size={14} /> Escribir con IA
                                            </button>
                                        </div>

                                        {/* Property Selectors Bar */}
                                        <div className="flex items-center flex-wrap gap-2 pt-4">
                                            <PropertyButton icon={Circle} label="ESTADO" color="text-slate-400" />
                                            <PropertyButton icon={User} label="Asignado" />
                                            <PropertyButton icon={Calendar} label="Fecha límite" />
                                            <PropertyButton icon={Flag} label="Prioridad" />
                                            <PropertyButton icon={Tags} label="Etiquetas" />
                                            <button type="button" className="p-2 rounded-lg border border-slate-200 dark:border-white/10 text-slate-400 hover:bg-slate-50 dark:hover:bg-white/5 transition-colors">
                                                <MoreHorizontal size={16} />
                                            </button>
                                        </div>
                                    </div>

                                    {/* Bottom Footer */}
                                    <div className="mt-auto px-6 py-4 bg-slate-50/50 dark:bg-[#1a1b1d] border-t border-slate-100 dark:border-white/5 flex items-center justify-between">
                                        <button type="button" className="flex items-center gap-2 px-3 py-2 rounded-xl border border-slate-200 dark:border-white/10 text-[11px] font-black uppercase tracking-widest text-slate-600 dark:text-slate-300 hover:bg-white dark:hover:bg-white/5 transition-all">
                                            <Wand2 size={14} /> Plantillas
                                        </button>
                                        
                                        <div className="flex items-center gap-4">
                                            <div className="flex items-center gap-3 pr-2 border-r border-slate-200 dark:border-white/10">
                                                <button type="button" className="text-slate-400 hover:text-slate-600 transition-colors"><Paperclip size={18} /></button>
                                                <button type="button" className="text-slate-400 hover:text-slate-600 transition-colors"><Bell size={18} /></button>
                                            </div>

                                            {/* Integrated Split Button */}
                                            <div className="flex items-center shadow-xl shadow-blue-500/10">
                                                <button 
                                                    type="submit"
                                                    className="px-6 py-2.5 bg-slate-900 dark:bg-white text-white dark:text-slate-900 text-[11px] font-black uppercase tracking-[0.2em] rounded-l-xl hover:opacity-90 transition-opacity"
                                                >
                                                    Crear {type === 'task' ? 'Tarea' : type.toUpperCase()}
                                                </button>
                                                <div className="w-[1px] h-10 bg-slate-700 dark:bg-slate-200" />
                                                <button 
                                                    type="button"
                                                    className="px-2 py-2.5 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-r-xl hover:opacity-90 transition-opacity"
                                                >
                                                    <ChevronDown size={16} />
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                </form>
                            </motion.div>
                        </Dialog.Content>
                    </Dialog.Portal>
                )}
            </AnimatePresence>
        </Dialog.Root>
    );
}

function Tab({ active, icon: Icon, label, onClick }: any) {
    return (
        <button 
            type="button" 
            onClick={onClick}
            className={clsx(
                "flex items-center gap-2 px-4 py-3 text-[11px] font-bold transition-all relative",
                active ? "text-slate-900 dark:text-white" : "text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
            )}
        >
            <Icon size={14} strokeWidth={active ? 2.5 : 2} className={active ? "text-blue-600" : ""} />
            {label}
            {active && (
                <motion.div 
                    layoutId="creation-tab"
                    className="absolute bottom-0 left-0 w-full h-[2px] bg-slate-900 dark:bg-white" 
                />
            )}
        </button>
    );
}

function LocationBadge({ label, icon: Icon }: any) {
    return (
        <div className="flex items-center gap-1.5 px-2 py-1 rounded-md hover:bg-slate-100 dark:hover:bg-white/5 transition-colors cursor-pointer group">
            <Icon size={12} className="text-slate-400 group-hover:text-blue-500" />
            <span className="text-[11px] font-bold text-slate-600 dark:text-slate-300">{label}</span>
            <ChevronDown size={12} className="text-slate-300 opacity-0 group-hover:opacity-100 transition-opacity" />
        </div>
    );
}

function PropertyButton({ icon: Icon, label, color = "text-slate-500" }: any) {
    return (
        <button type="button" className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-slate-200 dark:border-white/10 text-[11px] font-bold text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-white/5 transition-all shadow-sm">
            <Icon size={14} className={color} />
            {label}
        </button>
    );
}
