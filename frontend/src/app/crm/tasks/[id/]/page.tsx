"use client";

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { 
    CheckSquare, 
    CheckCircle2, 
    Circle, 
    Clock, 
    AlertCircle, 
    UserCircle, 
    ChevronLeft, 
    MoreHorizontal, 
    Calendar, 
    Tag, 
    Users, 
    Flame, 
    Send, 
    History, 
    Plus, 
    Link as LinkIcon,
    Paperclip,
    Archive,
    Trash2,
    Activity,
    Target
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import CrmShell from '@/components/crm/CrmShell';
import AdminHero from '@/components/admin/AdminHero';
import clsx from 'clsx';
import { motion, AnimatePresence } from 'framer-motion';

const STATUS_COLUMNS = [
    { key: 'urgent', label: 'Urgente', icon: Flame, color: 'rose', dot: 'bg-rose-500', bg: 'bg-rose-50 dark:bg-rose-900/10' },
    { key: 'pending', label: 'Pendiente', icon: Circle, color: 'slate', dot: 'bg-slate-400', bg: 'bg-slate-50 dark:bg-white/5' },
    { key: 'in_progress', label: 'En Seguimiento', icon: Clock, color: 'blue', dot: 'bg-blue-500', bg: 'bg-blue-50 dark:bg-blue-900/10' },
    { key: 'done', label: 'Completada', icon: CheckCircle2, color: 'emerald', dot: 'bg-emerald-500', bg: 'bg-emerald-50 dark:bg-emerald-900/10' },
];

export default function TaskDetailPage() {
    const { id } = useParams();
    const router = useRouter();
    const { token } = useAuth();
    const { addToast } = useToast();

    const [task, setTask] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('resumen');
    const [isUpdating, setIsUpdating] = useState(false);

    const fetchTask = useCallback(async () => {
        if (!token || !id) return;
        setLoading(true);
        try {
            const data = await apiFetch<any>(`/crm/tasks/${id}`, { token });
            setTask({
                ...data,
                subtasks: [
                    { id: 1, title: 'Llamar para confirmar asistencia', completed: true },
                    { id: 2, title: 'Preparar material de discipulado', completed: false },
                    { id: 3, title: 'Enviar ubicación del punto de encuentro', completed: false },
                ],
                comments: [
                    { id: 1, user: 'Pastor Roberto', text: 'Hay que tener especial cuidado con su disponibilidad horaria.', date: 'Hace 1 hora' }
                ]
            });
        } catch (err) {
            // Mock
            setTask({
                id,
                title: 'Seguimiento de Consolidación: Familia Pérez',
                description: 'Visitar a la familia Pérez para iniciar el proceso de discipulado nivel 1. Se mostraron interesados tras el servicio del domingo.',
                status: 'in_progress',
                priority: 'high',
                category: 'Consolidación',
                member_name: 'Juan Pérez',
                due_date: '2026-05-20',
                created_at: '2026-04-10',
                subtasks: [
                    { id: 1, title: 'Llamar para confirmar asistencia', completed: true },
                    { id: 2, title: 'Preparar material de discipulado', completed: false },
                ],
                comments: [
                    { id: 1, user: 'Pastor Roberto', text: 'Hay que tener especial cuidado con su disponibilidad horaria.', date: 'Hace 1 hora' }
                ]
            });
        } finally {
            setLoading(false);
        }
    }, [token, id]);

    useEffect(() => { fetchTask(); }, [fetchTask]);

    const handleUpdateStatus = async (newStatus: string) => {
        setIsUpdating(true);
        try {
            await apiFetch(`/crm/tasks/${id}`, { method: 'PATCH', token, body: { status: newStatus } });
            setTask((prev: any) => ({ ...prev, status: newStatus }));
            addToast('Estado de tarea actualizado', 'success');
        } catch {
            addToast('Error al actualizar estado', 'error');
        } finally {
            setIsUpdating(false);
        }
    };

    if (loading) return (
        <CrmShell breadcrumbs={[{ label: 'CRM', icon: CheckSquare }, { label: 'Tareas', icon: Clock }, { label: 'Cargando...' }]}>
            <div className="flex flex-col items-center justify-center h-full">
                <div className="size-16 relative">
                    <div className="absolute inset-0 border-4 border-blue-500/20 rounded-full" />
                    <div className="absolute inset-0 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
                </div>
                <p className="mt-6 text-[11px] font-black text-slate-400 tracking-[0.4em] uppercase">Sincronizando Tarea...</p>
            </div>
        </CrmShell>
    );

    return (
        <CrmShell
            breadcrumbs={[
                { label: 'CCF', icon: Users },
                { label: 'Tareas Pastorales', icon: CheckSquare },
                { label: 'Detalle de Tarea', icon: Activity }
            ]}
        >
            <div className="flex flex-col h-full bg-[#fafafa] dark:bg-[#09090a]">
                
                <div className="px-6 py-4">
                    <div className="flex items-center justify-between mb-4">
                        <button 
                            onClick={() => router.push('/crm/tasks')}
                            className="flex items-center gap-1.5 text-slate-400 hover:text-blue-600 transition-colors text-[10px] font-black uppercase tracking-widest"
                        >
                            <ChevronLeft size={14} /> Volver al Listado
                        </button>
                        <div className="flex items-center gap-2">
                            <button className="p-2 text-slate-400 hover:bg-slate-100 dark:hover:bg-white/5 rounded-xl transition-all"><Archive size={16} /></button>
                            <button className="p-2 text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-900/10 rounded-xl transition-all"><Trash2 size={16} /></button>
                        </div>
                    </div>

                    <AdminHero 
                        eyebrow={`${task.category.toUpperCase()} · PRIORIDAD ${task.priority.toUpperCase()}`}
                        title={task.title}
                        description={task.description || 'Sin descripción detallada.'}
                        tags={[task.category, task.status === 'urgent' ? 'Urgencia' : null].filter(Boolean)}
                        watchers={['Pastoral Central', 'Asignado a mí']}
                        primaryAction={{ 
                            label: task.status === 'done' ? 'Reabrir Tarea' : 'Completar Tarea', 
                            icon: CheckCircle2, 
                            onClick: () => handleUpdateStatus(task.status === 'done' ? 'pending' : 'done') 
                        }}
                    />
                </div>

                <div className="flex-1 px-6 pb-6 overflow-y-auto">
                    <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-6">
                        
                        {/* ── Left Column: Task Context ── */}
                        <div className="lg:col-span-8 space-y-6">
                            
                            <div className="flex items-center gap-8 border-b border-slate-200 dark:border-white/5 mb-4">
                                {[
                                    { id: 'resumen', label: 'Resumen y Notas', icon: Target },
                                    { id: 'subtareas', label: 'Lista de Control', icon: CheckCircle2 },
                                    { id: 'comentarios', label: 'Discusión', icon: MessageSquare },
                                ].map(tab => (
                                    <button
                                        key={tab.id}
                                        onClick={() => setActiveTab(tab.id)}
                                        className={clsx(
                                            "flex items-center gap-2 py-4 text-[11px] font-black uppercase tracking-widest transition-all relative",
                                            activeTab === tab.id ? "text-blue-600" : "text-slate-400 hover:text-slate-600"
                                        )}
                                    >
                                        <tab.icon size={14} />
                                        {tab.label}
                                        {activeTab === tab.id && (
                                            <motion.div layoutId="task-tab-underline" className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-600" />
                                        )}
                                    </button>
                                ))}
                            </div>

                            <AnimatePresence mode="wait">
                                {activeTab === 'resumen' && (
                                    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="space-y-6">
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                            <div className="p-6 bg-white dark:bg-white/5 rounded-3xl border border-slate-200 dark:border-white/10 flex items-center gap-4 group hover:border-blue-500/30 transition-all">
                                                <div className="size-12 rounded-2xl bg-slate-50 dark:bg-blue-900/20 text-slate-400 group-hover:text-blue-500 flex items-center justify-center transition-colors">
                                                    <UserCircle size={24} />
                                                </div>
                                                <div>
                                                    <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Vínculo con Miembro</p>
                                                    <p className="font-black text-slate-800 dark:text-white">{task.member_name || 'Sin vincular'}</p>
                                                </div>
                                                <button className="ml-auto p-2 opacity-0 group-hover:opacity-100 transition-opacity"><Plus size={16} /></button>
                                            </div>
                                            <div className="p-6 bg-white dark:bg-white/5 rounded-3xl border border-slate-200 dark:border-white/10 flex items-center gap-4">
                                                <div className="size-12 rounded-2xl bg-slate-50 dark:bg-amber-900/20 text-amber-500 flex items-center justify-center">
                                                    <Calendar size={24} />
                                                </div>
                                                <div>
                                                    <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Fecha Límite</p>
                                                    <p className="font-black text-slate-800 dark:text-white">{task.due_date || 'Sin fecha'}</p>
                                                </div>
                                            </div>
                                        </div>

                                        <div className="p-8 bg-white dark:bg-white/5 rounded-[2.5rem] border border-slate-200 dark:border-white/10 shadow-sm space-y-4">
                                            <h3 className="text-sm font-black uppercase tracking-widest text-slate-400 mb-2">Descripción Completa</h3>
                                            <div className="text-slate-700 dark:text-slate-300 leading-relaxed font-medium">
                                                {task.description ? (
                                                    <p>{task.description}</p>
                                                ) : (
                                                    <p className="italic opacity-50">No se ha proporcionado una descripción detallada para esta tarea.</p>
                                                )}
                                            </div>
                                        </div>

                                        <div className="flex gap-4">
                                            <button className="bg-white dark:bg-white/5 px-6 py-4 rounded-3xl border border-slate-200 dark:border-white/10 text-[10px] font-black uppercase tracking-widest flex items-center gap-2 hover:bg-slate-50 transition-all">
                                                <Paperclip size={14} /> Adjuntar Evidencia
                                            </button>
                                            <button className="bg-white dark:bg-white/5 px-6 py-4 rounded-3xl border border-slate-200 dark:border-white/10 text-[10px] font-black uppercase tracking-widest flex items-center gap-2 hover:bg-slate-50 transition-all">
                                                <LinkIcon size={14} /> Copiar Enlace
                                            </button>
                                        </div>
                                    </motion.div>
                                )}

                                {activeTab === 'subtareas' && (
                                    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
                                        <div className="bg-white dark:bg-white/5 rounded-[2.5rem] border border-slate-200 dark:border-white/10 overflow-hidden">
                                            <div className="px-8 py-6 border-b border-slate-100 dark:border-white/5 bg-slate-50/50 dark:bg-black/20 flex items-center justify-between">
                                                <h3 className="text-[11px] font-black uppercase tracking-widest text-slate-500">Lista de Control</h3>
                                                <span className="text-[10px] font-black text-blue-600 bg-blue-50 dark:bg-blue-900/40 px-3 py-1 rounded-full">33% completado</span>
                                            </div>
                                            <div className="divide-y divide-slate-100 dark:divide-white/5">
                                                {(task.subtasks || []).map((sub: any) => (
                                                    <div key={sub.id} className="p-6 flex items-center gap-4 hover:bg-slate-50 dark:hover:bg-white/[0.02] transition-colors cursor-pointer group">
                                                        <div className={clsx("size-5 rounded border-2 transition-all flex items-center justify-center", sub.completed ? "bg-emerald-500 border-emerald-500" : "border-slate-200 dark:border-white/10")}>
                                                            {sub.completed && <CheckCircle2 size={12} className="text-white" />}
                                                        </div>
                                                        <span className={clsx("text-sm font-bold flex-1", sub.completed && "line-through text-slate-400")}>{sub.title}</span>
                                                        <button className="opacity-0 group-hover:opacity-100 transition-opacity p-2 text-slate-300 hover:text-rose-500"><Trash2 size={14} /></button>
                                                    </div>
                                                ))}
                                                <button className="w-full p-6 text-left flex items-center gap-4 text-slate-400 hover:text-blue-600 transition-colors">
                                                    <Plus size={18} />
                                                    <span className="text-sm font-black uppercase tracking-widest">Agregar nuevo ítem...</span>
                                                </button>
                                            </div>
                                        </div>
                                    </motion.div>
                                )}

                                {activeTab === 'comentarios' && (
                                    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
                                        <div className="space-y-4">
                                            {(task.comments || []).map((c: any) => (
                                                <div key={c.id} className="flex gap-4">
                                                    <div className="size-10 rounded-2xl bg-indigo-600 flex items-center justify-center text-white shrink-0 font-black text-xs">R</div>
                                                    <div className="flex-1 space-y-1">
                                                        <div className="flex items-center justify-between">
                                                            <span className="text-[11px] font-black text-indigo-600 uppercase tracking-widest">{c.user}</span>
                                                            <span className="text-[10px] text-slate-400 font-bold">{c.date}</span>
                                                        </div>
                                                        <div className="bg-white dark:bg-white/5 p-4 rounded-2xl rounded-tl-none border border-slate-200 dark:border-white/10 shadow-sm">
                                                            <p className="text-sm text-slate-700 dark:text-slate-300 font-medium">{c.text}</p>
                                                        </div>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                        <div className="p-2 bg-white dark:bg-white/5 rounded-[2rem] border border-slate-200 dark:border-white/10">
                                            <input className="w-full bg-transparent px-6 py-4 outline-none text-sm" placeholder="Escribe un comentario ministerial..." />
                                            <div className="flex justify-end p-2 pb-2">
                                                <button className="px-6 py-2.5 bg-blue-600 text-white rounded-xl text-[10px] font-black uppercase tracking-widest shadow-lg shadow-blue-500/20">Publicar</button>
                                            </div>
                                        </div>
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </div>

                        {/* ── Right Column: Management ── */}
                        <div className="lg:col-span-4 space-y-6">
                            
                            <div className="p-8 bg-white dark:bg-white/5 rounded-[2.5rem] border border-slate-200 dark:border-white/10 shadow-sm space-y-8">
                                <div>
                                    <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-6 flex items-center gap-2">
                                        Fase Actual
                                    </h3>
                                    <div className="space-y-2">
                                        {STATUS_COLUMNS.map(opt => (
                                            <button
                                                key={opt.key}
                                                onClick={() => handleUpdateStatus(opt.key)}
                                                disabled={isUpdating}
                                                className={clsx(
                                                    "w-full flex items-center justify-between px-4 py-4 rounded-2xl border transition-all text-left",
                                                    task.status === opt.key
                                                        ? `${opt.bg} border-${opt.color}-500/30 text-${opt.color}-600`
                                                        : "bg-transparent border-transparent text-slate-500 hover:bg-slate-50 dark:hover:bg-white/5"
                                                )}
                                            >
                                                <div className="flex items-center gap-3">
                                                    <div className={clsx("size-2.5 rounded-full", opt.dot)} />
                                                    <span className="text-[11px] font-black uppercase tracking-widest">{opt.label}</span>
                                                </div>
                                            </button>
                                        ))}
                                    </div>
                                </div>

                                <div className="pt-8 border-t border-slate-100 dark:border-white/5 space-y-6">
                                    <div className="flex items-center justify-between">
                                        <div className="space-y-1">
                                            <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Asignado a</p>
                                            <p className="text-sm font-black text-slate-800 dark:text-white">Equipo Consolidación</p>
                                        </div>
                                        <button className="size-10 rounded-xl bg-slate-50 dark:bg-white/5 flex items-center justify-center text-slate-400"><Plus size={16} /></button>
                                    </div>
                                    <div className="flex items-center justify-between">
                                        <div className="space-y-1">
                                            <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Categoría</p>
                                            <p className="text-sm font-black text-slate-800 dark:text-white">{task.category}</p>
                                        </div>
                                        <button className="size-10 rounded-xl bg-slate-50 dark:bg-white/5 flex items-center justify-center text-slate-400"><Tag size={16} /></button>
                                    </div>
                                </div>
                            </div>

                            <div className="p-10 bg-gradient-to-br from-indigo-600 to-blue-700 text-white rounded-[2.5rem] shadow-2xl relative overflow-hidden">
                                <Activity size={100} className="absolute -bottom-4 -right-4 opacity-10 rotate-12" />
                                <div className="relative z-10">
                                    <h4 className="text-[11px] font-black uppercase tracking-[0.4em] mb-4 text-blue-200">Consejo Pastoral</h4>
                                    <p className="text-sm font-medium leading-relaxed italic opacity-90">
                                        "Es vital que el seguimiento sea en las primeras 72 horas para asegurar la retención del miembro nuevo."
                                    </p>
                                    <div className="mt-8 flex items-center gap-3">
                                        <div className="size-8 rounded-full border-2 border-white/20 overflow-hidden">
                                            <img src="https://api.dicebear.com/7.x/avataaars/svg?seed=Pastor" alt="P" />
                                        </div>
                                        <div>
                                            <p className="text-[10px] font-black uppercase">Pastor General</p>
                                            <p className="text-[8px] opacity-60">Dirección Espiritual</p>
                                        </div>
                                    </div>
                                </div>
                            </div>

                        </div>
                    </div>
                </div>
            </div>
        </CrmShell>
    );
}
