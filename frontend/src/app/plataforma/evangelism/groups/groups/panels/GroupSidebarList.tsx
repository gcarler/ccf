'use client';

import { Activity, Plus, Search, Trash2 } from 'lucide-react';
import { apiFetch } from '@/lib/http';
import React, { useEffect } from 'react';
import type { Grupo, Mode } from '../useGroupsPage';

interface GroupSidebarListProps {
  // Sidebar context passthrough
  pushSidebarPanel: ReturnType<typeof import('@/context/SidebarLayerContext')['useSidebarLayers']>['pushSidebarPanel'];
  // Data
  filteredHouses: Grupo[];
  loading: boolean;
  selectedHouse: Grupo | null;
  isCreating: boolean;
  mode: Mode;
  searchQuery: string;
  setSearchQuery: (v: string) => void;
  // Handlers
  getPersonaName: (id?: string) => string;
  requestDeleteHouse: (house: Grupo) => void;
  // Selection setters
  setSelectedHouse: (h: Grupo | null) => void;
  setIsCreating: (open: boolean) => void;
  setFormData: React.Dispatch<React.SetStateAction<Partial<Grupo>>>;
  setSelectedPersonaIds: React.Dispatch<React.SetStateAction<Set<string>>>;
  token: string | null;
}

export function GroupSidebarList({
  pushSidebarPanel,
  filteredHouses,
  loading,
  selectedHouse,
  isCreating,
  mode,
  searchQuery,
  setSearchQuery,
  getPersonaName,
  requestDeleteHouse,
  setSelectedHouse,
  setIsCreating,
  setFormData,
  setSelectedPersonaIds,
  token,
}: GroupSidebarListProps) {
  // PUSH LIST TO SIDEBAR 2
  useEffect(() => {
    pushSidebarPanel({
      id: 'groups-list',
      title: 'Grupos',
      replaceAll: true,
      content: (
        <div className="flex flex-col h-full">
          <div className="px-3 pt-3 pb-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">
                Buscar Grupo
              </span>
              <button
                onClick={() => {
                  setIsCreating(true);
                  setSelectedHouse(null);
                  setSelectedPersonaIds(new Set());
                  setFormData({ capacity: 15, status: 'Activo' });
                }}
                className="bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))] text-white rounded-lg size-7 flex items-center justify-center transition-all shadow-sm active:scale-95"
              >
                <Plus size={14} />
              </button>
            </div>
            <div className="relative">
              <Search
                className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]"
                size={14}
              />
              <input
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder="Buscar por nombre o zona..."
                className="w-full bg-[hsl(var(--bg-muted))] border border-transparent rounded-md py-2 pl-9 pr-3 text-xs font-medium focus:ring-2 focus:ring-[hsl(var(--primary)/0.2)] focus:border-[hsl(var(--primary))] outline-none transition-all"
              />
            </div>
          </div>

          <div className="flex-1 overflow-y-auto px-3 pb-4 scrollbar-thin flex flex-col gap-1">
            {loading ? (
              <div className="py-1.5 text-center text-[hsl(var(--text-secondary))]">
                <Activity className="animate-spin mx-auto opacity-50" />
              </div>
            ) : filteredHouses.length === 0 ? (
              <div className="py-1.5 px-4 text-center">
                <Search size={24} className="mx-auto text-[hsl(var(--text-secondary))] mb-3" />
                <p className="text-xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Sin resultados</p>
                <p className="text-xs text-[hsl(var(--text-secondary))] mt-1">No hay grupos que coincidan.</p>
              </div>
            ) : (
              filteredHouses.map(h => {
                const isActive = selectedHouse?.id === h.id;
                return (
                  <div
                    key={h.id}
                    className={`flex items-start gap-1 px-2 py-1.5 rounded-md border transition-all duration-200 ${
                      isActive
                        ? 'bg-info-soft border-info-muted shadow-sm'
                        : 'bg-transparent border-transparent hover:bg-[hsl(var(--bg-muted))]'
                    }`}
                  >
                    <button
                      onClick={async () => {
                        setIsCreating(false);
                        try {
                          const detail = await apiFetch<Grupo>(
                            `/evangelism/grupos/${h.id}`,
                            { token }
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
                        } catch {
                          setSelectedHouse(h);
                          setFormData(h);
                          setSelectedPersonaIds(new Set());
                        }
                      }}
                      className="flex-1 text-left min-w-0"
                    >
                      <p
                        className={`text-xs font-bold truncate leading-tight ${isActive ? 'text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]' : 'text-[hsl(var(--text-primary))]'}`}
                      >
                        {h.name}
                      </p>
                      <div className="mt-1 flex items-center justify-between">
                        <p className="text-2xs font-medium text-[hsl(var(--text-secondary))] truncate">
                          {h.zone || 'Sin zona'}
                        </p>
                        {h.leader_id && (
                          <span className="text-2xs font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-md bg-info-soft text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] shrink-0">
                            {getPersonaName(h.leader_id).split(' ')[0]}
                          </span>
                        )}
                      </div>
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); requestDeleteHouse(h); }}
                      className="shrink-0 p-1 rounded text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--destructive))] dark:hover:text-[hsl(var(--destructive))] hover:bg-danger-soft transition-colors"
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
    setSearchQuery,
    loading,
    selectedHouse,
    isCreating,
    mode,
    token,
    getPersonaName,
    requestDeleteHouse,
    setIsCreating,
    setFormData,
    setSelectedPersonaIds,
    setSelectedHouse,
  ]);

  return null;
}

export default GroupSidebarList;
