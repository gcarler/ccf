"use client";

import React, { useState, useEffect } from 'react';
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

interface MemberDetailSidebarProps {
    member: any;
    onUpdate?: () => void;
    onClose?: () => void;
}

export default function MemberDetailSidebar({ member: initialMember, onUpdate, onClose }: MemberDetailSidebarProps) {
    const { token } = useAuth();
    const { addToast } = useToast();
    const router = useRouter();

    const [selectedMember, setSelectedMember] = useState(initialMember);
    const [editedMember, setEditedMember] = useState(initialMember);
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

    useEffect(() => {
        if (!initialMember) return;
        loadMemberData(initialMember.id);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [initialMember]);

    const loadMemberData = async (memberId: string) => {
        if (!token) return;
        
        fetchTimeline(memberId);
        fetchFinance(memberId);
        fetchTasks(memberId);
    };

    const fetchTimeline = async (id: string) => {
        setLoadingHistory(true);
        try {
            const data = await apiFetch(`/crm/personas/${id}/timeline`, { token, cache: 'no-store' });
            setHistory(Array.isArray(data) ? data : []);
        } catch (err) {
            setHistory([]);
        } finally {
            setLoadingHistory(false);
        }
    };

    const fetchFinance = async (id: string) => {
        setLoadingFinance(true);
        try {
            const data = await apiFetch<any[]>(`/crm/personas/${id}/donations`, { token });
            setDonations(Array.isArray(data) ? data : []);
        } catch (e) {
            setDonations([]);
        } finally {
            setLoadingFinance(false);
        }
    };

    const fetchTasks = async (id: string) => {
        setLoadingTasks(true);
        try {
            const data = await apiFetch<any[]>(`/crm/tasks?assignee_id=${id}`, { token });
            setTasks(Array.isArray(data) ? data : []);
        } catch (e) {
            setTasks([]);
        } finally {
            setLoadingTasks(false);
        }
    };

    const handleUpdateMember = async () => {
        if (!token) return;
        try {
            await apiFetch(`/crm/personas/${selectedMember.id}`, {
                method: 'PATCH',
                token,
                body: editedMember
            });
            addToast("Ficha actualizada", "success");
            setEditMode(false);
            setSelectedMember({ ...selectedMember, ...editedMember });
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
            fetchTasks(selectedMember.id);
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
                    persona_id: selectedMember.id,
                    channel: messageChannel,
                    content: newMessageContent
                }
            });

            addToast("Mensaje enviado exitosamente", "success");
            setNewMessageContent('');
            fetchTimeline(selectedMember.id);
        } catch (err) {
            addToast("Error al enviar mensaje", "error");
        }
    };

    const handlePrint = () => window.print();

    return (
        <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] dark:bg-[#0f1113]">
            {/* Sidebar Header Cinematic */}
            <div className="p-4 border-b border-slate-100 dark:border-white/[0.04] bg-slate-50/50 dark:bg-[#0f1113]/50 backdrop-blur-3xl shrink-0 relative overflow-hidden rounded-t-lg">
                <div className="absolute top-0 right-0 p-4 opacity-[0.03] pointer-events-none text-[hsl(var(--primary))] dark:text-white">
                    <ShieldCheck size={160} />
                </div>
                
                {/* Top Bar Actions */}
                <div className="flex justify-between items-start mb-3 relative z-10">
                    <button 
                        onClick={onClose} 
                        className="p-2.5 bg-[hsl(var(--bg-primary))] dark:bg-white/5 hover:bg-slate-100 dark:hover:bg-white/10 rounded-lg text-slate-400 hover:text-slate-900 dark:hover:text-white transition-all shadow-sm border border-slate-100 dark:border-white/5 active:scale-95"
                    >
                        <CloseIcon size={20} />
                    </button>
                    <div className="flex gap-2.5">
                        <button onClick={handlePrint} className="px-3 py-2.5 bg-white/60 dark:bg-white/5 backdrop-blur-md text-[hsl(var(--primary))] dark:text-blue-300 rounded-lg text-[10px] font-bold uppercase tracking-wider border border-blue-100/50 dark:border-white/10 flex items-center gap-2 shadow-sm hover:bg-blue-50 transition-all active:scale-95">
                            <Printer size={14} /> PDF
                        </button>
                        <button 
                            onClick={() => editMode ? handleUpdateMember() : setEditMode(true)}
                            className={clsx(
                                "px-3 py-2.5 rounded-lg text-[10px] font-bold uppercase tracking-wider flex items-center gap-2 transition-all active:scale-95 shadow-lg", 
                                editMode 
                                    ? "bg-emerald-600 text-white shadow-emerald-500/20" 
                                    : "bg-slate-900 dark:bg-[hsl(var(--primary))] text-white shadow-blue-500/25"
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
                            className="size-10 rounded-md bg-gradient-to-br from-blue-600 to-indigo-700 text-white flex items-center justify-center font-bold text-lg shadow-2xl shadow-blue-500/30 border-4 border-white dark:border-[#1e1f21]"
                        >
                            {selectedMember.nombre_completo?.charAt(0) ?? ''}
                        </motion.div>
                        <div className="absolute -bottom-1 -right-1 size-9 rounded-lg bg-[hsl(var(--bg-primary))] dark:bg-[#0f1113] border-[3px] border-slate-50 dark:border-[#0f1113] flex items-center justify-center text-[hsl(var(--primary))] shadow-xl overflow-hidden">
                            <Zap size={15} fill="currentColor" className="animate-pulse" />
                        </div>
                    </div>
                    <div className="flex-1 min-w-0">
                        <h2 className="text-lg font-bold text-slate-900 dark:text-white uppercase tracking-[-0.04em] leading-[0.9] mb-2">
                            {selectedMember.nombre_completo}
                        </h2>
                        <div className="flex items-center gap-2.5">
                            <span className="px-3 py-1 rounded-md bg-blue-500/10 text-[hsl(var(--primary))] dark:text-blue-300 text-[9px] font-bold uppercase tracking-wider border border-blue-500/20">
                                {selectedMember.role_in_family || 'Miembro'}
                            </span>
                            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wide opacity-60">
                                ID {selectedMember.id}
                            </span>
                        </div>
                    </div>
                </div>

                {/* Glass KPI Cards */}
                <div className="grid grid-cols-3 gap-3 mt-3 relative z-10">
                    {[
                        { label: 'Salud Esp.', value: `${Math.round(selectedMember.spiritual_health * 100)}%`, color: 'text-emerald-600', bg: 'bg-emerald-500/5', border: 'border-emerald-500/10' },
                        { label: 'Academia', value: `${Math.round(selectedMember.academy_progress)}%`, color: 'text-[hsl(var(--primary))]', bg: 'bg-[hsl(var(--primary))]/5', border: 'border-[hsl(var(--primary))]/10' },
                        { label: 'Asistencia', value: '92%', color: 'text-sky-600', bg: 'bg-sky-500/5', border: 'border-sky-500/10' }
                    ].map((kpi, i) => (
                        <div key={i} className={clsx(
                            "p-4 rounded-md border backdrop-blur-sm transition-all hover:scale-105 cursor-default",
                            "bg-white/40 dark:bg-white/[0.03]",
                            kpi.border
                        )}>
                            <p className="text-[8px] font-bold text-slate-400 uppercase tracking-wide mb-1.5">{kpi.label}</p>
                            <p className={clsx("text-sm font-bold tracking-tighter leading-none", kpi.color)}>{kpi.value}</p>
                        </div>
                    ))}
                </div>
            </div>

            {/* Sidebar Tabs */}
            <div className="flex px-4 border-b border-slate-50 dark:border-white/[0.04] shrink-0 overflow-x-auto no-scrollbar bg-[hsl(var(--bg-primary))] dark:bg-transparent sticky top-0 z-30">
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
                            "px-3 py-2 text-[10px] font-bold uppercase tracking-wide border-b-2 transition-all flex items-center gap-2.5 shrink-0",
                            modalTab === tab.id ? "border-blue-600 text-[hsl(var(--primary))]" : "border-transparent text-slate-400 hover:text-slate-800 dark:hover:text-white"
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
                                <h3 className="text-[10px] font-bold text-slate-900 dark:text-white uppercase tracking-wide mb-3 flex items-center gap-3"><Award className="text-[hsl(var(--primary))]" size={16} /> Perfil Ministerial</h3>
                                <div className="space-y-4">
                                    <div className={clsx("p-3 rounded-md border transition-all", editMode ? "bg-[hsl(var(--bg-primary))] border-blue-200 ring-4 ring-blue-50" : "bg-slate-50 dark:bg-white/5 border-slate-100 dark:border-white/5")}>
                                        <p className="text-[9px] font-bold text-slate-400 uppercase tracking-wide mb-2">Talentos Detectados</p>
                                        {editMode ? (
                                            <textarea 
                                                value={editedMember.talents || ''} 
                                                onChange={e => setEditedMember({...editedMember, talents: e.target.value})} 
                                                className="w-full bg-transparent text-xs font-bold outline-none min-h-[60px] resize-none dark:text-white" 
                                            />
                                        ) : (
                                            <p className="text-xs font-bold text-slate-700 dark:text-slate-300 italic">&quot;{selectedMember.talents || 'Pendiente por registrar'}&quot;</p>
                                        )}
                                    </div>
                                    <div className={clsx("p-3 rounded-md border transition-all", editMode ? "bg-[hsl(var(--bg-primary))] border-blue-200 ring-4 ring-blue-50" : "bg-blue-50/30 dark:bg-blue-900/10 border-blue-100 dark:border-blue-900/30")}>
                                        <p className="text-[9px] font-bold text-[hsl(var(--primary))] uppercase tracking-wide mb-2">Dones Espirituales</p>
                                        {editMode ? (
                                            <textarea 
                                                value={editedMember.spiritual_gifts || ''} 
                                                onChange={e => setEditedMember({...editedMember, spiritual_gifts: e.target.value})} 
                                                className="w-full bg-transparent text-xs font-bold outline-none min-h-[60px] resize-none dark:text-white" 
                                            />
                                        ) : (
                                            <p className="text-xs font-bold text-slate-700 dark:text-slate-300 italic">&quot;{selectedMember.spiritual_gifts || 'En proceso de identificación'}&quot;</p>
                                        )}
                                    </div>
                                </div>
                            </div>
                            
                            <div>
                                <h3 className="text-[10px] font-bold text-slate-900 dark:text-white uppercase tracking-wide mb-3 flex items-center gap-3"><Clock className="text-[hsl(var(--primary))]" size={16} /> Línea de Tiempo</h3>
                                {loadingHistory ? (
                                    <div className="py-2 flex justify-center"><Loader2 className="animate-spin text-[hsl(var(--primary))]" /></div>
                                ) : history.length > 0 ? (
                                    <div className="relative border-l-2 border-slate-100 dark:border-white/[0.04] ml-3 space-y-4 py-2">
                                        {history.map((event, idx) => (
                                            <motion.div 
                                                key={idx} 
                                                initial={{ opacity: 0, x: -10 }}
                                                animate={{ opacity: 1, x: 0 }}
                                                transition={{ delay: idx * 0.1 }}
                                                className="relative pl-10 group"
                                            >
                                                <div className={clsx(
                                                    "absolute -left-[11px] top-0 size-5 rounded-full border-[3px] border-white dark:border-[#0f1113] shadow-lg transition-transform group-hover:scale-125 z-10", 
                                                    event.color || 'bg-slate-400'
                                                )} />
                                                <div className="flex items-center justify-between mb-2">
                                                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                                                        {new Date(event.date).toLocaleDateString('es-ES', {month:'long', day:'numeric'})}
                                                    </span>
                                                    <span className={clsx("px-2.5 py-0.5 rounded-lg text-[8px] font-bold uppercase tracking-wide text-white shadow-sm", event.color || 'bg-slate-400')}>
                                                        {event.type}
                                                    </span>
                                                </div>
                                                <div className="p-3 bg-slate-50 dark:bg-white/[0.02] border border-slate-100 dark:border-white/[0.05] rounded-md group-hover:bg-[hsl(var(--bg-primary))] dark:group-hover:bg-white/[0.05] transition-all group-hover:shadow-xl group-hover:shadow-blue-500/5 group-hover:border-blue-500/20">
                                                    <h4 className="text-xs font-bold text-slate-800 dark:text-slate-100 uppercase tracking-tight">
                                                        {event.title || event.name || event.event_name || 'Evento'}
                                                    </h4>
                                                    <p className="text-[12px] text-slate-500 dark:text-slate-400 font-medium mt-1 leading-relaxed">{event.description}</p>
                                                </div>
                                            </motion.div>
                                        ))}
                                    </div>
                                ) : (
                                    <div className="p-3 text-center bg-slate-50 dark:bg-white/5 rounded-md border-2 border-dashed border-slate-100 dark:border-white/10 text-slate-300 text-[10px] font-bold uppercase tracking-wide">Sin actividad</div>
                                )}
                            </div>
                        </motion.div>
                    )}

                    {modalTab === 'tasks' && (
                        <motion.div key="tasks" initial={{opacity:0, scale:0.98}} animate={{opacity:1, scale:1}} exit={{opacity:0, scale:0.98}} className="space-y-3">
                            <h3 className="text-[10px] font-bold text-slate-900 dark:text-white uppercase tracking-wide flex items-center gap-3"><ListTodo className="text-[hsl(var(--primary))]" size={16} /> Tareas de Seguimiento</h3>
                            <button onClick={() => router.push('/plataforma/crm/tasks/assign')} className="w-full py-2 bg-blue-50 dark:bg-blue-900/20 text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] rounded-lg text-[10px] font-bold uppercase tracking-wide border border-dashed border-blue-200 dark:border-blue-800 flex items-center justify-center gap-2">
                                <Plus size={14}/> Nueva Tarea
                            </button>
                            
                            {loadingTasks ? (
                                <div className="py-2 flex justify-center"><Loader2 className="animate-spin text-[hsl(var(--primary))]" /></div>
                            ) : tasks.length > 0 ? (
                                <div className="space-y-3">
                                    {tasks.map(task => (
                                        <div key={task.id} className="p-3 bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-slate-100 dark:border-white/10 rounded-md flex items-center justify-between group transition-all hover:border-blue-500/30">
                                            <div className="flex items-center gap-4">
                                                <button 
                                                    onClick={() => handleUpdateTaskStatus(task.id, task.status === 'done' ? 'todo' : 'done')}
                                                    className={clsx("size-6 rounded-lg flex items-center justify-center border transition-all", task.status === 'done' ? "bg-emerald-500 border-emerald-500 text-white" : "border-slate-200 dark:border-white/10 text-transparent")}
                                                >
                                                    <Check size={14} />
                                                </button>
                                                <div>
                                                    <p className={clsx("text-xs font-bold uppercase tracking-tight", task.status === 'done' ? "text-slate-400 line-through" : "text-slate-800 dark:text-slate-200")}>{task.title}</p>
                                                    <p className="text-[9px] text-slate-400 font-bold uppercase tracking-wide">{task.due_date ? new Date(task.due_date).toLocaleDateString() : 'Sin fecha'}</p>
                                                </div>
                                            </div>
                                            <span className={clsx("px-2 py-0.5 rounded text-[7px] font-bold uppercase tracking-wide", task.priority === 'urgent' ? 'bg-rose-100 text-rose-600' : 'bg-slate-100 dark:bg-white/10 text-slate-400')}>
                                                {task.priority}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div className="p-3 text-center text-slate-300 text-[10px] font-bold uppercase tracking-wide border-2 border-dashed border-slate-100 dark:border-white/10 rounded-md">Sin tareas asignadas</div>
                            )}
                        </motion.div>
                    )}

                    {modalTab === 'finance' && (
                        <motion.div key="finance" initial={{opacity:0, x:10}} animate={{opacity:1, x:0}} exit={{opacity:0, x:-10}} className="space-y-3 text-center">
                            <h3 className="text-[10px] font-bold text-slate-900 dark:text-white uppercase tracking-wide flex items-center gap-3"><DollarSign className="text-emerald-600" size={16} /> Fidelidad Financiera</h3>
                            {loadingFinance ? (
                                <div className="py-2 flex justify-center"><Loader2 className="animate-spin text-emerald-600" /></div>
                            ) : donations.length > 0 ? (
                                <div className="space-y-3">
                                    <div className="p-4 rounded-md bg-emerald-50 dark:bg-emerald-900/10 border border-emerald-100 dark:border-emerald-900/30">
                                        <p className="text-[9px] font-bold text-emerald-600 dark:text-emerald-400 uppercase tracking-wide mb-1">Impacto Total</p>
                                        <p className="text-lg font-bold text-emerald-900 dark:text-emerald-50 tracking-tighter">${donations.reduce((a,b)=>a+b.amount, 0).toLocaleString()}</p>
                                    </div>
                                    <div className="divide-y divide-slate-50 dark:divide-white/5 bg-slate-50 dark:bg-black/20 rounded-md border border-slate-100 dark:border-white/10 overflow-hidden text-left">
                                        {donations.map((d,i) => (
                                            <div key={i} className="p-4 flex justify-between items-center">
                                                <div className="space-y-0.5">
                                                    <p className="text-[10px] font-bold text-slate-800 dark:text-slate-200 uppercase">{d.donation_type}</p>
                                                    <p className="text-[9px] font-bold text-slate-400">{new Date(d.created_at).toLocaleDateString()}</p>
                                                </div>
                                                <p className="text-xs font-bold text-emerald-600">+${d.amount.toLocaleString()}</p>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            ) : (
                                <div className="p-3 bg-slate-50 dark:bg-white/5 rounded-md border-2 border-dashed border-slate-100 dark:border-white/10 text-slate-300 text-[10px] font-bold uppercase tracking-wide">Sin registros contables</div>
                            )}
                        </motion.div>
                    )}

                    {modalTab === 'messages' && (
                        <motion.div key="messages" initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}} className="space-y-3">
                            <h3 className="text-[10px] font-bold text-slate-900 dark:text-white uppercase tracking-wide flex items-center gap-3"><Mail className="text-[hsl(var(--primary))]" size={16} /> Mensajería Directa</h3>
                            <form onSubmit={handleSendMessage} className="bg-slate-50 dark:bg-black/20 p-4 rounded-md border border-slate-100 dark:border-white/10 space-y-2">
                                <div className="flex p-1 bg-[hsl(var(--bg-primary))] dark:bg-white/5 rounded-lg border border-slate-100 dark:border-white/10">
                                    {['WhatsApp', 'SMS', 'Email'].map(ch => (
                                        <button 
                                            key={ch} 
                                            type="button" 
                                            onClick={() => setMessageChannel(ch.toLowerCase())} 
                                            className={clsx(
                                                "flex-1 py-2 rounded-md text-[9px] font-bold uppercase tracking-wide transition-all", 
                                                messageChannel === ch.toLowerCase() ? "bg-[hsl(var(--primary))] text-white shadow-lg" : "text-slate-400 hover:text-slate-600"
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
                                    className="w-full p-3 rounded-md border border-slate-100 dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-white/5 text-xs font-bold focus:ring-4 focus:ring-blue-500/10 outline-none transition-all min-h-12 dark:text-white" 
                                    placeholder={`Escribe mensaje para ${selectedMember.nombre_completo}...`}
                                />
                                <button type="submit" disabled={!newMessageContent} className="w-full py-2 bg-[hsl(var(--primary))] text-white rounded-md text-[10px] font-bold uppercase tracking-wide shadow-xl shadow-blue-500/20 flex items-center justify-center gap-2 group">
                                    Enviar Ahora <ChevronRight size={16} className="group-hover:translate-x-1 transition-transform" />
                                </button>
                            </form>
                        </motion.div>
                    )}

                    {modalTab === 'profile' && (
                        <motion.div key="profile" initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}} className="space-y-3">
                            <h3 className="text-[10px] font-bold text-slate-900 dark:text-white uppercase tracking-wide flex items-center gap-3"><ShieldCheck className="text-[hsl(var(--primary))]" size={16} /> Notas del Pastor</h3>
                            <div className="space-y-1.5">
                                <label className="text-[9px] font-bold text-slate-400 uppercase tracking-wide ml-2">Información Privada y de Seguimiento</label>
                                <div className={clsx("p-4 rounded-md border transition-all min-h-[200px]", editMode ? "bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] border-blue-200 ring-4 ring-blue-50" : "bg-slate-50 dark:bg-white/5 border-slate-100 dark:border-white/10")}>
                                    {editMode ? (
                                        <textarea 
                                            value={editedMember.pastoral_notes || ''} 
                                            onChange={e => setEditedMember({...editedMember, pastoral_notes: e.target.value})} 
                                            className="w-full bg-transparent text-xs font-bold text-slate-700 dark:text-slate-300 outline-none min-h-[180px] resize-none" 
                                        />
                                    ) : (
                                        <p className="text-xs font-bold text-slate-600 dark:text-slate-400 leading-relaxed italic">
                                            {selectedMember.pastoral_notes || 'No hay notas pastorales registradas para este miembro.'}
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
