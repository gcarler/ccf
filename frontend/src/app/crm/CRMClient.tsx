"use client";

import React, { useState, useEffect, useMemo, useCallback, lazy, Suspense } from 'react';
import { DragEndEvent } from '@dnd-kit/core';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import CrmShell from '@/components/crm/CrmShell';
import AdminHero from '@/components/admin/AdminHero';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import { SectionHeader } from '@/components/ui/SectionHeader';
import MetricCard from '@/components/ui/MetricCard';
import InlineEdit from '@/components/ui/InlineEdit';
import StatusPicker, { StatusOption } from '@/components/ui/StatusPicker';
import Skeleton from '@/components/ui/Skeleton';
import { DSSkeleton } from '@/design';
import { ColumnDef } from '@tanstack/react-table';
import clsx from 'clsx';
import { motion, AnimatePresence } from 'framer-motion';
import { useRegisterCommands } from '@/context/CommandCenterContext';
import {
    Users,
    MessageSquare,
    Target,
    Layout,
    CheckCircle,
    Edit3,
    Calendar,
    Hash,
    Mail,
    Phone,
    History,
    ShieldCheck,
    MapPin,
    Star,
    Sparkles,
    Link2,
    Filter,
    Search,
    MoreHorizontal,
    UserPlus,
    KanbanSquare,
    List as ListIcon,
    Table as TableIcon,
} from 'lucide-react';
import { CrmMember, normalizeMembers } from './types';

const CrmKanbanView = lazy(() => import('@/components/crm/CrmKanbanView'));
const CrmTableView = lazy(() => import('@/components/crm/CrmTableView'));

const MEMBER_STATUS_OPTIONS: StatusOption[] = [
    { label: 'NUEVO', value: 'Nuevo', color: 'bg-blue-500', text: 'text-blue-600 dark:text-blue-400', bg: 'bg-blue-50 dark:bg-blue-900/20' },
    { label: 'CONSOLIDACIÓN', value: 'Consolidación', color: 'bg-indigo-500', text: 'text-indigo-600 dark:text-indigo-400', bg: 'bg-indigo-50 dark:bg-indigo-900/20' },
    { label: 'DISCIPULADO', value: 'Discipulado', color: 'bg-purple-500', text: 'text-purple-600 dark:text-purple-400', bg: 'bg-purple-50 dark:bg-indigo-900/20' },
    { label: 'ACTIVO', value: 'Activo', color: 'bg-emerald-500', text: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-50 dark:bg-emerald-900/20' },
];

type View = 'kanban' | 'table';

interface CRMClientProps {
    initialMembers: CrmMember[];
}

export default function CRMClient({ initialMembers }: CRMClientProps) {
    const { token } = useAuth();
    const { addToast } = useToast();
    const router = useRouter();
    const [viewType, setViewType] = useState<View>('kanban');
    const [selectedMember, setSelectedMember] = useState<CrmMember | null>(null);
    const [isDrawerOpen, setIsDrawerOpen] = useState(false);
    const [members, setMembers] = useState<CrmMember[]>(initialMembers);
    const [isLoading, setIsLoading] = useState(false);
    const [search, setSearch] = useState('');

    useEffect(() => {
        setMembers(initialMembers);
    }, [initialMembers]);

    const syncMembers = useCallback(async () => {
        if (!token) return;
        setIsLoading(true);
        try {
            const data = await apiFetch<any[]>('/crm/members/', { token, cache: 'no-store' });
            setMembers(normalizeMembers(data));
        } catch (err) {
            console.error(err);
            addToast('No pudimos sincronizar el CRM', 'error');
        } finally {
            setIsLoading(false);
        }
    }, [token, addToast]);

    const updateMemberStatus = useCallback(async (id: number, newStatus: string) => {
        setMembers((prev) => prev.map((m) => (m.id === id ? { ...m, status: newStatus } : m)));
        try {
            await apiFetch(`/crm/members/${id}`, { method: 'PATCH', token, body: { status: newStatus } });
            addToast(`Estado: ${newStatus}`, 'success');
        } catch (err) {
            addToast('Error al actualizar', 'error');
            setMembers((prev) => prev.map((m) => (m.id === id ? { ...m, status: 'Nuevo' } : m)));
        }
    }, [token, addToast]);

    const handleDragEnd = async (event: DragEndEvent) => {
        const { active, over } = event;
        if (!over) return;
        const memberId = active.id as number;
        const newStatus = over.id as string;
        const member = members.find((m) => m.id === memberId);
        if (member && member.status !== newStatus) {
            await updateMemberStatus(memberId, newStatus);
        }
    };

    const pipelineData = useMemo(() => (
        MEMBER_STATUS_OPTIONS.map((opt) => ({
            id: opt.value,
            title: opt.label,
            color: opt.color,
            members: members.filter((m) => m.status === opt.value && m.name.toLowerCase().includes(search.toLowerCase())),
        }))
    ), [members, search]);

    const columns = useMemo<ColumnDef<CrmMember>[]>(() => [
        { accessorKey: 'id', header: '#', size: 60, cell: (info) => <span className="text-[11px] font-bold text-slate-400">#{info.getValue() as number}</span> },
        { accessorKey: 'name', header: 'Miembro', cell: ({ row }) => (
            <div className="flex items-center gap-3">
                <div className="size-7 rounded-lg bg-blue-600 flex items-center justify-center text-white text-[10px] font-black">
                    {row.original.name.substring(0, 1)}
                </div>
                <span className="text-[13px] font-bold text-slate-700 dark:text-slate-200">{row.original.name}</span>
            </div>
        ) },
        { accessorKey: 'status', header: 'Etapa', cell: ({ row }) => (
            <StatusPicker currentValue={row.original.status} options={MEMBER_STATUS_OPTIONS} onSelect={(val) => updateMemberStatus(row.original.id, val)} />
        ) },
        { accessorKey: 'group', header: 'Casa de Bendición', cell: (info) => <span className="text-[11px] font-medium text-slate-500">{info.getValue() as string}</span> },
    ], [updateMemberStatus]);

    const handleOpenMember = (member: CrmMember) => {
        setSelectedMember(member);
        setIsDrawerOpen(true);
    };

    const crmBaseCommands = useMemo(() => [
        { id: 'crm-kanban', label: 'Vista embudo (Kanban)', description: 'Seguimiento por etapas', group: 'CRM', action: () => setViewType('kanban') },
        { id: 'crm-table', label: 'Vista tabla', description: 'Listado detallado de miembros', group: 'CRM', action: () => setViewType('table') },
        { id: 'crm-add-member', label: 'Agregar miembro', description: 'Crear perfil y asignar seguimiento', group: 'CRM', action: () => setIsDrawerOpen(true) },
        { id: 'crm-sync', label: 'Sincronizar CRM', description: 'Actualizar datos del embudo', group: 'CRM', action: () => syncMembers() },
        { id: 'crm-go-projects', label: 'Ir a proyectos pastorales', group: 'CRM', action: () => router.push('/projects') },
    ], [router, syncMembers]);

    const crmMemberCommands = useMemo(() => members.slice(0, 6).map((member) => ({
        id: `crm-member-${member.id}`,
        label: member.name,
        description: `Estado: ${member.status}`,
        group: 'Personas',
        action: () => handleOpenMember(member),
    })), [members]);

    const mergedCommands = useMemo(() => [...crmBaseCommands, ...crmMemberCommands], [crmBaseCommands, crmMemberCommands]);

    useRegisterCommands('crm-dashboard', mergedCommands);

    return (
        <>
            <CrmShell
                breadcrumbs={[{ label: 'CCF', icon: Layout }, { label: 'CRM Pastoral', icon: Users }]}
                viewOptions={['kanban', 'table']}
                viewType={viewType}
                onViewChange={(view) => setViewType(view as View)}
                onSearch={setSearch}
                rightActions={
                    <button onClick={syncMembers} className="flex items-center gap-2 px-3 py-1.5 bg-slate-900 text-white rounded-md text-[11px] font-bold hover:bg-black transition-all active:scale-95 shadow-sm">
                        <Sparkles size={14} /> Sincronizar IA
                    </button>
                }
            >
                <AdminHero
                    eyebrow="CRM Pastoral"
                    title="Automatiza la consolidación y el cuidado pastoral"
                    description="Embudos visuales, tablero IA y vistas en tiempo real para saber quién necesita seguimiento. Optimus Brain propone acciones antes de los lunes de staff."
                    tags={['Consolidación', 'IA Pastoral', 'Embudo']}
                    watchers={['Coordinación Pastoral', 'Optimus Brain']}
                    primaryAction={{ label: 'Agregar miembro', icon: UserPlus, onClick: () => setIsDrawerOpen(true) }}
                    secondaryAction={{ label: 'Ver pipeline', icon: Link2, onClick: () => setViewType('kanban') }}
                    commandBar={{
                        title: 'Comando rápido',
                        description: 'Escribe / para asignar visitas o generar notas de seguimiento.',
                        ctaLabel: '/seguimiento',
                        shortcuts: [
                            { label: 'Asignar visita', command: '/asignar visita' },
                            { label: 'Analizar grupos', command: '/insights grupos' },
                            { label: 'Resumen semanal', command: '/resumen crm' },
                        ],
                    }}
                />

                <section className="relative overflow-hidden rounded-[2.5rem] border border-[hsl(var(--border))] bg-white dark:bg-[#111216] shadow-xl">
                    <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_rgba(59,130,246,0.12),transparent)] pointer-events-none" />
                    <div className="relative">
                        <AnimatePresence mode="wait">
                            {isLoading ? (
                                <div className="p-8 space-y-4">
                                    <div className="grid grid-cols-4 gap-4 mb-8">{[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-24 rounded-3xl" />)}</div>
                                    {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-16 w-full rounded-2xl" />)}
                                </div>
                            ) : viewType === 'kanban' ? (
                                <motion.div key="kanban" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="h-full">
                                    <Suspense fallback={<KanbanSkeleton />}>
                                        <CrmKanbanView columns={pipelineData} onDragEnd={handleDragEnd} onOpenMember={handleOpenMember} />
                                    </Suspense>
                                </motion.div>
                            ) : (
                                <motion.div key="table" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="h-full flex flex-col p-6">
                                    <Suspense fallback={<TableSkeleton />}>
                                        <CrmTableView members={members} search={search} columns={columns} onRowClick={handleOpenMember} />
                                    </Suspense>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                </section>
            </CrmShell>

            <WorkspaceDrawer
                isOpen={isDrawerOpen}
                onClose={() => setIsDrawerOpen(false)}
                title={selectedMember?.name || 'Perfil Pastoral'}
                subtitle={selectedMember?.church_role || ''}
                actions={
                    <>
                        <button className="px-4 py-2 text-[11px] font-bold text-slate-500" onClick={() => setIsDrawerOpen(false)}>Cerrar</button>
                        <button className="px-6 py-2 bg-blue-600 text-white rounded-lg text-[11px] font-bold shadow-lg">Agendar Visita</button>
                    </>
                }
            >
                {selectedMember && (
                    <div className="space-y-10 animate-fade-in">
                        <section className="grid grid-cols-2 gap-4">
                            <ProfileStat label="Estado Espiritual" value={selectedMember.status} icon={ShieldCheck} color="text-rose-500" />
                            <ProfileStat label="Sede" value="Central" icon={MapPin} color="text-blue-500" />
                            <ProfileStat label="Grupo Vida" value={selectedMember.group} icon={Users} color="text-indigo-500" />
                            <ProfileStat label="Puntos" value="120" icon={Star} color="text-amber-500" />
                        </section>

                        <section className="space-y-6">
                            <div className="flex items-center justify-between">
                                <h4 className="text-[11px] font-black text-slate-400 uppercase tracking-[0.2em] flex items-center gap-2">
                                    <History size={14} className="text-blue-500" /> Timeline de Crecimiento
                                </h4>
                                <button className="text-[10px] font-black text-blue-600 uppercase tracking-widest hover:underline">+ Añadir Nota</button>
                            </div>
                            <div className="space-y-4 relative before:absolute before:left-[19px] before:top-2 before:bottom-2 before:w-[2px] before:bg-slate-100 dark:before:bg-white/5">
                                <TimelineItem icon={Sparkles} title="Encuentro con Dios" desc="Completó el retiro espiritual de fin de semana." date="Hoy" color="bg-purple-500" />
                                <TimelineItem icon={CheckCircle} title="Inscripción Academia" desc="Inició el curso de Fundamentos I." date="Hace 3 días" color="bg-emerald-500" />
                                <TimelineItem icon={Phone} title="Llamada Pastoral" desc="Se realizó seguimiento telefónico. Muestra mucho interés." date="Hace 1 semana" color="bg-blue-500" />
                            </div>
                        </section>
                    </div>
                )}
            </WorkspaceDrawer>
        </>
    );
}

function ProfileStat({ label, value, icon: Icon, color }: any) {
    return (
        <div className="p-4 bg-slate-50 dark:bg-white/5 border border-slate-100 dark:border-white/5 rounded-2xl group hover:border-blue-500/30 transition-all">
            <div className="flex items-center gap-2 mb-2">
                <Icon size={14} className={color} />
                <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest">{label}</span>
            </div>
            <p className="text-[14px] font-black text-slate-800 dark:text-white truncate">{value}</p>
        </div>
    );
}

function TimelineItem({ icon: Icon, title, desc, date, color }: any) {
    return (
        <div className="flex gap-4 relative z-10">
            <div className={clsx('size-10 rounded-xl flex items-center justify-center text-white shadow-lg shrink-0', color)}>
                <Icon size={18} />
            </div>
            <div className="flex-1 min-w-0">
                <div className="flex justify-between items-center mb-1">
                    <h5 className="text-[13px] font-bold text-slate-800 dark:text-slate-100">{title}</h5>
                    <span className="text-[10px] font-bold text-slate-400">{date}</span>
                </div>
                <p className="text-[12px] text-slate-500 dark:text-slate-400 leading-relaxed">{desc}</p>
            </div>
        </div>
    );
}

function KanbanSkeleton() {
    return (
        <div className="p-6 grid grid-cols-1 md:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
                <DSSkeleton key={i} className="h-[420px] rounded-[2.5rem]" />
            ))}
        </div>
    );
}

function TableSkeleton() {
    return (
        <div className="space-y-3">
            {[...Array(5)].map((_, idx) => (
                <DSSkeleton key={idx} className="h-16 rounded-2xl" />
            ))}
        </div>
    );
}
