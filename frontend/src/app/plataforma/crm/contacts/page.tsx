"use client";

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { useCrmAccess } from '@/hooks/useCrmAccess';
import { extractErrorMessage, apiFetch } from '@/lib/http';
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
        default:             return 'bg-[hsl(var(--surface-2))]/10 text-[hsl(var(--text-secondary))] border-[hsl(var(--border))]/20';
    }
}
function getStatusDot(stage: string) {
    switch (stage) {
        case 'new':          return 'bg-[hsl(var(--primary))]';
        case 'call':         return 'bg-amber-500';
        case 'visit':        return 'bg-sky-500';
        case 'discipleship': return 'bg-[hsl(var(--primary))]';
        case 'consolidated': return 'bg-emerald-500';
        default:             return 'bg-[hsl(var(--surface-2))]';
    }
}

export default function ContactsPage() {
    const { token } = useAuth();
    const { canEditCrm } = useCrmAccess();
    const { addToast } = useToast();
    const router = useRouter();

    const [leads, setLeads] = useState<Array<{ id: string; nombre_completo?: string; source?: string; phone?: string; telefono?: string; stage?: string; created_at?: string }>>([]);
    const [loading, setLoading] = useState(true);
    const [leadsError, setLeadsError] = useState<string | null>(null);
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
        if (!token) {
            setLoading(false);
            return;
        }
        setLoading(true);
        setLeadsError(null);
        try {
            const data = await apiFetch<Array<{ id: string; nombre_completo?: string; source?: string; phone?: string; telefono?: string; stage?: string; created_at?: string }> | { cases?: Array<{ id: string; nombre_completo?: string; source?: string; phone?: string; telefono?: string; stage?: string; created_at?: string }> }>('/crm/casos', { token, cache: 'no-store' });
            const items = Array.isArray(data) ? data : Array.isArray(data?.cases) ? data.cases : [];
            setLeads(items);
        } catch (err) {
            setLeads([]);
            const message = extractErrorMessage(err, 'Error al cargar contactos');
            setLeadsError(message);
            addToast(message, 'error');
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
        const map: Record<string, typeof filtered> = { new: [], call: [], visit: [], discipleship: [], consolidated: [] };
        for (const lead of filtered) {
            const stage = lead.stage || 'new';
            if (!map[stage]) map[stage] = [];
            map[stage].push(lead);
        }
        return map;
    }, [filtered]);

    const groupedByDate = useMemo(() => {
        const map: Record<string, { label: string; items: typeof filtered }> = {};
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
            rightActions={canEditCrm ? (
                <button
                    onClick={() => setIsCreateOpen(true)}
                    className="flex items-center gap-2 px-3 py-2 bg-[hsl(var(--primary))] text-white rounded-md text-[11px] font-bold uppercase tracking-wide shadow-xl shadow-blue-500/20 active:scale-95 transition-all"
                >
                    <Plus size={14} /> Nuevo Contacto
                </button>
            ) : undefined}
        >
            <div className="flex flex-col h-full overflow-hidden">
                {leadsError && (
                    <div className="mx-4 mt-4 rounded-lg border border-amber-300/60 bg-amber-50 dark:bg-amber-500/10 dark:border-amber-500/30 p-3 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                        <div className="min-w-0">
                            <p className="text-[11px] font-bold uppercase tracking-wide text-amber-800 dark:text-amber-200">
                                No se pudo cargar el pipeline de contactos
                            </p>
                            <p className="text-sm text-amber-900/80 dark:text-amber-100/80 mt-1 break-words">
                                {leadsError}
                            </p>
                        </div>
                        <button
                            onClick={fetchLeads}
                            className="shrink-0 px-3 py-2 rounded-lg bg-[hsl(var(--primary))] text-white text-[10px] font-bold uppercase tracking-wide shadow-lg shadow-blue-500/20 hover:opacity-90 transition-all"
                        >
                            Reintentar
                        </button>
                    </div>
                )}
                {/* Toolbar */}
                <div className="px-4 py-2 border-b border-[hsl(var(--border))] dark:border-white/5 space-y-3">
                    <div className="relative">
                        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" size={16} />
                        <input
                            type="text"
                            placeholder="Buscar por nombre o fuente..."
                            className="w-full bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg py-1.5 pl-11 pr-4 text-sm font-medium focus:ring-2 focus:ring-blue-500/20 outline-none dark:text-white transition-all"
                            value={searchQuery}
                            onChange={e => setSearchQuery(e.target.value)}
                        />
                    </div>
                    <div className="flex gap-2 overflow-x-auto pb-1">
                        <button
                            onClick={() => setActiveFilter('all')}
                            className={`px-4 py-1.5 rounded-full text-[10px] font-bold uppercase tracking-wide transition-all border whitespace-nowrap ${activeFilter === 'all' ? 'bg-[hsl(var(--primary))] text-white border-blue-600' : 'bg-[hsl(var(--surface-1))] dark:bg-white/5 text-[hsl(var(--text-secondary))] border-[hsl(var(--border))] dark:border-white/10'}`}
                        >
                            Todos ({leads.length})
                        </button>
                        {PIPELINE_STAGES.map(s => (
                            <button
                                key={s}
                                onClick={() => setActiveFilter(s)}
                                className={`px-4 py-1.5 rounded-full text-[10px] font-bold uppercase tracking-wide transition-all border whitespace-nowrap ${activeFilter === s ? 'bg-[hsl(var(--primary))] text-white border-blue-600' : 'bg-[hsl(var(--surface-1))] dark:bg-white/5 text-[hsl(var(--text-secondary))] border-[hsl(var(--border))] dark:border-white/10'}`}
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
                    ) : !leadsError && filtered.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-1.5 text-center space-y-4">
                            <div className="size-10 rounded-full bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center text-[hsl(var(--text-secondary))] border border-[hsl(var(--border))] dark:border-white/10">
                                <Search size={40} />
                            </div>
                            <h4 className="text-[hsl(var(--text-primary))] dark:text-white font-bold text-sm">No hay contactos</h4>
                            <p className="text-[hsl(var(--text-secondary))] text-sm max-w-[200px]">Agrega un nuevo contacto o ajusta los filtros.</p>
                            {canEditCrm && (
                                <button
                                    onClick={() => setIsCreateOpen(true)}
                                    className="px-4 py-1.5 bg-[hsl(var(--primary))] text-white rounded-md text-xs font-bold uppercase tracking-wide shadow-lg shadow-blue-500/20"
                                >
                                    Agregar Contacto
                                </button>
                            )}
                        </div>
                    ) : ['list', 'grid'].includes(viewType) ? filtered.map(lead => {
                        const stage = lead.stage ?? 'new';
                        return (
                        <div
                            key={lead.id}
                            onClick={() => router.push(`/plataforma/crm/contacts/${lead.id}`)}
                            className="bg-[hsl(var(--surface-1))] dark:bg-white/5 backdrop-blur-xl border border-[hsl(var(--border))] dark:border-white/10 rounded-md p-3 hover:border-blue-300 dark:hover:border-blue-700 transition-all group cursor-pointer shadow-sm hover:shadow-xl"
                        >
                            <div className="flex justify-between items-start mb-4">
                                <div className="flex gap-4">
                                    <div className="relative">
                                        <div className="size-8 rounded-lg bg-blue-500/10 dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 flex items-center justify-center text-[hsl(var(--primary))] dark:text-white font-bold text-sm uppercase group-hover:border-blue-400 transition-colors">
                                            {lead.nombre_completo?.charAt(0) || ''}{(lead.nombre_completo?.split(/\s+/).filter(Boolean).slice(-1)[0]?.[0]) || ''}
                                        </div>
                                        <div className={`absolute -bottom-1 -right-1 size-3.5 rounded-full border-2 border-white dark:border-[#1e1f21] ${getStatusDot(stage)}`} />
                                    </div>
                                    <div>
                                        <h3 className="font-bold text-[hsl(var(--text-primary))] dark:text-white text-base tracking-tight group-hover:text-[hsl(var(--primary))] transition-colors">
                                            {lead.nombre_completo || ''}
                                        </h3>
                                        <p className="text-[11px] text-[hsl(var(--text-secondary))] font-medium">
                                            {lead.source || 'Sin fuente'} · {(lead.telefono ?? lead.phone) || 'Sin teléfono'}
                                        </p>
                                    </div>
                                </div>
                                <span className={`px-3 py-1 rounded-lg text-[10px] font-bold uppercase tracking-wide border ${getStatusStyles(stage)}`}>
                                    {STAGE_LABELS[stage] || stage}
                                </span>
                            </div>
                            <div className="flex items-center justify-between pt-4 border-t border-[hsl(var(--border))] dark:border-white/5">
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
                        );
                    }) : ['board', 'kanban'].includes(viewType) ? (
                        <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
                            {PIPELINE_STAGES.map(stage => (
                                <div key={stage} className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))]/60 dark:bg-white/[0.03] p-3">
                                    <div className="mb-3 flex items-center justify-between">
                                        <span className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{STAGE_LABELS[stage]}</span>
                                        <span className="text-[10px] font-bold text-[hsl(var(--text-secondary))]">{groupedByStage[stage]?.length ?? 0}</span>
                                    </div>
                                    <div className="space-y-2">
                                        {(groupedByStage[stage] ?? []).map(lead => {
                                            return (
                                            <button key={lead.id} onClick={() => router.push(`/plataforma/crm/contacts/${lead.id}`)} className="w-full rounded-md border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 px-3 py-2 text-left hover:border-blue-300 dark:hover:border-blue-700 transition-all">
                                                <p className="text-xs font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{lead.nombre_completo || ''}</p>
                                                <p className="text-[10px] text-[hsl(var(--text-secondary))]">{(lead.telefono ?? lead.phone) || 'Sin teléfono'}</p>
                                            </button>
                                            );
                                        })}
                                        {(groupedByStage[stage] ?? []).length === 0 && (
                                            <div className="py-2 text-center text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Vacío</div>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : viewType === 'calendar' ? (
                        <div className="space-y-4">
                            {groupedByDate.length === 0 ? (
                                <div className="rounded-lg border border-dashed border-[hsl(var(--border))] dark:border-white/10 p-3 text-center text-[hsl(var(--text-secondary))]">
                                    <Calendar size={24} className="mx-auto mb-2" />
                                    Sin actividad para mostrar
                                </div>
                            ) : groupedByDate.map(([dateKey, payload]) => (
                                <div key={dateKey} className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 p-4">
                                    <p className="mb-3 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{payload.label}</p>
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                        {payload.items.map(lead => {
                                            const stage = lead.stage ?? 'new';
                                            return (
                                            <button key={lead.id} onClick={() => router.push(`/plataforma/crm/contacts/${lead.id}`)} className="rounded-md border border-[hsl(var(--border))] dark:border-white/10 px-3 py-2 text-left hover:border-blue-300 dark:hover:border-blue-700 transition-all">
                                                <p className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{lead.nombre_completo || ''}</p>
                                                <p className="text-[10px] text-[hsl(var(--text-secondary))]">{STAGE_LABELS[stage] || stage}</p>
                                            </button>
                                            );
                                        })}
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : viewType === 'gantt' ? (
                        <div className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 p-4 space-y-3">
                            <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]"><BarChart3 size={12} /> Progreso por contacto</div>
                            {filtered.map(lead => {
                                const stage = lead.stage ?? 'new';
                                return (
                                <div key={lead.id} className="space-y-1">
                                    <div className="flex items-center justify-between text-[11px]">
                                        <span className="font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{lead.nombre_completo || ''}</span>
                                        <span className="font-bold text-[hsl(var(--text-secondary))]">{STAGE_PROGRESS[stage] ?? 0}%</span>
                                    </div>
                                    <div className="h-2 rounded-full bg-[hsl(var(--surface-2))] dark:bg-white/10 overflow-hidden">
                                        <div className="h-full bg-[hsl(var(--primary))]" style={{ width: `${STAGE_PROGRESS[stage] ?? 0}%` }} />
                                    </div>
                                </div>
                                );
                            })}
                            {!leadsError && filtered.length === 0 && <div className="py-1.5 text-center text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Sin datos</div>}
                        </div>
                    ) : viewType === 'table' ? (
                        <div className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 overflow-x-auto">
                            <table className="w-full text-left min-w-[520px]">
                                <thead className="bg-[hsl(var(--surface-1))] dark:bg-white/5">
                                    <tr>
                                        <th className="px-4 py-1.5 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Nombre</th>
                                        <th className="px-4 py-1.5 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Fuente</th>
                                        <th className="px-4 py-1.5 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Telefono</th>
                                        <th className="px-4 py-1.5 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Etapa</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {filtered.map(lead => {
                                        const stage = lead.stage ?? 'new';
                                        return (
                                        <tr key={lead.id} onClick={() => router.push(`/plataforma/crm/contacts/${lead.id}`)} className="cursor-pointer border-t border-[hsl(var(--border))] dark:border-white/5 hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/[0.02]">
                                            <td className="px-4 py-1.5 text-sm font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{lead.nombre_completo || ''}</td>
                                            <td className="px-4 py-1.5 text-xs text-[hsl(var(--text-secondary))]">{lead.source || 'Sin fuente'}</td>
                                            <td className="px-4 py-1.5 text-xs text-[hsl(var(--text-secondary))]">{(lead.telefono ?? lead.phone) || 'Sin telefono'}</td>
                                            <td className="px-4 py-1.5 text-xs text-[hsl(var(--text-secondary))]">{STAGE_LABELS[stage] || stage}</td>
                                        </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    ) : viewType === 'wiki' ? (
                        <div className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 p-4 space-y-3">
                            <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]"><BookOpen size={12} /> Wiki de contactos</div>
                            <textarea
                                value={wikiNotes}
                                onChange={(e) => setWikiNotes(e.target.value)}
                                placeholder="Documenta políticas de seguimiento, guiones de llamada y estándares de consolidación..."
                                className="w-full min-h-[360px] rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-black/20 p-4 text-sm font-medium text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] outline-none focus:ring-2 focus:ring-blue-500/20"
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
                        <button type="button" onClick={() => setIsCreateOpen(false)} className="px-4 py-2 text-[11px] font-bold text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]">
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
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <label className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Nombre *</label>
                            <input
                                required
                                value={newLead.first_name}
                                onChange={e => setNewLead({ ...newLead, first_name: e.target.value })}
                                placeholder="Juan"
                                className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-black/20 outline-none focus:ring-2 focus:ring-blue-500/20 font-bold text-sm dark:text-white"
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Apellido</label>
                            <input
                                value={newLead.last_name}
                                onChange={e => setNewLead({ ...newLead, last_name: e.target.value })}
                                placeholder="Pérez"
                                className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-black/20 outline-none focus:ring-2 focus:ring-blue-500/20 font-bold text-sm dark:text-white"
                            />
                        </div>
                    </div>
                    <div className="space-y-2">
                        <label className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Teléfono</label>
                        <input
                            value={newLead.phone}
                            onChange={e => setNewLead({ ...newLead, phone: e.target.value })}
                            placeholder="+57 300 123 4567"
                            className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-black/20 outline-none focus:ring-2 focus:ring-blue-500/20 font-bold text-sm dark:text-white"
                        />
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <label className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Fuente</label>
                            <select
                                value={newLead.source}
                                onChange={e => setNewLead({ ...newLead, source: e.target.value })}
                                className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-black/20 outline-none focus:ring-2 focus:ring-blue-500/20 font-bold text-sm dark:text-white appearance-none"
                            >
                                {SOURCE_OPTS.map(s => <option key={s} value={s}>{s}</option>)}
                            </select>
                        </div>
                        <div className="space-y-2">
                            <label className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Etapa inicial</label>
                            <select
                                value={newLead.stage}
                                onChange={e => setNewLead({ ...newLead, stage: e.target.value })}
                                className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-black/20 outline-none focus:ring-2 focus:ring-blue-500/20 font-bold text-sm dark:text-white appearance-none"
                            >
                                {PIPELINE_STAGES.map(s => <option key={s} value={s}>{STAGE_LABELS[s]}</option>)}
                            </select>
                        </div>
                    </div>
                    <div className="space-y-2">
                        <label className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Notas</label>
                        <textarea
                            value={newLead.notes}
                            onChange={e => setNewLead({ ...newLead, notes: e.target.value })}
                            placeholder="Contexto del contacto inicial..."
                            rows={3}
                            className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-black/20 outline-none focus:ring-2 focus:ring-blue-500/20 font-bold text-sm dark:text-white resize-none"
                        />
                    </div>
                </form>
            </WorkspaceDrawer>
        </CrmShell>
    );
}
