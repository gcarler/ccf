/**
 * Hooks de datos para la página de detalle de estrategia.
 *
 * Extraídos de page.tsx (2500+ líneas original) para reducir el monolito.
 * Cada hook encapsula una responsabilidad de fetching/estado que antes
 * estaba dispersa en useState + useCallback + useEffect en la page.
 *
 * Reglas de extracción:
 * - No cambia el contrato de datos ni de acciones.
 * - Los hooks retornan el estado y las funciones que la page necesita.
 * - La page sigue siendo el orquestador que decide qué renderizar.
 */

import { useCallback, useRef, useState } from 'react';
import { apiFetch } from '@/lib/http';
import { toast } from 'sonner';
import type {
  GroupDetailResponse,
  SessionDetailResponse,
  SessionRow,
  Strategy,
  StrategyGroup,
  StrategyMetrics,
} from '../../types';
import type {
  AttendancePersona,
  CustomRole,
  FollowUpRecord,
  SearchablePersona as SharedSearchablePersona,
} from './strategyDetailShared';

// ── Hook: Estrategia ────────────────────────────────────────────────

export function useStrategy(id: string, token: string | null) {
  const [strategy, setStrategy] = useState<Strategy | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [saving, setSaving] = useState(false);

  const [editName, setEditName] = useState('');
  const [editDesc, setEditDesc] = useState('');
  const [editType, setEditType] = useState('');
  const [editStatus, setEditStatus] = useState<'active' | 'pending' | 'done'>('pending');
  const [editActiva, setEditActiva] = useState(true);
  const [editClaseRaiz, setEditClaseRaiz] = useState('');
  const [editDefaultRoleId, setEditDefaultRoleId] = useState<string | null | undefined>(undefined);
  const [editStartDate, setEditStartDate] = useState('');
  const [editEndDate, setEditEndDate] = useState('');
  const [editRecurrence, setEditRecurrence] = useState<string | null>(null);

  const fetchStrategy = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setLoadError(false);
    try {
      const result = await apiFetch<Strategy>(`/evangelism/strategies/${id}`, { token, silent: true });
      setStrategy(result);
      setEditName(result.name);
      setEditDesc(result.description || '');
      setEditType(result.strategy_type || '');
      setEditStatus(result.status || 'pending');
      setEditActiva(result.activa !== undefined ? result.activa : true);
      setEditClaseRaiz(result.clase_raiz || result.typology || '');
      setEditDefaultRoleId(result.default_role_id ?? null);
      setEditStartDate(result.start_date ? result.start_date.substring(0, 10) : '');
      setEditEndDate(result.end_date ? result.end_date.substring(0, 10) : '');
      setEditRecurrence(result.recurrence || null);
    } catch {
      setStrategy(null);
      setLoadError(true);
    } finally {
      setLoading(false);
    }
  }, [id, token]);

  const handleSave = useCallback(async () => {
    if (!strategy) return;
    setSaving(true);
    try {
      await apiFetch(`/evangelism/strategies/${id}`, {
        method: 'PUT', token, silent: true,
        body: {
          name: editName, description: editDesc, strategy_type: editType,
          status: editStatus, activa: editActiva,
          clase_raiz: editClaseRaiz || null,
          default_role_id: editDefaultRoleId ?? null,
          recurrence: editRecurrence,
          start_date: editStartDate ? `${editStartDate}T12:00:00` : null,
          end_date: editEndDate ? `${editEndDate}T12:00:00` : null,
        },
      });
      toast.success('Estrategia actualizada');
      window.dispatchEvent(new CustomEvent('evangelism-strategy-created'));
      await fetchStrategy();
    } catch (e: any) {
      toast.error('Error al guardar: ' + (e?.message || 'Error desconocido'));
    } finally {
      setSaving(false);
    }
  }, [strategy, id, token, editName, editDesc, editType, editStatus, editActiva, editClaseRaiz, editDefaultRoleId, editRecurrence, editStartDate, editEndDate, fetchStrategy]);

  const handleDelete = useCallback(async () => {
    if (!strategy) return;
    try {
      await apiFetch(`/evangelism/strategies/${id}`, { method: 'DELETE', token, silent: true });
      toast.success('Estrategia eliminada');
      window.dispatchEvent(new CustomEvent('evangelism-strategy-created'));
      window.location.href = '/plataforma/evangelism';
    } catch (e: any) {
      toast.error('Error al eliminar: ' + (e?.message || 'Intente de nuevo'));
    }
  }, [strategy, id, token]);

  return {
    strategy, loading, loadError, saving,
    editName, setEditName,
    editDesc, setEditDesc,
    editType, setEditType,
    editStatus, setEditStatus,
    editActiva, setEditActiva,
    editClaseRaiz, setEditClaseRaiz,
    editDefaultRoleId, setEditDefaultRoleId,
    editStartDate, setEditStartDate,
    editEndDate, setEditEndDate,
    editRecurrence, setEditRecurrence,
    fetchStrategy, handleSave, handleDelete,
  };
}

// ── Hook: Roles personalizados ──────────────────────────────────────

export function useCustomRoles(id: string, token: string | null) {
  const [customRoles, setCustomRoles] = useState<CustomRole[]>([]);
  const [loadingRoles, setLoadingRoles] = useState(false);
  const [showRoleForm, setShowRoleForm] = useState(false);
  const [newRoleName, setNewRoleName] = useState('');
  const [newRoleDesc, setNewRoleDesc] = useState('');

  const fetchCustomRoles = useCallback(async () => {
    if (!token) return;
    setLoadingRoles(true);
    try {
      const result = await apiFetch<CustomRole[]>(`/evangelism/strategies/${id}/roles`, { token, silent: true });
      setCustomRoles(result || []);
    } catch {
      setCustomRoles([]);
    } finally {
      setLoadingRoles(false);
    }
  }, [id, token]);

  return {
    customRoles, setCustomRoles, loadingRoles, showRoleForm, setShowRoleForm,
    newRoleName, setNewRoleName, newRoleDesc, setNewRoleDesc,
    fetchCustomRoles,
  };
}

// ── Hook: Grupos ────────────────────────────────────────────────────

export function useGroups(id: string, token: string | null) {
  const [groups, setGroups] = useState<StrategyGroup[]>([]);
  const [groupsLoading, setGroupsLoading] = useState(false);

  const fetchGroups = useCallback(async () => {
    if (!token) return;
    setGroupsLoading(true);
    try {
      const all = await apiFetch<StrategyGroup[]>('/evangelism/grupos', {
        token, silent: true,
        query: { evangelism_strategy_id: id },
      });
      setGroups(all || []);
    } catch {
      setGroups([]);
    } finally {
      setGroupsLoading(false);
    }
  }, [id, token]);

  return { groups, groupsLoading, fetchGroups, setGroups };
}

// ── Hook: Sesiones ──────────────────────────────────────────────────

export function useSessions(id: string, token: string | null) {
  const [sessions, setSessions] = useState<SessionRow[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);

  const fetchSessions = useCallback(async () => {
    if (!token) return;
    setSessionsLoading(true);
    try {
      const data = await apiFetch<SessionRow[]>(`/evangelism/sessions?strategy_id=${id}`, { token, silent: true });
      setSessions(data || []);
    } catch {
      setSessions([]);
    } finally {
      setSessionsLoading(false);
    }
  }, [id, token]);

  return { sessions, sessionsLoading, fetchSessions, setSessions };
}

// ── Hook: Métricas ──────────────────────────────────────────────────

export function useMetrics(id: string, token: string | null) {
  const [metrics, setMetrics] = useState<StrategyMetrics | null>(null);

  const fetchMetrics = useCallback(async () => {
    if (!token) return;
    try {
      const m = await apiFetch<StrategyMetrics>(`/evangelism/strategies/${id}/metrics`, { token, silent: true });
      setMetrics(m);
    } catch {
      setMetrics(null);
    }
  }, [id, token]);

  return { metrics, fetchMetrics };
}

// ── Hook: Seguimiento (follow-up) ───────────────────────────────────

export function useFollowUps(token: string | null) {
  const [followUps, setFollowUps] = useState<FollowUpRecord[]>([]);
  const [loadingFollowUps, setLoadingFollowUps] = useState(false);

  const fetchFollowUps = useCallback(async () => {
    if (!token) return;
    setLoadingFollowUps(true);
    try {
      const result = await apiFetch<FollowUpRecord[]>('/evangelism/follow-up/pending', { token, silent: true });
      setFollowUps(result || []);
    } catch {
      setFollowUps([]);
    } finally {
      setLoadingFollowUps(false);
    }
  }, [token]);

  return { followUps, loadingFollowUps, fetchFollowUps };
}

// ── Hook: Acciones de sesión (habilitación, bulk) ───────────────────

export function useSessionActions(fetchSessions: () => void, token: string | null) {
  const toggleSessionHabilitacion = useCallback(async (session: SessionRow) => {
    if (session.estado_habilitacion === 'CERRADO' || session.estado_habilitacion === 'CANCELADA') {
      toast.error('Esta sesión no se puede habilitar');
      return;
    }
    const accion = session.estado_habilitacion === 'HABILITADO' ? 'DESHABILITAR' : 'HABILITAR';
    try {
      await apiFetch(`/evangelism/sessions/${session.id}/habilitacion`, {
        method: 'PATCH', token, silent: true, body: { accion },
      });
      toast.success(accion === 'HABILITAR' ? 'Sesión habilitada' : 'Sesión bloqueada');
      fetchSessions();
    } catch {
      toast.error('Error al cambiar estado');
    }
  }, [fetchSessions, token]);

  const handleDeleteSession = useCallback(async (sessionId: string) => {
    try {
      await apiFetch(`/evangelism/sessions/${sessionId}`, { method: 'DELETE', token, silent: true });
      toast.success('Sesión eliminada');
      fetchSessions();
    } catch (e: any) {
      toast.error('Error: ' + (e.message || 'Intente de nuevo'));
    }
  }, [fetchSessions, token]);

  return { toggleSessionHabilitacion, handleDeleteSession };
}

// ── Hook: Gestión de grupos (creación, eliminación) ─────────────────

export function useGroupActions(
  id: string,
  fetchGroups: () => void,
  fetchStrategy: () => void,
  token: string | null,
) {
  const [isGroupDrawerOpen, setIsGroupDrawerOpen] = useState(false);
  const [groupSaving, setGroupSaving] = useState(false);
  const [roleResults, setRoleResults] = useState<Record<string, any[]>>({});
  const [roleLoading, setRoleLoading] = useState<Record<string, boolean>>({});

  const handleCreateGroup = useCallback(async (
    groupForm: any,
    buildRoleDrivenAssignments: () => any,
    resetForm: () => void,
  ) => {
    if (!groupForm.name.trim()) { toast.error('El nombre del grupo es obligatorio'); return; }
    setGroupSaving(true);
    try {
      const roleDrivenAssignments = buildRoleDrivenAssignments();
      await apiFetch('/evangelism/grupos', {
        method: 'POST', token, silent: true,
        body: {
          name: groupForm.name.trim(), code: null,
          zone: groupForm.zone || null, address: groupForm.address || null,
          latitude: null, longitude: null, leader_name: null,
          leader_id: roleDrivenAssignments.fixed.leader_id,
          assistant_id: roleDrivenAssignments.fixed.assistant_id,
          host_id: roleDrivenAssignments.fixed.host_id,
          evangelism_strategy_id: id,
          personas_count: 0, capacity: groupForm.capacity,
          status: 'Activo',
          day_of_week: groupForm.day_of_week || null,
          start_time: groupForm.start_time || null,
          end_time: groupForm.end_time || null,
          base_attendees_with_roles: roleDrivenAssignments.base_attendees_with_roles,
        },
      });
      toast.success('Grupo creado');
      resetForm();
      fetchGroups();
      fetchStrategy();
    } catch (e: any) {
      toast.error('Error al crear: ' + (e.message || 'Intente de nuevo'));
    } finally {
      setGroupSaving(false);
    }
  }, [id, token, fetchGroups, fetchStrategy]);

  const handleDeleteGroup = useCallback(async (groupId: string) => {
    try {
      await apiFetch(`/evangelism/grupos/${groupId}`, { method: 'DELETE', token, silent: true });
      toast.success('Grupo eliminado');
      fetchGroups();
      fetchStrategy();
    } catch {
      toast.error('Error al eliminar');
    }
  }, [token, fetchGroups, fetchStrategy]);

  return {
    isGroupDrawerOpen, setIsGroupDrawerOpen,
    groupSaving, setGroupSaving,
    roleResults, setRoleResults,
    roleLoading, setRoleLoading,
    handleCreateGroup, handleDeleteGroup,
  };
}

// ── Hook: Persona search (remoto con debounce + AbortController) ─────
// Este hook ya existía inline en page.tsx pero duplicado para
// addPersona y visitorSearch. Se unifica aquí.

export function useRemotePersonaSearch(token: string | null) {
  const abortRef = useRef<AbortController | null>(null);

  const search = useCallback(async (q: string, limit: number = 10): Promise<SharedSearchablePersona[]> => {
    if (!token || q.trim().length < 3) return [];
    if (abortRef.current) abortRef.current.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const res = await apiFetch<{ results: SharedSearchablePersona[] }>('/evangelism/personas/search', {
        token, silent: true, query: { q, limit }, signal: controller.signal,
      });
      if (!controller.signal.aborted) return res.results || [];
    } catch {
      if (!controller.signal.aborted) return [];
    }
    return [];
  }, [token]);

  const cancel = useCallback(() => {
    if (abortRef.current) abortRef.current.abort();
  }, []);

  return { search, cancel };
}

// ── Hook: Attendance drawer ─────────────────────────────────────────

export function useAttendanceDrawer(id: string, token: string | null, fetchSessions: () => void) {
  const [attendanceSession, setAttendanceSession] = useState<SessionRow | null>(null);
  const [attendancePersonas, setAttendancePersonas] = useState<AttendancePersona[]>([]);
  const [attendanceSaving, setAttendanceSaving] = useState(false);
  const [isAttendanceDrawerOpen, setIsAttendanceDrawerOpen] = useState(false);

  const openAttendanceDrawer = useCallback(async (session: SessionRow) => {
    if (session.estado_habilitacion !== 'HABILITADO') {
      toast.error('Habilita la sesión antes de registrar asistencia');
      return;
    }
    setAttendanceSession(session);
    setIsAttendanceDrawerOpen(true);
    try {
      const house = await apiFetch<GroupDetailResponse>(`/evangelism/grupos/${session.grupo_id}`, { token, silent: true });
      const existing = await apiFetch<SessionDetailResponse>(`/evangelism/sessions/${session.id}`, { token, silent: true }).catch(() => null);
      const existingMap: Record<string, { status: string; notes: string }> = {};
      if (existing?.attendance) {
        for (const a of existing.attendance) {
          existingMap[a.persona_id] = { status: a.status, notes: a.notes || '' };
        }
      }
      const personaList = house?.base_attendees?.map((a: any) => ({
        persona_id: a.persona_id,
        name: a.name || a.persona?.nombre_completo || '',
        role: a.role || 'persona',
        role_label: a.role_label,
        status: (existingMap[a.persona_id]?.status as any) || 'present',
        notes: existingMap[a.persona_id]?.notes || '',
      })) || [];
      setAttendancePersonas(personaList);
    } catch {
      setAttendancePersonas([]);
    }
  }, [token]);

  const handleSaveAttendance = useCallback(async () => {
    if (!attendanceSession) return;
    if (attendanceSession.estado_habilitacion !== 'HABILITADO') {
      toast.error('Habilita la sesión antes de registrar asistencia');
      return;
    }
    setAttendanceSaving(true);
    try {
      await apiFetch(`/evangelism/sessions/${attendanceSession.id}/attendance`, {
        method: 'POST', token,
        body: attendancePersonas.map(m => ({
          session_id: attendanceSession.id,
          persona_id: m.persona_id,
          status: m.status,
          notes: m.notes || null,
        })),
      });
      toast.success('Asistencia registrada');
      setIsAttendanceDrawerOpen(false);
      fetchSessions();
    } catch (e: any) {
      toast.error('Error: ' + (e.message || 'Intente de nuevo'));
    } finally {
      setAttendanceSaving(false);
    }
  }, [attendanceSession, attendancePersonas, token, fetchSessions]);

  return {
    attendanceSession, setAttendanceSession,
    attendancePersonas, setAttendancePersonas,
    attendanceSaving,
    isAttendanceDrawerOpen, setIsAttendanceDrawerOpen,
    openAttendanceDrawer, handleSaveAttendance,
  };
}
