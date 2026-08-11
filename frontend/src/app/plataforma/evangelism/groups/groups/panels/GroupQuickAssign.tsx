'use client';

import React from 'react';
import type { AssignmentSummary, Grupo } from '../useGroupsPage';

interface GroupQuickAssignProps {
  summary: AssignmentSummary;
  houses: Grupo[];
  quickAssignmentTargets: Record<string, string>;
  setQuickAssignmentTargets: React.Dispatch<React.SetStateAction<Record<string, string>>>;
  onAssign: (personaId: string) => void;
  saving: boolean;
}

export function GroupQuickAssign({
  summary,
  houses,
  quickAssignmentTargets,
  setQuickAssignmentTargets,
  onAssign,
  saving,
}: GroupQuickAssignProps) {
  return (
    <div className="p-4 space-y-3">
      <div className="rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-muted))] dark:bg-black/20 px-4 py-1.5">
        <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
          Asignación rápida
        </p>
        <p className="text-sm font-medium text-[hsl(var(--text-secondary))] mt-1">
          Asigna personas sin grupo a una casa específica sin salir de
          esta vista.
        </p>
      </div>

      <div className="space-y-3">
        {summary.unassigned_personas.length === 0 ? (
          <div className="rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] px-4 py-1.5 text-center text-[hsl(var(--text-secondary))]">
            No hay personas sin grupo asignado.
          </div>
        ) : (
          summary.unassigned_personas.map(persona => (
            <div
              key={persona.id}
              className="rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] p-4"
            >
              <div className="flex flex-col md:flex-row md:items-center gap-3">
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-bold text-[hsl(var(--text-primary))] truncate">
                    {persona.name}
                  </p>
                  <p className="text-2xs text-[hsl(var(--text-secondary))] mt-1">
                    {persona.church_role || 'Sin rol'} · Sin grupo
                    asignado
                  </p>
                </div>
                <select
                  value={quickAssignmentTargets[persona.id] || ''}
                  onChange={e =>
                    setQuickAssignmentTargets(prev => ({
                      ...prev,
                      [persona.id]: e.target.value,
                    }))
                  }
                  className="w-full md:w-72 bg-[hsl(var(--bg-muted))] dark:bg-black/20 border border-[hsl(var(--border-primary))] rounded-md px-3 py-2 text-xs font-medium outline-none focus:ring-2 focus:ring-[hsl(var(--primary)/0.2)]"
                >
                  <option value="">Selecciona una casa</option>
                  {houses.map(h => (
                    <option key={h.id} value={h.id}>
                      {h.name} {h.code ? `· ${h.code}` : ''}
                    </option>
                  ))}
                </select>
                <button
                  onClick={() => onAssign(persona.id)}
                  disabled={saving}
                  className="px-4 py-2.5 rounded-md bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))] text-white text-xs font-semibold uppercase tracking-wide disabled:opacity-50"
                >
                  Asignar
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default GroupQuickAssign;
