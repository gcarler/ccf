"use client";

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    X, AlignLeft, Flag, Loader2, Bell,
    Paperclip, User, Calendar, ChevronDown, Wand2, Plus, Tag
} from 'lucide-react';
import clsx from 'clsx';
import { useToast } from '@/context/ToastContext';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';

export type OmniTab = 'task' | 'document' | 'reminder' | 'whiteboard' | 'panel';

interface Props {
    isOpen: boolean;
    initialTab?: OmniTab;
    defaultStatus?: string;
    onClose: () => void;
    onTaskSubmit: (data: {
        title: string;
        description: string;
        priority: string;
        status: string;
        due_date?: string;
        assignee_id?: number;
    }) => Promise<void>;
}

const TABS: { id: OmniTab; label: string }[] = [
    { id: 'task',       label: 'Tarea'        },
    { id: 'document',   label: 'Documento'    },
    { id: 'reminder',   label: 'Recordatorio' },
    { id: 'whiteboard', label: 'Pizarra'      },
    { id: 'panel',      label: 'Panel'        },
];

export default function OmniCreateModal({
    isOpen,
    initialTab = 'task',
    defaultStatus = 'PENDIENTE',
    onClose,
    onTaskSubmit,
}: Props) {
    const [activeTab, setActiveTab] = useState<OmniTab>(initialTab);
    const { addToast } = useToast();

    useEffect(() => {
        if (isOpen) setActiveTab(initialTab);
    }, [isOpen, initialTab]);

    // Close on Escape
    useEffect(() => {
        const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
        if (isOpen) window.addEventListener('keydown', handler);
        return () => window.removeEventListener('keydown', handler);
    }, [isOpen, onClose]);

    return (
        <AnimatePresence>
            {isOpen && (
                <>
                    {/* Backdrop */}
                    <motion.div
                        key="omni-backdrop"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={onClose}
                        className="fixed inset-0 z-[8999] bg-black/20 backdrop-blur-[2px]"
                    />

                    {/* Floating Panel — centered, ClickUp-style */}
                    <motion.div
                        key="omni-panel"
                        initial={{ opacity: 0, scale: 0.96, y: 16 }}
                        animate={{ opacity: 1, scale: 1,    y: 0  }}
                        exit={{   opacity: 0, scale: 0.96, y:  8  }}
                        transition={{ type: 'spring', stiffness: 380, damping: 30 }}
                        className="fixed left-1/2 top-[10vh] z-[9000] w-full max-w-[680px] -translate-x-1/2 rounded-2xl bg-white dark:bg-[#1e1f21] shadow-2xl border border-slate-200 dark:border-white/10 overflow-hidden flex flex-col"
                        style={{ minHeight: 360, maxHeight: '80vh' }}
                    >
                        {/* ── Tab Bar ── */}
                        <header className="shrink-0 bg-white dark:bg-[#1e1f21] border-b border-slate-100 dark:border-white/5">
                            <div className="relative flex items-center px-5 pt-1">
                                {TABS.map((tab) => {
                                    const active = activeTab === tab.id;
                                    return (
                                        <button
                                            key={tab.id}
                                            onClick={() => setActiveTab(tab.id)}
                                            className={clsx(
                                                'relative px-4 py-3 text-[13px] font-semibold transition-colors whitespace-nowrap',
                                                active
                                                    ? 'text-slate-900 dark:text-white'
                                                    : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-300'
                                            )}
                                        >
                                            {tab.label}
                                            {active && (
                                                <motion.div
                                                    layoutId="omni-underline"
                                                    className="absolute bottom-0 inset-x-2 h-[2px] bg-slate-900 dark:bg-white rounded-full"
                                                />
                                            )}
                                        </button>
                                    );
                                })}
                                <button
                                    onClick={onClose}
                                    className="ml-auto p-1.5 hover:bg-slate-100 dark:hover:bg-white/10 rounded-lg text-slate-400 transition-all hover:rotate-90 duration-200"
                                >
                                    <X size={16} />
                                </button>
                            </div>
                        </header>

                        {/* ── Content ── */}
                        <div className="flex-1 overflow-y-auto">
                            <AnimatePresence mode="wait">
                                {activeTab === 'task' && (
                                    <TaskForm key="task" defaultStatus={defaultStatus} onSubmit={onTaskSubmit} onClose={onClose} />
                                )}
                                {activeTab === 'document' && (
                                    <DocumentForm key="document" onClose={onClose} addToast={addToast} />
                                )}
                                {activeTab === 'reminder' && (
                                    <ReminderForm key="reminder" onClose={onClose} addToast={addToast} />
                                )}
                                {activeTab === 'whiteboard' && (
                                    <WhiteboardForm key="whiteboard" onClose={onClose} addToast={addToast} />
                                )}
                                {activeTab === 'panel' && (
                                    <PanelForm key="panel" onClose={onClose} addToast={addToast} />
                                )}
                            </AnimatePresence>
                        </div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
}

// ─────────────────────────────────────────────────────────────────────────────
// Task Form — matches modals de tarea.png exactly
// ─────────────────────────────────────────────────────────────────────────────
function TaskForm({ defaultStatus, onSubmit, onClose }: any) {
    const { token } = useAuth();
    const [title,       setTitle]       = useState('');
    const [description, setDescription] = useState('');
    const [showDesc,    setShowDesc]    = useState(false);
    const [priority,    setPriority]    = useState('normal');
    const [dueDate,     setDueDate]     = useState('');
    const [assigneeId,  setAssigneeId]  = useState<number | undefined>();
    const [users,       setUsers]       = useState<any[]>([]);
    const [loading,     setLoading]     = useState(false);
    const [showFields,  setShowFields]  = useState(false);

    useEffect(() => {
        if (!token) return;
        apiFetch<any[]>('/auth/user-list?limit=50', { token })
            .then(d => setUsers(d || []))
            .catch(console.error);
    }, [token]);

    const handleSubmit = async (e?: React.FormEvent) => {
        if (e) e.preventDefault();
        if (!title.trim()) return;
        setLoading(true);
        try {
            await onSubmit({ title, description, priority, status: defaultStatus, due_date: dueDate || undefined, assignee_id: assigneeId });
            onClose();
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            <div className="px-6 pt-4 pb-2 space-y-3">
                {/* Breadcrumb: Proyecto > Tipo */}
                <div className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-400">
                    <span className="px-2 py-0.5 bg-slate-100 dark:bg-white/8 rounded-md hover:bg-slate-200 cursor-pointer transition-colors">
                        General
                    </span>
                    <ChevronDown size={12} className="-rotate-90 text-slate-300" />
                    <span className="px-2 py-0.5 bg-slate-100 dark:bg-white/8 rounded-md hover:bg-slate-200 cursor-pointer transition-colors">
                        Tarea
                    </span>
                    <ChevronDown size={12} className="text-slate-300" />
                </div>

                {/* Title input */}
                <input
                    autoFocus
                    value={title}
                    onChange={e => setTitle(e.target.value)}
                    onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) handleSubmit(); }}
                    placeholder="Escribe el nombre de Tarea o pulsa «/» para ver comandos"
                    className="w-full bg-transparent text-[20px] font-semibold outline-none placeholder:text-slate-300 dark:placeholder:text-white/20 text-slate-800 dark:text-white leading-snug"
                />

                {/* Description / AI toggle */}
                {!showDesc ? (
                    <div className="flex items-center gap-4">
                        <button
                            onClick={() => setShowDesc(true)}
                            className="flex items-center gap-1.5 text-[12px] text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
                        >
                            <AlignLeft size={13} /> Añadir descripción
                        </button>
                        <button className="flex items-center gap-1.5 text-[12px] font-semibold text-purple-500 hover:text-purple-700 transition-colors">
                            <Wand2 size={13} /> Escribir con IA
                        </button>
                    </div>
                ) : (
                    <textarea
                        autoFocus
                        value={description}
                        onChange={e => setDescription(e.target.value)}
                        placeholder="Descripción..."
                        rows={3}
                        className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/8 rounded-xl px-4 py-3 text-[13px] outline-none focus:ring-2 focus:ring-blue-500/20 text-slate-700 dark:text-slate-200 resize-none"
                    />
                )}

                {/* Metadata pills row */}
                <div className="flex flex-wrap items-center gap-1.5 pt-1">
                    {/* Status */}
                    <span className="px-3 py-1.5 border border-slate-200 dark:border-white/10 rounded-full text-[10px] font-black uppercase tracking-wider text-slate-600 dark:text-slate-300 bg-slate-50 dark:bg-white/5">
                        {defaultStatus || 'PENDIENTE'}
                    </span>

                    {/* Assignee */}
                    <div className="relative">
                        <select
                            value={assigneeId ?? ''}
                            onChange={e => setAssigneeId(e.target.value ? Number(e.target.value) : undefined)}
                            className="appearance-none pl-7 pr-3 py-1.5 border border-slate-200 dark:border-white/10 rounded-full text-[11px] font-semibold text-slate-500 bg-white dark:bg-transparent hover:bg-slate-50 dark:hover:bg-white/5 transition-colors cursor-pointer outline-none"
                        >
                            <option value="">Persona asignada</option>
                            {users.map(u => <option key={u.id} value={u.id}>{u.username}</option>)}
                        </select>
                        <User size={11} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
                    </div>

                    {/* Due date */}
                    <div className="relative">
                        <input
                            type="date"
                            value={dueDate}
                            onChange={e => setDueDate(e.target.value)}
                            className="pl-7 pr-3 py-1.5 border border-slate-200 dark:border-white/10 rounded-full text-[11px] font-semibold text-slate-500 bg-white dark:bg-transparent hover:bg-slate-50 dark:hover:bg-white/5 cursor-pointer outline-none min-w-[130px] appearance-none"
                        />
                        <Calendar size={11} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
                    </div>

                    {/* Priority */}
                    <div className="relative">
                        <select
                            value={priority}
                            onChange={e => setPriority(e.target.value)}
                            className="appearance-none pl-7 pr-3 py-1.5 border border-slate-200 dark:border-white/10 rounded-full text-[11px] font-semibold text-slate-500 bg-white dark:bg-transparent hover:bg-slate-50 dark:hover:bg-white/5 transition-colors cursor-pointer outline-none"
                        >
                            <option value="normal">Prioridad</option>
                            <option value="urgent">Urgente</option>
                            <option value="high">Alta</option>
                            <option value="low">Baja</option>
                        </select>
                        <Flag size={11} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
                    </div>

                    {/* Tags */}
                    <button className="flex items-center gap-1.5 pl-2.5 pr-3 py-1.5 border border-slate-200 dark:border-white/10 rounded-full text-[11px] font-semibold text-slate-500 hover:bg-slate-50 dark:hover:bg-white/5 transition-colors">
                        <Tag size={11} /> Etiquetas
                    </button>

                    {/* More */}
                    <button className="flex items-center gap-1 pl-2 pr-3 py-1.5 border border-slate-200 dark:border-white/10 rounded-full text-[11px] font-semibold text-slate-400 hover:bg-slate-50 dark:hover:bg-white/5 transition-colors">
                        <span className="text-base leading-none">···</span>
                    </button>
                </div>

                {/* Campos section */}
                <div className="pt-2">
                    <p className="text-[11px] font-black text-slate-400 uppercase tracking-widest mb-2">Campos</p>
                    <button
                        onClick={() => setShowFields(!showFields)}
                        className="flex items-center gap-1.5 text-[12px] font-semibold text-slate-400 hover:text-blue-600 transition-colors"
                    >
                        <Plus size={13} /> Crear un campo
                    </button>
                </div>
            </div>

            {/* Footer */}
            <footer className="px-6 py-3.5 border-t border-slate-100 dark:border-white/5 flex items-center justify-between bg-slate-50/50 dark:bg-black/10">
                <button className="flex items-center gap-1.5 px-3 py-1.5 border border-slate-200 dark:border-white/10 rounded-lg text-[11px] font-semibold text-slate-500 hover:bg-white dark:hover:bg-white/5 transition-colors">
                    <Wand2 size={13} /> Plantillas
                </button>
                <div className="flex items-center gap-2">
                    <button className="p-2 text-slate-400 hover:text-blue-600 transition-colors" title="Adjuntar archivo">
                        <Paperclip size={16} />
                    </button>
                    <button className="p-2 text-slate-400 hover:text-blue-600 transition-colors" title="Notificaciones">
                        <Bell size={16} />
                    </button>
                    {/* Split button */}
                    <div className="flex rounded-xl overflow-hidden shadow-md ml-1">
                        <button
                            disabled={!title.trim() || loading}
                            onClick={() => handleSubmit()}
                            className="bg-slate-900 dark:bg-white font-bold text-white dark:text-slate-900 px-5 py-2 text-[11px] uppercase tracking-widest flex items-center gap-2 disabled:opacity-40 hover:bg-slate-800 dark:hover:bg-slate-100 transition-colors"
                        >
                            {loading ? <Loader2 size={13} className="animate-spin" /> : 'Crear Tarea'}
                        </button>
                        <button className="bg-slate-900 dark:bg-white border-l border-white/10 dark:border-slate-200 px-2.5 text-white dark:text-slate-900 hover:bg-slate-700 dark:hover:bg-slate-100 transition-colors">
                            <ChevronDown size={13} />
                        </button>
                    </div>
                </div>
            </footer>
        </motion.div>
    );
}

// ─────────────────────────────────────────────────────────────────────────────
// Document Form — matches documento.png
// ─────────────────────────────────────────────────────────────────────────────
function DocumentForm({ onClose, addToast }: { onClose: () => void; addToast: any }) {
    const [title, setTitle] = useState('');
    const handleCreate = () => { addToast('Documento creado', 'success'); onClose(); };

    return (
        <SlideForm>
            <ContextDropdown label="Mis documentos" />
            <BigInput value={title} onChange={setTitle} placeholder="Ponle un nombre a este documento..." />
            <div className="flex flex-col gap-2 mt-1">
                <TextLink icon={AlignLeft} label="Empezar a escribir" />
                <TextLink icon={Wand2} label="Escribir con IA" accent />
            </div>
            <SlideFooter>
                <PrivateToggle />
                <SubmitBtn disabled={!title.trim()} onClick={handleCreate} label="Crear documento" />
            </SlideFooter>
        </SlideForm>
    );
}

// ─────────────────────────────────────────────────────────────────────────────
// Reminder Form — matches recordatorio.png
// ─────────────────────────────────────────────────────────────────────────────
function ReminderForm({ onClose, addToast }: { onClose: () => void; addToast: any }) {
    const [title, setTitle] = useState('');
    const handleCreate = () => { addToast('Recordatorio configurado', 'success'); onClose(); };

    return (
        <SlideForm>
            <BigInput
                value={title}
                onChange={setTitle}
                placeholder="Escribe el nombre del recordatorio o pulsa «/» para ver comandos"
            />
            <div className="flex items-center gap-2 mt-3 flex-wrap">
                <QuickChip label="Hoy" active />
                <QuickChip label="Para mí" active />
                <QuickChip label="Notificarme" />
            </div>
            <SlideFooter>
                <button className="p-2 text-slate-400 hover:text-blue-600 transition-colors">
                    <Paperclip size={16} />
                </button>
                <SubmitBtn disabled={!title.trim()} onClick={handleCreate} label="Crear recordatorio" />
            </SlideFooter>
        </SlideForm>
    );
}

// ─────────────────────────────────────────────────────────────────────────────
// Whiteboard Form — matches pizarra.png
// ─────────────────────────────────────────────────────────────────────────────
function WhiteboardForm({ onClose, addToast }: { onClose: () => void; addToast: any }) {
    const [title, setTitle] = useState('');
    const handleCreate = () => { addToast('Pizarra iniciada', 'success'); onClose(); };

    return (
        <SlideForm>
            <ContextDropdown label="Mis pizarras" />
            <BigInput value={title} onChange={setTitle} placeholder="Ponle un nombre a esta pizarra..." />
            <SlideFooter>
                <PrivateToggle />
                <SubmitBtn disabled={!title.trim()} onClick={handleCreate} label="Crear pizarra" />
            </SlideFooter>
        </SlideForm>
    );
}

// ─────────────────────────────────────────────────────────────────────────────
// Panel Form — matches Panel.png
// ─────────────────────────────────────────────────────────────────────────────
function PanelForm({ onClose, addToast }: { onClose: () => void; addToast: any }) {
    const [title, setTitle] = useState('');
    const handleCreate = () => { addToast('Panel creado', 'success'); onClose(); };

    return (
        <SlideForm>
            <ContextDropdown label="Mis paneles" />
            <BigInput value={title} onChange={setTitle} placeholder="Ponle un nombre a este panel..." />
            <SlideFooter>
                <PrivateToggle />
                <SubmitBtn disabled={!title.trim()} onClick={handleCreate} label="Crear panel" />
            </SlideFooter>
        </SlideForm>
    );
}

// ─────────────────────────────────────────────────────────────────────────────
// Primitives shared across forms
// ─────────────────────────────────────────────────────────────────────────────
function SlideForm({ children }: { children: React.ReactNode }) {
    return (
        <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className="flex flex-col px-6 py-5 gap-3 min-h-[280px]">
            {children}
        </motion.div>
    );
}

function SlideFooter({ children }: { children: React.ReactNode }) {
    return (
        <div className="mt-auto pt-4 border-t border-slate-100 dark:border-white/5 flex items-center justify-between">
            {children}
        </div>
    );
}

function ContextDropdown({ label }: { label: string }) {
    return (
        <button className="flex items-center gap-1.5 w-fit px-3 py-1.5 bg-slate-100 dark:bg-white/8 rounded-lg text-[11px] font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-white/12 transition-colors">
            <span className="text-base leading-none mr-0.5">≡</span>
            {label}
            <ChevronDown size={12} />
        </button>
    );
}

function BigInput({ value, onChange, placeholder }: { value: string; onChange: (v: string) => void; placeholder: string }) {
    return (
        <input
            autoFocus
            value={value}
            onChange={e => onChange(e.target.value)}
            placeholder={placeholder}
            className="w-full bg-transparent text-[18px] font-semibold outline-none placeholder:text-slate-300 dark:placeholder:text-white/20 text-slate-800 dark:text-white leading-snug"
        />
    );
}

function TextLink({ icon: Icon, label, accent }: { icon: any; label: string; accent?: boolean }) {
    return (
        <button className={clsx(
            'flex items-center gap-1.5 text-[12px] font-medium transition-colors w-fit',
            accent ? 'text-purple-500 hover:text-purple-700' : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-300'
        )}>
            <Icon size={13} /> {label}
        </button>
    );
}

function QuickChip({ label, active }: { label: string; active?: boolean }) {
    return (
        <button className={clsx(
            'px-3 py-1.5 rounded-full text-[11px] font-semibold border transition-all',
            active
                ? 'bg-slate-900 dark:bg-white text-white dark:text-slate-900 border-slate-900 dark:border-white'
                : 'border-slate-200 dark:border-white/10 text-slate-500 hover:bg-slate-50 dark:hover:bg-white/5'
        )}>
            {label}
        </button>
    );
}

function SubmitBtn({ disabled, onClick, label }: { disabled: boolean; onClick: () => void; label: string }) {
    return (
        <button
            disabled={disabled}
            onClick={onClick}
            className="bg-slate-900 dark:bg-white font-bold text-white dark:text-slate-900 px-5 py-2 rounded-xl text-[11px] uppercase tracking-widest hover:opacity-90 disabled:opacity-40 transition-all active:scale-95 shadow-md"
        >
            {label}
        </button>
    );
}

function PrivateToggle() {
    const [on, setOn] = useState(false);
    return (
        <label className="flex items-center gap-2 cursor-pointer select-none">
            <button
                type="button"
                onClick={() => setOn(!on)}
                className={clsx(
                    'relative w-8 h-4 rounded-full transition-colors duration-200',
                    on ? 'bg-slate-900 dark:bg-white' : 'bg-slate-200 dark:bg-white/20'
                )}
            >
                <span className={clsx(
                    'absolute top-0.5 left-0.5 size-3 bg-white dark:bg-slate-900 rounded-full shadow transition-transform duration-200',
                    on ? 'translate-x-4' : 'translate-x-0'
                )} />
            </button>
            <span className="text-[12px] font-medium text-slate-500">Privado</span>
        </label>
    );
}
