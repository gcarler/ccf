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
    id: string;
    username: string;
    role: string;
}

interface Persona {
    id: string;
    nombre_completo?: string;
    first_name?: string;
    last_name?: string;
    church_role: string;
    spiritual_status: string;
}

export default function TaskAssignment() {
    const { isAuthenticated, token, loading: authLoading } = useAuth();
    const { addToast } = useToast();
    const router = useRouter();
    
    const [leaders, setLeaders] = useState<Leader[]>([]);
    const [personas, setPersonas] = useState<Persona[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [reloadKey, setReloadKey] = useState(0);
    
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedPersonaId, setSelectedPersonaId] = useState<string | null>(null);
    const [selectedLeaderId, setSelectedLeaderId] = useState<string>('');
    const [taskTitle, setTaskTitle] = useState('Llamada de seguimiento');
    const [taskDescription, setTaskDescription] = useState('');
    const [isAssigning, setIsAssigning] = useState(false);

    const fetchData = useCallback(async (signal?: AbortSignal) => {
        if (!token) {
            setLoading(false);
            setError("Debes iniciar sesión para asignar tareas.");
            return;
        }
        setLoading(true);
        try {
            setError(null);
            const [usersData, personasData] = await Promise.all([
                apiFetch<{ items: Leader[]; total: number }>('/admin/users', { token, signal }),
                apiFetch<Persona[]>('/crm/personas', { token, signal })
            ]);
            
            // Filtrar solo líderes/admin/staff para asignar
            const usersItems = usersData?.items ?? [];
            setLeaders(usersItems.filter(u => ['admin', 'pastor', 'coordinador', 'docente'].includes(u.role)));
            setPersonas(Array.isArray(personasData) ? personasData : []);
        } catch (err) {
            setLeaders([]);
            setPersonas([]);
            setError("No se pudieron cargar los datos de asignación.");
            addToast("Error al cargar datos de asignación", "error");
        } finally {
            setLoading(false);
        }
    }, [token, addToast]);

    useEffect(() => {
        if (!isAuthenticated || authLoading) return;
        const controller = new AbortController();
        fetchData(controller.signal);
        return () => controller.abort();
    }, [authLoading, fetchData, isAuthenticated, reloadKey]);

    const filteredPersonas = useMemo(() => {
        return personas.filter(m =>
            (m.nombre_completo || `${m.first_name ?? ''} ${m.last_name ?? ''}`.trim()).toLowerCase().includes(searchQuery.toLowerCase())
        ).slice(0, 10); // Limit to 10 for assignment UI
    }, [personas, searchQuery]);

    const handleAssign = async () => {
        if (!selectedPersonaId || !selectedLeaderId || !taskTitle) {
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
                    persona_id: selectedPersonaId,
                    assignee_id: selectedLeaderId,
                    priority: 'normal',
                    due_date: new Date(Date.now() + 86400000 * 2).toISOString() // Default 2 days
                }
            });
            addToast("Tarea asignada exitosamente", "success");
            setTaskDescription('');
            setSelectedPersonaId(null);
            setSelectedLeaderId('');
        } catch (err) {
            addToast("Error al asignar tarea", "error");
        } finally {
            setIsAssigning(false);
        }
    };

    if (authLoading) return <div className="p-4 text-center animate-pulse font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Verificando sesión...</div>;

    if (!isAuthenticated) return null;

    const selectedPersona = personas.find(m => m.id === selectedPersonaId);

    return (
        <CrmShell
            breadcrumbs={[{ label: 'CCF', icon: Users }, { label: 'Consolidación', icon: Users }, { label: 'Asignación', icon: UserCheck }]}
            rightActions={
                <button className="flex size-8 items-center justify-center rounded-full bg-[hsl(var(--info-muted))] text-[hsl(var(--primary))] hover:bg-[hsl(var(--info-muted))] transition-all relative" aria-label="Notificaciones">
                    <Bell size={20} />
                    <span className="absolute top-2 right-2 size-2 bg-[hsl(var(--destructive))] rounded-full ring-2 ring-white"></span>
                </button>
            }
        >
        {error && (
            <div className="mb-4 flex flex-col gap-3 rounded-md border border-[hsl(var(--warning)/0.2)] bg-[hsl(var(--warning-muted))] p-4 text-[hsl(var(--warning))] dark:border-[hsl(var(--warning)/0.2)] dark:bg-[hsl(var(--warning)/0.1)] dark:text-[hsl(var(--warning))] md:flex-row md:items-center md:justify-between">
                <div>
                    <p className="text-[11px] font-bold uppercase tracking-wide">No se pudo cargar la asignación</p>
                    <p className="text-xs">{error}</p>
                </div>
                <button
                    onClick={() => setReloadKey(key => key + 1)}
                    className="rounded-md border border-[hsl(var(--warning)/0.3)] px-3 py-1.5 text-[11px] font-bold uppercase tracking-wide hover:bg-[hsl(var(--warning-muted))] dark:border-[hsl(var(--warning)/0.4)] dark:hover:bg-[hsl(var(--warning)/0.2)]"
                >
                    Reintentar
                </button>
            </div>
        )}
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
                background: linear-gradient(90deg, hsl(var(--primary)), hsl(var(--info)), hsl(var(--primary)));
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
            primaryAction={{ label: 'Pipeline Global', icon: Link2, onClick: () => router.push('/plataforma/crm/pipeline') }}
            secondaryAction={{ label: 'Actualizar', icon: Clock, onClick: fetchData }}
        />

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
            {/* Left Column: Search & List */}
            <div className="lg:col-span-7 space-y-3">
                <div className="relative group">
                    <Search className="absolute left-5 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))] group-focus-within:text-[hsl(var(--primary))] transition-colors" size={20} />
                    <input
                        type="text"
                        placeholder="Buscar persona para seguimiento..."
                        className="w-full bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/5 rounded-md py-2 pl-14 pr-6 text-sm font-bold shadow-sm focus:ring-4 focus:ring-[hsl(var(--primary))]/10 transition-all outline-none"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                    />
                </div>

                <div className="bg-[hsl(var(--surface-1))] dark:bg-[hsl(var(--surface-1))] rounded-lg p-4 shadow-sm border border-[hsl(var(--border))] dark:border-white/5 overflow-hidden">
                    <div className="flex items-center justify-between mb-3">
                        <h3 className="text-[11px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Resultados de Búsqueda</h3>
                        <span className="px-3 py-1 bg-[hsl(var(--info-muted))] text-[hsl(var(--primary))] rounded-full text-[9px] font-bold uppercase">{filteredPersonas.length} Personas</span>
                    </div>

                    <div className="space-y-4">
                        {loading ? (
                            <div className="py-1.5 flex flex-col items-center gap-4">
                                <Loader2 className="animate-spin text-[hsl(var(--primary))]" size={32} />
                                <p className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Cargando congregación...</p>
                            </div>
                        ) : filteredPersonas.map((m, idx) => (
                            <motion.div 
                                initial={{ opacity: 0, x: -20 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: idx * 0.05 }}
                                key={m.id}
                                onClick={() => setSelectedPersonaId(m.id)}
                                className={clsx(
                                    "p-3 rounded-md border transition-all cursor-pointer flex items-center justify-between group",
                                    selectedPersonaId === m.id ? "bg-[hsl(var(--primary))] border-[hsl(var(--primary))] text-white shadow-xl shadow-[hsl(var(--primary)/0.2)]" : "bg-[hsl(var(--surface-1))] dark:bg-white/5 border-transparent hover:border-[hsl(var(--primary))]"
                                )}
                            >
                                <div className="flex items-center gap-3">
                                    <div className={clsx(
                                        "size-9 rounded-lg flex items-center justify-center font-bold text-sm shadow-sm",
                                        selectedPersonaId === m.id ? "bg-white/20" : "bg-[hsl(var(--surface-1))] dark:bg-white/10 text-[hsl(var(--primary))]"
                                    )}>
                                        {m.nombre_completo?.charAt(0) ?? ''}
                                    </div>
                                    <div>
                                        <p className="font-bold uppercase tracking-tight text-sm leading-none mb-1">{m.nombre_completo || `${m.first_name ?? ''} ${m.last_name ?? ''}`.trim()}</p>
                                        <p className={clsx("text-[10px] font-bold uppercase tracking-wide", selectedPersonaId === m.id ? "text-[hsl(var(--info))]" : "text-[hsl(var(--text-secondary))]")}>{m.church_role} · {m.spiritual_status}</p>
                                    </div>
                                </div>
                                <div className={clsx(
                                    "size-8 rounded-md flex items-center justify-center transition-all",
                                    selectedPersonaId === m.id ? "bg-[hsl(var(--surface-1))] text-[hsl(var(--primary))] rotate-90" : "bg-[hsl(var(--surface-3))] dark:bg-white/10 text-[hsl(var(--text-secondary))] group-hover:bg-[hsl(var(--info-muted))] group-hover:text-[hsl(var(--primary))]"
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
                    {selectedPersona ? (
                        <motion.div 
                            key="form"
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.95 }}
                            className="glass-panel p-3 rounded-lg shadow-2xl space-y-4 sticky top-5"
                        >
                            <div className="space-y-4">
                                <div className="inline-flex items-center gap-3 px-4 py-1.5 bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))] border border-[hsl(var(--primary)/0.2)] rounded-full text-[10px] font-bold uppercase tracking-wide">
                                    <ShieldCheck size={14} /> Asignación Inteligente
                                </div>
                                <h3 className="text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tighter leading-none">
                                    Seguimiento para <br/>
                                    <span className="shimmer-text">{selectedPersona.nombre_completo || `${selectedPersona.first_name ?? ''} ${selectedPersona.last_name ?? ''}`.trim()}</span>
                                </h3>
                            </div>

                            <div className="space-y-3">
                                <div className="space-y-2">
                                    <label className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] ml-2">Líder Responsable</label>
                                    <select
                                        value={selectedLeaderId}
                                        onChange={(e) => setSelectedLeaderId(e.target.value)}
                                        className="w-full bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg py-2 px-4 text-sm font-bold outline-none focus:ring-4 focus:ring-[hsl(var(--primary))]/10 transition-all appearance-none"
                                    >
                                        <option value="">Seleccionar responsable...</option>
                                        {leaders.map(l => (
                                            <option key={l.id} value={l.id}>{l.username} ({l.role})</option>
                                        ))}
                                    </select>
                                </div>

                                <div className="space-y-2">
                                    <label className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] ml-2">Actividad de Consolidación</label>
                                    <div className="grid grid-cols-2 gap-2">
                                        {['Llamada', 'Visita', 'Consejería', 'Bienvenida'].map(type => (
                                            <button 
                                                key={type}
                                                onClick={() => setTaskTitle(`Seguimiento: ${type}`)}
                                                className={clsx(
                                                    "py-1.5 px-4 rounded-md text-[10px] font-bold uppercase tracking-wide border transition-all",
                                                    taskTitle.includes(type) ? "bg-[hsl(var(--primary))] border-[hsl(var(--primary))] text-white shadow-lg" : "bg-[hsl(var(--surface-1))] dark:bg-white/5 border-[hsl(var(--border))] dark:border-white/10 text-[hsl(var(--text-secondary))]"
                                                )}
                                            >
                                                {type}
                                            </button>
                                        ))}
                                    </div>
                                </div>

                                <div className="space-y-2">
                                    <label className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] ml-2">Nota de Contexto</label>
                                    <textarea
                                        rows={4}
                                        placeholder="Ej: Dar bienvenida, preguntar por su familia..."
                                        className="w-full bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-md py-2 px-4 text-sm font-medium outline-none focus:ring-4 focus:ring-[hsl(var(--primary))]/10 transition-all"
                                        value={taskDescription}
                                        onChange={(e) => setTaskDescription(e.target.value)}
                                    />
                                </div>

                                <button
                                    onClick={handleAssign}
                                    disabled={isAssigning}
                                    className="w-full py-2 bg-[hsl(var(--bg-muted))] dark:bg-[hsl(var(--bg-primary))] text-white dark:text-[hsl(var(--text-primary))] rounded-md font-bold text-xs uppercase tracking-wide shadow-2xl hover:translate-y-[-4px] active:scale-95 transition-all flex items-center justify-center gap-4 group"
                                >
                                    {isAssigning ? <Loader2 className="animate-spin" /> : <UserCheck size={20} className="group-hover:rotate-12 transition-transform" />}
                                    Confirmar Misión
                                </button>
                            </div>
                        </motion.div>
                    ) : (
                        <div className="h-full flex flex-col items-center justify-center p-4 text-center space-y-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/5 rounded-lg border-2 border-dashed border-[hsl(var(--border))] dark:border-white/10">
                            <div className="size-10 rounded-lg bg-[hsl(var(--surface-1))] dark:bg-white/10 shadow-2xl flex items-center justify-center text-[hsl(var(--text-secondary))]"><User size={64} strokeWidth={1} /></div>
                            <div className="space-y-2">
                                <h4 className="text-base font-bold text-[hsl(var(--text-primary))] dark:text-white uppercase tracking-tight">Esperando selección</h4>
                                <p className="text-sm text-[hsl(var(--text-secondary))] font-medium max-w-[240px] mx-auto leading-relaxed">Selecciona un persona de la congregación para iniciar el proceso de asignación pastoral.</p>
                            </div>
                        </div>
                    )}
                </AnimatePresence>
            </div>
        </div>
        </CrmShell>
    );
}
