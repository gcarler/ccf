'use client';

import { CheckCircle2, Loader2, Plus, Search } from 'lucide-react';
import React from 'react';
import type { Persona } from '../useGroupDetailPage';

interface GroupAddAttendeeDrawerProps {
  show: boolean;
  activeSessionEnabled: boolean;
  // Search + persona selection
  personaQuery: string;
  setPersonaQuery: (v: string) => void;
  setRemoteQuery: (v: string) => void;
  remoteLoading: boolean;
  filteredPersonas: Persona[];
  selectedIds: Set<string>;
  setSelectedIds: React.Dispatch<React.SetStateAction<Set<string>>>;
  saving: boolean;
  onSave: () => void;
  onCancel: () => void;
  // Create persona
  isCreatingPersona: boolean;
  setIsCreatingPersona: (open: boolean) => void;
  newPersonaForm: { first_name: string; last_name: string; phone: string; email: string };
  setNewPersonaForm: React.Dispatch<React.SetStateAction<{ first_name: string; last_name: string; phone: string; email: string }>>;
  creatingPersona: boolean;
  onCreatePersona: () => void;
}

export function GroupAddAttendeeDrawer(props: GroupAddAttendeeDrawerProps) {
  if (!props.show) return null;
  const {
    activeSessionEnabled,
    personaQuery,
    setPersonaQuery,
    setRemoteQuery,
    remoteLoading,
    filteredPersonas,
    selectedIds,
    setSelectedIds,
    saving,
    onSave,
    onCancel,
    isCreatingPersona,
    setIsCreatingPersona,
    newPersonaForm,
    setNewPersonaForm,
    creatingPersona,
    onCreatePersona,
  } = props;

  return (
    <div className="mx-8 mb-3 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-1))] border border-[hsl(var(--info)/25%)] dark:border-[hsl(var(--info)/100%)]/30 rounded-lg p-4 shadow-sm animate-in slide-in-from-top-2 fade-in duration-200">
      <div className="flex items-center justify-between mb-4 pb-4 border-b border-[hsl(var(--border-primary))]">
        <div>
          <h3 className="text-sm font-semibold text-[hsl(var(--text-primary))]">Registrar Asistentes</h3>
          <p className="text-2xs uppercase tracking-wide text-[hsl(var(--text-secondary))] font-bold mt-1">Busca o crea personas para registrar su asistencia</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--bg-muted))] rounded-md transition-colors"
          >
            Cancelar
          </button>
          {!isCreatingPersona && (
            <button
              onClick={onSave}
              disabled={saving || selectedIds.size === 0 || !activeSessionEnabled}
              className="px-3 py-2 bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))] text-white rounded-md text-2xs font-semibold uppercase tracking-wide transition-all flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {saving ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />}
              {saving ? 'Guardando...' : `Guardar ${selectedIds.size > 0 ? `(${selectedIds.size})` : ''}`}
            </button>
          )}
        </div>
      </div>
      <div className="flex flex-col h-full">
        {!isCreatingPersona && (
          <div className="pb-6 shrink-0">
            <div className="flex gap-2 mb-2">
              <div className="relative flex-1">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" size={14} />
                <input
                  autoFocus
                  value={personaQuery}
                  onChange={e => {
                    setPersonaQuery(e.target.value);
                    setRemoteQuery(e.target.value);
                  }}
                  placeholder="Buscar por nombre (>=3 letras)..."
                  className="w-full bg-[hsl(var(--bg-muted))] dark:bg-black/20 border border-[hsl(var(--border-primary))] rounded-lg py-1.5 pl-10 pr-4 text-sm font-bold outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]"
                />
                {remoteLoading && (
                  <Loader2 className="absolute right-4 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))] animate-spin" size={14} />
                )}
              </div>
              <button
                onClick={() => setIsCreatingPersona(true)}
                className="px-4 py-1.5 bg-[hsl(var(--bg-muted))] hover:bg-[hsl(var(--bg-muted))] dark:hover:bg-white/10 rounded-lg text-xs font-semibold uppercase tracking-wide text-[hsl(var(--text-primary))] transition-colors shrink-0 flex items-center gap-2"
              >
                <Plus size={14} /> Nuevo
              </button>
            </div>
            {selectedIds.size > 0 && (
              <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] ml-1">
                {selectedIds.size} seleccionado{selectedIds.size > 1 ? 's' : ''}
              </p>
            )}
          </div>
        )}

        {isCreatingPersona ? (
          <div className="flex-1 overflow-y-auto pb-6 space-y-4 pt-2">
            <div>
              <label htmlFor="persona-first-name" className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-2 block">Nombres *</label>
              <input id="persona-first-name" value={newPersonaForm.first_name} onChange={e => setNewPersonaForm(p => ({ ...p, first_name: e.target.value }))} className="w-full bg-[hsl(var(--bg-muted))] dark:bg-black/20 border border-[hsl(var(--border-primary))] rounded-lg py-1.5 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]" placeholder="Ej. Juan" />
            </div>
            <div>
              <label htmlFor="persona-last-name" className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-2 block">Apellidos *</label>
              <input id="persona-last-name" value={newPersonaForm.last_name} onChange={e => setNewPersonaForm(p => ({ ...p, last_name: e.target.value }))} className="w-full bg-[hsl(var(--bg-muted))] dark:bg-black/20 border border-[hsl(var(--border-primary))] rounded-lg py-1.5 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]" placeholder="Ej. Pérez" />
            </div>
            <div>
              <label htmlFor="persona-phone" className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-2 block">Teléfono</label>
              <input id="persona-phone" value={newPersonaForm.phone} onChange={e => setNewPersonaForm(p => ({ ...p, phone: e.target.value }))} className="w-full bg-[hsl(var(--bg-muted))] dark:bg-black/20 border border-[hsl(var(--border-primary))] rounded-lg py-1.5 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]" placeholder="Opcional" />
            </div>
            <div>
              <label htmlFor="persona-email" className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-2 block">Correo Electrónico</label>
              <input type="email" id="persona-email" value={newPersonaForm.email} onChange={e => setNewPersonaForm(p => ({ ...p, email: e.target.value }))} className="w-full bg-[hsl(var(--bg-muted))] dark:bg-black/20 border border-[hsl(var(--border-primary))] rounded-lg py-1.5 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]" placeholder="Opcional" />
            </div>
            <div className="flex gap-3 pt-4">
              <button onClick={() => setIsCreatingPersona(false)} className="flex-1 py-1.5 bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-primary))] rounded-lg text-sm font-bold hover:bg-[hsl(var(--bg-muted))] transition-all">Cancelar</button>
              <button onClick={onCreatePersona} disabled={creatingPersona || !newPersonaForm.first_name || !newPersonaForm.last_name} className="flex-1 py-1.5 bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))] text-white rounded-lg text-sm font-bold transition-all flex items-center justify-center gap-2 disabled:opacity-50">
                {creatingPersona ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />} Crear
              </button>
            </div>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto pb-6 space-y-1 border-t border-[hsl(var(--border-primary))] pt-4">
            {filteredPersonas.length === 0 ? (
              <p className="text-center text-[hsl(var(--text-secondary))] text-sm py-1.5">No se encontraron personas</p>
            ) : filteredPersonas.map(m => {
              const isSelected = selectedIds.has(m.id);
              return (
                <button
                  key={m.id}
                  onClick={() => setSelectedIds(prev => {
                    const next = new Set(prev);
                    isSelected ? next.delete(m.id) : next.add(m.id);
                    return next;
                  })}
                  className={`w-full flex items-center gap-3 p-3 rounded-lg text-left transition-all ${isSelected ? 'bg-info-soft dark:bg-[hsl(var(--info))]/20 border border-[hsl(var(--info)/30%)] dark:border-[hsl(var(--info)/100%)]/30' : 'hover:bg-[hsl(var(--bg-muted))] dark:hover:bg-white/5 border border-transparent'}`}
                >
                  <div className={`size-9 rounded-md flex items-center justify-center text-sm font-semibold shrink-0 ${isSelected ? 'bg-[hsl(var(--primary))] text-white' : 'bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))]'}`}>
                    {isSelected ? <CheckCircle2 size={16} /> : (m.nombre_completo?.charAt(0) || '')}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-bold text-[hsl(var(--text-primary))] truncate">{m.nombre_completo}</p>
                    {m.church_role && <p className="text-2xs text-[hsl(var(--text-secondary))]">{m.church_role}</p>}
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

export default GroupAddAttendeeDrawer;
