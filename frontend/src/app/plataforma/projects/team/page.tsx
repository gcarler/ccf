"use client";

import React, { useEffect, useState } from 'react';
import {
    Users, AlertTriangle,
    ChevronRight, UserPlus, UserMinus, Loader2
} from 'lucide-react';
import { motion } from 'framer-motion';
import clsx from 'clsx';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import ProjectsShell from '@/components/projects/ProjectsShell';
import { DSSkeleton } from '@/design';
import EmptyState from '@/components/ui/EmptyState';
import RightPanel from '@/components/ui/RightPanel';
import PersonaSelect from '@/components/ui/PersonaSelect';
import { useSidebarLayers } from '@/context/SidebarLayerContext';
import { toast } from 'sonner';
import type { ProjectRecord } from '@/types/projects';

interface TeamPersona {
    persona_id: string;
    name: string;
    load_status: string;
    open: number;
    critical: number;
    capacity_percent: number;
}

interface ProjectMemberItem {
    id: string;
    project_id: string;
    persona_id: string;
    role: string;
    invited_at?: string | null;
    persona_name?: string | null;
}

export default function TeamPage() {
    const { token, loading: authLoading } = useAuth();
    const { openLayer, closeLayer, setRightMode, layers } = useSidebarLayers();
    const [team, setTeam] = useState<TeamPersona[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [selectedPersona, setSelectedPersona] = useState<TeamPersona | null>(null);
    const [showInvite, setShowInvite] = useState(false);
    const [inviteProjectId, setInviteProjectId] = useState('');
    const [invitePersonaId, setInvitePersonaId] = useState<string | null>(null);
    const [inviting, setInviting] = useState(false);
    const [projects, setProjects] = useState<ProjectRecord[]>([]);
    const [members, setMembers] = useState<Record<string, ProjectMemberItem[]>>({});
    // View mode: 'workload' = global ministerial workload; 'members' = members of a specific project.
    const [viewMode, setViewMode] = useState<'workload' | 'members'>('workload');
    const [selectedProjectId, setSelectedProjectId] = useState('');
    const [removingId, setRemovingId] = useState<string | null>(null);

    useEffect(() => {
        if (!layers.RIGHT && selectedPersona) setSelectedPersona(null);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [layers.RIGHT]);

    useEffect(() => {
        if (authLoading) return;
        if (!token) {
            setLoading(false);
            setTeam([]);
            setError('Debes iniciar sesión para ver el equipo del proyecto.');
            return;
        }
        setError(null);
        apiFetch<TeamPersona[]>('/system/workload', { token })
            .then(data => setTeam(Array.isArray(data) ? data : []))
            .catch(() => {
                setTeam([]);
                setError('No se pudo cargar el equipo del proyecto.');
            })
            .finally(() => setLoading(false));
        // Cargar la lista de proyectos para el selector de vista de miembros.
        apiFetch<ProjectRecord[]>('/projects', { token })
            .then(data => setProjects(Array.isArray(data) ? data : []))
            .catch(() => setProjects([]));
    }, [authLoading, token]);

    // Cargar miembros reales del proyecto seleccionado vía GET /projects/{id}/team.
    useEffect(() => {
        if (!token || viewMode !== 'members' || !selectedProjectId) return;
        apiFetch<ProjectMemberItem[]>(`/projects/${selectedProjectId}/team`, { token })
            .then(data => setMembers(prev => ({ ...prev, [selectedProjectId]: Array.isArray(data) ? data : [] })))
            .catch(() => setMembers(prev => ({ ...prev, [selectedProjectId]: [] })));
    }, [token, viewMode, selectedProjectId]);

    const handleSelect = (persona: TeamPersona) => {
        setSelectedPersona(persona);
        setRightMode('overlay');
        openLayer('RIGHT');
    };

    const openInvite = () => {
        setInviteProjectId(viewMode === 'members' && selectedProjectId ? selectedProjectId : (projects[0]?.id ?? ''));
        setInvitePersonaId(null);
        setShowInvite(true);
    };

    const handleInvite = async () => {
        if (!token) return;
        if (!inviteProjectId || !invitePersonaId) {
            toast.error('Selecciona proyecto y persona para invitar');
            return;
        }
        setInviting(true);
        try {
            const member = await apiFetch<ProjectMemberItem>(`/projects/${inviteProjectId}/team`, {
                method: 'POST', token, body: { persona_id: invitePersonaId },
            });
            setMembers(prev => ({ ...prev, [inviteProjectId]: [...(prev[inviteProjectId] ?? []), member] }));
            toast.success('Persona invitada al equipo');
            setShowInvite(false);
            setInvitePersonaId(null);
        } catch {
            toast.error('No se pudo invitar a la persona');
        } finally {
            setInviting(false);
        }
    };

    const handleRemoveMember = async (projectId: string, personaId: string) => {
        if (!token) return;
        setRemovingId(personaId);
        try {
            await apiFetch(`/projects/${projectId}/team/${personaId}`, { method: 'DELETE', token });
            setMembers(prev => ({
                ...prev,
                [projectId]: (prev[projectId] ?? []).filter(m => m.persona_id !== personaId),
            }));
            toast.success('Integrante removido del equipo');
        } catch {
            toast.error('No se pudo remover al integrante');
        } finally {
            setRemovingId(null);
        }
    };

    return (
        <ProjectsShell
            breadcrumbs={[{ label: 'Proyectos', icon: Users }, { label: 'Equipo', icon: Users }]}
        >
            <div className="flex-1 flex flex-col font-display">
                <div className="w-full mx-auto p-3 space-y-3 pb-4">
                    {error && (
                        <div className="rounded-lg border border-[hsl(var(--warning)/25%)] bg-warning-soft p-3 text-warning-text dark:border-[hsl(var(--warning)/100%)]/20 dark:bg-[hsl(var(--warning))]/10 dark:text-[hsl(var(--warning))]">
                            <p className="text-xs font-bold uppercase tracking-wide">{error}</p>
                        </div>
                    )}

                    {/* View mode switcher + project selector */}
                    <div className="flex items-center gap-2 flex-wrap">
                        <button
                            onClick={() => { setViewMode('workload'); }}
                            className={clsx(
                                'px-3 py-1 rounded-full text-2xs font-bold uppercase tracking-wide border transition-colors',
                                viewMode === 'workload'
                                    ? 'bg-[hsl(var(--primary))] text-white border-[hsl(var(--primary))]'
                                    : 'border-[hsl(var(--border))] dark:border-white/10 text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5'
                            )}
                        >
                            Carga global
                        </button>
                        <button
                            onClick={() => { setViewMode('members'); setSelectedProjectId(projects[0]?.id ?? ''); }}
                            className={clsx(
                                'px-3 py-1 rounded-full text-2xs font-bold uppercase tracking-wide border transition-colors',
                                viewMode === 'members'
                                    ? 'bg-[hsl(var(--primary))] text-white border-[hsl(var(--primary))]'
                                    : 'border-[hsl(var(--border))] dark:border-white/10 text-[hsl(var(--secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5'
                            )}
                        >
                            Miembros por proyecto
                        </button>
                        {viewMode === 'members' && (
                            <select
                                value={selectedProjectId}
                                onChange={(e) => setSelectedProjectId(e.target.value)}
                                className="bg-[hsl(var(--surface-1))] dark:bg-black/20 border border-[hsl(var(--border))] dark:border-white/5 rounded-md px-3 py-1.5 text-sm font-medium outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]/20 transition-all text-[hsl(var(--text-primary))] dark:text-white"
                            >
                                {projects.length === 0 && <option value="">Sin proyectos</option>}
                                {projects.map((p) => (
                                    <option key={p.id} value={p.id}>{p.title}</option>
                                ))}
                            </select>
                        )}
                    </div>

                    {/* Sub-header */}
                    <div className="flex items-center justify-between">
                        <div>
                            <div className="flex items-center gap-2 mb-1">
                                <div className="size-7 rounded-lg bg-info-soft dark:bg-[hsl(var(--info))]/30 flex items-center justify-center">
                                    <Users size={14} className="text-[hsl(var(--primary))]" />
                                </div>
                                <span className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--primary))]">Recursos Humanos</span>
                            </div>
                            <h1 className="text-xl font-bold tracking-tight text-[hsl(var(--text-primary))] dark:text-white leading-none">
                                {viewMode === 'workload' ? 'Equipo del Proyecto' : 'Miembros del Proyecto'}
                            </h1>
                            <p className="text-sm text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] mt-0.5 font-medium">
                                {viewMode === 'workload'
                                    ? 'Disponibilidad y saturación del equipo ministerial en tiempo real.'
                                    : 'Personas asignadas al proyecto seleccionado.'}
                            </p>
                        </div>
                        <div className="flex items-center gap-3">
                            {viewMode === 'workload' && !loading && team.length > 0 && (
                                <div className="px-4 py-2 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-1))] rounded-md border border-[hsl(var(--border))] dark:border-white/[0.06] shadow-sm text-center">
                                    <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Cap. Prom.</p>
                                    <p className="text-sm font-semibold text-[hsl(var(--primary))]">
                                        {Math.round(team.reduce((a, m) => a + m.capacity_percent, 0) / team.length)}%
                                    </p>
                                </div>
                            )}
                            {viewMode === 'members' && selectedProjectId && (members[selectedProjectId]?.length ?? 0) > 0 && (
                                <div className="px-4 py-2 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-1))] rounded-md border border-[hsl(var(--border))] dark:border-white/[0.06] shadow-sm text-center">
                                    <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Miembros</p>
                                    <p className="text-sm font-semibold text-[hsl(var(--primary))]">
                                        {members[selectedProjectId].length}
                                    </p>
                                </div>
                            )}
                            <button
                                onClick={openInvite}
                                disabled={viewMode === 'members' && !selectedProjectId}
                                className="flex items-center gap-2 px-4 py-1.5 bg-[hsl(var(--primary))] text-white rounded-lg text-xs font-semibold uppercase tracking-wide shadow-xl shadow-[hsl(var(--info)/20%)] hover:bg-[hsl(var(--primary))] active:scale-95 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                <UserPlus size={13} /> Invitar
                            </button>
                        </div>
                    </div>
                    {loading && viewMode === 'workload' ? (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                            {[...Array(6)].map((_, i) => <DSSkeleton key={i} className="h-48 rounded-lg" />)}
                        </div>
                    ) : viewMode === 'members' ? (
                        !selectedProjectId ? (
                            <EmptyState
                                icon={Users}
                                title="Selecciona un proyecto"
                                description="Elige un proyecto del selector para ver las personas asignadas a su equipo."
                            />
                        ) : (members[selectedProjectId] === undefined ? (
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                                {[...Array(3)].map((_, i) => <DSSkeleton key={i} className="h-32 rounded-lg" />)}
                            </div>
                        ) : members[selectedProjectId].length === 0 ? (
                            <EmptyState
                                icon={Users}
                                title="Sin miembros en este proyecto"
                                description="Invita colaboradores a este proyecto para que aparezcan aquí."
                            />
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                                {members[selectedProjectId].map((member, idx) => (
                                    <motion.div
                                        key={member.id}
                                        initial={{ opacity: 0, scale: 0.97 }}
                                        animate={{ opacity: 1, scale: 1 }}
                                        transition={{ delay: idx * 0.05 }}
                                        className="group relative bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-1))] rounded-lg border border-[hsl(var(--border))]/70 dark:border-white/[0.06] p-3 shadow-sm transition-all overflow-hidden"
                                    >
                                        <div className="absolute top-0 left-0 right-0 h-[3px] bg-[hsl(var(--info))]" />
                                        <div className="flex items-start justify-between mb-3">
                                            <div className="flex items-center gap-3">
                                                <div className="size-8 rounded-md bg-[hsl(var(--surface-2))] dark:bg-white/10 flex items-center justify-center text-[hsl(var(--text-secondary))] shadow-sm font-bold text-xs">
                                                    {(member.persona_name ?? member.persona_id).substring(0, 2).toUpperCase()}
                                                </div>
                                                <div>
                                                    <p className="text-base font-medium text-[hsl(var(--text-primary))] dark:text-white leading-none">
                                                        {member.persona_name ?? 'Sin nombre'}
                                                    </p>
                                                    <span className="text-2xs font-semibold uppercase tracking-wide mt-0.5 block text-[hsl(var(--text-secondary))]">
                                                        {member.role}
                                                    </span>
                                                </div>
                                            </div>
                                        </div>
                                        <div className="p-2 bg-[hsl(var(--surface-1))] dark:bg-black/20 rounded-md mb-3">
                                            <p className="text-2xs font-bold uppercase text-[hsl(var(--text-secondary))] mb-0.5">Invitado</p>
                                            <p className="text-sm font-medium text-[hsl(var(--text-primary))] dark:text-white">
                                                {member.invited_at
                                                    ? new Date(member.invited_at).toLocaleDateString('es', { day: 'numeric', month: 'short', year: 'numeric' })
                                                    : '—'}
                                            </p>
                                        </div>
                                        <button
                                            onClick={() => handleRemoveMember(selectedProjectId, member.persona_id)}
                                            disabled={removingId === member.persona_id}
                                            className="w-full py-1.5 text-2xs font-bold uppercase tracking-wide text-[hsl(var(--danger))] border border-[hsl(var(--danger))]/30 rounded-md hover:bg-[hsl(var(--danger))]/10 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-1.5"
                                        >
                                            {removingId === member.persona_id ? <Loader2 className="animate-spin" size={12} /> : <UserMinus size={12} />}
                                            {removingId === member.persona_id ? 'Removiendo...' : 'Remover del proyecto'}
                                        </button>
                                    </motion.div>
                                ))}
                            </div>
                        ))
                    ) : !error && team.length === 0 ? (
                        <EmptyState
                            icon={Users}
                            title="No hay personas en el equipo"
                            description="Invita colaboradores al proyecto para visualizar su carga y disponibilidad aquí."
                        />
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                            {team.map((persona, idx) => {
                                const isOverloaded = persona.load_status === 'sobrecargado';
                                return (
                                    <motion.div
                                        key={persona.persona_id}
                                        initial={{ opacity: 0, scale: 0.97 }}
                                        animate={{ opacity: 1, scale: 1 }}
                                        transition={{ delay: idx * 0.05 }}
                                        onClick={() => handleSelect(persona)}
                                        className="group relative bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-1))] rounded-lg border border-[hsl(var(--border))]/70 dark:border-white/[0.06] p-3 shadow-sm hover:shadow-xl hover:shadow-black/10/60 dark:hover:shadow-black/30 transition-all cursor-pointer overflow-hidden active:scale-[0.99]"
                                    >
                                        {/* Status bar */}
                                        <div className={clsx(
                                            "absolute top-0 left-0 right-0 h-[3px]",
                                            isOverloaded ? "bg-[hsl(var(--danger))]" :
                                            persona.load_status === 'en_capacidad' ? "bg-[hsl(var(--warning))]" : "bg-[hsl(var(--success))]"
                                        )} />

                                        <div className="flex items-start justify-between mb-3">
                                            <div className="flex items-center gap-3">
                                                <div className="size-8 rounded-md bg-[hsl(var(--surface-2))] dark:bg-white/10 flex items-center justify-center text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] group-hover:bg-[hsl(var(--primary))] group-hover:text-white transition-all shadow-sm font-bold text-xs">
                                                    {persona.name.substring(0, 2).toUpperCase()}
                                                </div>
                                                <div>
                                                    <p className="text-base font-medium text-[hsl(var(--text-primary))] dark:text-white leading-none">{persona.name}</p>
                                                    <span className={clsx(
                                                        "text-2xs font-semibold uppercase tracking-wide mt-0.5 block",
                                                        isOverloaded ? "text-[hsl(var(--danger))]" : "text-[hsl(var(--text-secondary))]"
                                                    )}>{persona.load_status}</span>
                                                </div>
                                            </div>
                                            {isOverloaded && <AlertTriangle className="text-[hsl(var(--danger))] shrink-0" size={16} />}
                                        </div>

                                        <div className="grid grid-cols-2 gap-2 mb-3">
                                            <div className="p-2 bg-[hsl(var(--surface-1))] dark:bg-black/20 rounded-md">
                                                <p className="text-2xs font-bold uppercase text-[hsl(var(--text-secondary))] mb-0.5">Activas</p>
                                                <p className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white">{persona.open}</p>
                                            </div>
                                            <div className="p-2 bg-[hsl(var(--surface-1))] dark:bg-black/20 rounded-md">
                                                <p className="text-2xs font-bold uppercase text-[hsl(var(--text-secondary))] mb-0.5">Criticas</p>
                                                <p className={clsx("text-lg font-bold", persona.critical > 0 ? "text-[hsl(var(--danger))]" : "text-[hsl(var(--text-primary))] dark:text-white")}>
                                                    {persona.critical}
                                                </p>
                                            </div>
                                        </div>

                                        <div className="space-y-1.5">
                                            <div className="flex items-center justify-between text-2xs font-semibold uppercase tracking-wide">
                                                <span className="text-[hsl(var(--text-secondary))]">Saturación</span>
                                                <span className={isOverloaded ? "text-[hsl(var(--danger))]" : "text-[hsl(var(--primary))]"}>{persona.capacity_percent}%</span>
                                            </div>
                                            <div className="h-1.5 w-full bg-[hsl(var(--surface-2))] dark:bg-white/5 rounded-full overflow-hidden">
                                                <motion.div
                                                    initial={{ width: 0 }}
                                                    animate={{ width: `${persona.capacity_percent}%` }}
                                                    transition={{ duration: 0.8, delay: idx * 0.05 + 0.3 }}
                                                    className={clsx("h-full rounded-full", isOverloaded ? "bg-[hsl(var(--danger))]" : "bg-[hsl(var(--primary))]")}
                                                />
                                            </div>
                                        </div>

                                        <div className="mt-4 opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1 text-2xs font-semibold uppercase text-[hsl(var(--primary))] tracking-wide">
                                            Ver detalle <ChevronRight size={11} />
                                        </div>
                                    </motion.div>
                                );
                            })}
                        </div>
                    )}
                </div>
            </div>

            {/* Right Panel — Persona Detail (no modal) */}
            {selectedPersona && (
                <RightPanel title="Perfil de Carga" width={360}>
                    <div className="p-3 space-y-3">
                        <div className="flex items-center gap-3">
                            <div className="size-10 rounded-md bg-[hsl(var(--primary))] flex items-center justify-center text-white font-bold text-sm shadow-lg shadow-[hsl(var(--info)/20%)]">
                                {selectedPersona.name.substring(0, 2).toUpperCase()}
                            </div>
                            <div>
                                <h3 className="text-sm font-medium text-[hsl(var(--text-primary))] dark:text-white">{selectedPersona.name}</h3>
                                <span className={clsx(
                                    "text-2xs font-semibold uppercase tracking-wide",
                                    selectedPersona.load_status === 'sobrecargado' ? "text-[hsl(var(--danger))]" : "text-[hsl(var(--success))]"
                                )}>{selectedPersona.load_status}</span>
                            </div>
                        </div>

                        <div className="grid grid-cols-2 gap-3">
                            {[
                                { label: 'Tareas Activas', value: selectedPersona.open, color: 'text-[hsl(var(--primary))]' },
                                { label: 'Criticas Hoy', value: selectedPersona.critical, color: 'text-[hsl(var(--danger))]' },
                                { label: 'Saturacion', value: `${selectedPersona.capacity_percent}%`, color: selectedPersona.capacity_percent > 80 ? 'text-[hsl(var(--danger))]' : 'text-[hsl(var(--primary))]' },
                                { label: 'Estado', value: selectedPersona.load_status === 'disponible' ? 'Disponible' : 'Ocupado', color: 'text-[hsl(var(--success))]' },
                            ].map(item => (
                                <div key={item.label} className="bg-[hsl(var(--surface-1))] dark:bg-white/5 rounded-md p-2 border border-[hsl(var(--border))] dark:border-white/5">
                                    <p className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{item.label}</p>
                                    <p className={clsx("text-lg font-bold mt-0.5", item.color)}>{item.value}</p>
                                </div>
                            ))}
                        </div>

                        <button
                            onClick={() => closeLayer('RIGHT')}
                            className="w-full py-2 border border-[hsl(var(--border))] dark:border-white/10 rounded-md text-xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 transition-all"
                        >
                            Cerrar
                        </button>
                    </div>
                </RightPanel>
            )}

            {/* Right Panel — Invitar al equipo (F4) */}
            <RightPanel
                title="Invitar al Equipo"
                width={380}
                open={showInvite}
                onClose={() => setShowInvite(false)}
            >
                <div className="p-3 space-y-4">
                    <p className="text-sm text-[hsl(var(--text-secondary))] leading-relaxed">
                        Agrega una persona de la sede al equipo de un proyecto para que colabore y aparezca en la carga de trabajo.
                    </p>

                    <div className="space-y-1.5">
                        <label className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                            Proyecto
                        </label>
                        <select
                            value={inviteProjectId}
                            onChange={(e) => setInviteProjectId(e.target.value)}
                            className="w-full bg-[hsl(var(--surface-1))] dark:bg-black/20 border border-[hsl(var(--border))] dark:border-white/5 rounded-md px-3 py-2 text-sm font-medium outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]/20 transition-all text-[hsl(var(--text-primary))] dark:text-white"
                        >
                            {projects.length === 0 && <option value="">Sin proyectos disponibles</option>}
                            {projects.map((p) => (
                                <option key={p.id} value={p.id}>{p.title}</option>
                            ))}
                        </select>
                    </div>

                    <div className="space-y-1.5">
                        <label className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                            Persona
                        </label>
                        <PersonaSelect
                            value={invitePersonaId}
                            onChange={(v) => setInvitePersonaId(v)}
                            placeholder="Seleccionar persona"
                        />
                    </div>

                    {inviteProjectId && (members[inviteProjectId]?.length ?? 0) > 0 && (
                        <div className="space-y-1.5">
                            <p className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                                Ya en el equipo ({members[inviteProjectId].length})
                            </p>
                            <ul className="space-y-1">
                                {members[inviteProjectId].map((m) => (
                                    <li key={m.id} className="flex items-center justify-between px-2.5 py-1.5 rounded-md bg-[hsl(var(--surface-1))] dark:bg-black/20 border border-[hsl(var(--border))] dark:border-white/5 text-sm font-medium text-[hsl(var(--text-primary))] dark:text-white">
                                        <span>{m.persona_name ?? m.persona_id}</span>
                                        <span className="text-2xs uppercase tracking-wide text-[hsl(var(--text-secondary))]">{m.role}</span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}

                    <button
                        onClick={handleInvite}
                        disabled={inviting || !inviteProjectId || !invitePersonaId}
                        className="w-full py-2 bg-[hsl(var(--primary))] text-white rounded-md text-xs font-bold uppercase tracking-wide shadow-lg shadow-[hsl(var(--info)/20%)] hover:bg-[hsl(var(--primary))] active:scale-95 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                    >
                        {inviting ? <Loader2 className="animate-spin" size={12} /> : <UserPlus size={12} />}
                        {inviting ? 'Invitando...' : 'Invitar al equipo'}
                    </button>
                </div>
            </RightPanel>
        </ProjectsShell>
    );
}
