'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Users, Plus, Calendar, Clock, Heart, Search, MessageSquare, History, Link2, ShieldCheck, CheckCircle2, XCircle, Loader2, ChevronRight, MoreHorizontal, BookOpen } from 'lucide-react';
import UniversalTableView from '@/components/ui/UniversalTableView';
import { useTheme } from '@/app/plataforma/theme/ThemeContext';
import { extractErrorMessage, apiFetch } from '@/lib/http';
import { useWikiDocument } from '@/hooks/useWikiDocument';
import { useToast } from '@/context/ToastContext';
import { useAuth } from '@/context/AuthContext';
import CrmShell from '@/components/crm/CrmShell';
import { ViewType, getStoredView } from '@/components/ViewSwitcher';
import SplitDropdownButton from '@/components/ui/SplitDropdownButton';
import CrmViewPlaceholder from '@/components/crm/CrmViewPlaceholder';
import { useSidebarLayers } from '@/context/SidebarLayerContext';
import CounselingDetailSidebar from '@/components/crm/CounselingDetailSidebar';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import PersonaSelect from '@/components/ui/PersonaSelect';
import { useRouter } from 'next/navigation';
import { CounselingSession } from '@/types/crm';

const STATUS_ORDER = ['Pendiente', 'Realizada', 'Cancelada'];
const STATUS_PROGRESS: Record<string, number> = { Pendiente: 30, Realizada: 100, Cancelada: 0 };

export default function CounselingPage() {
    const { token } = useAuth();
    const { theme } = useTheme();
    const { addToast } = useToast();
    const router = useRouter();
    const [sessions, setSessions] = useState<CounselingSession[]>([]);
    const [loading, setLoading] = useState(true);
    const [sessionsError, setSessionsError] = useState<string | null>(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [filterStatus, setFilterStatus] = useState('All');
    const { pushSidebarPanel, popSidebarPanel } = useSidebarLayers();
    const [isDrawerOpen, setIsDrawerOpen] = useState(false);   // ← Drawer, NO modal
    const [isSaving, setIsSaving] = useState(false);
    const ALL_VIEWS: ViewType[] = ['table', 'list', 'grid', 'board', 'kanban', 'gantt', 'calendar', 'wiki'];
    const [viewType, setViewType] = useState<ViewType>(() => getStoredView('crm_counseling_view', 'grid'));
    const { content: wikiNotes, setContent: setWikiNotes } = useWikiDocument('crm_counseling_wiki_notes', {
        title: 'Wiki de consejeria CRM',
    });

    const [newSession, setNewSession] = useState({
        pastor_id: null,
        persona_id: '',
        scheduled_at: '',
        topic: '',
        notes: '',
        status: 'Pendiente',
        duration_minutes: 60
    });

    const filteredSessions = useMemo(() => {
        return sessions.filter(s => {
            const matchesSearch = (s.topic || '').toLowerCase().includes(searchTerm.toLowerCase());
            const matchesStatus = filterStatus === 'All' || s.status === filterStatus;
            return matchesSearch && matchesStatus;
        });
    }, [sessions, searchTerm, filterStatus]);

    const fetchSessions = useCallback(async () => {
        if (!token) {
            setSessions([]);
            setLoading(false);
            return;
        }
        setLoading(true);
        setSessionsError(null);
        try {
            const sessionsData = await apiFetch<CounselingSession[]>('/crm/counseling/', { token, cache: 'no-store' });
            setSessions(Array.isArray(sessionsData) ? sessionsData : []);
        } catch (err) {
            setSessions([]);
            const message = extractErrorMessage(err, 'Error al cargar la sesion de consejeria');
            setSessionsError(message);
            addToast(message, 'error');
        } finally {
            setLoading(false);
        }
    }, [token, addToast]);

    useEffect(() => {
        fetchSessions();
    }, [fetchSessions]);


    const handleCreateSession = async () => {
        if (!token) return;
        setIsSaving(true);
        try {
            await apiFetch('/crm/counseling/', {
                method: 'POST',
                token,
                body: newSession,
            });
            addToast('Sesión agendada correctamente', 'success');
            setIsDrawerOpen(false);
            setNewSession({ pastor_id: null, persona_id: '', scheduled_at: '', topic: '', notes: '', status: 'Pendiente', duration_minutes: 60 });
            fetchSessions();
        } catch {
            addToast('Error al agendar sesión', 'error');
        } finally {
            setIsSaving(false);
        }
    };

    const handleUpdateStatus = async (id: string, status: string) => {
        if (!token) return;
        try {
            await apiFetch(`/crm/counseling/${id}`, { method: 'PATCH', token, body: { status } });
            addToast(`Estado actualizado a ${status}`, 'success');
            fetchSessions();
        } catch {
            addToast('Error al actualizar estado', 'error');
        }
    };

    const openSessionDetail = (session: CounselingSession) => {
        pushSidebarPanel({
            id: `session-detail-${session.id}`,
            title: session.topic || 'Detalle de Sesión',
            content: (
                <CounselingDetailSidebar 
                    session={session} 
                    onUpdate={fetchSessions} 
                    onClose={popSidebarPanel}
                />
            )
        });
    };

    const groupedByDate = useMemo(() => {
        const map: Record<string, { label: string; items: CounselingSession[] }> = {};
        for (const session of filteredSessions) {
            if (!session.scheduled_at) continue;
            const date = new Date(session.scheduled_at);
            if (isNaN(date.getTime())) continue;
            const key = date.toISOString().slice(0, 10);
            const label = date.toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: 'numeric' });
            if (!map[key]) map[key] = { label, items: [] };
            map[key].items.push(session);
        }
        return Object.entries(map).sort((a, b) => a[0].localeCompare(b[0]));
    }, [filteredSessions]);

    return (
        <CrmShell
            breadcrumbs={[{ label: 'CCF', icon: Users }, { label: 'Consolidación', icon: Users }, { label: 'Consejería', icon: Heart }]}
            viewOptions={ALL_VIEWS}
            viewType={viewType}
            onViewChange={setViewType}
            rightActions={
                <SplitDropdownButton
                    mainLabel="Nuevo"
                    icon={Plus}
                    onMainClick={() => setIsDrawerOpen(true)}
                    options={[
                        { id: 'counseling', label: 'Sesión', icon: Heart, onClick: () => setIsDrawerOpen(true) },
                        { id: 'followup', label: 'Seguimiento', icon: MessageSquare, onClick: () => setIsDrawerOpen(true) }
                    ]}
                />
            }
        >
        {sessionsError && (
            <div className="mx-3 mt-3 rounded-lg border border-amber-300/60 bg-amber-50 dark:bg-amber-500/10 dark:border-amber-500/30 p-3 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                <div className="min-w-0">
                    <p className="text-[11px] font-bold uppercase tracking-wide text-amber-800 dark:text-amber-200">No se pudo cargar la consejería</p>
                    <p className="text-sm text-amber-900/80 dark:text-amber-100/80 mt-1 break-words">{sessionsError}</p>
                </div>
                <button onClick={fetchSessions} className="shrink-0 px-3 py-2 rounded-lg bg-[hsl(var(--primary))] text-white text-[10px] font-bold uppercase tracking-wide shadow-lg shadow-blue-500/20 hover:opacity-90 transition-all">
                    Reintentar
                </button>
            </div>
        )}
        {/* Header */}
        <div className="px-3 py-4 border-b border-[hsl(var(--border))]/50 dark:border-white/5 mb-4 flex items-center justify-between">
            <h1 className="text-2xl font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tight">Consejería</h1>
            <div className="flex gap-2">
                <button
                    onClick={() => router.push('/privacy')}
                    className="flex items-center gap-2 px-4 py-1.5 bg-[hsl(var(--surface-1))] dark:bg-white/5 text-[hsl(var(--text-secondary))] border border-[hsl(var(--border))] dark:border-white/10 rounded-lg text-[11px] font-bold uppercase tracking-wide hover:bg-[hsl(var(--surface-2))] transition-all"
                >
                    <Link2 size={16} /> Ver políticas
                </button>
                <button
                    onClick={() => setIsDrawerOpen(true)}
                    className="flex items-center gap-2 px-4 py-1.5 bg-[hsl(var(--surface-2))] dark:bg-white/5 text-[hsl(var(--primary))] border border-[hsl(var(--border))] dark:border-white/10 rounded-lg text-[11px] font-bold uppercase tracking-wide shadow-sm hover:shadow-md hover:scale-105 transition-all active:scale-95 shrink-0"
                >
                    <Plus size={16} /> Agendar sesión
                </button>
            </div>
        </div>

        {/* Filters Global */}
        <div className="flex flex-col md:flex-row gap-4 items-center justify-between bg-[hsl(var(--surface-2))] dark:bg-white/5 p-4 rounded-lg border border-[hsl(var(--border))] dark:border-white/5 mb-3">
            <div className="relative w-full md:w-96">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" size={18} />
                <input
                    type="text"
                    placeholder="Buscar por tema..."
                    className="w-full bg-[hsl(var(--surface-1))] dark:bg-black/30 border border-[hsl(var(--border))] dark:border-white/10 rounded-md py-1.5 pl-12 pr-4 text-sm text-[hsl(var(--text-primary))] dark:text-white focus:outline-none focus:border-sky-500 transition-all"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                />
            </div>
            <div className="flex gap-2 w-full md:w-auto overflow-x-auto pb-1 md:pb-0">
                {['All', 'Pendiente', 'Realizada', 'Cancelada'].map(status => (
                    <button
                        key={status}
                        onClick={() => setFilterStatus(status)}
                        className={`px-4 py-2 rounded-lg text-[10px] font-bold uppercase tracking-wide transition-all ${filterStatus === status ? 'bg-sky-600 text-white shadow-lg' : 'bg-[hsl(var(--surface-3))] dark:bg-white/5 text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] dark:hover:text-white hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10'}`}
                    >
                        {status === 'All' ? 'Todos' : status}
                    </button>
                ))}
            </div>
        </div>

        {viewType === 'grid' && (
        <div className="space-y-3">
            {/* Stats */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {[
                    { label: 'Sesiones Pendientes', val: sessions.filter(s => s.status === 'Pendiente').length, color: 'text-amber-500', bg: 'bg-amber-500/10' },
                    { label: 'Completadas', val: sessions.filter(s => s.status === 'Realizada').length, color: 'text-emerald-500', bg: 'bg-emerald-500/10' },
                    { label: 'Total Histórico', val: sessions.length, color: 'text-[hsl(var(--primary))]', bg: 'bg-blue-500/10' },
                ].map((stat, i) => (
                    <div key={i} className="bg-[hsl(var(--surface-2))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/5 p-4 rounded-md flex items-center justify-between">
                        <div>
                            <p className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide leading-none mb-2">{stat.label}</p>
                            <p className="text-xl font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{stat.val}</p>
                        </div>
                        <div className={`p-4 rounded-lg ${stat.bg} ${stat.color}`}>
                            <History size={24} />
                        </div>
                    </div>
                ))}
            </div>

            {/* Sessions Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {loading ? (
                    Array.from({ length: 6 }).map((_, i) => (
                        <div key={i} className="h-48 bg-[hsl(var(--surface-2))] dark:bg-white/5 animate-pulse rounded-lg border border-[hsl(var(--border))] dark:border-white/5" />
                    ))
                ) : !sessionsError && filteredSessions.length > 0 ? (
                    filteredSessions.map(session => (
                        <div 
                            key={session.id} 
                            onClick={() => openSessionDetail(session)}
                            className="bg-[hsl(var(--surface-1))] dark:bg-white/[0.03] border border-[hsl(var(--border))] dark:border-white/10 rounded-lg p-4 space-y-3 hover:border-sky-500/40 hover:shadow-2xl hover:shadow-sky-500/5 transition-all group relative overflow-hidden cursor-pointer"
                        >
                            <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity text-sky-500">
                                <MessageSquare size={80} />
                            </div>

                            <div className="flex justify-between items-start relative z-10">
                                <div className="flex gap-2 flex-wrap">
                                    <span className={`px-4 py-1.5 rounded-full text-[10px] font-bold uppercase tracking-wide ${session.status === 'Realizada' ? 'bg-emerald-500 text-white' : session.status === 'Cancelada' ? 'bg-rose-500/10 text-rose-500' : 'bg-amber-500 text-white'}`}>
                                        {session.status}
                                    </span>
                                    {(session as any).priority_level && (
                                        <span className={`px-4 py-1.5 rounded-full text-[10px] font-bold uppercase tracking-wide flex items-center gap-1 ${(session as any).priority_level === 'URGENTE' ? 'bg-rose-600 text-white animate-pulse' : (session as any).priority_level === 'ALTA' ? 'bg-orange-500/20 text-orange-600 dark:text-orange-400' : 'bg-blue-500/10 text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]'}`}>
                                            <ShieldCheck size={10} /> {(session as any).priority_level}
                                        </span>
                                    )}
                                </div>
                                <p className="text-[11px] font-bold text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] flex items-center gap-2 shrink-0">
                                    <Clock size={12} /> {session.duration_minutes} min
                                </p>
                            </div>

                            <div className="space-y-2 relative z-10">
                                <h3 className="text-base font-bold text-[hsl(var(--text-primary))] dark:text-white leading-tight group-hover:text-sky-600 dark:group-hover:text-sky-400 transition-colors">{session.topic || 'Sin tema definido'}</h3>
                                <p className="text-xs text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] font-medium flex items-center gap-2">
                                    <Calendar size={14} className="text-sky-500" />
                                    {session.scheduled_at ? new Date(session.scheduled_at).toLocaleString('es-CO', { day: '2-digit', month: 'long', hour: '2-digit', minute: '2-digit' }) : '—'}
                                </p>
                            </div>

                            {session.status === 'Pendiente' && (
                                <div className="flex gap-2 pt-2 relative z-10">
                                    <button
                                        onClick={() => handleUpdateStatus(session.id, 'Realizada')}
                                        className="flex-1 py-1.5 bg-[hsl(var(--bg-muted))] dark:bg-white/10 hover:bg-emerald-600 text-white rounded-lg text-[10px] font-bold uppercase tracking-wide shadow-xl shadow-black/10 transition-all flex items-center justify-center gap-2"
                                    >
                                        <CheckCircle2 size={14} /> Completar
                                    </button>
                                    <button
                                        onClick={() => handleUpdateStatus(session.id, 'Cancelada')}
                                        className="flex-1 py-1.5 bg-[hsl(var(--surface-1))] dark:bg-white/5 hover:bg-rose-600 text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] hover:text-white rounded-lg text-[10px] font-bold uppercase tracking-wide transition-all flex items-center justify-center gap-2 border border-[hsl(var(--border))] dark:border-white/5"
                                    >
                                        <XCircle size={14} /> Cancelar
                                    </button>
                                </div>
                            )}
                        </div>
                    ))
                ) : (
                    <div className="col-span-full py-1.5 text-center space-y-4 bg-[hsl(var(--bg-muted))]/20 rounded-lg border border-dashed border-white/10">
                        <MessageSquare size={48} className="mx-auto text-[hsl(var(--text-primary))]" />
                        <p className="text-[hsl(var(--text-secondary))] font-bold uppercase tracking-wide text-[10px]">No hay sesiones registradas</p>
                    </div>
                )}
            </div>
        </div>
        )}

        {viewType === 'list' && (
            <div className="bg-[hsl(var(--surface-1))] dark:bg-[#1E1F21] rounded-lg border border-[hsl(var(--border))] dark:border-white/10 overflow-hidden shadow-sm">
                <div className="divide-y divide-[hsl(var(--border))] dark:divide-white/5">
                    {filteredSessions.map(session => (
                        <div 
                            key={session.id} 
                            onClick={() => openSessionDetail(session)}
                            className="flex flex-col sm:flex-row sm:items-center gap-4 p-4 hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/[0.02] transition-colors group relative cursor-pointer"
                        >
                            {/* Status Indicator & Priority */}
                            <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 min-w-[200px]">
                                <div className="flex items-center gap-3">
                                    <div className={`size-2.5 rounded-full shadow-sm shrink-0 ${session.status === 'Pendiente' ? 'bg-amber-500 shadow-amber-500/50' : session.status === 'Realizada' ? 'bg-emerald-500 shadow-emerald-500/50' : 'bg-rose-500 shadow-rose-500/50'}`} />
                                    <span className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] w-20">{session.status}</span>
                                </div>
                                {(session as any).priority_level && (
                                    <span className={`px-2 py-0.5 rounded-md text-[9px] font-bold uppercase tracking-wide flex items-center gap-1 ${(session as any).priority_level === 'URGENTE' ? 'bg-rose-500 text-white' : (session as any).priority_level === 'ALTA' ? 'bg-orange-500/10 text-orange-600 dark:text-orange-400' : 'bg-blue-500/10 text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]'}`}>
                                        {(session as any).priority_level}
                                    </span>
                                )}
                            </div>

                            {/* Main Info */}
                            <div className="flex-1 min-w-0 flex items-center gap-4">
                                <div className="size-8 rounded-full bg-[hsl(var(--surface-2))] dark:bg-white/10 flex items-center justify-center text-[10px] font-bold text-[hsl(var(--text-secondary))] shrink-0">
                                    {session.persona_id ? 'MB' : 'LD'}
                                </div>
                                <div className="min-w-0">
                                    <h3 className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] truncate group-hover:text-sky-600 dark:group-hover:text-sky-400 transition-colors">{session.topic || 'Sin tema definido'}</h3>
                                    <div className="flex items-center gap-3 mt-1">
                                        <p className="text-[11px] font-semibold text-[hsl(var(--text-secondary))] flex items-center gap-1.5">
                                            <Calendar size={12} className="text-sky-500" />
                                            {session.scheduled_at ? new Date(session.scheduled_at).toLocaleDateString('es-CO', { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—'}
                                        </p>
                                        <p className="text-[11px] font-bold text-[hsl(var(--text-secondary))] flex items-center gap-1">
                                            <Clock size={12} />
                                            {session.duration_minutes}m
                                        </p>
                                    </div>
                                </div>
                            </div>

                            {/* Actions */}
                            <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity absolute right-4 sm:static">
                                <button className="p-2 text-[hsl(var(--text-secondary))] hover:text-sky-500 bg-[hsl(var(--surface-1))] dark:bg-black rounded-lg shadow-sm border border-[hsl(var(--border))] dark:border-white/10 transition-all">
                                    <MessageSquare size={14} />
                                </button>
                                {session.status === 'Pendiente' && (
                                    <>
                                        <button onClick={() => handleUpdateStatus(session.id, 'Realizada')} aria-label="Completar" className="p-2 text-emerald-500 hover:bg-emerald-500 hover:text-white bg-[hsl(var(--surface-1))] dark:bg-black rounded-lg shadow-sm border border-[hsl(var(--border))] dark:border-white/10 transition-all">
                                            <CheckCircle2 size={14} />
                                        </button>
                                        <button onClick={() => handleUpdateStatus(session.id, 'Cancelada')} aria-label="Cancelar" className="p-2 text-rose-500 hover:bg-rose-500 hover:text-white bg-[hsl(var(--surface-1))] dark:bg-black rounded-lg shadow-sm border border-[hsl(var(--border))] dark:border-white/10 transition-all">
                                            <XCircle size={14} />
                                        </button>
                                    </>
                                )}
                            </div>
                        </div>
                    ))}
                    {!sessionsError && filteredSessions.length === 0 && (
                        <div className="py-1.5 text-center space-y-3">
                            <Search className="mx-auto text-[hsl(var(--text-secondary))] dark:text-white/10" size={32} />
                            <p className="text-[hsl(var(--text-secondary))] font-bold uppercase tracking-wide text-[10px]">No hay sesiones registradas</p>
                        </div>
                    )}
                </div>
            </div>
        )}

        {viewType === 'table' && (
            <UniversalTableView
                data={filteredSessions}
                columns={[
                    { 
                        key: 'topic', 
                        label: 'Tema', 
                        type: 'text', 
                        width: '300px',
                        render: (val, session) => (
                            <span className="font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{session.topic || 'Sin tema'}</span>
                        )
                    },
                    { 
                        key: 'scheduled_at', 
                        label: 'Fecha y Hora', 
                        type: 'date', 
                        width: '200px',
                        render: (val, session) => (
                            <div className="flex items-center gap-2 text-[hsl(var(--text-secondary))]">
                                <Calendar size={12} className="text-sky-500" />
                                <span>{session.scheduled_at ? new Date(session.scheduled_at).toLocaleDateString('es-CO', { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—'}</span>
                            </div>
                        )
                    },
                    { 
                        key: 'duration_minutes', 
                        label: 'Duración', 
                        type: 'text', 
                        width: '120px',
                        render: (val, session) => (
                            <div className="flex items-center gap-2 text-[hsl(var(--text-secondary))]">
                                <Clock size={12} />
                                <span>{session.duration_minutes} min</span>
                            </div>
                        )
                    },
                    { 
                        key: 'priority_level', 
                        label: 'Prioridad', 
                        type: 'priority', 
                        width: '120px',
                        render: (val, session) => {
                            const prior = (session as any).priority_level;
                            if (!prior) return <span className="text-[hsl(var(--text-secondary))]">—</span>;
                            return (
                                <span className={`px-2 py-0.5 rounded-md text-[9px] font-bold uppercase tracking-wide flex items-center gap-1 w-max ${prior === 'URGENTE' ? 'bg-rose-500 text-white' : prior === 'ALTA' ? 'bg-orange-500/10 text-orange-600 dark:text-orange-400' : 'bg-blue-500/10 text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]'}`}>
                                    {prior}
                                </span>
                            );
                        }
                    },
                    { 
                        key: 'status', 
                        label: 'Estado', 
                        type: 'status', 
                        width: '120px',
                        render: (val, session) => (
                            <span className={`px-2 py-1 rounded-full text-[9px] font-bold uppercase tracking-wide ${session.status === 'Pendiente' ? 'bg-amber-100 dark:bg-amber-500/10 text-amber-600 dark:text-amber-500' : session.status === 'Realizada' ? 'bg-emerald-100 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-500' : 'bg-rose-100 dark:bg-rose-500/10 text-rose-600 dark:text-rose-500'}`}>
                                {session.status}
                            </span>
                        )
                    },
                    {
                        key: 'actions',
                        label: '',
                        type: 'text',
                        width: '100px',
                        render: (val, session) => session.status === 'Pendiente' ? (
                            <div className="flex gap-2 justify-end">
                                <button onClick={(e) => { e.stopPropagation(); handleUpdateStatus(session.id, 'Realizada'); }} className="p-1.5 hover:bg-emerald-50 dark:hover:bg-emerald-500/10 text-emerald-500 rounded-lg transition-colors"><CheckCircle2 size={16} /></button>
                                <button onClick={(e) => { e.stopPropagation(); handleUpdateStatus(session.id, 'Cancelada'); }} className="p-1.5 hover:bg-rose-50 dark:hover:bg-rose-500/10 text-rose-500 rounded-lg transition-colors"><XCircle size={16} /></button>
                            </div>
                        ) : null
                    }
                ]}
                emptyMessage="No se encontraron sesiones."
                onRowClick={openSessionDetail}
            />
        )}

        {(viewType === 'board' || viewType === 'kanban') && (
            <div className="flex gap-4 overflow-x-auto pb-6 pt-2 items-start min-h-[60vh]">
                {STATUS_ORDER.map(status => (
                    <div key={status} className="w-80 shrink-0 flex flex-col h-full max-h-[75vh] rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-2))]/50 dark:bg-white/[0.02]">
                        <div className="p-3 flex items-center justify-between border-b border-[hsl(var(--border))] dark:border-white/5 bg-white/50 dark:bg-white/[0.02] backdrop-blur-md rounded-t-[32px] sticky top-0 z-10">
                            <div className="flex items-center gap-2.5">
                                <div className={`size-2.5 rounded-full shadow-sm ${status === 'Pendiente' ? 'bg-amber-500 shadow-amber-500/50' : status === 'Realizada' ? 'bg-emerald-500 shadow-emerald-500/50' : 'bg-rose-500 shadow-rose-500/50'}`} />
                                <p className="text-[11px] font-bold uppercase tracking-wider text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{status}</p>
                            </div>
                            <span className="text-[10px] font-bold text-[hsl(var(--text-secondary))] bg-[hsl(var(--surface-3))]/80 dark:bg-white/10 px-2.5 py-1 rounded-full">{filteredSessions.filter(s => s.status === status).length}</span>
                        </div>
                        <div className="p-4 space-y-3 overflow-y-auto flex-1 custom-scrollbar">
                            {filteredSessions.filter(s => s.status === status).map(session => (
                                <div key={session.id} onClick={() => openSessionDetail(session)} className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-[#1A1A1A] p-3 space-y-4 shadow-sm hover:shadow-xl hover:shadow-sky-500/5 hover:border-sky-500/40 transition-all duration-300 group relative overflow-hidden flex flex-col cursor-pointer">
                                    <div className="flex justify-between items-start">
                                        <div className="flex gap-1.5 flex-wrap">
                                            {(session as any).priority_level && (
                                                <span className={`px-2.5 py-1 rounded-lg text-[9px] font-bold uppercase tracking-wide flex items-center gap-1 ${(session as any).priority_level === 'URGENTE' ? 'bg-rose-500 text-white' : (session as any).priority_level === 'ALTA' ? 'bg-orange-500/10 text-orange-600 dark:text-orange-400' : 'bg-blue-500/10 text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]'}`}>
                                                    {(session as any).priority_level}
                                                </span>
                                            )}
                                        </div>
                                        <button className="text-[hsl(var(--text-secondary))] opacity-0 group-hover:opacity-100 transition-opacity hover:text-[hsl(var(--text-primary))] dark:hover:text-white p-1 hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 rounded-lg">
                                            <MoreHorizontal size={16} />
                                        </button>
                                    </div>
                                    <h3 className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] leading-snug group-hover:text-sky-600 dark:group-hover:text-sky-400 transition-colors">{session.topic || 'Sin tema definido'}</h3>
                                    <div className="flex items-center justify-between mt-auto pt-4 border-t border-[hsl(var(--border))] dark:border-white/[0.05]">
                                        <p className="text-[11px] font-semibold text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] flex items-center gap-1.5">
                                            <Calendar size={13} className="text-sky-500" />
                                            {session.scheduled_at ? new Date(session.scheduled_at).toLocaleDateString('es-CO', { month: 'short', day: 'numeric' }) : '—'}
                                        </p>
                                        <p className="text-[11px] font-bold text-[hsl(var(--text-secondary))] flex items-center gap-1">
                                            <Clock size={12} />
                                            {session.duration_minutes}m
                                        </p>
                                    </div>
                                    
                                    {/* Action overlay on hover for pending */}
                                    {status === 'Pendiente' && (
                                        <div className="absolute inset-0 bg-white/95 dark:bg-[#1A1A1A]/95 backdrop-blur-sm opacity-0 group-hover:opacity-100 transition-all duration-300 flex flex-col items-center justify-center gap-3 p-4 translate-y-4 group-hover:translate-y-0">
                                             <button onClick={() => handleUpdateStatus(session.id, 'Realizada')} className="w-full py-1.5 bg-emerald-500 hover:bg-emerald-600 text-white rounded-md text-[10px] font-bold uppercase tracking-wide shadow-lg shadow-emerald-500/20 transition-all flex items-center justify-center gap-2">
                                                <CheckCircle2 size={14} /> Completar
                                             </button>
                                             <button onClick={() => handleUpdateStatus(session.id, 'Cancelada')} className="w-full py-2.5 bg-[hsl(var(--surface-2))] dark:bg-white/5 hover:bg-rose-500 text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] hover:text-white rounded-md text-[10px] font-bold uppercase tracking-wide transition-all flex items-center justify-center gap-2 border border-[hsl(var(--border))] dark:border-white/5">
                                                <XCircle size={14} /> Cancelar
                                             </button>
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                ))}
            </div>
        )}

        {viewType === 'calendar' && (
            <div className="space-y-3 bg-[hsl(var(--surface-1))] dark:bg-[#1E1F21] p-4 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 shadow-sm relative overflow-hidden">
                <div className="absolute top-0 right-0 p-4 opacity-5 pointer-events-none">
                    <Calendar size={200} />
                </div>
                
                {groupedByDate.map(([dateKey, payload]) => (
                    <div key={dateKey} className="relative z-10">
                        <div className="sticky top-0 bg-white/95 dark:bg-[#1E1F21]/95 backdrop-blur-md z-20 py-2 mb-5 -mx-4 px-4 flex items-center gap-3 border-b border-[hsl(var(--border))] dark:border-white/5">
                            <div className="size-8 rounded-md bg-sky-100 dark:bg-sky-900/30 flex items-center justify-center text-sky-600">
                                <Calendar size={14} />
                            </div>
                            <h3 className="text-xs font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] uppercase tracking-wide">{payload.label}</h3>
                            <div className="flex-1 border-t border-dashed border-[hsl(var(--border))] dark:border-white/10 mx-4" />
                            <span className="text-[10px] font-bold text-[hsl(var(--text-secondary))] bg-[hsl(var(--surface-2))] dark:bg-white/5 px-2.5 py-1 rounded-md">{payload.items.length} sesiones</span>
                        </div>
                        
                        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                            {payload.items.map(session => (
                                <div key={session.id} onClick={() => openSessionDetail(session)} className="group rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/[0.02] p-3 hover:border-sky-500/30 hover:shadow-lg hover:shadow-sky-500/5 transition-all flex gap-3 cursor-pointer">
                                    <div className="flex flex-col items-center justify-center min-w-[50px] shrink-0">
                                        <p className="text-base font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] leading-none tracking-tighter">
                                            {new Date(session.scheduled_at).toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit', hour12: false })}
                                        </p>
                                        <p className="text-[10px] font-bold text-[hsl(var(--text-secondary))] mt-1.5 flex items-center gap-1"><Clock size={10}/> {session.duration_minutes}m</p>
                                    </div>
                                    <div className="w-px bg-[hsl(var(--surface-3))] dark:bg-white/10" />
                                    <div className="flex-1 min-w-0">
                                        <div className="flex justify-between items-start mb-2.5">
                                            <span className={`px-2 py-0.5 rounded-md text-[9px] font-bold uppercase tracking-wide ${session.status === 'Pendiente' ? 'bg-amber-100 text-amber-600 dark:bg-amber-500/10 dark:text-amber-500' : session.status === 'Realizada' ? 'bg-emerald-100 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-500' : 'bg-rose-100 text-rose-600 dark:bg-rose-500/10 dark:text-rose-500'}`}>
                                                {session.status}
                                            </span>
                                            {(session as any).priority_level === 'URGENTE' && <ShieldCheck size={14} className="text-rose-500 animate-pulse" />}
                                        </div>
                                        <p className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] leading-snug truncate">{session.topic || 'Sin tema definido'}</p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                ))}
                
                {!sessionsError && groupedByDate.length === 0 && (
                    <div className="py-1.5 text-center space-y-2 relative z-10">
                        <div className="size-10 rounded-full bg-[hsl(var(--surface-1))] dark:bg-white/5 flex items-center justify-center mx-auto text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">
                            <Calendar size={40} />
                        </div>
                        <div className="space-y-1">
                            <p className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">Agenda despejada</p>
                            <p className="text-[11px] font-medium text-[hsl(var(--text-secondary))]">No hay sesiones programadas en este rango de fechas.</p>
                        </div>
                    </div>
                )}
            </div>
        )}

        {viewType === 'gantt' && (
            <div className="bg-[hsl(var(--surface-1))] dark:bg-[#1E1F21] rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-4 shadow-sm">
                <div className="mb-3 flex items-center justify-between">
                    <div>
                        <h3 className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">Timeline de Consolidación</h3>
                        <p className="text-[11px] font-bold text-[hsl(var(--text-secondary))] mt-1 uppercase tracking-wide">Progreso por estado de sesión</p>
                    </div>
                </div>

                <div className="space-y-3">
                    {filteredSessions.map(session => (
                        <div key={session.id} className="group relative">
                            <div className="flex items-center justify-between text-[11px] mb-2 px-1">
                                <div className="flex items-center gap-3">
                                    <span className={`size-2 rounded-full ${session.status === 'Pendiente' ? 'bg-amber-500' : session.status === 'Realizada' ? 'bg-emerald-500' : 'bg-rose-500'}`} />
                                    <span className="font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{session.topic || 'Sin tema definido'}</span>
                                    {(session as any).priority_level === 'URGENTE' && <span className="bg-rose-500 text-white text-[8px] px-1.5 py-0.5 rounded-sm font-bold uppercase">Urgente</span>}
                                </div>
                                <span className="font-bold text-[hsl(var(--text-secondary))] font-mono">{STATUS_PROGRESS[session.status] ?? 0}%</span>
                            </div>
                            <div className="h-3.5 rounded-full bg-[hsl(var(--surface-2))] dark:bg-white/5 overflow-hidden border border-[hsl(var(--border))]/50 dark:border-white/5 relative">
                                <div 
                                    className={`h-full transition-all duration-1000 ease-out relative overflow-hidden ${session.status === 'Realizada' ? 'bg-emerald-500' : session.status === 'Cancelada' ? 'bg-rose-500' : 'bg-gradient-to-r from-sky-600 to-sky-500'}`}
                                    style={{ width: `${STATUS_PROGRESS[session.status] ?? 0}%` }}
                                >
                                    <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent w-full h-full -translate-x-full group-hover:animate-[shimmer_1.5s_infinite]" />
                                </div>
                            </div>
                        </div>
                    ))}
                    {!sessionsError && filteredSessions.length === 0 && (
                        <div className="py-1.5 border-2 border-dashed border-[hsl(var(--border))] dark:border-white/10 rounded-lg flex items-center justify-center">
                            <p className="text-[11px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Añade sesiones para visualizar el progreso</p>
                        </div>
                    )}
                </div>
            </div>
        )}

        {viewType === 'wiki' && (
            <div className="flex flex-col h-[75vh] bg-[hsl(var(--surface-1))] dark:bg-[#1E1F21] rounded-lg border border-[hsl(var(--border))] dark:border-white/10 overflow-hidden shadow-sm">
                <div className="flex items-center justify-between p-4 px-4 border-b border-[hsl(var(--border))] dark:border-white/5 bg-[hsl(var(--surface-1))] dark:bg-[#1A1A1A]">
                    <div className="flex items-center gap-3">
                        <div className="size-8 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center text-[hsl(var(--primary))]">
                            <BookOpen size={16} />
                        </div>
                        <div>
                            <h3 className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] uppercase tracking-wide">Wiki de Consejería</h3>
                            <p className="text-[10px] text-[hsl(var(--text-secondary))] font-medium">Auto-guardado local</p>
                        </div>
                    </div>
                    <div className="flex gap-2">
                        <button className="px-3 py-1.5 bg-[hsl(var(--surface-2))] dark:bg-white/5 text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] rounded-md text-[11px] font-bold uppercase tracking-wide hover:bg-[hsl(var(--surface-3))] dark:hover:bg-white/10 transition-colors">Plantillas</button>
                        <button className="px-3 py-1.5 bg-sky-600 text-white rounded-md text-[11px] font-bold uppercase tracking-wide shadow-lg shadow-sky-500/20 hover:bg-sky-500 transition-colors">Exportar</button>
                    </div>
                </div>
                <div className="flex-1 overflow-y-auto p-4 md:p-4 lg:p-4 custom-scrollbar bg-[hsl(var(--surface-1))] dark:bg-transparent">
                    <div className="max-w-3xl mx-auto">
                        <textarea
                            value={wikiNotes}
                            onChange={(e) => setWikiNotes(e.target.value)}
                            placeholder="Comienza a escribir protocolos, guías de acompañamiento o criterios de derivación psicológica..."
                            className="w-full min-h-48 bg-transparent text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] outline-none resize-none placeholder:text-[hsl(var(--text-secondary))] dark:placeholder:text-[hsl(var(--text-primary))] leading-relaxed"
                            style={{ fontSize: '1.05rem', lineHeight: '1.8' }}
                        />
                    </div>
                </div>
            </div>
        )}

        {!['table', 'list', 'grid', 'board', 'kanban', 'gantt', 'calendar', 'wiki'].includes(viewType) && (
            <CrmViewPlaceholder moduleName="Consejeria" viewType={viewType} />
        )}

        {/* ─── Drawer: Agendar Sesión ─── (NO modal) */}
        <WorkspaceDrawer
            isOpen={isDrawerOpen}
            onClose={() => setIsDrawerOpen(false)}
            title="Agendar Consejería"
            subtitle="Nuevo acompañamiento espiritual"
            actions={
                <>
                    <button onClick={() => setIsDrawerOpen(false)} className="px-4 py-2 text-[11px] font-bold text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] transition-colors">
                        Descartar
                    </button>
                    <button
                        onClick={handleCreateSession}
                        disabled={isSaving}
                        className="px-3 py-2 bg-sky-600 hover:bg-sky-500 disabled:opacity-60 text-white rounded-lg text-[11px] font-bold uppercase tracking-wide shadow-lg shadow-sky-500/20 active:scale-95 transition-all flex items-center gap-2"
                    >
                        {isSaving ? <Loader2 size={14} className="animate-spin" /> : null}
                        Agendar Ahora
                    </button>
                </>
            }
        >
            <div className="space-y-3">
                <div className="space-y-2">
                    <label className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">Persona / Lead</label>
                    <PersonaSelect
                        value={newSession.persona_id || null}
                        onChange={(id) => setNewSession({ ...newSession, persona_id: id ?? '' })}
                        placeholder="Selecciona persona..."
                    />
                </div>

                <div className="space-y-2">
                    <label className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">Tema de la Sesión</label>
                    <input
                        type="text"
                        className="w-full bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg px-3 py-2 text-sm text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] placeholder:text-[hsl(var(--text-secondary))] dark:placeholder:text-[hsl(var(--text-secondary))] focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 transition-all font-semibold"
                        placeholder="Ej: Orientación Familiar, Fortaleza..."
                        value={newSession.topic}
                        onChange={(e) => setNewSession({ ...newSession, topic: e.target.value })}
                    />
                </div>

                <div className="space-y-2">
                    <label className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">Notas Iniciales</label>
                    <textarea
                        className="w-full bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg px-3 py-2 text-sm text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] placeholder:text-[hsl(var(--text-secondary))] dark:placeholder:text-[hsl(var(--text-secondary))] focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 transition-all font-semibold min-h-12 resize-none"
                        placeholder="Describe brevemente el caso..."
                        value={newSession.notes}
                        onChange={(e) => setNewSession({ ...newSession, notes: e.target.value })}
                    />
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                        <label className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">Fecha y Hora</label>
                        <input
                            type="datetime-local"
                            className="w-full bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg px-4 py-2 text-sm text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 transition-all font-semibold"
                            style={{ colorScheme: theme === 'night' ? 'dark' : 'light' }}
                            value={newSession.scheduled_at}
                            onChange={(e) => setNewSession({ ...newSession, scheduled_at: e.target.value })}
                        />
                    </div>
                    <div className="space-y-2">
                        <label className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">Duración</label>
                        <div className="relative">
                            <select
                                className="w-full bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg px-4 py-2 text-sm text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] focus:outline-none focus:ring-2 focus:ring-sky-500/20 focus:border-sky-500 transition-all font-semibold appearance-none"
                                value={newSession.duration_minutes}
                                onChange={(e) => setNewSession({ ...newSession, duration_minutes: parseInt(e.target.value) })}
                            >
                                <option value={30} className="dark:bg-[hsl(var(--bg-muted))]">30 min</option>
                                <option value={60} className="dark:bg-[hsl(var(--bg-muted))]">1 hora</option>
                                <option value={90} className="dark:bg-[hsl(var(--bg-muted))]">1.5 horas</option>
                                <option value={120} className="dark:bg-[hsl(var(--bg-muted))]">2 horas</option>
                            </select>
                            <ChevronRight size={16} className="absolute right-5 top-1/2 -translate-y-1/2 rotate-90 text-[hsl(var(--text-secondary))] pointer-events-none" />
                        </div>
                    </div>
                </div>
            </div>
        </WorkspaceDrawer>

        </CrmShell>
    );
}
