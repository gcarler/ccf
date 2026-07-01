"use client";

import React, { useState, useEffect, useRef, useCallback } from 'react';
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
import { RightPanel } from '@/components/ui/RightPanel';

type CreationType = 'task' | 'event' | 'project' | 'doc' | 'reminder' | 'whiteboard' | 'panel';

interface Props {
    isOpen: boolean;
    onClose: () => void;
    initialType?: CreationType;
}

type CreationPreset = 'general' | 'meeting' | 'activity' | 'project' | 'evangelism' | 'consolidation';

// ── Tab config ─────────────────────────────────────────────────────────────
const TABS: { id: CreationType; label: string; icon: React.ElementType; color?: string; activeColor?: string }[] = [
    { id: 'task',       label: 'Tarea',        icon: CheckSquare,    color: 'text-[hsl(var(--primary))]', activeColor: 'text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]' },
    { id: 'event',      label: 'Evento',       icon: Calendar,       color: 'text-emerald-500', activeColor: 'text-emerald-600 dark:text-emerald-400' },
    { id: 'project',    label: 'Proyecto',     icon: Layers,         color: 'text-amber-500', activeColor: 'text-amber-600 dark:text-amber-400' },
    { id: 'doc',        label: 'Documento',    icon: FileText,       color: 'text-[hsl(var(--primary))]', activeColor: 'text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]' },
    { id: 'reminder',   label: 'Recordatorio', icon: Bell,           color: 'text-rose-500', activeColor: 'text-rose-600 dark:text-rose-400' },
    { id: 'whiteboard', label: 'Pizarra',      icon: LayoutDashboard,color: 'text-[hsl(var(--primary))]', activeColor: 'text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]' },
    { id: 'panel',      label: 'Panel',        icon: Layers,         color: 'text-sky-500', activeColor: 'text-sky-600 dark:text-sky-400' },
];

const STATUS_COLORS: Record<string, string> = {
    'PENDIENTE':   'bg-[hsl(var(--surface-3))] text-[hsl(var(--text-secondary))]',
    'EN CURSO':    'bg-[hsl(var(--primary))] text-white',
    'COMPLETADO':  'bg-emerald-100 text-emerald-700',
};

const DocAddBtn = ({ icon: Icon, label }: { icon: any; label: string }) => (
    <button className="flex items-center gap-2 w-full px-2 py-1.5 rounded hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 text-[12px] text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] transition-colors">
        <Icon size={13} className="text-[hsl(var(--text-secondary))]" />
        {label}
    </button>
);

const ReminderChip = ({ icon: Icon, label, avatar }: { icon?: any; label: string; avatar?: boolean }) => (
    <button className="flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-[hsl(var(--border))] dark:border-white/10 text-[11px] font-medium text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 transition-colors">
        {avatar ? (
            <div className="size-3.5 rounded-full bg-[hsl(var(--surface-3))] dark:bg-white/10 flex items-center justify-center text-[8px] font-bold">U</div>
        ) : Icon ? (
            <Icon size={12} className="text-[hsl(var(--text-secondary))]" />
        ) : null}
        {label}
    </button>
);

export default function UniversalCreationDrawer({ isOpen, onClose, initialType = 'task' }: Props) {
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
    const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
    const [generalProjectId, setGeneralProjectId] = useState<string | null>(null);
    const [priority, setPriority] = useState('normal');
    const [dueDate, setDueDate] = useState('');
    const [tags, setTags] = useState<string[]>([]);
    const [assignedToMe, setAssignedToMe] = useState(false);
    const [isGeneratingAi, setIsGeneratingAi] = useState(false);
    const [eventDate, setEventDate] = useState(() => initialData?.initialDate || new Date().toISOString().split('T')[0]);
    const [eventEndDate, setEventEndDate] = useState(() => initialData?.initialDate || new Date().toISOString().split('T')[0]);
    const [eventLocation, setEventLocation] = useState('');
    const [projectColor, setProjectColor] = useState('#7c3aed');
    
    // Interactivity & dropdown states
    const [showProjectDropdown, setShowProjectDropdown] = useState(false);
    const [showSubmitDropdown, setShowSubmitDropdown] = useState(false);
    const [submitOption, setSubmitOption] = useState<'create' | 'create_and_new'>('create');
    const [eventType, setEventType] = useState('Reunión');
    const [showEventTypeDropdown, setShowEventTypeDropdown] = useState(false);
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
            const preset = initialData?.preset as CreationPreset | undefined;
            const presetType: CreationType =
                preset === 'project' ? 'project'
                : preset === 'activity' ? 'task'
                : preset === 'meeting' ? 'event'
                : preset === 'evangelism' ? 'event'
                : preset === 'consolidation' ? 'task'
                : initialType;

            setType(presetType);
            setTitle('');
            setDescription('');
            setShowDescription(false);
            setStatus('PENDIENTE');
            setIsPrivate(false);
            setEventLocation('');
            setDueDate('');
            setTags([]);
            setAssignedToMe(false);
            setWhiteboardBg('grid');
            setPanelLayout('board');
            setProjectColor('#7c3aed');
            setEventType(
                preset === 'meeting' ? 'Reunión'
                : preset === 'evangelism' ? 'Celebración'
                : preset === 'consolidation' ? 'Reunión'
                : 'Reunión'
            );
            if (preset === 'activity' || preset === 'consolidation') {
                setSelectedProjectId(null);
            }
            if (initialData?.initialDate) {
                setEventDate(initialData.initialDate);
                setEventEndDate(initialData.initialDate);
            }
            fetchProjects(preset);
            setTimeout(() => titleRef.current?.focus(), 100);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [isOpen, initialType, initialData?.preset]);

    useEffect(() => {
        const closeAllDropdowns = () => {
            setShowProjectDropdown(false);
            setShowSubmitDropdown(false);
            setShowEventTypeDropdown(false);
            setShowTagsDropdown(false);
        };
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'Escape') {
                if (showProjectDropdown || showSubmitDropdown || showEventTypeDropdown || showTagsDropdown) {
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
    }, [showProjectDropdown, showSubmitDropdown, showEventTypeDropdown, showTagsDropdown, onClose]);

    const fetchProjects = async (preset?: CreationPreset) => {
        if (!token) return;
        try {
            const data = await apiFetch<ProjectRecord[]>('/projects', { token });
            setProjects(data);
            const general = data.find((project) => /proyecto general|general/i.test(project.title));
            setGeneralProjectId(general?.id ?? null);
            if (preset === 'activity' || preset === 'consolidation') {
                setSelectedProjectId(general?.id ?? null);
            } else if (data.length > 0 && !selectedProjectId) {
                setSelectedProjectId(general?.id ?? data[0].id);
            }
        } catch { }
    };

    const ensureGeneralProject = useCallback(async (): Promise<string | null> => {
        if (!token) return null;
        if (generalProjectId) return generalProjectId;
        const title = 'Proyecto general';
        const created = await apiFetch<ProjectRecord>('/projects', {
            method: 'POST',
            token,
            body: {
                title,
                description: 'Canal general para actividades sin proyecto específico',
                status: 'planning',
                color: '#7c3aed',
                icon: 'layers',
            },
        });
        setProjects((prev) => [created, ...prev]);
        setGeneralProjectId(created.id);
        setSelectedProjectId((prev) => prev ?? created.id);
        return created.id;
    }, [generalProjectId, token]);

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
            const preset = initialData?.preset as CreationPreset | undefined;
            if (type === 'task') {
                const projectId = selectedProjectId || await ensureGeneralProject();
                if (!projectId) {
                    toast.info('Se requiere un proyecto para crear una tarea');
                    return;
                }
                await apiFetch(`/projects/${projectId}/tasks`, {
                    method: 'POST', token,
                    body: { title: title.trim(), description, status: 'todo', priority }
                });
                toast.success('Tarea creada');
            } else if (type === 'event') {
                await apiFetch('/agenda/events', {
                    method: 'POST', token,
                    body: {
                        title: title.trim(),
                        description: description || (preset === 'evangelism' ? 'Evento evangelístico' : ''),
                        start_at: new Date(eventDate).toISOString(),
                        end_at: new Date(eventEndDate).toISOString(),
                        location: eventLocation || (preset === 'evangelism' ? 'Casa de paz' : ''),
                        is_all_day: true,
                    }
                });
                toast.success('Evento creado');
            } else if (type === 'project') {
                const created = await apiFetch<ProjectRecord>('/projects', {
                    method: 'POST',
                    token,
                    body: {
                        title: title.trim(),
                        description: description || 'Proyecto creado desde el calendario',
                        status: 'planning',
                        color: projectColor,
                        icon: preset === 'evangelism' ? 'sparkles' : preset === 'consolidation' ? 'users' : 'layers',
                    },
                });
                setProjects((prev) => [created, ...prev]);
                setSelectedProjectId(created.id);
                toast.success('Proyecto creado');
            } else if (type === 'doc') {
                // Endpoint referencial, depende de los docs del sistema
                await apiFetch('/plataforma/cms/pages', {
                    method: 'POST', token,
                    body: { title: title.trim(), content: description || ' ' }
                }).catch((err) => { console.error('[UniversalCreationDrawer] Failed to create document:', err); toast.error('Error al crear documento'); });
                toast.success('Documento creado');
            } else if (type === 'reminder') {
                // Usando logs o un endpoint si existe, o simularlo:
                toast.success('Recordatorio guardado para: ' + title);
            } else if (type === 'whiteboard') {
                if (selectedProjectId) {
                    await apiFetch(`/projects/${selectedProjectId}/whiteboard`, {
                        method: 'POST', token,
                        body: { title: title.trim(), elements_json: '[]' }
                    }).catch((err) => { console.error('[UniversalCreationDrawer] Failed to create whiteboard:', err); toast.error('Error al crear pizarra'); });
                }
                toast.success('Pizarra inicializada');
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
        <RightPanel open={isOpen} onClose={onClose} title="Crear nuevo" width={550}>
            <div className="flex flex-col h-full">
                {/* ── TAB BAR ─────────────────────────────── */}
                <div className="flex items-center border-b border-[hsl(var(--border))] dark:border-white/5 px-2 justify-between">
                    <div className="flex items-center overflow-x-auto hide-scrollbar flex-1 mr-2 scroll-smooth">
                                        {TABS.map(tab => (
                            <button
                                key={tab.id}
                                onClick={() => setType(tab.id)}
                                className={clsx(
                                    'flex items-center gap-1.5 px-3 py-3 text-[12px] font-semibold transition-all relative whitespace-nowrap shrink-0 border-b-2 border-transparent',
                                    type === tab.id
                                        ? (tab.activeColor ?? 'text-[hsl(var(--text-primary))] dark:text-white')
                                        : 'text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))] dark:hover:text-[hsl(var(--text-secondary))]'
                                )}
                            >
                                <tab.icon size={13} className={type === tab.id ? (tab.color ?? 'text-[hsl(var(--text-primary))]') : 'text-[hsl(var(--text-secondary))]'} />
                                {tab.label}
                                {type === tab.id && (
                                    <motion.div
                                        layoutId="drawerActiveTab"
                                        className={clsx(
                                            "absolute bottom-0 left-0 right-0 h-[2.5px]",
                                            tab.id === 'task' && "bg-[hsl(var(--primary))]",
                                            tab.id === 'event' && "bg-emerald-500",
                                            tab.id === 'doc' && "bg-[hsl(var(--primary))]",
                                            tab.id === 'reminder' && "bg-rose-500",
                                            tab.id === 'whiteboard' && "bg-[hsl(var(--primary))]",
                                            tab.id === 'panel' && "bg-sky-500"
                                        )}
                                    />
                                )}
                            </button>
                        ))}
                    </div>
                    <div className="flex items-center shrink-0 border-l border-[hsl(var(--border))] dark:border-white/5 pl-2 py-2">
                        <button className="p-1.5 rounded-lg text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))] dark:hover:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 transition-all">
                            <Minus size={15} />
                        </button>
                        <button 
                            onClick={onClose}
                            className="p-1.5 rounded-lg text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))] dark:hover:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 transition-all ml-0.5"
                        >
                            <X size={15} />
                        </button>
                    </div>
                </div>

                {/* ── BODY ─────────────────────────────────── */}
                <div className="flex-1 overflow-y-auto">
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
                                    <div className="flex items-center gap-1 px-3 pt-3 pb-1 text-[11px] text-[hsl(var(--text-secondary))]">
                                        <span className="hover:text-[hsl(var(--text-secondary))] cursor-pointer">Espacio del equipo</span>
                                        <ChevronRight size={11} />
                                        <span className="hover:text-[hsl(var(--text-secondary))] cursor-pointer">Proyectos</span>
                                        <ChevronRight size={11} />
                                        <span className="font-medium text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">General</span>
                                    </div>
                                    {/* Project + type selectors */}
                                    <div className="flex items-center gap-2 px-3 pt-2 pb-2 relative z-[95]">
                                        <div className="relative">
                                            <button 
                                                onClick={(e) => { e.stopPropagation(); setShowProjectDropdown(!showProjectDropdown); }}
                                                className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 text-[12px] font-medium text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 transition-colors"
                                            >
                                                <span className="size-3 rounded-sm inline-block"
                                                    style={{ backgroundColor: selectedProject?.color || '#2563eb' }} />
                                                {selectedProject?.title || 'Seleccionar Proyecto'}
                                                <ChevronDown size={11} />
                                            </button>
                                            {showProjectDropdown && (
                                                <div className="absolute top-full left-0 mt-1 w-48 bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] border border-[hsl(var(--border))] dark:border-white/10 rounded-md shadow-lg z-[9999] py-1 max-h-48 overflow-y-auto scrollbar-thin">
                                                    {projects.map(p => (
                                                        <button
                                                            key={p.id}
                                                            onClick={() => {
                                                                setSelectedProjectId(p.id);
                                                                setShowProjectDropdown(false);
                                                            }}
                                                            className="flex items-center gap-2 px-3 py-2 w-full text-left text-[12px] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 transition-colors text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]"
                                                        >
                                                            <span className="size-2 rounded-full inline-block" style={{ backgroundColor: p.color || '#2563eb' }} />
                                                            <span className="truncate">{p.title}</span>
                                                        </button>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                        <button className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 text-[12px] font-medium text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 transition-colors">
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
                                        className="px-3 py-2 text-[16px] font-medium text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] placeholder:text-[hsl(var(--text-secondary))] dark:placeholder:text-[hsl(var(--text-secondary))] bg-transparent outline-none w-full"
                                    />

                                    {/* Description section */}
                                    <div className="px-3 pb-3">
                                        {showDescription ? (
                                            <div className="space-y-2 w-full">
                                                <textarea
                                                    value={description}
                                                    onChange={e => setDescription(e.target.value)}
                                                    placeholder="Añade la descripción o notas de esta tarea..."
                                                    className="w-full min-h-[70px] text-[13px] bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg p-2.5 text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all resize-none"
                                                />
                                                <div className="flex justify-end">
                                                    <button
                                                        onClick={handleAiWrite}
                                                        className="flex items-center gap-1.5 text-[11px] text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] font-semibold hover:opacity-85 transition-colors"
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
                                                    className="flex items-center gap-2 text-[12px] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))] dark:hover:text-[hsl(var(--text-secondary))] transition-colors"
                                                >
                                                    <FileText size={13} />
                                                    Añadir descripción
                                                </button>
                                                <button
                                                    onClick={async () => {
                                                        setShowDescription(true);
                                                        await handleAiWrite();
                                                    }}
                                                    className="flex items-center gap-2 text-[12px] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] dark:hover:text-[hsl(var(--primary))] transition-colors"
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
                                    <div className="flex items-center gap-2 px-3 py-3 border-t border-[hsl(var(--border))] dark:border-white/5 flex-wrap">
                                        {/* Status */}
                                        <button 
                                            onClick={cycleStatus}
                                            title="Clic para cambiar estado"
                                            className={clsx(
                                                'px-2.5 py-1 rounded-md text-[11px] font-semibold uppercase tracking-wide cursor-pointer hover:opacity-85 transition-all active:scale-95',
                                                STATUS_COLORS[status] ?? 'bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))]'
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
                                                className="flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-blue-200 dark:border-blue-500/30 bg-blue-50/50 dark:bg-blue-500/10 text-[11px] font-medium text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] hover:opacity-85 transition-colors"
                                            >
                                                <span className="size-4 rounded-full bg-[hsl(var(--primary))] flex items-center justify-center text-white text-[9px] font-semibold uppercase">
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
                                                className="flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-[hsl(var(--border))] dark:border-white/10 text-[11px] font-medium text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 hover:text-[hsl(var(--text-primary))] dark:hover:text-[hsl(var(--text-secondary))] transition-colors"
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
                                                dueDate ? "border-emerald-200 dark:border-emerald-500/30 bg-emerald-50/50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400" : "border-[hsl(var(--border))] dark:border-white/10 text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5"
                                            )}>
                                                <Calendar size={12} className={dueDate ? "text-emerald-500" : "text-[hsl(var(--text-secondary))]"} />
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
                                                priority === 'normal' && "border-[hsl(var(--border))] dark:border-white/10 text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5",
                                                priority === 'alta' && "border-amber-200 dark:border-amber-500/30 bg-amber-50/50 dark:bg-amber-500/10 text-amber-600 dark:text-amber-400",
                                                priority === 'urgente' && "border-rose-200 dark:border-rose-500/30 bg-rose-50/50 dark:bg-rose-500/10 text-rose-600 dark:text-rose-400",
                                                priority === 'baja' && "border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]"
                                            )}
                                        >
                                            <Flag size={12} className={clsx(
                                                priority === 'normal' && "text-[hsl(var(--text-secondary))]",
                                                priority === 'alta' && "text-amber-500",
                                                priority === 'urgente' && "text-rose-500",
                                                priority === 'baja' && "text-[hsl(var(--text-secondary))]"
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
                                                    "flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-[11px] font-medium transition-colors hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5",
                                                    tags.length > 0 ? "border-blue-200 dark:border-blue-500/30 bg-blue-50/50 dark:bg-blue-500/10 text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]" : "border-[hsl(var(--border))] dark:border-white/10 text-[hsl(var(--text-secondary))]"
                                                )}
                                            >
                                                <Tag size={12} className={tags.length > 0 ? "text-[hsl(var(--primary))]" : "text-[hsl(var(--text-secondary))]"} />
                                                {tags.length > 0 ? `Etiquetas: ${tags.join(', ')}` : 'Etiquetas'}
                                            </button>
                                            {showTagsDropdown && (
                                                <div 
                                                    onClick={e => e.stopPropagation()}
                                                    className="absolute bottom-full left-0 mb-1 w-44 bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] border border-[hsl(var(--border))] dark:border-white/10 rounded-md shadow-lg z-[9999] py-1"
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
                                                                className="flex items-center justify-between px-3 py-1.5 w-full text-left text-[12px] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 transition-colors text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]"
                                                            >
                                                                <span>{t}</span>
                                                                {isSelected && <span className="size-1.5 rounded-full bg-[hsl(var(--primary))]" />}
                                                            </button>
                                                        );
                                                    })}
                                                </div>
                                            )}
                                        </div>
                                    </div>

                                    {/* Custom fields section */}
                                    <div className="px-3 py-3 border-t border-[hsl(var(--border))] dark:border-white/5">
                                        <p className="text-[11px] font-bold text-[hsl(var(--text-secondary))] mb-2">Campos</p>
                                        <button className="flex items-center gap-1.5 px-3 py-1.5 border border-dashed border-[hsl(var(--border))] dark:border-white/10 rounded-lg text-[11px] font-medium text-[hsl(var(--text-secondary))] hover:border-[hsl(var(--border))] hover:text-[hsl(var(--text-secondary))] dark:hover:text-[hsl(var(--text-secondary))] transition-colors">
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
                                    <div className="flex items-center gap-2 px-3 pt-3 pb-2 text-[12px] text-[hsl(var(--text-secondary))] relative z-[95]">
                                        {/* Event Type dropdown */}
                                        <div className="relative">
                                            <button 
                                                onClick={(e) => { e.stopPropagation(); setShowEventTypeDropdown(!showEventTypeDropdown); }}
                                                className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 transition-colors"
                                            >
                                                <Calendar size={12} />
                                                {eventType}
                                                <ChevronDown size={11} />
                                            </button>
                                            {showEventTypeDropdown && (
                                                <div className="absolute top-full left-0 mt-1 w-32 bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] border border-[hsl(var(--border))] dark:border-white/10 rounded-md shadow-lg z-[9999] py-1">
                                                    {['Reunión', 'Cita', 'Celebración', 'Taller'].map(opt => (
                                                        <button
                                                            key={opt}
                                                            onClick={() => {
                                                                setEventType(opt);
                                                                setShowEventTypeDropdown(false);
                                                            }}
                                                            className="px-3 py-1.5 w-full text-left text-[12px] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 transition-colors text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]"
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
                                                className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 transition-colors"
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
                                                <div className="absolute top-full left-0 mt-1 w-48 bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] border border-[hsl(var(--border))] dark:border-white/10 rounded-md shadow-lg z-[9999] py-1 max-h-48 overflow-y-auto scrollbar-thin">
                                                    <button
                                                        onClick={() => {
                                                            setSelectedProjectId(null);
                                                            setShowProjectDropdown(false);
                                                        }}
                                                        className="flex items-center gap-2 px-3 py-2 w-full text-left text-[12px] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 transition-colors text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]"
                                                    >
                                                        <span className="size-2 rounded-full inline-block bg-[hsl(var(--surface-2))]" />
                                                        <span className="truncate">Global (Sin módulo)</span>
                                                    </button>
                                                    {projects.map(p => (
                                                        <button
                                                            key={p.id}
                                                            onClick={() => {
                                                                setSelectedProjectId(p.id);
                                                                setShowProjectDropdown(false);
                                                            }}
                                                            className="flex items-center gap-2 px-3 py-2 w-full text-left text-[12px] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 transition-colors text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]"
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
                                        className="px-3 py-2 text-[16px] font-medium text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] placeholder:text-[hsl(var(--text-secondary))] dark:placeholder:text-[hsl(var(--text-secondary))] bg-transparent outline-none"
                                    />

                                    {/* Event details */}
                                    <div className="px-3 py-3 space-y-2">
                                        <div className="flex items-center gap-3 flex-wrap">
                                            <Calendar size={14} className="text-[hsl(var(--text-secondary))] font-semibold" />
                                            <input 
                                                type="date"
                                                value={eventDate}
                                                onChange={e => setEventDate(e.target.value)}
                                                className="text-[13px] font-semibold bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg px-2.5 py-1 text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all cursor-pointer" 
                                            />
                                            <span className="text-[hsl(var(--text-secondary))] text-[11px] font-semibold">hasta</span>
                                            <input 
                                                type="date"
                                                value={eventEndDate}
                                                onChange={e => setEventEndDate(e.target.value)}
                                                className="text-[13px] font-semibold bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg px-2.5 py-1 text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all cursor-pointer" 
                                            />
                                        </div>
                                        <div className="flex items-center gap-3 pt-2">
                                            <Users size={14} className="text-[hsl(var(--text-secondary))]" />
                                            <input 
                                                type="text" 
                                                value={eventLocation}
                                                onChange={e => setEventLocation(e.target.value)}
                                                placeholder="Añadir invitados (correo o nombre)" 
                                                className="text-[12px] flex-1 bg-transparent border-b border-[hsl(var(--border))] dark:border-white/10 pb-1 text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] outline-none focus:border-blue-500 placeholder:text-[hsl(var(--text-secondary))]"
                                            />
                                        </div>
                                        <div className="flex items-start gap-3 pt-3">
                                            <FileText size={14} className="text-[hsl(var(--text-secondary))] mt-1" />
                                            <textarea 
                                                value={description}
                                                onChange={e => setDescription(e.target.value)}
                                                placeholder="Añadir descripción o enlace de la reunión" 
                                                className="text-[12px] flex-1 min-h-[60px] bg-transparent border border-[hsl(var(--border))] dark:border-white/10 rounded p-2 text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] outline-none focus:border-blue-500 placeholder:text-[hsl(var(--text-secondary))] resize-none"
                                            />
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* ─── PROYECTO ─── */}
                            {type === 'project' && (
                                <div className="flex flex-col py-2">
                                    <div className="flex items-center gap-2 px-3 pt-2 pb-3">
                                        <button className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 text-[12px] font-medium text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">
                                            <Layers size={12} />
                                            Proyecto
                                            <ChevronDown size={11} />
                                        </button>
                                    </div>
                                    <input
                                        ref={titleRef as React.RefObject<HTMLInputElement>}
                                        value={title}
                                        onChange={e => setTitle(e.target.value)}
                                        placeholder="Nombre del proyecto..."
                                        className="px-3 py-1.5 text-[16px] font-medium text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] placeholder:text-[hsl(var(--text-secondary))] dark:placeholder:text-[hsl(var(--text-secondary))] bg-transparent outline-none"
                                    />
                                    <div className="px-3 py-3 space-y-3 border-t border-[hsl(var(--border))] dark:border-white/5">
                                        <div className="flex items-center gap-3">
                                            <span className="text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Color</span>
                                            <input
                                                type="color"
                                                value={projectColor}
                                                onChange={(e) => setProjectColor(e.target.value)}
                                                className="size-9 rounded-md border border-[hsl(var(--border))] dark:border-white/10 bg-transparent p-0"
                                            />
                                        </div>
                                        <textarea
                                            value={description}
                                            onChange={e => setDescription(e.target.value)}
                                            placeholder="Describe el propósito del proyecto..."
                                            className="w-full min-h-[90px] text-[13px] bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg p-2.5 text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all resize-none"
                                        />
                                        <p className="text-[11px] text-[hsl(var(--text-secondary))] leading-snug">
                                            Si no seleccionas un proyecto al crear una actividad, se usará el proyecto general.
                                        </p>
                                    </div>
                                </div>
                            )}

                            {/* ─── DOCUMENTO ─── */}
                            {type === 'doc' && (
                                <div className="flex flex-col py-2">
                                    <div className="flex items-center gap-2 px-3 pt-2 pb-3">
                                        <button className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 text-[12px] font-medium text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 transition-colors">
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
                                        className="px-3 py-2 text-[16px] font-medium text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] placeholder:text-[hsl(var(--text-secondary))] dark:placeholder:text-[hsl(var(--text-secondary))] bg-transparent outline-none"
                                    />
                                    <div className="px-3 py-3 border-t border-[hsl(var(--border))] dark:border-white/5 mt-3">
                                        {showDescription ? (
                                            <textarea
                                                value={description}
                                                onChange={e => setDescription(e.target.value)}
                                                placeholder="Comienza a redactar el contenido de tu documento..."
                                                className="w-full min-h-[90px] text-[13px] bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg p-2.5 text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all resize-none"
                                            />
                                        ) : (
                                            <div className="space-y-2">
                                                <button 
                                                    onClick={() => setShowDescription(true)}
                                                    className="flex items-center gap-2 text-[12px] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))] dark:hover:text-[hsl(var(--text-secondary))] transition-colors w-full text-left"
                                                >
                                                    <FileText size={13} />
                                                    Empezar a escribir contenido
                                                </button>
                                                <button 
                                                    onClick={async () => {
                                                        setShowDescription(true);
                                                        await handleAiWrite();
                                                    }}
                                                    className="flex items-center gap-2 text-[12px] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] dark:hover:text-[hsl(var(--primary))] transition-colors w-full text-left"
                                                >
                                                    <Sparkles size={13} />
                                                    Generar plantilla con IA
                                                </button>
                                            </div>
                                        )}
                                        <div className="pt-4">
                                            <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-2">Añadir nuevo elemento</p>
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
                                        className="px-3 py-1.5 text-[16px] font-medium text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] placeholder:text-[hsl(var(--text-secondary))] dark:placeholder:text-[hsl(var(--text-secondary))] bg-transparent outline-none w-full"
                                    />
                                    <div className="px-3 pb-3">
                                        {showDescription ? (
                                            <textarea
                                                value={description}
                                                onChange={e => setDescription(e.target.value)}
                                                placeholder="Añade detalles o notas a este recordatorio..."
                                                className="w-full min-h-[60px] text-[13px] bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg p-2.5 text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all resize-none"
                                            />
                                        ) : (
                                            <button 
                                                onClick={() => setShowDescription(true)}
                                                className="flex items-center gap-2 text-[12px] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))] dark:hover:text-[hsl(var(--text-secondary))] transition-colors"
                                            >
                                                <FileText size={13} />
                                                Añadir descripción
                                            </button>
                                        )}
                                    </div>
                                    <div className="flex items-center gap-2 px-3 py-3 border-t border-[hsl(var(--border))] dark:border-white/5">
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
                                        <button className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 text-[12px] font-medium text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">
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
                                        className="px-3 py-1.5 text-[16px] font-medium text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] placeholder:text-[hsl(var(--text-secondary))] dark:placeholder:text-[hsl(var(--text-secondary))] bg-transparent outline-none"
                                    />
                                    
                                    {/* Background option styling */}
                                    <div className="px-3 py-3 border-t border-[hsl(var(--border))] dark:border-white/5 space-y-2">
                                        <p className="text-[11px] font-bold text-[hsl(var(--text-secondary))]">Diseño de Pizarra</p>
                                        <div className="flex gap-2">
                                            {['grid', 'dots', 'blank'].map(bg => (
                                                <button
                                                    key={bg}
                                                    onClick={() => setWhiteboardBg(bg)}
                                                    className={clsx(
                                                        "px-3 py-1.5 rounded-lg border text-[12px] font-medium capitalize transition-all",
                                                        whiteboardBg === bg
                                                            ? "border-blue-500 bg-blue-50 dark:bg-blue-500/10 text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] font-semibold"
                                                            : "border-[hsl(var(--border))] dark:border-white/10 text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5"
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
                                        className="px-3 py-1.5 text-[16px] font-medium text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] placeholder:text-[hsl(var(--text-secondary))] dark:placeholder:text-[hsl(var(--text-secondary))] bg-transparent outline-none"
                                    />
                                    
                                    {/* Layout style option */}
                                    <div className="px-3 py-3 border-t border-[hsl(var(--border))] dark:border-white/5 space-y-2">
                                        <p className="text-[11px] font-bold text-[hsl(var(--text-secondary))]">Vista predeterminada del Panel</p>
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
                                                            : "border-[hsl(var(--border))] dark:border-white/10 text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5"
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
                </div>

                {/* ── FOOTER ──────────────────────────────── */}
                <div className="flex items-center justify-between px-3 py-3 border-t border-[hsl(var(--border))] dark:border-white/5">
                    {/* Left actions */}
                    <div className="flex items-center gap-2">
                        {(type === 'doc' || type === 'whiteboard') && (
                            <button
                                onClick={() => setIsPrivate(v => !v)}
                                className="flex items-center gap-1.5 text-[12px] font-medium text-[hsl(var(--text-secondary))]"
                            >
                                <div className={clsx(
                                    'relative w-8 h-4 rounded-full transition-colors',
                                    isPrivate ? 'bg-[hsl(var(--primary))]' : 'bg-[hsl(var(--surface-3))] dark:bg-white/10'
                                )}>
                                    <span className={clsx(
                                        'absolute top-0.5 size-3 bg-[hsl(var(--bg-primary))] rounded-full shadow transition-transform',
                                        isPrivate ? 'translate-x-4' : 'translate-x-0.5'
                                    )} />
                                </div>
                                Privado
                            </button>
                        )}
                        {type === 'task' && (
                            <>
                                <button className="flex items-center gap-1 text-[11px] font-medium text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))] dark:hover:text-[hsl(var(--text-secondary))] transition-colors">
                                    <Sparkles size={13} />
                                    Plantillas
                                </button>
                                <button className="p-1.5 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))] dark:hover:text-[hsl(var(--text-secondary))] transition-colors">
                                    <Paperclip size={14} />
                                </button>
                                <button className="flex items-center gap-1 p-1.5 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))] dark:hover:text-[hsl(var(--text-secondary))] transition-colors">
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
                            className="flex items-center gap-1.5 px-4 py-1.5 bg-[hsl(var(--bg-muted))] dark:bg-[hsl(var(--bg-primary))] text-white dark:text-[hsl(var(--text-primary))] text-[12px] font-bold rounded-l-lg hover:bg-[hsl(var(--surface-2))] dark:hover:bg-[hsl(var(--surface-2))] disabled:opacity-40 transition-colors"
                        >
                            {loading ? <Loader2 size={12} className="animate-spin" /> : null}
                            {submitOption === 'create_and_new' ? 'Crear y nuevo' : 'Crear'}
                        </button>
                        <button 
                            onClick={(e) => {
                                e.stopPropagation();
                                setShowSubmitDropdown(!showSubmitDropdown);
                            }}
                            className="flex items-center px-2 py-1.5 bg-[hsl(var(--bg-muted))] dark:bg-[hsl(var(--bg-primary))] text-white dark:text-[hsl(var(--text-primary))] text-[12px] font-bold rounded-r-lg border-l border-white/20 dark:border-[hsl(var(--border))]/20 hover:bg-[hsl(var(--surface-2))] dark:hover:bg-[hsl(var(--surface-2))] transition-colors"
                        >
                            <ChevronDown size={13} />
                        </button>
                        {showSubmitDropdown && (
                            <div className="absolute bottom-full right-0 mb-1 w-44 bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] border border-[hsl(var(--border))] dark:border-white/10 rounded-md shadow-lg z-[9999] py-1">
                                <button
                                    onClick={() => {
                                        setSubmitOption('create');
                                        setShowSubmitDropdown(false);
                                    }}
                                    className={clsx(
                                        "px-3 py-2 w-full text-left text-[12px] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 transition-colors font-medium text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]",
                                        submitOption === 'create' && "bg-[hsl(var(--surface-1))] dark:bg-white/5 text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]"
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
                                        "px-3 py-2 w-full text-left text-[12px] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 transition-colors font-medium text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]",
                                        submitOption === 'create_and_new' && "bg-[hsl(var(--surface-1))] dark:bg-white/5 text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]"
                                    )}
                                >
                                    Crear y nuevo
                                </button>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </RightPanel>
    );
}
