"use client";

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import { useWikiDocument } from '@/hooks/useWikiDocument';
import { Search, UserPlus, Phone, MessageSquare, Link2, Users, Plus, Loader2, Send, Calendar, BarChart3, BookOpen } from 'lucide-react';
import CrmShell from '@/components/crm/CrmShell';
import Skeleton from '@/components/ui/Skeleton';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import { ViewType, getStoredView } from '@/components/ViewSwitcher';
import CrmViewPlaceholder from '@/components/crm/CrmViewPlaceholder';

const PIPELINE_STAGES = ['new', 'call', 'visit', 'discipleship', 'consolidated'];
const STAGE_LABELS: Record<string, string> = {
    new: 'Nuevo',
    call: 'Por Llamar',
    visit: 'Visita',
    discipleship: 'Discipulado',
    consolidated: 'Consolidado',
};
const SOURCE_OPTS = ['Visitante', 'Formulario Web', 'Redes Sociales', 'Invitado Directo', 'Evento', 'Referido'];
const STAGE_PROGRESS: Record<string, number> = { new: 20, call: 40, visit: 60, discipleship: 80, consolidated: 100 };

function getStatusStyles(stage: string) {
    switch (stage) {
        case 'new':          return 'bg-blue-500/10 text-[hsl(var(--primary))] border-blue-500/20';
        case 'call':         return 'bg-amber-500/10 text-amber-600 border-amber-500/20';
        case 'visit':        return 'bg-sky-500/10 text-sky-600 border-sky-500/20';
        case 'discipleship': return 'bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))] border-[hsl(var(--primary))]/20';
        case 'consolidated': return 'bg-emerald-500/10 text-emerald-600 border-emerald-500/20';
        default:             return 'bg-slate-500/10 text-slate-400 border-slate-500/20';
    }
}
function getStatusDot(stage: string) {
    switch (stage) {
        case 'new':          return 'bg-[hsl(var(--primary))]';
        case 'call':         return 'bg-amber-500';
        case 'visit':        return 'bg-sky-500';
        case 'discipleship': return 'bg-[hsl(var(--primary))]';
        case 'consolidated': return 'bg-emerald-500';
        default:             return 'bg-slate-400';
    }
}

export default function ContactsPage() {
    const { token } = useAuth();
    const { addToast } = useToast();
    const router = useRouter();

    const [leads, setLeads] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [viewType, setViewType] = useState<ViewType>(() => getStoredView('crm_contacts_view', 'list'));
    const [searchQuery, setSearchQuery] = useState('');
    const [activeFilter, setActiveFilter] = useState('all');
    const { content: wikiNotes, setContent: setWikiNotes } = useWikiDocument('crm_contacts_wiki_notes', {
        title: 'Wiki de contactos CRM',
    });

    // Create drawer
    const [isCreateOpen, setIsCreateOpen] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const [newLead, setNewLead] = useState({
        first_name: '', last_name: '', phone: '', source: 'Visitante', stage: 'new', notes: ''
    });

    const fetchLeads = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const data = await apiFetch<any[]>('/crm/consolidation/cases', { token, cache: 'no-store' });
            setLeads(Array.isArray(data) ? data : []);
        } catch {
            addToast('Error al cargar contactos', 'error');
        } finally {
            setLoading(false);
        }
    }, [token, addToast]);

    useEffect(() => { fetchLeads(); }, [fetchLeads]);


    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!newLead.first_name.trim()) return;
        setIsSaving(true);
        try {
            await apiFetch('/crm/personas/', {
                method: 'POST', token,
                body: {
                    first_name: newLead.first_name,
                    last_name: newLead.last_name,
                    phone: newLead.phone,
                    source: newLead.source,
                    spiritual_status: 'Prospecto',
                }
            });
            addToast('Contacto registrado exitosamente', 'success');
            setIsCreateOpen(false);
            setNewLead({ first_name: '', last_name: '', phone: '', source: 'Visitante', stage: 'new', notes: '' });
            fetchLeads();
        } catch {
            addToast('Error al registrar contacto', 'error');
        } finally {
            setIsSaving(false);
        }
    };

    const filtered = leads.filter(lead => {
        const name = (lead.nombre_completo || '').toLowerCase();
        const matchesSearch = name.includes(searchQuery.toLowerCase()) ||
            (lead.source || '').toLowerCase().includes(searchQuery.toLowerCase());
        const matchesFilter = activeFilter === 'all' || lead.stage === activeFilter;
        return matchesSearch && matchesFilter;
    });

    const groupedByStage = useMemo(() => {
        const map: Record<string, any[]> = { new: [], call: [], visit: [], discipleship: [], consolidated: [] };
        for (const lead of filtered) {
            if (!map[lead.stage]) map[lead.stage] = [];
            map[lead.stage].push(lead);
        }
        return map;
    }, [filtered]);

    const groupedByDate = useMemo(() => {
        const map: Record<string, { label: string; items: any[] }> = {};
        for (const lead of filtered) {
            const date = lead.created_at ? new Date(lead.created_at) : new Date();
            const isoKey = date.toISOString().slice(0, 10);
            const label = date.toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: 'numeric' });
            if (!map[isoKey]) map[isoKey] = { label, items: [] };
            map[isoKey].items.push(lead);
        }
        return Object.entries(map).sort((a, b) => b[0].localeCompare(a[0]));
    }, [filtered]);

    return (
        <CrmShell
            breadcrumbs={[
                { label: 'Consolidación', icon: Users },
                { label: 'Contactos / Leads', icon: UserPlus }
            ]}
            viewOptions={['table', 'list', 'grid', 'board', 'kanban', 'gantt', 'calendar', 'wiki']}
            viewType={viewType}
            onViewChange={setViewType}
            rightActions={
                <button
                    onClick={() => setIsCreateOpen(true)}
                    className="flex items-center gap-2 px-3 py-2 bg-[hsl(var(--primary))] text-white rounded-md text-[11px] font-bold uppercase tracking-wide shadow-xl shadow-blue-500/20 active:scale-95 transition-all"
                >
                    <Plus size={14} /> Nuevo Contacto
                </button>
            }
        >
            <div className="flex flex-col h-full overflow-hidden">
                {/* Toolbar */}
                <div className="px-4 py-2 border-b border-slate-100 dark:border-white/5 space-y-3">
                    <div className="relative">
                        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
                        <input
                            type="text"
                            placeholder="Buscar por nombre o fuente..."
                            className="w-full bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg py-1.5 pl-11 pr-4 text-sm font-medium focus:ring-2 focus:ring-blue-500/20 outline-none dark:text-white transition-all"
                            value={searchQuery}
                            onChange={e => setSearchQuery(e.target.value)}
                        />
                    </div>
                    <div className="flex gap-2 overflow-x-auto pb-1">
                        <button
                            onClick={() => setActiveFilter('all')}
                            className={`px-4 py-1.5 rounded-full text-[10px] font-bold uppercase tracking-wide transition-all border whitespace-nowrap ${activeFilter === 'all' ? 'bg-[hsl(var(--primary))] text-white border-blue-600' : 'bg-[hsl(var(--surface-1))] dark:bg-white/5 text-slate-400 border-slate-200 dark:border-white/10'}`}
                        >
                            Todos ({leads.length})
                        </button>
                        {PIPELINE_STAGES.map(s => (
                            <button
                                key={s}
                                onClick={() => setActiveFilter(s)}
                                className={`px-4 py-1.5 rounded-full text-[10px] font-bold uppercase tracking-wide transition-all border whitespace-nowrap ${activeFilter === s ? 'bg-[hsl(var(--primary))] text-white border-blue-600' : 'bg-[hsl(var(--surface-1))] dark:bg-white/5 text-slate-400 border-slate-200 dark:border-white/10'}`}
                            >
                                {STAGE_LABELS[s]} ({leads.filter(l => l.stage === s).length})
                            </button>
                        ))}
                    </div>
                </div>

                {/* List */}
                <div className="flex-1 overflow-y-auto p-4 space-y-3">
                    {loading ? (
                        [...Array(5)].map((_, i) => <Skeleton key={i} className="h-24 w-full rounded-md" />)
                    ) : filtered.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-1.5 text-center space-y-4">
                            <div className="size-10 rounded-full bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-300 border border-slate-200 dark:border-white/10">
                                <Search size={40} />
                            </div>
                            <h4 className="text-slate-800 dark:text-white font-bold text-sm">No hay contactos</h4>
                            <p className="text-slate-400 text-sm max-w-[200px]">Agrega un nuevo contacto o ajusta los filtros.</p>
                            <button
                                onClick={() => setIsCreateOpen(true)}
                                className="px-4 py-1.5 bg-[hsl(var(--primary))] text-white rounded-md text-xs font-bold uppercase tracking-wide shadow-lg shadow-blue-500/20"
                            >
                                Agregar Contacto
                            </button>
                        </div>
                    ) : ['list', 'grid'].includes(viewType) ? filtered.map(lead => (
                        <div
                            key={lead.id}
                            onClick={() => router.push(`/plataforma/crm/contacts/${lead.id}`)}
                            className="bg-[hsl(var(--surface-1))] dark:bg-white/5 backdrop-blur-xl border border-slate-200 dark:border-white/10 rounded-md p-3 hover:border-blue-300 dark:hover:border-blue-700 transition-all group cursor-pointer shadow-sm hover:shadow-xl"
                        >
                            <div className="flex justify-between items-start mb-4">
                                <div className="flex gap-4">
                                    <div className="relative">
                                        <div className="size-8 rounded-lg bg-blue-500/10 dark:bg-white/5 border border-slate-200 dark:border-white/10 flex items-center justify-center text-[hsl(var(--primary))] dark:text-white font-bold text-sm uppercase group-hover:border-blue-400 transition-colors">
                                            {lead.nombre_completo?.charAt(0) || ''}{(lead.nombre_completo?.split(/\s+/).filter(Boolean).slice(-1)[0]?.[0]) || ''}
                                        </div>
                                        <div className={`absolute -bottom-1 -right-1 size-3.5 rounded-full border-2 border-white dark:border-[#1e1f21] ${getStatusDot(lead.stage)}`} />
                                    </div>
                                    <div>
                                        <h3 className="font-bold text-slate-800 dark:text-white text-base tracking-tight group-hover:text-[hsl(var(--primary))] transition-colors">
                                            {lead.nombre_completo || ''}
                                        </h3>
                                        <p className="text-[11px] text-slate-400 font-medium">
                                            {lead.source || 'Sin fuente'} · {(lead.telefono ?? lead.phone) || 'Sin teléfono'}
                                        </p>
                                    </div>
                                </div>
                                <span className={`px-3 py-1 rounded-lg text-[10px] font-bold uppercase tracking-wide border ${getStatusStyles(lead.stage)}`}>
                                    {STAGE_LABELS[lead.stage] || lead.stage}
                                </span>
                            </div>
                            <div className="flex items-center justify-between pt-4 border-t border-slate-100 dark:border-white/5">
                                <button
                                    onClick={e => { e.stopPropagation(); router.push('/plataforma/crm/pipeline'); }}
                                    className="text-[hsl(var(--primary))] text-[10px] font-bold uppercase tracking-wide flex items-center gap-2 hover:text-[hsl(var(--primary))] transition-colors"
                                >
                                    <div className="size-5 rounded-lg bg-blue-600/10 flex items-center justify-center">
                                        <Link2 size={11} />
                                    </div>
                                    Ver en Pipeline
                                </button>
                                <div className="flex gap-2">
                                    {(lead.telefono ?? lead.phone) && (
                                        <a
                                            href={`tel:${lead.telefono ?? lead.phone}`}
                                            onClick={e => e.stopPropagation()}
                                            className="size-9 rounded-md bg-emerald-500/10 text-emerald-600 flex items-center justify-center hover:bg-emerald-500 hover:text-white transition-all border border-emerald-500/20"
                                        >
                                            <Phone size={15} />
                                        </a>
                                    )}
                                    <button
                                        onClick={e => { e.stopPropagation(); }}
                                        className="size-9 rounded-md bg-blue-500/10 text-[hsl(var(--primary))] flex items-center justify-center hover:bg-[hsl(var(--primary))] hover:text-white transition-all border border-blue-500/20"
                                    >
                                        <MessageSquare size={15} />
                                    </button>
                                </div>
                            </div>
                        </div>
                    )) : ['board', 'kanban'].includes(viewType) ? (
                        <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
                            {PIPELINE_STAGES.map(stage => (
                                <div key={stage} className="rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50/60 dark:bg-white/[0.03] p-3">
                                    <div className="mb-3 flex items-center justify-between">
                                        <span className="text-[10px] font-bold uppercase tracking-wide text-slate-500">{STAGE_LABELS[stage]}</span>
                                        <span className="text-[10px] font-bold text-slate-400">{groupedByStage[stage]?.length ?? 0}</span>
                                    </div>
                                    <div className="space-y-2">
                                        {(groupedByStage[stage] ?? []).map(lead => (
                                            <button key={lead.id} onClick={() => router.push(`/plataforma/crm/contacts/${lead.id}`)} className="w-full rounded-md border border-slate-200 dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 px-3 py-2 text-left hover:border-blue-300 dark:hover:border-blue-700 transition-all">
                                                <p className="text-xs font-bold text-slate-800 dark:text-slate-100">{lead.nombre_completo || ''}</p>
                                                <p className="text-[10px] text-slate-400">{(lead.telefono ?? lead.phone) || 'Sin teléfono'}</p>
                                            </button>
                                        ))}
                                        {(groupedByStage[stage] ?? []).length === 0 && (
                                            <div className="py-2 text-center text-[10px] font-bold uppercase tracking-wide text-slate-400">Vacío</div>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : viewType === 'calendar' ? (
                        <div className="space-y-4">
                            {groupedByDate.length === 0 ? (
                                <div className="rounded-lg border border-dashed border-slate-200 dark:border-white/10 p-3 text-center text-slate-400">
                                    <Calendar size={24} className="mx-auto mb-2" />
                                    Sin actividad para mostrar
                                </div>
                            ) : groupedByDate.map(([dateKey, payload]) => (
                                <div key={dateKey} className="rounded-lg border border-slate-200 dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 p-4">
                                    <p className="mb-3 text-[10px] font-bold uppercase tracking-wide text-slate-500">{payload.label}</p>
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                        {payload.items.map(lead => (
                                            <button key={lead.id} onClick={() => router.push(`/plataforma/crm/contacts/${lead.id}`)} className="rounded-md border border-slate-200 dark:border-white/10 px-3 py-2 text-left hover:border-blue-300 dark:hover:border-blue-700 transition-all">
                                                <p className="text-sm font-bold text-slate-800 dark:text-slate-100">{lead.nombre_completo || ''}</p>
                                                <p className="text-[10px] text-slate-400">{STAGE_LABELS[lead.stage] || lead.stage}</p>
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : viewType === 'gantt' ? (
                        <div className="rounded-lg border border-slate-200 dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 p-4 space-y-3">
                            <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-wide text-slate-500"><BarChart3 size={12} /> Progreso por contacto</div>
                            {filtered.map(lead => (
                                <div key={lead.id} className="space-y-1">
                                    <div className="flex items-center justify-between text-[11px]">
                                        <span className="font-bold text-slate-700 dark:text-slate-300">{lead.nombre_completo || ''}</span>
                                        <span className="font-bold text-slate-400">{STAGE_PROGRESS[lead.stage] ?? 0}%</span>
                                    </div>
                                    <div className="h-2 rounded-full bg-slate-100 dark:bg-white/10 overflow-hidden">
                                        <div className="h-full bg-[hsl(var(--primary))]" style={{ width: `${STAGE_PROGRESS[lead.stage] ?? 0}%` }} />
                                    </div>
                                </div>
                            ))}
                            {filtered.length === 0 && <div className="py-1.5 text-center text-[10px] font-bold uppercase tracking-wide text-slate-400">Sin datos</div>}
                        </div>
                    ) : viewType === 'table' ? (
                        <div className="rounded-lg border border-slate-200 dark:border-white/10 overflow-hidden">
                            <table className="w-full text-left">
                                <thead className="bg-slate-50 dark:bg-white/5">
                                    <tr>
                                        <th className="px-4 py-1.5 text-[10px] font-bold uppercase tracking-wide text-slate-400">Nombre</th>
                                        <th className="px-4 py-1.5 text-[10px] font-bold uppercase tracking-wide text-slate-400">Fuente</th>
                                        <th className="px-4 py-1.5 text-[10px] font-bold uppercase tracking-wide text-slate-400">Telefono</th>
                                        <th className="px-4 py-1.5 text-[10px] font-bold uppercase tracking-wide text-slate-400">Etapa</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {filtered.map(lead => (
                                        <tr key={lead.id} onClick={() => router.push(`/plataforma/crm/contacts/${lead.id}`)} className="cursor-pointer border-t border-slate-100 dark:border-white/5 hover:bg-slate-50 dark:hover:bg-white/[0.02]">
                                            <td className="px-4 py-1.5 text-sm font-bold text-slate-800 dark:text-slate-100">{lead.nombre_completo || ''}</td>
                                            <td className="px-4 py-1.5 text-xs text-slate-500">{lead.source || 'Sin fuente'}</td>
                                            <td className="px-4 py-1.5 text-xs text-slate-500">{(lead.telefono ?? lead.phone) || 'Sin telefono'}</td>
                                            <td className="px-4 py-1.5 text-xs text-slate-500">{STAGE_LABELS[lead.stage] || lead.stage}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    ) : viewType === 'wiki' ? (
                        <div className="rounded-lg border border-slate-200 dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 p-4 space-y-3">
                            <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-wide text-slate-500"><BookOpen size={12} /> Wiki de contactos</div>
                            <textarea
                                value={wikiNotes}
                                onChange={(e) => setWikiNotes(e.target.value)}
                                placeholder="Documenta políticas de seguimiento, guiones de llamada y estándares de consolidación..."
                                className="w-full min-h-[360px] rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 p-4 text-sm font-medium text-slate-700 dark:text-slate-200 outline-none focus:ring-2 focus:ring-blue-500/20"
                            />
                        </div>
                    ) : (
                        <CrmViewPlaceholder moduleName="Contactos / Leads" viewType={viewType} />
                    )}
                </div>
            </div>

            {/* ─── Drawer: Nuevo Contacto ─── */}
            <WorkspaceDrawer
                isOpen={isCreateOpen}
                onClose={() => setIsCreateOpen(false)}
                title="Nuevo Contacto"
                subtitle="Registrar prospecto en el pipeline pastoral"
                actions={
                    <>
                        <button type="button" onClick={() => setIsCreateOpen(false)} className="px-4 py-2 text-[11px] font-bold text-slate-500 hover:text-slate-700">
                            Cancelar
                        </button>
                        <button
                            form="create-contact-form"
                            type="submit"
                            disabled={isSaving}
                            className="px-3 py-2 bg-[hsl(var(--primary))] text-white rounded-lg text-[11px] font-bold uppercase tracking-wide shadow-lg shadow-blue-500/20 hover:bg-[hsl(var(--primary))] active:scale-95 transition-all flex items-center gap-2"
                        >
                            {isSaving ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
                            Registrar
                        </button>
                    </>
                }
            >
                <form id="create-contact-form" onSubmit={handleCreate} className="space-y-2">
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">Nombre *</label>
                            <input
                                required
                                value={newLead.first_name}
                                onChange={e => setNewLead({ ...newLead, first_name: e.target.value })}
                                placeholder="Juan"
                                className="w-full px-4 py-1.5 rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 outline-none focus:ring-2 focus:ring-blue-500/20 font-bold text-sm dark:text-white"
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">Apellido</label>
                            <input
                                value={newLead.last_name}
                                onChange={e => setNewLead({ ...newLead, last_name: e.target.value })}
                                placeholder="Pérez"
                                className="w-full px-4 py-1.5 rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 outline-none focus:ring-2 focus:ring-blue-500/20 font-bold text-sm dark:text-white"
                            />
                        </div>
                    </div>
                    <div className="space-y-2">
                        <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">Teléfono</label>
                        <input
                            value={newLead.phone}
                            onChange={e => setNewLead({ ...newLead, phone: e.target.value })}
                            placeholder="+57 300 123 4567"
                            className="w-full px-4 py-1.5 rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 outline-none focus:ring-2 focus:ring-blue-500/20 font-bold text-sm dark:text-white"
                        />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">Fuente</label>
                            <select
                                value={newLead.source}
                                onChange={e => setNewLead({ ...newLead, source: e.target.value })}
                                className="w-full px-4 py-1.5 rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 outline-none focus:ring-2 focus:ring-blue-500/20 font-bold text-sm dark:text-white appearance-none"
                            >
                                {SOURCE_OPTS.map(s => <option key={s} value={s}>{s}</option>)}
                            </select>
                        </div>
                        <div className="space-y-2">
                            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">Etapa inicial</label>
                            <select
                                value={newLead.stage}
                                onChange={e => setNewLead({ ...newLead, stage: e.target.value })}
                                className="w-full px-4 py-1.5 rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 outline-none focus:ring-2 focus:ring-blue-500/20 font-bold text-sm dark:text-white appearance-none"
                            >
                                {PIPELINE_STAGES.map(s => <option key={s} value={s}>{STAGE_LABELS[s]}</option>)}
                            </select>
                        </div>
                    </div>
                    <div className="space-y-2">
                        <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">Notas</label>
                        <textarea
                            value={newLead.notes}
                            onChange={e => setNewLead({ ...newLead, notes: e.target.value })}
                            placeholder="Contexto del contacto inicial..."
                            rows={3}
                            className="w-full px-4 py-1.5 rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 outline-none focus:ring-2 focus:ring-blue-500/20 font-bold text-sm dark:text-white resize-none"
                        />
                    </div>
                </form>
            </WorkspaceDrawer>
        </CrmShell>
    );
}

