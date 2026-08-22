'use client';

import type { LucideIcon } from 'lucide-react';
import { type ConfirmActionState } from '@/components/evangelism/ConfirmActionDrawer';
import type { ViewType } from '@/components/ViewSwitcher';
import { useAuth } from '@/context/AuthContext';
import { useSidebarLayers } from '@/context/SidebarLayerContext';
import { apiFetch } from '@/lib/http';
import { filtroAPersona } from '@/lib/filtroAPersonas';
import { parseAndValidateTime } from '@/lib/time';
import {
  BarChart3,
  Home as HomeIcon,
  Plus,
  ShieldCheck,
  UserPlus,
  Users,
} from 'lucide-react';
import { useSearchParams, useRouter } from 'next/navigation';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';
import { getErrorMessage } from '../../utils';

// Los tipos públicos del módulo (Grupo era exportado en el original page; se preserva
// la firma para no romper el import `type { Grupo } from './page'` que hace GroupViews.tsx).

export interface Grupo {
  id: string;
  code?: string;
  name: string;
  zone?: string;
  address?: string;
  leader_id?: string;
  assistant_id?: string;
  host_id?: string;
  base_attendee_ids?: string[];
  base_attendees?: Array<{
    persona_id: string;
    name: string;
    role?: string;
    church_role?: string;
  }>;
  capacity: number;
  day_of_week?: string;
  start_time?: string;
  end_time?: string;
  status: string;
}

export interface Persona {
  id: string;
  nombre_completo: string;
  church_role?: string;
}

export interface AssignmentSummary {
  houses_total: number;
  houses_with_leader: number;
  houses_without_leader: number;
  houses_with_assistant: number;
  houses_without_assistant: number;
  houses_with_host: number;
  houses_without_host: number;
  houses_with_personas: number;
  houses_without_personas: number;
  personas_total: number;
  personas_unassigned: number;
  houses_needing_leader: Array<{
    id: string;
    name: string;
    code?: string;
    zone?: string;
    address?: string;
  }>;
  houses_needing_assistant: Array<{
    id: string;
    name: string;
    code?: string;
    zone?: string;
    address?: string;
  }>;
  houses_needing_host: Array<{
    id: string;
    name: string;
    code?: string;
    zone?: string;
    address?: string;
  }>;
  unassigned_personas: Array<{ id: string; name: string; church_role?: string }>;
}

export type Mode = 'create' | 'leader' | 'assistant' | 'host' | 'personas' | 'monitor';

export const MODE_CONFIG: Record<
  Mode,
  { title: string; description: string; icon: LucideIcon }
> = {
  create: {
    title: 'Crear Grupo',
    description: 'Alta rápida con datos mínimos',
    icon: Plus,
  },
  leader: {
    title: 'Asignar líder',
    description: 'Casas sin líder o con líder actual',
    icon: Users,
  },
  assistant: {
    title: 'Asignar colíder',
    description: 'Casas sin colíder o con colíder actual',
    icon: ShieldCheck,
  },
  host: {
    title: 'Asignar anfitrión',
    description: 'Cambios de casa, dirección y anfitrión',
    icon: HomeIcon,
  },
  personas: {
    title: 'Asignar personas',
    description: 'Personas sin casa y personas por casa',
    icon: UserPlus,
  },
  monitor: {
    title: 'Monitoreo',
    description: 'Tendencia, alertas y actividad por casa',
    icon: BarChart3,
  },
};

export const FORM_INPUT_CLASS =
  'w-full bg-[hsl(var(--bg-muted))] dark:bg-black/20 border border-[hsl(var(--border-primary))] rounded-md px-4 py-1.5 text-sm font-medium focus:ring-2 focus:ring-[hsl(var(--primary)/0.2)] focus:border-[hsl(var(--primary))] outline-none transition-all placeholder:text-[hsl(var(--text-secondary))]';

export function useGroupsPage() {
  const { token } = useAuth();
  const searchParams = useSearchParams();
  const router = useRouter();
  const { pushSidebarPanel, resetSidebarStack } = useSidebarLayers();
  const [houses, setHouses] = useState<Grupo[]>([]);
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [summary, setSummary] = useState<AssignmentSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [viewType, setViewType] = useState<ViewType>('list');
  const [mode, setMode] = useState<Mode>('create');

  const [selectedHouse, setSelectedHouse] = useState<Grupo | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [isAddingPersonas, setIsAddingPersonas] = useState(false);
  const [formData, setFormData] = useState<Partial<Grupo>>({
    capacity: 15,
    status: 'Activo',
  });
  const [selectedPersonaIds, setSelectedPersonaIds] = useState<Set<string>>(
    new Set()
  );
  const [personaSearchQuery, setPersonaSearchQuery] = useState('');
  const [personaRoleFilter, setPersonaRoleLinkFilter] = useState('');
  const [personaAssignmentFilter, setPersonaAssignmentFilter] = useState('all');
  const [confirmAction, setConfirmAction] = useState<ConfirmActionState>(null);
  const [quickAssignmentTargets, setQuickAssignmentTargets] = useState<
    Record<string, string>
  >({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const raw = (searchParams?.get('mode') || 'create').toLowerCase();
    if (
      raw === 'leader' ||
      raw === 'assistant' ||
      raw === 'host' ||
      raw === 'personas' ||
      raw === 'monitor' ||
      raw === 'create'
    ) {
      setMode(raw);
    } else {
      setMode('create');
    }
  }, [searchParams]);

  useEffect(() => {
    if (!token) return;
    setLoading(true);

    let cancelled = false;

    const loadPersonas = async () => {
      const pageSize = 250;
      let skip = 0;
      const allPersonas: Persona[] = [];

      while (true) {
        const data = await apiFetch<unknown>('/crm/personas', {
          token,
          silent: true,
          query: {
            skip,
            limit: pageSize,
            sort_by: 'nombre_completo',
            sort_dir: 'asc',
          },
        });

        const page = Array.isArray(data)
          ? data
          : Array.isArray((data as { items?: Persona[] })?.items)
            ? (data as { items: Persona[] }).items
            : [];

        allPersonas.push(...page);

        if (page.length < pageSize) break;
        skip += pageSize;
      }

      return allPersonas;
    };

    Promise.all([
      apiFetch<Grupo[]>('/evangelism/grupos', { token, silent: true }),
      loadPersonas(),
      apiFetch<AssignmentSummary>('/evangelism/groups/assignment-summary', {
        token,
        silent: true,
      }).catch(() => null),
    ])
      .then(([housesData, personasData, summaryData]) => {
        if (cancelled) return;
        setHouses(housesData);
        setPersonas(personasData);
        setSummary(summaryData);
      })
      .catch(() => {
        if (!cancelled) {
          setHouses([]);
          setPersonas([]);
          setSummary(null);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [token]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      let start_time = formData.start_time || '';
      let end_time = formData.end_time || '';

      if (start_time) {
        const startParsed = parseAndValidateTime(start_time);
        if (!startParsed.valid) {
          toast.error("Formato de hora de inicio inválido (use HH:MM o AM/PM)");
          setSaving(false);
          return;
        }
        start_time = startParsed.normalized;
      }
      if (end_time) {
        const endParsed = parseAndValidateTime(end_time);
        if (!endParsed.valid) {
          toast.error("Formato de hora de finalización inválido (use HH:MM o AM/PM)");
          setSaving(false);
          return;
        }
        end_time = endParsed.normalized;
      }

      if (start_time && end_time) {
        const startParsed = parseAndValidateTime(start_time);
        const endParsed = parseAndValidateTime(end_time);
        if (startParsed.valid && endParsed.valid && endParsed.minutes <= startParsed.minutes) {
          toast.error("La hora de finalización debe ser posterior a la hora de inicio");
          setSaving(false);
          return;
        }
      }

      const payload = {
        ...formData,
        start_time: start_time || null,
        end_time: end_time || null,
        base_attendee_ids: Array.from(selectedPersonaIds),
      };
      if (isCreating) {
        const res = await apiFetch<Grupo>('/evangelism/grupos', {
          method: 'POST',
          body: payload,
          token,
          silent: true,
        });
        setHouses([res, ...houses]);
        const detail = await apiFetch<Grupo>(
          `/evangelism/grupos/${res.id}`,
          { token, silent: true }
        );
        setSelectedHouse(detail);
        setFormData(detail);
        setSelectedPersonaIds(
          new Set(
            detail.base_attendee_ids ||
            detail.base_attendees?.map(m => m.persona_id) ||
            []
          )
        );
        toast.success('Grupo creado');
        setIsCreating(false);
      } else if (selectedHouse) {
        const res = await apiFetch<Grupo>(
          `/evangelism/grupos/${selectedHouse.id}`,
          {
            method: 'PUT',
            body: payload,
            token,
            silent: true,
          }
        );
        setHouses(houses.map(h => (h.id === res.id ? res : h)));
        const detail = await apiFetch<Grupo>(
          `/evangelism/grupos/${res.id}`,
          { token, silent: true }
        );
        setSelectedHouse(detail);
        setFormData(detail);
        setSelectedPersonaIds(
          new Set(
            detail.base_attendee_ids ||
            detail.base_attendees?.map(m => m.persona_id) ||
            []
          )
        );
        toast.success('Grupo actualizado');
      }
    } catch (error: unknown) {
      toast.error(getErrorMessage(error, 'Error al guardar grupo'));
    } finally {
      setSaving(false);
    }
  };

  const handleSelectHouse = useCallback(async (h: Grupo) => {
    setIsCreating(false);
    try {
      const detail = await apiFetch<Grupo>(`/evangelism/grupos/${h.id}`, { token, silent: true });
      setSelectedHouse(detail);
      setFormData(detail);
      setSelectedPersonaIds(new Set(detail.base_attendee_ids || detail.base_attendees?.map(m => m.persona_id) || []));
    } catch {
      setSelectedHouse(h);
      setFormData(h);
      setSelectedPersonaIds(new Set());
    }
  }, [token]);

  const handleDeleteHouse = useCallback(async (house: Grupo) => {
    try {
      await apiFetch(`/evangelism/grupos/${house.id}`, {
        method: 'DELETE',
        token,
        silent: true,
      });
      setHouses(houses.filter(h => h.id !== house.id));
      if (selectedHouse?.id === house.id) {
        setSelectedHouse(null);
        setIsCreating(false);
      }
      toast.success(`Grupo "${house.name}" eliminado`);
    } catch (error: unknown) {
      toast.error(getErrorMessage(error, 'Error al eliminar grupo'));
    }
  }, [token, houses, selectedHouse]);

  const requestDeleteHouse = useCallback((house: Grupo) => {
    setConfirmAction({
      title: 'Eliminar grupo',
      description: `Se eliminará "${house.name}" y dejará de estar disponible para reportes nuevos.`,
      confirmLabel: 'Eliminar',
      destructive: true,
      onConfirm: () => handleDeleteHouse(house),
    });
  }, [handleDeleteHouse]);

  const handleQuickAssignPersona = async (personaId: string) => {
    const grupoId = quickAssignmentTargets[personaId];
    if (!grupoId) {
      toast.error('Selecciona una casa');
      return;
    }
    setSaving(true);
    try {
      const detail = await apiFetch<Grupo>(`/evangelism/grupos/${grupoId}`, { token, silent: true });
      const current = new Set(
        detail.base_attendee_ids ||
        detail.base_attendees?.map(m => m.persona_id) ||
        []
      );
      current.add(personaId);
      const updated = await apiFetch<Grupo>(`/evangelism/grupos/${grupoId}`, {
        method: 'PUT',
        body: {
          code: detail.code,
          name: detail.name,
          zone: detail.zone,
          address: detail.address,
          leader_id: detail.leader_id,
          assistant_id: detail.assistant_id,
          host_id: detail.host_id,
          capacity: detail.capacity,
          day_of_week: detail.day_of_week,
          start_time: detail.start_time,
          end_time: detail.end_time,
          status: detail.status,
          base_attendee_ids: Array.from(current),
        },
        token,
        silent: true,
      });
      setHouses(prev => prev.map(h => (h.id === updated.id ? updated : h)));
      const refreshed = await apiFetch<AssignmentSummary>(
        '/evangelism/groups/assignment-summary',
        { token }
      );
      setSummary(refreshed);
      toast.success('Persona asignado');
    } catch {
      toast.error('Error al asignar persona');
    } finally {
      setSaving(false);
    }
  };

  const filteredHouses = useMemo(() => {
    const q = searchQuery.toLowerCase();
    let items = houses.filter(
      h =>
        h.name.toLowerCase().includes(q) ||
        h.zone?.toLowerCase().includes(q) ||
        h.code?.toLowerCase().includes(q)
    );
    if (mode === 'leader') items = items.filter(h => !h.leader_id);
    if (mode === 'assistant') items = items.filter(h => !h.assistant_id);
    if (mode === 'host') items = items.filter(h => !h.host_id);
    if (mode === 'personas')
      items = items.filter(h => (h.capacity ?? 0) > 0 || h.status === 'Activo');
    return items;
  }, [houses, mode, searchQuery]);

  const getPersonaName = useCallback((id?: string) => {
    if (!id) return 'No asignado';
    const m = personas.find(m => m.id === id);
    return m ? m.nombre_completo : 'Desconocido';
  }, [personas]);

  const uniqueRoles = useMemo(() => {
    return Array.from(new Set(personas.map(m => m.church_role).filter(Boolean))).sort();
  }, [personas]);

  const filteredPersonasList = useMemo(() => {
    const base = [...personas].sort((a, b) =>
      (a.nombre_completo || '').localeCompare(b.nombre_completo || '', 'es')
    );

    return base.filter(m => {
      if (!filtroAPersona(m, personaSearchQuery)) {
        return false;
      }
      if (personaRoleFilter && m.church_role !== personaRoleFilter) {
        return false;
      }
      if (personaAssignmentFilter !== 'all') {
        const isAssignedToThis = selectedPersonaIds.has(m.id);
        const isUnassigned = summary?.unassigned_personas.some(u => u.id === m.id);

        if (personaAssignmentFilter === 'this_house' && !isAssignedToThis) return false;
        if (personaAssignmentFilter === 'unassigned' && !isUnassigned) return false;
        if (personaAssignmentFilter === 'other_house' && (isAssignedToThis || isUnassigned)) return false;
      }
      return true;
    });
  }, [personas, personaSearchQuery, personaRoleFilter, personaAssignmentFilter, selectedPersonaIds, summary]);

  const showPanel = selectedHouse !== null || isCreating || mode === 'personas';

  return {
    // State - data
    houses,
    personas,
    summary,
    loading,
    // State - UI
    searchQuery, setSearchQuery,
    viewType, setViewType,
    mode,
    // State - selection/form
    selectedHouse,
    setSelectedHouse,
    isCreating, setIsCreating,
    isAddingPersonas, setIsAddingPersonas,
    formData, setFormData,
    selectedPersonaIds, setSelectedPersonaIds,
    personaSearchQuery, setPersonaSearchQuery,
    personaRoleFilter, setPersonaRoleLinkFilter,
    personaAssignmentFilter, setPersonaAssignmentFilter,
    confirmAction, setConfirmAction,
    quickAssignmentTargets, setQuickAssignmentTargets,
    saving,
    // Derived
    filteredHouses,
    filteredPersonasList,
    uniqueRoles,
    showPanel,
    getPersonaName,
    // Handlers
    handleSave,
    handleSelectHouse,
    requestDeleteHouse,
    handleQuickAssignPersona,
    // Sidebar context (passthrough para que el page los use en useEffect)
    pushSidebarPanel,
    resetSidebarStack,
    router,
    token,
  };
}
