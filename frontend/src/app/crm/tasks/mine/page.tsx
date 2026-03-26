"use client";

import React, { useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { Search, Calendar, History, Link2, Plus, Users } from 'lucide-react';
import CrmShell from '@/components/crm/CrmShell';
import AdminHero from '@/components/admin/AdminHero';
import CommunityToolbarChip from '@/components/community/ToolbarChip';
import CommunityQuickCommentCard from '@/components/community/QuickCommentCard';
import CommunityListRow from '@/components/community/ListRow';
import { formatDueLabel } from '@/lib/community/utils';

interface Task {
    id: string;
    contactName: string;
    contactAvatar: string;
    type: string;
    status: 'Pendiente' | 'Atrasada' | 'Completada';
    priority: 'Alta' | 'Media' | 'Baja';
    dueDate: string;
}

const priorityTone: Record<'Alta' | 'Media' | 'Baja', string> = {
    Alta: 'bg-rose-100 text-rose-600 border-rose-200',
    Media: 'bg-amber-100 text-amber-600 border-amber-200',
    Baja: 'bg-slate-100 text-slate-500 border-slate-200'
};

const statusTone: Record<Task['status'], string> = {
    Pendiente: 'bg-slate-100 text-slate-600 border-slate-200',
    Atrasada: 'bg-rose-100 text-rose-600 border-rose-200',
    Completada: 'bg-emerald-100 text-emerald-600 border-emerald-200'
};

const typeAccent: Record<string, string> = {
    'Llamada de Bienvenida': 'bg-indigo-400',
    'Visita Domiciliaria': 'bg-amber-400',
    'Seguimiento Consolidación': 'bg-emerald-400'
};

export default function MyTasks() {
    const { isAuthenticated } = useAuth();
    const router = useRouter();
    const [activeTab, setActiveTab] = useState('pending');

    const tasks = useMemo<Task[]>(() => [
        {
            id: '1',
            contactName: 'Carlos Méndez',
            contactAvatar: 'https://i.pravatar.cc/150?u=20',
            type: 'Llamada de Bienvenida',
            status: 'Pendiente',
            priority: 'Alta',
            dueDate: 'Hoy'
        },
        {
            id: '2',
            contactName: 'Elena Rodríguez',
            contactAvatar: 'https://i.pravatar.cc/150?u=21',
            type: 'Visita Domiciliaria',
            status: 'Pendiente',
            priority: 'Media',
            dueDate: 'Mañana'
        },
        {
            id: '3',
            contactName: 'Ricardo Santos',
            contactAvatar: 'https://i.pravatar.cc/150?u=22',
            type: 'Seguimiento Consolidación',
            status: 'Atrasada',
            priority: 'Alta',
            dueDate: 'Ayer'
        }
    ], []);

    const filteredTasks = useMemo(
        () =>
            tasks.filter((task) =>
                activeTab === 'completed' ? task.status === 'Completada' : task.status !== 'Completada'
            ),
        [activeTab, tasks]
    );

    if (!isAuthenticated) return null;

    const heroWatchers = ['Equipo Seguimiento', 'Optimus Brain'];

    return (
        <CrmShell
            breadcrumbs={[{ label: 'CCF', icon: Calendar }, { label: 'CRM Pastoral', icon: Users }, { label: 'Mis tareas', icon: Calendar }]}
            rightActions={
                <button className="flex size-10 items-center justify-center rounded-xl bg-primary/10 text-primary hover:bg-primary/20 transition-all">
                    <Search size={20} />
                </button>
            }
        >
        <AdminHero
            eyebrow="Tareas"
            title="Mis tareas"
            description="Planifica llamadas, visitas y seguimientos con recomendaciones IA antes del lunes de staff."
            tags={['Pastoral', 'IA', 'Seguimiento']}
            watchers={heroWatchers}
            primaryAction={{ label: 'Ver pipeline', icon: Link2, onClick: () => router.push('/crm/pipeline') }}
            secondaryAction={{ label: 'Agregar tarea', icon: Plus, onClick: () => setActiveTab('pending') }}
        />
            {/* Summary Cards */}
            <section className="flex gap-4 mb-10 overflow-x-auto hide-scrollbar">
                        <div className="flex-1 min-w-[140px] bg-gradient-to-br from-primary to-primary-700 rounded-3xl p-6 text-white shadow-xl shadow-primary/20 relative overflow-hidden group">
                            <div className="absolute top-0 right-0 -mr-10 -mt-10 size-32 bg-white/10 rounded-full blur-2xl group-hover:bg-white/20 transition-all"></div>
                            <div className="flex items-center gap-2 mb-4 relative z-10">
                                <Calendar size={14} className="text-blue-200" />
                                <span className="text-[10px] font-black uppercase tracking-widest text-blue-100">Hoy</span>
                            </div>
                            <h3 className="text-4xl font-black mb-1 relative z-10">8</h3>
                            <p className="text-[10px] font-bold text-blue-200 uppercase tracking-widest relative z-10">Tareas asignadas</p>
                        </div>
                        <div className="flex-1 min-w-[140px] bg-slate-900/40 backdrop-blur-xl border border-white/5 rounded-3xl p-6 shadow-xl relative overflow-hidden group">
                            <div className="flex items-center gap-2 mb-4 text-rose-500">
                                <History size={14} />
                                <span className="text-[10px] font-black uppercase tracking-widest">Atrasadas</span>
                            </div>
                            <h3 className="text-4xl font-black text-white mb-1">3</h3>
                            <p className="text-[10px] font-black text-rose-500/60 uppercase tracking-widest">Acción inmediata</p>
                        </div>
                    </section>

                    {/* Vista estilo ClickUp */}
                    <section className="space-y-6 bg-white text-slate-900 rounded-[2.5rem] p-6 shadow-[0_30px_120px_rgba(15,23,42,0.35)]">
                        <div className="flex flex-wrap items-center gap-2">
                            {[
                                { id: 'pending', label: 'Pendientes' },
                                { id: 'completed', label: 'Completadas' }
                            ].map((tab) => (
                                <CommunityToolbarChip
                                    key={tab.id}
                                    label={tab.label}
                                    active={activeTab === tab.id}
                                    variant={activeTab === tab.id ? 'solid' : 'outline'}
                                    onClick={() => setActiveTab(tab.id)}
                                />
                            ))}
                        </div>

                        <CommunityQuickCommentCard
                            title="Agrega notas rápidas para el equipo de seguimiento."
                            description="Usa @menciones para delegar y #etiquetas para agrupar." />

                        <div className="rounded-2xl border border-slate-200 overflow-hidden">
                            <div className="grid grid-cols-[32px_minmax(0,2.4fr)_1.4fr_1.1fr_0.9fr_1fr_0.9fr] items-center gap-4 px-6 py-3 text-[10px] font-semibold uppercase tracking-[0.3em] text-slate-400 bg-slate-50">
                                <div className="text-center">#</div>
                                {['Tarea', 'Asignado', 'Fecha límite', 'Prioridad', 'Estado', 'Comentarios'].map((header) => (
                                    <div key={header}>{header}</div>
                                ))}
                            </div>
                            {filteredTasks.map((task, index) => (
                                <CommunityListRow
                                    key={task.id}
                                    index={index}
                                    item={{
                                        id: task.id,
                                        name: task.type,
                                        owner: task.contactName,
                                        due: formatDueLabel(task.dueDate),
                                        priority: task.priority,
                                        status: task.status,
                                        comments: '0 comentarios',
                                        stage: task.contactName
                                    }}
                                    accentClass={typeAccent[task.type] ?? 'bg-indigo-400'}
                                    priorityClass={priorityTone[task.priority]}
                                    statusClass={statusTone[task.status]}
                                />
                            ))}
                        </div>
                    </section>
        </CrmShell>
    );
}
