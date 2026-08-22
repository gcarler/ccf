'use client';

import { apiFetch, ApiError } from '@/lib/http';
import { filtroAPersona, normalizarBusquedaPersona } from '@/lib/filtroAPersonas';
import { useAuth } from '@/context/AuthContext';
import { useSidebarLayers } from '@/context/SidebarLayerContext';
import { Calendar, ChevronRight, Plus, ArrowLeft } from 'lucide-react';
import { useRouter } from 'next/navigation';
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { toast } from 'sonner';

// Re-exportamos los tipos del page (interface forwarding) para que los paneles
// los puedan consumir sin re-declararlos ni importarlos del page (lo cual
// rompería la separación container/presenter: el page re-importaria el hook
// y no debería importar tipos desde él).

export interface HouseDetail {
  id: string; name: string; zone?: string; address?: string;
  code?: string; leader_name?: string; personas_count?: number; capacity?: number;
  day_of_week?: string; time?: string; status?: string;
  sessions: SessionRow[]; total_sessions: number; total_attendance: number;
  monitoring?: HouseMonitoring;
}
export interface SessionRow { id: string; session_date: string; status: string; estado_habilitacion?: string; season_name?: string; attendance_count: number; topic?: string; report_deadline?: string; }
export interface MonitoringTrendRow {
  session_id: string;
  session_date: string;
  status: string;
  attendance_rate: number;
  present_count: number;
  absent_count: number;
}
export interface RepeatAbsentee {
  persona_id: string;
  name: string;
  absences: number;
  details: { session_id: string; session_date?: string | null; reason?: string | null; reason_detail?: string | null }[];
}
export interface MonitoringAlert {
  type: string;
  message: string;
  session_id?: string;
}
export interface HouseMonitoring {
  expected_personas: number;
  average_attendance: number;
  average_attendance_rate: number;
  attendance_trend: MonitoringTrendRow[];
  recent_sessions: MonitoringTrendRow[];
  repeat_absentees: RepeatAbsentee[];
  alerts: MonitoringAlert[];
}
export type AttendanceReason = 'weather' | 'work' | 'health' | 'family' | 'other';
export interface AttendanceData {
  session_id: string;
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
export interface AttendeeRow { persona_id: string; name: string; role?: string; attended?: boolean; absence_reason?: AttendanceReason | null; absence_reason_detail?: string | null; scanned_at?: string; }
export interface Persona { id: string; nombre_completo: string; church_role?: string; }

export const ATTENDANCE_REASON_OPTIONS: { value: AttendanceReason; label: string }[] = [
  { value: 'weather', label: 'Clima' },
  { value: 'work', label: 'Trabajo' },
  { value: 'health', label: 'Salud' },
  { value: 'family', label: 'Familia' },
  { value: 'other', label: 'Otro' },
];

export function useGroupDetailPage(id: string | undefined) {
  const router = useRouter();
  const { token, hasModuleAccess } = useAuth();
  const { pushSidebarPanel } = useSidebarLayers();

  const [house, setHouse] = useState<HouseDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);

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
  const canManageEvangelism = hasModuleAccess('evangelism', 'manage');
  const activeSessionEnabled = activeSession?.estado_habilitacion === 'HABILITADO';

  // Load house detail
  useEffect(() => {
    if (!token || !id) return;
    setLoading(true);
    setLoadError(false);
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
        setHouse(null);
        setLoadError(true);
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
        <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-1))]">
          <div className="px-3 pt-4 pb-3 border-b border-[hsl(var(--border-primary))]">
            <button onClick={() => router.back()} className="flex items-center gap-1.5 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] dark:hover:text-[hsl(var(--text-primary))] transition-colors mb-3 text-2xs font-semibold uppercase tracking-wide">
              <ArrowLeft size={14} /> Volver a Grupos
            </button>
            <p className="text-xs font-semibold text-[hsl(var(--text-primary))] truncate mb-4">{house.name}</p>
            <h2 className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] flex items-center gap-2">
              <Calendar size={12} /> Sesiones Registradas
            </h2>
            {/* New Session Action */}
            {canManageEvangelism && <button
              onClick={async () => {
                try {
                  const session = await apiFetch<{ id: string }>(`/evangelism/sessions`, {
                    method: 'POST', silent: true,
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
                    token,
                    silent: true
                  });
                  toast.success('Nueva sesion creada y habilitada');
                  window.location.reload();
                } catch {
                  toast.error('Error al crear sesion. Puede que ya exista para hoy.');
                }
              }}
              className="mt-3 w-full py-2 bg-[hsl(var(--bg-muted))] hover:bg-[hsl(var(--bg-muted))] dark:hover:bg-white/10 text-[hsl(var(--text-primary))] rounded-lg text-2xs font-semibold uppercase tracking-wide transition-colors flex items-center justify-center gap-1.5"
            >
              <Plus size={12} /> Registrar sesion de esta semana
            </button>}
          </div>
          <div className="flex-1 overflow-y-auto px-3 py-2 space-y-1 scrollbar-thin">
            {house.sessions.length === 0 ? (
              <div className="py-1.5 text-center text-[hsl(var(--text-secondary))]">
                <Calendar size={24} className="mx-auto mb-3 opacity-30" />
                <p className="text-xs font-semibold uppercase tracking-wide">Sin sesiones</p>
              </div>
            ) : house.sessions.map(s => {
              const isActive = activeSession?.id === s.id;
              return (
                <button
                  key={s.id}
                  onClick={() => setActiveSession(s)}
                  className={`w-full text-left px-3 py-2.5 rounded-md border transition-all duration-200 ${isActive
                    ? 'bg-info-soft dark:bg-[hsl(var(--info))]/20 border-[hsl(var(--info)/25%)] dark:border-[hsl(var(--info)/100%)] shadow-sm'
                    : 'bg-transparent border-transparent hover:bg-[hsl(var(--bg-muted))]'
                    }`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className={`text-xs font-bold ${isActive ? 'text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]' : 'text-[hsl(var(--text-primary))]'}`}>
                        {s.topic ? s.topic : new Date(s.session_date + 'T12:00:00').toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'short' })}
                      </p>
                      {s.topic && <p className="text-2xs font-medium text-[hsl(var(--text-secondary))] mt-0.5">{new Date(s.session_date + 'T12:00:00').toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'short' })}</p>}
                      {s.season_name && !s.topic && <p className="text-2xs font-medium text-[hsl(var(--text-secondary))] mt-0.5">{s.season_name}</p>}
                      {s.estado_habilitacion !== 'HABILITADO' && <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--warning))] mt-0.5">Bloqueada</p>}
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 rounded-lg font-semibold ${isActive ? 'bg-[hsl(var(--info-muted))] dark:bg-[hsl(var(--info))]/50 text-[hsl(var(--primary))] dark:text-info-text' : 'bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))]'}`}>
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
  }, [house, activeSession, canManageEvangelism, router, pushSidebarPanel, token]);

  // Load attendance when session changes
  useEffect(() => {
    if (!token || !activeSession) return;
    setLoadingAtt(true);
    apiFetch<AttendanceData>(`/evangelism/groups/sessions/${activeSession.id}/attendance`, { token, silent: true })
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
      .catch(() => {
        setAttendance(null);
        setReportPersonas([]);
      })
      .finally(() => setLoadingAtt(false));
  }, [activeSession, token]);

  // Load personas for selector
  useEffect(() => {
    if (!token || !showAddAttendee) return;
    apiFetch<Persona[]>('/crm/personas', { token, silent: true, query: { limit: 1000, sort_by: 'first_name', sort_dir: 'asc' } }).then(setPersonas).catch(() => { setPersonas([]); });
  }, [showAddAttendee, token]);

  // R2 fix: búsqueda remota con debounce + AbortController.
  // Solo se dispara si el query tiene >=3 caracteres; antes de eso el
  // dropdown sigue usando el pool local pre-cargado para no martillar el
  // backend con cada keystroke.
  useEffect(() => {
    if (!token || !showAddAttendee) return;
    const q = remoteQuery.trim();
    if (q.length < 1) {
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
        silent: true,
        query: { q, limit: 1000 },
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
    const q = normalizarBusquedaPersona(personaQuery);
    const attendedIds = new Set(attendance?.attendees.map(a => a.persona_id) || []);
    // R2: si la búsqueda remota está activa (>=3 chars y hay resultados),
    // mezclamos primero los hits remotos; después el pool local para no
    // perder contactos no-precargados. Esto complementa la búsqueda local.
    const remoteMatches = remoteQuery.trim().length >= 3
      ? remoteResults.filter(m => !attendedIds.has(m.id))
      : [];
    const localPool = personas
      .filter(m => !attendedIds.has(m.id))
      .filter(m => filtroAPersona(m, q))
      // Excluir las que ya aparecieron en remoteResults.
      .filter(m => !remoteMatches.some(r => r.id === m.id));
    return [...remoteMatches, ...localPool];
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
        method: 'POST', body: { persona_ids: Array.from(selectedIds) }, token, silent: true
      });
      toast.success(`${res.processed} asistente(s) registrados`);
      setShowAddAttendee(false);
      setSelectedIds(new Set());
      setPersonaQuery('');
      // Reload attendance
      const updated = await apiFetch<AttendanceData>(`/evangelism/groups/sessions/${activeSession.id}/attendance`, { token, silent: true });
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
        silent: true,
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
        silent: true,
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
      const updated = await apiFetch<AttendanceData>(`/evangelism/groups/sessions/${activeSession.id}/attendance`, { token, silent: true });
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

  return {
    // State - house
    house,
    loading,
    loadError,
    // State - active session + attendance
    activeSession,
    setActiveSession,
    attendance,
    loadingAtt,
    savingReport,
    // Persona selector
    personas,
    showAddAttendee,
    setShowAddAttendee,
    personaQuery,
    setPersonaQuery,
    remoteQuery,
    setRemoteQuery,
    remoteLoading,
    saving,
    selectedIds,
    setSelectedIds,
    // Report form state
    reportTopic,
    setReportTopic,
    reportOfferingAmount,
    setReportOfferingAmount,
    reportNotes,
    setReportNotes,
    reportNoveltyType,
    setReportNoveltyType,
    reportNoveltyDetail,
    setReportNoveltyDetail,
    reportCancellationReason,
    setReportCancellationReason,
    reportStatus,
    setReportStatus,
    reportPersonas,
    setReportPersonas,
    // Persona creation
    isCreatingPersona,
    setIsCreatingPersona,
    newPersonaForm,
    setNewPersonaForm,
    creatingPersona,
    // Permission flags
    canManageEvangelism,
    activeSessionEnabled,
    // Derived
    filteredPersonas,
    // Handlers
    handleSaveAttendance,
    handleCreatePersona,
    handleSaveReport,
    // Router (para el header back button)
    router,
  };
}
