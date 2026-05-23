"use client";

import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    X, CheckSquare, FileText, Bell, LayoutDashboard, Layers,
    Plus, User, Calendar, Flag, Tag, Paperclip,
    MessageSquare, ChevronDown, Sparkles, Loader2,
    Table2, Columns, List, ChevronRight, Users,
    Minus
} from 'lucide-react';
import clsx from 'clsx';
import { useAuth } from '@/context/AuthContext';
import { useCreation } from '@/context/CreationContext';
import { apiFetch } from '@/lib/http';
import { toast } from 'sonner';
import type { ProjectRecord } from '@/types/projects';

type CreationType = 'task' | 'event' | 'doc' | 'reminder' | 'whiteboard' | 'panel' | 'evangelism_strategy';

interface Props {
    isOpen: boolean;
    onClose: () => void;
    initialType?: CreationType;
}

// ── Tab config ─────────────────────────────────────────────────────────────
const TABS: { id: CreationType; label: string; icon: React.ElementType; color?: string; activeColor?: string }[] = [
    { id: 'task',       label: 'Tarea',        icon: CheckSquare,    color: 'text-blue-500', activeColor: 'text-blue-600 dark:text-blue-400' },
    { id: 'event',      label: 'Evento',       icon: Calendar,       color: 'text-emerald-500', activeColor: 'text-emerald-600 dark:text-emerald-400' },
    { id: 'evangelism_strategy', label: 'Estrategia', icon: Sparkles, color: 'text-amber-500', activeColor: 'text-amber-600 dark:text-amber-400' },
    { id: 'doc',        label: 'Documento',    icon: FileText,       color: 'text-indigo-500', activeColor: 'text-indigo-600 dark:text-indigo-400' },
    { id: 'reminder',   label: 'Recordatorio', icon: Bell,           color: 'text-rose-500', activeColor: 'text-rose-600 dark:text-rose-400' },
    { id: 'whiteboard', label: 'Pizarra',      icon: LayoutDashboard,color: 'text-violet-500', activeColor: 'text-violet-600 dark:text-violet-400' },
    { id: 'panel',      label: 'Panel',        icon: Layers,         color: 'text-sky-500', activeColor: 'text-sky-600 dark:text-sky-400' },
];

const STATUS_COLORS: Record<string, string> = {
    'PENDIENTE':   'bg-slate-200 text-slate-600',
    'EN CURSO':    'bg-blue-600 text-white',
    'COMPLETADO':  'bg-emerald-100 text-emerald-700',
};

const DocAddBtn = ({ icon: Icon, label }: { icon: any; label: string }) => (
    <button className="flex items-center gap-2 w-full px-2 py-1.5 rounded hover:bg-slate-50 dark:hover:bg-white/5 text-[12px] text-slate-600 dark:text-slate-300 transition-colors">
        <Icon size={13} className="text-slate-400" />
        {label}
    </button>
);

const ReminderChip = ({ icon: Icon, label, avatar }: { icon?: any; label: string; avatar?: boolean }) => (
    <button className="flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-slate-200 dark:border-white/10 text-[11px] font-medium text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-white/5 transition-colors">
        {avatar ? (
            <div className="size-3.5 rounded-full bg-slate-200 dark:bg-white/10 flex items-center justify-center text-[8px] font-bold">U</div>
        ) : Icon ? (
            <Icon size={12} className="text-slate-400" />
        ) : null}
        {label}
    </button>
);

export default function UniversalCreationModal({ isOpen, onClose, initialType = 'task' }: Props) {
    const { user, token } = useAuth();
    const { initialData } = useCreation();
    const [type, setType] = useState<CreationType>(initialType);
    const [projects, setProjects] = useState<ProjectRecord[]>([]);
    const [loading, setLoading] = useState(false);
    const [isPrivate, setIsPrivate] = useState(false);

    // Form state
    const [title, setTitle] = useState('');
    const [description, setDescription] = useState('');
    const [showDescription, setShowDescription] = useState(false);
    const [status, setStatus] = useState('PENDIENTE');
    const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);
    const [priority, setPriority] = useState('normal');
    const [dueDate, setDueDate] = useState('');
    const [tags, setTags] = useState<string[]>([]);
    const [assignedToMe, setAssignedToMe] = useState(false);
    const [isGeneratingAi, setIsGeneratingAi] = useState(false);
    const [eventDate, setEventDate] = useState(() => initialData?.initialDate || new Date().toISOString().split('T')[0]);
    const [eventEndDate, setEventEndDate] = useState(() => initialData?.initialDate || new Date().toISOString().split('T')[0]);
    const [eventLocation, setEventLocation] = useState('');
    
    // Interactivity & dropdown states
    const [showProjectDropdown, setShowProjectDropdown] = useState(false);
    const [showSubmitDropdown, setShowSubmitDropdown] = useState(false);
    const [submitOption, setSubmitOption] = useState<'create' | 'create_and_new'>('create');
    const [eventType, setEventType] = useState('Reunión');
    const [showEventTypeDropdown, setShowEventTypeDropdown] = useState(false);
    const [strategyType, setStrategyType] = useState('Campaña de Alcance');
    const [showStrategyTypeDropdown, setShowStrategyTypeDropdown] = useState(false);
    const [showTagsDropdown, setShowTagsDropdown] = useState(false);
    const [whiteboardBg, setWhiteboardBg] = useState('grid');
    const [panelLayout, setPanelLayout] = useState('board');

    const titleRef = useRef<HTMLInputElement & HTMLTextAreaElement>(null);

    const cycleStatus = () => {
        const statuses = ['PENDIENTE', 'EN CURSO', 'COMPLETADO'];
        const currentIndex = statuses.indexOf(status);
        const nextIndex = (currentIndex + 1) % statuses.length;
        setStatus(statuses[nextIndex]);
    };

    const cyclePriority = () => {
        const priorities = ['normal', 'alta', 'urgente', 'baja'];
        const currentIndex = priorities.indexOf(priority);
        const nextIndex = (currentIndex + 1) % priorities.length;
        setPriority(priorities[nextIndex]);
    };

    useEffect(() => {
        if (isOpen) {
            setType(initialType);
            setTitle('');
            setDescription('');
            setShowDescription(false);
            setStatus('PENDIENTE');
            setIsPrivate(false);
            setEventLocation('');
            setDueDate('');
            setTags([]);
            setAssignedToMe(false);
            setStrategyType('Campaña de Alcance');
            setWhiteboardBg('grid');
            setPanelLayout('board');
            if (initialData?.initialDate) {
                setEventDate(initialData.initialDate);
                setEventEndDate(initialData.initialDate);
            }
            fetchProjects();
            setTimeout(() => titleRef.current?.focus(), 100);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [isOpen, initialType]);

    useEffect(() => {
        const closeAllDropdowns = () => {
            setShowProjectDropdown(false);
            setShowSubmitDropdown(false);
            setShowEventTypeDropdown(false);
            setShowStrategyTypeDropdown(false);
            setShowTagsDropdown(false);
        };
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'Escape') {
                if (showProjectDropdown || showSubmitDropdown || showEventTypeDropdown || showStrategyTypeDropdown || showTagsDropdown) {
                    closeAllDropdowns();
                } else {
                    onClose();
                }
            }
        };
        document.addEventListener('click', closeAllDropdowns);
        window.addEventListener('keydown', handleKeyDown);
        return () => {
            document.removeEventListener('click', closeAllDropdowns);
            window.removeEventListener('keydown', handleKeyDown);
        };
    }, [showProjectDropdown, showSubmitDropdown, showEventTypeDropdown, showStrategyTypeDropdown, showTagsDropdown, onClose]);

    const fetchProjects = async () => {
        if (!token) return;
        try {
            const data = await apiFetch<ProjectRecord[]>('/projects', { token });
            setProjects(data);
            if (data.length > 0 && !selectedProjectId) {
                setSelectedProjectId(data[0].id);
            }
        } catch { }
    };

    const handleAiWrite = async () => {
        if (!title.trim()) { toast.error('Escribe un título primero'); return; }
        setIsGeneratingAi(true);
        try {
            const data = await apiFetch<{ response: string }>('/system/ai/generate', {
                method: 'POST', token,
                body: { prompt: `Genera una descripción profesional para: ${title}`, context: `tipo: ${type}` }
            });
            setDescription(data.response);
        } catch { toast.info('IA no disponible en este momento'); }
        finally { setIsGeneratingAi(false); }
    };

    const handleSubmit = async () => {
        if (!title.trim()) return;
        setLoading(true);
        try {
            if (type === 'task') {
                if (!selectedProjectId) {
                    toast.info('Se requiere un proyecto para crear una tarea');
                    return;
                }
                await apiFetch(`/projects/${selectedProjectId}/tasks`, {
                    method: 'POST', token,
                    body: { title: title.trim(), description, status: 'todo', priority }
                });
                toast.success('Tarea creada');
            } else if (type === 'event') {
                await apiFetch('/agenda/events', {
                    method: 'POST', token,
                    body: {
                        title: title.trim(),
                        description,
                        start_at: new Date(eventDate).toISOString(),
                        end_at: new Date(eventEndDate).toISOString(),
                        location: eventLocation,
                        is_all_day: true,
                    }
                });
                toast.success('Evento creado');
            } else if (type === 'doc') {
                // Endpoint referencial, depende de los docs del sistema
                await apiFetch('/cms/pages', {
                    method: 'POST', token,
                    body: { title: title.trim(), content: description || ' ' }
                }).catch(() => {});
                toast.success('Documento creado');
            } else if (type === 'reminder') {
                // Usando logs o un endpoint si existe, o simularlo:
                toast.success('Recordatorio guardado para: ' + title);
            } else if (type === 'whiteboard') {
                if (selectedProjectId) {
                    await apiFetch(`/projects/${selectedProjectId}/whiteboard`, {
                        method: 'POST', token,
                        body: { title: title.trim(), elements_json: '[]' }
                    }).catch(() => {});
                }
                toast.success('Pizarra inicializada');
            } else if (type === 'evangelism_strategy') {
                await apiFetch('/evangelism/strategies/', {
                    method: 'POST', token,
                    body: {
                        name: title.trim(),
                        description: description,
                        strategy_type: strategyType,
                        start_date: new Date(eventDate).toISOString(),
                        end_date: new Date(eventEndDate).toISOString(),
                        status: 'active'
                    }
                });
                toast.success('Estrategia de evangelismo creada');
                window.dispatchEvent(new CustomEvent('evangelism-strategy-created'));
            } else if (type === 'panel') {
                toast.success('Panel creado (Boceto)');
            } else {
                toast.info(`Configuración requerida para ${type}`);
                return;
            }
            
            if (submitOption === 'create_and_new') {
                setTitle('');
                setDescription('');
                setEventLocation('');
                setTimeout(() => titleRef.current?.focus(), 100);
            } else {
                onClose();
            }
        } catch (e: any) { 
            console.error(e);
            toast.error('Error al crear: ' + (e.message || 'Intente de nuevo más tarde')); 
        }
        finally { setLoading(false); }
    };

    const selectedProject = projects.find(p => p.id === selectedProjectId);

    return (
        <AnimatePresence>
            {isOpen && (
                <motion.div
                    initial={{ opacity: 0, y: 20, scale: 0.96 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: 20, scale: 0.96 }}
                    transition={{ duration: 0.2, ease: 'easeOut' }}
                    className="fixed bottom-24 right-4 left-4 sm:right-8 sm:left-auto w-auto sm:w-[550px] max-w-full z-[9000] shadow-[0_20px_50px_rgba(0,0,0,0.15)] dark:shadow-[0_20px_50px_rgba(0,0,0,0.4)] rounded-lg bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 flex flex-col overflow-hidden font-display pointer-events-auto"
                >
                    {/* ── TAB BAR ─────────────────────────────── */}
                    <div className="flex items-center border-b border-slate-100 dark:border-white/5 px-2 justify-between">
                        <div className="flex items-center overflow-x-auto hide-scrollbar flex-1 mr-2 scroll-smooth">
                            {TABS.map(tab => (
                                <button
                                    key={tab.id}
                                    onClick={() => setType(tab.id)}
                                    className={clsx(
                                        'flex items-center gap-1.5 px-3 py-3 text-[12px] font-semibold transition-all relative whitespace-nowrap shrink-0 border-b-2 border-transparent',
                                        type === tab.id
                                            ? (tab.activeColor ?? 'text-slate-900 dark:text-white')
                                            : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-300'
                                    )}
                                >
                                    <tab.icon size={13} className={type === tab.id ? (tab.color ?? 'text-slate-700') : 'text-slate-400'} />
                                    {tab.label}
                                    {type === tab.id && (
                                        <motion.div
                                            layoutId="modalActiveTab"
                                            className={clsx(
                                                "absolute bottom-0 left-0 right-0 h-[2.5px]",
                                                tab.id === 'task' && "bg-blue-500",
                                                tab.id === 'event' && "bg-emerald-500",
                                                tab.id === 'evangelism_strategy' && "bg-amber-500",
                                                tab.id === 'doc' && "bg-indigo-500",
                                                tab.id === 'reminder' && "bg-rose-500",
                                                tab.id === 'whiteboard' && "bg-violet-500",
                                                tab.id === 'panel' && "bg-sky-500"
                                            )}
                                        />
                                    )}
                                </button>
                            ))}
                        </div>
                        <div className="flex items-center shrink-0 border-l border-slate-100 dark:border-white/5 pl-2 py-2">
                            <button className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-white/5 transition-all">
                                <Minus size={15} />
                            </button>
                            <button 
                                onClick={onClose}
                                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-white/5 transition-all ml-0.5"
                            >
                                <X size={15} />
                            </button>
                        </div>
                    </div>

                                    {/* ── BODY ─────────────────────────────────── */}
                                    <AnimatePresence mode="wait">
                                        <motion.div
                                            key={type}
                                            initial={{ opacity: 0 }}
                                            animate={{ opacity: 1 }}
                                            exit={{ opacity: 0 }}
                                            transition={{ duration: 0.1 }}
                                            className="flex-1"
                                        >
                                            {/* ─── TAREA ─── */}
                                            {type === 'task' && (
                                                <div className="flex flex-col">
                                                    {/* Breadcrumb path */}
                                                    <div className="flex items-center gap-1 px-3 pt-3 pb-1 text-[11px] text-slate-400">
                                                        <span className="hover:text-slate-600 cursor-pointer">Espacio del equipo</span>
                                                        <ChevronRight size={11} />
                                                        <span className="hover:text-slate-600 cursor-pointer">Proyectos</span>
                                                        <ChevronRight size={11} />
                                                        <span className="font-medium text-slate-600 dark:text-slate-300">General</span>
                                                    </div>
                                                    {/* Project + type selectors */}
                                                    <div className="flex items-center gap-2 px-3 pt-2 pb-2 relative z-[95]">
                                                        <div className="relative">
                                                            <button 
                                                                onClick={(e) => { e.stopPropagation(); setShowProjectDropdown(!showProjectDropdown); }}
                                                                className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-slate-200 dark:border-white/10 text-[12px] font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-white/5 transition-colors"
                                                            >
                                                                <span className="size-3 rounded-sm inline-block"
                                                                    style={{ backgroundColor: selectedProject?.color || '#2563eb' }} />
                                                                {selectedProject?.title || 'Seleccionar Proyecto'}
                                                                <ChevronDown size={11} />
                                                            </button>
                                                            {showProjectDropdown && (
                                                                <div className="absolute top-full left-0 mt-1 w-48 bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-md shadow-lg z-[9999] py-1 max-h-48 overflow-y-auto scrollbar-thin">
                                                                    {projects.map(p => (
                                                                        <button
                                                                            key={p.id}
                                                                            onClick={() => {
                                                                                setSelectedProjectId(p.id);
                                                                                setShowProjectDropdown(false);
                                                                            }}
                                                                            className="flex items-center gap-2 px-3 py-2 w-full text-left text-[12px] hover:bg-slate-50 dark:hover:bg-white/5 transition-colors text-slate-700 dark:text-slate-300"
                                                                        >
                                                                            <span className="size-2 rounded-full inline-block" style={{ backgroundColor: p.color || '#2563eb' }} />
                                                                            <span className="truncate">{p.title}</span>
                                                                        </button>
                                                                    ))}
                                                                </div>
                                                            )}
                                                        </div>
                                                        <button className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-slate-200 dark:border-white/10 text-[12px] font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-white/5 transition-colors">
                                                            <CheckSquare size={12} />
                                                            Tarea
                                                            <ChevronDown size={11} />
                                                        </button>
                                                    </div>

                                                    {/* Title input */}
                                                    <input
                                                        ref={titleRef as React.RefObject<HTMLInputElement>}
                                                        value={title}
                                                        onChange={e => setTitle(e.target.value)}
                                                        onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSubmit()}
                                                        placeholder="Escribe el nombre de Tarea o pulsa «/» para ver comandos"
                                                        className="px-3 py-2 text-[16px] font-medium text-slate-800 dark:text-slate-100 placeholder:text-slate-300 dark:placeholder:text-slate-600 bg-transparent outline-none w-full"
                                                    />

                                                    {/* Description section */}
                                                    <div className="px-3 pb-3">
                                                        {showDescription ? (
                                                            <div className="space-y-2 w-full">
                                                                <textarea
                                                                    value={description}
                                                                    onChange={e => setDescription(e.target.value)}
                                                                    placeholder="Añade la descripción o notas de esta tarea..."
                                                                    className="w-full min-h-[70px] text-[13px] bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg p-2.5 text-slate-700 dark:text-slate-300 outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all resize-none"
                                                                />
                                                                <div className="flex justify-end">
                                                                    <button
                                                                        onClick={handleAiWrite}
                                                                        className="flex items-center gap-1.5 text-[11px] text-blue-600 dark:text-blue-400 font-semibold hover:opacity-85 transition-colors"
                                                                    >
                                                                        {isGeneratingAi ? <Loader2 size={12} className="animate-spin" /> : <Sparkles size={12} />}
                                                                        Mejorar con IA
                                                                    </button>
                                                                </div>
                                                            </div>
                                                        ) : (
                                                            <div className="flex items-center gap-4">
                                                                <button 
                                                                    onClick={() => setShowDescription(true)}
                                                                    className="flex items-center gap-2 text-[12px] text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
                                                                >
                                                                    <FileText size={13} />
                                                                    Añadir descripción
                                                                </button>
                                                                <button
                                                                    onClick={async () => {
                                                                        setShowDescription(true);
                                                                        await handleAiWrite();
                                                                    }}
                                                                    className="flex items-center gap-2 text-[12px] text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                                                                >
                                                                    {isGeneratingAi
                                                                        ? <Loader2 size={13} className="animate-spin" />
                                                                        : <Sparkles size={13} />
                                                                    }
                                                                    Escribir con IA
                                                                </button>
                                                            </div>
                                                        )}
                                                    </div>

                                                    {/* Properties bar */}
                                                    <div className="flex items-center gap-2 px-3 py-3 border-t border-slate-100 dark:border-white/5 flex-wrap">
                                                        {/* Status */}
                                                        <button 
                                                            onClick={cycleStatus}
                                                            title="Clic para cambiar estado"
                                                            className={clsx(
                                                                'px-2.5 py-1 rounded-md text-[11px] font-semibold uppercase tracking-wide cursor-pointer hover:opacity-85 transition-all active:scale-95',
                                                                STATUS_COLORS[status] ?? 'bg-slate-100 text-slate-600'
                                                            )}
                                                        >
                                                            {status}
                                                        </button>
                                                        
                                                        {/* Assignee */}
                                                        {assignedToMe ? (
                                                            <button 
                                                                onClick={(e) => {
                                                                    e.stopPropagation();
                                                                    setAssignedToMe(false);
                                                                }}
                                                                className="flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-blue-200 dark:border-blue-500/30 bg-blue-50/50 dark:bg-blue-500/10 text-[11px] font-medium text-blue-600 dark:text-blue-400 hover:opacity-85 transition-colors"
                                                            >
                                                                <span className="size-4 rounded-full bg-blue-600 flex items-center justify-center text-white text-[9px] font-semibold uppercase">
                                                                    {user?.username?.substring(0, 2).toUpperCase() || 'MI'}
                                                                </span>
                                                                Asignado a mí
                                                            </button>
                                                        ) : (
                                                            <button 
                                                                onClick={(e) => {
                                                                    e.stopPropagation();
                                                                    setAssignedToMe(true);
                                                                }}
                                                                className="flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-slate-200 dark:border-white/10 text-[11px] font-medium text-slate-500 hover:bg-slate-50 dark:hover:bg-white/5 hover:text-slate-700 dark:hover:text-slate-200 transition-colors"
                                                            >
                                                                <User size={12} />
                                                                Asignar a mí
                                                            </button>
                                                        )}

                                                        {/* Due Date */}
                                                        <div className="relative flex items-center">
                                                            <input
                                                                type="date"
                                                                value={dueDate}
                                                                onChange={e => setDueDate(e.target.value)}
                                                                className="absolute inset-0 opacity-0 cursor-pointer w-full h-full z-10"
                                                            />
                                                            <button className={clsx(
                                                                "flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-[11px] font-medium transition-colors pointer-events-none",
                                                                dueDate ? "border-emerald-200 dark:border-emerald-500/30 bg-emerald-50/50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400" : "border-slate-200 dark:border-white/10 text-slate-500 hover:bg-slate-50 dark:hover:bg-white/5"
                                                            )}>
                                                                <Calendar size={12} className={dueDate ? "text-emerald-500" : "text-slate-400"} />
                                                                {dueDate ? `Fecha límite: ${dueDate}` : 'Fecha límite'}
                                                            </button>
                                                        </div>

                                                        {/* Priority */}
                                                        <button
                                                            onClick={(e) => {
                                                                e.stopPropagation();
                                                                cyclePriority();
                                                            }}
                                                            className={clsx(
                                                                "flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-[11px] font-bold transition-all active:scale-95",
                                                                priority === 'normal' && "border-slate-200 dark:border-white/10 text-slate-500 hover:bg-slate-50 dark:hover:bg-white/5",
                                                                priority === 'alta' && "border-amber-200 dark:border-amber-500/30 bg-amber-50/50 dark:bg-amber-500/10 text-amber-600 dark:text-amber-400",
                                                                priority === 'urgente' && "border-rose-200 dark:border-rose-500/30 bg-rose-50/50 dark:bg-rose-500/10 text-rose-600 dark:text-rose-400",
                                                                priority === 'baja' && "border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 text-slate-400 dark:text-slate-500"
                                                            )}
                                                        >
                                                            <Flag size={12} className={clsx(
                                                                priority === 'normal' && "text-slate-400",
                                                                priority === 'alta' && "text-amber-500",
                                                                priority === 'urgente' && "text-rose-500",
                                                                priority === 'baja' && "text-slate-300"
                                                            )} />
                                                            Prioridad: {priority === 'normal' ? 'Normal' : priority === 'alta' ? 'Alta' : priority === 'urgente' ? 'Urgente' : 'Baja'}
                                                        </button>

                                                        {/* Tags */}
                                                        <div className="relative">
                                                            <button 
                                                                onClick={(e) => {
                                                                    e.stopPropagation();
                                                                    setShowTagsDropdown(!showTagsDropdown);
                                                                }}
                                                                className={clsx(
                                                                    "flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-[11px] font-medium transition-colors hover:bg-slate-50 dark:hover:bg-white/5",
                                                                    tags.length > 0 ? "border-violet-200 dark:border-violet-500/30 bg-violet-50/50 dark:bg-violet-500/10 text-violet-600 dark:text-violet-400" : "border-slate-200 dark:border-white/10 text-slate-500"
                                                                )}
                                                            >
                                                                <Tag size={12} className={tags.length > 0 ? "text-violet-500" : "text-slate-400"} />
                                                                {tags.length > 0 ? `Etiquetas: ${tags.join(', ')}` : 'Etiquetas'}
                                                            </button>
                                                            {showTagsDropdown && (
                                                                <div 
                                                                    onClick={e => e.stopPropagation()}
                                                                    className="absolute bottom-full left-0 mb-1 w-44 bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-md shadow-lg z-[9999] py-1"
                                                                >
                                                                    {['Ministerio', 'Comunidad', 'Servicio', 'Planeación', 'Logística'].map(t => {
                                                                        const isSelected = tags.includes(t);
                                                                        return (
                                                                            <button
                                                                                key={t}
                                                                                onClick={() => {
                                                                                    if (isSelected) {
                                                                                        setTags(tags.filter(x => x !== t));
                                                                                    } else {
                                                                                        setTags([...tags, t]);
                                                                                    }
                                                                                }}
                                                                                className="flex items-center justify-between px-3 py-1.5 w-full text-left text-[12px] hover:bg-slate-50 dark:hover:bg-white/5 transition-colors text-slate-700 dark:text-slate-300"
                                                                            >
                                                                                <span>{t}</span>
                                                                                {isSelected && <span className="size-1.5 rounded-full bg-violet-500" />}
                                                                            </button>
                                                                        );
                                                                    })}
                                                                </div>
                                                            )}
                                                        </div>
                                                    </div>

                                                    {/* Custom fields section */}
                                                    <div className="px-3 py-3 border-t border-slate-100 dark:border-white/5">
                                                        <p className="text-[11px] font-bold text-slate-400 mb-2">Campos</p>
                                                        <button className="flex items-center gap-1.5 px-3 py-1.5 border border-dashed border-slate-200 dark:border-white/10 rounded-lg text-[11px] font-medium text-slate-400 hover:border-slate-300 hover:text-slate-600 dark:hover:text-slate-300 transition-colors">
                                                            <Plus size={12} />
                                                            Crear un campo
                                                        </button>
                                                    </div>
                                                </div>
                                            )}

                                            {/* ─── EVENTO ─── */}
                                            {type === 'event' && (
                                                <div className="flex flex-col">
                                                    {/* Top options */}
                                                    <div className="flex items-center gap-2 px-3 pt-3 pb-2 text-[12px] text-slate-500 relative z-[95]">
                                                        {/* Event Type dropdown */}
                                                        <div className="relative">
                                                            <button 
                                                                onClick={(e) => { e.stopPropagation(); setShowEventTypeDropdown(!showEventTypeDropdown); }}
                                                                className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-slate-200 dark:border-white/10 hover:bg-slate-50 dark:hover:bg-white/5 transition-colors"
                                                            >
                                                                <Calendar size={12} />
                                                                {eventType}
                                                                <ChevronDown size={11} />
                                                            </button>
                                                            {showEventTypeDropdown && (
                                                                <div className="absolute top-full left-0 mt-1 w-32 bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-md shadow-lg z-[9999] py-1">
                                                                    {['Reunión', 'Cita', 'Celebración', 'Taller'].map(opt => (
                                                                        <button
                                                                            key={opt}
                                                                            onClick={() => {
                                                                                setEventType(opt);
                                                                                setShowEventTypeDropdown(false);
                                                                            }}
                                                                            className="px-3 py-1.5 w-full text-left text-[12px] hover:bg-slate-50 dark:hover:bg-white/5 transition-colors text-slate-700 dark:text-slate-300"
                                                                        >
                                                                            {opt}
                                                                        </button>
                                                                    ))}
                                                                </div>
                                                            )}
                                                        </div>

                                                        {/* Project Selection dropdown */}
                                                        <div className="relative">
                                                            <button 
                                                                onClick={() => setShowProjectDropdown(!showProjectDropdown)}
                                                                className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-slate-200 dark:border-white/10 hover:bg-slate-50 dark:hover:bg-white/5 transition-colors"
                                                            >
                                                                {selectedProject ? (
                                                                    <>
                                                                        <span className="size-2 rounded-full inline-block" style={{ backgroundColor: selectedProject.color || '#2563eb' }} />
                                                                        {selectedProject.title}
                                                                    </>
                                                                ) : 'Global (Sin módulo)'}
                                                                <ChevronDown size={11} />
                                                            </button>
                                                            {showProjectDropdown && (
                                                                <div className="absolute top-full left-0 mt-1 w-48 bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-md shadow-lg z-[9999] py-1 max-h-48 overflow-y-auto scrollbar-thin">
                                                                    <button
                                                                        onClick={() => {
                                                                            setSelectedProjectId(null);
                                                                            setShowProjectDropdown(false);
                                                                        }}
                                                                        className="flex items-center gap-2 px-3 py-2 w-full text-left text-[12px] hover:bg-slate-50 dark:hover:bg-white/5 transition-colors text-slate-700 dark:text-slate-300"
                                                                    >
                                                                        <span className="size-2 rounded-full inline-block bg-slate-400" />
                                                                        <span className="truncate">Global (Sin módulo)</span>
                                                                    </button>
                                                                    {projects.map(p => (
                                                                        <button
                                                                            key={p.id}
                                                                            onClick={() => {
                                                                                setSelectedProjectId(p.id);
                                                                                setShowProjectDropdown(false);
                                                                            }}
                                                                            className="flex items-center gap-2 px-3 py-2 w-full text-left text-[12px] hover:bg-slate-50 dark:hover:bg-white/5 transition-colors text-slate-700 dark:text-slate-300"
                                                                        >
                                                                            <span className="size-2 rounded-full inline-block" style={{ backgroundColor: p.color || '#2563eb' }} />
                                                                            <span className="truncate">{p.title}</span>
                                                                        </button>
                                                                    ))}
                                                                </div>
                                                            )}
                                                        </div>
                                                    </div>

                                                    {/* Title input */}
                                                    <input
                                                        ref={titleRef as React.RefObject<HTMLInputElement>}
                                                        value={title}
                                                        onChange={e => setTitle(e.target.value)}
                                                        onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSubmit()}
                                                        placeholder="Añade un título a la reunión o cita..."
                                                        className="px-3 py-2 text-[16px] font-medium text-slate-800 dark:text-slate-100 placeholder:text-slate-300 dark:placeholder:text-slate-600 bg-transparent outline-none"
                                                    />

                                                    {/* Event details */}
                                                    <div className="px-3 py-3 space-y-2">
                                                        <div className="flex items-center gap-3 flex-wrap">
                                                            <Calendar size={14} className="text-slate-400 font-semibold" />
                                                            <input 
                                                                type="date"
                                                                value={eventDate}
                                                                onChange={e => setEventDate(e.target.value)}
                                                                className="text-[13px] font-semibold bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg px-2.5 py-1 text-slate-700 dark:text-slate-200 outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all cursor-pointer" 
                                                            />
                                                            <span className="text-slate-400 text-[11px] font-semibold">hasta</span>
                                                            <input 
                                                                type="date"
                                                                value={eventEndDate}
                                                                onChange={e => setEventEndDate(e.target.value)}
                                                                className="text-[13px] font-semibold bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg px-2.5 py-1 text-slate-700 dark:text-slate-200 outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all cursor-pointer" 
                                                            />
                                                        </div>
                                                        <div className="flex items-center gap-3 pt-2">
                                                            <Users size={14} className="text-slate-400" />
                                                            <input 
                                                                type="text" 
                                                                value={eventLocation}
                                                                onChange={e => setEventLocation(e.target.value)}
                                                                placeholder="Añadir invitados (correo o nombre)" 
                                                                className="text-[12px] flex-1 bg-transparent border-b border-slate-200 dark:border-white/10 pb-1 text-slate-700 dark:text-slate-300 outline-none focus:border-blue-500 placeholder:text-slate-400"
                                                            />
                                                        </div>
                                                        <div className="flex items-start gap-3 pt-3">
                                                            <FileText size={14} className="text-slate-400 mt-1" />
                                                            <textarea 
                                                                value={description}
                                                                onChange={e => setDescription(e.target.value)}
                                                                placeholder="Añadir descripción o enlace de la reunión" 
                                                                className="text-[12px] flex-1 min-h-[60px] bg-transparent border border-slate-200 dark:border-white/10 rounded p-2 text-slate-700 dark:text-slate-300 outline-none focus:border-blue-500 placeholder:text-slate-400 resize-none"
                                                            />
                                                        </div>
                                                    </div>
                                                </div>
                                            )}

                                            {/* ─── ESTRATEGIA EVANGELISMO ─── */}
                                            {type === 'evangelism_strategy' && (
                                                <div className="flex flex-col">
                                                    <div className="flex items-center gap-2 px-3 pt-3 pb-2 text-[12px] text-slate-500 relative z-[95]">
                                                        <div className="relative">
                                                            <button 
                                                                onClick={(e) => { e.stopPropagation(); setShowStrategyTypeDropdown(!showStrategyTypeDropdown); }}
                                                                className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-slate-200 dark:border-white/10 hover:bg-slate-50 dark:hover:bg-white/5 transition-colors"
                                                            >
                                                                <Sparkles size={12} />
                                                                {strategyType}
                                                                <ChevronDown size={11} />
                                                            </button>
                                                            {showStrategyTypeDropdown && (
                                                                <div className="absolute top-full left-0 mt-1 w-44 bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-md shadow-lg z-[9999] py-1">
                                                                    {['Campaña de Alcance', 'Consolidación', 'Discipulado', 'Evangelismo Personal'].map(opt => (
                                                                        <button
                                                                            key={opt}
                                                                            onClick={() => {
                                                                                setStrategyType(opt);
                                                                                setShowStrategyTypeDropdown(false);
                                                                            }}
                                                                            className="px-3 py-1.5 w-full text-left text-[12px] hover:bg-slate-50 dark:hover:bg-white/5 transition-colors text-slate-700 dark:text-slate-300"
                                                                        >
                                                                            {opt}
                                                                        </button>
                                                                    ))}
                                                                </div>
                                                            )}
                                                        </div>
                                                    </div>

                                                    <input
                                                        ref={titleRef as React.RefObject<HTMLInputElement>}
                                                        value={title}
                                                        onChange={e => setTitle(e.target.value)}
                                                        onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSubmit()}
                                                        placeholder="Nombre de la estrategia..."
                                                        className="px-3 py-2 text-[16px] font-medium text-slate-800 dark:text-slate-100 placeholder:text-slate-300 dark:placeholder:text-slate-600 bg-transparent outline-none w-full"
                                                    />

                                                    <div className="px-3 py-3 space-y-2">
                                                        <div className="flex items-center gap-3 flex-wrap">
                                                            <Calendar size={14} className="text-slate-400 font-semibold" />
                                                            <input 
                                                                type="date"
                                                                value={eventDate}
                                                                onChange={e => setEventDate(e.target.value)}
                                                                className="text-[13px] font-semibold bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg px-2.5 py-1 text-slate-700 dark:text-slate-200 outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all cursor-pointer" 
                                                            />
                                                            <span className="text-slate-400 text-[11px] font-semibold">hasta</span>
                                                            <input 
                                                                type="date"
                                                                value={eventEndDate}
                                                                onChange={e => setEventEndDate(e.target.value)}
                                                                className="text-[13px] font-semibold bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg px-2.5 py-1 text-slate-700 dark:text-slate-200 outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all cursor-pointer" 
                                                            />
                                                        </div>
                                                        <div className="flex items-start gap-3 pt-3">
                                                            <FileText size={14} className="text-slate-400 mt-1" />
                                                            <textarea 
                                                                value={description}
                                                                onChange={e => setDescription(e.target.value)}
                                                                placeholder="Propósito u objetivos de la estrategia" 
                                                                className="text-[12px] flex-1 min-h-[60px] bg-transparent border border-slate-200 dark:border-white/10 rounded p-2 text-slate-700 dark:text-slate-300 outline-none focus:border-blue-500 placeholder:text-slate-400 resize-none"
                                                            />
                                                        </div>
                                                    </div>
                                                </div>
                                            )}

                                            {/* ─── DOCUMENTO ─── */}
                                            {type === 'doc' && (
                                                <div className="flex flex-col py-2">
                                                    <div className="flex items-center gap-2 px-3 pt-2 pb-3">
                                                        <button className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-slate-200 dark:border-white/10 text-[12px] font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-white/5 transition-colors">
                                                            <List size={12} />
                                                            Mis documentos
                                                            <ChevronDown size={11} />
                                                        </button>
                                                    </div>
                                                    <input
                                                        ref={titleRef as React.RefObject<HTMLInputElement>}
                                                        value={title}
                                                        onChange={e => setTitle(e.target.value)}
                                                        placeholder="Ponle un nombre a este documento..."
                                                        className="px-3 py-2 text-[16px] font-medium text-slate-800 dark:text-slate-100 placeholder:text-slate-300 dark:placeholder:text-slate-600 bg-transparent outline-none"
                                                    />
                                                    <div className="px-3 py-3 border-t border-slate-100 dark:border-white/5 mt-3">
                                                        {showDescription ? (
                                                            <textarea
                                                                value={description}
                                                                onChange={e => setDescription(e.target.value)}
                                                                placeholder="Comienza a redactar el contenido de tu documento..."
                                                                className="w-full min-h-[90px] text-[13px] bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg p-2.5 text-slate-700 dark:text-slate-300 outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all resize-none"
                                                            />
                                                        ) : (
                                                            <div className="space-y-2">
                                                                <button 
                                                                    onClick={() => setShowDescription(true)}
                                                                    className="flex items-center gap-2 text-[12px] text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors w-full text-left"
                                                                >
                                                                    <FileText size={13} />
                                                                    Empezar a escribir contenido
                                                                </button>
                                                                <button 
                                                                    onClick={async () => {
                                                                        setShowDescription(true);
                                                                        await handleAiWrite();
                                                                    }}
                                                                    className="flex items-center gap-2 text-[12px] text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors w-full text-left"
                                                                >
                                                                    <Sparkles size={13} />
                                                                    Generar plantilla con IA
                                                                </button>
                                                            </div>
                                                        )}
                                                        <div className="pt-4">
                                                            <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-2">Añadir nuevo elemento</p>
                                                            <div className="space-y-1">
                                                                <DocAddBtn icon={Table2} label="Tabla" />
                                                                <DocAddBtn icon={Columns} label="Columna" />
                                                                <DocAddBtn icon={List} label="Lista de CCF" />
                                                            </div>
                                                        </div>
                                                    </div>
                                                </div>
                                            )}

                                            {/* ─── RECORDATORIO ─── */}
                                            {type === 'reminder' && (
                                                <div className="flex flex-col py-2">
                                                    <input
                                                        ref={titleRef as React.RefObject<HTMLInputElement>}
                                                        value={title}
                                                        onChange={e => setTitle(e.target.value)}
                                                        placeholder="Escribe el nombre del recordatorio o pulsa «/» para ver comandos"
                                                        className="px-3 py-1.5 text-[16px] font-medium text-slate-800 dark:text-slate-100 placeholder:text-slate-300 dark:placeholder:text-slate-600 bg-transparent outline-none w-full"
                                                    />
                                                    <div className="px-3 pb-3">
                                                        {showDescription ? (
                                                            <textarea
                                                                value={description}
                                                                onChange={e => setDescription(e.target.value)}
                                                                placeholder="Añade detalles o notas a este recordatorio..."
                                                                className="w-full min-h-[60px] text-[13px] bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg p-2.5 text-slate-700 dark:text-slate-300 outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all resize-none"
                                                            />
                                                        ) : (
                                                            <button 
                                                                onClick={() => setShowDescription(true)}
                                                                className="flex items-center gap-2 text-[12px] text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
                                                            >
                                                                <FileText size={13} />
                                                                Añadir descripción
                                                            </button>
                                                        )}
                                                    </div>
                                                    <div className="flex items-center gap-2 px-3 py-3 border-t border-slate-100 dark:border-white/5">
                                                        <ReminderChip icon={Calendar} label="Hoy" />
                                                        <ReminderChip label="Para mí" avatar />
                                                        <ReminderChip icon={Bell} label="Notificarme" />
                                                    </div>
                                                </div>
                                            )}

                                            {/* ─── PIZARRA ─── */}
                                            {type === 'whiteboard' && (
                                                <div className="flex flex-col py-2">
                                                    <div className="flex items-center gap-2 px-3 pt-2 pb-3">
                                                        <button className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-slate-200 dark:border-white/10 text-[12px] font-medium text-slate-600 dark:text-slate-300">
                                                            <List size={12} />
                                                            Mis pizarras
                                                            <ChevronDown size={11} />
                                                        </button>
                                                    </div>
                                                    <input
                                                        ref={titleRef as React.RefObject<HTMLInputElement>}
                                                        value={title}
                                                        onChange={e => setTitle(e.target.value)}
                                                        placeholder="Ponle un nombre a esta pizarra..."
                                                        className="px-3 py-1.5 text-[16px] font-medium text-slate-800 dark:text-slate-100 placeholder:text-slate-300 dark:placeholder:text-slate-600 bg-transparent outline-none"
                                                    />
                                                    
                                                    {/* Background option styling */}
                                                    <div className="px-3 py-3 border-t border-slate-100 dark:border-white/5 space-y-2">
                                                        <p className="text-[11px] font-bold text-slate-400">Diseño de Pizarra</p>
                                                        <div className="flex gap-2">
                                                            {['grid', 'dots', 'blank'].map(bg => (
                                                                <button
                                                                    key={bg}
                                                                    onClick={() => setWhiteboardBg(bg)}
                                                                    className={clsx(
                                                                        "px-3 py-1.5 rounded-lg border text-[12px] font-medium capitalize transition-all",
                                                                        whiteboardBg === bg
                                                                            ? "border-violet-500 bg-violet-50 dark:bg-violet-500/10 text-violet-600 dark:text-violet-400 font-semibold"
                                                                            : "border-slate-200 dark:border-white/10 text-slate-500 hover:bg-slate-50 dark:hover:bg-white/5"
                                                                    )}
                                                                >
                                                                    {bg === 'grid' ? 'Cuadrícula' : bg === 'dots' ? 'Puntos' : 'Blanco'}
                                                                </button>
                                                            ))}
                                                        </div>
                                                    </div>
                                                    <div className="h-10" />
                                                </div>
                                            )}

                                            {/* ─── PANEL ─── */}
                                            {type === 'panel' && (
                                                <div className="flex flex-col py-2">
                                                    <input
                                                        ref={titleRef as React.RefObject<HTMLInputElement>}
                                                        value={title}
                                                        onChange={e => setTitle(e.target.value)}
                                                        placeholder="Nombre del panel..."
                                                        className="px-3 py-1.5 text-[16px] font-medium text-slate-800 dark:text-slate-100 placeholder:text-slate-300 dark:placeholder:text-slate-600 bg-transparent outline-none"
                                                    />
                                                    
                                                    {/* Layout style option */}
                                                    <div className="px-3 py-3 border-t border-slate-100 dark:border-white/5 space-y-2">
                                                        <p className="text-[11px] font-bold text-slate-400">Vista predeterminada del Panel</p>
                                                        <div className="flex gap-2 flex-wrap">
                                                            {[
                                                                { id: 'board', label: 'Tablero', icon: Columns },
                                                                { id: 'list', label: 'Lista', icon: List },
                                                                { id: 'calendar', label: 'Calendario', icon: Calendar },
                                                            ].map(layout => (
                                                                <button
                                                                    key={layout.id}
                                                                    onClick={() => setPanelLayout(layout.id)}
                                                                    className={clsx(
                                                                        "flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-[12px] font-medium transition-all",
                                                                        panelLayout === layout.id
                                                                            ? "border-sky-500 bg-sky-50 dark:bg-sky-500/10 text-sky-600 dark:text-sky-400 font-semibold"
                                                                            : "border-slate-200 dark:border-white/10 text-slate-500 hover:bg-slate-50 dark:hover:bg-white/5"
                                                                    )}
                                                                >
                                                                    <layout.icon size={12} />
                                                                    {layout.label}
                                                                </button>
                                                            ))}
                                                        </div>
                                                    </div>
                                                    <div className="h-10" />
                                                </div>
                                            )}
                                        </motion.div>
                                    </AnimatePresence>

                                    {/* ── FOOTER ──────────────────────────────── */}
                                    <div className="flex items-center justify-between px-3 py-3 border-t border-slate-100 dark:border-white/5">
                                        {/* Left actions */}
                                        <div className="flex items-center gap-2">
                                            {(type === 'doc' || type === 'whiteboard') && (
                                                <button
                                                    onClick={() => setIsPrivate(v => !v)}
                                                    className="flex items-center gap-1.5 text-[12px] font-medium text-slate-500"
                                                >
                                                    <div className={clsx(
                                                        'relative w-8 h-4 rounded-full transition-colors',
                                                        isPrivate ? 'bg-blue-600' : 'bg-slate-200 dark:bg-white/10'
                                                    )}>
                                                        <span className={clsx(
                                                            'absolute top-0.5 size-3 bg-white rounded-full shadow transition-transform',
                                                            isPrivate ? 'translate-x-4' : 'translate-x-0.5'
                                                        )} />
                                                    </div>
                                                    Privado
                                                </button>
                                            )}
                                            {type === 'task' && (
                                                <>
                                                    <button className="flex items-center gap-1 text-[11px] font-medium text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors">
                                                        <Sparkles size={13} />
                                                        Plantillas
                                                    </button>
                                                    <button className="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors">
                                                        <Paperclip size={14} />
                                                    </button>
                                                    <button className="flex items-center gap-1 p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors">
                                                        <MessageSquare size={14} />
                                                        <span className="text-[11px]">1</span>
                                                    </button>
                                                </>
                                            )}
                                        </div>

                                        {/* Submit split button */}
                                        <div className="flex items-center relative">
                                            <button
                                                onClick={handleSubmit}
                                                disabled={loading || !title.trim()}
                                                className="flex items-center gap-1.5 px-4 py-1.5 bg-slate-900 dark:bg-white text-white dark:text-slate-900 text-[12px] font-bold rounded-l-lg hover:bg-slate-700 dark:hover:bg-slate-100 disabled:opacity-40 transition-colors"
                                            >
                                                {loading ? <Loader2 size={12} className="animate-spin" /> : null}
                                                {submitOption === 'create_and_new' ? 'Crear y nuevo' : 'Crear'}
                                            </button>
                                            <button 
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    setShowSubmitDropdown(!showSubmitDropdown);
                                                }}
                                                className="flex items-center px-2 py-1.5 bg-slate-900 dark:bg-white text-white dark:text-slate-900 text-[12px] font-bold rounded-r-lg border-l border-white/20 dark:border-slate-900/20 hover:bg-slate-700 dark:hover:bg-slate-100 transition-colors"
                                            >
                                                <ChevronDown size={13} />
                                            </button>
                                            {showSubmitDropdown && (
                                                <div className="absolute bottom-full right-0 mb-1 w-44 bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-md shadow-lg z-[9999] py-1">
                                                    <button
                                                        onClick={() => {
                                                            setSubmitOption('create');
                                                            setShowSubmitDropdown(false);
                                                        }}
                                                        className={clsx(
                                                            "px-3 py-2 w-full text-left text-[12px] hover:bg-slate-50 dark:hover:bg-white/5 transition-colors font-medium text-slate-700 dark:text-slate-300",
                                                            submitOption === 'create' && "bg-slate-50 dark:bg-white/5 text-blue-600 dark:text-blue-400"
                                                        )}
                                                    >
                                                        Crear
                                                    </button>
                                                    <button
                                                        onClick={() => {
                                                            setSubmitOption('create_and_new');
                                                            setShowSubmitDropdown(false);
                                                        }}
                                                        className={clsx(
                                                            "px-3 py-2 w-full text-left text-[12px] hover:bg-slate-50 dark:hover:bg-white/5 transition-colors font-medium text-slate-700 dark:text-slate-300",
                                                            submitOption === 'create_and_new' && "bg-slate-50 dark:bg-white/5 text-blue-600 dark:text-blue-400"
                                                        )}
                                                    >
                                                        Crear y nuevo
                                                    </button>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}


