"use client";

import React, { useEffect, useState, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import EvangelismShell from "@/components/evangelism/EvangelismShell";
import { Calendar, MapPin, Users, CheckCircle2, ArrowLeft, Mic, Save, X, Search, Download } from "lucide-react";
import { DSCard } from "@/design/components/DSCard";
import { toast } from "sonner";
import clsx from "clsx";
import type { Member } from "@/app/evangelism/types";
import WorkspaceDrawer from "@/components/WorkspaceDrawer";

type MinistryEventDetail = {
    id: number;
    name: string;
    title?: string;
    description: string | null;
    event_date: string | null;
    location: string | null;
    attendees_count: number;
    status: string;
    created_at: string | null;
};

type Assignment = { member_id: number; role: string; member_name?: string };
type SessionData = {
    event_id: number;
    session_date: string;
    assignments: Assignment[];
    metrics: Record<string, number>;
    attendees: { member_id: number; name: string; role: string; scanned_at: string | null }[];
    absentees: { member_id: number; name: string; role: string; phone: string }[];
    total_absentees: number;
    absentees_truncated: boolean;
    total_attendance: number;
    total_expected: number;
    attendance_rate: number;
};
interface MemberSelectProps {
    members: Member[];
    value: number | number[] | null;
    onChange: (next: number | number[] | null) => void;
    label: string;
    multi?: boolean;
}

type EventAnalyticsData = {
    kpis: {
        historical_avg: number;
        trend_percentage: number;
        peak_month: { month: string; avg: number };
    };
    monthly_data: Array<{
        month: string;
        avg_attendance: number;
    }>;
};

function MemberSelect({ members, value, onChange, label, multi = false }: MemberSelectProps) {
    const [search, setSearch] = useState('');
    const [open, setOpen] = useState(false);

    const filtered = useMemo(() => {
        if (!search) return members.slice(0, 50);
        const q = search.toLowerCase();
        return members.filter((m) => 
            m.first_name.toLowerCase().includes(q) || 
            m.last_name.toLowerCase().includes(q)
        ).slice(0, 50);
    }, [members, search]);

    const handleSelect = (m: Member) => {
        if (multi) {
            const selected = Array.isArray(value) ? value : [];
            if (!selected.includes(m.id)) onChange([...selected, m.id]);
        } else {
            onChange(m.id);
            setOpen(false);
        }
    };

    const handleRemove = (id: number) => {
        if (multi) {
            const selected = Array.isArray(value) ? value : [];
            onChange(selected.filter((v) => v !== id));
        }
        else onChange(null);
    };

    return (
        <div className="relative">
            <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-2 block">{label}</label>
            
            {multi ? (
                <div className="flex flex-wrap gap-2 mb-2">
                    {(Array.isArray(value) ? value : []).map((id) => {
                        const m = members.find((x) => x.id === id);
                        if (!m) return null;
                        return (
                            <div key={id} className="flex items-center gap-2 px-3 py-1.5 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 rounded-lg text-sm font-bold">
                                {m.first_name} {m.last_name}
                                <button type="button" aria-label={`Quitar ${m.first_name} ${m.last_name}`} onClick={() => handleRemove(id)} className="hover:text-red-500"><X size={14}/></button>
                            </div>
                        );
                    })}
                </div>
            ) : value ? (
                <div className="flex items-center justify-between px-4 py-1.5 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg mb-2">
                    <span className="text-sm font-bold text-blue-800 dark:text-blue-300">
                        {(() => {
                            const m = members.find((x) => x.id === value);
                            return m ? `${m.first_name} ${m.last_name}` : 'Cargando...';
                        })()}
                    </span>
                    <button type="button" aria-label="Quitar selección" onClick={() => typeof value === 'number' && handleRemove(value)} className="text-blue-400 hover:text-red-500"><X size={16}/></button>
                </div>
            ) : null}

            {(!value || multi) && (
                <div>
                    <div className="relative">
                        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                        <input 
                            aria-label={label}
                            value={search}
                            onChange={(e) => { setSearch(e.target.value); setOpen(true); }}
                            onFocus={() => setOpen(true)}
                            placeholder="Buscar miembro..."
                            className="w-full pl-9 pr-4 py-1.5 bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-lg text-sm outline-none focus:ring-2 focus:ring-blue-500"
                        />
                    </div>
                    {open && search && (
                        <div className="absolute z-20 top-full left-0 right-0 mt-2 bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-lg shadow-xl max-h-60 overflow-y-auto">
                            {filtered.map((m: Member) => (
                                <button
                                    key={m.id}
                                    onClick={() => handleSelect(m)}
                                    className="w-full text-left px-4 py-1.5 hover:bg-slate-50 dark:hover:bg-white/5 border-b border-slate-100 dark:border-white/5 flex flex-col"
                                >
                                    <span className="text-sm font-bold text-slate-800 dark:text-white">{m.first_name} {m.last_name}</span>
                                    <span className="text-[10px] uppercase font-bold tracking-wide text-slate-400">{m.church_role || 'Miembro'}</span>
                                </button>
                            ))}
                            {filtered.length === 0 && <div className="p-4 text-center text-sm text-slate-500">Sin resultados</div>}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

export default function EventDetailPage() {
    const params = useParams();
    const router = useRouter();
    const id = params?.id as string;
    const { token } = useAuth();
    
    const [event, setEvent] = useState<MinistryEventDetail | null>(null);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState<'details' | 'session' | 'analytics'>('details');
    const [analytics, setAnalytics] = useState<EventAnalyticsData | null>(null);
    const [loadingAnalytics, setLoadingAnalytics] = useState(false);
    
    // Session State
    const [sessionDate, setSessionDate] = useState(() => new Date().toISOString().split('T')[0]);
    const [sessionData, setSessionData] = useState<SessionData | null>(null);
    const [initialSessionFingerprint, setInitialSessionFingerprint] = useState<string | null>(null);
    const [sessionLoading, setSessionLoading] = useState(false);
    const [isVisitorModalOpen, setIsVisitorModalOpen] = useState(false);
    const [visitorForm, setVisitorForm] = useState({ first_name: '', last_name: '', phone: '', email: '' });
    const [refreshKey, setRefreshKey] = useState(0);
    const [savingSession, setSavingSession] = useState(false);
    const [exportingCsv, setExportingCsv] = useState(false);
    const [savingVisitor, setSavingVisitor] = useState(false);
    
    // Agenda Form State
    const [members, setMembers] = useState<Member[]>([]);
    const [mcId, setMcId] = useState<number | null>(null);
    const [preacherIds, setPreacherIds] = useState<number[]>([]);
    const [offeringId, setOfferingId] = useState<number | null>(null);

    const buildSessionFingerprint = useMemo(() => {
        return (mc: number | null, preachers: number[], offering: number | null) => JSON.stringify({
            mc,
            preachers: [...preachers].sort((a, b) => a - b),
            offering,
        });
    }, []);

    const currentSessionFingerprint = buildSessionFingerprint(mcId, preacherIds, offeringId);
    const hasUnsavedSessionChanges = Boolean(
        activeTab === 'session' &&
        initialSessionFingerprint !== null &&
        currentSessionFingerprint !== initialSessionFingerprint
    );

    useEffect(() => {
        if (!token || !id) return;
        const loadEvent = async () => {
            try {
                setLoading(true);
                const data = await apiFetch<MinistryEventDetail>(`/evangelism/events/${id}`, { token });
                setEvent(data);
                if (data.event_date) setSessionDate(new Date(data.event_date).toISOString().split('T')[0]);
            } catch (err) {
                console.error(err);
                toast.error("Error al cargar detalle del evento");
            } finally {
                setLoading(false);
            }
        };
        loadEvent();
    }, [id, token]);

    useEffect(() => {
        if (activeTab === 'session' && token) {
            apiFetch<Member[]>('/crm/members/', { token }).then(setMembers).catch(console.error);
        }
    }, [activeTab, token]);

    useEffect(() => {
        if (activeTab === 'session' && sessionDate && token) {
            const loadSession = async () => {
                try {
                    setSessionLoading(true);
                    const data = await apiFetch<SessionData>(`/evangelism/events/${id}/sessions/${sessionDate}`, { token });
                    setSessionData(data);
                    
                    // Pre-fill forms
                    const mc = data.assignments.find(a => a.role === 'MC');
                    const pre = data.assignments.filter(a => a.role === 'PREACHER');
                    const off = data.assignments.find(a => a.role === 'OFFERING');
                    
                    setMcId(mc?.member_id || null);
                    setPreacherIds(pre.map(a => a.member_id));
                    setOfferingId(off?.member_id || null);
                    setInitialSessionFingerprint(JSON.stringify({
                        mc: mc?.member_id || null,
                        preachers: pre.map((a) => a.member_id).sort((a, b) => a - b),
                        offering: off?.member_id || null,
                    }));
                } catch (err) {
                    console.error(err);
                } finally {
                    setSessionLoading(false);
                }
            };
            loadSession();
        }
    }, [activeTab, sessionDate, token, id, refreshKey]);

    useEffect(() => {
        if (activeTab === 'analytics' && !analytics && !loadingAnalytics) {
            loadAnalytics();
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [activeTab]);

    const handleExportCsv = async () => {
        if (!token || !event) return;
        setExportingCsv(true);
        try {
            const res = await apiFetch<string>(`/evangelism/events/${event.id}/sessions/${sessionDate}/export`, { token });
            const blob = new Blob([res], { type: 'text/csv;charset=utf-8;' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Reporte_${event.name}_${sessionDate}.csv`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
        } catch {
            toast.error("Error al exportar el reporte");
        } finally {
            setExportingCsv(false);
        }
    };

    const handleAddVisitor = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!token || !event) return;
        setSavingVisitor(true);
        try {
            await apiFetch(`/evangelism/events/${event.id}/sessions/${sessionDate}/visitors`, {
                method: 'POST',
                token,
                body: visitorForm
            });
            toast.success("Visitante registrado con éxito");
            setIsVisitorModalOpen(false);
            setVisitorForm({ first_name: '', last_name: '', phone: '', email: '' });
            setRefreshKey(k => k + 1);
        } catch {
            toast.error("Error al registrar visitante");
        } finally {
            setSavingVisitor(false);
        }
    };

    const saveSession = async () => {
        if (!token || !sessionDate) return;
        setSavingSession(true);
        try {
            const assignments: Assignment[] = [];
            if (mcId) assignments.push({ member_id: mcId, role: 'MC' });
            if (offeringId) assignments.push({ member_id: offeringId, role: 'OFFERING' });
            preacherIds.forEach(pid => assignments.push({ member_id: pid, role: 'PREACHER' }));

            await apiFetch(`/evangelism/events/${id}/assignments`, {
                method: 'POST',
                token,
                body: { session_date: sessionDate, assignments }
            });
            setInitialSessionFingerprint(currentSessionFingerprint);
            toast.success("Agenda configurada correctamente");
        } catch (err) {
            console.error(err);
            toast.error("Error al guardar la agenda");
        } finally {
            setSavingSession(false);
        }
    };

    const loadAnalytics = async () => {
        if (!token || !event) return;
        setLoadingAnalytics(true);
        try {
            const data = await apiFetch<EventAnalyticsData>(`/evangelism/events/${event.id}/analytics`, { token });
            setAnalytics(data);
        } catch {
            toast.error("Error al cargar analítica");
        } finally {
            setLoadingAnalytics(false);
        }
    };

    if (loading || !event) {
        return <div className="p-4 text-center animate-pulse font-bold text-slate-400">Cargando...</div>;
    }

    return (
        <EvangelismShell breadcrumbs={[{ label: "Evangelismo", href: "/evangelism/events" }, { label: "Eventos", href: "/evangelism/events" }, { label: event.name }]}>
            <main className="flex-1 overflow-y-auto p-4 lg:p-4">
                <div className="max-w-6xl mx-auto space-y-3">
                    {/* Header */}
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                        <div>
                            <h1 className="text-xl font-bold text-slate-900 dark:text-white uppercase">{event.name}</h1>
                            <p className="text-slate-500 font-medium text-sm flex items-center gap-2 mt-1">
                                <MapPin size={14}/> {event.location || 'Sin ubicacion'}
                            </p>
                        </div>
                        <div className="flex flex-col items-stretch gap-3">
                            <div className="flex flex-wrap justify-end gap-2">
                                <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-slate-500 dark:border-white/10 dark:bg-white/5 dark:text-slate-300">
                                    Seguimiento ministerial
                                </span>
                                <span
                                    className={`rounded-full px-3 py-1 text-[10px] font-semibold uppercase tracking-wide ${
                                        activeTab === 'session'
                                            ? "bg-blue-50 text-blue-700 dark:bg-blue-500/10 dark:text-blue-300"
                                            : "bg-slate-100 text-slate-600 dark:bg-white/5 dark:text-slate-300"
                                    }`}
                                >
                                    {activeTab === 'session' ? (
                                        hasUnsavedSessionChanges ? "Cambios pendientes" : "Sesión sincronizada"
                                    ) : (
                                        "Evento con seguimiento"
                                    )}
                                </span>
                            </div>
                            <div className="flex bg-slate-100 dark:bg-white/5 p-1 rounded-lg">
                                <button 
                                    onClick={() => setActiveTab('details')}
                                    className={clsx("px-4 py-2.5 rounded-md text-xs font-semibold uppercase tracking-wide transition-all", activeTab === 'details' ? "bg-white dark:bg-[#252528] text-blue-600 shadow-sm" : "text-slate-500")}
                                >Detalles Generales</button>
                                <button 
                                    onClick={() => setActiveTab('session')}
                                    className={clsx("px-4 py-2.5 rounded-md text-xs font-semibold uppercase tracking-wide transition-all", activeTab === 'session' ? "bg-white dark:bg-[#252528] text-blue-600 shadow-sm" : "text-slate-500")}
                                >Configurar Sesion</button>
                                <button 
                                    onClick={() => setActiveTab('analytics')}
                                    className={clsx("px-4 py-2.5 rounded-md text-xs font-semibold uppercase tracking-wide transition-all", activeTab === 'analytics' ? "bg-white dark:bg-[#252528] text-blue-600 shadow-sm" : "text-slate-500")}
                                >Analitica</button>
                            </div>
                        </div>
                    </div>

                    {activeTab === 'details' && (
                        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                            <div className="lg:col-span-2 space-y-3">
                                <DSCard>
                                    <h3 className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-4">Descripcion</h3>
                                    <p className="text-slate-600 dark:text-slate-300 font-medium">{event.description || "Sin descripcion."}</p>
                                </DSCard>
                            </div>
                            <div className="space-y-3">
                                <DSCard>
                                    <h3 className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-4">Acciones</h3>
                                    <button onClick={() => router.push('/evangelism/events')} className="w-full py-1.5 bg-blue-50 dark:bg-blue-900/20 text-blue-600 rounded-md font-bold flex items-center justify-center gap-2">
                                        <ArrowLeft size={16}/> Volver a Eventos
                                    </button>
                                </DSCard>
                            </div>
                        </div>
                    )}

                    {activeTab === 'analytics' && (
                        <div className="space-y-3">
                            {loadingAnalytics || !analytics ? (
                                <div className="text-center py-1.5 text-slate-400 font-medium">Cargando analítica...</div>
                            ) : (
                                <>
                                    {/* KPIs */}
                                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                        <div className="bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg p-3 text-center">
                                            <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-1">Promedio Histórico</p>
                                            <h3 className="text-xl font-bold text-slate-900 dark:text-white">{analytics.kpis.historical_avg}</h3>
                                            <p className="text-xs font-medium text-slate-500 mt-1">Personas por sesión</p>
                                        </div>
                                        <div className="bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg p-3 text-center">
                                            <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-1">Tendencia de Crecimiento</p>
                                            <h3 className={`text-xl font-bold ${analytics.kpis.trend_percentage > 0 ? 'text-emerald-500' : analytics.kpis.trend_percentage < 0 ? 'text-red-500' : 'text-slate-500'}`}>
                                                {analytics.kpis.trend_percentage > 0 ? '+' : ''}{analytics.kpis.trend_percentage}%
                                            </h3>
                                            <p className="text-xs font-medium text-slate-500 mt-1">Respecto al mes anterior</p>
                                        </div>
                                        <div className="bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg p-3 text-center">
                                            <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-1">Mes Pico (Récord)</p>
                                            <h3 className="text-xl font-bold text-blue-500">{analytics.kpis.peak_month.avg}</h3>
                                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mt-1">{analytics.kpis.peak_month.month}</p>
                                        </div>
                                    </div>
                                    
                                    {/* Gráfico de Barras CSS */}
                                    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-white/10 rounded-md p-4 shadow-sm">
                                        <h3 className="text-[11px] font-semibold uppercase tracking-wide text-slate-400 mb-3">Asistencia Promedio por Mes</h3>
                                        
                                        {analytics.monthly_data.length === 0 ? (
                                            <div className="text-center py-2 text-slate-400 text-sm">No hay datos suficientes para graficar.</div>
                                        ) : (
                                            <div className="flex items-end gap-2 h-48 mt-4 w-full overflow-x-auto pb-4 scrollbar-thin">
                                                {analytics.monthly_data.map((d) => {
                                                    // Calculate height percentage relative to peak month
                                                    const maxAvg = analytics.kpis.peak_month.avg || 1;
                                                    const heightPct = Math.max(5, Math.round((d.avg_attendance / maxAvg) * 100));
                                                    
                                                    return (
                                                        <div key={d.month} className="flex-1 min-w-[40px] max-w-[80px] flex flex-col items-center justify-end group">
                                                            <div className="opacity-0 group-hover:opacity-100 transition-opacity bg-slate-800 text-white text-[10px] font-bold px-2 py-1 rounded-md mb-2 whitespace-nowrap">
                                                                {d.avg_attendance} asis.
                                                            </div>
                                                            <div 
                                                                className="w-full bg-blue-100 dark:bg-blue-900/40 hover:bg-blue-500 dark:hover:bg-blue-500 rounded-t-lg transition-all duration-500" 
                                                                style={{ height: `${heightPct}%` }}
                                                            ></div>
                                                            <div className="mt-2 text-[9px] font-semibold uppercase tracking-wide text-slate-400 rotate-[-45deg] origin-top-left translate-y-2 translate-x-2">
                                                                {d.month}
                                                            </div>
                                                        </div>
                                                    );
                                                })}
                                            </div>
                                        )}
                                    </div>
                                </>
                            )}
                        </div>
                    )}
                    
                    {activeTab === 'session' && (
                        <div className="space-y-3">
                            {/* Toolbar de Sesion */}
                            <div className="flex flex-col md:flex-row gap-4 items-end bg-white dark:bg-white/5 p-4 rounded-md border border-slate-100 dark:border-white/5 shadow-sm">
                                <div className="flex-1 w-full">
                                    <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-2 block">Fecha de la Sesion</label>
                                    <div className="relative">
                                        <Calendar className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
                                        <input 
                                            type="date" 
                                            value={sessionDate}
                                            onChange={(e) => setSessionDate(e.target.value)}
                                            className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-lg py-1.5 pl-11 pr-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500"
                                        />
                                    </div>
                                </div>
                                <div className="flex items-center gap-4">
                                    <button 
                                        onClick={saveSession}
                                        disabled={savingSession || !sessionDate}
                                        className="px-3 py-1.5 bg-blue-600 text-white rounded-lg text-[10px] font-semibold uppercase tracking-wide shadow-lg shadow-blue-500/30 hover:scale-105 transition-all flex items-center gap-2 disabled:opacity-60 disabled:hover:scale-100"
                                    >
                                        <Save size={16}/> {savingSession ? 'Guardando...' : 'Guardar Agenda'}
                                    </button>
                                </div>
                            </div>

                            {sessionLoading ? (
                                <div className="p-4 text-center animate-pulse font-bold text-slate-400">Cargando datos de la sesion...</div>
                            ) : (
                                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                                    {/* AGENDA PANNEL */}
                                    <div className="bg-white dark:bg-white/5 rounded-md border border-slate-200 dark:border-white/5 p-4 shadow-sm">
                                        <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-800 dark:text-white mb-3 flex items-center gap-2">
                                            <Mic className="text-blue-600" size={18}/> Agenda de la Reunion
                                        </h3>
                                        <div className="space-y-3">
                                            <MemberSelect 
                                                label="Maestro de Ceremonia"
                                                members={members}
                                                value={mcId}
                                                onChange={(next) => setMcId(typeof next === 'number' ? next : null)}
                                            />
                                            <div className="h-px bg-slate-100 dark:bg-white/5 w-full my-4" />
                                            <MemberSelect 
                                                label="Predicador(es)"
                                                members={members}
                                                value={preacherIds}
                                                onChange={(next) => setPreacherIds(Array.isArray(next) ? next : [])}
                                                multi
                                            />
                                            <div className="h-px bg-slate-100 dark:bg-white/5 w-full my-4" />
                                            <MemberSelect 
                                                label="Palabra de Ofrenda"
                                                members={members}
                                                value={offeringId}
                                                onChange={(next) => setOfferingId(typeof next === 'number' ? next : null)}
                                            />
                                        </div>
                                    </div>

                                    {/* ATTENDANCE PANNEL */}
                                    <div className="space-y-3">
                                        <div className="bg-white dark:bg-white/5 rounded-md border border-slate-200 dark:border-white/5 p-4 shadow-sm">
                                            <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-800 dark:text-white mb-3 flex items-center gap-2">
                                                <Users className="text-emerald-500" size={18}/> Reporte de Asistencia
                                            </h3>
                                            <div className="flex items-center gap-4 mb-3">
                                                <div className="size-8 rounded-md bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 flex items-center justify-center text-lg font-bold">
                                                    {sessionData?.total_attendance || 0}
                                                </div>
                                                <div>
                                                    <p className="text-lg font-bold text-slate-800 dark:text-white">Asistentes Totales</p>
                                                    <p className="text-xs font-bold text-slate-500 uppercase tracking-wide">Registrados en check-in</p>
                                                </div>
                                            </div>

                                            <div className="space-y-4">
                                                <h4 className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Desglose por Ministerio / Perfil</h4>
                                                {sessionData?.metrics && Object.entries(sessionData.metrics).map(([key, val]) => (
                                                    <div key={key} className="flex items-center justify-between p-3 rounded-md bg-slate-50 dark:bg-white/5">
                                                        <span className="text-sm font-bold text-slate-700 dark:text-slate-300">{key}</span>
                                                        <span className="text-sm font-semibold text-blue-600 bg-blue-100 dark:bg-blue-900/30 px-3 py-1 rounded-lg">{val}</span>
                                                    </div>
                                                ))}
                                            </div>

                                            {/* Absentees Banner */}
                                            {(sessionData?.total_absentees ?? 0) > 0 && (
                                                <div className="mt-3 p-4 rounded-lg bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-500/20 flex items-center justify-between gap-4">
                                                    <div>
                                                        <p className="text-xs font-semibold uppercase tracking-wide text-amber-700 dark:text-amber-400">Inasistentes</p>
                                                        <p className="text-lg font-bold text-amber-700 dark:text-amber-400 mt-0.5">{sessionData?.total_absentees}</p>
                                                        {sessionData?.absentees_truncated && (
                                                            <p className="text-[10px] text-amber-600/70 mt-1">Mostrando {sessionData?.absentees?.length} de {sessionData?.total_absentees}. Descarga el CSV para ver todos.</p>
                                                        )}
                                                    </div>
                                                    <button
                                                        onClick={handleExportCsv}
                                                        disabled={exportingCsv}
                                                        className="shrink-0 px-4 py-2 bg-amber-500 hover:bg-amber-600 text-white rounded-md text-[10px] font-semibold uppercase tracking-wide transition-all flex items-center gap-2 disabled:opacity-60"
                                                    >
                                                        <Download size={12} /> {exportingCsv ? 'Exportando...' : 'Exportar Lista'}
                                                    </button>
                                                </div>
                                            )}

                                            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-3">
                                                <div className="rounded-lg border border-slate-100 dark:border-white/5 bg-slate-50 dark:bg-white/5 p-4">
                                                    <div className="flex items-center justify-between mb-3">
                                                        <h4 className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Personas presentes</h4>
                                                        <span className="text-[10px] font-semibold uppercase tracking-wide text-emerald-600">{sessionData?.attendees?.length ?? 0}</span>
                                                    </div>
                                                    <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                                                        {(sessionData?.attendees || []).length === 0 ? (
                                                            <p className="text-sm text-slate-400">Sin registros de asistentes.</p>
                                                        ) : (
                                                            sessionData!.attendees.map((att) => (
                                                                <div key={`${att.member_id}-${att.role}`} className="flex items-center justify-between gap-3 rounded-md bg-white dark:bg-[#1e1f21] border border-slate-100 dark:border-white/5 px-3 py-2">
                                                                    <div className="min-w-0">
                                                                        <p className="text-sm font-bold text-slate-800 dark:text-white truncate">{att.name}</p>
                                                                        <p className="text-[10px] uppercase font-bold tracking-wide text-slate-400">{att.role}</p>
                                                                    </div>
                                                                    <span className="text-[10px] font-semibold uppercase tracking-wide text-emerald-600">
                                                                        {att.scanned_at ? new Date(att.scanned_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'OK'}
                                                                    </span>
                                                                </div>
                                                            ))
                                                        )}
                                                    </div>
                                                </div>

                                                <div className="rounded-lg border border-slate-100 dark:border-white/5 bg-slate-50 dark:bg-white/5 p-4">
                                                    <div className="flex items-center justify-between mb-3">
                                                        <h4 className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Personas ausentes</h4>
                                                        <span className="text-[10px] font-semibold uppercase tracking-wide text-amber-600">{sessionData?.absentees?.length ?? 0}</span>
                                                    </div>
                                                    <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                                                        {(sessionData?.absentees || []).length === 0 ? (
                                                            <p className="text-sm text-slate-400">No hay ausentes en esta sesión.</p>
                                                        ) : (
                                                            sessionData!.absentees.map((att) => (
                                                                <div key={`${att.member_id}-${att.role}`} className="flex items-center justify-between gap-3 rounded-md bg-white dark:bg-[#1e1f21] border border-slate-100 dark:border-white/5 px-3 py-2">
                                                                    <div className="min-w-0">
                                                                        <p className="text-sm font-bold text-slate-800 dark:text-white truncate">{att.name}</p>
                                                                        <p className="text-[10px] uppercase font-bold tracking-wide text-slate-400">{att.role}</p>
                                                                    </div>
                                                                    <span className="text-[10px] font-semibold uppercase tracking-wide text-rose-600">Ausente</span>
                                                                </div>
                                                            ))
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </main>

        {/* DRAWER Visitante */}
        <WorkspaceDrawer
            isOpen={isVisitorModalOpen}
            onClose={() => setIsVisitorModalOpen(false)}
            title="Nuevo Visitante"
            subtitle="Registra a una persona no perteneciente a la base de datos"
            actions={
                <>
                    <button type="button" disabled={savingVisitor} onClick={() => setIsVisitorModalOpen(false)} className="px-4 py-2 text-[11px] font-bold text-slate-500 hover:text-slate-700 transition-colors disabled:opacity-60">
                        Cancelar
                    </button>
                    <button type="button" onClick={handleAddVisitor} disabled={savingVisitor || !visitorForm.first_name || !visitorForm.last_name} className="flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded-lg text-[11px] font-semibold uppercase tracking-wide shadow-lg shadow-blue-500/30 hover:bg-blue-700 transition-all disabled:opacity-60">
                        <CheckCircle2 size={16} /> {savingVisitor ? 'Guardando...' : 'Guardar Asistencia'}
                    </button>
                </>
            }
        >
            <div className="space-y-3 mt-4">
                <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1.5">
                        <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 block">Nombre</label>
                        <input required disabled={savingVisitor} value={visitorForm.first_name} onChange={e => setVisitorForm({...visitorForm, first_name: e.target.value})} className="w-full px-4 py-1.5 bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-md text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-60" placeholder="Juan" />
                    </div>
                    <div className="space-y-1.5">
                        <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 block">Apellido</label>
                        <input required value={visitorForm.last_name} onChange={e => setVisitorForm({...visitorForm, last_name: e.target.value})} className="w-full px-4 py-1.5 bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-md text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500" placeholder="Pérez" />
                    </div>
                </div>
                <div className="space-y-1.5">
                    <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 block">Teléfono (WhatsApp)</label>
                    <input disabled={savingVisitor} value={visitorForm.phone} onChange={e => setVisitorForm({...visitorForm, phone: e.target.value})} className="w-full px-4 py-1.5 bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-md text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-60" placeholder="+57 300 000 0000" />
                </div>
                <div className="space-y-1.5">
                    <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 block">Correo Electrónico (Opcional)</label>
                    <input type="email" disabled={savingVisitor} value={visitorForm.email} onChange={e => setVisitorForm({...visitorForm, email: e.target.value})} className="w-full px-4 py-1.5 bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-md text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-60" placeholder="correo@ejemplo.com" />
                </div>
            </div>
        </WorkspaceDrawer>

        </EvangelismShell>
    );
}
