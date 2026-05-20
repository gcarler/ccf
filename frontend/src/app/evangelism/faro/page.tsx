'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { apiFetch, ApiError } from '@/lib/http';
import EvangelismShell from '@/components/evangelism/EvangelismShell';
import { Home, Plus, Calendar, Users, CheckCircle2, Loader2, ChevronRight, BarChart3, Clock } from 'lucide-react';
import { toast } from 'react-toastify';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';

interface FaroSeason { id: number; name: string; start_date: string; end_date: string; periodicity: string; status: string; }
interface GloryHouse { id: number; name: string; leader_name?: string; zone?: string; day_of_week?: string; time?: string; status?: string; }
interface FaroAnalytics {
    active_faros: number;
    total_sessions: number;
    total_attendance: number;
    avg_per_session: number;
    per_faro: Array<{
        glory_house_id: number;
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
    const [seasons, setSeasons] = useState<FaroSeason[]>([]);
    const [houses, setHouses] = useState<GloryHouse[]>([]);
    const [analytics, setAnalytics] = useState<FaroAnalytics | null>(null);
    const [activeSeason, setActiveSeason] = useState<FaroSeason | null>(null);
    const [loading, setLoading] = useState(true);
    const [showNewSeason, setShowNewSeason] = useState(false);
    const [showNewSession, setShowNewSession] = useState(false);
    const [savingSession, setSavingSession] = useState(false);
    const [savingSeason, setSavingSeason] = useState(false);
    const [sessionForm, setSessionForm] = useState({ glory_house_id: '', session_date: new Date().toISOString().split('T')[0], topic: 'S1', report_deadline: '' });
    const [seasonForm, setSeasonForm] = useState<SeasonForm>({ name: '', start_date: '', end_date: '', periodicity: 'SEMANAL' });
    const isSeasonFormValid = Boolean(seasonForm.name.trim() && seasonForm.start_date && seasonForm.end_date);
    const isSessionFormValid = Boolean(sessionForm.glory_house_id && sessionForm.session_date && activeSeason);
    const role = String(user?.role || '').toLowerCase();
    const isPrivileged = role === 'admin' || role === 'pastor';

    const load = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const [s, h]: [FaroSeason[], GloryHouse[]] = await Promise.all([
                apiFetch<FaroSeason[]>('/evangelism/faro/seasons', { token }).catch(() => [] as FaroSeason[]),
                apiFetch<GloryHouse[]>('/evangelism/glory-houses/mine', { token }).catch(() => [] as GloryHouse[])
            ]);
            setSeasons(s);
            setHouses(h);
            const active = s.find(x => x.status === 'Activa') || s[0] || null;
            setActiveSeason(active);
            if (active) {
                const a = await apiFetch<FaroAnalytics>(`/evangelism/faro/analytics?season_id=${active.id}`, { token }).catch(() => null);
                setAnalytics(a);
            }
        } catch { toast.error('Error al cargar Faro en Casa'); }
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
        if (!sessionForm.glory_house_id || !sessionForm.session_date || !activeSeason) return toast.error('Selecciona el Faro y la fecha');
        setSavingSession(true);
        try {
            const bodyPayload: any = { ...sessionForm, season_id: activeSeason.id };
            if (sessionForm.glory_house_id !== 'all') {
                bodyPayload.glory_house_id = Number(sessionForm.glory_house_id);
            }
            if (sessionForm.report_deadline) {
                // report_deadline is a local datetime string (e.g. 2026-05-18T23:59), we append Z to store as UTC or just send it as is if backend handles naive.
                bodyPayload.report_deadline = sessionForm.report_deadline + ':00Z';
            } else {
                delete bodyPayload.report_deadline;
            }

            const res = await apiFetch<{ message: string, created_count: number }>('/evangelism/faro/sessions', { method: 'POST', body: bodyPayload, token });
            toast.success(res.message || 'SesiÃ³n registrada');
            setShowNewSession(false);
            setSessionForm({ glory_house_id: '', session_date: new Date().toISOString().split('T')[0], topic: 'S1', report_deadline: '' });
            load();
        } catch (e) {
            const detail = e instanceof ApiError && typeof e.detail === 'object' && e.detail && 'detail' in e.detail
                ? String((e.detail as { detail?: string }).detail || '')
                : '';
            toast.error(detail || 'Error al registrar sesiÃ³n');
        }
        finally { setSavingSession(false); }
    };

    const handleCloseSeason = async (id: number) => {
        if (!confirm('Â¿Finalizar esta temporada?')) return;
        await apiFetch(`/evangelism/faro/seasons/${id}`, { method: 'PATCH', body: { status: 'Finalizada' }, token });
        toast.success('Temporada finalizada');
        load();
    };

    const kpis = [
        { label: 'Faros Activos', value: analytics?.active_faros ?? 'â€”', icon: Home, color: 'bg-emerald-500' },
        { label: 'Sesiones Totales', value: analytics?.total_sessions ?? 'â€”', icon: Calendar, color: 'bg-blue-500' },
        { label: 'Asistentes Totales', value: analytics?.total_attendance ?? 'â€”', icon: Users, color: 'bg-blue-500' },
        { label: 'Prom. por SesiÃ³n', value: analytics?.avg_per_session ?? 'â€”', icon: BarChart3, color: 'bg-amber-500' },
    ];

    return (
        <EvangelismShell breadcrumbs={[{ label: 'Evangelismo', icon: Home }, { label: 'Faro en Casa', icon: Home }]}>
            <main className="flex-1 overflow-y-auto">
                {/* Page Header */}
                <div className="px-5 pt-8 pb-6 border-b border-slate-100 dark:border-white/5">
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                        <div>
                            <p className="text-[10px] font-black uppercase tracking-[0.25em] text-slate-400 mb-1">Evangelismo Â· Estrategia</p>
                            <h1 className="text-lg font-black text-slate-900 dark:text-white tracking-tight">Faro en Casa</h1>
                            {activeSeason
                                ? <p className="text-slate-500 dark:text-slate-400 text-sm font-medium flex items-center gap-1.5 mt-1">
                                    <span className="inline-block size-2 rounded-full bg-emerald-500" />
                                    Temporada activa: <strong className="text-slate-700 dark:text-slate-200">{activeSeason.name}</strong>
                                    <span className="text-slate-300 dark:text-white/20">Â·</span>
                                    {PERIODICITY_LABEL[activeSeason.periodicity]}
                                  </p>
                                : <p className="text-slate-400 text-sm font-medium mt-1">Sin temporada activa. Crea una para comenzar.</p>
                            }
                        </div>
                        <div className="flex gap-2 shrink-0">
                            {activeSeason && isPrivileged && (
                                <button disabled={loading} onClick={() => setShowNewSession(true)} className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-[11px] font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 active:scale-95 transition-all disabled:opacity-60 disabled:active:scale-100">
                                    <Plus size={14} /> Registrar SesiÃ³n
                                </button>
                            )}
                            {isPrivileged && (
                                <button disabled={loading} onClick={() => setShowNewSeason(true)} className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-700 dark:text-slate-200 rounded-lg text-[11px] font-black uppercase tracking-widest hover:bg-slate-50 dark:hover:bg-white/10 active:scale-95 transition-all disabled:opacity-60 disabled:active:scale-100">
                                    <Plus size={14} /> Nueva Temporada
                                </button>
                            )}
                        </div>
                    </div>
                </div>

                {/* KPIs */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 px-5 pt-6 pb-2">
                    {kpis.map(k => (
                        <div key={k.label} className="bg-white dark:bg-[#252528] rounded-2xl border border-slate-200/70 dark:border-white/5 p-5 shadow-sm">
                            <div className={`inline-flex size-8 rounded-xl ${k.color} items-center justify-center text-white mb-3 shadow-md`}><k.icon size={18} /></div>
                            <div className="text-3xl font-black text-slate-900 dark:text-white">{loading ? 'â€”' : k.value}</div>
                            <p className="text-[10px] font-black uppercase tracking-widest text-slate-400 mt-1">{k.label}</p>
                        </div>
                    ))}
                </div>

                <div className="px-5 pb-12 space-y-3">
                    <div>
                        <h2 className="text-[11px] font-black uppercase tracking-widest text-slate-400 mb-4">Mis Faros en Casa</h2>
                        {houses.length === 0 && !loading ? (
                            <div className="py-12 text-center text-slate-400">
                                <Home size={24} className="mx-auto mb-3 opacity-30" />
                                <p className="font-bold">No tienes Faro en Casa asignados.</p>
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                                {houses.map((h) => (
                                    <button
                                        key={h.id}
                                        onClick={() => router.push(`/evangelism/faro/${h.id}`)}
                                        className="text-left bg-white dark:bg-[#252528] rounded-2xl border border-slate-200 dark:border-white/5 p-5 shadow-sm hover:shadow-md transition-all"
                                    >
                                        <p className="text-sm font-black text-slate-900 dark:text-white">{h.name}</p>
                                        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{h.zone || 'Sin zona'} · {h.day_of_week || 'Sin dia'}</p>
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Temporadas */}
                    {isPrivileged && <div>
                        <h2 className="text-[11px] font-black uppercase tracking-widest text-slate-400 mb-4">Temporadas</h2>
                        {seasons.length === 0 && !loading ? (
                            <div className="py-16 text-center text-slate-400">
                                <Clock size={40} className="mx-auto mb-4 opacity-30" />
                                <p className="font-bold">No hay temporadas. Crea la primera para comenzar.</p>
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                {seasons.map(s => (
                                    <div key={s.id} className={`bg-white dark:bg-[#252528] rounded-2xl border p-4 shadow-sm ${s.status === 'Activa' ? 'border-blue-400/50 ring-1 ring-blue-400/30' : 'border-slate-200 dark:border-white/5'}`}>
                                        <div className="flex items-start justify-between mb-3">
                                            <span className={`px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-widest ${s.status === 'Activa' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400' : 'bg-slate-100 text-slate-400 dark:bg-white/5'}`}>
                                                {s.status}
                                            </span>
                                            <span className="text-[10px] font-bold text-slate-400">{PERIODICITY_LABEL[s.periodicity]}</span>
                                        </div>
                                        <h3 className="text-base font-black text-slate-900 dark:text-white mb-2">{s.name}</h3>
                                        <p className="text-xs text-slate-500 font-medium mb-4">{s.start_date} â†’ {s.end_date}</p>
                                        {s.status === 'Activa' && (
                                            <button onClick={() => handleCloseSeason(s.id)} className="text-[10px] font-black uppercase tracking-widest text-red-500 hover:text-red-700 transition-colors">Finalizar Temporada</button>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>}

                    {/* DesempeÃ±o por Faro */}
                    {isPrivileged && Boolean(analytics && analytics.per_faro && analytics.per_faro.length > 0) && (
                        <div>
                            <h2 className="text-[11px] font-black uppercase tracking-widest text-slate-400 mb-4">DesempeÃ±o por Faro Â· {activeSeason?.name}</h2>
                            <div className="bg-white dark:bg-[#252528] rounded-xl border border-slate-200 dark:border-white/5 overflow-hidden shadow-sm">
                                <table className="w-full">
                                    <thead>
                                        <tr className="border-b border-slate-100 dark:border-white/5">
                                            <th className="text-left px-4 py-2 text-[10px] font-black uppercase tracking-widest text-slate-400">Faro</th>
                                            <th className="text-center px-4 py-2 text-[10px] font-black uppercase tracking-widest text-slate-400">Sesiones</th>
                                            <th className="text-center px-4 py-2 text-[10px] font-black uppercase tracking-widest text-slate-400">Asistentes</th>
                                            <th className="text-center px-4 py-2 text-[10px] font-black uppercase tracking-widest text-slate-400">Prom.</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {analytics!.per_faro.map((row) => {
                                            const house = houses.find(h => h.id === row.glory_house_id);
                                            return (
                                                <tr key={row.glory_house_id} onClick={() => router.push(`/evangelism/faro/${row.glory_house_id}`)} className="border-b border-slate-50 dark:border-white/5 last:border-0 hover:bg-slate-50 dark:hover:bg-white/5 transition-colors cursor-pointer">
                                                    <td className="px-4 py-2">
                                                        <div className="flex items-center gap-3">
                                                            <div className="size-8 rounded-xl bg-blue-100 dark:bg-blue-900/30 text-blue-600 flex items-center justify-center"><Home size={14} /></div>
                                                            <span className="text-sm font-bold text-slate-800 dark:text-white">{house?.name || `Faro #${row.glory_house_id}`}</span>
                                                        </div>
                                                    </td>
                                                    <td className="text-center px-4 py-2 text-sm font-bold text-slate-600 dark:text-slate-400">{row.total_sessions}</td>
                                                    <td className="text-center px-4 py-2"><span className="px-3 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 rounded-lg text-sm font-black">{row.total_attendance}</span></td>
                                                    <td className="text-center px-4 py-2 text-sm font-bold text-slate-600 dark:text-slate-400">{row.avg}</td>
                                                </tr>
                                            );
                                        })}
                                    </tbody>

                                </table>
                            </div>
                        </div>
                    )}
                </div>
            </main>

            {/* NEW SEASON DRAWER */}
            <WorkspaceDrawer
                isOpen={showNewSeason && isPrivileged}
                onClose={() => setShowNewSeason(false)}
                title="Nueva Temporada"
                subtitle="Configura una nueva temporada para Faro en Casa"
                actions={
                    <>
                        <button disabled={savingSeason} onClick={() => setShowNewSeason(false)} className="px-4 py-2 text-[11px] font-bold text-slate-500 hover:text-slate-700 transition-colors disabled:opacity-60">
                            Cancelar
                        </button>
                        <button onClick={handleCreateSeason} disabled={savingSeason || !isSeasonFormValid} className="flex items-center gap-2 px-5 py-2 bg-blue-600 text-white rounded-lg text-[11px] font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:bg-blue-700 active:scale-95 transition-all disabled:opacity-60">
                            {savingSeason ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />} Crear
                        </button>
                    </>
                }
            >
                <div className="space-y-3 mt-4">
                    {[
                        { label: 'Nombre de la CampaÃ±a', key: 'name', type: 'text', placeholder: 'Faro en Casa Temporada 2026' },
                        { label: 'Fecha de Inicio', key: 'start_date', type: 'date', placeholder: '' },
                        { label: 'Fecha de Cierre', key: 'end_date', type: 'date', placeholder: '' },
                    ].map(f => (
                        <div key={f.key} className="space-y-1.5">
                            <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 block">{f.label}</label>
                            <input type={f.type} placeholder={f.placeholder} value={seasonForm[f.key as keyof SeasonForm]} onChange={e => setSeasonForm(p => ({ ...p, [f.key]: e.target.value } as SeasonForm))} className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-2xl py-1.5 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500" />
                        </div>
                    ))}
                    <div className="space-y-1.5">
                        <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 block">Periodicidad de Reporte</label>
                        <select value={seasonForm.periodicity} onChange={e => setSeasonForm(p => ({ ...p, periodicity: e.target.value as SeasonForm['periodicity'] }))} className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-2xl py-1.5 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500 appearance-none">
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
                title="Registrar SesiÃ³n Semanal"
                subtitle="Ingresa la asistencia y detalles de la reuniÃ³n"
                actions={
                    <>
                        <button disabled={savingSession} onClick={() => setShowNewSession(false)} className="px-4 py-2 text-[11px] font-bold text-slate-500 hover:text-slate-700 transition-colors disabled:opacity-60">
                            Cancelar
                        </button>
                        <button onClick={handleCreateSession} disabled={savingSession || !isSessionFormValid} className="flex items-center gap-2 px-5 py-2 bg-emerald-600 text-white rounded-lg text-[11px] font-black uppercase tracking-widest shadow-lg shadow-emerald-500/20 hover:bg-emerald-700 active:scale-95 transition-all disabled:opacity-60">
                            {savingSession ? <Loader2 size={14} className="animate-spin" /> : <ChevronRight size={14} />} Registrar
                        </button>
                    </>
                }
            >
                <div className="space-y-3 mt-4">
                    <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-2xl border border-blue-100 dark:border-blue-900/30">
                        <p className="text-[10px] font-black uppercase tracking-widest text-blue-400 dark:text-blue-300 mb-1">Temporada Activa</p>
                        <p className="text-sm font-bold text-blue-700 dark:text-blue-400">{activeSeason?.name}</p>
                    </div>
                    
                    <div className="space-y-1.5">
                        <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 block">Faro en Casa</label>
                        <select value={sessionForm.glory_house_id} onChange={e => setSessionForm(p => ({ ...p, glory_house_id: e.target.value }))} className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-2xl py-1.5 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500 appearance-none">
                            <option value="">â€” Seleccionar Faro â€”</option>
                            {isPrivileged && <option value="all" className="font-bold">âœ¨ TODOS LOS FAROS ACTIVOS</option>}
                            {houses.map(h => <option key={h.id} value={h.id}>{h.name} {h.leader_name ? `Â· LÃ­der: ${h.leader_name}` : ''}</option>)}
                        </select>
                        {sessionForm.glory_house_id === 'all' && (
                            <p className="text-[10px] text-blue-500 font-bold mt-1">Se crearÃ¡ una sesiÃ³n idÃ©ntica para todas las casas activas simultÃ¡neamente.</p>
                        )}
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-1.5">
                            <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 block">Nombre / Alias (Ej. S1)</label>
                            <input type="text" placeholder="S1" value={sessionForm.topic} onChange={e => setSessionForm(p => ({ ...p, topic: e.target.value }))} className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-2xl py-1.5 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500" />
                        </div>
                        <div className="space-y-1.5">
                            <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 block">Fecha de la ReuniÃ³n</label>
                            <input type="date" value={sessionForm.session_date} onChange={e => setSessionForm(p => ({ ...p, session_date: e.target.value }))} className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-2xl py-1.5 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500" />
                        </div>
                    </div>

                    <div className="space-y-1.5">
                        <label className="text-[10px] font-black uppercase tracking-widest text-slate-400 block flex items-center gap-2">
                            Fecha y Hora LÃ­mite para Reportar <span className="px-1.5 py-0.5 rounded-md bg-slate-200 dark:bg-white/10 text-[8px] font-bold">OPCIONAL</span>
                        </label>
                        <input type="datetime-local" value={sessionForm.report_deadline} onChange={e => setSessionForm(p => ({ ...p, report_deadline: e.target.value }))} className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-2xl py-1.5 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500" />
                        <p className="text-[10px] text-slate-500 mt-1">Si configuras este lÃ­mite, los lÃ­deres no podrÃ¡n guardar asistencia despuÃ©s de esta hora.</p>
                    </div>
                </div>
            </WorkspaceDrawer>
        </EvangelismShell>
    );
}

