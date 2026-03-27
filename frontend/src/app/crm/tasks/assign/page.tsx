"use client";

import React, { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import {
    Search,
    Bell,
    Clock,
    UserCheck,
    Link2,
    Users
} from 'lucide-react';
import CrmShell from '@/components/crm/CrmShell';
import AdminHero from '@/components/admin/AdminHero';
import CommunityToolbarChip from '@/components/community/ToolbarChip';
import CommunityQuickCommentCard from '@/components/community/QuickCommentCard';
import CommunityListRow from '@/components/community/ListRow';

interface Prospect {
    id: string;
    name: string;
    interest: string;
    avatar: string;
    priority: 'Alta' | 'Media' | 'Baja';
}

const priorityTone: Record<'Alta' | 'Media' | 'Baja', string> = {
    Alta: 'bg-rose-100 text-rose-600 border-rose-200',
    Media: 'bg-amber-100 text-amber-600 border-amber-200',
    Baja: 'bg-slate-100 text-slate-500 border-slate-200'
};

const accentTone: Record<'Alta' | 'Media' | 'Baja', string> = {
    Alta: 'bg-rose-400',
    Media: 'bg-amber-400',
    Baja: 'bg-slate-400'
};

export default function TaskAssignment() {
    const { isAuthenticated } = useAuth();
    const router = useRouter();
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedProspectId, setSelectedProspectId] = useState<string | null>(null);
    const [selectedLeader, setSelectedLeader] = useState('');
    const [assignmentMessage, setAssignmentMessage] = useState<string | null>(null);

    const prospects = useMemo<Prospect[]>(() => [
        {
            id: '1',
            name: 'Marta Gómez',
            interest: 'Interesada en curso de bautismo',
            avatar: 'https://i.pravatar.cc/150?u=10',
            priority: 'Alta'
        },
        {
            id: '2',
            name: 'Ricardo Ruiz',
            interest: 'Consulta sobre grupos familiares',
            avatar: 'https://i.pravatar.cc/150?u=11',
            priority: 'Media'
        }
    ], []);

    const filteredProspects = useMemo(
        () =>
            prospects.filter((prospect) =>
                prospect.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                prospect.interest.toLowerCase().includes(searchQuery.toLowerCase())
            ),
        [prospects, searchQuery]
    );

    useEffect(() => {
        if (!filteredProspects.length) {
            setSelectedProspectId(null);
            return;
        }
        if (!selectedProspectId || !filteredProspects.some((prospect) => prospect.id === selectedProspectId)) {
            setSelectedProspectId(filteredProspects[0].id);
        }
    }, [filteredProspects, selectedProspectId]);

    useEffect(() => {
        if (!assignmentMessage) return;
        const timeout = setTimeout(() => setAssignmentMessage(null), 3000);
        return () => clearTimeout(timeout);
    }, [assignmentMessage]);

    const selectedProspect = filteredProspects.find((prospect) => prospect.id === selectedProspectId) ?? null;

    const handleAssign = () => {
        if (!selectedProspect || !selectedLeader) {
            setAssignmentMessage('Selecciona un líder para continuar.');
            return;
        }
        setAssignmentMessage(`Asignado ${selectedProspect.name} a ${selectedLeader}.`);
        setSelectedLeader('');
    };

    if (!isAuthenticated) return null;

    const heroWatchers = ['Coord. Voluntarios', 'Optimus Brain'];

    return (
        <CrmShell
            breadcrumbs={[{ label: 'CCF', icon: Users }, { label: 'CRM Pastoral', icon: Users }, { label: 'Asignación', icon: UserCheck }]}
            rightActions={
                <button className="flex size-10 items-center justify-center rounded-full bg-white/5 text-slate-400 hover:text-white transition-all relative">
                    <Bell size={20} />
                    <span className="absolute top-3 right-3 size-2 bg-primary rounded-full ring-2 ring-slate-950"></span>
                </button>
            }
        >
        <AdminHero
            eyebrow="Distribución"
            title="Asignación de tareas"
            description="Prioriza prospectos y asigna líderes para darle seguimiento con IA que balancea cargas."
            tags={['Leads', 'Voluntariado', 'IA']}
            watchers={heroWatchers}
            primaryAction={{ label: 'Ver pipeline', icon: Link2, onClick: () => router.push('/crm/pipeline') }}
            secondaryAction={{ label: 'Agregar líder', icon: UserCheck, onClick: () => {} }}
        />
            <section className="mb-4">
                <div className="relative group">
                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-primary transition-colors" size={18} />
                    <input
                        type="text"
                        placeholder="Buscar contactos pendientes..."
                        className="w-full bg-slate-900/40 border border-white/5 rounded-2xl py-4 pl-12 pr-4 text-sm font-medium focus:ring-2 focus:ring-primary/40 focus:border-primary/40 transition-all outline-none backdrop-blur-xl"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                    />
                </div>
            </section>

            <section className="space-y-6 bg-white text-slate-900 rounded-[2.5rem] p-6 shadow-[0_30px_120px_rgba(15,23,42,0.35)]">
                <div className="flex flex-wrap items-center gap-2">
                    <CommunityToolbarChip label="Pendientes" active variant="solid" />
                    <CommunityToolbarChip label="Asignadas" />
                    <CommunityToolbarChip label="Urgentes" icon={Clock} />
                </div>

                <CommunityQuickCommentCard
                    title="Registra contexto antes de asignar líderes"
                    description="Menciona al responsable o adjunta notas para entregar todo el contexto." />

                <div className="rounded-2xl border border-slate-200 overflow-hidden">
                    <div className="grid grid-cols-[32px_minmax(0,2.4fr)_1.4fr_1.2fr_1fr_0.9fr_0.9fr] items-center gap-4 px-6 py-3 text-[10px] font-semibold uppercase tracking-[0.3em] text-slate-400 bg-slate-50">
                        <div className="text-center">#</div>
                        {['Prospecto', 'Responsable', 'Interés', 'Prioridad', 'Estado', 'Comentarios'].map((header) => (
                            <div key={header}>{header}</div>
                        ))}
                    </div>
                    {filteredProspects.map((prospect, index) => (
                        <CommunityListRow
                            key={prospect.id}
                            index={index}
                            item={{
                                id: prospect.id,
                                name: prospect.name,
                                owner: selectedProspectId === prospect.id ? 'Seleccionando…' : 'Sin asignar',
                                due: '—',
                                priority: prospect.priority,
                                status: 'Pendiente',
                                comments: '0 comentarios',
                                stage: prospect.interest
                            }}
                            accentClass={accentTone[prospect.priority]}
                            priorityClass={priorityTone[prospect.priority]}
                            statusClass="bg-slate-100 text-slate-600 border-slate-200"
                            className={selectedProspectId === prospect.id ? 'bg-[hsl(var(--surface-2))]' : ''}
                            onClick={() => setSelectedProspectId(prospect.id)}
                        />
                    ))}
                </div>
            </section>

            {selectedProspect && (
                <section className="rounded-[2.5rem] border border-white/10 bg-slate-900/60 backdrop-blur-xl p-6 space-y-6">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.3em]">Asignando a</p>
                            <h3 className="text-2xl font-black text-white">{selectedProspect.name}</h3>
                            <p className="text-sm text-slate-400">{selectedProspect.interest}</p>
                        </div>
                        <CommunityToolbarChip
                            label={`Prioridad ${selectedProspect.priority}`}
                            variant="solid"
                            className="bg-slate-900 text-white border-slate-900"
                        />
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <label className="text-[10px] font-bold uppercase tracking-[0.3em] text-slate-500 space-y-2">
                            Líder responsable
                            <select
                                value={selectedLeader}
                                onChange={(event) => setSelectedLeader(event.target.value)}
                                className="w-full bg-slate-950/50 border border-white/10 rounded-2xl py-4 px-5 text-sm font-semibold text-white appearance-none"
                            >
                                <option value="">Seleccionar líder...</option>
                                <option value="Pastor Juan">Pastor Juan - 5 tareas activas</option>
                                <option value="Líder Elena">Líder Elena - 2 tareas activas</option>
                                <option value="Diác. Marcos">Diác. Marcos - 8 tareas activas</option>
                            </select>
                        </label>
                        <label className="text-[10px] font-bold uppercase tracking-[0.3em] text-slate-500 space-y-2">
                            Nota
                            <textarea
                                rows={3}
                                placeholder="Agrega contexto para el líder"
                                className="w-full bg-slate-950/40 border border-white/10 rounded-2xl py-3 px-5 text-sm text-white"
                            />
                        </label>
                    </div>

                    <div className="flex items-center justify-between gap-4">
                        {assignmentMessage && (
                            <p className="text-sm text-slate-300">{assignmentMessage}</p>
                        )}
                        <button
                            type="button"
                            onClick={handleAssign}
                            className="ml-auto px-6 py-3 rounded-2xl bg-primary text-white text-[10px] font-black uppercase tracking-[0.3em] flex items-center gap-2"
                        >
                            <UserCheck size={16} /> Confirmar asignación
                        </button>
                    </div>
                </section>
            )}
        </CrmShell>
    );
}
