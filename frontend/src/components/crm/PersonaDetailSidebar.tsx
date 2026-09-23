"use client";

import React, { useState, useEffect, useCallback } from 'react';
import {
    X as CloseIcon,
    Printer,
    PencilLine,
    Check,
    Zap,
    ShieldCheck,
    History,
    ListTodo,
    DollarSign,
    Mail,
    Award,
    Clock,
    Plus,
    Loader2,
    ChevronRight,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { useRouter } from 'next/navigation';
import clsx from 'clsx';

interface PersonaDetailSidebarProps {
    persona: any;
    onUpdate?: () => void;
    onClose?: () => void;
}

export default function PersonaDetailSidebar({ persona: initialPersona, onUpdate, onClose }: PersonaDetailSidebarProps) {
    const { token } = useAuth();
    const { addToast } = useToast();
    const router = useRouter();

    const [selectedPersona, setSelectedPersona] = useState(initialPersona);
    const [editedPersona, setEditedPersona] = useState(initialPersona);
    const [editMode, setEditMode] = useState(false);
    const [modalTab, setModalTab] = useState<'timeline' | 'profile' | 'messages' | 'finance' | 'tasks'>('timeline');

    // Sub-data states
    const [history, setHistory] = useState<any[]>([]);
    const [donations, setDonations] = useState<any[]>([]);
    const [tasks, setTasks] = useState<any[]>([]);

    const [loadingHistory, setLoadingHistory] = useState(false);
    const [loadingFinance, setLoadingFinance] = useState(false);
    const [loadingTasks, setLoadingTasks] = useState(false);

    // Messaging State
    const [newMessageContent, setNewMessageContent] = useState('');
    const [messageChannel, setMessageChannel] = useState('whatsapp');

    const fetchTimeline = useCallback(async (id: string) => {
        setLoadingHistory(true);
        try {
            const data = await apiFetch(`/crm/personas/${id}/timeline`, { token, cache: 'no-store' });
            setHistory(Array.isArray(data) ? data : []);
        } catch (err) {
            setHistory([]);
        } finally {
            setLoadingHistory(false);
        }
    }, [token]);

    const fetchFinance = useCallback(async (id: string) => {
        setLoadingFinance(true);
        try {
            const data = await apiFetch<any[]>(`/crm/personas/${id}/donations`, { token });
            setDonations(Array.isArray(data) ? data : []);
        } catch (e) {
            setDonations([]);
        } finally {
            setLoadingFinance(false);
        }
    }, [token]);

    const fetchTasks = useCallback(async (id: string) => {
        setLoadingTasks(true);
        try {
            const data = await apiFetch<any[]>(`/crm/tasks?assignee_id=${id}`, { token });
            setTasks(Array.isArray(data) ? data : []);
        } catch (e) {
            setTasks([]);
        } finally {
            setLoadingTasks(false);
        }
    }, [token]);

    const loadPersonaData = useCallback(async (personaId: string) => {
        if (!token) return;
        fetchTimeline(personaId);
        fetchFinance(personaId);
        fetchTasks(personaId);
    }, [token, fetchTimeline, fetchFinance, fetchTasks]);

    useEffect(() => {
        if (!initialPersona?.id) return;
        loadPersonaData(initialPersona.id);
    }, [initialPersona?.id, loadPersonaData]);

    const handleUpdatePersona = async () => {
        if (!token) return;
        try {
            await apiFetch(`/crm/personas/${selectedPersona.id}`, {
                method: 'PATCH',
                token,
                body: editedPersona
            });
            addToast("Ficha actualizada", "success");
            setEditMode(false);
            setSelectedPersona({ ...selectedPersona, ...editedPersona });
            if (onUpdate) onUpdate();
        } catch (err) {
            addToast("Error al actualizar", "error");
        }
    };

    const handleUpdateTaskStatus = async (taskId: number, newStatus: string) => {
        try {
            await apiFetch(`/crm/tasks/${taskId}`, {
                method: 'PATCH',
                token,
                body: { status: newStatus }
            });
            addToast("Estado de tarea actualizado", "success");
            fetchTasks(selectedPersona.id);
        } catch (err) {
            addToast("Error al actualizar tarea", "error");
        }
    };

    const handleSendMessage = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!newMessageContent || !token) return;

        try {
            await apiFetch('/messaging/send', {
                method: 'POST',
                token,
                body: {
                    persona_id: selectedPersona.id,
                    channel: messageChannel,
                    content: newMessageContent
                }
            });

            addToast("Mensaje enviado exitosamente", "success");
            setNewMessageContent('');
            fetchTimeline(selectedPersona.id);
        } catch (err) {
            addToast("Error al enviar mensaje", "error");
        }
    };

    const handlePrint = () => window.print();

    return (
        <div className="flex flex-col h-full bg-[hsl(var(--surface-1))]">
            {/* Sidebar Header Cinematic */}
            <div className="p-4 border-b border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] backdrop-blur-3xl shrink-0 relative overflow-hidden rounded-t-lg">
                <div className="absolute top-0 right-0 p-4 opacity-[0.03] pointer-events-none text-[hsl(var(--primary))]">
                    <ShieldCheck size={160} />
                </div>

                {/* Top Bar Actions */}
                <div className="flex justify-between items-start mb-3 relative z-10">
                    <button
                        onClick={onClose}
                        className="p-2.5 bg-[hsl(var(--surface-2))] hover:bg-[hsl(var(--surface-3))] rounded-lg text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] transition-all shadow-sm border border-[hsl(var(--border))] active:scale-95"
                        aria-label="Cerrar"
                    >
                        <CloseIcon size={20} />
                    </button>
                    <div className="flex gap-2.5">
                        <button onClick={handlePrint} className="px-3 py-2.5 bg-[hsl(var(--surface-2))] text-[hsl(var(--primary))] rounded-lg text-2xs font-bold uppercase tracking-wider border border-[hsl(var(--border))] flex items-center gap-2 shadow-sm hover:bg-[hsl(var(--primary)/0.1)] transition-all active:scale-95">
                            <Printer size={14} /> PDF
                        </button>
                        <button
                            onClick={() => editMode ? handleUpdatePersona() : setEditMode(true)}
                            className={clsx(
                                "px-3 py-2.5 rounded-lg text-2xs font-bold uppercase tracking-wider flex items-center gap-2 transition-all active:scale-95 shadow-lg",
                                editMode
                                    ? "bg-[hsl(var(--success))] text-[hsl(var(--primary-foreground))] shadow-[hsl(var(--success)/0.2)]"
                                    : "bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] shadow-[hsl(var(--primary)/0.25)]"
                            )}
                        >
                            {editMode ? <Check size={14}/> : <PencilLine size={14}/>}
                            {editMode ? 'Guardar' : 'Editar CV'}
                        </button>
                    </div>
                </div>

                <div className="flex items-center gap-4 relative z-10">
                    <div className="relative">
                        <motion.div
                            whileHover={{ scale: 1.05 }}
                            className="size-10 rounded-md bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] flex items-center justify-center font-bold text-lg shadow-xl shadow-[hsl(var(--primary)/0.25)] border-2 border-[hsl(var(--border))]"
                        >
                            {selectedPersona.nombre_completo?.charAt(0) ?? ''}
                        </motion.div>
                        <div className="absolute -bottom-1 -right-1 size-9 rounded-lg bg-[hsl(var(--surface-2))] border-2 border-[hsl(var(--border))] flex items-center justify-center text-[hsl(var(--primary))] shadow-lg overflow-hidden">
                            <Zap size={15} fill="currentColor" className="animate-pulse" />
                        </div>
                    </div>
                    <div className="flex-1 min-w-0">
                        <h2 className="text-lg font-bold text-[hsl(var(--text-primary))] uppercase tracking-[-0.04em] leading-[0.9] mb-2">
                            {selectedPersona.nombre_completo}
                        </h2>
                        <div className="flex items-center gap-2.5">
                            <span className="px-3 py-1 rounded-md bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))] text-2xs font-bold uppercase tracking-wider border border-[hsl(var(--primary)/0.2)]">
                                {selectedPersona.role_in_family || 'Persona'}
                            </span>
                            <span className="text-2xs font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide opacity-60">
                                ID {selectedPersona.id}
                            </span>
                        </div>
                    </div>
                </div>

                {/* Glass KPI Cards */}
                <div className="grid grid-cols-3 gap-3 mt-3 relative z-10">
                    {[
                        { label: 'Salud Esp.', value: `${Math.round(selectedPersona.spiritual_health * 100)}%`, color: 'text-[hsl(var(--success))]', bg: 'bg-[hsl(var(--success)/0.1)]', border: 'border-[hsl(var(--success)/0.2)]' },
                        { label: 'Academia', value: `${Math.round(selectedPersona.academy_progress)}%`, color: 'text-[hsl(var(--primary))]', bg: 'bg-[hsl(var(--primary)/0.1)]', border: 'border-[hsl(var(--primary)/0.2)]' },
                        { label: 'Asistencia', value: '92%', color: 'text-[hsl(var(--primary))]', bg: 'bg-[hsl(var(--primary)/0.1)]', border: 'border-[hsl(var(--primary)/0.2)]' }
                    ].map((kpi, i) => (
                        <div key={i} className={clsx(
                            "p-4 rounded-md border backdrop-blur-sm transition-all hover:scale-105 cursor-default",
                            "bg-[hsl(var(--surface-1))]",
                            kpi.border
                        )}>
                            <p className="text-2xs font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide mb-1.5">{kpi.label}</p>
                            <p className={clsx("text-sm font-bold tracking-tighter leading-none", kpi.color)}>{kpi.value}</p>
                        </div>
                    ))}
                </div>
            </div>

            {/* Sidebar Tabs */}
            <div className="flex px-4 border-b border-[hsl(var(--border))] shrink-0 overflow-x-auto no-scrollbar bg-[hsl(var(--surface-1))] sticky top-0 z-30">
                {[
                    { id: 'timeline', label: 'CV', icon: History },
                    { id: 'tasks', label: 'Tareas', icon: ListTodo },
                    { id: 'finance', label: 'Diezmos', icon: DollarSign },
                    { id: 'messages', label: 'Chat', icon: Mail },
                    { id: 'profile', label: 'Ficha', icon: ShieldCheck }
                ].map(tab => (
                    <button
                        key={tab.id}
                        onClick={() => setModalTab(tab.id as any)}
                        className={clsx(
                            "px-3 py-2 text-2xs font-bold uppercase tracking-wide border-b-2 transition-all flex items-center gap-2.5 shrink-0",
                            modalTab === tab.id ? "border-[hsl(var(--primary))] text-[hsl(var(--primary))]" : "border-transparent text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]"
                        )}
                    >
                        <tab.icon size={12} className={modalTab === tab.id ? "animate-bounce" : ""} /> {tab.label}
                    </button>
                ))}
            </div>

            {/* Sidebar Content Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
                <AnimatePresence mode="wait">
                    {modalTab === 'timeline' && (
                        <motion.div key="timeline" initial={{opacity:0, y:10}} animate={{opacity:1, y:0}} exit={{opacity:0, y:-10}} className="space-y-4">
                            <div>
                                <h3 className="text-2xs font-bold text-[hsl(var(--text-primary))] uppercase tracking-wide mb-3 flex items-center gap-3"><Award className="text-[hsl(var(--primary))]" size={16} /> Perfil Ministerial</h3>
                                <div className="space-y-4">
                                    <div className={clsx("p-3 rounded-md border transition-all", editMode ? "bg-[hsl(var(--surface-2))] border-[hsl(var(--primary)/0.5)] ring-2 ring-[hsl(var(--primary)/0.2)]" : "bg-[hsl(var(--surface-1))] border-[hsl(var(--border))]")}>
                                        <p className="text-2xs font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide mb-2">Talentos Detectados</p>
                                        {editMode ? (
                                            <textarea
                                                value={editedPersona.talents || ''}
                                                onChange={e => setEditedPersona({...editedPersona, talents: e.target.value})}
                                                className="w-full bg-transparent text-xs font-bold text-[hsl(var(--text-primary))] outline-none min-h-[60px] resize-none"
                                            />
                                        ) : (
                                            <p className="text-xs font-bold text-[hsl(var(--text-primary))] italic">&quot;{selectedPersona.talents || 'Pendiente por registrar'}&quot;</p>
                                        )}
                                    </div>
                                    <div className={clsx("p-3 rounded-md border transition-all", editMode ? "bg-[hsl(var(--surface-2))] border-[hsl(var(--primary)/0.5)] ring-2 ring-[hsl(var(--primary)/0.2)]" : "bg-[hsl(var(--primary)/0.05)] border-[hsl(var(--primary)/0.2)]")}>
                                        <p className="text-2xs font-bold text-[hsl(var(--primary))] uppercase tracking-wide mb-2">Dones Espirituales</p>
                                        {editMode ? (
                                            <textarea
                                                value={editedPersona.spiritual_gifts || ''}
                                                onChange={e => setEditedPersona({...editedPersona, spiritual_gifts: e.target.value})}
                                                className="w-full bg-transparent text-xs font-bold text-[hsl(var(--text-primary))] outline-none min-h-[60px] resize-none"
                                            />
                                        ) : (
                                            <p className="text-xs font-bold text-[hsl(var(--text-primary))] italic">&quot;{selectedPersona.spiritual_gifts || 'En proceso de identificación'}&quot;</p>
                                        )}
                                    </div>
                                </div>
                            </div>

                            <div>
                                <h3 className="text-2xs font-bold text-[hsl(var(--text-primary))] uppercase tracking-wide mb-3 flex items-center gap-3"><Clock className="text-[hsl(var(--primary))]" size={16} /> Línea de Tiempo</h3>
                                {loadingHistory ? (
                                    <div className="py-2 flex justify-center"><Loader2 className="animate-spin text-[hsl(var(--primary))]" /></div>
                                ) : history.length > 0 ? (
                                    <div className="relative border-l-2 border-[hsl(var(--border))] ml-3 space-y-4 py-2">
                                        {history.map((event, idx) => (
                                            <motion.div
                                                key={idx}
                                                initial={{ opacity: 0, x: -10 }}
                                                animate={{ opacity: 1, x: 0 }}
                                                transition={{ delay: idx * 0.1 }}
                                                className="relative pl-10 group"
                                            >
                                                <div className={clsx(
                                                    "absolute -left-[11px] top-0 size-5 rounded-full border-[3px] border-[hsl(var(--surface-1))] shadow-lg transition-transform group-hover:scale-125 z-10",
                                                    event.color || 'bg-[hsl(var(--surface-2))]'
                                                )} />
                                                <div className="flex items-center justify-between mb-2">
                                                    <span className="text-2xs font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wider">
                                                        {new Date(event.date).toLocaleDateString('es-ES', {month:'long', day:'numeric'})}
                                                    </span>
                                                    <span className={clsx("px-2.5 py-0.5 rounded-lg text-2xs font-bold uppercase tracking-wide text-[hsl(var(--primary-foreground))] shadow-sm", event.color || 'bg-[hsl(var(--surface-2))]')}>
                                                        {event.type}
                                                    </span>
                                                </div>
                                                <div className="p-3 bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] rounded-md group-hover:bg-[hsl(var(--surface-2))] transition-all group-hover:shadow-md group-hover:border-[hsl(var(--primary)/0.3)]">
                                                    <h4 className="text-xs font-bold text-[hsl(var(--text-primary))] uppercase tracking-tight">
                                                        {event.title || event.name || event.event_name || 'Evento'}
                                                    </h4>
                                                    <p className="text-sm text-[hsl(var(--text-secondary))] font-medium mt-1 leading-relaxed">{event.description}</p>
                                                </div>
                                            </motion.div>
                                        ))}
                                    </div>
                                ) : (
                                    <div className="p-3 text-center bg-[hsl(var(--surface-1))] rounded-md border-2 border-dashed border-[hsl(var(--border))] text-[hsl(var(--text-secondary))] text-2xs font-bold uppercase tracking-wide">Sin actividad</div>
                                )}
                            </div>
                        </motion.div>
                    )}

                    {modalTab === 'tasks' && (
                        <motion.div key="tasks" initial={{opacity:0, scale:0.98}} animate={{opacity:1, scale:1}} exit={{opacity:0, scale:0.98}} className="space-y-3">
                            <h3 className="text-2xs font-bold text-[hsl(var(--text-primary))] uppercase tracking-wide flex items-center gap-3"><ListTodo className="text-[hsl(var(--primary))]" size={16} /> Tareas de Seguimiento</h3>
                            <button onClick={() => router.push('/plataforma/crm/tasks/assign')} className="w-full py-2 bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))] rounded-lg text-2xs font-bold uppercase tracking-wide border border-dashed border-[hsl(var(--primary)/0.3)] flex items-center justify-center gap-2">
                                <Plus size={14}/> Nueva Tarea
                            </button>

                            {loadingTasks ? (
                                <div className="py-2 flex justify-center"><Loader2 className="animate-spin text-[hsl(var(--primary))]" /></div>
                            ) : tasks.length > 0 ? (
                                <div className="space-y-3">
                                    {tasks.map(task => (
                                        <div key={task.id} className="p-3 bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] rounded-md flex items-center justify-between group transition-all hover:border-[hsl(var(--primary)/0.3)]">
                                            <div className="flex items-center gap-4">
                                                <button
                                                    onClick={() => handleUpdateTaskStatus(task.id, task.status === 'done' ? 'todo' : 'done')}
                                                    className={clsx("size-6 rounded-lg flex items-center justify-center border transition-all", task.status === 'done' ? "bg-[hsl(var(--success))] border-[hsl(var(--success))] text-[hsl(var(--primary-foreground))]" : "border-[hsl(var(--border))] text-transparent")}
                                                    aria-label="Completar tarea"
                                                >
                                                    <Check size={14} />
                                                </button>
                                                <div>
                                                    <p className={clsx("text-xs font-bold uppercase tracking-tight", task.status === 'done' ? "text-[hsl(var(--text-secondary))] line-through" : "text-[hsl(var(--text-primary))]")}>{task.title}</p>
                                                    <p className="text-2xs text-[hsl(var(--text-secondary))] font-bold uppercase tracking-wide">{task.due_date ? new Date(task.due_date).toLocaleDateString() : 'Sin fecha'}</p>
                                                </div>
                                            </div>
                                            <span className={clsx("px-2 py-0.5 rounded text-2xs font-bold uppercase tracking-wide", task.priority === 'urgent' ? 'bg-[hsl(var(--destructive)/0.1)] text-[hsl(var(--destructive))]' : 'bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))]')}>
                                                {task.priority}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div className="p-3 text-center text-[hsl(var(--text-secondary))] text-2xs font-bold uppercase tracking-wide border-2 border-dashed border-[hsl(var(--border))] rounded-md">Sin tareas asignadas</div>
                            )}
                        </motion.div>
                    )}

                    {modalTab === 'finance' && (
                        <motion.div key="finance" initial={{opacity:0, x:10}} animate={{opacity:1, x:0}} exit={{opacity:0, x:-10}} className="space-y-3 text-center">
                            <h3 className="text-2xs font-bold text-[hsl(var(--text-primary))] uppercase tracking-wide flex items-center gap-3"><DollarSign className="text-[hsl(var(--success))]" size={16} /> Fidelidad Financiera</h3>
                            {loadingFinance ? (
                                <div className="py-2 flex justify-center"><Loader2 className="animate-spin text-[hsl(var(--success))]" /></div>
                            ) : donations.length > 0 ? (
                                <div className="space-y-3">
                                    <div className="p-4 rounded-md bg-[hsl(var(--success)/0.1)] border border-[hsl(var(--success)/0.25)]">
                                        <p className="text-2xs font-bold text-[hsl(var(--success))] uppercase tracking-wide mb-1">Impacto Total</p>
                                        <p className="text-lg font-bold text-[hsl(var(--success))] tracking-tighter">${donations.reduce((a,b)=>a+b.amount, 0).toLocaleString()}</p>
                                    </div>
                                    <div className="divide-y divide-[hsl(var(--border))] bg-[hsl(var(--surface-1))] rounded-md border border-[hsl(var(--border))] overflow-hidden text-left">
                                        {donations.map((d,i) => (
                                            <div key={i} className="p-4 flex justify-between items-center">
                                                <div className="space-y-0.5">
                                                    <p className="text-2xs font-bold text-[hsl(var(--text-primary))] uppercase">{d.donation_type}</p>
                                                    <p className="text-2xs font-bold text-[hsl(var(--text-secondary))]">{new Date(d.created_at).toLocaleDateString()}</p>
                                                </div>
                                                <p className="text-xs font-bold text-[hsl(var(--success))]">+${d.amount.toLocaleString()}</p>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            ) : (
                                <div className="p-3 bg-[hsl(var(--surface-1))] rounded-md border-2 border-dashed border-[hsl(var(--border))] text-[hsl(var(--text-secondary))] text-2xs font-bold uppercase tracking-wide">Sin registros contables</div>
                            )}
                        </motion.div>
                    )}

                    {modalTab === 'messages' && (
                        <motion.div key="messages" initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}} className="space-y-3">
                            <h3 className="text-2xs font-bold text-[hsl(var(--text-primary))] uppercase tracking-wide flex items-center gap-3"><Mail className="text-[hsl(var(--primary))]" size={16} /> Mensajería Directa</h3>
                            <form onSubmit={handleSendMessage} className="bg-[hsl(var(--surface-1))] p-4 rounded-md border border-[hsl(var(--border))] space-y-2">
                                <div className="flex p-1 bg-[hsl(var(--surface-2))] rounded-lg border border-[hsl(var(--border))]">
                                    {['WhatsApp', 'SMS', 'Email'].map(ch => (
                                        <button
                                            key={ch}
                                            type="button"
                                            onClick={() => setMessageChannel(ch.toLowerCase())}
                                            className={clsx(
                                                "flex-1 py-2 rounded-md text-2xs font-bold uppercase tracking-wide transition-all",
                                                messageChannel === ch.toLowerCase() ? "bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] shadow-md" : "text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]"
                                            )}
                                        >
                                            {ch}
                                        </button>
                                    ))}
                                </div>
                                <textarea
                                    required
                                    value={newMessageContent}
                                    onChange={e => setNewMessageContent(e.target.value)}
                                    className="w-full p-3 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-xs font-bold text-[hsl(var(--text-primary))] focus:ring-2 focus:ring-[hsl(var(--primary))/0.2] outline-none transition-all min-h-12"
                                    placeholder={`Escribe mensaje para ${selectedPersona.nombre_completo}...`}
                                />
                                <button type="submit" disabled={!newMessageContent} className="w-full py-2 bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] rounded-md text-2xs font-bold uppercase tracking-wide shadow-lg shadow-[hsl(var(--primary)/0.2)] flex items-center justify-center gap-2 group">
                                    Enviar Ahora <ChevronRight size={16} className="group-hover:translate-x-1 transition-transform" />
                                </button>
                            </form>
                        </motion.div>
                    )}

                    {modalTab === 'profile' && (
                        <motion.div key="profile" initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}} className="space-y-3">
                            <h3 className="text-2xs font-bold text-[hsl(var(--text-primary))] uppercase tracking-wide flex items-center gap-3"><ShieldCheck className="text-[hsl(var(--primary))]" size={16} /> Notas del Pastor</h3>
                            <div className="space-y-1.5">
                                <label className="text-2xs font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide ml-2">Información Privada y de Seguimiento</label>
                                <div className={clsx("p-4 rounded-md border transition-all min-h-[200px]", editMode ? "bg-[hsl(var(--surface-2))] border-[hsl(var(--primary)/0.5)] ring-2 ring-[hsl(var(--primary)/0.2)]" : "bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))]")}>
                                    {editMode ? (
                                        <textarea
                                            value={editedPersona.pastoral_notes || ''}
                                            onChange={e => setEditedPersona({...editedPersona, pastoral_notes: e.target.value})}
                                            className="w-full bg-transparent text-xs font-bold text-[hsl(var(--text-primary))] outline-none min-h-[180px] resize-none"
                                        />
                                    ) : (
                                        <p className="text-xs font-bold text-[hsl(var(--text-secondary))] leading-relaxed italic">
                                            {selectedPersona.pastoral_notes || 'No hay notas pastorales registradas para este persona.'}
                                        </p>
                                    )}
                                </div>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </div>
    );
}
