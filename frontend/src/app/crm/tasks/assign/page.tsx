"use client";

import React, { useEffect, useMemo, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import {
    Search,
    Bell,
    Clock,
    UserCheck,
    Link2,
    Users,
    Loader2,
    Plus,
    User,
    ShieldCheck
} from 'lucide-react';
import CrmShell from '@/components/crm/CrmShell';
import AdminHero from '@/components/admin/AdminHero';
import { apiFetch } from '@/lib/http';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

interface Leader {
    id: number;
    username: string;
    role: string;
}

interface Member {
    id: number;
    first_name: string;
    last_name: string;
    church_role: string;
    spiritual_status: string;
}

export default function TaskAssignment() {
    const { isAuthenticated, token } = useAuth();
    const { addToast } = useToast();
    const router = useRouter();
    
    const [leaders, setLeaders] = useState<Leader[]>([]);
    const [members, setMembers] = useState<Member[]>([]);
    const [loading, setLoading] = useState(true);
    
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedMemberId, setSelectedMemberId] = useState<number | null>(null);
    const [selectedLeaderId, setSelectedLeaderId] = useState<string>('');
    const [taskTitle, setTaskTitle] = useState('Llamada de seguimiento');
    const [taskDescription, setTaskDescription] = useState('');
    const [isAssigning, setIsAssigning] = useState(false);

    const fetchData = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const [usersData, membersData] = await Promise.all([
                apiFetch<any[]>('/auth/user-list', { token }),
                apiFetch<any[]>('/crm/members', { token })
            ]);
            
            // Filtrar solo líderes/admin/staff para asignar
            setLeaders(usersData.filter(u => ['admin', 'pastor', 'coordinador', 'docente'].includes(u.role)));
            setMembers(Array.isArray(membersData) ? membersData : []);
        } catch (err) {
            console.error(err);
            addToast("Error al cargar datos de asignación", "error");
        } finally {
            setLoading(false);
        }
    }, [token, addToast]);

    useEffect(() => {
        if (isAuthenticated) fetchData();
    }, [isAuthenticated, fetchData]);

    const filteredMembers = useMemo(() => {
        return members.filter(m => 
            `${m.first_name} ${m.last_name}`.toLowerCase().includes(searchQuery.toLowerCase())
        ).slice(0, 10); // Limit to 10 for assignment UI
    }, [members, searchQuery]);

    const handleAssign = async () => {
        if (!selectedMemberId || !selectedLeaderId || !taskTitle) {
            addToast("Completa todos los campos obligatorios", "warning");
            return;
        }

        setIsAssigning(true);
        try {
            await apiFetch('/crm/tasks/', {
                method: 'POST',
                token,
                body: {
                    title: taskTitle,
                    description: taskDescription,
                    member_id: selectedMemberId,
                    assignee_id: parseInt(selectedLeaderId),
                    priority: 'normal',
                    due_date: new Date(Date.now() + 86400000 * 2).toISOString() // Default 2 days
                }
            });
            addToast("Tarea asignada exitosamente", "success");
            setTaskDescription('');
            setSelectedMemberId(null);
            setSelectedLeaderId('');
        } catch (err) {
            addToast("Error al asignar tarea", "error");
        } finally {
            setIsAssigning(false);
        }
    };

    if (!isAuthenticated) return null;

    const selectedMember = members.find(m => m.id === selectedMemberId);

    return (
        <CrmShell
            breadcrumbs={[{ label: 'CCF', icon: Users }, { label: 'Consolidación', icon: Users }, { label: 'Asignación', icon: UserCheck }]}
            rightActions={
                <button className="flex size-10 items-center justify-center rounded-full bg-blue-50 text-blue-600 hover:bg-blue-100 transition-all relative">
                    <Bell size={20} />
                    <span className="absolute top-2 right-2 size-2 bg-rose-500 rounded-full ring-2 ring-white"></span>
                </button>
            }
        >
        <style jsx global>{`
            .glass-panel {
                background: rgba(255, 255, 255, 0.7);
                backdrop-filter: blur(20px) saturate(180%);
                border: 1px solid rgba(255, 255, 255, 0.3);
            }
            .dark .glass-panel {
                background: rgba(30, 31, 33, 0.8);
                border: 1px solid rgba(255, 255, 255, 0.05);
            }
            .shimmer-text {
                background: linear-gradient(90deg, #3b82f6, #818cf8, #3b82f6);
                background-size: 200% auto;
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                animation: shine 3s linear infinite;
            }
            @keyframes shine {
                to { background-position: 200% center; }
            }
        `}</style>

        <AdminHero
            eyebrow="Despliegue de Consolidación"
            title="Asignación de Seguimiento"
            description="Distribuye la carga ministerial entre tus líderes y asegura que nadie se quede sin cuidado."
            tags={['Liderazgo', 'Orden', 'Optimus Brain']}
            watchers={['Pastores CCF', 'Optimus Brain']}
            primaryAction={{ label: 'Pipeline Global', icon: Link2, onClick: () => router.push('/crm/pipeline') }}
            secondaryAction={{ label: 'Actualizar', icon: Clock, onClick: fetchData }}
        />

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
            {/* Left Column: Search & List */}
            <div className="lg:col-span-7 space-y-8">
                <div className="relative group">
                    <Search className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-blue-500 transition-colors" size={20} />
                    <input
                        type="text"
                        placeholder="Buscar miembro para seguimiento..."
                        className="w-full bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 rounded-[2rem] py-5 pl-14 pr-6 text-sm font-bold shadow-sm focus:ring-4 focus:ring-blue-500/10 transition-all outline-none"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                    />
                </div>

                <div className="bg-white dark:bg-[#1e1f21] rounded-[3rem] p-8 shadow-sm border border-slate-50 dark:border-white/5 overflow-hidden">
                    <div className="flex items-center justify-between mb-8">
                        <h3 className="text-[11px] font-black uppercase tracking-[0.3em] text-slate-400">Resultados de Búsqueda</h3>
                        <span className="px-3 py-1 bg-blue-50 text-blue-600 rounded-full text-[9px] font-black uppercase">{filteredMembers.length} Personas</span>
                    </div>

                    <div className="space-y-4">
                        {loading ? (
                            <div className="py-20 flex flex-col items-center gap-4">
                                <Loader2 className="animate-spin text-blue-600" size={32} />
                                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Cargando congregación...</p>
                            </div>
                        ) : filteredMembers.map((m, idx) => (
                            <motion.div 
                                initial={{ opacity: 0, x: -20 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: idx * 0.05 }}
                                key={m.id}
                                onClick={() => setSelectedMemberId(m.id)}
                                className={clsx(
                                    "p-5 rounded-[2rem] border transition-all cursor-pointer flex items-center justify-between group",
                                    selectedMemberId === m.id ? "bg-blue-600 border-blue-600 text-white shadow-xl shadow-blue-500/20" : "bg-slate-50 dark:bg-white/5 border-transparent hover:border-blue-200"
                                )}
                            >
                                <div className="flex items-center gap-5">
                                    <div className={clsx(
                                        "size-12 rounded-2xl flex items-center justify-center font-black text-lg shadow-sm",
                                        selectedMemberId === m.id ? "bg-white/20" : "bg-white dark:bg-white/10 text-blue-600"
                                    )}>
                                        {m.first_name.charAt(0)}
                                    </div>
                                    <div>
                                        <p className="font-black uppercase tracking-tight text-[15px] leading-none mb-1">{m.first_name} {m.last_name}</p>
                                        <p className={clsx("text-[10px] font-bold uppercase tracking-widest", selectedMemberId === m.id ? "text-blue-100" : "text-slate-400")}>{m.church_role} · {m.spiritual_status}</p>
                                    </div>
                                </div>
                                <div className={clsx(
                                    "size-8 rounded-xl flex items-center justify-center transition-all",
                                    selectedMemberId === m.id ? "bg-white text-blue-600 rotate-90" : "bg-slate-200 dark:bg-white/10 text-slate-400 group-hover:bg-blue-100 group-hover:text-blue-600"
                                )}>
                                    <Plus size={18} />
                                </div>
                            </motion.div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Right Column: Assignment Form */}
            <div className="lg:col-span-5">
                <AnimatePresence mode="wait">
                    {selectedMember ? (
                        <motion.div 
                            key="form"
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.95 }}
                            className="glass-panel p-10 rounded-[3.5rem] shadow-2xl space-y-10 sticky top-10"
                        >
                            <div className="space-y-4">
                                <div className="inline-flex items-center gap-3 px-4 py-1.5 bg-blue-600/10 text-blue-600 border border-blue-600/20 rounded-full text-[10px] font-black uppercase tracking-[0.2em]">
                                    <ShieldCheck size={14} /> Asignación Inteligente
                                </div>
                                <h3 className="text-3xl font-black text-slate-900 dark:text-white tracking-tighter leading-none">
                                    Seguimiento para <br/>
                                    <span className="shimmer-text">{selectedMember.first_name}</span>
                                </h3>
                            </div>

                            <div className="space-y-6">
                                <div className="space-y-2">
                                    <label className="text-[10px] font-black uppercase tracking-[0.25em] text-slate-400 ml-2">Líder Responsable</label>
                                    <select
                                        value={selectedLeaderId}
                                        onChange={(e) => setSelectedLeaderId(e.target.value)}
                                        className="w-full bg-white dark:bg-white/5 border border-slate-100 dark:border-white/10 rounded-2xl py-4 px-6 text-sm font-bold outline-none focus:ring-4 focus:ring-blue-500/10 transition-all appearance-none"
                                    >
                                        <option value="">Seleccionar responsable...</option>
                                        {leaders.map(l => (
                                            <option key={l.id} value={l.id}>{l.username} ({l.role})</option>
                                        ))}
                                    </select>
                                </div>

                                <div className="space-y-2">
                                    <label className="text-[10px] font-black uppercase tracking-[0.25em] text-slate-400 ml-2">Actividad de Consolidación</label>
                                    <div className="grid grid-cols-2 gap-2">
                                        {['Llamada', 'Visita', 'Consejería', 'Bienvenida'].map(type => (
                                            <button 
                                                key={type}
                                                onClick={() => setTaskTitle(`Seguimiento: ${type}`)}
                                                className={clsx(
                                                    "py-3 px-4 rounded-xl text-[10px] font-black uppercase tracking-widest border transition-all",
                                                    taskTitle.includes(type) ? "bg-blue-600 border-blue-600 text-white shadow-lg" : "bg-white dark:bg-white/5 border-slate-100 dark:border-white/10 text-slate-500"
                                                )}
                                            >
                                                {type}
                                            </button>
                                        ))}
                                    </div>
                                </div>

                                <div className="space-y-2">
                                    <label className="text-[10px] font-black uppercase tracking-[0.25em] text-slate-400 ml-2">Nota de Contexto</label>
                                    <textarea
                                        rows={4}
                                        placeholder="Ej: Dar bienvenida, preguntar por su familia..."
                                        className="w-full bg-white dark:bg-white/5 border border-slate-100 dark:border-white/10 rounded-[2rem] py-5 px-6 text-sm font-medium outline-none focus:ring-4 focus:ring-blue-500/10 transition-all"
                                        value={taskDescription}
                                        onChange={(e) => setTaskDescription(e.target.value)}
                                    />
                                </div>

                                <button
                                    onClick={handleAssign}
                                    disabled={isAssigning}
                                    className="w-full py-5 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-[2rem] font-black text-xs uppercase tracking-[0.3em] shadow-2xl hover:translate-y-[-4px] active:scale-95 transition-all flex items-center justify-center gap-4 group"
                                >
                                    {isAssigning ? <Loader2 className="animate-spin" /> : <UserCheck size={20} className="group-hover:rotate-12 transition-transform" />}
                                    Confirmar Misión
                                </button>
                            </div>
                        </motion.div>
                    ) : (
                        <div className="h-full flex flex-col items-center justify-center p-12 text-center space-y-6 bg-slate-50/50 dark:bg-white/5 rounded-[4rem] border-2 border-dashed border-slate-200 dark:border-white/10">
                            <div className="size-32 rounded-[3.5rem] bg-white dark:bg-white/10 shadow-2xl flex items-center justify-center text-slate-200"><User size={64} strokeWidth={1} /></div>
                            <div className="space-y-2">
                                <h4 className="text-xl font-black text-slate-800 dark:text-white uppercase tracking-tight">Esperando selección</h4>
                                <p className="text-sm text-slate-400 font-medium max-w-[240px] mx-auto leading-relaxed">Selecciona un miembro de la congregación para iniciar el proceso de asignación pastoral.</p>
                            </div>
                        </div>
                    )}
                </AnimatePresence>
            </div>
        </div>
        </CrmShell>
    );
}

