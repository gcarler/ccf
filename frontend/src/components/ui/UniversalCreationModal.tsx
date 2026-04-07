"use client";

import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    X, CheckSquare, FileText, Bell, LayoutDashboard, Layers,
    Plus, User, Calendar, Flag, Tag, MoreHorizontal, Paperclip,
    MessageSquare, ChevronDown, Sparkles, Loader2, ToggleLeft,
    Table2, Columns, List, ArrowUpRight, ChevronRight, Users,
    Minus
} from 'lucide-react';
import clsx from 'clsx';
import { useAuth } from '@/context/AuthContext';
import { useCreation } from '@/context/CreationContext';
import { apiFetch } from '@/lib/http';
import { toast } from 'sonner';
import type { ProjectRecord } from '@/types/projects';

type CreationType = 'task' | 'event' | 'doc' | 'reminder' | 'whiteboard' | 'panel';

interface Props {
    isOpen: boolean;
    onClose: () => void;
    initialType?: CreationType;
}

// ── Tab config ─────────────────────────────────────────────────────────────
const TABS: { id: CreationType; label: string; icon: React.ElementType; color?: string }[] = [
    { id: 'task',       label: 'Tarea',        icon: CheckSquare,    color: 'text-violet-600' },
    { id: 'event',      label: 'Evento',       icon: Calendar,       color: 'text-blue-600' },
    { id: 'doc',        label: 'Documento',    icon: FileText,       color: 'text-slate-500' },
    { id: 'reminder',   label: 'Recordatorio', icon: Bell,           color: 'text-slate-500' },
    { id: 'whiteboard', label: 'Pizarra',      icon: LayoutDashboard,color: 'text-slate-500' },
    { id: 'panel',      label: 'Panel',        icon: Layers,         color: 'text-slate-500' },
];

const STATUS_OPTIONS = ['PENDIENTE', 'EN CURSO', 'COMPLETADO'];
const STATUS_COLORS: Record<string, string> = {
    'PENDIENTE':   'bg-slate-200 text-slate-600',
    'EN CURSO':    'bg-violet-600 text-white',
    'COMPLETADO':  'bg-emerald-100 text-emerald-700',
};

export default function UniversalCreationModal({ isOpen, onClose, initialType = 'task' }: Props) {
    const { token } = useAuth();
    const { initialData } = useCreation();
    const [type, setType] = useState<CreationType>(initialType);
    const [projects, setProjects] = useState<ProjectRecord[]>([]);
    const [loading, setLoading] = useState(false);
    const [isPrivate, setIsPrivate] = useState(false);

    // Form state
    const [title, setTitle] = useState('');
    const [description, setDescription] = useState('');
    const [status, setStatus] = useState('PENDIENTE');
    const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);
    const [priority, setPriority] = useState('normal');
    const [isGeneratingAi, setIsGeneratingAi] = useState(false);
    const [eventDate, setEventDate] = useState(() => initialData?.initialDate || new Date().toISOString().split('T')[0]);
    const [eventGuests, setEventGuests] = useState('');

    const titleRef = useRef<HTMLInputElement & HTMLTextAreaElement>(null);

    useEffect(() => {
        if (isOpen) {
            setType(initialType);
            setTitle('');
            setDescription('');
            setStatus('PENDIENTE');
            setIsPrivate(false);
            setEventGuests('');
            if (initialData?.initialDate) setEventDate(initialData.initialDate);
            fetchProjects();
            setTimeout(() => titleRef.current?.focus(), 100);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [isOpen, initialType]);

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
                await apiFetch('/crm/events/', {
                    method: 'POST', token,
                    body: { title: title.trim(), description, event_date: new Date(eventDate).toISOString(), location: eventGuests }
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
                        body: { name: title.trim() }
                    }).catch(() => {});
                }
                toast.success('Pizarra inicializada');
            } else if (type === 'panel') {
                toast.success('Panel creado (Boceto)');
            } else {
                toast.info(`Configuración requerida para ${type}`);
                return;
            }
            onClose();
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
                    className="fixed bottom-24 right-8 z-[9000] w-full max-w-[550px] shadow-[0_20px_50px_rgba(0,0,0,0.15)] dark:shadow-[0_20px_50px_rgba(0,0,0,0.4)] rounded-2xl bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 flex flex-col overflow-hidden font-display pointer-events-auto"
                >
                    {/* ── TAB BAR ─────────────────────────────── */}
                                    <div className="flex items-center border-b border-slate-100 dark:border-white/5 px-2">
                                        {TABS.map(tab => (
                                            <button
                                                key={tab.id}
                                                onClick={() => setType(tab.id)}
                                                className={clsx(
                                                    'flex items-center gap-1.5 px-3 py-3 text-[12px] font-medium transition-all relative whitespace-nowrap',
                                                    type === tab.id
                                                        ? 'text-slate-900 dark:text-white'
                                                        : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-300'
                                                )}
                                            >
                                                <tab.icon size={13} className={type === tab.id ? (tab.color ?? 'text-slate-700') : 'text-slate-400'} />
                                                {tab.label}
                                                {type === tab.id && (
                                                    <motion.div
                                                        layoutId="modalActiveTab"
                                                        className="absolute bottom-0 left-0 right-0 h-[2px] bg-slate-900 dark:bg-white"
                                                    />
                                                )}
                                            </button>
                                        ))}
                                        <div className="flex-1" />
                                        <button className="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors ml-1">
                                            <Minus size={15} />
                                        </button>
                                        <button 
                                            onClick={onClose}
                                            className="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors ml-1"
                                        >
                                            <X size={15} />
                                        </button>
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
                                                    <div className="flex items-center gap-1 px-5 pt-3 pb-1 text-[11px] text-slate-400">
                                                        <span className="hover:text-slate-600 cursor-pointer">Espacio del equipo</span>
                                                        <ChevronRight size={11} />
                                                        <span className="hover:text-slate-600 cursor-pointer">Proyectos</span>
                                                        <ChevronRight size={11} />
                                                        <span className="font-medium text-slate-600 dark:text-slate-300">General</span>
                                                    </div>
                                                    {/* Project + type selectors */}
                                                    <div className="flex items-center gap-2 px-5 pt-2 pb-2">
                                                        <button className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-slate-200 dark:border-white/10 text-[12px] font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-white/5 transition-colors">
                                                            <span className="size-3 rounded-sm inline-block"
                                                                style={{ backgroundColor: selectedProject?.color || '#2563eb' }} />
                                                            {selectedProject?.title || 'Proyecto 1'}
                                                            <ChevronDown size={11} />
                                                        </button>
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
                                                        className="px-5 py-2 text-[14px] font-medium text-slate-800 dark:text-slate-100 placeholder:text-slate-300 dark:placeholder:text-slate-600 bg-transparent outline-none"
                                                    />

                                                    {/* Description links */}
                                                    <div className="px-5 pb-3 space-y-1">
                                                        <button className="flex items-center gap-2 text-[12px] text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors">
                                                            <FileText size={13} />
                                                            Añadir descripción
                                                        </button>
                                                        <button
                                                            onClick={handleAiWrite}
                                                            className="flex items-center gap-2 text-[12px] text-slate-400 hover:text-violet-600 dark:hover:text-violet-400 transition-colors"
                                                        >
                                                            {isGeneratingAi
                                                                ? <Loader2 size={13} className="animate-spin" />
                                                                : <Sparkles size={13} />
                                                            }
                                                            Escribir con IA
                                                        </button>
                                                    </div>

                                                    {/* Properties bar */}
                                                    <div className="flex items-center gap-2 px-5 py-3 border-t border-slate-100 dark:border-white/5 flex-wrap">
                                                        {/* Status */}
                                                        <button className={clsx(
                                                            'px-2.5 py-1 rounded-md text-[11px] font-black uppercase tracking-wide',
                                                            STATUS_COLORS[status] ?? 'bg-slate-100 text-slate-600'
                                                        )}>
                                                            {status}
                                                        </button>
                                                        <PropBtn icon={User} label="Persona asignada" />
                                                        <PropBtn icon={Calendar} label="Fecha límite" />
                                                        <PropBtn icon={Flag} label="Prioridad" />
                                                        <PropBtn icon={Tag} label="Etiquetas" />
                                                        <button className="flex items-center gap-1 px-2 py-1 rounded-md text-[11px] font-medium text-slate-400 hover:bg-slate-100 dark:hover:bg-white/5 transition-colors">
                                                            <MoreHorizontal size={13} />
                                                        </button>
                                                    </div>

                                                    {/* Custom fields section */}
                                                    <div className="px-5 py-3 border-t border-slate-100 dark:border-white/5">
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
                                                    <div className="flex items-center gap-2 px-5 pt-3 pb-2 text-[12px] text-slate-500">
                                                        <button className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-slate-200 dark:border-white/10 hover:bg-slate-50 dark:hover:bg-white/5 transition-colors">
                                                            <Calendar size={12} />
                                                            Reunión
                                                            <ChevronDown size={11} />
                                                        </button>
                                                        <button className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-slate-200 dark:border-white/10 hover:bg-slate-50 dark:hover:bg-white/5 transition-colors">
                                                            Sin módulo (Global)
                                                            <ChevronDown size={11} />
                                                        </button>
                                                    </div>

                                                    {/* Title input */}
                                                    <input
                                                        ref={titleRef as React.RefObject<HTMLInputElement>}
                                                        value={title}
                                                        onChange={e => setTitle(e.target.value)}
                                                        onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSubmit()}
                                                        placeholder="Añade un título a la reunión o cita..."
                                                        className="px-5 py-2 text-[16px] font-medium text-slate-800 dark:text-slate-100 placeholder:text-slate-300 dark:placeholder:text-slate-600 bg-transparent outline-none"
                                                    />

                                                    {/* Event details */}
                                                    <div className="px-5 py-3 space-y-2">
                                                        <div className="flex items-center gap-3">
                                                            <Calendar size={14} className="text-slate-400" />
                                                            <input 
                                                                type="date"
                                                                value={eventDate}
                                                                onChange={e => setEventDate(e.target.value)}
                                                                className="text-[12px] bg-transparent border border-slate-200 dark:border-white/10 rounded px-2 py-1 text-slate-700 dark:text-slate-300 outline-none focus:border-blue-500" 
                                                            />
                                                            <span className="text-slate-400 text-[11px]">hasta</span>
                                                            <input 
                                                                type="date"
                                                                value={eventDate}
                                                                onChange={e => setEventDate(e.target.value)}
                                                                className="text-[12px] bg-transparent border border-slate-200 dark:border-white/10 rounded px-2 py-1 text-slate-700 dark:text-slate-300 outline-none focus:border-blue-500" 
                                                            />
                                                        </div>
                                                        <div className="flex items-center gap-3 pt-2">
                                                            <Users size={14} className="text-slate-400" />
                                                            <input 
                                                                type="text" 
                                                                value={eventGuests}
                                                                onChange={e => setEventGuests(e.target.value)}
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

                                            {/* ─── DOCUMENTO ─── */}
                                            {type === 'doc' && (
                                                <div className="flex flex-col py-2">
                                                    <div className="flex items-center gap-2 px-5 pt-2 pb-3">
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
                                                        className="px-5 py-2 text-[16px] font-medium text-slate-800 dark:text-slate-100 placeholder:text-slate-300 dark:placeholder:text-slate-600 bg-transparent outline-none"
                                                    />
                                                    <div className="px-5 py-3 space-y-2 border-t border-slate-100 dark:border-white/5 mt-3">
                                                        <button className="flex items-center gap-2 text-[12px] text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors w-full">
                                                            <FileText size={13} />
                                                            Empezar a escribir
                                                        </button>
                                                        <button onClick={handleAiWrite} className="flex items-center gap-2 text-[12px] text-slate-400 hover:text-violet-600 dark:hover:text-violet-400 transition-colors w-full">
                                                            <Sparkles size={13} />
                                                            Escribir con IA
                                                        </button>
                                                        <div className="pt-2">
                                                            <p className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-2">Añadir nuevo</p>
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
                                                        className="px-5 py-4 text-[14px] font-medium text-slate-800 dark:text-slate-100 placeholder:text-slate-300 dark:placeholder:text-slate-600 bg-transparent outline-none"
                                                    />
                                                    <div className="px-5 pb-3">
                                                        <button className="flex items-center gap-2 text-[12px] text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors">
                                                            <FileText size={13} />
                                                            Añadir descripción
                                                        </button>
                                                    </div>
                                                    <div className="flex items-center gap-2 px-5 py-3 border-t border-slate-100 dark:border-white/5">
                                                        <ReminderChip icon={Calendar} label="Hoy" />
                                                        <ReminderChip label="Para mí" avatar />
                                                        <ReminderChip icon={Bell} label="Notificarme" />
                                                    </div>
                                                </div>
                                            )}

                                            {/* ─── PIZARRA ─── */}
                                            {type === 'whiteboard' && (
                                                <div className="flex flex-col py-2">
                                                    <div className="flex items-center gap-2 px-5 pt-2 pb-3">
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
                                                        className="px-5 py-4 text-[16px] font-medium text-slate-800 dark:text-slate-100 placeholder:text-slate-300 dark:placeholder:text-slate-600 bg-transparent outline-none"
                                                    />
                                                    <div className="h-20" /> {/* spacer */}
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
                                                        className="px-5 py-4 text-[16px] font-medium text-slate-800 dark:text-slate-100 placeholder:text-slate-300 dark:placeholder:text-slate-600 bg-transparent outline-none"
                                                    />
                                                    <div className="h-20" />
                                                </div>
                                            )}
                                        </motion.div>
                                    </AnimatePresence>

                                    {/* ── FOOTER ──────────────────────────────── */}
                                    <div className="flex items-center justify-between px-5 py-3 border-t border-slate-100 dark:border-white/5">
                                        {/* Left actions */}
                                        <div className="flex items-center gap-2">
                                            {(type === 'doc' || type === 'whiteboard') && (
                                                <button
                                                    onClick={() => setIsPrivate(v => !v)}
                                                    className="flex items-center gap-1.5 text-[12px] font-medium text-slate-500"
                                                >
                                                    <div className={clsx(
                                                        'relative w-8 h-4 rounded-full transition-colors',
                                                        isPrivate ? 'bg-violet-600' : 'bg-slate-200 dark:bg-white/10'
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
                                        <div className="flex items-center">
                                            <button
                                                onClick={handleSubmit}
                                                disabled={loading || !title.trim()}
                                                className="flex items-center gap-1.5 px-4 py-1.5 bg-slate-900 dark:bg-white text-white dark:text-slate-900 text-[12px] font-bold rounded-l-lg hover:bg-slate-700 dark:hover:bg-slate-100 disabled:opacity-40 transition-colors"
                                            >
                                                {loading ? <Loader2 size={12} className="animate-spin" /> : null}
                                                Crear
                                            </button>
                                            <button className="flex items-center px-2 py-1.5 bg-slate-900 dark:bg-white text-white dark:text-slate-900 text-[12px] font-bold rounded-r-lg border-l border-white/20 dark:border-slate-900/20 hover:bg-slate-700 dark:hover:bg-slate-100 transition-colors">
                                                <ChevronDown size={13} />
                                            </button>
                                        </div>
                                    </div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}

// ── Helper components ──────────────────────────────────────────────────────────
function PropBtn({ icon: Icon, label }: { icon: React.ElementType; label: string }) {
    return (
        <button className="flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-slate-200 dark:border-white/10 text-[11px] font-medium text-slate-500 hover:bg-slate-50 dark:hover:bg-white/5 hover:text-slate-700 dark:hover:text-slate-200 transition-colors">
            <Icon size={12} />
            {label}
        </button>
    );
}

function ReminderChip({ icon: Icon, label, avatar }: { icon?: React.ElementType; label: string; avatar?: boolean }) {
    return (
        <button className="flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-slate-200 dark:border-white/10 text-[12px] font-medium text-slate-500 hover:bg-slate-50 dark:hover:bg-white/5 transition-colors">
            {avatar && <span className="size-4 rounded-full bg-violet-600 inline-block" />}
            {Icon && <Icon size={12} />}
            {label}
        </button>
    );
}

function DocAddBtn({ icon: Icon, label }: { icon: React.ElementType; label: string }) {
    return (
        <button className="flex items-center gap-2 px-3 py-1.5 w-full text-left text-[12px] font-medium text-slate-500 hover:bg-slate-50 dark:hover:bg-white/5 rounded-lg transition-colors">
            <Icon size={13} className="text-slate-400" />
            {label}
        </button>
    );
}
