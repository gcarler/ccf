'use client';

import React, { useState, useEffect, useMemo, useRef } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { apiFetch, ApiError } from '@/lib/http';
import { useSidebarLayers } from '@/context/SidebarLayerContext';
import EvangelismShell from '@/components/evangelism/EvangelismShell';

import {
 Home, MapPin, Users, Calendar, CheckCircle2, Clock,
 ArrowLeft, Search, UserPlus, Loader2, ChevronRight, Plus,
 BarChart3, Activity
} from 'lucide-react';
import { toast } from 'sonner';

interface HouseDetail {
 id: string; name: string; zone?: string; address?: string;
 code?: string; leader_name?: string; personas_count?: number; capacity?: number;
 day_of_week?: string; time?: string; status?: string;
 sessions: SessionRow[]; total_sessions: number; total_attendance: number;
 monitoring?: HouseMonitoring;
}
interface SessionRow { id: number; session_date: string; status: string; estado_habilitacion?: string; season_name?: string; attendance_count: number; topic?: string; report_deadline?: string; }
interface MonitoringTrendRow {
 session_id: number;
 session_date: string;
 status: string;
 attendance_rate: number;
 present_count: number;
 absent_count: number;
}
interface RepeatAbsentee {
 persona_id: string;
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
 expected_personas: number;
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
 grupo_id: string;
 status: string;
 topic?: string | null;
 offering_amount?: number | null;
 report_notes?: string | null;
 novelty_type?: string | null;
 novelty_detail?: string | null;
 cancellation_reason?: string | null;
 reported_by_persona_id?: string | null;
 total: number;
 present_count?: number;
 absent_count?: number;
 attendees: AttendeeRow[];
 absentees: AttendeeRow[];
 expected_personas: AttendeeRow[];
}
interface AttendeeRow { persona_id: string; name: string; role?: string; attended?: boolean; absence_reason?: AttendanceReason | null; absence_reason_detail?: string | null; scanned_at?: string; }
interface Persona { id: string; nombre_completo: string; church_role?: string; }

export default function GroupDetailPage() {
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

 // Persona selector
 const [personas, setPersonas] = useState<Persona[]>([]);
 const [showAddAttendee, setShowAddAttendee] = useState(false);
 const [personaQuery, setPersonaQuery] = useState('');
 // R2 fix (residual audit): el formulario ahora soporta búsqueda REMOTA
 // con debounce 300ms + AbortController. Las variables de abajo son los
 // artefactos del efecto: query, resultados remotos, marcador de carga
 // y AbortController por ciclo.
 const [remoteResults, setRemoteResults] = useState<Persona[]>([]);
 const [remoteQuery, setRemoteQuery] = useState('');
 const [remoteLoading, setRemoteLoading] = useState(false);
 const remoteAbortRef = useRef<AbortController | null>(null);
 const [saving, setSaving] = useState(false);
 const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
 const [reportTopic, setReportTopic] = useState('');
 const [reportOfferingAmount, setReportOfferingAmount] = useState('');
 const [reportNotes, setReportNotes] = useState('');
 const [reportNoveltyType, setReportNoveltyType] = useState('');
 const [reportNoveltyDetail, setReportNoveltyDetail] = useState('');
 const [reportCancellationReason, setReportCancellationReason] = useState('');
 const [reportStatus, setReportStatus] = useState<'Realizada' | 'Cancelada' | 'No realizada'>('Realizada');
 const [reportPersonas, setReportPersonas] = useState<AttendeeRow[]>([]);

 // Se eliminó la dependencia de layers.RIGHT para showAddAttendee porque ahora usamos WorkspaceDrawer

 const [isCreatingPersona, setIsCreatingPersona] = useState(false);
 const [newPersonaForm, setNewPersonaForm] = useState({ first_name: '', last_name: '', phone: '', email: '' });
 const [creatingPersona, setCreatingPersona] = useState(false);
 const role = String(user?.role || '').toLowerCase();
 const isPrivileged = ['admin', 'administrador', 'pastor'].includes(role);
 const activeSessionEnabled = activeSession?.estado_habilitacion === 'HABILITADO';

 // Load house detail
 useEffect(() => {
 if (!token || !id) return;
 setLoading(true);
 apiFetch<HouseDetail>(`/evangelism/grupos/${id}`, { token, silent: true })
 .then(data => {
 setHouse(data);
 // Auto-select the most recent session
 if (data.sessions.length > 0) setActiveSession(data.sessions[0]);
 })
 .catch((error: unknown) => {
 if (error instanceof ApiError && error.status === 404) {
 setHouse(null);
 return;
 }
 toast.error('Error al cargar el grupo');
 })
 .finally(() => setLoading(false));
 }, [id, token]);

 // PUSH SESSIONS LIST TO SIDEBAR
 useEffect(() => {
 if (!house) return;
 pushSidebarPanel({
 id: 'groups-sessions-list',
 title: 'Grupos en Casa',
 replaceAll: true,
 content: (
 <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21]">
 <div className="px-3 pt-4 pb-3 border-b border-[hsl(var(--border-primary))]">
 <button onClick={() => router.back()} className="flex items-center gap-1.5 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] dark:hover:text-[hsl(var(--text-primary))] transition-colors mb-3 text-[10px] font-semibold uppercase tracking-wide">
 <ArrowLeft size={14} /> Volver a Grupos
 </button>
 <p className="text-xs font-semibold text-[hsl(var(--text-primary))] truncate mb-4">{house.name}</p>
 <h2 className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] flex items-center gap-2">
 <Calendar size={12} /> Sesiones Registradas
 </h2>
 {/* New Session Action */}
 {isPrivileged && <button 
 onClick={async () => {
 try {
	 const session = await apiFetch<{ id: number }>(`/evangelism/sessions`, {
	 method: 'POST',
	 body: {
	 grupo_id: house.id,
	 session_date: `${new Date().toISOString().split('T')[0]}T12:00:00`,
	 status: 'Realizada',
	 },
	 token
 });
 await apiFetch(`/evangelism/sessions/${session.id}/habilitacion`, {
 method: 'PATCH',
 body: { accion: 'HABILITAR' },
 token
 });
 toast.success('Nueva sesion creada y habilitada');
 window.location.reload();
 } catch {
 toast.error('Error al crear sesion. Puede que ya exista para hoy.');
 }
 }}
 className="mt-3 w-full py-2 bg-[hsl(var(--bg-muted))] hover:bg-[hsl(var(--bg-muted))] dark:hover:bg-white/10 text-[hsl(var(--text-primary))] rounded-lg text-[10px] font-semibold uppercase tracking-wide transition-colors flex items-center justify-center gap-1.5"
 >
 <Plus size={12} /> Registrar sesion de esta semana
 </button>}
 </div>
 <div className="flex-1 overflow-y-auto px-3 py-2 space-y-1 scrollbar-thin">
 {house.sessions.length === 0 ? (
 <div className="py-1.5 text-center text-[hsl(var(--text-secondary))]">
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
 : 'bg-transparent border-transparent hover:bg-[hsl(var(--bg-muted))]'
 }`}
 >
 <div className="flex items-center justify-between">
 <div>
 <p className={`text-xs font-bold ${isActive ? 'text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]' : 'text-[hsl(var(--text-primary))]'}`}>
 {s.topic ? s.topic : new Date(s.session_date + 'T12:00:00').toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'short' })}
 </p>
 {s.topic && <p className="text-[10px] font-medium text-[hsl(var(--text-secondary))] mt-0.5">{new Date(s.session_date + 'T12:00:00').toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'short' })}</p>}
 {s.season_name && !s.topic && <p className="text-[10px] font-medium text-[hsl(var(--text-secondary))] mt-0.5">{s.season_name}</p>}
 {s.estado_habilitacion !== 'HABILITADO' && <p className="text-[9px] font-semibold uppercase tracking-wide text-amber-500 mt-0.5">Bloqueada</p>}
 </div>
 <div className="flex items-center gap-2">
 <span className={`px-2 py-0.5 rounded-lg font-semibold ${isActive ? 'bg-blue-100 dark:bg-blue-900/50 text-[hsl(var(--primary))] dark:text-blue-300' : 'bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))]'}`}>
 {s.attendance_count}
 </span>
 <ChevronRight size={14} className={isActive ? 'text-[hsl(var(--primary))]' : 'text-[hsl(var(--text-secondary))]'} />
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
 apiFetch<AttendanceData>(`/evangelism/groups/sessions/${activeSession.id}/attendance`, { token })
 .then(data => {
 setAttendance(data);
 
 // Merge expected personas and attendees perfectly
 const mergedMap = new Map<string, AttendeeRow>();

 // First add all expected personas
 (data.expected_personas || []).forEach(row => {
 mergedMap.set(row.persona_id, {
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
 if (mergedMap.has(row.persona_id)) {
 mergedMap.get(row.persona_id)!.attended = true;
 mergedMap.get(row.persona_id)!.scanned_at = row.scanned_at;
 } else {
 mergedMap.set(row.persona_id, {
 ...row,
 attended: true,
 });
 }
 });
 
 setReportPersonas(Array.from(mergedMap.values()));
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
 .catch(() => { toast.error('Error al cargar datos de asistencia'); })
 .finally(() => setLoadingAtt(false));
 }, [activeSession, token]);

 // Load personas for selector
 useEffect(() => {
 if (!token || !showAddAttendee) return;
 apiFetch<Persona[]>('/crm/personas', { token, query: { limit: 1000, sort_by: 'first_name', sort_dir: 'asc' } }).then(setPersonas).catch(() => { toast.error('Error al cargar personas'); });
 }, [showAddAttendee, token]);

 // R2 fix: búsqueda remota con debounce + AbortController.
 // Solo se dispara si el query tiene >=3 caracteres; antes de eso el
 // dropdown sigue usando el pool local pre-cargado para no martillar el
 // backend con cada keystroke.
 useEffect(() => {
 if (!token || !showAddAttendee) return;
 const q = remoteQuery.trim();
 if (q.length < 3) {
 setRemoteResults([]);
 if (remoteAbortRef.current) {
 remoteAbortRef.current.abort();
 remoteAbortRef.current = null;
 }
 return;
 }
 if (remoteAbortRef.current) {
 remoteAbortRef.current.abort();
 }
 const controller = new AbortController();
 remoteAbortRef.current = controller;
 setRemoteLoading(true);
 const handle = setTimeout(() => {
 apiFetch<{ results: Persona[] }>('/evangelism/personas/search', {
 token,
 query: { q, limit: 10 },
 signal: controller.signal,
 })
 .then(res => {
 if (controller.signal.aborted) return;
 setRemoteResults(res.results || []);
 })
 .catch(_err => {
if (controller.signal.aborted) return;
setRemoteResults([]);
})
 .finally(() => {
 if (!controller.signal.aborted) setRemoteLoading(false);
 });
 }, 300);
 return () => {
 clearTimeout(handle);
 controller.abort();
 };
 }, [remoteQuery, showAddAttendee, token]);

 const filteredPersonas = useMemo(() => {
 const q = personaQuery.toLowerCase();
 const attendedIds = new Set(attendance?.attendees.map(a => a.persona_id) || []);
 // R2: si la búsqueda remota está activa (>=3 chars y hay resultados),
 // mezclamos primero los hits remotos; después el pool local para no
 // perder contactos no-precargados. Esto complementa la búsqueda local.
 const remoteMatches = remoteQuery.trim().length >= 3
 ? remoteResults.filter(m => !attendedIds.has(m.id))
 : [];
 const localPool = personas
 .filter(m => !attendedIds.has(m.id))
 .filter(m => !q || (m.nombre_completo || '').toLowerCase().includes(q))
 // Excluir las que ya aparecieron en remoteResults.
 .filter(m => !remoteMatches.some(r => r.id === m.id));
 return [...remoteMatches, ...localPool].slice(0, 30);
 }, [personas, personaQuery, attendance, remoteQuery, remoteResults]);

 const handleSaveAttendance = async () => {
 if (!activeSession || selectedIds.size === 0) return;
 if (!activeSessionEnabled) {
 toast.error('La sesion esta bloqueada. Debe habilitarse antes de reportar asistencia.');
 return;
 }
 setSaving(true);
 try {
 const res = await apiFetch<{ processed: number }>(`/evangelism/groups/sessions/${activeSession.id}/attendance`, {
 method: 'POST', body: { persona_ids: Array.from(selectedIds) }, token
 });
 toast.success(`${res.processed} asistente(s) registrados`);
 setShowAddAttendee(false);
 setSelectedIds(new Set());
 setPersonaQuery('');
 // Reload attendance
 const updated = await apiFetch<AttendanceData>(`/evangelism/groups/sessions/${activeSession.id}/attendance`, { token });
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

 const handleCreatePersona = async () => {
 if (!newPersonaForm.first_name || !newPersonaForm.last_name) {
 return toast.error('El nombre y apellido son obligatorios');
 }
 setCreatingPersona(true);
 try {
 const res = await apiFetch<Persona>('/crm/personas', {
 method: 'POST',
 token,
 body: { ...newPersonaForm, church_role: 'Visitante' }
 });
 toast.success('Invitado creado con éxito');
 setPersonas(prev => [res, ...prev]);
 setSelectedIds(prev => new Set(prev).add(res.id));
 setNewPersonaForm({ first_name: '', last_name: '', phone: '', email: '' });
 setIsCreatingPersona(false);
 } catch {
 toast.error('Error al crear el invitado');
 } finally {
 setCreatingPersona(false);
 }
 };

 const handleSaveReport = async () => {
 if (!activeSession) return;
 if (!activeSessionEnabled) {
 toast.error('La sesion esta bloqueada. Debe habilitarse antes de guardar el reporte.');
 return;
 }
 setSavingReport(true);
 try {
 const attendees = reportPersonas.map((row) => ({
 persona_id: row.persona_id,
 attended: row.attended ?? true,
 absence_reason: row.attended ? null : row.absence_reason,
 absence_reason_detail: row.attended ? null : row.absence_reason_detail,
 }));
 await apiFetch<{ status: string }>(`/evangelism/groups/sessions/${activeSession.id}/attendance`, {
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
 const updated = await apiFetch<AttendanceData>(`/evangelism/groups/sessions/${activeSession.id}/attendance`, { token });
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
 <EvangelismShell breadcrumbs={[{ label: 'Grupos en Casa', href: '/plataforma/evangelism/groups', icon: Home }, { label: '...', icon: Home }]}>
 <div className="flex items-center justify-center h-full"><Loader2 className="animate-spin text-[hsl(var(--primary))]" size={40} /></div>
 </EvangelismShell>
 );

 if (!house) return (
 <EvangelismShell breadcrumbs={[{ label: 'Grupos en Casa', href: '/plataforma/evangelism/groups', icon: Home }]}>
 <div className="p-4 text-center text-[hsl(var(--text-secondary))]">
   <p className="mb-4">Grupo no encontrado.</p>
   <Link href="/plataforma/evangelism/groups" className="text-[hsl(var(--primary))] underline">Volver a grupos</Link>
 </div>
 </EvangelismShell>
 );

 const avgAttendance = house.total_sessions > 0 ? Math.round(house.total_attendance / house.total_sessions) : 0;
 const monitoring = house.monitoring;
 const trendRows = monitoring?.attendance_trend ?? [];
 const alerts = monitoring?.alerts ?? [];
 const repeatAbsentees = monitoring?.repeat_absentees ?? [];

 return (
 <EvangelismShell breadcrumbs={[
 { label: 'Grupos en Casa', href: '/plataforma/evangelism/groups', icon: Home },
 { label: house.name, icon: Home }
 ]}>
 <main className="flex-1 overflow-y-auto">
 {/* Page Header */}
 <div className="px-3 pt-8 pb-6 border-b border-[hsl(var(--border-primary))]">
 <button onClick={() => router.back()} className="flex items-center gap-1.5 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] dark:hover:text-[hsl(var(--text-primary))] transition-colors mb-4 text-xs font-bold uppercase tracking-wide">
 <ArrowLeft size={14} /> Volver
 </button>
 <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
 <div>
 <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1">Grupos en Casa</p>
 <h1 className="text-lg font-bold text-[hsl(var(--text-primary))] tracking-tight">{house.name}</h1>
 <div className="flex flex-wrap gap-4 text-xs text-[hsl(var(--text-secondary))] font-medium mt-1.5">
 {house.code && <span className="flex items-center gap-1.5"><Activity size={12} /> Código: {house.code}</span>}
 {house.leader_name && <span className="flex items-center gap-1.5"><Users size={12} /> Líder: {house.leader_name}</span>}
 {house.address && <span className="flex items-center gap-1.5"><MapPin size={12} /> {house.address}</span>}
 {house.day_of_week && <span className="flex items-center gap-1.5"><Clock size={12} /> {house.day_of_week} {house.time || ''}</span>}
 </div>
 </div>
 <div className="flex gap-3 shrink-0">
 <div className="text-center px-3 py-1.5 bg-[hsl(var(--bg-primary))] dark:bg-[#252528] rounded-md border border-[hsl(var(--border-primary))] shadow-sm">
 <p className="text-base font-bold text-[hsl(var(--text-primary))]">{house.total_sessions}</p>
 <p className="text-[10px] text-[hsl(var(--text-secondary))] font-semibold uppercase tracking-wide mt-0.5">Sesiones</p>
 </div>
 <div className="text-center px-3 py-1.5 bg-[hsl(var(--bg-primary))] dark:bg-[#252528] rounded-md border border-[hsl(var(--border-primary))] shadow-sm">
 <p className="text-base font-bold text-[hsl(var(--text-primary))]">{house.total_attendance}</p>
 <p className="text-[10px] text-[hsl(var(--text-secondary))] font-semibold uppercase tracking-wide mt-0.5">Asistentes</p>
 </div>
 <div className="text-center px-3 py-1.5 bg-[hsl(var(--bg-primary))] dark:bg-[#252528] rounded-md border border-[hsl(var(--border-primary))] shadow-sm">
 <p className="text-base font-bold text-[hsl(var(--text-primary))]">{avgAttendance}</p>
 <p className="text-[10px] text-[hsl(var(--text-secondary))] font-semibold uppercase tracking-wide mt-0.5">Promedio</p>
 </div>
 </div>
 </div>
 </div>

 <div className="p-4">
 {/* ATTENDANCE PANEL */}
 <div className="w-full">
 {!activeSession ? (
 <div className="h-full flex items-center justify-center py-1.5 text-[hsl(var(--text-secondary))]">
 <div className="text-center">
 <Activity size={40} className="mx-auto mb-4 opacity-30" />
 <p className="font-bold">Selecciona una sesión para ver la asistencia</p>
 </div>
 </div>
 ) : (
 <div className="space-y-2">
 <div className="flex items-center justify-between">
 <div>
 <h2 className="text-sm font-semibold text-[hsl(var(--text-primary))]">
 {activeSession.topic ? activeSession.topic : new Date(activeSession.session_date + 'T12:00:00').toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
 </h2>
 {activeSession.topic && <p className="text-xs text-[hsl(var(--text-secondary))] font-bold mt-0.5">{new Date(activeSession.session_date + 'T12:00:00').toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}</p>}
 {activeSession.season_name && !activeSession.topic && <p className="text-xs text-[hsl(var(--text-secondary))] font-bold mt-0.5">{activeSession.season_name}</p>}
 </div>
 <button
 onClick={() => setShowAddAttendee(true)}
 disabled={!activeSessionEnabled}
 className="flex items-center gap-2 px-3 py-2.5 bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))] text-white rounded-lg text-[11px] font-semibold uppercase tracking-wide transition-all shadow-lg shadow-blue-500/20"
 >
 <UserPlus size={14} /> Añadir Asistentes
 </button>
 </div>

 {/* Stat strip */}
 <div className="flex gap-4">
 <div className="flex-1 bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border-primary))] rounded-lg p-4 text-center">
 <p className="text-lg font-bold text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]">{loadingAtt ? 'â€”' : attendance?.total ?? 0}</p>
 <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mt-1">Presentes</p>
 </div>
 <div className="flex-1 bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border-primary))] rounded-lg p-4 text-center">
 <p className="text-lg font-bold text-[hsl(var(--text-primary))]">{house.capacity ?? 'â€”'}</p>
 <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mt-1">Capacidad</p>
 </div>
 <div className="flex-1 bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border-primary))] rounded-lg p-4 text-center">
 <p className="text-lg font-bold text-emerald-600 dark:emerald-400">
 {house.capacity && attendance ? `${Math.round(attendance.total / house.capacity * 100)}%` : 'â€”'}
 </p>
 <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mt-1">Ocupación</p>
 </div>
 </div>

 <div className="bg-[hsl(var(--bg-primary))] rounded-md border border-[hsl(var(--border-primary))] p-4 shadow-sm space-y-2">
 <div className="flex items-center justify-between gap-4">
 <h3 className="text-sm font-semibold uppercase tracking-wide text-[hsl(var(--text-primary))] flex items-center gap-2">
 <BarChart3 className="text-[hsl(var(--primary))]" size={18} /> Monitoreo de la casa
 </h3>
 <span className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
 {monitoring?.expected_personas ?? 0} esperados
 </span>
 </div>

 <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
 <div className="rounded-lg border border-[hsl(var(--border-primary))] p-4 bg-[hsl(var(--bg-muted))] dark:bg-black/20">
 <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Promedio de presencia</p>
 <p className="mt-2 text-lg font-bold text-[hsl(var(--text-primary))]">{monitoring?.average_attendance ?? avgAttendance}</p>
 </div>
 <div className="rounded-lg border border-[hsl(var(--border-primary))] p-4 bg-[hsl(var(--bg-muted))] dark:bg-black/20">
 <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Tasa promedio</p>
 <p className="mt-2 text-lg font-bold text-[hsl(var(--text-primary))]">{monitoring?.average_attendance_rate ?? 0}%</p>
 </div>
 <div className="rounded-lg border border-[hsl(var(--border-primary))] p-4 bg-[hsl(var(--bg-muted))] dark:bg-black/20">
 <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Alertas activas</p>
 <p className="mt-2 text-lg font-bold text-[hsl(var(--text-primary))]">{alerts.length}</p>
 </div>
 </div>

 <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
 <div className="rounded-lg border border-[hsl(var(--border-primary))] p-4">
 <div className="flex items-center justify-between mb-4">
 <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Tendencia reciente</p>
 <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{trendRows.length} sesiones</p>
 </div>
 <div className="space-y-3">
 {trendRows.length === 0 ? (
 <p className="text-sm text-[hsl(var(--text-secondary))]">No hay datos de tendencia todavía.</p>
 ) : trendRows.map((row) => (
 <div key={row.session_id} className="flex items-center justify-between gap-4 rounded-lg bg-[hsl(var(--bg-muted))] dark:bg-black/20 px-4 py-1.5">
 <div className="min-w-0">
 <p className="text-sm font-bold text-[hsl(var(--text-primary))] truncate">
 {new Date(row.session_date + 'T12:00:00').toLocaleDateString('es-CO', { month: 'short', day: 'numeric' })}
 </p>
 <p className="text-[10px] font-medium text-[hsl(var(--text-secondary))]">{row.status}</p>
 </div>
 <div className="text-right shrink-0">
 <p className="text-sm font-semibold text-[hsl(var(--text-primary))]">{row.attendance_rate}%</p>
 <p className="text-[10px] font-medium text-[hsl(var(--text-secondary))]">{row.present_count}/{row.present_count + row.absent_count}</p>
 </div>
 </div>
 ))}
 </div>
 </div>

 <div className="rounded-lg border border-[hsl(var(--border-primary))] p-4">
 <div className="flex items-center justify-between mb-4">
 <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Alertas</p>
 <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{repeatAbsentees.length} reincidentes</p>
 </div>
 <div className="space-y-3">
 {alerts.length === 0 && repeatAbsentees.length === 0 ? (
 <p className="text-sm text-[hsl(var(--text-secondary))]">Sin alertas activas.</p>
 ) : (
 <>
 {alerts.map((alert, index) => (
 <div key={`${alert.type}-${index}`} className="rounded-lg border border-amber-200 dark:border-amber-500/30 bg-amber-50 dark:bg-amber-500/10 px-4 py-1.5">
 <p className="text-sm font-bold text-amber-800 dark:text-amber-200">{alert.message}</p>
 </div>
 ))}
 {repeatAbsentees.slice(0, 4).map((item) => (
 <div key={item.persona_id} className="rounded-lg border border-rose-200 dark:border-rose-500/30 bg-rose-50 dark:bg-rose-500/10 px-4 py-1.5">
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
 <h3 className="text-sm font-semibold uppercase tracking-wide text-[hsl(var(--text-primary))] flex items-center gap-2">
 <Activity className="text-[hsl(var(--primary))]" size={18} /> Reporte semanal
 </h3>
 <span className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
 {reportPersonas.length} personas
 </span>
 </div>

 <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
 <div>
 <label className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-2 block">Tema tratado</label>
 <input
 value={reportTopic}
 onChange={(e) => setReportTopic(e.target.value)}
 className="w-full bg-[hsl(var(--bg-muted))] dark:bg-black/20 border border-[hsl(var(--border-primary))] rounded-lg py-1.5 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500"
 placeholder="Unidad familiar, fe, oración..."
 />
 </div>
 <div>
 <label className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-2 block">Ofrenda recibida</label>
 <input
 type="number"
 value={reportOfferingAmount}
 onChange={(e) => setReportOfferingAmount(e.target.value)}
 className="w-full bg-[hsl(var(--bg-muted))] dark:bg-black/20 border border-[hsl(var(--border-primary))] rounded-lg py-1.5 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500"
 placeholder="0"
 min="0"
 step="0.01"
 />
 </div>
 <div>
 <label className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-2 block">Estado</label>
 <select
 value={reportStatus}
 onChange={(e) => {
 const nextStatus =
 e.target.value === 'Cancelada' || e.target.value === 'No realizada' || e.target.value === 'Realizada'
 ? e.target.value
 : 'Realizada';
 setReportStatus(nextStatus);
 }}
 className="w-full bg-[hsl(var(--bg-muted))] dark:bg-black/20 border border-[hsl(var(--border-primary))] rounded-lg py-1.5 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500"
 >
 <option value="Realizada">Realizada</option>
 <option value="No realizada">No realizada</option>
 <option value="Cancelada">Cancelada</option>
 </select>
 </div>
 <div>
 <label className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-2 block">Novedad</label>
 <select
 value={reportNoveltyType}
 onChange={(e) => setReportNoveltyType(e.target.value)}
 className="w-full bg-[hsl(var(--bg-muted))] dark:bg-black/20 border border-[hsl(var(--border-primary))] rounded-lg py-1.5 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500"
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
 <label className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-2 block">Detalle de novedad</label>
 <textarea
 value={reportNoveltyDetail}
 onChange={(e) => setReportNoveltyDetail(e.target.value)}
 className="w-full min-h-24 bg-[hsl(var(--bg-muted))] dark:bg-black/20 border border-[hsl(var(--border-primary))] rounded-lg p-4 text-sm font-medium outline-none focus:ring-2 focus:ring-blue-500"
 placeholder="Explica la novedad o la razón del ajuste..."
 />
 </div>
 <div>
 <label className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-2 block">Motivo de cancelación</label>
 <textarea
 value={reportCancellationReason}
 onChange={(e) => setReportCancellationReason(e.target.value)}
 className="w-full min-h-24 bg-[hsl(var(--bg-muted))] dark:bg-black/20 border border-[hsl(var(--border-primary))] rounded-lg p-4 text-sm font-medium outline-none focus:ring-2 focus:ring-blue-500"
 placeholder="Si no se realizó, explica la causa..."
 />
 </div>
 </div>

 <div>
 <label className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-2 block">Notas del reporte</label>
 <textarea
 value={reportNotes}
 onChange={(e) => setReportNotes(e.target.value)}
 className="w-full min-h-28 bg-[hsl(var(--bg-muted))] dark:bg-black/20 border border-[hsl(var(--border-primary))] rounded-lg p-4 text-sm font-medium outline-none focus:ring-2 focus:ring-blue-500"
 placeholder="Resumen pastoral, acuerdos, seguimiento..."
 />
 </div>

 <div className="space-y-3">
 <div className="flex items-center justify-between">
 <h4 className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Asistencia por persona</h4>
 <span className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Presente / Ausente</span>
 </div>
 <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
 {reportPersonas.map((row) => {
 const attended = row.attended !== false;
 return (
 <div key={row.persona_id} className="rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-muted))] dark:bg-black/20 p-4 space-y-3">
 <div className="flex items-center justify-between gap-3">
 <div className="min-w-0">
 <p className="text-sm font-bold text-[hsl(var(--text-primary))] truncate">{row.name}</p>
 <p className="text-[10px] uppercase font-bold tracking-wide text-[hsl(var(--text-secondary))]">{row.role || 'Persona'}</p>
 </div>
 <label className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
 <input
 type="checkbox"
 checked={attended}
 onChange={(e) => {
 const checked = e.target.checked;
 setReportPersonas(prev => prev.map(item => item.persona_id === row.persona_id ? {
 ...item,
 attended: checked,
 absence_reason: checked ? null : item.absence_reason || 'other',
 absence_reason_detail: checked ? null : item.absence_reason_detail || '',
 } : item));
 }}
 className="size-4 rounded border-[hsl(var(--border-primary))] text-[hsl(var(--primary))] focus:ring-blue-500"
 />
 {attended ? 'Presente' : 'Ausente'}
 </label>
 </div>

 {!attended && (
 <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
 <div>
 <label className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-2 block">Razón</label>
 <select
 value={row.absence_reason || 'other'}
 onChange={(e) => setReportPersonas(prev => prev.map(item => item.persona_id === row.persona_id ? { ...item, absence_reason: e.target.value as AttendanceReason } : item))}
 className="w-full bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] border border-[hsl(var(--border-primary))] rounded-lg py-2.5 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500"
 >
 {reasonOptions.map(opt => <option key={opt.value} value={opt.value}>{opt.label}</option>)}
 </select>
 </div>
 <div>
 <label className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-2 block">Detalle</label>
 <input
 value={row.absence_reason_detail || ''}
 onChange={(e) => setReportPersonas(prev => prev.map(item => item.persona_id === row.persona_id ? { ...item, absence_reason_detail: e.target.value } : item))}
 className="w-full bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] border border-[hsl(var(--border-primary))] rounded-lg py-2.5 px-4 text-sm font-medium outline-none focus:ring-2 focus:ring-blue-500"
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
 disabled={savingReport || !activeSession || !activeSessionEnabled}
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
 <div className="flex items-center justify-center py-1.5"><Loader2 className="animate-spin text-[hsl(var(--primary))]" size={24} /></div>
 ) : !attendance || attendance.attendees.length === 0 ? (
 <div className="py-1.5 text-center bg-[hsl(var(--bg-muted))] rounded-lg text-[hsl(var(--text-secondary))]">
 <Users size={32} className="mx-auto mb-3 opacity-30" />
 <p className="font-bold text-sm">Sin asistentes registrados</p>
 <p className="text-xs mt-1">Usa el botón &ldquo;Añadir Asistentes&rdquo; para marcar presentes</p>
 </div>
 ) : (
 <div className="bg-[hsl(var(--bg-primary))] dark:bg-[#252528] rounded-md border border-[hsl(var(--border-primary))] overflow-hidden shadow-sm">
 <div className="px-4 py-2 border-b border-[hsl(var(--border-primary))] flex items-center justify-between">
 <h3 className="text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] flex items-center gap-2">
 <CheckCircle2 size={14} className="text-emerald-500" /> Lista de Asistencia
 </h3>
 <span className="text-xs font-semibold text-[hsl(var(--primary))] bg-blue-100 dark:bg-blue-900/30 px-3 py-1 rounded-lg">{attendance.total} personas</span>
 </div>
 <div className="divide-y divide-[hsl(var(--border-primary))]">
 {attendance.attendees.map((a) => (
 <div key={a.persona_id} className="flex items-center gap-4 px-4 py-1.5 hover:bg-[hsl(var(--bg-muted))] dark:hover:bg-white/5 transition-colors">
 <div className="size-8 rounded-md bg-gradient-to-br from-blue-400 to-sky-600 text-white flex items-center justify-center text-xs font-semibold shrink-0">
 {a.name.charAt(0)}
 </div>
 <div className="flex-1 min-w-0">
 <p className="text-sm font-bold text-[hsl(var(--text-primary))] truncate">{a.name}</p>
 {a.role && <p className="text-[10px] text-[hsl(var(--text-secondary))] font-medium">{a.role}</p>}
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
 <div className="mx-8 mb-3 bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] border border-blue-200 dark:border-blue-500/30 rounded-lg p-4 shadow-sm animate-in slide-in-from-top-2 fade-in duration-200">
 <div className="flex items-center justify-between mb-4 pb-4 border-b border-[hsl(var(--border-primary))]">
 <div>
 <h3 className="text-sm font-semibold text-[hsl(var(--text-primary))]">Registrar Asistentes</h3>
 <p className="text-[10px] uppercase tracking-wide text-[hsl(var(--text-secondary))] font-bold mt-1">Busca o crea personas para registrar su asistencia</p>
 </div>
 <div className="flex items-center gap-3">
 <button
 onClick={() => {
 setShowAddAttendee(false);
 setSelectedIds(new Set());
 setIsCreatingPersona(false);
 }}
 className="px-4 py-2 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--bg-muted))] rounded-md transition-colors"
 >
 Cancelar
 </button>
 {!isCreatingPersona && (
 <button
 onClick={handleSaveAttendance}
 disabled={saving || selectedIds.size === 0 || !activeSessionEnabled}
 className="px-3 py-2 bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))] text-white rounded-md text-[10px] font-semibold uppercase tracking-wide transition-all flex items-center justify-center gap-2 disabled:opacity-50"
 >
 {saving ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />}
 {saving ? 'Guardando...' : `Guardar ${selectedIds.size > 0 ? `(${selectedIds.size})` : ''}`}
 </button>
 )}
 </div>
 </div>
 <div className="flex flex-col h-full">
 {!isCreatingPersona && (
 <div className="pb-6 shrink-0">
 <div className="flex gap-2 mb-2">
 <div className="relative flex-1">
 <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" size={14} />
 <input
 autoFocus
 value={personaQuery}
 onChange={e => {
 setPersonaQuery(e.target.value);
 setRemoteQuery(e.target.value);
 }}
 placeholder="Buscar por nombre (>=3 letras)..."
 className="w-full bg-[hsl(var(--bg-muted))] dark:bg-black/20 border border-[hsl(var(--border-primary))] rounded-lg py-1.5 pl-10 pr-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500"
 />
 {remoteLoading && (
 <Loader2 className="absolute right-4 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))] animate-spin" size={14} />
 )}
 </div>
 <button
 onClick={() => setIsCreatingPersona(true)}
 className="px-4 py-1.5 bg-[hsl(var(--bg-muted))] hover:bg-[hsl(var(--bg-muted))] dark:hover:bg-white/10 rounded-lg text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-primary))] transition-colors shrink-0 flex items-center gap-2"
 >
 <Plus size={14} /> Nuevo
 </button>
 </div>
 {selectedIds.size > 0 && (
 <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] ml-1">
 {selectedIds.size} seleccionado{selectedIds.size > 1 ? 's' : ''}
 </p>
 )}
 </div>
 )}

 {isCreatingPersona ? (
 <div className="flex-1 overflow-y-auto pb-6 space-y-4 pt-2">
 <div>
 <label className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-2 block">Nombres *</label>
 <input value={newPersonaForm.first_name} onChange={e => setNewPersonaForm(p => ({ ...p, first_name: e.target.value }))} className="w-full bg-[hsl(var(--bg-muted))] dark:bg-black/20 border border-[hsl(var(--border-primary))] rounded-lg py-1.5 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500" placeholder="Ej. Juan" />
 </div>
 <div>
 <label className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-2 block">Apellidos *</label>
 <input value={newPersonaForm.last_name} onChange={e => setNewPersonaForm(p => ({ ...p, last_name: e.target.value }))} className="w-full bg-[hsl(var(--bg-muted))] dark:bg-black/20 border border-[hsl(var(--border-primary))] rounded-lg py-1.5 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500" placeholder="Ej. Pérez" />
 </div>
 <div>
 <label className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-2 block">Teléfono</label>
 <input value={newPersonaForm.phone} onChange={e => setNewPersonaForm(p => ({ ...p, phone: e.target.value }))} className="w-full bg-[hsl(var(--bg-muted))] dark:bg-black/20 border border-[hsl(var(--border-primary))] rounded-lg py-1.5 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500" placeholder="Opcional" />
 </div>
 <div>
 <label className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-2 block">Correo Electrónico</label>
 <input type="email" value={newPersonaForm.email} onChange={e => setNewPersonaForm(p => ({ ...p, email: e.target.value }))} className="w-full bg-[hsl(var(--bg-muted))] dark:bg-black/20 border border-[hsl(var(--border-primary))] rounded-lg py-1.5 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500" placeholder="Opcional" />
 </div>
 <div className="flex gap-3 pt-4">
 <button onClick={() => setIsCreatingPersona(false)} className="flex-1 py-1.5 bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-primary))] rounded-lg text-sm font-bold hover:bg-[hsl(var(--bg-muted))] transition-all">Cancelar</button>
 <button onClick={handleCreatePersona} disabled={creatingPersona || !newPersonaForm.first_name || !newPersonaForm.last_name} className="flex-1 py-1.5 bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))] text-white rounded-lg text-sm font-bold transition-all flex items-center justify-center gap-2 disabled:opacity-50">
 {creatingPersona ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />} Crear
 </button>
 </div>
 </div>
 ) : (
 <div className="flex-1 overflow-y-auto pb-6 space-y-1 border-t border-[hsl(var(--border-primary))] pt-4">
 {filteredPersonas.length === 0 ? (
 <p className="text-center text-[hsl(var(--text-secondary))] text-sm py-1.5">No se encontraron personas</p>
 ) : filteredPersonas.map(m => {
 const isSelected = selectedIds.has(m.id);
 return (
 <button
 key={m.id}
 onClick={() => setSelectedIds(prev => {
 const next = new Set(prev);
 isSelected ? next.delete(m.id) : next.add(m.id);
 return next;
 })}
 className={`w-full flex items-center gap-3 p-3 rounded-lg text-left transition-all ${isSelected ? 'bg-blue-50 dark:bg-blue-900/20 border border-blue-300 dark:border-blue-500/30' : 'hover:bg-[hsl(var(--bg-muted))] dark:hover:bg-white/5 border border-transparent'}`}
 >
 <div className={`size-9 rounded-md flex items-center justify-center text-sm font-semibold shrink-0 ${isSelected ? 'bg-[hsl(var(--primary))] text-white' : 'bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))]'}`}>
 {isSelected ? <CheckCircle2 size={16} /> : (m.nombre_completo?.charAt(0) || '')}
 </div>
 <div className="flex-1 min-w-0">
 <p className="text-sm font-bold text-[hsl(var(--text-primary))] truncate">{m.nombre_completo}</p>
 {m.church_role && <p className="text-[10px] text-[hsl(var(--text-secondary))]">{m.church_role}</p>}
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
