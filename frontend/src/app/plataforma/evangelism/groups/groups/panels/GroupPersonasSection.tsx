'use client';

import {
  Calendar,
  FileSpreadsheet,
  FileText,
  Search,
  UserPlus,
  Users,
  X,
} from 'lucide-react';
import { downloadGroupAttendanceExcel, downloadGroupAttendancePdf } from '@/lib/evangelism-downloads';
import React from 'react';
import {
  FORM_INPUT_CLASS,
  type Grupo,
  type Persona,
} from '../useGroupsPage';

interface GroupPersonasSectionProps {
  selectedHouse: Pick<Grupo, 'id'>;
  selectedPersonaIds: Set<string>;
  setSelectedPersonaIds: React.Dispatch<React.SetStateAction<Set<string>>>;
  personas: Persona[];
  isAddingPersonas: boolean;
  setIsAddingPersonas: (open: boolean) => void;
  personaSearchQuery: string;
  setPersonaSearchQuery: (v: string) => void;
  personaRoleFilter: string;
  setPersonaRoleLinkFilter: (v: string) => void;
  personaAssignmentFilter: string;
  setPersonaAssignmentFilter: (v: string) => void;
  filteredPersonasList: Persona[];
  uniqueRoles: Array<string | undefined>;
}

export function GroupPersonasSection(props: GroupPersonasSectionProps) {
  const {
    selectedHouse,
    selectedPersonaIds,
    setSelectedPersonaIds,
    personas,
    isAddingPersonas,
    setIsAddingPersonas,
    personaSearchQuery,
    setPersonaSearchQuery,
    personaRoleFilter,
    setPersonaRoleLinkFilter,
    personaAssignmentFilter,
    setPersonaAssignmentFilter,
    filteredPersonasList,
    uniqueRoles,
  } = props;

  return (
    <div className="space-y-4">
      <div className="flex flex-col xl:flex-row xl:items-start justify-between gap-4 border-t border-[hsl(var(--border-primary))] pt-8 mt-4">
        <div>
          <h3 className="text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1 flex items-center gap-2">
            <Users size={12} className="text-[hsl(var(--primary))]" /> Personas actuales ({selectedPersonaIds.size})
          </h3>
          <p className="text-xs text-[hsl(var(--text-secondary))]">
            Estos son los personas actualmente asignados al grupo.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setIsAddingPersonas(!isAddingPersonas)}
          className={`px-4 py-2 text-xs font-semibold uppercase tracking-wide rounded-lg transition-colors flex items-center gap-2 ${
            isAddingPersonas
              ? 'bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--bg-muted))] dark:hover:bg-white/20'
              : 'bg-info-soft text-[hsl(var(--primary))] hover:bg-info-muted dark:bg-[hsl(var(--info)/0.1)] dark:text-[hsl(var(--primary))]'
          }`}
        >
          <UserPlus size={14} /> {isAddingPersonas ? 'Ocultar catálogo' : 'Añadir personas'}
        </button>
      </div>
      {/* CURRENT PERSONAS LIST */}
      {selectedPersonaIds.size > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {personas.filter(m => selectedPersonaIds.has(m.id)).map(persona => (
            <div key={persona.id} className="flex items-center justify-between gap-3 rounded-lg border border-info-muted dark:border-[hsl(var(--info)/0.3)] bg-info-soft px-4 py-1.5">
              <div className="min-w-0">
                <p className="text-sm font-bold text-[hsl(var(--text-primary))] truncate">
                  {persona.nombre_completo}
                </p>
                <p className="text-2xs text-[hsl(var(--text-secondary))] mt-0.5 truncate">
                  {persona.church_role || 'Sin rol'}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setSelectedPersonaIds(prev => {
                  const next = new Set(prev);
                  next.delete(persona.id);
                  return next;
                })}
                className="text-[hsl(var(--text-secondary))] hover:text-danger transition-colors shrink-0"
                title="Remover del Grupo"
              >
                <X size={16} />
              </button>
            </div>
          ))}
        </div>
      ) : (
        <div className="py-2 text-center border-2 border-dashed border-[hsl(var(--border-primary))] rounded-lg">
          <p className="text-sm text-[hsl(var(--text-secondary))] font-medium">No hay personas asignados a este grupo.</p>
        </div>
      )}

      {/* QUICK ACTION TO ATTENDANCE PANEL */}
      <div className="mt-3 pt-6 border-t border-[hsl(var(--border-primary))] flex items-center justify-between bg-info-soft rounded-lg px-4 py-2">
        <div>
          <h3 className="text-sm font-semibold text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] mb-1">Registrar Asistencia Semanal</h3>
          <p className="text-xs font-medium text-info-text/70 dark:text-info/70">
            Ir al panel dedicado para registrar la asistencia, ofrendas y novedades de las reuniones semanales de este grupo.
          </p>
        </div>
        <div className="flex flex-col sm:flex-row sm:items-center gap-2 shrink-0">
          <a
            href={`/plataforma/evangelism/groups/${selectedHouse.id}`}
            className="px-3 py-2.5 bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))] text-white rounded-md text-xs font-semibold uppercase tracking-wide transition-all shadow-lg shadow-primary flex items-center gap-2"
          >
            <Calendar size={14} /> Registrar Asistencia
          </a>
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => downloadGroupAttendancePdf(selectedHouse.id)}
              title="Descargar reporte de asistencia (PDF)"
              className="px-2.5 py-2.5 bg-danger-soft text-[hsl(var(--destructive))] dark:text-danger border border-danger-muted dark:border-[hsl(var(--danger)/0.3)] hover:bg-danger-muted dark:hover:bg-[hsl(var(--danger)/0.15)] rounded-md text-xs font-bold transition-all flex items-center gap-1.5"
            >
              <FileText size={13} /> PDF
            </button>
            <button
              type="button"
              onClick={() => downloadGroupAttendanceExcel(selectedHouse.id)}
              title="Descargar reporte de asistencia (Excel)"
              className="px-2.5 py-2.5 bg-success-soft text-[hsl(var(--secondary))] dark:text-success border border-success-muted dark:border-[hsl(var(--success)/0.3)] hover:bg-success-soft dark:hover:bg-[hsl(var(--success)/0.15)] rounded-md text-xs font-bold transition-all flex items-center gap-1.5"
            >
              <FileSpreadsheet size={13} /> XLSX
            </button>
          </div>
        </div>
      </div>
      {/* ADD PERSONAS CATALOG */}
      {isAddingPersonas && (
        <div className="mt-3 pt-6 border-t border-[hsl(var(--border-primary))] space-y-4">
          <div className="flex flex-col md:flex-row items-center gap-2 w-full">
            <div className="relative w-full md:flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" size={14} />
              <input
                value={personaSearchQuery}
                onChange={e => setPersonaSearchQuery(e.target.value)}
                placeholder="Buscar persona..."
                className={FORM_INPUT_CLASS + " pl-9 py-2"}
              />
            </div>
            <select
              value={personaRoleFilter}
              onChange={e => setPersonaRoleLinkFilter(e.target.value)}
              className={FORM_INPUT_CLASS + " py-2 w-full md:w-36 text-xs"}
            >
              <option value="">Todos los roles</option>
              {uniqueRoles.map(r => (
                <option key={r as string} value={r as string}>{r}</option>
              ))}
            </select>
            <select
              value={personaAssignmentFilter}
              onChange={e => setPersonaAssignmentFilter(e.target.value)}
              className={FORM_INPUT_CLASS + " py-2 w-full md:w-48 text-xs"}
            >
              <option value="all">Cualquier estado</option>
              <option value="unassigned">Sin grupo asignado</option>
              <option value="other_house">En otra casa</option>
            </select>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 max-h-[24rem] overflow-y-auto pr-1 scrollbar-thin">
            {filteredPersonasList.map(persona => {
              const checked = selectedPersonaIds.has(persona.id);
              // Hide already selected personas from the add list to prevent confusion
              if (checked) return null;

              return (
                <label
                  key={persona.id}
                  className="flex items-start gap-3 rounded-lg border px-4 py-1.5 cursor-pointer transition-all bg-[hsl(var(--bg-primary))] border-[hsl(var(--border-primary))] hover:border-[hsl(var(--primary)/0.3)]"
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() =>
                      setSelectedPersonaIds(prev => {
                        const next = new Set(prev);
                        if (next.has(persona.id))
                          next.delete(persona.id);
                        else next.add(persona.id);
                        return next;
                      })
                    }
                    className="mt-1 size-4 accent-[hsl(var(--primary))] shrink-0"
                  />
                  <div className="min-w-0">
                    <p className="text-sm font-bold text-[hsl(var(--text-primary))] truncate">
                      {persona.nombre_completo}
                    </p>
                    <p className="text-2xs text-[hsl(var(--text-secondary))] mt-0.5 truncate">
                      {persona.church_role || 'Sin rol'}
                    </p>
                  </div>
                </label>
              );
            })}
            {filteredPersonasList.filter(m => !selectedPersonaIds.has(m.id)).length === 0 && (
              <div className="col-span-full py-1.5 text-center text-[hsl(var(--text-secondary))] text-sm">
                No se encontraron personas disponibles con estos filtros.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default GroupPersonasSection;
