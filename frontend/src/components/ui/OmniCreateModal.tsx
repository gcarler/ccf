"use client";

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, CheckSquare, Type, AlignLeft, Flag, Loader2, Link2, Bell, FileText, LayoutDashboard, Layout, ChevronDown, Wand2, Paperclip, MoreHorizontal, User } from 'lucide-react';
import * as Dialog from '@radix-ui/react-dialog';
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
    onTaskSubmit: (data: { title: string; description: string; priority: string; status: string; due_date?: string; assignee_id?: number }) => Promise<void>;
}

export default function OmniCreateModal({ isOpen, initialTab = 'task', defaultStatus = 'PENDIENTE', onClose, onTaskSubmit }: Props) {
    const [activeTab, setActiveTab] = useState<OmniTab>(initialTab);
    const { addToast } = useToast();

    useEffect(() => {
        if (isOpen) {
            setActiveTab(initialTab);
        }
    }, [isOpen, initialTab]);

    const TABS = [
        { id: 'task', label: 'Tarea' },
        { id: 'document', label: 'Documento' },
        { id: 'reminder', label: 'Recordatorio' },
        { id: 'whiteboard', label: 'Pizarra' },
        { id: 'panel', label: 'Panel' },
    ];

    return (
        <Dialog.Root open={isOpen} onOpenChange={(open) => !open && onClose()}>
            <AnimatePresence>
                {isOpen && (
                    <Dialog.Portal forceMount>
                        <Dialog.Overlay asChild>
                            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-[9000] bg-slate-900/40 backdrop-blur-sm" />
                        </Dialog.Overlay>
                        <Dialog.Content asChild>
                            <motion.div 
                                initial={{ opacity: 0, scale: 0.95, y: 30 }} 
                                animate={{ opacity: 1, scale: 1, y: 0 }} 
                                exit={{ opacity: 0, scale: 0.95, y: 20 }}
                                transition={{ type: "spring", stiffness: 300, damping: 25 }}
                                className="fixed left-1/2 top-24 z-[9001] w-full max-w-[700px] -translate-x-1/2 rounded-[min(1.5rem,24px)] bg-white dark:bg-[#1e1f21] shadow-2xl border border-slate-200 dark:border-white/10 overflow-hidden flex flex-col min-h-[450px]"
                            >
                                {/* Header / Tabs */}
                                <div className="h-14 flex flex-col justify-end border-b border-slate-100 dark:border-white/5 relative bg-slate-50 dark:bg-black/20 shrink-0">
                                    <button onClick={onClose} className="absolute right-4 top-4 p-1.5 hover:bg-slate-200 dark:hover:bg-white/10 rounded-full transition-colors text-slate-400">
                                        <X size={16} />
                                    </button>

                                    <div className="flex px-6 gap-6 relative">
                                        {TABS.map((tab) => {
                                            const isActive = activeTab === tab.id;
                                            return (
                                                <button
                                                    key={tab.id}
                                                    onClick={() => setActiveTab(tab.id as OmniTab)}
                                                    className={clsx(
                                                        "pb-3 text-[13px] font-bold transition-all relative",
                                                        isActive ? "text-slate-900 dark:text-white" : "text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
                                                    )}
                                                >
                                                    {tab.label}
                                                    {isActive && (
                                                        <motion.div layoutId="omni-tab-indicator" className="absolute bottom-0 left-0 right-0 h-0.5 bg-slate-900 dark:bg-white" />
                                                    )}
                                                </button>
                                            )
                                        })}
                                    </div>
                                </div>

                                {/* Content Area */}
                                <div className="flex-1 overflow-y-auto p-6 bg-white dark:bg-[#1e1f21] relative">
                                    <AnimatePresence mode="wait">
                                        {activeTab === 'task' && <TaskForm key="task" defaultStatus={defaultStatus} onSubmit={onTaskSubmit} onClose={onClose} />}
                                        {activeTab === 'document' && <DocumentForm key="document" onClose={onClose} addToast={addToast} />}
                                        {activeTab === 'reminder' && <ReminderForm key="reminder" onClose={onClose} addToast={addToast} />}
                                        {activeTab === 'whiteboard' && <WhiteboardForm key="whiteboard" onClose={onClose} addToast={addToast} />}
                                        {activeTab === 'panel' && <PanelForm key="panel" onClose={onClose} addToast={addToast} />}
                                    </AnimatePresence>
                                </div>
                            </motion.div>
                        </Dialog.Content>
                    </Dialog.Portal>
                )}
            </AnimatePresence>
        </Dialog.Root>
    );
}

// ------------------------------------------------------------------------------------------------------------------
// Sub-Forms
// ------------------------------------------------------------------------------------------------------------------

function TaskForm({ defaultStatus, onSubmit, onClose }: any) {
    const { token } = useAuth();
    const [title, setTitle] = useState('');
    const [description, setDescription] = useState('');
    const [showDesc, setShowDesc] = useState(false);
    const [priority, setPriority] = useState('normal');
    const [dueDate, setDueDate] = useState('');
    const [assigneeId, setAssigneeId] = useState<number | undefined>();
    const [users, setUsers] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (!token) return;
        apiFetch<any[]>(`/auth/user-list?limit=50`, { token })
            .then(data => setUsers(data || []))
            .catch(console.error);
    }, [token]);

    const handleSubmit = async (e?: React.FormEvent) => {
        if(e) e.preventDefault();
        if (!title.trim()) return;
        setLoading(true);
        try {
            await onSubmit({ 
                title, 
                description, 
                priority, 
                status: defaultStatus,
                due_date: dueDate || undefined,
                assignee_id: assigneeId
            });
            onClose();
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, scale: 0.98 }} className="h-full flex flex-col">
            <div className="flex items-center gap-3 mb-6">
                <div className="flex items-center gap-1.5 px-2 py-1 bg-slate-100 dark:bg-white/5 rounded text-[11px] font-bold text-slate-500 cursor-pointer hover:bg-slate-200 dark:hover:bg-white/10 transition-colors">
                    <CheckSquare size={12} />
                    <span>General</span>
                    <ChevronDown size={10} className="ml-1" />
                </div>
                <div className="flex items-center gap-1.5 px-2 py-1 bg-slate-100 dark:bg-white/5 rounded text-[11px] font-bold text-slate-500 cursor-pointer hover:bg-slate-200 dark:hover:bg-white/10 transition-colors">
                    <CheckSquare size={12} />
                    <span>Tarea</span>
                    <ChevronDown size={10} className="ml-1" />
                </div>
            </div>

            <input 
                autoFocus
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') handleSubmit(); }}
                placeholder="Escribe el nombre de Tarea o pulsa «/» para ver comandos"
                className="w-full bg-transparent text-[22px] font-black outline-none placeholder:text-slate-300 dark:placeholder:text-white/20 text-slate-900 dark:text-white mb-6"
            />

            <div className="flex flex-col gap-3">
                {!showDesc ? (
                    <button onClick={() => setShowDesc(true)} className="flex items-center gap-2 text-[12px] text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 font-bold transition-colors w-fit">
                        <AlignLeft size={16} /> Añadir descripción
                    </button>
                ) : (
                    <textarea 
                        autoFocus
                        value={description}
                        onChange={(e) => setDescription(e.target.value)}
                        placeholder="Descripción de la tarea..."
                        className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/5 rounded-xl px-4 py-3 text-[13px] outline-none focus:ring-2 focus:ring-blue-500/20 text-slate-900 dark:text-white min-h-[80px] resize-none"
                    />
                )}
                
                {!showDesc && (
                    <button className="flex items-center gap-2 text-[12px] font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-500 to-purple-500 hover:opacity-80 transition-opacity w-fit">
                        <Wand2 size={16} className="text-blue-500" /> Escribir con IA
                    </button>
                )}
            </div>

            <div className="flex flex-wrap items-center gap-2 mt-8">
                <div className="px-2 py-1 bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-md text-[10px] font-black uppercase tracking-widest text-slate-500">{defaultStatus}</div>
                
                <div className="relative group/select">
                    <select 
                        value={assigneeId || ''} 
                        onChange={(e) => setAssigneeId(e.target.value ? Number(e.target.value) : undefined)}
                        className="appearance-none flex items-center gap-1.5 pl-8 pr-4 py-1.5 border border-slate-200 dark:border-white/10 rounded-md text-[11px] font-bold text-slate-500 bg-transparent hover:bg-slate-50 dark:hover:bg-white/5 transition-colors cursor-pointer outline-none"
                    >
                        <option value="">Sin asignar</option>
                        {users.map(u => (
                            <option key={u.id} value={u.id}>{u.username}</option>
                        ))}
                    </select>
                    <User size={12} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" />
                </div>

                <div className="relative group/select">
                    <input 
                        type="date" 
                        value={dueDate}
                        onChange={(e) => setDueDate(e.target.value)}
                        className="appearance-none flex flex-row-reverse items-center justify-between gap-2 px-3 py-1.5 border border-slate-200 dark:border-white/10 rounded-md text-[11px] font-bold text-slate-500 bg-transparent hover:bg-slate-50 dark:hover:bg-white/5 transition-colors cursor-pointer outline-none min-w-[130px]"
                    />
                </div>

                <div className="relative group/select">
                    <select 
                        value={priority}
                        onChange={(e) => setPriority(e.target.value)}
                        className="appearance-none flex items-center gap-1.5 pl-8 pr-4 py-1.5 border border-slate-200 dark:border-white/10 rounded-md text-[11px] font-bold text-slate-500 bg-transparent hover:bg-slate-50 dark:hover:bg-white/5 transition-colors cursor-pointer outline-none"
                    >
                        <option value="normal">Prioridad Normal</option>
                        <option value="high">Prioridad Alta</option>
                        <option value="urgent">Urgente</option>
                        <option value="low">Prioridad Baja</option>
                    </select>
                    <Flag size={12} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" />
                </div>
            </div>

            <div className="mt-auto px-1 py-4 border-t border-slate-100 dark:border-white/5 flex items-center justify-between">
                <button className="flex items-center gap-2 px-3 py-1.5 border border-slate-200 dark:border-white/10 rounded-lg text-[12px] font-bold text-slate-500 hover:bg-slate-50 dark:hover:bg-white/5 transition-colors shadow-sm">
                    <Wand2 size={14} /> Plantillas
                </button>

                <div className="flex items-center gap-3">
                    <button className="p-1.5 text-slate-400 hover:bg-slate-50 dark:hover:bg-white/5 rounded text-[11px]"><Paperclip size={16} /></button>
                    <button className="p-1.5 text-slate-400 hover:bg-slate-50 dark:hover:bg-white/5 rounded text-[11px]"><Bell size={16} /></button>
                    
                    <div className="flex rounded-lg overflow-hidden shadow-[0_4px_14px_0_rgba(15,23,42,0.15)] ml-2">
                        <button 
                            disabled={!title.trim() || loading}
                            onClick={() => handleSubmit()}
                            className="bg-[#1e272e] font-bold text-white px-5 py-2 text-[12px] flex items-center justify-center gap-2 disabled:opacity-50 hover:bg-[#2f3640] transition-colors"
                        >
                            {loading ? <Loader2 size={14} className="animate-spin" /> : 'Crear Tarea'}
                        </button>
                        <button className="bg-[#1e272e] border-l border-white/10 px-2 py-2 text-white hover:bg-[#2f3640] transition-colors">
                            <ChevronDown size={14} />
                        </button>
                    </div>
                </div>
            </div>
        </motion.div>
    );
}


function DocumentForm({ onClose, addToast }: { onClose: () => void, addToast: any }) {
    const [title, setTitle] = useState('');

    const handleCreate = () => {
        addToast("Documento de Wiki creado (Simulación)", "success");
        onClose();
    };

    return (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, scale: 0.98 }} className="h-full flex flex-col">
            <div className="flex items-center gap-3 mb-6">
                <div className="flex items-center gap-1.5 px-2 py-1 bg-slate-100 dark:bg-white/5 rounded text-[11px] font-bold text-slate-500 cursor-pointer hover:bg-slate-200 dark:hover:bg-white/10 transition-colors">
                    <FileText size={12} /> Mis documentos <ChevronDown size={10} />
                </div>
            </div>

            <input 
                autoFocus
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Ponle un nombre a este documento..."
                className="w-full bg-transparent text-[22px] font-black outline-none placeholder:text-slate-300 dark:placeholder:text-white/20 text-slate-900 dark:text-white mb-6"
            />
            
            <div className="flex flex-col gap-3">
                <button className="flex items-center gap-2 text-[12px] text-slate-400 font-bold w-fit"><AlignLeft size={16} /> Empezar a escribir</button>
                <button className="flex items-center gap-2 text-[12px] font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-500 to-purple-500 w-fit"><Wand2 size={16} className="text-blue-500" /> Escribir con IA</button>
            </div>

            <div className="mt-8">
                <span className="text-[10px] font-bold text-slate-400 tracking-wider">Añadir a...</span>
                <div className="flex flex-col gap-2 mt-3">
                    <button className="flex items-center gap-2 text-[12px] font-bold text-slate-500"><Layout size={14} /> Tabla</button>
                    <button className="flex items-center gap-2 text-[12px] font-bold text-slate-500"><LayoutDashboard size={14} /> Columna</button>
                </div>
            </div>

            <div className="mt-auto px-1 py-4 border-t border-slate-100 dark:border-white/5 flex items-center justify-between">
                <label className="flex items-center gap-2 cursor-pointer">
                    <div className="relative inline-flex items-center">
                        <input type="checkbox" className="sr-only peer" />
                        <div className="w-8 h-4 bg-slate-200 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-3 after:w-3 after:transition-all dark:bg-slate-700 peer-checked:bg-slate-800"></div>
                    </div>
                    <span className="text-[12px] font-bold text-slate-500">Privado</span>
                </label>
                <button 
                    disabled={!title.trim()}
                    onClick={handleCreate}
                    className="bg-[#1e272e] font-bold text-white px-5 py-2 rounded-lg text-[12px] hover:bg-[#2f3640] transition-colors disabled:opacity-50"
                >
                    Crear documento
                </button>
            </div>
        </motion.div>
    );
}


function ReminderForm({ onClose, addToast }: { onClose: () => void, addToast: any }) {
    const [title, setTitle] = useState('');
    const handleCreate = () => { addToast("Recordatorio configurado", "success"); onClose(); };

    return (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, scale: 0.98 }} className="h-full flex flex-col">
            <input 
                autoFocus
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Acuérdate de..."
                className="w-full mt-4 bg-transparent text-[22px] font-black outline-none placeholder:text-slate-300 dark:placeholder:text-white/20 text-slate-900 dark:text-white mb-6"
            />
            <div className="flex items-center gap-2 mt-8">
                <button className="flex items-center gap-1.5 px-3 py-1.5 border border-slate-200 dark:border-white/10 rounded-md text-[11px] font-bold text-slate-500 hover:bg-slate-50 transition-colors">
                    <Bell size={12} /> Hoy
                </button>
                <button className="flex items-center gap-1.5 px-3 py-1.5 border border-slate-200 dark:border-white/10 rounded-md text-[11px] font-bold text-slate-500 hover:bg-slate-50 transition-colors">
                    <Link2 size={12} /> Adjuntar a
                </button>
            </div>
            <div className="mt-auto px-1 py-4 border-t border-slate-100 dark:border-white/5 flex justify-end">
                <button disabled={!title.trim()} onClick={handleCreate} className="bg-[#1e272e] font-bold text-white px-5 py-2 rounded-lg text-[12px] hover:bg-[#2f3640] transition-colors disabled:opacity-50">
                    Crear Recordatorio
                </button>
            </div>
        </motion.div>
    );
}

function WhiteboardForm({ onClose, addToast }: { onClose: () => void, addToast: any }) {
    const [title, setTitle] = useState('');
    const handleCreate = () => { addToast("Pizarra iniciada", "success"); onClose(); };

    return (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, scale: 0.98 }} className="h-full flex flex-col">
            <div className="flex items-center gap-3 mb-6 animate-pulse p-4 rounded-xl bg-slate-50 dark:bg-white/5 text-slate-400 text-sm font-bold justify-center border border-dashed border-slate-200 dark:border-white/10">
                <LayoutDashboard size={18} /> Previsualización de Lienzo en Blanco
            </div>
            <input 
                autoFocus
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Nombre para la pizarra infinita..."
                className="w-full mt-2 bg-transparent text-[22px] font-black outline-none placeholder:text-slate-300 dark:placeholder:text-white/20 text-slate-900 dark:text-white mb-6"
            />
            <div className="mt-auto px-1 py-4 border-t border-slate-100 dark:border-white/5 flex justify-end">
                <button disabled={!title.trim()} onClick={handleCreate} className="bg-[#1e272e] font-bold text-white px-5 py-2 rounded-lg text-[12px] hover:bg-[#2f3640] transition-colors disabled:opacity-50">
                    Lanzar Pizarra
                </button>
            </div>
        </motion.div>
    );
}

function PanelForm({ onClose, addToast }: { onClose: () => void, addToast: any }) {
    const [title, setTitle] = useState('');
    const handleCreate = () => { addToast("Dashboard Creado", "success"); onClose(); };

    return (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, scale: 0.98 }} className="h-full flex flex-col">
             <div className="flex items-center gap-3 mb-6">
                <div className="flex items-center gap-1.5 px-2 py-1 bg-slate-100 dark:bg-white/5 rounded text-[11px] font-bold text-slate-500 cursor-pointer">
                    <Layout size={12} /> Mis paneles <ChevronDown size={10} />
                </div>
            </div>
            <input 
                autoFocus
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Ponle un nombre a este panel..."
                className="w-full bg-transparent text-[22px] font-black outline-none placeholder:text-slate-300 dark:placeholder:text-white/20 text-slate-900 dark:text-white mb-6"
            />
            <div className="mt-auto px-1 py-4 flex items-center justify-between border-t border-slate-100 dark:border-white/5">
                <label className="flex items-center gap-2 cursor-pointer">
                    <div className="relative inline-flex items-center">
                        <input type="checkbox" className="sr-only peer" />
                        <div className="w-8 h-4 bg-slate-200 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-3 after:w-3 after:transition-all dark:bg-slate-700 peer-checked:bg-slate-800"></div>
                    </div>
                    <span className="text-[12px] font-bold text-slate-500">Privado</span>
                </label>
                <button disabled={!title.trim()} onClick={handleCreate} className="bg-[#1e272e] font-bold text-white px-5 py-2 rounded-lg text-[12px] hover:bg-[#2f3640] transition-colors disabled:opacity-50">
                    Crear panel
                </button>
            </div>
        </motion.div>
    );
}
