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
  SessionRow,
  Strategy,
  StrategyGroup,
  StrategyMetrics,
} from '../../types';
import type {
  CustomRole,
  FollowUpRecord,
  SearchablePersona as SharedSearchablePersona,
} from './strategyDetailShared';
import { getErrorMessage } from '../../utils';

const normalizeRootClass = (value: string | null | undefined): string => {
  const normalized = String(value || '').trim().toLowerCase().replace(/\s+/g, '_');
  if (normalized === 'relacional' || normalized === 'evento_masivo' || normalized === 'sectorial') {
    return normalized;
  }
  return '';
};

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
      // The API persists clase_raiz in uppercase (e.g. RELACIONAL), while
      // the selector values are lowercase. Normalize on read so the active
      // button is visibly selected when opening an existing strategy.
      setEditClaseRaiz(normalizeRootClass(result.clase_raiz) || normalizeRootClass(result.typology));
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
    } catch (error: unknown) {
      toast.error('Error al guardar: ' + getErrorMessage(error, 'Error desconocido'));
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
    } catch (error: unknown) {
      toast.error('Error al eliminar: ' + getErrorMessage(error, 'Intente de nuevo'));
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

export function useFollowUps(token: string | null, strategyId?: string | null) {
  const [followUps, setFollowUps] = useState<FollowUpRecord[]>([]);
  const [loadingFollowUps, setLoadingFollowUps] = useState(false);

  const fetchFollowUps = useCallback(async () => {
    if (!token) return;
    setLoadingFollowUps(true);
    try {
      // Si ``strategyId`` está presente, scoping por estrategia — el panel
      // dentro de ``/strategies/[id]`` solo muestra seguimientos de esa
      // estrategia en vez de toda la sede (brecha #10 auditoria follow-up).
      const query = strategyId ? `?strategy_id=${encodeURIComponent(strategyId)}` : '';
      const result = await apiFetch<FollowUpRecord[]>(`/evangelism/follow-up/pending${query}`, { token, silent: true });
      setFollowUps(result || []);
    } catch {
      setFollowUps([]);
    } finally {
      setLoadingFollowUps(false);
    }
  }, [token, strategyId]);

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
    } catch (error: unknown) {
      toast.error('Error: ' + getErrorMessage(error, 'Intente de nuevo'));
    }
  }, [fetchSessions, token]);

  return { toggleSessionHabilitacion, handleDeleteSession };
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
