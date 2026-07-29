'use client';

import React, { useMemo } from 'react';
import { MapPin, Users, Search, ChevronRight, Trash2 } from 'lucide-react';
import type { Grupo } from './page';

interface BaseViewProps {
  houses: Grupo[];
  onSelectHouse: (house: Grupo) => void;
  getPersonaName: (id?: string) => string;
  /** Only TableView uses this; kept optional so the three read-only views don't need it. */
  onDeleteHouse?: (house: Grupo) => void;
}

function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`px-1.5 py-0.5 rounded text-2xs font-semibold ${
        status === 'Activo'
          ? 'text-success bg-success-soft dark:text-success dark:bg-[hsl(var(--success)/0.1)]'
          : 'text-[hsl(var(--text-secondary))] bg-[hsl(var(--bg-muted))]'
      }`}
    >
      {status}
    </span>
  );
}

export function ListView({ houses, onSelectHouse, getPersonaName }: BaseViewProps) {
  return (
    <div className="flex-1 overflow-y-auto p-4">
      {houses.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-full text-[hsl(var(--text-secondary))] gap-2">
          <Search size={32} className="opacity-40" />
          <p className="text-sm font-medium">No hay grupos que coincidan</p>
        </div>
      ) : (
        <div className="space-y-1 max-w-3xl">
          {houses.map((h) => (
            <button
              key={h.id}
              onClick={() => onSelectHouse(h)}
              className="w-full text-left flex items-center justify-between gap-3 px-4 py-3 rounded-lg bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border-primary))] hover:border-[hsl(var(--primary)/0.3)] dark:hover:border-[hsl(var(--primary)/0.4)] transition-all group"
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-bold text-[hsl(var(--text-primary))] truncate">{h.name}</span>
                  {h.code && <span className="text-2xs font-mono text-[hsl(var(--text-secondary))]">{h.code}</span>}
                </div>
                <div className="flex items-center gap-3 mt-1 text-xs text-[hsl(var(--text-secondary))]">
                  {h.zone && (
                    <span>
                      <MapPin size={11} className="inline mr-1" />
                      {h.zone}
                    </span>
                  )}
                  {h.leader_id ? (
                    <span>
                      <Users size={11} className="inline mr-1" />
                      {getPersonaName(h.leader_id)}
                    </span>
                  ) : (
                    <span className="text-warning font-semibold">Sin líder</span>
                  )}
                  <StatusBadge status={h.status} />
                </div>
              </div>
              <ChevronRight
                size={16}
                className="text-[hsl(var(--text-secondary))] group-hover:text-[hsl(var(--primary))] transition-colors shrink-0"
              />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export function GridView({ houses, onSelectHouse, getPersonaName }: BaseViewProps) {
  return (
    <div className="flex-1 overflow-y-auto p-4">
      {houses.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-full text-[hsl(var(--text-secondary))] gap-2">
          <Search size={32} className="opacity-40" />
          <p className="text-sm font-medium">No hay grupos que coincidan</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
          {houses.map((h) => (
            <button
              key={h.id}
              onClick={() => onSelectHouse(h)}
              className="text-left w-full bg-[hsl(var(--bg-primary))] rounded-lg border border-[hsl(var(--border-primary))] p-4 hover:border-[hsl(var(--primary)/0.3)] dark:hover:border-[hsl(var(--primary)/0.4)] transition-all hover:shadow-md space-y-3"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="text-sm font-bold text-[hsl(var(--text-primary))] truncate">{h.name}</p>
                  {h.code && (
                    <p className="text-2xs font-mono text-[hsl(var(--text-secondary))]">{h.code}</p>
                  )}
                </div>
                <StatusBadge status={h.status} />
              </div>
              <div className="space-y-1.5 text-xs text-[hsl(var(--text-secondary))]">
                {h.zone && (
                  <p>
                    <MapPin size={12} className="inline mr-1.5" />
                    {h.zone}
                  </p>
                )}
                <p>
                  <Users size={12} className="inline mr-1.5" />
                  {h.leader_id ? getPersonaName(h.leader_id) : <span className="text-warning font-semibold">Sin líder</span>}
                </p>
                {h.address && <p className="truncate opacity-60">{h.address}</p>}
              </div>
              <div className="flex items-center gap-2 pt-2 border-t border-[hsl(var(--border-primary))]">
                <span className="text-2xs text-[hsl(var(--text-secondary))]">Cap. {h.capacity || '—'}</span>
                {h.day_of_week && <span className="text-2xs text-[hsl(var(--text-secondary))]">{h.day_of_week}</span>}
                {h.start_time && <span className="text-2xs text-[hsl(var(--text-secondary))]">{h.start_time}</span>}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export function KanbanView({ houses, onSelectHouse, getPersonaName }: BaseViewProps) {
  const zones = useMemo(() => {
    const map = new Map<string, Grupo[]>();
    houses.forEach((h) => {
      const z = h.zone || 'Sin zona';
      if (!map.has(z)) map.set(z, []);
      map.get(z)!.push(h);
    });
    return Array.from(map.entries()).sort(([a], [b]) => a.localeCompare(b));
  }, [houses]);

  return (
    <div className="flex-1 overflow-x-auto p-4">
      {zones.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-full text-[hsl(var(--text-secondary))] gap-2">
          <Search size={32} className="opacity-40" />
          <p className="text-sm font-medium">No hay grupos que coincidan</p>
        </div>
      ) : (
        <div className="flex gap-4 h-full min-h-[400px]">
          {zones.map(([zone, zoneHouses]) => (
            <div
              key={zone}
              className="flex-shrink-0 w-72 bg-[hsl(var(--bg-muted))] rounded-lg border border-[hsl(var(--border-primary))] flex flex-col"
            >
              <div className="px-3 py-2 border-b border-[hsl(var(--border-primary))] flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                  {zone}
                </span>
                <span className="text-2xs font-semibold text-[hsl(var(--text-secondary))] bg-[hsl(var(--bg-muted))] px-2 py-0.5 rounded-full">
                  {zoneHouses.length}
                </span>
              </div>
              <div className="flex-1 overflow-y-auto p-2 space-y-2">
                {zoneHouses.map((h) => (
                  <button
                    key={h.id}
                    onClick={() => onSelectHouse(h)}
                    className="text-left w-full bg-[hsl(var(--bg-primary))] rounded-lg border border-[hsl(var(--border-primary))] p-3 hover:border-[hsl(var(--primary)/0.3)] dark:hover:border-[hsl(var(--primary)/0.4)] transition-all space-y-2"
                  >
                    <div className="flex items-start justify-between gap-1">
                      <p className="text-xs font-bold text-[hsl(var(--text-primary))] truncate">{h.name}</p>
                      <StatusBadge status={h.status} />
                    </div>
                    <div className="text-2xs text-[hsl(var(--text-secondary))] space-y-1">
                      <p>
                        <Users size={10} className="inline mr-1" />
                        {h.leader_id ? getPersonaName(h.leader_id) : <span className="text-warning">Sin líder</span>}
                      </p>
                      {h.address && <p className="truncate opacity-60">{h.address}</p>}
                    </div>
                    <div className="flex items-center gap-2 text-2xs text-[hsl(var(--text-secondary))]">
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

interface TableViewProps extends BaseViewProps {
  onDeleteHouse: (house: Grupo) => void;
}

export function TableView({ houses, onSelectHouse, getPersonaName, onDeleteHouse }: TableViewProps) {
  return (
    <div className="flex-1 overflow-auto p-4">
      {houses.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-full text-[hsl(var(--text-secondary))] gap-2">
          <Search size={32} className="opacity-40" />
          <p className="text-sm font-medium">No hay grupos que coincidan</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-[hsl(var(--border-primary))]">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-[hsl(var(--bg-muted))] border-b border-[hsl(var(--border-primary))]">
                <th className="text-left px-4 py-2.5 font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider">Nombre</th>
                <th className="text-left px-4 py-2.5 font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider">Código</th>
                <th className="text-left px-4 py-2.5 font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider">Zona</th>
                <th className="text-left px-4 py-2.5 font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider">Líder</th>
                <th className="text-left px-4 py-2.5 font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider">Dirección</th>
                <th className="text-center px-4 py-2.5 font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider">Cap.</th>
                <th className="text-center px-4 py-2.5 font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider">Día</th>
                <th className="text-center px-4 py-2.5 font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider">Estado</th>
                <th className="text-right px-4 py-2.5 font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider">Acción</th>
              </tr>
            </thead>
            <tbody>
              {houses.map((h) => (
                <tr
                  key={h.id}
                  tabIndex={0}
                  role="button"
                  onClick={() => onSelectHouse(h)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      (e.currentTarget as HTMLElement).click();
                    }
                  }}
                  className="border-b border-[hsl(var(--border-primary))] hover:bg-info-soft/50 dark:hover:bg-[hsl(var(--info)/0.05)] transition-colors cursor-pointer"
                >
                  <td className="px-4 py-2.5 font-medium text-[hsl(var(--text-primary))] whitespace-nowrap">{h.name}</td>
                  <td className="px-4 py-2.5 text-[hsl(var(--text-secondary))] font-mono">{h.code || '—'}</td>
                  <td className="px-4 py-2.5 text-[hsl(var(--text-secondary))]">{h.zone || '—'}</td>
                  <td className="px-4 py-2.5 text-[hsl(var(--text-secondary))]">
                    {h.leader_id ? getPersonaName(h.leader_id) : <span className="text-warning font-semibold">Sin líder</span>}
                  </td>
                  <td className="px-4 py-2.5 text-[hsl(var(--text-secondary))] max-w-[200px] truncate">{h.address || '—'}</td>
                  <td className="px-4 py-2.5 text-center text-[hsl(var(--text-secondary))]">{h.capacity || '—'}</td>
                  <td className="px-4 py-2.5 text-center text-[hsl(var(--text-secondary))]">{h.day_of_week || '—'}</td>
                  <td className="px-4 py-2.5 text-center">
                    <StatusBadge status={h.status} />
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteHouse(h);
                      }}
                      className="p-1 rounded text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--destructive))] hover:bg-danger-soft transition-colors"
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
