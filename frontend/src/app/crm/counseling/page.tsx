'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Users, Plus, Calendar, Clock, Heart, Search, MessageSquare, History, Link2, ShieldCheck, CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import { apiFetch } from '@/lib/http';
import { useToast } from '@/context/ToastContext';
import { useAuth } from '@/context/AuthContext';
import CrmShell from '@/components/crm/CrmShell';
import AdminHero from '@/components/admin/AdminHero';
import { ViewType, getStoredView } from '@/components/ViewSwitcher';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import SplitDropdownButton from '@/components/ui/SplitDropdownButton';
import CrmViewPlaceholder from '@/components/crm/CrmViewPlaceholder';

const STATUS_ORDER = ['Pendiente', 'Realizada', 'Cancelada'];
const STATUS_PROGRESS: Record<string, number> = { Pendiente: 30, Realizada: 100, Cancelada: 0 };

interface CounselingSession {
    id: number;
    pastor_id: number;
    member_id?: number;
    lead_id?: number;
    scheduled_at: string;
    duration_minutes: number;
    status: string;
    topic?: string;
    summary?: string;
    confidential_notes?: string;
    created_at: string;
}

export default function CounselingPage() {
    const { token, user } = useAuth();
    const { addToast } = useToast();
    const [sessions, setSessions] = useState<CounselingSession[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [filterStatus, setFilterStatus] = useState('All');
    const [isDrawerOpen, setIsDrawerOpen] = useState(false);   // ← Drawer, NO modal
    const [isSaving, setIsSaving] = useState(false);
    const ALL_VIEWS: ViewType[] = ['table', 'list', 'grid', 'board', 'kanban', 'gantt', 'calendar', 'wiki'];
    const [viewType, setViewType] = useState<ViewType>(() => getStoredView('crm_counseling_view', 'grid'));
    const [wikiNotes, setWikiNotes] = useState('');

    const [members, setMembers] = useState<any[]>([]);
    const [newSession, setNewSession] = useState({
        pastor_id: user?.id || 1,
        member_id: '',
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

    const heroWatchers = ['Equipo Pastoral', 'Optimus Brain'];

    const fetchSessions = useCallback(async () => {
        if (!token) {
            setSessions([]);
            setMembers([]);
            setLoading(false);
            return;
        }
        setLoading(true);
        try {
            const [sessionsData, membersData] = await Promise.all([
                apiFetch<CounselingSession[]>('/crm/counseling/', { token, cache: 'no-store' }),
                apiFetch<any[]>('/crm/members', { token, cache: 'no-store' })
            ]);
            setSessions(Array.isArray(sessionsData) ? sessionsData : []);
            setMembers(Array.isArray(membersData) ? membersData : []);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    }, [token]);

    useEffect(() => {
        fetchSessions();
    }, [fetchSessions]);

    useEffect(() => {
        const saved = localStorage.getItem('crm_counseling_wiki_notes');
        if (saved) setWikiNotes(saved);
    }, []);

    useEffect(() => {
        localStorage.setItem('crm_counseling_wiki_notes', wikiNotes);
    }, [wikiNotes]);

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
            setNewSession({ pastor_id: user?.id || 1, member_id: '', scheduled_at: '', topic: '', notes: '', status: 'Pendiente', duration_minutes: 60 });
            fetchSessions();
        } catch {
            addToast('Error al agendar sesión', 'error');
        } finally {
            setIsSaving(false);
        }
    };

    const handleUpdateStatus = async (id: number, status: string) => {
        if (!token) return;
        try {
            await apiFetch(`/crm/counseling/${id}`, { method: 'PATCH', token, body: { status } });
            addToast(`Estado actualizado a ${status}`, 'success');
            fetchSessions();
        } catch {
            addToast('Error al actualizar estado', 'error');
        }
    };

    const getSentimentIcon = (label: string) => {
        switch (label) {
            case 'POSITIVE': return { icon: '😊', label: 'Radiante', color: 'text-emerald-500' };
            case 'NEGATIVE': return { icon: '😔', label: 'Sombrío', color: 'text-rose-400' };
            default: return { icon: '😐', label: 'Sereno', color: 'text-slate-400' };
        }
    };

    const groupedByDate = useMemo(() => {
        const map: Record<string, { label: string; items: CounselingSession[] }> = {};
        for (const session of filteredSessions) {
            const date = new Date(session.scheduled_at);
            const key = date.toISOString().slice(0, 10);
            const label = date.toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: 'numeric' });
            if (!map[key]) map[key] = { label, items: [] };
            map[key].items.push(session);
        }
        return Object.entries(map).sort((a, b) => a[0].localeCompare(b[0]));
    }, [filteredSessions]);

    return (
        <CrmShell
            breadcrumbs={[{ label: 'CCF', icon: Users }, { label: 'CRM Pastoral', icon: Users }, { label: 'Consejería', icon: Heart }]}
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
        <AdminHero
            eyebrow="Consejería"
            title="Centro de consejería"
            description="Coordina sesiones pastorales y seguimiento espiritual por estado con IA que prioriza casos urgentes."
            tags={['Consejería', 'Seguimiento', 'IA']}
            watchers={heroWatchers}
            primaryAction={{ label: 'Agendar sesión', icon: Plus, onClick: () => setIsDrawerOpen(true) }}
            secondaryAction={{ label: 'Ver políticas', icon: Link2, onClick: () => {} }}
        />

        {viewType === 'grid' && (
        <div className="space-y-8">
            {/* Stats */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {[
                    { label: 'Sesiones Pendientes', val: sessions.filter(s => s.status === 'Pendiente').length, color: 'text-amber-500', bg: 'bg-amber-500/10' },
                    { label: 'Completadas', val: sessions.filter(s => s.status === 'Realizada').length, color: 'text-emerald-500', bg: 'bg-emerald-500/10' },
                    { label: 'Total Histórico', val: sessions.length, color: 'text-blue-500', bg: 'bg-blue-500/10' },
                ].map((stat, i) => (
                    <div key={i} className="bg-slate-900/40 dark:bg-white/5 border border-white/5 p-6 rounded-3xl flex items-center justify-between">
                        <div>
                            <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest leading-none mb-2">{stat.label}</p>
                            <p className="text-3xl font-black text-white dark:text-slate-100">{stat.val}</p>
                        </div>
                        <div className={`p-4 rounded-2xl ${stat.bg} ${stat.color}`}>
                            <History size={24} />
                        </div>
                    </div>
                ))}
            </div>

            {/* Filters */}
            <div className="flex flex-col md:flex-row gap-4 items-center justify-between bg-slate-900/20 dark:bg-white/5 p-4 rounded-2xl border border-white/5">
                <div className="relative w-full md:w-96">
                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
                    <input
                        type="text"
                        placeholder="Buscar por tema..."
                        className="w-full bg-slate-900 dark:bg-black/30 border border-white/10 rounded-xl py-3 pl-12 pr-4 text-sm text-white focus:outline-none focus:border-purple-500 transition-all"
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                </div>
                <div className="flex gap-2 w-full md:w-auto overflow-x-auto pb-1 md:pb-0">
                    {['All', 'Pendiente', 'Realizada', 'Cancelada'].map(status => (
                        <button
                            key={status}
                            onClick={() => setFilterStatus(status)}
                            className={`px-4 py-2 rounded-lg text-[10px] font-black uppercase tracking-widest transition-all ${filterStatus === status ? 'bg-purple-600 text-white shadow-lg' : 'bg-white/5 text-slate-400 hover:text-white hover:bg-white/10'}`}
                        >
                            {status === 'All' ? 'Todos' : status}
                        </button>
                    ))}
                </div>
            </div>

            {/* Sessions Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {loading ? (
                    Array.from({ length: 6 }).map((_, i) => (
                        <div key={i} className="h-64 bg-slate-900/50 animate-pulse rounded-[40px] border border-white/5" />
                    ))
                ) : filteredSessions.length > 0 ? (
                    filteredSessions.map(session => (
                        <div key={session.id} className="bg-slate-900/40 dark:bg-white/5 border border-white/5 rounded-[40px] p-8 space-y-6 hover:border-purple-500/30 transition-all group relative overflow-hidden">
                            <div className="absolute top-0 right-0 p-6 opacity-5 group-hover:opacity-10 transition-opacity">
                                <MessageSquare size={80} />
                            </div>

                            <div className="flex justify-between items-start relative z-10">
                                <div className="flex gap-2 flex-wrap">
                                    <span className={`px-4 py-1.5 rounded-full text-[9px] font-black uppercase tracking-widest ${session.status === 'Realizada' ? 'bg-emerald-500/10 text-emerald-500' : session.status === 'Cancelada' ? 'bg-rose-500/10 text-rose-500' : 'bg-amber-500/10 text-amber-500'}`}>
                                        {session.status}
                                    </span>
                                    {(session as any).priority_level && (
                                        <span className={`px-4 py-1.5 rounded-full text-[9px] font-black uppercase tracking-widest flex items-center gap-1 ${(session as any).priority_level === 'URGENTE' ? 'bg-rose-600 text-white animate-pulse' : (session as any).priority_level === 'ALTA' ? 'bg-orange-500/20 text-orange-500' : 'bg-blue-500/10 text-blue-400'}`}>
                                            <ShieldCheck size={10} /> {(session as any).priority_level}
                                        </span>
                                    )}
                                    {(session as any).sentiment_label && (
                                        <div className={`flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/5 border border-white/5 ${getSentimentIcon((session as any).sentiment_label).color}`}>
                                            <span className="text-sm">{getSentimentIcon((session as any).sentiment_label).icon}</span>
                                            <span className="text-[9px] font-black uppercase tracking-widest">{getSentimentIcon((session as any).sentiment_label).label}</span>
                                        </div>
                                    )}
                                </div>
                                <p className="text-[10px] font-bold text-slate-500 flex items-center gap-2 shrink-0">
                                    <Clock size={12} /> {session.duration_minutes} min
                                </p>
                            </div>

                            <div className="space-y-2 relative z-10">
                                <h3 className="text-xl font-bold text-white dark:text-white leading-tight">{session.topic || 'Sin tema definido'}</h3>
                                <p className="text-xs text-slate-400 flex items-center gap-2">
                                    <Calendar size={14} className="text-purple-500" />
                                    {new Date(session.scheduled_at).toLocaleString()}
                                </p>
                            </div>

                            {session.status === 'Pendiente' && (
                                <div className="flex gap-2 pt-2 relative z-10">
                                    <button
                                        onClick={() => handleUpdateStatus(session.id, 'Realizada')}
                                        className="flex-1 py-3 bg-white/5 hover:bg-emerald-500 text-slate-300 hover:text-white rounded-2xl text-[10px] font-black uppercase tracking-widest transition-all flex items-center justify-center gap-2"
                                    >
                                        <CheckCircle2 size={14} /> Completar
                                    </button>
                                    <button
                                        onClick={() => handleUpdateStatus(session.id, 'Cancelada')}
                                        className="flex-1 py-3 bg-white/5 hover:bg-rose-500 text-slate-300 hover:text-white rounded-2xl text-[10px] font-black uppercase tracking-widest transition-all flex items-center justify-center gap-2"
                                    >
                                        <XCircle size={14} /> Cancelar
                                    </button>
                                </div>
                            )}
                        </div>
                    ))
                ) : (
                    <div className="col-span-full py-20 text-center space-y-4 bg-slate-900/20 rounded-[40px] border border-dashed border-white/10">
                        <MessageSquare size={48} className="mx-auto text-slate-800" />
                        <p className="text-slate-500 font-bold uppercase tracking-[0.2em] text-[10px]">No hay sesiones registradas</p>
                    </div>
                )}
            </div>
        </div>
        )}

        {viewType === 'list' && (
            <div className="space-y-3">
                {filteredSessions.map(session => (
                    <div key={session.id} className="rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 p-4 flex items-center justify-between">
                        <div>
                            <p className="text-sm font-black text-slate-800 dark:text-slate-100">{session.topic || 'Sin tema definido'}</p>
                            <p className="text-[11px] text-slate-500">{new Date(session.scheduled_at).toLocaleString()}</p>
                        </div>
                        <div className="flex items-center gap-2">
                            <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">{session.status}</span>
                            {session.status === 'Pendiente' && <button onClick={() => handleUpdateStatus(session.id, 'Realizada')} className="px-3 py-1.5 rounded-lg bg-emerald-600 text-white text-[10px] font-black uppercase">Completar</button>}
                        </div>
                    </div>
                ))}
                {filteredSessions.length === 0 && <div className="py-10 text-center text-slate-400 text-sm">Sin sesiones</div>}
            </div>
        )}

        {viewType === 'table' && (
            <div className="rounded-2xl border border-slate-200 dark:border-white/10 overflow-hidden bg-white dark:bg-white/5">
                <table className="w-full text-left">
                    <thead className="bg-slate-50 dark:bg-white/5">
                        <tr>
                            <th className="px-4 py-3 text-[10px] font-black uppercase tracking-widest text-slate-400">Tema</th>
                            <th className="px-4 py-3 text-[10px] font-black uppercase tracking-widest text-slate-400">Fecha</th>
                            <th className="px-4 py-3 text-[10px] font-black uppercase tracking-widest text-slate-400">Duración</th>
                            <th className="px-4 py-3 text-[10px] font-black uppercase tracking-widest text-slate-400">Estado</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filteredSessions.map(session => (
                            <tr key={session.id} className="border-t border-slate-100 dark:border-white/5">
                                <td className="px-4 py-3 text-sm font-bold text-slate-800 dark:text-slate-100">{session.topic || 'Sin tema'}</td>
                                <td className="px-4 py-3 text-xs text-slate-500">{new Date(session.scheduled_at).toLocaleString()}</td>
                                <td className="px-4 py-3 text-xs text-slate-500">{session.duration_minutes} min</td>
                                <td className="px-4 py-3 text-xs font-black text-slate-500 uppercase">{session.status}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        )}

        {(viewType === 'board' || viewType === 'kanban') && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                {STATUS_ORDER.map(status => (
                    <div key={status} className="rounded-2xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/[0.03] p-3">
                        <div className="mb-3 flex items-center justify-between">
                            <p className="text-[10px] font-black uppercase tracking-widest text-slate-500">{status}</p>
                            <span className="text-[10px] font-black text-slate-400">{filteredSessions.filter(s => s.status === status).length}</span>
                        </div>
                        <div className="space-y-2">
                            {filteredSessions.filter(s => s.status === status).map(session => (
                                <div key={session.id} className="rounded-xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 p-3">
                                    <p className="text-sm font-black text-slate-800 dark:text-slate-100">{session.topic || 'Sin tema'}</p>
                                    <p className="text-[10px] text-slate-400">{new Date(session.scheduled_at).toLocaleString()}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                ))}
            </div>
        )}

        {viewType === 'calendar' && (
            <div className="space-y-4">
                {groupedByDate.map(([dateKey, payload]) => (
                    <div key={dateKey} className="rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 p-4">
                        <p className="mb-3 text-[10px] font-black uppercase tracking-widest text-slate-500">{payload.label}</p>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            {payload.items.map(session => (
                                <div key={session.id} className="rounded-xl border border-slate-200 dark:border-white/10 p-3">
                                    <p className="text-sm font-black text-slate-800 dark:text-slate-100">{session.topic || 'Sin tema'}</p>
                                    <p className="text-[10px] text-slate-400">{new Date(session.scheduled_at).toLocaleTimeString()}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                ))}
                {groupedByDate.length === 0 && <div className="py-10 text-center text-slate-400 text-sm">Sin agenda de sesiones</div>}
            </div>
        )}

        {viewType === 'gantt' && (
            <div className="rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 p-4 space-y-3">
                <p className="text-[10px] font-black uppercase tracking-widest text-slate-500">Progreso de sesiones</p>
                {filteredSessions.map(session => (
                    <div key={session.id} className="space-y-1">
                        <div className="flex items-center justify-between text-[11px]">
                            <span className="font-bold text-slate-700 dark:text-slate-300">{session.topic || 'Sin tema'}</span>
                            <span className="font-black text-slate-400">{STATUS_PROGRESS[session.status] ?? 0}%</span>
                        </div>
                        <div className="h-2 rounded-full bg-slate-100 dark:bg-white/10 overflow-hidden">
                            <div className="h-full bg-purple-600" style={{ width: `${STATUS_PROGRESS[session.status] ?? 0}%` }} />
                        </div>
                    </div>
                ))}
            </div>
        )}

        {viewType === 'wiki' && (
            <div className="rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 p-4 space-y-3">
                <p className="text-[10px] font-black uppercase tracking-widest text-slate-500">Wiki de consejería</p>
                <textarea
                    value={wikiNotes}
                    onChange={(e) => setWikiNotes(e.target.value)}
                    placeholder="Documenta protocolos de confidencialidad, criterios de urgencia y rutas de derivación..."
                    className="w-full min-h-[360px] rounded-2xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 p-4 text-sm font-medium text-slate-700 dark:text-slate-200 outline-none focus:ring-2 focus:ring-purple-500/20"
                />
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
                    <button onClick={() => setIsDrawerOpen(false)} className="px-4 py-2 text-[11px] font-bold text-slate-500 hover:text-slate-700 transition-colors">
                        Descartar
                    </button>
                    <button
                        onClick={handleCreateSession}
                        disabled={isSaving}
                        className="px-8 py-2 bg-purple-600 hover:bg-purple-500 disabled:opacity-60 text-white rounded-lg text-[11px] font-black uppercase tracking-widest shadow-lg shadow-purple-500/20 active:scale-95 transition-all flex items-center gap-2"
                    >
                        {isSaving ? <Loader2 size={14} className="animate-spin" /> : null}
                        Agendar Ahora
                    </button>
                </>
            }
        >
            <div className="space-y-6">
                <div className="space-y-2">
                    <label className="text-[9px] font-black uppercase tracking-[0.2em] text-slate-400">Miembro / Lead</label>
                    <select
                        required
                        className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-2xl px-5 py-4 text-sm text-slate-800 dark:text-white focus:outline-none focus:border-purple-500 transition-all font-medium appearance-none"
                        value={newSession.member_id}
                        onChange={(e) => setNewSession({ ...newSession, member_id: e.target.value })}
                    >
                        <option value="">Selecciona miembro...</option>
                        {members.map(m => (
                            <option key={m.id} value={m.id}>{m.first_name} {m.last_name}</option>
                        ))}
                    </select>
                </div>

                <div className="space-y-2">
                    <label className="text-[9px] font-black uppercase tracking-[0.2em] text-slate-400">Tema de la Sesión</label>
                    <input
                        type="text"
                        className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-2xl px-5 py-4 text-sm text-slate-800 dark:text-white focus:outline-none focus:border-purple-500 transition-all font-medium"
                        placeholder="Ej: Orientación Familiar, Fortaleza..."
                        value={newSession.topic}
                        onChange={(e) => setNewSession({ ...newSession, topic: e.target.value })}
                    />
                </div>

                <div className="space-y-2">
                    <label className="text-[9px] font-black uppercase tracking-[0.2em] text-slate-400">Notas Iniciales</label>
                    <textarea
                        className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-2xl px-5 py-4 text-sm text-slate-800 dark:text-white focus:outline-none focus:border-purple-500 transition-all font-medium min-h-[100px] resize-none"
                        placeholder="Describe brevemente el caso..."
                        value={newSession.notes}
                        onChange={(e) => setNewSession({ ...newSession, notes: e.target.value })}
                    />
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                        <label className="text-[9px] font-black uppercase tracking-[0.2em] text-slate-400">Fecha y Hora</label>
                        <input
                            type="datetime-local"
                            className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-2xl px-4 py-4 text-sm text-slate-800 dark:text-white focus:outline-none focus:border-purple-500 transition-all font-medium"
                            style={{ colorScheme: 'dark' }}
                            value={newSession.scheduled_at}
                            onChange={(e) => setNewSession({ ...newSession, scheduled_at: e.target.value })}
                        />
                    </div>
                    <div className="space-y-2">
                        <label className="text-[9px] font-black uppercase tracking-[0.2em] text-slate-400">Duración (min)</label>
                        <select
                            className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-2xl px-4 py-4 text-sm text-slate-800 dark:text-white focus:outline-none focus:border-purple-500 transition-all font-medium appearance-none"
                            value={newSession.duration_minutes}
                            onChange={(e) => setNewSession({ ...newSession, duration_minutes: parseInt(e.target.value) })}
                        >
                            <option value={30}>30 min</option>
                            <option value={60}>1 hora</option>
                            <option value={90}>1.5 horas</option>
                            <option value={120}>2 horas</option>
                        </select>
                    </div>
                </div>
            </div>
        </WorkspaceDrawer>

        </CrmShell>
    );
}
