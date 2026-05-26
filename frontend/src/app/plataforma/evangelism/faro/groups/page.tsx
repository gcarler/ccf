'use client';

import React, { useState, Suspense, useEffect, useMemo, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useSearchParams, useRouter } from 'next/navigation';
import { apiFetch } from '@/lib/http';
import { useSidebarLayers } from '@/context/SidebarLayerContext';
import EvangelismShell from '@/components/evangelism/EvangelismShell';
import {
  Home,
  Plus,
  Search,
  MapPin,
  Users,
  Activity,
  X,
  CheckCircle2,
  Clock,
  Calendar,
  UserPlus,
  ShieldCheck,
  BarChart3,
  Trash2,
  List,
  LayoutGrid,
  Columns3,
  Table2,
  ChevronRight,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { toast } from 'sonner';
import { parseAndValidateTime } from '@/lib/time';
import type { ViewType } from '@/components/ViewSwitcher';



interface GloryHouse {
  id: number;
  code?: string;
  name: string;
  zone?: string;
  address?: string;
  leader_id?: number;
  assistant_id?: number;
  host_id?: number;
  base_attendee_ids?: number[];
  base_attendees?: Array<{
    member_id: number;
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

interface Member {
  id: number;
  first_name: string;
  last_name: string;
  church_role?: string;
}

interface AssignmentSummary {
  houses_total: number;
  houses_with_leader: number;
  houses_without_leader: number;
  houses_with_assistant: number;
  houses_without_assistant: number;
  houses_with_host: number;
  houses_without_host: number;
  houses_with_members: number;
  houses_without_members: number;
  members_total: number;
  members_unassigned: number;
  houses_needing_leader: Array<{
    id: number;
    name: string;
    code?: string;
    zone?: string;
    address?: string;
  }>;
  houses_needing_assistant: Array<{
    id: number;
    name: string;
    code?: string;
    zone?: string;
    address?: string;
  }>;
  houses_needing_host: Array<{
    id: number;
    name: string;
    code?: string;
    zone?: string;
    address?: string;
  }>;
  unassigned_members: Array<{ id: number; name: string; church_role?: string }>;
}

type Mode = 'create' | 'leader' | 'assistant' | 'host' | 'members' | 'monitor';

const MODE_CONFIG: Record<
  Mode,
  { title: string; description: string; icon: LucideIcon }
> = {
  create: {
    title: 'Crear Faro',
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
    icon: Home,
  },
  members: {
    title: 'Asignar miembros',
    description: 'Miembros sin casa y miembros por casa',
    icon: UserPlus,
  },
  monitor: {
    title: 'Monitoreo',
    description: 'Tendencia, alertas y actividad por casa',
    icon: BarChart3,
  },
};

function FaroGroupsContent() {
  const { token } = useAuth();
  const searchParams = useSearchParams();
  const router = useRouter();
  const { pushSidebarPanel, resetSidebarStack } = useSidebarLayers();
  const [houses, setHouses] = useState<GloryHouse[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [summary, setSummary] = useState<AssignmentSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [viewType, setViewType] = useState<ViewType>('list');
  const [mode, setMode] = useState<Mode>('create');

  const [selectedHouse, setSelectedHouse] = useState<GloryHouse | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [isAddingMembers, setIsAddingMembers] = useState(false);
  const [formData, setFormData] = useState<Partial<GloryHouse>>({
    capacity: 15,
    status: 'Activo',
  });
  const [selectedMemberIds, setSelectedMemberIds] = useState<Set<number>>(
    new Set()
  );
  const [memberSearchQuery, setMemberSearchQuery] = useState('');
  const [memberRoleFilter, setMemberRoleFilter] = useState('');
  const [memberAssignmentFilter, setMemberAssignmentFilter] = useState('all');
  const [quickAssignmentTargets, setQuickAssignmentTargets] = useState<
    Record<number, number>
  >({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const raw = (searchParams?.get('mode') || 'create').toLowerCase();
    if (
      raw === 'leader' ||
      raw === 'assistant' ||
      raw === 'host' ||
      raw === 'members' ||
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
    Promise.all([
      apiFetch<GloryHouse[]>('/evangelism/glory-houses', { token }),
      apiFetch<Member[]>('/crm/members/', { token }),
      apiFetch<AssignmentSummary>('/evangelism/faro/assignment-summary', {
        token,
      }).catch(() => null),
    ])
      .then(([housesData, membersData, summaryData]) => {
        setHouses(housesData);
        setMembers(membersData);
        setSummary(summaryData);
      })
      .catch(() => toast.error('Error al cargar datos'))
      .finally(() => setLoading(false));
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
        base_attendee_ids: Array.from(selectedMemberIds),
      };
      if (isCreating) {
        const res = await apiFetch<GloryHouse>('/evangelism/glory-houses', {
          method: 'POST',
          body: payload,
          token,
        });
        setHouses([res, ...houses]);
        const detail = await apiFetch<GloryHouse>(
          `/evangelism/glory-houses/${res.id}`,
          { token }
        );
        setSelectedHouse(detail);
        setFormData(detail);
        setSelectedMemberIds(
          new Set(
            detail.base_attendee_ids ||
              detail.base_attendees?.map(m => m.member_id) ||
              []
          )
        );
        toast.success('Grupo creado');
        setIsCreating(false);
      } else if (selectedHouse) {
        const res = await apiFetch<GloryHouse>(
          `/evangelism/glory-houses/${selectedHouse.id}`,
          {
            method: 'PUT',
            body: payload,
            token,
          }
        );
        setHouses(houses.map(h => (h.id === res.id ? res : h)));
        const detail = await apiFetch<GloryHouse>(
          `/evangelism/glory-houses/${res.id}`,
          { token }
        );
        setSelectedHouse(detail);
        setFormData(detail);
        setSelectedMemberIds(
          new Set(
            detail.base_attendee_ids ||
              detail.base_attendees?.map(m => m.member_id) ||
              []
          )
        );
        toast.success('Grupo actualizado');
      }
    } catch (error: any) {
      console.error("Error saving group:", error);
      const msg = error?.message || 'Error al guardar grupo';
      toast.error(msg);
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteHouse = async (house: GloryHouse) => {
    if (!confirm(`¿Está seguro que desea eliminar "${house.name}"?\n\nEsta acción no se puede deshacer.`)) return;
    try {
      await apiFetch(`/evangelism/glory-houses/${house.id}`, {
        method: 'DELETE',
        token,
      });
      setHouses(houses.filter(h => h.id !== house.id));
      if (selectedHouse?.id === house.id) {
        setSelectedHouse(null);
        setIsCreating(false);
      }
      toast.success(`Grupo "${house.name}" eliminado`);
    } catch (error: any) {
      const msg = error?.message || 'Error al eliminar grupo';
      toast.error(msg);
    }
  };

  const handleQuickAssignMember = async (memberId: number) => {
    const houseId = quickAssignmentTargets[memberId];
    if (!houseId) {
      toast.error('Selecciona una casa');
      return;
    }
    setSaving(true);
    try {
      const detail = await apiFetch<GloryHouse>(
        `/evangelism/glory-houses/${houseId}`,
        { token }
      );
      const current = new Set(
        detail.base_attendee_ids ||
          detail.base_attendees?.map(m => m.member_id) ||
          []
      );
      current.add(memberId);
      const updated = await apiFetch<GloryHouse>(
        `/evangelism/glory-houses/${houseId}`,
        {
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
        }
      );
      setHouses(prev => prev.map(h => (h.id === updated.id ? updated : h)));
      const refreshed = await apiFetch<AssignmentSummary>(
        '/evangelism/faro/assignment-summary',
        { token }
      );
      setSummary(refreshed);
      toast.success('Miembro asignado');
    } catch {
      toast.error('Error al asignar miembro');
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
    if (mode === 'members')
      items = items.filter(h => (h.capacity ?? 0) > 0 || h.status === 'Activo');
    return items;
  }, [houses, mode, searchQuery]);

  const getMemberName = useCallback((id?: number) => {
    if (!id) return 'No asignado';
    const m = members.find(m => m.id === id);
    return m ? `${m.first_name} ${m.last_name}` : 'Desconocido';
  }, [members]);

  const uniqueRoles = useMemo(() => {
    return Array.from(new Set(members.map(m => m.church_role).filter(Boolean))).sort();
  }, [members]);

  const filteredMembersList = useMemo(() => {
    return members.filter(m => {
      if (memberSearchQuery && !`${m.first_name} ${m.last_name}`.toLowerCase().includes(memberSearchQuery.toLowerCase())) {
        return false;
      }
      if (memberRoleFilter && m.church_role !== memberRoleFilter) {
        return false;
      }
      if (memberAssignmentFilter !== 'all') {
        const isAssignedToThis = selectedMemberIds.has(m.id);
        const isUnassigned = summary?.unassigned_members.some(u => u.id === m.id);
        
        if (memberAssignmentFilter === 'this_house' && !isAssignedToThis) return false;
        if (memberAssignmentFilter === 'unassigned' && !isUnassigned) return false;
        if (memberAssignmentFilter === 'other_house' && (isAssignedToThis || isUnassigned)) return false;
      }
      return true;
    });
  }, [members, memberSearchQuery, memberRoleFilter, memberAssignmentFilter, selectedMemberIds, summary]);

  const inputCls =
    'w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-md px-4 py-1.5 text-sm font-medium focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400 outline-none transition-all placeholder:text-slate-400';

  const showPanel = selectedHouse !== null || isCreating || mode === 'members';

  // ── View Components ────────────────────────────────────────────────

  function ListView({ houses: items }: { houses: GloryHouse[] }) {
    return (
      <div className="flex-1 overflow-y-auto p-4">
        {items.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-400 gap-2">
            <Search size={32} className="opacity-40" />
            <p className="text-sm font-medium">No hay grupos que coincidan</p>
          </div>
        ) : (
          <div className="space-y-1 max-w-3xl">
            {items.map(h => (
              <button
                key={h.id}
                onClick={async () => {
                  setIsCreating(false);
                  try {
                    const detail = await apiFetch<GloryHouse>(`/evangelism/glory-houses/${h.id}`, { token });
                    setSelectedHouse(detail);
                    setFormData(detail);
                    setSelectedMemberIds(new Set(detail.base_attendee_ids || detail.base_attendees?.map(m => m.member_id) || []));
                  } catch {
                    setSelectedHouse(h); setFormData(h); setSelectedMemberIds(new Set());
                  }
                }}
                className="w-full text-left flex items-center justify-between gap-3 px-4 py-3 rounded-lg bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 hover:border-blue-300 dark:hover:border-blue-600 transition-all group"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-bold text-slate-900 dark:text-white truncate">{h.name}</span>
                    {h.code && <span className="text-[10px] font-mono text-slate-400">{h.code}</span>}
                  </div>
                  <div className="flex items-center gap-3 mt-1 text-xs text-slate-500">
                    {h.zone && <span><MapPin size={11} className="inline mr-1" />{h.zone}</span>}
                    {h.leader_id ? (
                      <span><Users size={11} className="inline mr-1" />{getMemberName(h.leader_id)}</span>
                    ) : (
                      <span className="text-amber-500 font-semibold">Sin líder</span>
                    )}
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${h.status === 'Activo' ? 'text-green-600 bg-green-50 dark:text-green-400 dark:bg-green-500/10' : 'text-slate-400 bg-slate-100 dark:bg-white/5'}`}>
                      {h.status}
                    </span>
                  </div>
                </div>
                <ChevronRight size={16} className="text-slate-300 group-hover:text-blue-500 transition-colors shrink-0" />
              </button>
            ))}
          </div>
        )}
      </div>
    );
  }

  function GridView({ houses: items }: { houses: GloryHouse[] }) {
    return (
      <div className="flex-1 overflow-y-auto p-4">
        {items.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-400 gap-2">
            <Search size={32} className="opacity-40" />
            <p className="text-sm font-medium">No hay grupos que coincidan</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
            {items.map(h => (
              <button
                key={h.id}
                onClick={async () => {
                  setIsCreating(false);
                  try {
                    const detail = await apiFetch<GloryHouse>(`/evangelism/glory-houses/${h.id}`, { token });
                    setSelectedHouse(detail); setFormData(detail);
                    setSelectedMemberIds(new Set(detail.base_attendee_ids || detail.base_attendees?.map(m => m.member_id) || []));
                  } catch {
                    setSelectedHouse(h); setFormData(h); setSelectedMemberIds(new Set());
                  }
                }}
                className="text-left w-full bg-white dark:bg-white/5 rounded-lg border border-slate-200 dark:border-white/10 p-4 hover:border-blue-300 dark:hover:border-blue-600 transition-all hover:shadow-md space-y-3"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="text-sm font-bold text-slate-900 dark:text-white truncate">{h.name}</p>
                    {h.code && <p className="text-[10px] font-mono text-slate-400">{h.code}</p>}
                  </div>
                  <span className={`shrink-0 px-2 py-0.5 rounded text-[10px] font-semibold ${h.status === 'Activo' ? 'text-green-600 bg-green-50 dark:text-green-400 dark:bg-green-500/10' : 'text-slate-400 bg-slate-100 dark:bg-white/5'}`}>
                    {h.status}
                  </span>
                </div>
                <div className="space-y-1.5 text-xs text-slate-500">
                  {h.zone && <p><MapPin size={12} className="inline mr-1.5" />{h.zone}</p>}
                  <p><Users size={12} className="inline mr-1.5" />{h.leader_id ? getMemberName(h.leader_id) : <span className="text-amber-500 font-semibold">Sin líder</span>}</p>
                  {h.address && <p className="truncate opacity-60">{h.address}</p>}
                </div>
                <div className="flex items-center gap-2 pt-2 border-t border-slate-100 dark:border-white/5">
                  <span className="text-[10px] text-slate-400">Cap. {h.capacity || '—'}</span>
                  {h.day_of_week && <span className="text-[10px] text-slate-400">{h.day_of_week}</span>}
                  {h.start_time && <span className="text-[10px] text-slate-400">{h.start_time}</span>}
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    );
  }

  function KanbanView({ houses: items }: { houses: GloryHouse[] }) {
    const zones = useMemo(() => {
      const map = new Map<string, GloryHouse[]>();
      items.forEach(h => {
        const z = h.zone || 'Sin zona';
        if (!map.has(z)) map.set(z, []);
        map.get(z)!.push(h);
      });
      return Array.from(map.entries()).sort(([a], [b]) => a.localeCompare(b));
    }, [items]);

    return (
      <div className="flex-1 overflow-x-auto p-4">
        {zones.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-400 gap-2">
            <Search size={32} className="opacity-40" />
            <p className="text-sm font-medium">No hay grupos que coincidan</p>
          </div>
        ) : (
          <div className="flex gap-4 h-full min-h-[400px]">
            {zones.map(([zone, zoneHouses]) => (
              <div key={zone} className="flex-shrink-0 w-72 bg-slate-50 dark:bg-white/5 rounded-lg border border-slate-200 dark:border-white/10 flex flex-col">
                <div className="px-3 py-2 border-b border-slate-200 dark:border-white/10 flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wide text-slate-600 dark:text-slate-300">{zone}</span>
                  <span className="text-[10px] font-semibold text-slate-400 bg-slate-200 dark:bg-white/10 px-2 py-0.5 rounded-full">{zoneHouses.length}</span>
                </div>
                <div className="flex-1 overflow-y-auto p-2 space-y-2">
                  {zoneHouses.map(h => (
                    <button
                      key={h.id}
                      onClick={async () => {
                        setIsCreating(false);
                        try {
                          const detail = await apiFetch<GloryHouse>(`/evangelism/glory-houses/${h.id}`, { token });
                          setSelectedHouse(detail); setFormData(detail);
                          setSelectedMemberIds(new Set(detail.base_attendee_ids || detail.base_attendees?.map(m => m.member_id) || []));
                        } catch {
                          setSelectedHouse(h); setFormData(h); setSelectedMemberIds(new Set());
                        }
                      }}
                      className="text-left w-full bg-white dark:bg-white/10 rounded-lg border border-slate-200 dark:border-white/5 p-3 hover:border-blue-300 dark:hover:border-blue-500 transition-all space-y-2"
                    >
                      <div className="flex items-start justify-between gap-1">
                        <p className="text-xs font-bold text-slate-900 dark:text-white truncate">{h.name}</p>
                        <span className={`shrink-0 px-1.5 py-0.5 rounded text-[9px] font-semibold ${h.status === 'Activo' ? 'text-green-600 bg-green-50 dark:text-green-400 dark:bg-green-500/10' : 'text-slate-400 bg-slate-100 dark:bg-white/5'}`}>
                          {h.status}
                        </span>
                      </div>
                      <div className="text-[10px] text-slate-500 space-y-1">
                        <p><Users size={10} className="inline mr-1" />{h.leader_id ? getMemberName(h.leader_id) : <span className="text-amber-500">Sin líder</span>}</p>
                        {h.address && <p className="truncate opacity-60">{h.address}</p>}
                      </div>
                      <div className="flex items-center gap-2 text-[9px] text-slate-400">
                        <span>Cap. {h.capacity || '—'}</span>
                        {h.day_of_week && <span>{h.day_of_week}</span>}
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  function TableView({ houses: items }: { houses: GloryHouse[] }) {
    return (
      <div className="flex-1 overflow-auto p-4">
        {items.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-400 gap-2">
            <Search size={32} className="opacity-40" />
            <p className="text-sm font-medium">No hay grupos que coincidan</p>
          </div>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-white/10">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-slate-50 dark:bg-white/5 border-b border-slate-200 dark:border-white/10">
                  <th className="text-left px-4 py-2.5 font-semibold text-slate-500 uppercase tracking-wider">Nombre</th>
                  <th className="text-left px-4 py-2.5 font-semibold text-slate-500 uppercase tracking-wider">Código</th>
                  <th className="text-left px-4 py-2.5 font-semibold text-slate-500 uppercase tracking-wider">Zona</th>
                  <th className="text-left px-4 py-2.5 font-semibold text-slate-500 uppercase tracking-wider">Líder</th>
                  <th className="text-left px-4 py-2.5 font-semibold text-slate-500 uppercase tracking-wider">Dirección</th>
                  <th className="text-center px-4 py-2.5 font-semibold text-slate-500 uppercase tracking-wider">Cap.</th>
                  <th className="text-center px-4 py-2.5 font-semibold text-slate-500 uppercase tracking-wider">Día</th>
                  <th className="text-center px-4 py-2.5 font-semibold text-slate-500 uppercase tracking-wider">Estado</th>
                  <th className="text-right px-4 py-2.5 font-semibold text-slate-500 uppercase tracking-wider">Acción</th>
                </tr>
              </thead>
              <tbody>
                {items.map(h => (
                  <tr
                    key={h.id}
                    onClick={async () => {
                      setIsCreating(false);
                      try {
                        const detail = await apiFetch<GloryHouse>(`/evangelism/glory-houses/${h.id}`, { token });
                        setSelectedHouse(detail); setFormData(detail);
                        setSelectedMemberIds(new Set(detail.base_attendee_ids || detail.base_attendees?.map(m => m.member_id) || []));
                      } catch {
                        setSelectedHouse(h); setFormData(h); setSelectedMemberIds(new Set());
                      }
                    }}
                    className="border-b border-slate-100 dark:border-white/5 hover:bg-blue-50/50 dark:hover:bg-blue-500/5 transition-colors cursor-pointer"
                  >
                    <td className="px-4 py-2.5 font-medium text-slate-900 dark:text-white whitespace-nowrap">{h.name}</td>
                    <td className="px-4 py-2.5 text-slate-500 font-mono">{h.code || '—'}</td>
                    <td className="px-4 py-2.5 text-slate-500">{h.zone || '—'}</td>
                    <td className="px-4 py-2.5 text-slate-500">{h.leader_id ? getMemberName(h.leader_id) : <span className="text-amber-500 font-semibold">Sin líder</span>}</td>
                    <td className="px-4 py-2.5 text-slate-400 max-w-[200px] truncate">{h.address || '—'}</td>
                    <td className="px-4 py-2.5 text-center text-slate-500">{h.capacity || '—'}</td>
                    <td className="px-4 py-2.5 text-center text-slate-500">{h.day_of_week || '—'}</td>
                    <td className="px-4 py-2.5 text-center">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${h.status === 'Activo' ? 'text-green-600 bg-green-50 dark:text-green-400 dark:bg-green-500/10' : 'text-slate-400 bg-slate-100 dark:bg-white/5'}`}>
                        {h.status}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      <button
                        onClick={(e) => { e.stopPropagation(); handleDeleteHouse(h); }}
                        className="p-1 rounded text-slate-300 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-500/10 transition-colors"
                        title="Eliminar"
                      >
                        <Trash2 size={13} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    );
  }

  // PUSH LIST TO SIDEBAR 2
  useEffect(() => {
    pushSidebarPanel({
      id: 'faro-groups-list',
      title: 'Grupos Faro',
      replaceAll: true,
      content: (
        <div className="flex flex-col h-full">
          <div className="px-3 pt-3 pb-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wide">
                Buscar Grupo
              </span>
              <button
                onClick={() => {
                  setIsCreating(true);
                  setSelectedHouse(null);
                  setSelectedMemberIds(new Set());
                  setFormData({ capacity: 15, status: 'Activo' });
                }}
                className="bg-blue-600 hover:bg-blue-700 text-white rounded-lg size-7 flex items-center justify-center transition-all shadow-sm active:scale-95"
              >
                <Plus size={14} />
              </button>
            </div>
            <div className="relative">
              <Search
                className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                size={14}
              />
              <input
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder="Buscar por nombre o zona..."
                className="w-full bg-slate-100 dark:bg-white/5 border border-transparent rounded-md py-2 pl-9 pr-3 text-xs font-medium focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400 outline-none transition-all"
              />
            </div>
          </div>

          <div className="flex-1 overflow-y-auto px-3 pb-4 scrollbar-thin flex flex-col gap-1">
            {loading ? (
              <div className="py-1.5 text-center text-slate-400">
                <Activity className="animate-spin mx-auto opacity-50" />
              </div>
            ) : filteredHouses.length === 0 ? (
              <div className="py-1.5 px-4 text-center">
                <Search size={24} className="mx-auto text-slate-300 dark:text-slate-600 mb-3" />
                <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">Sin resultados</p>
                <p className="text-xs text-slate-500 mt-1">No hay grupos que coincidan.</p>
              </div>
            ) : (
              filteredHouses.map(h => {
                const isActive = selectedHouse?.id === h.id;
                return (
                  <div
                    key={h.id}
                    className={`flex items-start gap-1 px-2 py-1.5 rounded-md border transition-all duration-200 ${
                      isActive
                        ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800 shadow-sm'
                        : 'bg-transparent border-transparent hover:bg-slate-100 dark:hover:bg-white/5'
                    }`}
                  >
                    <button
                      onClick={async () => {
                        setIsCreating(false);
                        try {
                          const detail = await apiFetch<GloryHouse>(
                            `/evangelism/glory-houses/${h.id}`,
                            { token }
                          );
                          setSelectedHouse(detail);
                          setFormData(detail);
                          setSelectedMemberIds(
                            new Set(
                              detail.base_attendee_ids ||
                                detail.base_attendees?.map(m => m.member_id) ||
                                []
                            )
                          );
                        } catch {
                          setSelectedHouse(h);
                          setFormData(h);
                          setSelectedMemberIds(new Set());
                        }
                      }}
                      className="flex-1 text-left min-w-0"
                    >
                      <p
                        className={`text-xs font-bold truncate leading-tight ${isActive ? 'text-blue-700 dark:text-blue-400' : 'text-slate-800 dark:text-white'}`}
                      >
                        {h.name}
                      </p>
                      <div className="mt-1 flex items-center justify-between">
                        <p className="text-[10px] font-medium text-slate-400 truncate">
                          {h.zone || 'Sin zona'}
                        </p>
                        {h.leader_id && (
                          <span className="text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-md bg-blue-100/50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 shrink-0">
                            {getMemberName(h.leader_id).split(' ')[0]}
                          </span>
                        )}
                      </div>
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); handleDeleteHouse(h); }}
                      className="shrink-0 p-1 rounded text-slate-300 dark:text-slate-600 hover:text-red-500 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-500/10 transition-colors"
                      title="Eliminar grupo"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                );
              })
            )}
          </div>
        </div>
      ),
    });
  }, [
    pushSidebarPanel,
    filteredHouses,
    searchQuery,
    loading,
    selectedHouse,
    isCreating,
    mode,
    token,
    getMemberName,
  ]);

  // Clean up sidebar when unmounting
  useEffect(() => {
    return () => resetSidebarStack();
  }, [resetSidebarStack]);

  return (
    <EvangelismShell
      breadcrumbs={[
        { label: 'Faro en Casa', href: '/plataforma/evangelism/faro', icon: Home },
        { label: 'Grupos', icon: Home },
      ]}
      viewType={viewType}
      onViewChange={setViewType}
      viewOptions={['list', 'kanban', 'grid', 'table']}
      onSearch={setSearchQuery}
    >
      <div className="flex h-full p-4 lg:p-4 bg-slate-50/50 dark:bg-[#252528]/50">
        {/* Detail/Edit Panel */}
        {showPanel ? (
          <div className="flex-1 bg-white dark:bg-[#252528] rounded-lg border border-slate-200 dark:border-white/5 shadow-sm flex flex-col overflow-hidden animate-in fade-in slide-in-from-right-4 duration-300">
            <div className="px-3 py-2 border-b border-slate-100/80 dark:border-white/5 flex items-center justify-between shrink-0 bg-slate-50/50 dark:bg-white/[0.02]">
              <h2 className="text-base font-bold text-slate-900 dark:text-white">
                {isCreating ? 'Nuevo Faro' : MODE_CONFIG[mode].title}
              </h2>
              <div className="flex items-center gap-1">
                {!isCreating && selectedHouse && (
                  <button
                    onClick={() => router.push(`/plataforma/evangelism/faro/sessions/${selectedHouse.id}`)}
                    className="size-8 rounded-lg bg-green-50 dark:bg-green-500/10 flex items-center justify-center text-green-600 dark:text-green-400 hover:bg-green-100 dark:hover:bg-green-500/20 transition-colors"
                    title="Reportar sesión"
                  >
                    <Calendar size={15} />
                  </button>
                )}
                {!isCreating && selectedHouse && (
                  <button
                    onClick={() => handleDeleteHouse(selectedHouse)}
                    className="size-8 rounded-lg bg-red-50 dark:bg-red-500/10 flex items-center justify-center text-red-500 hover:bg-red-100 dark:hover:bg-red-500/20 transition-colors"
                    title="Eliminar grupo"
                  >
                    <Trash2 size={15} />
                  </button>
                )}
                <button
                  onClick={() => {
                    setIsCreating(false);
                    setSelectedHouse(null);
                  }}
                  className="size-8 rounded-lg bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-500 hover:text-slate-900 dark:hover:text-white transition-colors"
                >
                  <X size={15} />
                </button>
              </div>
            </div>

            {selectedHouse || isCreating ? (
              <>
              <div className="flex-1 overflow-y-auto px-3 py-2 scrollbar-thin">
                {!isCreating && (
                <div className="mb-5 rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 px-4 py-1.5 flex items-start justify-between gap-4">
                  <div>
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                      {MODE_CONFIG[mode].title}
                    </p>
                    <p className="text-sm font-medium text-slate-600 dark:text-slate-300 mt-1">
                      {MODE_CONFIG[mode].description}
                    </p>
                  </div>
                  <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                    Edición
                  </span>
                </div>
              )}
              <form
                id="faro-form"
                onSubmit={handleSave}
                className="space-y-4 w-full"
              >
                {/* Identidad */}
                <div className="space-y-4">
                  <div>
                    <label className="block text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-2">
                      Código del Faro
                    </label>
                    <input
                      value={formData.code || ''}
                      onChange={e =>
                        setFormData({
                          ...formData,
                          code: e.target.value,
                        } as Partial<GloryHouse>)
                      }
                      className={inputCls}
                      placeholder="FARO-001 o dejar vacío"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-2">
                      Nombre o Número del Grupo
                    </label>
                    <input
                      value={formData.name || ''}
                      onChange={e =>
                        setFormData({ ...formData, name: e.target.value })
                      }
                      className={inputCls}
                      placeholder="Ej. Casa Bethel, Grupo 12 o dejar pendiente"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-2 flex items-center gap-1">
                        <MapPin size={11} /> Zona/Barrio
                      </label>
                      <input
                        value={formData.zone || ''}
                        onChange={e =>
                          setFormData({ ...formData, zone: e.target.value })
                        }
                        className={inputCls}
                        placeholder="Norte, Centro..."
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-2 flex items-center gap-1">
                        <MapPin size={11} /> Dirección
                      </label>
                      <input
                        value={formData.address || ''}
                        onChange={e =>
                          setFormData({ ...formData, address: e.target.value })
                        }
                        className={inputCls}
                        placeholder="Calle, número..."
                      />
                    </div>
                  </div>
                </div>

                {/* Roles */}
                <div>
                  <h3 className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-4 flex items-center gap-2">
                    <Users size={12} className="text-blue-500" /> Roles del
                    Grupo
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {[
                      { key: 'leader_id', label: 'Líder' },
                      { key: 'assistant_id', label: 'Asistente de Líder' },
                      { key: 'host_id', label: 'Anfitrión' },
                    ].map(({ key, label }) => (
                      <div key={key}>
                        <label className="block text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-2">
                          {label}
                        </label>
                        <select
                          value={
                            formData[
                              key as 'leader_id' | 'assistant_id' | 'host_id'
                            ] ?? ''
                          }
                          onChange={e =>
                            setFormData({
                              ...formData,
                              [key]: e.target.value
                                ? Number(e.target.value)
                                : undefined,
                            })
                          }
                          className={inputCls}
                        >
                          <option value="">Seleccionar...</option>
                          {members.map(m => (
                            <option key={m.id} value={m.id}>
                              {m.first_name} {m.last_name}
                            </option>
                          ))}
                        </select>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Logística */}
                <div>
                  <h3 className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-4 flex items-center gap-2">
                    <Calendar size={12} className="text-blue-500" /> Logística
                  </h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="col-span-2">
                      <label className="block text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-2 flex items-center gap-1">
                        <Clock size={11} /> Día de Reunión
                      </label>
                      <select
                        value={formData.day_of_week || ''}
                        onChange={e =>
                          setFormData({
                            ...formData,
                            day_of_week: e.target.value,
                          })
                        }
                        className={inputCls}
                      >
                        <option value="">Seleccionar...</option>
                        {[
                          'Lunes',
                          'Martes',
                          'Miércoles',
                          'Jueves',
                          'Viernes',
                          'Sábado',
                          'Domingo',
                        ].map(d => (
                          <option key={d} value={d}>
                            {d}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-2">
                        Hora Inicio
                      </label>
                      <input
                        type="time"
                        value={formData.start_time || ''}
                        onChange={e =>
                          setFormData({
                            ...formData,
                            start_time: e.target.value,
                          })
                        }
                        className={inputCls}
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-2">
                        Hora Fin
                      </label>
                      <input
                        type="time"
                        value={formData.end_time || ''}
                        onChange={e =>
                          setFormData({ ...formData, end_time: e.target.value })
                        }
                        className={inputCls}
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-2">
                        Capacidad
                      </label>
                      <input
                        type="number"
                        value={formData.capacity || ''}
                        onChange={e =>
                          setFormData({
                            ...formData,
                            capacity: Number(e.target.value),
                          })
                        }
                        className={inputCls}
                      />
                    </div>
                  </div>
                </div>

                {selectedHouse && (
                  <div className="space-y-4">
                    <div className="flex flex-col xl:flex-row xl:items-start justify-between gap-4 border-t border-slate-100 dark:border-white/5 pt-8 mt-4">
                      <div>
                        <h3 className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1 flex items-center gap-2">
                          <Users size={12} className="text-blue-500" /> Miembros actuales ({selectedMemberIds.size})
                        </h3>
                        <p className="text-xs text-slate-500">
                          Estos son los miembros actualmente asignados al Faro.
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => setIsAddingMembers(!isAddingMembers)}
                        className={`px-4 py-2 text-[11px] font-semibold uppercase tracking-wide rounded-lg transition-colors flex items-center gap-2 ${
                          isAddingMembers 
                            ? 'bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-white/10 dark:text-white dark:hover:bg-white/20' 
                            : 'bg-blue-50 text-blue-600 hover:bg-blue-100 dark:bg-blue-500/10 dark:text-blue-400'
                        }`}
                      >
                        <UserPlus size={14} /> {isAddingMembers ? 'Ocultar catálogo' : 'Añadir miembros'}
                      </button>
                    </div>

                    {/* CURRENT MEMBERS LIST */}
                    {selectedMemberIds.size > 0 ? (
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                        {members.filter(m => selectedMemberIds.has(m.id)).map(member => (
                          <div key={member.id} className="flex items-center justify-between gap-3 rounded-lg border border-blue-200 dark:border-blue-500/30 bg-blue-50/50 dark:bg-blue-900/10 px-4 py-1.5">
                            <div className="min-w-0">
                              <p className="text-sm font-bold text-slate-900 dark:text-white truncate">
                                {member.first_name} {member.last_name}
                              </p>
                              <p className="text-[10px] text-slate-400 mt-0.5 truncate">
                                {member.church_role || 'Sin rol'}
                              </p>
                            </div>
                            <button
                              type="button"
                              onClick={() => setSelectedMemberIds(prev => {
                                const next = new Set(prev);
                                next.delete(member.id);
                                return next;
                              })}
                              className="text-slate-400 hover:text-rose-500 transition-colors shrink-0"
                              title="Remover del Faro"
                            >
                              <X size={16} />
                            </button>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="py-2 text-center border-2 border-dashed border-slate-200 dark:border-white/10 rounded-lg">
                        <p className="text-sm text-slate-400 font-medium">No hay miembros asignados a este Faro.</p>
                      </div>
                    )}

                    {/* QUICK ACTION TO ATTENDANCE PANEL */}
                    <div className="mt-3 pt-6 border-t border-slate-100 dark:border-white/5 flex items-center justify-between bg-blue-50/50 dark:bg-blue-900/10 rounded-lg px-4 py-2">
                      <div>
                        <h3 className="text-sm font-semibold text-blue-900 dark:text-blue-100 mb-1">Registrar Asistencia Semanal</h3>
                        <p className="text-xs font-medium text-blue-700/70 dark:text-blue-300/70">
                          Ir al panel dedicado para registrar la asistencia, ofrendas y novedades de las reuniones semanales de este grupo.
                        </p>
                      </div>
                      <a
                        href={`/evangelism/faro/${selectedHouse.id}`}
                        className="px-3 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-xs font-semibold uppercase tracking-wide transition-all shadow-lg shadow-blue-500/30 flex items-center gap-2 shrink-0"
                      >
                        <Calendar size={14} /> Registrar Asistencia
                      </a>
                    </div>

                    {/* ADD MEMBERS CATALOG */}
                    {isAddingMembers && (
                      <div className="mt-3 pt-6 border-t border-slate-100 dark:border-white/5 space-y-4">
                        <div className="flex flex-col md:flex-row items-center gap-2 w-full">
                          <div className="relative w-full md:flex-1">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={14} />
                            <input
                              value={memberSearchQuery}
                              onChange={e => setMemberSearchQuery(e.target.value)}
                              placeholder="Buscar miembro..."
                              className={inputCls + " pl-9 py-2"}
                            />
                          </div>
                          <select
                            value={memberRoleFilter}
                            onChange={e => setMemberRoleFilter(e.target.value)}
                            className={inputCls + " py-2 w-full md:w-36 text-xs"}
                          >
                            <option value="">Todos los roles</option>
                            {uniqueRoles.map(r => (
                              <option key={r as string} value={r as string}>{r}</option>
                            ))}
                          </select>
                          <select
                            value={memberAssignmentFilter}
                            onChange={e => setMemberAssignmentFilter(e.target.value)}
                            className={inputCls + " py-2 w-full md:w-48 text-xs"}
                          >
                            <option value="all">Cualquier estado</option>
                            <option value="unassigned">Sin faro asignado</option>
                            <option value="other_house">En otra casa</option>
                          </select>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 max-h-[24rem] overflow-y-auto pr-1 scrollbar-thin">
                          {filteredMembersList.map(member => {
                            const checked = selectedMemberIds.has(member.id);
                            // Hide already selected members from the add list to prevent confusion
                            if (checked) return null;
                            
                            return (
                              <label
                                key={member.id}
                                className="flex items-start gap-3 rounded-lg border px-4 py-1.5 cursor-pointer transition-all bg-white dark:bg-white/5 border-slate-200 dark:border-white/10 hover:border-blue-300/40"
                              >
                                <input
                                  type="checkbox"
                                  checked={checked}
                                  onChange={() =>
                                    setSelectedMemberIds(prev => {
                                      const next = new Set(prev);
                                      if (next.has(member.id))
                                        next.delete(member.id);
                                      else next.add(member.id);
                                      return next;
                                    })
                                  }
                                  className="mt-1 size-4 accent-blue-600 shrink-0"
                                />
                                <div className="min-w-0">
                                  <p className="text-sm font-bold text-slate-900 dark:text-white truncate">
                                    {member.first_name} {member.last_name}
                                  </p>
                                  <p className="text-[10px] text-slate-400 mt-0.5 truncate">
                                    {member.church_role || 'Sin rol'}
                                  </p>
                                </div>
                              </label>
                            );
                          })}
                          {filteredMembersList.filter(m => !selectedMemberIds.has(m.id)).length === 0 && (
                              <div className="col-span-full py-1.5 text-center text-slate-400 text-sm">
                                No se encontraron miembros disponibles con estos filtros.
                              </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </form>
            </div>

            <div className="px-3 py-2 border-t border-slate-100 dark:border-white/5 shrink-0 flex justify-end gap-2">
              <button
                onClick={() => {
                  setIsCreating(false);
                  setSelectedHouse(null);
                }}
                className="px-4 py-2 rounded-lg text-xs font-semibold uppercase tracking-wide text-slate-500 hover:bg-slate-100 dark:hover:bg-white/5 transition-colors"
              >
                Cancelar
              </button>
              <button
                type="submit"
                form="faro-form"
                disabled={saving}
                className="px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold uppercase tracking-wide transition-all shadow-lg shadow-blue-500/20 active:scale-95 disabled:opacity-50 flex items-center gap-2"
              >
                {saving ? (
                  <Activity className="animate-spin" size={13} />
                ) : (
                  <CheckCircle2 size={13} />
                )}
                Guardar Grupo
              </button>
            </div>
            </>
        ) : (
          <div className="flex-1 overflow-y-auto bg-white dark:bg-[#1e1f21]">
            {mode === 'members' && summary ? (
              <div className="p-4 space-y-3">
                <div className="rounded-lg border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 px-4 py-1.5">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                    Asignación rápida
                  </p>
                  <p className="text-sm font-medium text-slate-600 dark:text-slate-300 mt-1">
                    Asigna miembros sin faro a una casa específica sin salir de
                    esta vista.
                  </p>
                </div>

                <div className="space-y-3">
                  {summary.unassigned_members.length === 0 ? (
                    <div className="rounded-lg border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 px-4 py-1.5 text-center text-slate-400">
                      No hay miembros sin faro asignado.
                    </div>
                  ) : (
                    summary.unassigned_members.map(member => (
                      <div
                        key={member.id}
                        className="rounded-lg border border-slate-200 dark:border-white/10 bg-white dark:bg-white/5 p-4"
                      >
                        <div className="flex flex-col md:flex-row md:items-center gap-3">
                          <div className="min-w-0 flex-1">
                            <p className="text-sm font-bold text-slate-900 dark:text-white truncate">
                              {member.name}
                            </p>
                            <p className="text-[10px] text-slate-400 mt-1">
                              {member.church_role || 'Sin rol'} · Sin faro
                              asignado
                            </p>
                          </div>
                          <select
                            value={quickAssignmentTargets[member.id] || ''}
                            onChange={e =>
                              setQuickAssignmentTargets(prev => ({
                                ...prev,
                                [member.id]: Number(e.target.value),
                              }))
                            }
                            className="w-full md:w-72 bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-md px-3 py-2 text-xs font-medium outline-none focus:ring-2 focus:ring-blue-500/30"
                          >
                            <option value="">Selecciona una casa</option>
                            {houses.map(h => (
                              <option key={h.id} value={h.id}>
                                {h.name} {h.code ? `· ${h.code}` : ''}
                              </option>
                            ))}
                          </select>
                          <button
                            onClick={() => handleQuickAssignMember(member.id)}
                            disabled={saving}
                            className="px-4 py-2.5 rounded-md bg-blue-600 hover:bg-blue-700 text-white text-[11px] font-semibold uppercase tracking-wide disabled:opacity-50"
                          >
                            Asignar
                          </button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            ) : (
              <div className="flex-1 flex items-center justify-center text-slate-300 dark:text-white/20 h-full">
                <div className="text-center">
                  <Home size={40} className="mx-auto mb-3 opacity-40" />
                  <p className="text-sm font-bold">
                    Selecciona un grupo o crea uno nuevo
                  </p>
                </div>
              </div>
            )}
              </div>
            )}
          </div>
        ) : (
          <div className="flex-1 bg-white/50 dark:bg-[#252528]/50 rounded-lg border border-dashed border-slate-200 dark:border-white/10 flex flex-col items-center justify-center animate-in fade-in duration-500 shadow-sm">
            <div className="size-8 rounded-md bg-slate-100 dark:bg-white/5 flex items-center justify-center mb-3 shadow-inner">
              <Home size={32} className="text-slate-400" />
            </div>
            <h2 className="text-base font-bold text-slate-800 dark:text-white tracking-tight mb-2">Espacio de Trabajo Faro</h2>
            <p className="text-sm text-slate-500 font-medium max-w-sm text-center">
              Selecciona un grupo en el menú izquierdo para ver sus detalles, o crea uno nuevo para comenzar a gestionar tu equipo.
            </p>
          </div>
        )}
      </div>
    </EvangelismShell>
  );
}

export default function FaroGroupsPage() {
  return (
    <Suspense
      fallback={
        <div className="p-4 text-center text-slate-500">Cargando grupos...</div>
      }
    >
      <FaroGroupsContent />
    </Suspense>
  );
}
