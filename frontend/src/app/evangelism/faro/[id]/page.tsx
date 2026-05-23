'use client';

import React, { useState, useEffect, useMemo } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { useSidebarLayers } from '@/context/SidebarLayerContext';
import EvangelismShell from '@/components/evangelism/EvangelismShell';

import {
    Home, MapPin, Users, Calendar, CheckCircle2, Clock,
    ArrowLeft, Search, UserPlus, Loader2, ChevronRight, Plus,
    BarChart3, Activity
} from 'lucide-react';
import { toast } from 'sonner';

interface HouseDetail {
    id: number; name: string; zone?: string; address?: string;
    code?: string; leader_name?: string; members_count?: number; capacity?: number;
    day_of_week?: string; time?: string; status?: string;
    sessions: SessionRow[]; total_sessions: number; total_attendance: number;
    monitoring?: HouseMonitoring;
}
interface SessionRow { id: number; session_date: string; status: string; season_name?: string; attendance_count: number; topic?: string; report_deadline?: string; }
interface MonitoringTrendRow {
    session_id: number;
    session_date: string;
    status: string;
    attendance_rate: number;
    present_count: number;
    absent_count: number;
}
interface RepeatAbsentee {
    member_id: number;
    name: string;
    absences: number;
    details: { session_id: number; session_date?: string | null; reason?: string | null; reason_detail?: string | null }[];
}
interface MonitoringAlert {
    type: string;
    message: string;
    session_id?: number;
}
interface HouseMonitoring {
    expected_members: number;
    average_attendance: number;
    average_attendance_rate: number;
    attendance_trend: MonitoringTrendRow[];
    recent_sessions: MonitoringTrendRow[];
    repeat_absentees: RepeatAbsentee[];
    alerts: MonitoringAlert[];
}
type AttendanceReason = 'weather' | 'work' | 'health' | 'family' | 'other';
interface AttendanceData {
    session_id: number;
    session_date: string;
    glory_house_id: number;
    status: string;
    topic?: string | null;
    offering_amount?: number | null;
    report_notes?: string | null;
    novelty_type?: string | null;
    novelty_detail?: string | null;
    cancellation_reason?: string | null;
    reported_by_member_id?: number | null;
    total: number;
    present_count?: number;
    absent_count?: number;
    attendees: AttendeeRow[];
    absentees: AttendeeRow[];
    expected_members: AttendeeRow[];
}
interface AttendeeRow { member_id: number; name: string; role?: string; attended?: boolean; absence_reason?: AttendanceReason | null; absence_reason_detail?: string | null; scanned_at?: string; }
interface Member { id: number; first_name: string; last_name: string; church_role?: string; }

export default function FaroDetailPage() {
    const params = useParams();
    const id = params?.id as string | undefined;
    const router = useRouter();
    const { token, user } = useAuth();
    const { pushSidebarPanel } = useSidebarLayers();

    const [house, setHouse] = useState<HouseDetail | null>(null);
    const [loading, setLoading] = useState(true);

    // Active session attendance
    const [activeSession, setActiveSession] = useState<SessionRow | null>(null);
    const [attendance, setAttendance] = useState<AttendanceData | null>(null);
    const [loadingAtt, setLoadingAtt] = useState(false);
    const [savingReport, setSavingReport] = useState(false);

    // Member selector
    const [members, setMembers] = useState<Member[]>([]);
    const [showAddAttendee, setShowAddAttendee] = useState(false);
    const [memberQuery, setMemberQuery] = useState('');
    const [saving, setSaving] = useState(false);
    const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
    const [reportTopic, setReportTopic] = useState('');
    const [reportOfferingAmount, setReportOfferingAmount] = useState('');
    const [reportNotes, setReportNotes] = useState('');
    const [reportNoveltyType, setReportNoveltyType] = useState('');
    const [reportNoveltyDetail, setReportNoveltyDetail] = useState('');
    const [reportCancellationReason, setReportCancellationReason] = useState('');
    const [reportStatus, setReportStatus] = useState<'Realizada' | 'Cancelada' | 'No realizada'>('Realizada');
    const [reportMembers, setReportMembers] = useState<AttendeeRow[]>([]);

    // Se eliminÃ³ la dependencia de layers.RIGHT para showAddAttendee porque ahora usamos WorkspaceDrawer

    const [isCreatingMember, setIsCreatingMember] = useState(false);
    const [newMemberForm, setNewMemberForm] = useState({ first_name: '', last_name: '', phone: '', email: '' });
    const [creatingMember, setCreatingMember] = useState(false);
    const role = String(user?.role || '').toLowerCase();
    const isPrivileged = role === 'admin' || role === 'pastor';

    // Load house detail
    useEffect(() => {
        if (!token || !id) return;
        setLoading(true);
        apiFetch<HouseDetail>(`/evangelism/glory-houses/${id}`, { token })
            .then(data => {
                setHouse(data);
                // Auto-select the most recent session
                if (data.sessions.length > 0) setActiveSession(data.sessions[0]);
            })
            .catch(() => toast.error('Error al cargar el Faro'))
            .finally(() => setLoading(false));
    }, [id, token]);

    // PUSH SESSIONS LIST TO SIDEBAR
    useEffect(() => {
        if (!house) return;
        pushSidebarPanel({
            id: 'faro-sessions-list',
            title: 'Faro en Casa',
            replaceAll: true,
            content: (
                <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21]">
                    <div className="px-3 pt-4 pb-3 border-b border-slate-100 dark:border-white/5">
                        <button onClick={() => router.back()} className="flex items-center gap-1.5 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition-colors mb-3 text-[10px] font-semibold uppercase tracking-wide">
                            <ArrowLeft size={14} /> Volver a Faros
                        </button>
                        <p className="text-xs font-semibold text-slate-800 dark:text-white truncate mb-4">{house.name}</p>
                        <h2 className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 flex items-center gap-2">
                            <Calendar size={12} /> Sesiones Registradas
                        </h2>
                        {/* New Session Action */}
                        {isPrivileged && <button 
                            onClick={() => {
                                apiFetch(`/evangelism/faro/sessions`, {
                                    method: 'POST',
                                    body: {
                                        glory_house_id: house.id,
                                        session_date: new Date().toISOString().split('T')[0],
                                        season_id: house.sessions[0]?.season_name ? null : undefined // Backend automatically grabs active season if we omit or pass null if properly wired, but let's just make it simple.
                                    },
                                    token
                                }).then(() => {
                                    toast.success('Nueva sesiÃ³n creada');
                                    // Trigger reload by mutating house
                                    window.location.reload();
                                }).catch(() => toast.error('Error al crear sesiÃ³n. Puede que ya exista para hoy.'));
                            }}
                            className="mt-3 w-full py-2 bg-slate-100 hover:bg-slate-200 dark:bg-white/5 dark:hover:bg-white/10 text-slate-700 dark:text-slate-200 rounded-lg text-[10px] font-semibold uppercase tracking-wide transition-colors flex items-center justify-center gap-1.5"
                        >
                            <Plus size={12} /> Registrar sesiÃ³n de esta semana
                        </button>}
                    </div>
                    <div className="flex-1 overflow-y-auto px-3 py-2 space-y-1 scrollbar-thin">
                        {house.sessions.length === 0 ? (
                            <div className="py-1.5 text-center text-slate-400">
                                <Calendar size={24} className="mx-auto mb-3 opacity-30" />
                                <p className="text-[11px] font-semibold uppercase tracking-wide">Sin sesiones</p>
                            </div>
                        ) : house.sessions.map(s => {
                            const isActive = activeSession?.id === s.id;
                            return (
                                <button
                                    key={s.id}
                                    onClick={() => setActiveSession(s)}
                                    className={`w-full text-left px-3 py-2.5 rounded-md border transition-all duration-200 ${isActive
                                        ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800 shadow-sm'
                                        : 'bg-transparent border-transparent hover:bg-slate-100 dark:hover:bg-white/5'
                                    }`}
                                >
                                    <div className="flex items-center justify-between">
                                        <div>
                                            <p className={`text-xs font-bold ${isActive ? 'text-blue-700 dark:text-blue-400' : 'text-slate-800 dark:text-white'}`}>
                                                {s.topic ? s.topic : new Date(s.session_date + 'T12:00:00').toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'short' })}
                                            </p>
                                            {s.topic && <p className="text-[10px] font-medium text-slate-400 mt-0.5">{new Date(s.session_date + 'T12:00:00').toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'short' })}</p>}
                                            {s.season_name && !s.topic && <p className="text-[10px] font-medium text-slate-400 mt-0.5">{s.season_name}</p>}
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <span className={`px-2 py-0.5 rounded-lg font-semibold ${isActive ? 'bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300' : 'bg-slate-100 dark:bg-white/10 text-slate-500'}`}>
                                                {s.attendance_count}
                                            </span>
                                            <ChevronRight size={14} className={isActive ? 'text-blue-500' : 'text-slate-300'} />
                                        </div>
                                    </div>
                                </button>
                            );
                        })}
                    </div>
                </div>
            )
        });
    }, [house, activeSession, isPrivileged, router, pushSidebarPanel, token]);

    // Load attendance when session changes
    useEffect(() => {
        if (!token || !activeSession) return;
        setLoadingAtt(true);
        apiFetch<AttendanceData>(`/evangelism/faro/sessions/${activeSession.id}/attendance`, { token })
            .then(data => {
                setAttendance(data);
                
                // Merge expected members and attendees perfectly
                const mergedMap = new Map<number, AttendeeRow>();
                
                // First add all expected members
                (data.expected_members || []).forEach(row => {
                    mergedMap.set(row.member_id, {
                        ...row,
                        // By default, if there is no attendance data yet, mark them as 'attended: false' initially? 
                        // The user said: "no me dijiste quines fueron y quines no".
                        // Wait, if we mark attended: false, they show as absent. 
                        // Let's rely on the row.attended property if it exists, otherwise false.
                        attended: row.attended ?? false,
                    });
                });
                
                // Then add/overwrite with any explicit attendees (extra guests added via Add Attendee)
                (data.attendees || []).forEach(row => {
                    if (mergedMap.has(row.member_id)) {
                        mergedMap.get(row.member_id)!.attended = true;
                        mergedMap.get(row.member_id)!.scanned_at = row.scanned_at;
                    } else {
                        mergedMap.set(row.member_id, {
                            ...row,
                            attended: true,
                        });
                    }
                });
                
                setReportMembers(Array.from(mergedMap.values()));
                setReportTopic(data.topic || '');
                setReportOfferingAmount(data.offering_amount != null ? String(data.offering_amount) : '');
                setReportNotes(data.report_notes || '');
                setReportNoveltyType(data.novelty_type || '');
                setReportNoveltyDetail(data.novelty_detail || '');
                setReportCancellationReason(data.cancellation_reason || '');
                const nextStatus =
                    data.status === 'Cancelada' || data.status === 'No realizada' || data.status === 'Realizada'
                        ? data.status
                        : 'Realizada';
                setReportStatus(nextStatus);
            })
            .catch(() => {})
            .finally(() => setLoadingAtt(false));
    }, [activeSession, token]);

    // Load members for selector
    useEffect(() => {
        if (!token || !showAddAttendee) return;
        apiFetch<Member[]>('/crm/members/', { token }).then(setMembers).catch(() => {});
    }, [showAddAttendee, token]);

    const filteredMembers = useMemo(() => {
        const q = memberQuery.toLowerCase();
        const attendedIds = new Set(attendance?.attendees.map(a => a.member_id) || []);
        return members
            .filter(m => !attendedIds.has(m.id))
            .filter(m => !q || `${m.first_name} ${m.last_name}`.toLowerCase().includes(q))
            .slice(0, 30);
    }, [members, memberQuery, attendance]);

    const handleSaveAttendance = async () => {
        if (!activeSession || selectedIds.size === 0) return;
        setSaving(true);
        try {
            const res = await apiFetch<{ added: number }>(`/evangelism/faro/sessions/${activeSession.id}/attendance`, {
                method: 'POST', body: { member_ids: Array.from(selectedIds) }, token
            });
            toast.success(`${res.added} asistente(s) registrados`);
            setShowAddAttendee(false);
            setSelectedIds(new Set());
            setMemberQuery('');
            // Reload attendance
            const updated = await apiFetch<AttendanceData>(`/evangelism/faro/sessions/${activeSession.id}/attendance`, { token });
            setAttendance(updated);
            // Update session count in list
            if (house) {
                setHouse(prev => prev ? {
                    ...prev,
                    sessions: prev.sessions.map(s => s.id === activeSession.id ? { ...s, attendance_count: updated.total } : s)
                } : prev);
            }
        } catch { toast.error('Error al guardar asistencia'); }
        finally { setSaving(false); }
    };

    const handleCreateMember = async () => {
        if (!newMemberForm.first_name || !newMemberForm.last_name) {
            return toast.error('El nombre y apellido son obligatorios');
        }
        setCreatingMember(true);
        try {
            const res = await apiFetch<Member>('/crm/members/', {
                method: 'POST',
                token,
                body: { ...newMemberForm, church_role: 'Visitante Faro en Casa' }
            });
            toast.success('Invitado creado con Ã©xito');
            setMembers(prev => [res, ...prev]);
            setSelectedIds(prev => new Set(prev).add(res.id));
            setNewMemberForm({ first_name: '', last_name: '', phone: '', email: '' });
            setIsCreatingMember(false);
        } catch {
            toast.error('Error al crear el invitado');
        } finally {
            setCreatingMember(false);
        }
    };

    const handleSaveReport = async () => {
        if (!activeSession) return;
        setSavingReport(true);
        try {
            const attendees = reportMembers.map((row) => ({
                member_id: row.member_id,
                attended: row.attended ?? true,
                absence_reason: row.attended ? null : row.absence_reason,
                absence_reason_detail: row.attended ? null : row.absence_reason_detail,
            }));
            await apiFetch<{ status: string }>(`/evangelism/faro/sessions/${activeSession.id}/attendance`, {
                method: 'POST',
                token,
                body: {
                    status: reportStatus,
                    topic: reportTopic,
                    offering_amount: reportOfferingAmount ? Number(reportOfferingAmount) : null,
                    report_notes: reportNotes,
                    novelty_type: reportNoveltyType || null,
                    novelty_detail: reportNoveltyDetail || null,
                    cancellation_reason: reportCancellationReason || null,
                    attendees,
                }
            });
            toast.success('Reporte semanal guardado');
            const updated = await apiFetch<AttendanceData>(`/evangelism/faro/sessions/${activeSession.id}/attendance`, { token });
            setAttendance(updated);
            setHouse(prev => prev ? {
                ...prev,
                sessions: prev.sessions.map(s => s.id === activeSession.id ? { ...s, attendance_count: updated.total } : s)
            } : prev);
        } catch {
            toast.error('Error al guardar el reporte');
        } finally {
            setSavingReport(false);
        }
    };

    const reasonOptions: { value: AttendanceReason; label: string }[] = [
        { value: 'weather', label: 'Clima' },
        { value: 'work', label: 'Trabajo' },
        { value: 'health', label: 'Salud' },
        { value: 'family', label: 'Familia' },
        { value: 'other', label: 'Otro' },
    ];

    if (loading) return (
        <EvangelismShell breadcrumbs={[{ label: 'Faro en Casa', href: '/evangelism/faro', icon: Home }, { label: '...', icon: Home }]}>
            <div className="flex items-center justify-center h-full"><Loader2 className="animate-spin text-blue-500" size={40} /></div>
        </EvangelismShell>
    );

    if (!house) return (
        <EvangelismShell breadcrumbs={[{ label: 'Faro en Casa', href: '/evangelism/faro', icon: Home }]}>
            <div className="p-4 text-center text-slate-400">Faro no encontrado.</div>
        </EvangelismShell>
    );

    const avgAttendance = house.total_sessions > 0 ? Math.round(house.total_attendance / house.total_sessions) : 0;
    const monitoring = house.monitoring;
    const trendRows = monitoring?.attendance_trend ?? [];
    const alerts = monitoring?.alerts ?? [];
    const repeatAbsentees = monitoring?.repeat_absentees ?? [];

    return (
        <EvangelismShell breadcrumbs={[
            { label: 'Faro en Casa', href: '/evangelism/faro', icon: Home },
            { label: house.name, icon: Home }
        ]}>
            <main className="flex-1 overflow-y-auto">
                {/* Page Header */}
                <div className="px-3 pt-8 pb-6 border-b border-slate-100 dark:border-white/5">
                    <button onClick={() => router.back()} className="flex items-center gap-1.5 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition-colors mb-4 text-xs font-bold uppercase tracking-wide">
                        <ArrowLeft size={14} /> Volver
                    </button>
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                        <div>
                            <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-1">Faro en Casa</p>
                            <h1 className="text-lg font-black text-slate-900 dark:text-white tracking-tight">{house.name}</h1>
                            <div className="flex flex-wrap gap-4 text-xs text-slate-500 dark:text-slate-400 font-medium mt-1.5">
                                {house.code && <span className="flex items-center gap-1.5"><Activity size={12} /> CÃ³digo: {house.code}</span>}
                                {house.leader_name && <span className="flex items-center gap-1.5"><Users size={12} /> LÃ­der: {house.leader_name}</span>}
                                {house.address && <span className="flex items-center gap-1.5"><MapPin size={12} /> {house.address}</span>}
                                {house.day_of_week && <span className="flex items-center gap-1.5"><Clock size={12} /> {house.day_of_week} {house.time || ''}</span>}
                            </div>
                        </div>
                        <div className="flex gap-3 shrink-0">
                            <div className="text-center px-3 py-1.5 bg-white dark:bg-[#252528] rounded-md border border-slate-200 dark:border-white/5 shadow-sm">
                                <p className="text-base font-black text-slate-900 dark:text-white">{house.total_sessions}</p>
                                <p className="text-[10px] text-slate-400 font-semibold uppercase tracking-wide mt-0.5">Sesiones</p>
                            </div>
                            <div className="text-center px-3 py-1.5 bg-white dark:bg-[#252528] rounded-md border border-slate-200 dark:border-white/5 shadow-sm">
                                <p className="text-base font-black text-slate-900 dark:text-white">{house.total_attendance}</p>
                                <p className="text-[10px] text-slate-400 font-semibold uppercase tracking-wide mt-0.5">Asistentes</p>
                            </div>
                            <div className="text-center px-3 py-1.5 bg-white dark:bg-[#252528] rounded-md border border-slate-200 dark:border-white/5 shadow-sm">
                                <p className="text-base font-black text-slate-900 dark:text-white">{avgAttendance}</p>
                                <p className="text-[10px] text-slate-400 font-semibold uppercase tracking-wide mt-0.5">Promedio</p>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="p-4">
                    {/* ATTENDANCE PANEL */}
                    <div className="w-full">
                        {!activeSession ? (
                            <div className="h-full flex items-center justify-center py-1.5 text-slate-400">
                                <div className="text-center">
                                    <Activity size={40} className="mx-auto mb-4 opacity-30" />
                                    <p className="font-bold">Selecciona una sesiÃ³n para ver la asistencia</p>
                                </div>
                            </div>
                        ) : (
                            <div className="space-y-2">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <h2 className="text-sm font-semibold text-slate-900 dark:text-white">
                                            {activeSession.topic ? activeSession.topic : new Date(activeSession.session_date + 'T12:00:00').toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
                                        </h2>
                                        {activeSession.topic && <p className="text-xs text-slate-400 font-bold mt-0.5">{new Date(activeSession.session_date + 'T12:00:00').toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}</p>}
                                        {activeSession.season_name && !activeSession.topic && <p className="text-xs text-slate-400 font-bold mt-0.5">{activeSession.season_name}</p>}
                                    </div>
                                    <button
                                        onClick={() => setShowAddAttendee(true)}
                                        className="flex items-center gap-2 px-3 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-[11px] font-semibold uppercase tracking-wide transition-all shadow-lg shadow-blue-500/20"
                                    >
                                        <UserPlus size={14} /> AÃ±adir Asistentes
                                    </button>
                                </div>

                                {/* Stat strip */}
                                <div className="flex gap-4">
                                    <div className="flex-1 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg p-4 text-center">
                                        <p className="text-lg font-black text-blue-600 dark:text-blue-400">{loadingAtt ? 'â€”' : attendance?.total ?? 0}</p>
                                        <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mt-1">Presentes</p>
                                    </div>
                                    <div className="flex-1 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg p-4 text-center">
                                        <p className="text-lg font-black text-slate-700 dark:text-slate-300">{house.capacity ?? 'â€”'}</p>
                                        <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mt-1">Capacidad</p>
                                    </div>
                                    <div className="flex-1 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg p-4 text-center">
                                        <p className="text-lg font-black text-emerald-600 dark:emerald-400">
                                            {house.capacity && attendance ? `${Math.round(attendance.total / house.capacity * 100)}%` : 'â€”'}
                                        </p>
                                        <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mt-1">OcupaciÃ³n</p>
                                    </div>
                                </div>

                                <div className="bg-white dark:bg-white/5 rounded-md border border-slate-200 dark:border-white/5 p-4 shadow-sm space-y-2">
                                    <div className="flex items-center justify-between gap-4">
                                        <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-800 dark:text-white flex items-center gap-2">
                                            <BarChart3 className="text-indigo-500" size={18} /> Monitoreo de la casa
                                        </h3>
                                        <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                                            {monitoring?.expected_members ?? 0} esperados
                                        </span>
                                    </div>

                                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                        <div className="rounded-lg border border-slate-200 dark:border-white/10 p-4 bg-slate-50 dark:bg-black/20">
                                            <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Promedio de presencia</p>
                                            <p className="mt-2 text-lg font-black text-slate-900 dark:text-white">{monitoring?.average_attendance ?? avgAttendance}</p>
                                        </div>
                                        <div className="rounded-lg border border-slate-200 dark:border-white/10 p-4 bg-slate-50 dark:bg-black/20">
                                            <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Tasa promedio</p>
                                            <p className="mt-2 text-lg font-black text-slate-900 dark:text-white">{monitoring?.average_attendance_rate ?? 0}%</p>
                                        </div>
                                        <div className="rounded-lg border border-slate-200 dark:border-white/10 p-4 bg-slate-50 dark:bg-black/20">
                                            <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Alertas activas</p>
                                            <p className="mt-2 text-lg font-black text-slate-900 dark:text-white">{alerts.length}</p>
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                                        <div className="rounded-lg border border-slate-200 dark:border-white/10 p-4">
                                            <div className="flex items-center justify-between mb-4">
                                                <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Tendencia reciente</p>
                                                <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">{trendRows.length} sesiones</p>
                                            </div>
                                            <div className="space-y-3">
                                                {trendRows.length === 0 ? (
                                                    <p className="text-sm text-slate-400">No hay datos de tendencia todavÃ­a.</p>
                                                ) : trendRows.map((row) => (
                                                    <div key={row.session_id} className="flex items-center justify-between gap-4 rounded-lg bg-slate-50 dark:bg-black/20 px-4 py-1.5">
                                                        <div className="min-w-0">
                                                            <p className="text-sm font-bold text-slate-800 dark:text-white truncate">
                                                                {new Date(row.session_date + 'T12:00:00').toLocaleDateString('es-CO', { month: 'short', day: 'numeric' })}
                                                            </p>
                                                            <p className="text-[10px] font-medium text-slate-400">{row.status}</p>
                                                        </div>
                                                        <div className="text-right shrink-0">
                                                            <p className="text-sm font-semibold text-slate-900 dark:text-white">{row.attendance_rate}%</p>
                                                            <p className="text-[10px] font-medium text-slate-400">{row.present_count}/{row.present_count + row.absent_count}</p>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>

                                        <div className="rounded-lg border border-slate-200 dark:border-white/10 p-4">
                                            <div className="flex items-center justify-between mb-4">
                                                <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Alertas</p>
                                                <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">{repeatAbsentees.length} reincidentes</p>
                                            </div>
                                            <div className="space-y-3">
                                                {alerts.length === 0 && repeatAbsentees.length === 0 ? (
                                                    <p className="text-sm text-slate-400">Sin alertas activas.</p>
                                                ) : (
                                                    <>
                                                        {alerts.map((alert, index) => (
                                                            <div key={`${alert.type}-${index}`} className="rounded-lg border border-amber-200 dark:border-amber-500/30 bg-amber-50 dark:bg-amber-500/10 px-4 py-1.5">
                                                                <p className="text-sm font-bold text-amber-800 dark:text-amber-200">{alert.message}</p>
                                                            </div>
                                                        ))}
                                                        {repeatAbsentees.slice(0, 4).map((item) => (
                                                            <div key={item.member_id} className="rounded-lg border border-rose-200 dark:border-rose-500/30 bg-rose-50 dark:bg-rose-500/10 px-4 py-1.5">
                                                                <p className="text-sm font-bold text-rose-800 dark:text-rose-200">{item.name}</p>
                                                                <p className="text-[10px] font-semibold uppercase tracking-wide text-rose-500 mt-1">{item.absences} ausencias recurrentes</p>
                                                            </div>
                                                        ))}
                                                    </>
                                                )}
                                            </div>
                                        </div>
                                    </div>

                                    <div className="flex items-center justify-between gap-4">
                                        <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-800 dark:text-white flex items-center gap-2">
                                            <Activity className="text-blue-500" size={18} /> Reporte semanal
                                        </h3>
                                        <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                                            {reportMembers.length} miembros
                                        </span>
                                    </div>

                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                        <div>
                                            <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-2 block">Tema tratado</label>
                                            <input
                                                value={reportTopic}
                                                onChange={(e) => setReportTopic(e.target.value)}
                                                className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-lg py-1.5 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500"
                                                placeholder="Unidad familiar, fe, oraciÃ³n..."
                                            />
                                        </div>
                                        <div>
                                            <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-2 block">Ofrenda recibida</label>
                                            <input
                                                type="number"
                                                value={reportOfferingAmount}
                                                onChange={(e) => setReportOfferingAmount(e.target.value)}
                                                className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-lg py-1.5 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500"
                                                placeholder="0"
                                                min="0"
                                                step="0.01"
                                            />
                                        </div>
                                        <div>
                                            <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-2 block">Estado</label>
                                            <select
                                                value={reportStatus}
                                                onChange={(e) => {
                                                    const nextStatus =
                                                        e.target.value === 'Cancelada' || e.target.value === 'No realizada' || e.target.value === 'Realizada'
                                                            ? e.target.value
                                                            : 'Realizada';
                                                    setReportStatus(nextStatus);
                                                }}
                                                className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-lg py-1.5 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500"
                                            >
                                                <option value="Realizada">Realizada</option>
                                                <option value="No realizada">No realizada</option>
                                                <option value="Cancelada">Cancelada</option>
                                            </select>
                                        </div>
                                        <div>
                                            <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-2 block">Novedad</label>
                                            <select
                                                value={reportNoveltyType}
                                                onChange={(e) => setReportNoveltyType(e.target.value)}
                                                className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-lg py-1.5 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500"
                                            >
                                                <option value="">Sin novedad</option>
                                                <option value="weather">Clima</option>
                                                <option value="work">Trabajo</option>
                                                <option value="health">Salud</option>
                                                <option value="family">Familia</option>
                                                <option value="other">Otro</option>
                                            </select>
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                        <div>
                                            <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-2 block">Detalle de novedad</label>
                                            <textarea
                                                value={reportNoveltyDetail}
                                                onChange={(e) => setReportNoveltyDetail(e.target.value)}
                                                className="w-full min-h-24 bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-lg p-4 text-sm font-medium outline-none focus:ring-2 focus:ring-blue-500"
                                                placeholder="Explica la novedad o la razÃ³n del ajuste..."
                                            />
                                        </div>
                                        <div>
                                            <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-2 block">Motivo de cancelaciÃ³n</label>
                                            <textarea
                                                value={reportCancellationReason}
                                                onChange={(e) => setReportCancellationReason(e.target.value)}
                                                className="w-full min-h-24 bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-lg p-4 text-sm font-medium outline-none focus:ring-2 focus:ring-blue-500"
                                                placeholder="Si no se realizÃ³, explica la causa..."
                                            />
                                        </div>
                                    </div>

                                    <div>
                                        <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-2 block">Notas del reporte</label>
                                        <textarea
                                            value={reportNotes}
                                            onChange={(e) => setReportNotes(e.target.value)}
                                            className="w-full min-h-28 bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-lg p-4 text-sm font-medium outline-none focus:ring-2 focus:ring-blue-500"
                                            placeholder="Resumen pastoral, acuerdos, seguimiento..."
                                        />
                                    </div>

                                    <div className="space-y-3">
                                        <div className="flex items-center justify-between">
                                            <h4 className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Asistencia por miembro</h4>
                                            <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Presente / Ausente</span>
                                        </div>
                                        <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
                                            {reportMembers.map((row) => {
                                                const attended = row.attended !== false;
                                                return (
                                                    <div key={row.member_id} className="rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 p-4 space-y-3">
                                                        <div className="flex items-center justify-between gap-3">
                                                            <div className="min-w-0">
                                                                <p className="text-sm font-bold text-slate-800 dark:text-white truncate">{row.name}</p>
                                                                <p className="text-[10px] uppercase font-bold tracking-wide text-slate-400">{row.role || 'Miembro'}</p>
                                                            </div>
                                                            <label className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                                                                <input
                                                                    type="checkbox"
                                                                    checked={attended}
                                                                    onChange={(e) => {
                                                                        const checked = e.target.checked;
                                                                        setReportMembers(prev => prev.map(item => item.member_id === row.member_id ? {
                                                                            ...item,
                                                                            attended: checked,
                                                                            absence_reason: checked ? null : item.absence_reason || 'other',
                                                                            absence_reason_detail: checked ? null : item.absence_reason_detail || '',
                                                                        } : item));
                                                                    }}
                                                                    className="size-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                                                                />
                                                                {attended ? 'Presente' : 'Ausente'}
                                                            </label>
                                                        </div>

                                                        {!attended && (
                                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                                                <div>
                                                                    <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-2 block">RazÃ³n</label>
                                                                    <select
                                                                        value={row.absence_reason || 'other'}
                                                                        onChange={(e) => setReportMembers(prev => prev.map(item => item.member_id === row.member_id ? { ...item, absence_reason: e.target.value as AttendanceReason } : item))}
                                                                        className="w-full bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-lg py-2.5 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500"
                                                                    >
                                                                        {reasonOptions.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
                                                                    </select>
                                                                </div>
                                                                <div>
                                                                    <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-2 block">Detalle</label>
                                                                    <input
                                                                        value={row.absence_reason_detail || ''}
                                                                        onChange={(e) => setReportMembers(prev => prev.map(item => item.member_id === row.member_id ? { ...item, absence_reason_detail: e.target.value } : item))}
                                                                        className="w-full bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-lg py-2.5 px-4 text-sm font-medium outline-none focus:ring-2 focus:ring-blue-500"
                                                                        placeholder="Especifica el motivo"
                                                                    />
                                                                </div>
                                                            </div>
                                                        )}
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    </div>

                                     <div className="flex justify-end">
                                        {activeSession?.report_deadline && new Date() > new Date(activeSession.report_deadline) ? (
                                            <div className="flex items-center gap-2 text-rose-500 bg-rose-50 dark:bg-rose-500/10 px-4 py-1.5 rounded-lg">
                                                <Clock size={16} />
                                                <span className="text-[11px] font-semibold uppercase tracking-wide">Plazo de reporte vencido ({new Date(activeSession.report_deadline).toLocaleString()})</span>
                                            </div>
                                        ) : (
                                            <button
                                                onClick={handleSaveReport}
                                                disabled={savingReport || !activeSession}
                                                className="inline-flex items-center gap-2 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-[11px] font-semibold uppercase tracking-wide transition-all shadow-lg shadow-emerald-500/20 disabled:opacity-50"
                                            >
                                                {savingReport ? <Loader2 className="animate-spin" size={14} /> : <CheckCircle2 size={14} />}
                                                Guardar reporte
                                            </button>
                                        )}
                                    </div>
                                </div>

                                {/* Attendee list */}
                                {loadingAtt ? (
                                    <div className="flex items-center justify-center py-1.5"><Loader2 className="animate-spin text-blue-500" size={24} /></div>
                                ) : !attendance || attendance.attendees.length === 0 ? (
                                    <div className="py-1.5 text-center bg-slate-50 dark:bg-white/5 rounded-lg text-slate-400">
                                        <Users size={32} className="mx-auto mb-3 opacity-30" />
                                        <p className="font-bold text-sm">Sin asistentes registrados</p>
                                        <p className="text-xs mt-1">Usa el botÃ³n &ldquo;AÃ±adir Asistentes&rdquo; para marcar presentes</p>
                                    </div>
                                ) : (
                                    <div className="bg-white dark:bg-[#252528] rounded-md border border-slate-200 dark:border-white/5 overflow-hidden shadow-sm">
                                        <div className="px-4 py-2 border-b border-slate-100 dark:border-white/5 flex items-center justify-between">
                                            <h3 className="text-[11px] font-semibold uppercase tracking-wide text-slate-400 flex items-center gap-2">
                                                <CheckCircle2 size={14} className="text-emerald-500" /> Lista de Asistencia
                                            </h3>
                                            <span className="text-xs font-semibold text-blue-600 bg-blue-100 dark:bg-blue-900/30 px-3 py-1 rounded-lg">{attendance.total} personas</span>
                                        </div>
                                        <div className="divide-y divide-slate-50 dark:divide-white/5">
                                            {attendance.attendees.map((a) => (
                                                <div key={a.member_id} className="flex items-center gap-4 px-4 py-1.5 hover:bg-slate-50 dark:hover:bg-white/5 transition-colors">
                                                    <div className="size-8 rounded-md bg-gradient-to-br from-blue-400 to-sky-600 text-white flex items-center justify-center text-xs font-semibold shrink-0">
                                                        {a.name.charAt(0)}
                                                    </div>
                                                    <div className="flex-1 min-w-0">
                                                        <p className="text-sm font-bold text-slate-800 dark:text-white truncate">{a.name}</p>
                                                        {a.role && <p className="text-[10px] text-slate-400 font-medium">{a.role}</p>}
                                                    </div>
                                                    <CheckCircle2 size={16} className="text-emerald-500 shrink-0" />
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            </main>

            {/* ADD ATTENDEES INLINE SECTION */}
            {showAddAttendee && (
                <div className="mx-8 mb-3 bg-white dark:bg-[#1e1f21] border border-blue-200 dark:border-blue-500/30 rounded-lg p-4 shadow-sm animate-in slide-in-from-top-2 fade-in duration-200">
                    <div className="flex items-center justify-between mb-4 pb-4 border-b border-slate-100 dark:border-white/5">
                        <div>
                            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Registrar Asistentes</h3>
                            <p className="text-[10px] uppercase tracking-wide text-slate-400 font-bold mt-1">Busca o crea miembros para registrar su asistencia</p>
                        </div>
                        <div className="flex items-center gap-3">
                            <button
                                onClick={() => {
                                    setShowAddAttendee(false);
                                    setSelectedIds(new Set());
                                    setIsCreatingMember(false);
                                }}
                                className="px-4 py-2 text-[10px] font-semibold uppercase tracking-wide text-slate-500 hover:bg-slate-100 dark:hover:bg-white/5 rounded-md transition-colors"
                            >
                                Cancelar
                            </button>
                            {!isCreatingMember && (
                                <button
                                    onClick={handleSaveAttendance}
                                    disabled={saving || selectedIds.size === 0}
                                    className="px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-[10px] font-semibold uppercase tracking-wide transition-all flex items-center justify-center gap-2 disabled:opacity-50"
                                >
                                    {saving ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />}
                                    {saving ? 'Guardando...' : `Guardar ${selectedIds.size > 0 ? `(${selectedIds.size})` : ''}`}
                                </button>
                            )}
                        </div>
                    </div>
                    <div className="flex flex-col h-full">
                        {!isCreatingMember && (
                            <div className="pb-6 shrink-0">
                                <div className="flex gap-2 mb-2">
                                    <div className="relative flex-1">
                                        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={14} />
                                        <input
                                            autoFocus
                                            value={memberQuery}
                                            onChange={e => setMemberQuery(e.target.value)}
                                            placeholder="Buscar por nombre..."
                                            className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-lg py-1.5 pl-10 pr-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500"
                                        />
                                    </div>
                                    <button
                                        onClick={() => setIsCreatingMember(true)}
                                        className="px-4 py-1.5 bg-slate-100 hover:bg-slate-200 dark:bg-white/5 dark:hover:bg-white/10 rounded-lg text-[11px] font-semibold uppercase tracking-wide text-slate-700 dark:text-slate-300 transition-colors shrink-0 flex items-center gap-2"
                                    >
                                        <Plus size={14} /> Nuevo
                                    </button>
                                </div>
                                {selectedIds.size > 0 && (
                                    <p className="text-[10px] font-semibold uppercase tracking-wide text-blue-600 dark:text-blue-400 ml-1">
                                        {selectedIds.size} seleccionado{selectedIds.size > 1 ? 's' : ''}
                                    </p>
                                )}
                            </div>
                        )}

                        {isCreatingMember ? (
                            <div className="flex-1 overflow-y-auto pb-6 space-y-4 pt-2">
                                <div>
                                    <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-2 block">Nombres *</label>
                                    <input value={newMemberForm.first_name} onChange={e => setNewMemberForm(p => ({ ...p, first_name: e.target.value }))} className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-lg py-1.5 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500" placeholder="Ej. Juan" />
                                </div>
                                <div>
                                    <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-2 block">Apellidos *</label>
                                    <input value={newMemberForm.last_name} onChange={e => setNewMemberForm(p => ({ ...p, last_name: e.target.value }))} className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-lg py-1.5 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500" placeholder="Ej. PÃ©rez" />
                                </div>
                                <div>
                                    <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-2 block">TelÃ©fono</label>
                                    <input value={newMemberForm.phone} onChange={e => setNewMemberForm(p => ({ ...p, phone: e.target.value }))} className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-lg py-1.5 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500" placeholder="Opcional" />
                                </div>
                                <div>
                                    <label className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-2 block">Correo ElectrÃ³nico</label>
                                    <input type="email" value={newMemberForm.email} onChange={e => setNewMemberForm(p => ({ ...p, email: e.target.value }))} className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-lg py-1.5 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500" placeholder="Opcional" />
                                </div>
                                <div className="flex gap-3 pt-4">
                                    <button onClick={() => setIsCreatingMember(false)} className="flex-1 py-1.5 bg-slate-100 dark:bg-white/5 text-slate-700 dark:text-white rounded-lg text-sm font-bold hover:bg-slate-200 transition-all">Cancelar</button>
                                    <button onClick={handleCreateMember} disabled={creatingMember || !newMemberForm.first_name || !newMemberForm.last_name} className="flex-1 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-bold transition-all flex items-center justify-center gap-2 disabled:opacity-50">
                                        {creatingMember ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />} Crear
                                    </button>
                                </div>
                            </div>
                        ) : (
                            <div className="flex-1 overflow-y-auto pb-6 space-y-1 border-t border-slate-100 dark:border-white/5 pt-4">
                                {filteredMembers.length === 0 ? (
                                    <p className="text-center text-slate-400 text-sm py-1.5">No se encontraron miembros</p>
                                ) : filteredMembers.map(m => {
                                    const isSelected = selectedIds.has(m.id);
                                    return (
                                        <button
                                            key={m.id}
                                            onClick={() => setSelectedIds(prev => {
                                                const next = new Set(prev);
                                                isSelected ? next.delete(m.id) : next.add(m.id);
                                                return next;
                                            })}
                                            className={`w-full flex items-center gap-3 p-3 rounded-lg text-left transition-all ${isSelected ? 'bg-blue-50 dark:bg-blue-900/20 border border-blue-300 dark:border-blue-500/30' : 'hover:bg-slate-50 dark:hover:bg-white/5 border border-transparent'}`}
                                        >
                                            <div className={`size-9 rounded-md flex items-center justify-center text-sm font-semibold shrink-0 ${isSelected ? 'bg-blue-600 text-white' : 'bg-slate-100 dark:bg-white/10 text-slate-600 dark:text-slate-300'}`}>
                                                {isSelected ? <CheckCircle2 size={16} /> : m.first_name.charAt(0)}
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <p className="text-sm font-bold text-slate-800 dark:text-white truncate">{m.first_name} {m.last_name}</p>
                                                {m.church_role && <p className="text-[10px] text-slate-400">{m.church_role}</p>}
                                            </div>
                                        </button>
                                    );
                                })}
                            </div>
                        )}
                    </div>
                </div>
            )}
        </EvangelismShell>
    );
}

