'use client';

import React, { useState, Suspense, useEffect, useMemo, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';

import { apiFetch } from '@/lib/http';
import { useSidebarLayers } from '@/context/SidebarLayerContext';
import EvangelismShell from '@/components/evangelism/EvangelismShell';
import RightPanel from '@/components/ui/RightPanel';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import UniversalCalendarView from '@/components/ui/UniversalCalendarView';
import UniversalGanttView from '@/components/ui/UniversalGanttView';
import UniversalWikiView from '@/components/ui/UniversalWikiView';
import { ViewType, getStoredView } from '@/components/ViewSwitcher';
import {
  Home,
  MapPin,
  Users,
  Activity,
  X,
  CheckCircle2,
  Clock,
  UserPlus,
  BarChart3,
  Trash2,
  Filter,
  Save,
} from 'lucide-react';
import { toast } from 'react-toastify';

function parseAndValidateTime(timeStr: string): { valid: boolean; minutes: number; normalized: string } {
  if (!timeStr) return { valid: false, minutes: 0, normalized: '' };
  
  const clean = timeStr.trim().toLowerCase().replace(/\s+/g, ' ');
  
  // Handle standard 24h format HH:MM
  const match24 = clean.match(/^(\d{1,2}):(\d{2})$/);
  if (match24) {
    const h = parseInt(match24[1], 10);
    const m = parseInt(match24[2], 10);
    if (h >= 0 && h < 24 && m >= 0 && m < 60) {
      const padH = String(h).padStart(2, '0');
      const padM = String(m).padStart(2, '0');
      return { valid: true, minutes: h * 60 + m, normalized: `${padH}:${padM}` };
    }
  }
  
  // Handle formats with AM/PM
  const matchAmpm = clean.match(/^(\d{1,2}):(\d{2})\s*([ap](?:\.?,?\s*m?\.?)?)/i);
  if (matchAmpm) {
    let h = parseInt(matchAmpm[1], 10);
    const m = parseInt(matchAmpm[2], 10);
    const periodStr = matchAmpm[3];
    
    const isPm = periodStr.includes('p');
    const isAm = periodStr.includes('a');
    
    if (h >= 1 && h <= 12 && m >= 0 && m < 60 && (isAm || isPm)) {
      if (isPm && h < 12) {
        h += 12;
      } else if (isAm && h === 12) {
        h = 0;
      }
      const padH = String(h).padStart(2, '0');
      const padM = String(m).padStart(2, '0');
      return { valid: true, minutes: h * 60 + m, normalized: `${padH}:${padM}` };
    }
  }
  
  return { valid: false, minutes: 0, normalized: '' };
}

function getLocalDateForDayOfWeek(dayName: string): string {
  const days = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'];
  const targetIndex = days.indexOf(dayName);
  if (targetIndex === -1) return new Date().toISOString().split('T')[0];
  
  const today = new Date();
  const todayIndex = today.getDay();
  const diff = targetIndex - todayIndex;
  const targetDate = new Date(today);
  targetDate.setDate(today.getDate() + diff);
  return targetDate.toISOString().split('T')[0];
}

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

function FaroGroupsContent() {
  const { token } = useAuth();

  const { openLayer, closeLayer, setRightMode, layers } = useSidebarLayers();
  
  // Workspace Views State
  const [viewType, setViewType] = useState<ViewType>(() => getStoredView('evangelism_faro_groups_view', 'grid'));
  
  // Data States
  const [houses, setHouses] = useState<GloryHouse[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [summary, setSummary] = useState<AssignmentSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  
  // Filter States
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [dayFilter, setDayFilter] = useState<string>('all');
  const [zoneFilter, setZoneFilter] = useState<string>('all');
  
  // Detail Panel / Editing States
  const [selectedHouse, setSelectedHouse] = useState<GloryHouse | null>(null);
  const [activeDetailTab, setActiveDetailTab] = useState<'general' | 'roles' | 'members'>('general');
  const [formData, setFormData] = useState<Partial<GloryHouse>>({});
  const [selectedMemberIds, setSelectedMemberIds] = useState<Set<number>>(new Set());
  const [isAddingMembers, setIsAddingMembers] = useState(false);
  
  // Member Catalog Search inside Detail Tab
  const [memberSearchQuery, setMemberSearchQuery] = useState('');
  const [memberRoleFilter] = useState('');
  const [memberAssignmentFilter, setMemberAssignmentFilter] = useState('all');
  
  // Creation Drawer State
  const [isCreateDrawerOpen, setIsCreateDrawerOpen] = useState(false);
  const [newFaroData, setNewFaroData] = useState<Partial<GloryHouse>>({
    capacity: 15,
    status: 'Activo',
  });
  
  // Kanban Drag and Drop Visual Highlight State
  const [draggedOverCol, setDraggedOverCol] = useState<string | null>(null);
  const [quickAssignmentTargets, setQuickAssignmentTargets] = useState<Record<number, number>>({});

  // Synchronize viewType storage
  const handleViewChange = (newView: ViewType) => {
    setViewType(newView);
    if (typeof window !== 'undefined') {
      window.localStorage.setItem('evangelism_faro_groups_view', newView);
    }
  };

  // Fetch initial data
  const fetchData = useCallback(() => {
    if (!token) return;
    setLoading(true);
    Promise.all([
      apiFetch<GloryHouse[]>('/evangelism/glory-houses', { token }),
      apiFetch<Member[]>('/crm/members/', { token }),
      apiFetch<AssignmentSummary>('/evangelism/faro/assignment-summary', { token }).catch(() => null),
    ])
      .then(([housesData, membersData, summaryData]) => {
        setHouses(housesData);
        setMembers(membersData);
        setSummary(summaryData);
      })
      .catch(() => toast.error('Error al cargar datos'))
      .finally(() => setLoading(false));
  }, [token]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Synchronize RIGHT panel open state with selected house or general stats
  useEffect(() => {
    if (token) {
      setRightMode('push');
      openLayer('RIGHT');
    }
  }, [selectedHouse, token, setRightMode, openLayer]);

  // Handle closing RIGHT panel (clean up selected house)
  useEffect(() => {
    if (layers && !layers.RIGHT && selectedHouse) {
      setSelectedHouse(null);
    }
  }, [layers, selectedHouse]);

  // Member Name helper
  const getMemberName = useCallback((id?: number) => {
    if (!id) return 'No asignado';
    const m = members.find(m => m.id === id);
    return m ? `${m.first_name} ${m.last_name}` : 'Desconocido';
  }, [members]);

  // Extract unique Zones/Barrios
  const uniqueZones = useMemo(() => {
    return Array.from(new Set(houses.map(h => h.zone).filter(Boolean))).sort() as string[];
  }, [houses]);



  // Filtered Faro groups list
  const filteredHouses = useMemo(() => {
    return houses.filter(h => {
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const leaderName = getMemberName(h.leader_id).toLowerCase();
        const assistantName = getMemberName(h.assistant_id).toLowerCase();
        const hostName = getMemberName(h.host_id).toLowerCase();
        const matches =
          h.name.toLowerCase().includes(q) ||
          h.zone?.toLowerCase().includes(q) ||
          h.code?.toLowerCase().includes(q) ||
          leaderName.includes(q) ||
          assistantName.includes(q) ||
          hostName.includes(q);
        if (!matches) return false;
      }
      if (statusFilter !== 'all' && h.status !== statusFilter) return false;
      if (dayFilter !== 'all' && h.day_of_week !== dayFilter) return false;
      if (zoneFilter !== 'all' && h.zone !== zoneFilter) return false;
      return true;
    });
  }, [houses, searchQuery, statusFilter, dayFilter, zoneFilter, getMemberName]);

  // Filtered members list for detail catalog
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

  // Detail panel triggers
  const handleSelectHouse = async (house: GloryHouse) => {
    setSelectedHouse(house);
    setActiveDetailTab('general');
    setIsAddingMembers(false);
    setFormData(house);
    setSelectedMemberIds(new Set(house.base_attendee_ids || house.base_attendees?.map(m => m.member_id) || []));
    setRightMode('push');
    openLayer('RIGHT');
  };

  // Creation Drawer submission
  const handleCreateFaro = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      let start_time = newFaroData.start_time || '';
      let end_time = newFaroData.end_time || '';

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
        ...newFaroData,
        start_time: start_time || null,
        end_time: end_time || null,
        base_attendee_ids: [],
      };

      const res = await apiFetch<GloryHouse>('/evangelism/glory-houses', {
        method: 'POST',
        body: payload,
        token,
      });

      setHouses([res, ...houses]);
      setIsCreateDrawerOpen(false);
      setNewFaroData({ capacity: 15, status: 'Activo' });
      toast.success('Grupo Faro creado con éxito');
      
      // Auto-select the newly created Faro
      handleSelectHouse(res);
      
      // Refresh summary
      apiFetch<AssignmentSummary>('/evangelism/faro/assignment-summary', { token })
        .then(setSummary)
        .catch(() => null);
    } catch (error: any) {
      toast.error(error?.message || 'Error al crear el grupo');
    } finally {
      setSaving(false);
    }
  };

  // Update Detail Form submission
  const handleUpdateFaro = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedHouse) return;
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

      const res = await apiFetch<GloryHouse>(`/evangelism/glory-houses/${selectedHouse.id}`, {
        method: 'PUT',
        body: payload,
        token,
      });

      setHouses(houses.map(h => (h.id === res.id ? res : h)));
      setSelectedHouse(res);
      setFormData(res);
      toast.success('Grupo Faro actualizado con éxito');

      // Refresh summary
      apiFetch<AssignmentSummary>('/evangelism/faro/assignment-summary', { token })
        .then(setSummary)
        .catch(() => null);
    } catch (error: any) {
      toast.error(error?.message || 'Error al actualizar el grupo');
    } finally {
      setSaving(false);
    }
  };

  // Delete Faro group
  const handleDeleteFaro = async (id: number) => {
    if (!window.confirm('¿Está seguro de que desea eliminar este grupo Faro? Esta acción es irreversible.')) return;
    setSaving(true);
    try {
      await apiFetch(`/evangelism/glory-houses/${id}`, {
        method: 'DELETE',
        token,
      });
      setHouses(houses.filter(h => h.id !== id));
      setSelectedHouse(null);
      closeLayer('RIGHT');
      toast.success('Grupo Faro eliminado con éxito');

      // Refresh summary
      apiFetch<AssignmentSummary>('/evangelism/faro/assignment-summary', { token })
        .then(setSummary)
        .catch(() => null);
    } catch {
      toast.error('Error al eliminar el grupo Faro');
    } finally {
      setSaving(false);
    }
  };

  // Quick assign member to a house (from the Filters/Stats panel)
  const handleQuickAssignMember = async (memberId: number) => {
    const houseId = quickAssignmentTargets[memberId];
    if (!houseId) {
      toast.error('Por favor, selecciona un Faro');
      return;
    }
    setSaving(true);
    try {
      const detail = await apiFetch<GloryHouse>(`/evangelism/glory-houses/${houseId}`, { token });
      const current = new Set(detail.base_attendee_ids || detail.base_attendees?.map(m => m.member_id) || []);
      current.add(memberId);
      
      const updated = await apiFetch<GloryHouse>(`/evangelism/glory-houses/${houseId}`, {
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
      });

      setHouses(prev => prev.map(h => (h.id === updated.id ? updated : h)));
      const refreshed = await apiFetch<AssignmentSummary>('/evangelism/faro/assignment-summary', { token });
      setSummary(refreshed);
      setQuickAssignmentTargets(prev => {
        const next = { ...prev };
        delete next[memberId];
        return next;
      });
      toast.success('Miembro asignado con éxito');
    } catch {
      toast.error('Error al asignar miembro');
    } finally {
      setSaving(false);
    }
  };

  // HTML5 Drag and Drop for Board / Kanban View
  const handleDragStart = (e: React.DragEvent, id: number) => {
    e.dataTransfer.setData('text/plain', id.toString());
  };

  const handleDragOver = (e: React.DragEvent, colStatus: string) => {
    e.preventDefault();
    setDraggedOverCol(colStatus);
  };

  const handleDragLeave = () => {
    setDraggedOverCol(null);
  };

  const handleDrop = async (e: React.DragEvent, newStatus: string) => {
    e.preventDefault();
    setDraggedOverCol(null);
    const idStr = e.dataTransfer.getData('text/plain');
    if (!idStr) return;
    const houseId = Number(idStr);
    
    const house = houses.find(h => h.id === houseId);
    if (!house) return;
    if (house.status === newStatus) return;

    // Optimistically update
    setHouses(prev => prev.map(h => (h.id === houseId ? { ...h, status: newStatus } : h)));

    try {
      const updated = await apiFetch<GloryHouse>(`/evangelism/glory-houses/${houseId}`, {
        method: 'PUT',
        token,
        body: {
          code: house.code,
          name: house.name,
          zone: house.zone,
          address: house.address,
          leader_id: house.leader_id,
          assistant_id: house.assistant_id,
          host_id: house.host_id,
          capacity: house.capacity,
          day_of_week: house.day_of_week,
          start_time: house.start_time,
          end_time: house.end_time,
          status: newStatus,
          base_attendee_ids: house.base_attendee_ids || house.base_attendees?.map(m => m.member_id) || [],
        },
      });
      setHouses(prev => prev.map(h => (h.id === updated.id ? updated : h)));
      toast.success(`Faro "${house.name}" movido a ${newStatus}`);
    } catch {
      // Revert status
      setHouses(prev => prev.map(h => (h.id === houseId ? { ...h, status: house.status } : h)));
      toast.error('Error al actualizar el estado en el servidor');
    }
  };

  // Calendar Event Format Mapping
  const calendarEvents = useMemo(() => {
    return filteredHouses.map(h => {
      const date = h.day_of_week ? getLocalDateForDayOfWeek(h.day_of_week) : new Date().toISOString().split('T')[0];
      return {
        id: h.id.toString(),
        title: `${h.name} (${h.code || 'S/C'})`,
        date,
        time: h.start_time || undefined,
        color: (h.status === 'Activo' ? 'emerald' : h.status === 'Inactivo' ? 'amber' : 'rose') as 'emerald' | 'amber' | 'rose',
      };
    });
  }, [filteredHouses]);

  const handleCalendarEventClick = (event: any) => {
    const houseId = Number(event.id);
    const house = houses.find(h => h.id === houseId);
    if (house) {
      handleSelectHouse(house);
    }
  };

  // Gantt Item Format Mapping
  const ganttItems = useMemo(() => {
    return filteredHouses.map(h => {
      const date = h.day_of_week ? getLocalDateForDayOfWeek(h.day_of_week) : new Date().toISOString().split('T')[0];
      const count = h.base_attendee_ids?.length || h.base_attendees?.length || 0;
      const progress = h.capacity > 0 ? Math.min(100, Math.round((count / h.capacity) * 100)) : 0;
      
      let color: 'blue' | 'purple' | 'emerald' | 'amber' | 'rose' | 'indigo' = 'blue';
      if (h.status === 'Activo') color = 'emerald';
      else if (h.status === 'Inactivo') color = 'amber';
      else if (h.status === 'Suspendido') color = 'rose';
      
      const leaderName = getMemberName(h.leader_id);
      
      return {
        id: h.id,
        title: h.name,
        subtitle: `Líder: ${leaderName} · ${h.day_of_week || ''} ${h.start_time || ''}`,
        start_date: date,
        end_date: date,
        progress,
        color,
      };
    });
  }, [filteredHouses, getMemberName]);

  const handleGanttItemClick = (item: any) => {
    const house = houses.find(h => h.id === item.id);
    if (house) {
      handleSelectHouse(house);
    }
  };

  // Analytics/KPI values
  const metrics = useMemo(() => {
    const totalFaros = houses.length;
    const activeFaros = houses.filter(h => h.status === 'Activo').length;
    const totalMembers = houses.reduce((acc, h) => acc + (h.base_attendee_ids?.length || h.base_attendees?.length || 0), 0);
    const totalCapacity = houses.reduce((acc, h) => acc + (h.capacity || 0), 0);
    const occupancyRate = totalCapacity > 0 ? Math.round((totalMembers / totalCapacity) * 100) : 0;
    const withoutLeader = houses.filter(h => !h.leader_id).length;
    const withoutAssistant = houses.filter(h => !h.assistant_id).length;
    const withoutHost = houses.filter(h => !h.host_id).length;

    return {
      totalFaros,
      activeFaros,
      totalMembers,
      totalCapacity,
      occupancyRate,
      withoutLeader,
      withoutAssistant,
      withoutHost,
    };
  }, [houses]);

  // CSS classes
  const inputCls =
    'w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-xl px-4 py-2 text-sm font-medium focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400 outline-none transition-all placeholder:text-slate-400 text-slate-800 dark:text-white';

  const selectCls =
    'w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-xl px-4 py-2 text-sm font-medium focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400 outline-none transition-all text-slate-800 dark:text-white';

  return (
    <EvangelismShell
      breadcrumbs={[
        { label: 'Faro en Casa', href: '/evangelism/faro', icon: Home },
        { label: 'Grupos', icon: Home },
      ]}
      viewOptions={['grid', 'table', 'kanban', 'calendar', 'gantt', 'wiki']}
      viewType={viewType}
      onViewChange={handleViewChange}
      onSearch={setSearchQuery}
      onAdd={() => setIsCreateDrawerOpen(true)}
    >
      <div className="h-full flex flex-col relative">
        {loading ? (
          <div className="p-4 space-y-4">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-20 w-full bg-slate-100 dark:bg-white/5 rounded-2xl animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="pb-16 flex-1">
            {/* ─── 1. GRID VIEW ─── */}
            {viewType === 'grid' && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {filteredHouses.map(h => {
                  const attendeesCount = h.base_attendee_ids?.length || h.base_attendees?.length || 0;
                  const occupancyPercent = h.capacity > 0 ? Math.min(100, Math.round((attendeesCount / h.capacity) * 100)) : 0;
                  const isSelected = selectedHouse?.id === h.id;

                  // Define status tag colors
                  const statusColors = {
                    Activo: 'bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-400 border-emerald-100 dark:border-emerald-500/20',
                    Inactivo: 'bg-amber-50 text-amber-600 dark:bg-amber-500/10 dark:text-amber-400 border-amber-100 dark:border-amber-500/20',
                    Suspendido: 'bg-rose-50 text-rose-600 dark:bg-rose-500/10 dark:text-rose-400 border-rose-100 dark:border-rose-500/20',
                  }[h.status] || 'bg-slate-50 text-slate-600';

                  return (
                    <div
                      key={h.id}
                      onClick={() => handleSelectHouse(h)}
                      className={`group relative bg-white dark:bg-[#1e1f21] rounded-2xl border p-5 shadow-sm hover:shadow-xl dark:hover:shadow-black/20 hover:-translate-y-0.5 cursor-pointer transition-all duration-300 flex flex-col justify-between min-h-[180px] ${
                        isSelected ? 'border-blue-500 ring-2 ring-blue-500/10' : 'border-slate-200/80 dark:border-white/5'
                      }`}
                    >
                      <div>
                        {/* Title and status */}
                        <div className="flex items-start justify-between gap-4">
                          <div>
                            <span className="text-[10px] font-black tracking-widest text-slate-400 uppercase">
                              {h.code || 'S/C'}
                            </span>
                            <h3 className="text-sm font-black text-slate-900 dark:text-white mt-0.5 group-hover:text-blue-600 transition-colors">
                              {h.name}
                            </h3>
                          </div>
                          <span className={`px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-wider border ${statusColors}`}>
                            {h.status}
                          </span>
                        </div>

                        {/* Leader & logistics */}
                        <div className="mt-3 space-y-1.5 text-xs text-slate-500 dark:text-slate-400 font-medium">
                          <p className="flex items-center gap-1.5 truncate">
                            <Users size={13} className="text-slate-400" />
                            Líder: <span className="font-bold text-slate-700 dark:text-slate-200">{getMemberName(h.leader_id)}</span>
                          </p>
                          {(h.day_of_week || h.start_time) && (
                            <p className="flex items-center gap-1.5">
                              <Clock size={13} className="text-slate-400" />
                              Reunión: <span className="font-bold text-slate-700 dark:text-slate-200">{h.day_of_week || 'Sin día'} {h.start_time ? `a las ${h.start_time}` : ''}</span>
                            </p>
                          )}
                          {h.zone && (
                            <p className="flex items-center gap-1.5 truncate">
                              <MapPin size={13} className="text-slate-400" />
                              Zona: <span className="text-slate-700 dark:text-slate-200">{h.zone}</span>
                            </p>
                          )}
                        </div>
                      </div>

                      {/* Progress occupancy bar */}
                      <div className="mt-4 pt-3 border-t border-slate-100 dark:border-white/5">
                        <div className="flex items-center justify-between text-[10px] font-black uppercase tracking-widest text-slate-400 mb-1.5">
                          <span>Miembros ({attendeesCount} / {h.capacity})</span>
                          <span>{occupancyPercent}%</span>
                        </div>
                        <div className="h-2 w-full bg-slate-100 dark:bg-white/5 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all duration-500 ${
                              occupancyPercent > 80 ? 'bg-amber-500' : 'bg-blue-600 dark:bg-blue-500'
                            }`}
                            style={{ width: `${occupancyPercent}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  );
                })}
                {filteredHouses.length === 0 && (
                  <div className="col-span-full py-16 text-center text-slate-400 bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/5 rounded-2xl">
                    No se encontraron grupos Faro.
                  </div>
                )}
              </div>
            )}

            {/* ─── 2. TABLE VIEW ─── */}
            {viewType === 'table' && (
              <div className="overflow-x-auto border border-slate-200 dark:border-white/[0.06] rounded-2xl bg-white dark:bg-[#1e1f21] shadow-sm">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-slate-100 dark:border-white/5 bg-slate-50/50 dark:bg-black/10">
                      <th className="px-6 py-4 text-[10px] font-black uppercase tracking-[0.15em] text-slate-400 w-24">Código</th>
                      <th className="px-6 py-4 text-[10px] font-black uppercase tracking-[0.15em] text-slate-400">Nombre</th>
                      <th className="px-6 py-4 text-[10px] font-black uppercase tracking-[0.15em] text-slate-400 w-32">Zona</th>
                      <th className="px-6 py-4 text-[10px] font-black uppercase tracking-[0.15em] text-slate-400">Líder</th>
                      <th className="px-6 py-4 text-[10px] font-black uppercase tracking-[0.15em] text-slate-400 w-44">Horario</th>
                      <th className="px-6 py-4 text-[10px] font-black uppercase tracking-[0.15em] text-slate-400 w-36">Ocupación</th>
                      <th className="px-6 py-4 text-[10px] font-black uppercase tracking-[0.15em] text-slate-400 w-28">Estado</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-white/[0.04]">
                    {filteredHouses.map(h => {
                      const count = h.base_attendee_ids?.length || h.base_attendees?.length || 0;
                      const occupancy = h.capacity > 0 ? Math.min(100, Math.round((count / h.capacity) * 100)) : 0;
                      const isSelected = selectedHouse?.id === h.id;

                      const statusColors = {
                        Activo: 'bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-400',
                        Inactivo: 'bg-amber-50 text-amber-600 dark:bg-amber-500/10 dark:text-amber-400',
                        Suspendido: 'bg-rose-50 text-rose-600 dark:bg-rose-500/10 dark:text-rose-400',
                      }[h.status] || 'bg-slate-50 text-slate-600';

                      return (
                        <tr
                          key={h.id}
                          onClick={() => handleSelectHouse(h)}
                          className={`hover:bg-slate-50/50 dark:hover:bg-white/[0.02] cursor-pointer group transition-colors ${
                            isSelected ? 'bg-blue-50/30 dark:bg-blue-900/10' : ''
                          }`}
                        >
                          <td className="px-6 py-4 text-[12px] font-black text-slate-400 dark:text-slate-500">
                            {h.code || '—'}
                          </td>
                          <td className="px-6 py-4 text-[13px] font-bold text-slate-900 dark:text-white group-hover:text-blue-600 transition-colors">
                            {h.name}
                          </td>
                          <td className="px-6 py-4 text-[12px] font-semibold text-slate-600 dark:text-slate-300">
                            {h.zone || '—'}
                          </td>
                          <td className="px-6 py-4 text-[12px] font-bold text-slate-700 dark:text-slate-200">
                            {getMemberName(h.leader_id)}
                          </td>
                          <td className="px-6 py-4 text-[12px] text-slate-500 dark:text-slate-400 font-medium">
                            {h.day_of_week ? `${h.day_of_week} ${h.start_time || ''}` : '—'}
                          </td>
                          <td className="px-6 py-4">
                            <div className="flex items-center gap-2">
                              <span className="text-[11px] font-bold text-slate-500 min-w-[32px]">{count}/{h.capacity}</span>
                              <div className="h-1.5 w-16 bg-slate-100 dark:bg-white/5 rounded-full overflow-hidden shrink-0">
                                <div
                                  className="h-full bg-blue-600 dark:bg-blue-500 rounded-full"
                                  style={{ width: `${occupancy}%` }}
                                />
                              </div>
                            </div>
                          </td>
                          <td className="px-6 py-4">
                            <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${statusColors}`}>
                              {h.status}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                    {filteredHouses.length === 0 && (
                      <tr>
                        <td colSpan={7} className="py-16 text-center text-slate-400 text-sm">
                          No se encontraron grupos Faro.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}

            {/* ─── 3. KANBAN / BOARD VIEW ─── */}
            {viewType === 'kanban' && (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-full min-h-[600px] items-start">
                {(['Activo', 'Inactivo', 'Suspendido'] as const).map(colStatus => {
                  const colItems = filteredHouses.filter(h => h.status === colStatus);
                  const isDraggedOver = draggedOverCol === colStatus;

                  const columnColors = {
                    Activo: 'bg-emerald-500',
                    Inactivo: 'bg-amber-500',
                    Suspendido: 'bg-rose-500',
                  }[colStatus];

                  return (
                    <div
                      key={colStatus}
                      onDragOver={(e) => handleDragOver(e, colStatus)}
                      onDragLeave={handleDragLeave}
                      onDrop={(e) => handleDrop(e, colStatus)}
                      className={`rounded-3xl p-4 flex flex-col max-h-[80vh] transition-all ${
                        isDraggedOver
                          ? 'border-2 border-dashed border-blue-500 bg-blue-50/20 dark:bg-blue-500/10'
                          : 'bg-slate-50/50 dark:bg-white/[0.02] border border-slate-100 dark:border-white/5'
                      }`}
                    >
                      <header className="flex items-center justify-between mb-4 px-2 shrink-0">
                        <div className="flex items-center gap-2">
                          <span className={`size-2.5 rounded-full ${columnColors}`} />
                          <h3 className="text-[11px] font-black uppercase tracking-[0.15em] text-slate-800 dark:text-slate-200">
                            {colStatus}
                          </h3>
                        </div>
                        <span className="text-[10px] font-black bg-slate-200/50 dark:bg-white/5 px-2 py-0.5 rounded-md text-slate-500">
                          {colItems.length}
                        </span>
                      </header>

                      <div className="space-y-4 flex-1 overflow-y-auto scrollbar-thin min-h-[200px]">
                        {colItems.map(h => {
                          const count = h.base_attendee_ids?.length || h.base_attendees?.length || 0;
                          return (
                            <div
                              key={h.id}
                              draggable
                              onDragStart={(e) => handleDragStart(e, h.id)}
                              onClick={() => handleSelectHouse(h)}
                              className="group relative bg-white dark:bg-[#1e1f21] rounded-2xl border border-slate-200/70 dark:border-white/5 p-4 shadow-sm hover:shadow-md hover:border-blue-500/30 transition-all duration-300 cursor-pointer active:scale-[0.99]"
                            >
                              <div className="flex items-start justify-between gap-4">
                                <h4 className="text-[13px] font-bold text-slate-900 dark:text-white group-hover:text-blue-600 transition-colors">
                                  {h.name}
                                </h4>
                                <span className="text-[9px] font-black text-slate-400 shrink-0">
                                  {h.code || 'S/C'}
                                </span>
                              </div>
                              <p className="text-[11px] text-slate-500 mt-2 font-medium">
                                Líder: {getMemberName(h.leader_id)}
                              </p>
                              <div className="mt-3 pt-2.5 border-t border-slate-100 dark:border-white/5 flex items-center justify-between text-[10px] text-slate-400 font-bold">
                                <span className="flex items-center gap-1"><Clock size={10} /> {h.day_of_week || 'Sin día'}</span>
                                <span>Cap: {count}/{h.capacity}</span>
                              </div>
                            </div>
                          );
                        })}

                        {colItems.length === 0 && (
                          <div className="py-12 text-center border border-dashed border-slate-200 dark:border-white/5 rounded-2xl text-[10px] font-bold uppercase tracking-widest text-slate-400">
                            Arrastre faros aquí
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* ─── 4. CALENDAR VIEW ─── */}
            {viewType === 'calendar' && (
              <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-white/5 dark:bg-[#1e1f21]">
                <UniversalCalendarView
                  events={calendarEvents}
                  title="Horarios de Reunión Faro"
                  onEventClick={handleCalendarEventClick}
                />
              </div>
            )}

            {/* ─── 5. GANTT VIEW ─── */}
            {viewType === 'gantt' && (
              <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-white/5 dark:bg-[#1e1f21]">
                <UniversalGanttView
                  items={ganttItems}
                  moduleName="Ocupación de Faro"
                  onItemClick={handleGanttItemClick}
                />
              </div>
            )}

            {/* ─── 6. WIKI VIEW ─── */}
            {viewType === 'wiki' && (
              <div className="rounded-xl overflow-hidden shadow-sm">
                <UniversalWikiView
                  moduleName="Faro en Casa"
                  storageKey="evangelism_faro_groups_wiki_notes"
                />
              </div>
            )}
          </div>
        )}
      </div>

      {/* ─── CREATION DRAWER: NUEVO FARO ─── */}
      <WorkspaceDrawer
        isOpen={isCreateDrawerOpen}
        onClose={() => setIsCreateDrawerOpen(false)}
        title="Nuevo Faro"
        subtitle="CREACIÓN DE GRUPO"
        actions={
          <>
            <button
              type="button"
              onClick={() => setIsCreateDrawerOpen(false)}
              className="px-4 py-2 rounded-lg text-xs font-black uppercase tracking-widest text-slate-500 hover:bg-slate-100 dark:hover:bg-white/5 transition-colors"
            >
              Cancelar
            </button>
            <button
              form="create-faro-form"
              type="submit"
              disabled={saving}
              className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-black uppercase tracking-widest transition-all shadow-lg shadow-blue-500/20 active:scale-95 disabled:opacity-50 flex items-center gap-2"
            >
              {saving ? <Activity className="animate-spin" size={13} /> : <CheckCircle2 size={13} />}
              Crear Faro
            </button>
          </>
        }
      >
        <form id="create-faro-form" onSubmit={handleCreateFaro} className="space-y-6">
          <div className="space-y-4">
            <div>
              <label className="block text-[10px] font-black uppercase tracking-[0.15em] text-slate-400 mb-2">
                Código del Faro
              </label>
              <input
                value={newFaroData.code || ''}
                onChange={e => setNewFaroData({ ...newFaroData, code: e.target.value })}
                className={inputCls}
                placeholder="Ej. FARO-001 (o dejar en blanco)"
              />
            </div>
            <div>
              <label className="block text-[10px] font-black uppercase tracking-[0.15em] text-slate-400 mb-2">
                Nombre del Grupo Faro *
              </label>
              <input
                required
                value={newFaroData.name || ''}
                onChange={e => setNewFaroData({ ...newFaroData, name: e.target.value })}
                className={inputCls}
                placeholder="Ej. Casa de Paz, Grupo Faro Luz"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-[10px] font-black uppercase tracking-[0.15em] text-slate-400 mb-2">
                  Zona / Barrio
                </label>
                <input
                  value={newFaroData.zone || ''}
                  onChange={e => setNewFaroData({ ...newFaroData, zone: e.target.value })}
                  className={inputCls}
                  placeholder="Ej. Norte, Centro"
                />
              </div>
              <div>
                <label className="block text-[10px] font-black uppercase tracking-[0.15em] text-slate-400 mb-2">
                  Dirección
                </label>
                <input
                  value={newFaroData.address || ''}
                  onChange={e => setNewFaroData({ ...newFaroData, address: e.target.value })}
                  className={inputCls}
                  placeholder="Ej. Calle Falsa 123"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-[10px] font-black uppercase tracking-[0.15em] text-slate-400 mb-2">
                  Día de Reunión
                </label>
                <select
                  value={newFaroData.day_of_week || ''}
                  onChange={e => setNewFaroData({ ...newFaroData, day_of_week: e.target.value })}
                  className={selectCls}
                >
                  <option value="">Seleccionar...</option>
                  {['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'].map(d => (
                    <option key={d} value={d}>{d}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-[10px] font-black uppercase tracking-[0.15em] text-slate-400 mb-2">
                  Capacidad de Integrantes
                </label>
                <input
                  type="number"
                  value={newFaroData.capacity || ''}
                  onChange={e => setNewFaroData({ ...newFaroData, capacity: Number(e.target.value) })}
                  className={inputCls}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-[10px] font-black uppercase tracking-[0.15em] text-slate-400 mb-2">
                  Hora Inicio
                </label>
                <input
                  type="time"
                  value={newFaroData.start_time || ''}
                  onChange={e => setNewFaroData({ ...newFaroData, start_time: e.target.value })}
                  className={inputCls}
                />
              </div>
              <div>
                <label className="block text-[10px] font-black uppercase tracking-[0.15em] text-slate-400 mb-2">
                  Hora Fin
                </label>
                <input
                  type="time"
                  value={newFaroData.end_time || ''}
                  onChange={e => setNewFaroData({ ...newFaroData, end_time: e.target.value })}
                  className={inputCls}
                />
              </div>
            </div>
            <div>
              <label className="block text-[10px] font-black uppercase tracking-[0.15em] text-slate-400 mb-2">
                Estado Inicial
              </label>
              <select
                value={newFaroData.status || ''}
                onChange={e => setNewFaroData({ ...newFaroData, status: e.target.value })}
                className={selectCls}
              >
                <option value="Activo">Activo</option>
                <option value="Inactivo">Inactivo</option>
                <option value="Suspendido">Suspendido</option>
              </select>
            </div>
          </div>
        </form>
      </WorkspaceDrawer>

      {/* ─── RIGHT PANEL: DETAIL/EDIT OR STATS/FILTERS ─── */}
      <RightPanel
        title={selectedHouse ? `Editar Faro: ${selectedHouse.code || ''}` : "Filtros y Métricas"}
        width={480}
      >
        {selectedHouse ? (
          /* ─── CASE A: DETAIL / EDIT FARO PANEL ─── */
          <div className="flex flex-col h-full overflow-hidden">
            {/* Action Bar */}
            <header className="px-4 py-3 border-b border-slate-100 dark:border-white/5 flex items-center justify-between bg-slate-50/50 dark:bg-black/20 shrink-0">
              <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">
                Faro #{selectedHouse.id}
              </span>
              <button
                type="button"
                onClick={() => handleDeleteFaro(selectedHouse.id)}
                className="p-1.5 hover:bg-rose-50 dark:hover:bg-rose-950/20 text-rose-500 hover:text-rose-600 rounded-lg transition-colors"
                title="Eliminar Faro"
              >
                <Trash2 size={15} />
              </button>
            </header>

            {/* Navigation Tabs */}
            <div className="px-4 border-b border-slate-100 dark:border-white/5 flex gap-4 shrink-0 bg-slate-50/20 dark:bg-black/10">
              {(['general', 'roles', 'members'] as const).map(tab => (
                <button
                  key={tab}
                  type="button"
                  onClick={() => setActiveDetailTab(tab)}
                  className={`py-3 text-[11px] font-black uppercase tracking-widest border-b-2 transition-all ${
                    activeDetailTab === tab
                      ? 'border-blue-600 text-blue-600 dark:text-blue-400'
                      : 'border-transparent text-slate-400 hover:text-slate-600'
                  }`}
                >
                  {tab === 'general' && 'Identidad'}
                  {tab === 'roles' && 'Roles'}
                  {tab === 'members' && `Miembros (${selectedMemberIds.size})`}
                </button>
              ))}
            </div>

            {/* Tab Contents */}
            <div className="flex-1 overflow-y-auto p-6 scrollbar-thin space-y-6">
              <form id="edit-faro-form" onSubmit={handleUpdateFaro} className="space-y-5">
                {activeDetailTab === 'general' && (
                  <div className="space-y-4">
                    <div>
                      <label className="block text-[10px] font-black uppercase tracking-[0.15em] text-slate-400 mb-2">
                        Código
                      </label>
                      <input
                        value={formData.code || ''}
                        onChange={e => setFormData({ ...formData, code: e.target.value })}
                        className={inputCls}
                        placeholder="FARO-001"
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] font-black uppercase tracking-[0.15em] text-slate-400 mb-2">
                        Nombre del Faro
                      </label>
                      <input
                        required
                        value={formData.name || ''}
                        onChange={e => setFormData({ ...formData, name: e.target.value })}
                        className={inputCls}
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-[10px] font-black uppercase tracking-[0.15em] text-slate-400 mb-2">
                          Zona
                        </label>
                        <input
                          value={formData.zone || ''}
                          onChange={e => setFormData({ ...formData, zone: e.target.value })}
                          className={inputCls}
                        />
                      </div>
                      <div>
                        <label className="block text-[10px] font-black uppercase tracking-[0.15em] text-slate-400 mb-2">
                          Dirección
                        </label>
                        <input
                          value={formData.address || ''}
                          onChange={e => setFormData({ ...formData, address: e.target.value })}
                          className={inputCls}
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-[10px] font-black uppercase tracking-[0.15em] text-slate-400 mb-2">
                          Día Reunión
                        </label>
                        <select
                          value={formData.day_of_week || ''}
                          onChange={e => setFormData({ ...formData, day_of_week: e.target.value })}
                          className={selectCls}
                        >
                          <option value="">Seleccionar...</option>
                          {['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'].map(d => (
                            <option key={d} value={d}>{d}</option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="block text-[10px] font-black uppercase tracking-[0.15em] text-slate-400 mb-2">
                          Capacidad
                        </label>
                        <input
                          type="number"
                          value={formData.capacity || ''}
                          onChange={e => setFormData({ ...formData, capacity: Number(e.target.value) })}
                          className={inputCls}
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-[10px] font-black uppercase tracking-[0.15em] text-slate-400 mb-2">
                          Hora Inicio
                        </label>
                        <input
                          type="time"
                          value={formData.start_time || ''}
                          onChange={e => setFormData({ ...formData, start_time: e.target.value })}
                          className={inputCls}
                        />
                      </div>
                      <div>
                        <label className="block text-[10px] font-black uppercase tracking-[0.15em] text-slate-400 mb-2">
                          Hora Fin
                        </label>
                        <input
                          type="time"
                          value={formData.end_time || ''}
                          onChange={e => setFormData({ ...formData, end_time: e.target.value })}
                          className={inputCls}
                        />
                      </div>
                    </div>
                    <div>
                      <label className="block text-[10px] font-black uppercase tracking-[0.15em] text-slate-400 mb-2">
                        Estado
                      </label>
                      <select
                        value={formData.status || ''}
                        onChange={e => setFormData({ ...formData, status: e.target.value })}
                        className={selectCls}
                      >
                        <option value="Activo">Activo</option>
                        <option value="Inactivo">Inactivo</option>
                        <option value="Suspendido">Suspendido</option>
                      </select>
                    </div>
                  </div>
                )}

                {activeDetailTab === 'roles' && (
                  <div className="space-y-4">
                    {[
                      { key: 'leader_id', label: 'Líder del Faro' },
                      { key: 'assistant_id', label: 'Colíder / Asistente' },
                      { key: 'host_id', label: 'Anfitrión / Casa' },
                    ].map(({ key, label }) => (
                      <div key={key}>
                        <label className="block text-[10px] font-black uppercase tracking-[0.15em] text-slate-400 mb-2">
                          {label}
                        </label>
                        <select
                          value={formData[key as 'leader_id' | 'assistant_id' | 'host_id'] ?? ''}
                          onChange={e =>
                            setFormData({
                              ...formData,
                              [key]: e.target.value ? Number(e.target.value) : undefined,
                            })
                          }
                          className={selectCls}
                        >
                          <option value="">Seleccionar miembro...</option>
                          {members.map(m => (
                            <option key={m.id} value={m.id}>
                              {m.first_name} {m.last_name} ({m.church_role || 'Sin Rol'})
                            </option>
                          ))}
                        </select>
                      </div>
                    ))}
                  </div>
                )}

                {activeDetailTab === 'members' && (
                  <div className="space-y-4">
                    {/* Header and Toggle Add */}
                    <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-white/5">
                      <div>
                        <h4 className="text-xs font-black text-slate-900 dark:text-white uppercase tracking-wider">
                          Asignados a este Faro
                        </h4>
                        <p className="text-[10px] text-slate-400 font-medium">Gestiona la membresía del grupo</p>
                      </div>
                      <button
                        type="button"
                        onClick={() => setIsAddingMembers(!isAddingMembers)}
                        className={`px-3 py-1.5 text-[10px] font-black uppercase tracking-widest rounded-lg transition-colors flex items-center gap-1.5 ${
                          isAddingMembers
                            ? 'bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-white/10 dark:text-white dark:hover:bg-white/20'
                            : 'bg-blue-50 text-blue-600 hover:bg-blue-100 dark:bg-blue-500/10 dark:text-blue-400'
                        }`}
                      >
                        <UserPlus size={13} /> {isAddingMembers ? 'Ocultar Catálogo' : 'Añadir Miembros'}
                      </button>
                    </div>

                    {/* Weekly Attendance CTA */}
                    <div className="bg-blue-50/50 dark:bg-blue-900/10 border border-blue-100 dark:border-blue-900/30 rounded-2xl p-4 flex flex-col gap-2">
                      <p className="text-xs font-semibold text-blue-800 dark:text-blue-300">
                        ¿Quieres registrar la asistencia semanal u ofrendas de este grupo?
                      </p>
                      <a
                        href={`/evangelism/faro/${selectedHouse.id}`}
                        className="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-[10px] font-black uppercase tracking-widest text-center transition-all shadow-md"
                      >
                        Ir a Registrar Asistencia
                      </a>
                    </div>

                    {/* Member Catalog to Add */}
                    {isAddingMembers && (
                      <div className="bg-slate-50 dark:bg-black/10 border border-slate-200/60 dark:border-white/5 rounded-2xl p-4 space-y-3">
                        <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Catálogo de Miembros</p>
                        
                        {/* Search inside catalog */}
                        <div className="flex gap-2">
                          <input
                            value={memberSearchQuery}
                            onChange={e => setMemberSearchQuery(e.target.value)}
                            placeholder="Buscar por nombre..."
                            className="flex-1 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl px-3 py-1.5 text-xs outline-none"
                          />
                          <select
                            value={memberAssignmentFilter}
                            onChange={e => setMemberAssignmentFilter(e.target.value)}
                            className="bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl px-2 py-1.5 text-xs outline-none"
                          >
                            <option value="all">Cualquiera</option>
                            <option value="unassigned">Sin faro</option>
                            <option value="other_house">En otro</option>
                          </select>
                        </div>

                        {/* List grid */}
                        <div className="grid grid-cols-1 gap-2 max-h-56 overflow-y-auto pr-1 scrollbar-thin">
                          {filteredMembersList.map(member => {
                            const checked = selectedMemberIds.has(member.id);
                            if (checked) return null; // already assigned shows in lists above
                            return (
                              <label
                                key={member.id}
                                className="flex items-center gap-2 px-3 py-2 bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 rounded-xl cursor-pointer hover:border-blue-500/20 transition-all text-xs"
                              >
                                <input
                                  type="checkbox"
                                  checked={checked}
                                  onChange={() => {
                                    setSelectedMemberIds(prev => {
                                      const next = new Set(prev);
                                      next.add(member.id);
                                      return next;
                                    });
                                  }}
                                  className="accent-blue-600 size-3.5 rounded"
                                />
                                <div className="min-w-0">
                                  <p className="font-bold truncate text-slate-800 dark:text-slate-200">{member.first_name} {member.last_name}</p>
                                  <p className="text-[9px] text-slate-400">{member.church_role || 'Sin Rol'}</p>
                                </div>
                              </label>
                            );
                          })}
                          {filteredMembersList.filter(m => !selectedMemberIds.has(m.id)).length === 0 && (
                            <p className="text-center text-[10px] text-slate-400 py-4 font-bold">No hay miembros disponibles</p>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Assigned Members list */}
                    <div className="space-y-2">
                      <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Miembros Asignados ({selectedMemberIds.size})</p>
                      <div className="grid grid-cols-1 gap-2 max-h-72 overflow-y-auto pr-1 scrollbar-thin">
                        {members.filter(m => selectedMemberIds.has(m.id)).map(member => (
                          <div
                            key={member.id}
                            className="flex items-center justify-between gap-3 bg-white dark:bg-[#1a1b1e] border border-blue-100 dark:border-blue-900/20 rounded-xl px-3 py-2"
                          >
                            <div className="min-w-0">
                              <p className="text-xs font-bold text-slate-800 dark:text-slate-100 truncate">
                                {member.first_name} {member.last_name}
                              </p>
                              <p className="text-[9px] text-slate-400">{member.church_role || 'Sin rol'}</p>
                            </div>
                            <button
                              type="button"
                              onClick={() => {
                                setSelectedMemberIds(prev => {
                                  const next = new Set(prev);
                                  next.delete(member.id);
                                  return next;
                                });
                              }}
                              className="text-slate-400 hover:text-rose-500 transition-colors p-1"
                              title="Remover"
                            >
                              <X size={14} />
                            </button>
                          </div>
                        ))}
                        {selectedMemberIds.size === 0 && (
                          <div className="py-8 text-center border-2 border-dashed border-slate-200 dark:border-white/5 rounded-xl">
                            <p className="text-xs text-slate-400">No hay miembros en este grupo Faro.</p>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </form>
            </div>

            {/* Footer buttons */}
            <footer className="px-6 py-4 border-t border-slate-100 dark:border-white/5 flex gap-4 bg-slate-50 dark:bg-transparent shrink-0">
              <button
                type="button"
                onClick={() => {
                  closeLayer('RIGHT');
                  setSelectedHouse(null);
                }}
                className="flex-1 py-2.5 bg-slate-50 dark:bg-white/5 text-slate-600 dark:text-slate-300 rounded-xl text-[10px] font-black uppercase tracking-widest hover:bg-slate-100 transition-all border border-slate-200 dark:border-white/10"
              >
                Cerrar
              </button>
              <button
                type="submit"
                form="edit-faro-form"
                disabled={saving}
                className="flex-1 py-2.5 bg-blue-600 text-white rounded-xl text-[10px] font-black uppercase tracking-widest hover:bg-blue-700 shadow-xl shadow-blue-500/20 active:scale-95 transition-all flex items-center justify-center gap-1.5 disabled:opacity-50"
              >
                <Save size={12} />
                {saving ? 'Guardando...' : 'Guardar Cambios'}
              </button>
            </footer>
          </div>
        ) : (
          /* ─── CASE B: GENERAL STATS & FILTERS SIDEBAR PANEL ─── */
          <div className="flex flex-col h-full overflow-hidden p-6 space-y-6">
            <div>
              <h3 className="text-xs font-black text-slate-800 dark:text-slate-200 uppercase tracking-wider flex items-center gap-2">
                <Filter size={14} className="text-blue-500" /> Filtros del Espacio
              </h3>
              <p className="text-[10px] text-slate-400 uppercase font-black tracking-widest mt-1">Afina la búsqueda de Faros</p>
            </div>

            {/* Filter inputs */}
            <div className="space-y-4">
              <div>
                <label className="block text-[10px] font-black uppercase tracking-widest text-slate-400 mb-1.5">Estado</label>
                <select
                  value={statusFilter}
                  onChange={e => setStatusFilter(e.target.value)}
                  className={selectCls}
                >
                  <option value="all">Cualquier estado</option>
                  <option value="Activo">Activo</option>
                  <option value="Inactivo">Inactivo</option>
                  <option value="Suspendido">Suspendido</option>
                </select>
              </div>

              <div>
                <label className="block text-[10px] font-black uppercase tracking-widest text-slate-400 mb-1.5">Día de Reunión</label>
                <select
                  value={dayFilter}
                  onChange={e => setDayFilter(e.target.value)}
                  className={selectCls}
                >
                  <option value="all">Cualquier día</option>
                  {['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'].map(d => (
                    <option key={d} value={d}>{d}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-[10px] font-black uppercase tracking-widest text-slate-400 mb-1.5">Zona / Barrio</label>
                <select
                  value={zoneFilter}
                  onChange={e => setZoneFilter(e.target.value)}
                  className={selectCls}
                >
                  <option value="all">Cualquier zona</option>
                  {uniqueZones.map(z => (
                    <option key={z} value={z}>{z}</option>
                  ))}
                </select>
              </div>

              <button
                type="button"
                onClick={() => {
                  setStatusFilter('all');
                  setDayFilter('all');
                  setZoneFilter('all');
                  setSearchQuery('');
                }}
                className="w-full py-2 bg-slate-50 dark:bg-white/5 hover:bg-slate-100 text-slate-600 dark:text-slate-300 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all border border-slate-200 dark:border-white/10"
              >
                Restablecer Filtros
              </button>
            </div>

            <div className="h-px bg-slate-100 dark:bg-white/5 my-2" />

            {/* Dashboard Metrics */}
            <div className="space-y-4 flex-1 overflow-y-auto scrollbar-thin">
              <h3 className="text-xs font-black text-slate-800 dark:text-slate-200 uppercase tracking-wider flex items-center gap-2">
                <BarChart3 size={14} className="text-blue-500" /> Indicadores Clave (KPI)
              </h3>
              
              <div className="grid grid-cols-2 gap-3">
                <div className="border border-slate-200/60 dark:border-white/5 bg-slate-50/50 dark:bg-white/[0.01] p-3 rounded-2xl flex flex-col justify-between">
                  <span className="text-[9px] font-black text-slate-400 uppercase tracking-wider">Total Faros</span>
                  <span className="text-xl font-black italic tracking-tight text-slate-800 dark:text-white mt-1">
                    {metrics.totalFaros} <span className="text-[10px] font-bold text-slate-400 not-italic">({metrics.activeFaros} act)</span>
                  </span>
                </div>

                <div className="border border-slate-200/60 dark:border-white/5 bg-slate-50/50 dark:bg-white/[0.01] p-3 rounded-2xl flex flex-col justify-between">
                  <span className="text-[9px] font-black text-slate-400 uppercase tracking-wider">Ocupación Prom.</span>
                  <span className="text-xl font-black italic tracking-tight text-slate-800 dark:text-white mt-1">
                    {metrics.occupancyRate}%
                  </span>
                </div>
              </div>

              {/* Warnings and needs */}
              <div className="space-y-2">
                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Necesidades de Roles</p>
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs p-2.5 bg-slate-50 dark:bg-white/[0.01] border border-slate-200/40 dark:border-white/5 rounded-xl">
                    <span className="font-semibold text-slate-500">Faros sin Líder</span>
                    <span className={`px-2 py-0.5 rounded font-black ${metrics.withoutLeader > 0 ? 'bg-rose-50 text-rose-600 dark:bg-rose-950/20 dark:text-rose-400' : 'bg-slate-100 text-slate-400'}`}>
                      {metrics.withoutLeader}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-xs p-2.5 bg-slate-50 dark:bg-white/[0.01] border border-slate-200/40 dark:border-white/5 rounded-xl">
                    <span className="font-semibold text-slate-500">Faros sin Colíder</span>
                    <span className={`px-2 py-0.5 rounded font-black ${metrics.withoutAssistant > 0 ? 'bg-amber-50 text-amber-600 dark:bg-amber-950/20 dark:text-amber-400' : 'bg-slate-100 text-slate-400'}`}>
                      {metrics.withoutAssistant}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-xs p-2.5 bg-slate-50 dark:bg-white/[0.01] border border-slate-200/40 dark:border-white/5 rounded-xl">
                    <span className="font-semibold text-slate-500">Faros sin Anfitrión</span>
                    <span className={`px-2 py-0.5 rounded font-black ${metrics.withoutHost > 0 ? 'bg-amber-50 text-amber-600 dark:bg-amber-950/20 dark:text-amber-400' : 'bg-slate-100 text-slate-400'}`}>
                      {metrics.withoutHost}
                    </span>
                  </div>
                </div>
              </div>

              {/* Quick assignment catalog */}
              {summary && summary.unassigned_members.length > 0 && (
                <div className="space-y-3 pt-2">
                  <div className="flex items-center justify-between">
                    <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Asignación Rápida ({summary.unassigned_members.length})</p>
                    <span className="text-[9px] font-bold text-amber-500 uppercase tracking-wider animate-pulse">Integrantes sin Faro</span>
                  </div>
                  <div className="space-y-3 max-h-60 overflow-y-auto pr-1 scrollbar-thin">
                    {summary.unassigned_members.map(member => (
                      <div
                        key={member.id}
                        className="rounded-2xl border border-slate-200/60 dark:border-white/5 bg-white dark:bg-white/[0.01] p-3 space-y-2.5 shadow-sm"
                      >
                        <div className="min-w-0">
                          <p className="text-xs font-bold text-slate-900 dark:text-white truncate">
                            {member.name}
                          </p>
                          <p className="text-[9px] text-slate-400 mt-0.5">{member.church_role || 'Sin rol'}</p>
                        </div>
                        <div className="flex gap-2">
                          <select
                            value={quickAssignmentTargets[member.id] || ''}
                            onChange={e =>
                              setQuickAssignmentTargets(prev => ({
                                ...prev,
                                [member.id]: Number(e.target.value),
                              }))
                            }
                            className="flex-1 bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-xl px-2 py-1 text-[11px] font-medium outline-none focus:ring-1 focus:ring-blue-500/20"
                          >
                            <option value="">Elegir Faro...</option>
                            {houses.map(h => (
                              <option key={h.id} value={h.id}>
                                {h.name} {h.code ? `(${h.code})` : ''}
                              </option>
                            ))}
                          </select>
                          <button
                            onClick={() => handleQuickAssignMember(member.id)}
                            disabled={saving}
                            className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-[10px] font-black uppercase tracking-widest disabled:opacity-50 shadow-sm"
                          >
                            Asignar
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </RightPanel>
    </EvangelismShell>
  );
}

export default function FaroGroupsPage() {
  return (
    <Suspense
      fallback={
        <div className="p-6 space-y-4">
          <div className="text-center text-sm font-bold text-slate-500">Cargando grupos Faro...</div>
          {[1, 2, 3].map(i => (
            <div key={i} className="h-16 w-full bg-slate-100 dark:bg-white/5 rounded-2xl animate-pulse" />
          ))}
        </div>
      }
    >
      <FaroGroupsContent />
    </Suspense>
  );
}

