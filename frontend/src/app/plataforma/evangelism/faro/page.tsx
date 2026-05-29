'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { apiFetch, ApiError } from '@/lib/http';
import { Home, Plus, CheckCircle2, Loader2, ChevronRight, Clock } from 'lucide-react';
import { toast } from 'sonner';
import clsx from 'clsx';
import EvangelismShell from '@/components/evangelism/EvangelismShell';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import ViewSwitcher, { ViewType } from '@/components/ViewSwitcher';
import { useViewType, MINIMAL_VIEWS } from '@/hooks/useViewType';
import Skeleton from '@/components/ui/Skeleton';
import EmptyState from '@/components/ui/EmptyState';
import { DSMetric, DSCard, DSBadge } from '@/design';

interface FaroSeason { id: number; name: string; start_date: string; end_date: string; periodicity: string; status: string; }
interface Grupo { id: number; name: string; leader_name?: string; zone?: string; day_of_week?: string; time?: string; status?: string; }
interface FaroAnalytics {
    active_faros: number;
    total_sessions: number;
    total_attendance: number;
    avg_per_session: number;
    per_faro: Array<{
        grupo_id: number;
        total_sessions: number;
        total_attendance: number;
        avg: number;
    }>;
}
interface SeasonForm {
    name: string;
    start_date: string;
    end_date: string;
    periodicity: 'SEMANAL' | 'MENSUAL';
}

const PERIODICITY_LABEL: Record<string, string> = { SEMANAL: 'Semanal', MENSUAL: 'Mensual' };

export default function FaroPage() {
    const { token, user } = useAuth();
    const router = useRouter();
    const { viewType, setViewType } = useViewType('evangelism_faro', 'grid');
    const [seasons, setSeasons] = useState<FaroSeason[]>([]);
    const [houses, setHouses] = useState<Grupo[]>([]);
    const [analytics, setAnalytics] = useState<FaroAnalytics | null>(null);
    const [activeSeason, setActiveSeason] = useState<FaroSeason | null>(null);
    const [loading, setLoading] = useState(true);
    const [showNewSeason, setShowNewSeason] = useState(false);
    const [showNewSession, setShowNewSession] = useState(false);
    const [savingSession, setSavingSession] = useState(false);
    const [savingSeason, setSavingSeason] = useState(false);
    const [sessionForm, setSessionForm] = useState({ grupo_id: '', session_date: new Date().toISOString().split('T')[0], topic: 'S1', report_deadline: '' });
    const [seasonForm, setSeasonForm] = useState<SeasonForm>({ name: '', start_date: '', end_date: '', periodicity: 'SEMANAL' });
    const isSeasonFormValid = Boolean(seasonForm.name.trim() && seasonForm.start_date && seasonForm.end_date);
    const isSessionFormValid = Boolean(sessionForm.grupo_id && sessionForm.session_date && activeSeason);
    const role = String(user?.role || '').toLowerCase();
    const isPrivileged = role === 'admin' || role === 'pastor';

    const load = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const [s, h]: [FaroSeason[], Grupo[]] = await Promise.all([
                apiFetch<FaroSeason[]>('/evangelism/faro/seasons', { token }).catch(() => [] as FaroSeason[]),
                apiFetch<Grupo[]>('/evangelism/grupos/mine', { token }).catch(() => [] as Grupo[])
            ]);
            setSeasons(s);
            setHouses(h);
            const active = s.find(x => x.status === 'Activa') || s[0] || null;
            setActiveSeason(active);
            if (active) {
                const a = await apiFetch<FaroAnalytics>(`/evangelism/faro/analytics?season_id=${active.id}`, { token }).catch(() => null);
                setAnalytics(a);
            }
        } catch { toast.error('Error al cargar Grupos en Casa'); }
        finally { setLoading(false); }
    }, [token]);

    useEffect(() => {
        load();
    }, [load]);

    const handleCreateSeason = async () => {
        if (!seasonForm.name || !seasonForm.start_date || !seasonForm.end_date) return toast.error('Completa todos los campos');
        setSavingSeason(true);
        try {
            await apiFetch('/evangelism/faro/seasons', { method: 'POST', body: seasonForm, token });
            toast.success('Temporada creada');
            setShowNewSeason(false);
            setSeasonForm({ name: '', start_date: '', end_date: '', periodicity: 'SEMANAL' });
            load();
        } catch (e) {
            const detail = e instanceof ApiError && typeof e.detail === 'object' && e.detail && 'detail' in e.detail
                ? String((e.detail as { detail?: string }).detail || '')
                : '';
            toast.error(detail || 'Error al crear temporada');
        }
        finally { setSavingSeason(false); }
    };

    const handleCreateSession = async () => {
        if (!sessionForm.grupo_id || !sessionForm.session_date || !activeSeason) return toast.error('Selecciona el grupo y la fecha');
        setSavingSession(true);
        try {
            const bodyPayload: any = { ...sessionForm, season_id: activeSeason.id };
            if (sessionForm.grupo_id !== 'all') {
                bodyPayload.grupo_id = Number(sessionForm.grupo_id);
            }
            if (sessionForm.report_deadline) {
                bodyPayload.report_deadline = sessionForm.report_deadline + ':00Z';
            } else {
                delete bodyPayload.report_deadline;
            }

            const res = await apiFetch<{ message: string, created_count: number }>('/evangelism/faro/sessions', { method: 'POST', body: bodyPayload, token });
            toast.success(res.message || 'Sesión registrada');
            setShowNewSession(false);
            setSessionForm({ grupo_id: '', session_date: new Date().toISOString().split('T')[0], topic: 'S1', report_deadline: '' });
            load();
        } catch (e) {
            const detail = e instanceof ApiError && typeof e.detail === 'object' && e.detail && 'detail' in e.detail
                ? String((e.detail as { detail?: string }).detail || '')
                : '';
            toast.error(detail || 'Error al registrar sesión');
        }
        finally { setSavingSession(false); }
    };

    const handleCloseSeason = async (id: number) => {
        if (!confirm('¿Finalizar esta temporada?')) return;
        await apiFetch(`/evangelism/faro/seasons/${id}`, { method: 'PATCH', body: { status: 'Finalizada' }, token });
        toast.success('Temporada finalizada');
        load();
    };

    if (loading) {
        return (
            <EvangelismShell breadcrumbs={[]}>
                <div className="p-4 space-y-3">
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                        {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-32 rounded-lg" />)}
                    </div>
                    <Skeleton className="h-[400px] rounded-lg" />
                </div>
            </EvangelismShell>
        );
    }

    return (
        <EvangelismShell breadcrumbs={[]}>
            <div className="p-4 space-y-3">
                {/* Page Header Area */}
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div>
                        <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-1">Evangelismo · Estrategia</p>
                        <h1 className="text-xl font-bold text-slate-900 dark:text-white tracking-tight">Grupos en Casa</h1>
                        {activeSeason
                                ? <p className="text-slate-500 dark:text-slate-400 text-sm font-medium flex items-center gap-1.5 mt-2">
                                    <span className="inline-block size-2 rounded-full bg-emerald-500" />
                                    Temporada activa: <strong className="text-slate-700 dark:text-slate-200">{activeSeason.name}</strong>
                                    <span className="text-slate-300 dark:text-white/20">·</span>
                                    {PERIODICITY_LABEL[activeSeason.periodicity]}
                                  </p>
                                : <p className="text-amber-500 text-sm font-bold mt-2 flex items-center gap-2">
                                    <Clock size={16} /> Sin temporada activa. Crea una para comenzar.
                                  </p>
                            }
                        </div>
                    </div>

                    {/* View Switcher */}
                    <div className="flex items-center gap-2 mt-2 mb-4">
                        <ViewSwitcher viewType={viewType} setViewType={setViewType} availableViews={MINIMAL_VIEWS} />
                    </div>

                    {/* KPIs */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                        <DSMetric label="Grupos Activos" value={String(analytics?.active_faros ?? '—')} tone="emerald" trend="Red actual" />
                        <DSMetric label="Sesiones Totales" value={String(analytics?.total_sessions ?? '—')} tone="blue" trend={activeSeason?.name} />
                        <DSMetric label="Asistentes Totales" value={String(analytics?.total_attendance ?? '—')} tone="blue" trend="Acumulado" />
                        <DSMetric label="Promedio / Sesión" value={String(analytics?.avg_per_session ?? '—')} tone="amber" trend="Por semana" />
                    </div>

                    <div className="space-y-3 pb-12">
                        {/* Mis Faros */}
                        <section>
                            <h2 className="text-[11px] font-semibold uppercase tracking-wide text-slate-500 mb-3">Mis Grupos</h2>
                            {houses.length === 0 ? (
                                <EmptyState 
                                    icon={Home} 
                                    title="Sin Grupos Asignados" 
                                    description="No tienes ningún grupo asignado como líder." 
                                />
                            ) : (
                                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                                    {houses.map((h) => (
                                        <button
                                            key={h.id}
                                            onClick={() => router.push(`/evangelism/faro/${h.id}`)}
                                            className="text-left bg-white dark:bg-white/5 rounded-lg border border-slate-100 dark:border-white/5 p-3 shadow-sm hover:shadow-xl hover:shadow-blue-500/5 hover:border-blue-500/30 transition-all group"
                                        >
                                            <div className="size-7 rounded-lg bg-blue-50 dark:bg-blue-900/30 text-blue-600 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                                                <Home size={24} />
                                            </div>
                                            <p className="text-lg font-bold text-slate-900 dark:text-white">{h.name}</p>
                                            <p className="text-sm font-bold text-slate-500 dark:text-slate-400 mt-1">{h.zone || 'Sin zona'} · {h.day_of_week || 'Sin dia'}</p>
                                        </button>
                                    ))}
                                </div>
                            )}
                        </section>

                        {/* Temporadas */}
                        {isPrivileged && (
                            <section>
                                <h2 className="text-[11px] font-semibold uppercase tracking-wide text-slate-500 mb-3">Temporadas</h2>
                                {seasons.length === 0 ? (
                                    <EmptyState 
                                        icon={Clock} 
                                        title="No hay temporadas" 
                                        description="Crea la primera temporada para comenzar a registrar sesiones."
                                        onAction={() => setShowNewSeason(true)}
                                        actionLabel="Nueva Temporada"
                                    />
                                ) : (
                                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                                        {seasons.map(s => (
                                            <div key={s.id} className={clsx(
                                                "bg-white dark:bg-white/5 rounded-lg border p-3 shadow-sm transition-all",
                                                s.status === 'Activa' ? 'border-blue-400/50 shadow-blue-500/10' : 'border-slate-100 dark:border-white/5'
                                            )}>
                                                <div className="flex items-start justify-between mb-4">
                                                    <DSBadge tone={s.status === 'Activa' ? 'emerald' : 'slate'} label={s.status} />
                                                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">{PERIODICITY_LABEL[s.periodicity]}</span>
                                                </div>
                                                <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-2 tracking-tight">{s.name}</h3>
                                                <p className="text-sm text-slate-500 font-bold mb-3">{s.start_date} → {s.end_date}</p>
                                                {s.status === 'Activa' && (
                                                    <button onClick={() => handleCloseSeason(s.id)} className="w-full py-2 bg-red-50 text-red-600 dark:bg-red-500/10 dark:text-red-400 rounded-md text-[10px] font-semibold uppercase tracking-wide hover:bg-red-100 dark:hover:bg-red-500/20 transition-colors">
                                                        Finalizar Temporada
                                                    </button>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </section>
                        )}

                        {/* Desempeño por Grupo */}
                        {isPrivileged && Boolean(analytics && analytics.per_faro && analytics.per_faro.length > 0) && (
                            <section>
                                <h2 className="text-[11px] font-semibold uppercase tracking-wide text-slate-500 mb-3">Desempeño por Grupo · {activeSeason?.name}</h2>
                                <DSCard tone="light" className="shadow-2xl overflow-hidden rounded-lg">
                                    <div className="overflow-x-auto">
                                        <table className="w-full text-left">
                                            <thead className="bg-slate-50/50 dark:bg-white/[0.02] text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                                                <tr>
                                                    <th className="px-4 py-1.5">Grupo</th>
                                                    <th className="px-4 py-1.5 text-center">Sesiones</th>
                                                    <th className="px-4 py-1.5 text-center">Asistentes</th>
                                                    <th className="px-4 py-1.5 text-center">Promedio</th>
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y divide-slate-100 dark:divide-white/5">
                                                {analytics!.per_faro.map((row) => {
                                                    const house = houses.find(h => h.id === row.grupo_id);
                                                    return (
                                                        <tr key={row.grupo_id} onClick={() => router.push(`/evangelism/faro/${row.grupo_id}`)} className="group hover:bg-slate-50 dark:hover:bg-white/[0.01] transition-colors cursor-pointer">
                                                            <td className="px-4 py-2">
                                                                <div className="flex items-center gap-4">
                                                                    <div className="size-10 rounded-md bg-blue-100 dark:bg-blue-900/30 text-blue-600 flex items-center justify-center shrink-0 group-hover:scale-110 transition-transform"><Home size={18} /></div>
                                                                    <span className="text-base font-bold text-slate-900 dark:text-white group-hover:text-blue-600 transition-colors">{house?.name || `Grupo #${row.grupo_id}`}</span>
                                                                </div>
                                                            </td>
                                                            <td className="px-4 py-2 text-center text-sm font-bold text-slate-600 dark:text-slate-400">{row.total_sessions}</td>
                                                            <td className="px-4 py-2 text-center">
                                                                <span className="px-4 py-1.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 rounded-md text-sm font-semibold">{row.total_attendance}</span>
                                                            </td>
                                                            <td className="px-4 py-2 text-center text-sm font-bold text-slate-600 dark:text-slate-400">{row.avg}</td>
                                                        </tr>
                                                    );
                                                })}
                                            </tbody>
                                        </table>
                                    </div>
                                </DSCard>
                            </section>
                        )}
                    </div>
                </div>

            {/* NEW SEASON DRAWER */}
            <WorkspaceDrawer
                isOpen={showNewSeason && isPrivileged}
                onClose={() => setShowNewSeason(false)}
                title="Nueva Temporada"
                subtitle="Configura una nueva temporada para Grupos en Casa"
                actions={
                    <>
                        <button disabled={savingSeason} onClick={() => setShowNewSeason(false)} className="px-4 py-2 text-[11px] font-bold text-slate-500 hover:text-slate-700 transition-colors disabled:opacity-60">
                            Cancelar
                        </button>
                        <button onClick={handleCreateSeason} disabled={savingSeason || !isSeasonFormValid} className="flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded-lg text-[11px] font-semibold uppercase tracking-wide shadow-lg shadow-blue-500/20 hover:bg-blue-700 active:scale-95 transition-all disabled:opacity-60">
                            {savingSeason ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />} Crear
                        </button>
                    </>
                }
            >
                <div className="space-y-3 mt-4">
                    {[
                        { label: 'Nombre de la Campaña', key: 'name', type: 'text', placeholder: 'Grupos en Casa Temporada 2026' },
                        { label: 'Fecha de Inicio', key: 'start_date', type: 'date', placeholder: '' },
                        { label: 'Fecha de Cierre', key: 'end_date', type: 'date', placeholder: '' },
                    ].map(f => (
                        <div key={f.key} className="space-y-1.5">
                            <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 block">{f.label}</label>
                            <input type={f.type} placeholder={f.placeholder} value={seasonForm[f.key as keyof SeasonForm]} onChange={e => setSeasonForm(p => ({ ...p, [f.key]: e.target.value } as SeasonForm))} className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-lg py-1.5 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500" />
                        </div>
                    ))}
                    <div className="space-y-1.5">
                        <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 block">Periodicidad de Reporte</label>
                        <select value={seasonForm.periodicity} onChange={e => setSeasonForm(p => ({ ...p, periodicity: e.target.value as SeasonForm['periodicity'] }))} className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-lg py-1.5 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500 appearance-none">
                            <option value="SEMANAL">Semanal (Reporte cada semana)</option>
                            <option value="MENSUAL">Mensual (Reporte cada mes)</option>
                        </select>
                    </div>
                </div>
            </WorkspaceDrawer>

            {/* NEW SESSION DRAWER */}
            <WorkspaceDrawer
                isOpen={showNewSession && !!activeSeason && isPrivileged}
                onClose={() => setShowNewSession(false)}
                title="Registrar Sesión Semanal"
                subtitle="Ingresa la asistencia y detalles de la reunión"
                actions={
                    <>
                        <button disabled={savingSession} onClick={() => setShowNewSession(false)} className="px-4 py-2 text-[11px] font-bold text-slate-500 hover:text-slate-700 transition-colors disabled:opacity-60">
                            Cancelar
                        </button>
                        <button onClick={handleCreateSession} disabled={savingSession || !isSessionFormValid} className="flex items-center gap-2 px-3 py-2 bg-emerald-600 text-white rounded-lg text-[11px] font-semibold uppercase tracking-wide shadow-lg shadow-emerald-500/20 hover:bg-emerald-700 active:scale-95 transition-all disabled:opacity-60">
                            {savingSession ? <Loader2 size={14} className="animate-spin" /> : <ChevronRight size={14} />} Registrar
                        </button>
                    </>
                }
            >
                <div className="space-y-3 mt-4">
                    <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-100 dark:border-blue-900/30">
                        <p className="text-[10px] font-semibold uppercase tracking-wide text-blue-400 dark:text-blue-300 mb-1">Temporada Activa</p>
                        <p className="text-sm font-bold text-blue-700 dark:text-blue-400">{activeSeason?.name}</p>
                    </div>
                    
                    <div className="space-y-1.5">
                        <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 block">Grupo</label>
                        <select value={sessionForm.grupo_id} onChange={e => setSessionForm(p => ({ ...p, grupo_id: e.target.value }))} className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-lg py-1.5 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500 appearance-none">
                            <option value="">— Seleccionar Grupo —</option>
                            {isPrivileged && <option value="all" className="font-bold">✨ TODOS LOS GRUPOS ACTIVOS</option>}
                            {houses.map(h => <option key={h.id} value={h.id}>{h.name} {h.leader_name ? `· Líder: ${h.leader_name}` : ''}</option>)}
                        </select>
                        {sessionForm.grupo_id === 'all' && (
                            <p className="text-[10px] text-blue-500 font-bold mt-1">Se creará una sesión idéntica para todas las casas activas simultáneamente.</p>
                        )}
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-1.5">
                            <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 block">Nombre / Alias (Ej. S1)</label>
                            <input type="text" placeholder="S1" value={sessionForm.topic} onChange={e => setSessionForm(p => ({ ...p, topic: e.target.value }))} className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-lg py-1.5 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500" />
                        </div>
                        <div className="space-y-1.5">
                            <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 block">Fecha de la Reunión</label>
                            <input type="date" value={sessionForm.session_date} onChange={e => setSessionForm(p => ({ ...p, session_date: e.target.value }))} className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-lg py-1.5 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500" />
                        </div>
                    </div>

                    <div className="space-y-1.5">
                        <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 block flex items-center gap-2">
                            Fecha y Hora Límite para Reportar <span className="px-1.5 py-0.5 rounded-md bg-slate-200 dark:bg-white/10 text-[8px] font-bold">OPCIONAL</span>
                        </label>
                        <input type="datetime-local" value={sessionForm.report_deadline} onChange={e => setSessionForm(p => ({ ...p, report_deadline: e.target.value }))} className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-lg py-1.5 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500" />
                        <p className="text-[10px] text-slate-500 mt-1">Si configuras este límite, los líderes no podrán guardar asistencia después de esta hora.</p>
                    </div>
                </div>
            </WorkspaceDrawer>
        </EvangelismShell>
    );
}


