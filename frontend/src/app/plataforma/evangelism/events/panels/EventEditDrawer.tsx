'use client';

import type { EventAudience, MinistryEvent, Persona, RoleDefinition } from '@/app/plataforma/evangelism/types';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import ErrorBoundary from '@/components/ErrorBoundary';
import { Pencil } from 'lucide-react';
import type { AudiencePresetData } from './EventCreateDrawer';
import { DSButton } from '@/design';

interface EventEditDrawerProps {
  event: MinistryEvent | null;
  setEvent: React.Dispatch<React.SetStateAction<MinistryEvent | null>>;
  updatingId: string | null;
  onSave: (evId: string, payload: Partial<MinistryEvent> & {
    target_audience?: string;
    target_role_ids?: string[];
    target_persona_ids?: string[];
  }) => void;
  roles: RoleDefinition[];
  getTargetRoleIds: (event: MinistryEvent | null | undefined) => string[];
  manualSearch: string;
  setManualSearch: (value: string) => void;
  manualPersonas: Persona[];
  presets: AudiencePresetData[];
  onApplyPreset: (presetId: string) => void;
  onDeletePreset: (presetId: string) => void;
  onAddSuggestions: () => void;
  onSavePreset: (source: { target_audience: string; target_role_ids?: Array<string | number>; target_persona_ids?: Array<string | number> }) => void;
}

export default function EventEditDrawer({
  event,
  setEvent,
  updatingId,
  onSave,
  roles,
  getTargetRoleIds,
  manualSearch,
  setManualSearch,
  manualPersonas,
  presets,
  onApplyPreset,
  onDeletePreset,
  onAddSuggestions,
  onSavePreset,
}: EventEditDrawerProps) {
  return (
 <ErrorBoundary moduleName="Eventos - Editar" compact>
 <WorkspaceDrawer
 isOpen={!!event}
 onClose={() => setEvent(null)}
 title="Editar Evento"
 subtitle="Modifica los detalles o configuración"
 actions={
 <>
 <DSButton variant="ghost" disabled={!!event && updatingId === event.id} onClick={() => setEvent(null)} className="px-4 py-2 text-xs font-bold text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] transition-colors disabled:opacity-60">
 Cancelar
 </DSButton>
 <DSButton variant="primary" disabled={!event || updatingId === event.id} onClick={() => event && onSave(event.id, { name: event.name, description: event.description, location: event.location, status: event.status, cancellation_reason: event.cancellation_reason, start_time: event.start_time, end_time: event.end_time, target_audience: event.target_audience || 'ALL', target_role_id: (event.target_audience || 'ALL') === 'ROLE' ? (event.target_role_ids?.[0] || event.target_role_id) : null, target_role_ids: (event.target_audience || 'ALL') === 'ROLE' ? (event.target_role_ids || getTargetRoleIds(event)) : [], target_persona_ids: (event.target_audience || 'ALL') === 'MANUAL' ? (event.target_persona_ids || []) : [] })} className="px-3 py-2 bg-[hsl(var(--primary))] text-white rounded-lg text-xs font-semibold uppercase tracking-wide shadow-lg hover:bg-[hsl(var(--primary))] active:scale-95 transition-all flex items-center gap-2 disabled:opacity-60">
 {event && updatingId === event.id ? 'Guardando...' : 'Guardar'} <Pencil size={14} />
 </DSButton>
 </>
 }
 >
 {event && (
 <div className="space-y-3">
 <div className="space-y-1.5">
 <label htmlFor="edit-event-name" className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Nombre</label>
 <input id="edit-event-name" type="text" value={event.name} onChange={e => setEvent({...event, name: e.target.value})} className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-black/20 focus:ring-2 focus:ring-primary outline-none font-bold text-sm text-[hsl(var(--text-primary))]" />
 </div>
 <div className="space-y-1.5">
 <label htmlFor="edit-event-status" className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Estado</label>
 <select
 id="edit-event-status"
 value={event.status || 'SCHEDULED'}
 onChange={e => setEvent({...event, status: e.target.value})}
 className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-black/20 focus:ring-2 focus:ring-primary outline-none font-bold text-sm text-[hsl(var(--text-primary))] appearance-none"
 >
 <option value="SCHEDULED">Programado</option>
 <option value="COMPLETED">Realizado</option>
 <option value="CANCELLED">Cancelado</option>
 </select>
 </div>
 <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
 <div className="space-y-1.5">
 <label htmlFor="edit-event-audience" className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Universo Esperado</label>
 <select
 id="edit-event-audience"
 value={event.target_audience || 'ALL'}
 onChange={e => setEvent({
 ...event,
 target_audience: e.target.value as EventAudience,
 target_role_id: e.target.value === 'ROLE' ? event.target_role_id : null,
 target_role_ids: e.target.value === 'ROLE' ? (event.target_role_ids || getTargetRoleIds(event)) : [],
 target_persona_ids: e.target.value === 'MANUAL' ? (event.target_persona_ids || []) : [],
 })}
 className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-black/20 focus:ring-2 focus:ring-primary outline-none font-bold text-sm text-[hsl(var(--text-primary))] appearance-none"
 >
 <option value="ALL">Toda la iglesia</option>
 <option value="ROLE">Uno o varios roles</option>
 <option value="MANUAL">Selección manual</option>
 </select>
 </div>
 <div className="space-y-1.5">
 <label htmlFor="edit-event-roles" className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Roles esperados</label>
 <select
 id="edit-event-roles"
 multiple
 disabled={(event.target_audience || 'ALL') !== 'ROLE'}
 value={(event.target_role_ids || getTargetRoleIds(event)).map((value: string) => String(value))}
 onChange={e => {
 const selectedValues = Array.from(e.target.selectedOptions).map((option) => option.value);
 setEvent({ ...event, target_role_ids: selectedValues, target_role_id: selectedValues[0] || null });
 }}
 className="min-h-[140px] w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-black/20 focus:ring-2 focus:ring-primary outline-none font-bold text-sm text-[hsl(var(--text-primary))] disabled:opacity-50"
 >
 {roles.map((role) => (
 <option key={role.id} value={role.id}>{role.name}</option>
 ))}
 </select>
 </div>
 </div>
 <div className="space-y-3 rounded-md border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-muted))] dark:bg-black/20 p-4">
 <div className="flex items-center justify-between gap-3">
 <div>
 <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Plantillas de audiencia</p>
 <p className="text-sm font-bold text-[hsl(var(--text-primary))] ">Aplica o guarda universos reutilizables</p>
 </div>
 <div className="flex items-center gap-2">
 <button type="button" onClick={onAddSuggestions} className="rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] px-4 py-2 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] transition-all hover:bg-[hsl(var(--bg-muted))] dark:hover:bg-white/10">Sugerencias</button>
 <button type="button" onClick={() => onSavePreset({ target_audience: event.target_audience || 'ALL', target_role_ids: event.target_role_ids || [], target_persona_ids: event.target_persona_ids || [] })} className="rounded-lg bg-[hsl(var(--primary))] px-4 py-2 text-2xs font-semibold uppercase tracking-wide text-white transition-all hover:bg-[hsl(var(--primary))]">Guardar actual</button>
 </div>
 </div>
 <div className="space-y-2">
 {presets.length === 0 ? (
 <div className="rounded-lg border border-dashed border-[hsl(var(--border-primary))] px-4 py-2 text-center text-sm text-[hsl(var(--text-secondary))]">Aun no hay plantillas guardadas</div>
 ) : presets.map((preset) => (
 <div key={preset.id} className="flex items-center justify-between gap-3 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] px-4 py-1.5">
 <div className="min-w-0">
 <p className="truncate text-sm font-bold text-[hsl(var(--text-primary))]">{preset.name}</p>
 <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{preset.target_audience === 'ALL' ? 'Toda la iglesia' : preset.target_audience === 'ROLE' ? `${preset.target_role_ids.length} roles` : `${preset.target_persona_ids.length} personas`}</p>
 </div>
 <div className="flex items-center gap-2">
 <button type="button" onClick={() => onApplyPreset(preset.id)} className="rounded-lg bg-[hsl(var(--bg-primary))] px-3 py-2 text-2xs font-semibold uppercase tracking-wide text-white transition-all hover:opacity-85 ">Aplicar</button>
 <button type="button" onClick={() => onDeletePreset(preset.id)} className="rounded-lg border border-[hsl(var(--border-primary))] px-3 py-2 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] transition-all hover:bg-[hsl(var(--bg-muted))]">Borrar</button>
 </div>
 </div>
 ))}
 </div>
 </div>
 {event.target_audience === 'MANUAL' && (
 <div className="space-y-3">
 <div className="flex items-center justify-between gap-3">
  <label htmlFor="edit-event-personas" className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Personas esperadas</label>
 <span className="rounded-full bg-[hsl(var(--info-muted))] dark:bg-[hsl(var(--info)/0.2)] px-3 py-1 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--primary))] dark:text-info">{(event.target_persona_ids || []).length} seleccionadas</span>
 </div>
   <input id="edit-event-personas" value={manualSearch} onChange={e => setManualSearch(e.target.value)} placeholder="Buscar por nombre, correo o rol..." className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-black/20 focus:ring-2 focus:ring-primary outline-none font-bold text-sm text-[hsl(var(--text-primary))]" />
 <div className="max-h-48 space-y-2 overflow-y-auto rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-muted))] dark:bg-black/20 p-3">
 {manualPersonas.map((persona) => {
 const isSelected = (event.target_persona_ids || []).includes(persona.id);
 return (
 <button key={persona.id} type="button" onClick={() => setEvent({ ...event, target_persona_ids: isSelected ? (event.target_persona_ids || []).filter((value) => value !== persona.id) : [...(event.target_persona_ids || []), persona.id], })} className={`flex w-full items-center justify-between rounded-lg border px-4 py-1.5 text-left transition-all ${isSelected ? 'border-info bg-info-muted dark:border-info dark:bg-[hsl(var(--info)/0.2)]' : 'border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] '}`}>
 <div>
 <p className="text-sm font-bold text-[hsl(var(--text-primary))]">{persona.nombre_completo}</p>
 <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{persona.church_role || 'Sin rol'}</p>
 </div>
 <span className={`text-2xs font-semibold uppercase tracking-wide ${isSelected ? 'text-[hsl(var(--primary))] dark:text-info' : 'text-[hsl(var(--text-secondary))]'}`}>{isSelected ? 'Incluida' : 'Agregar'}</span>
 </button>
 );
 })}
 {manualPersonas.length === 0 && <div className="py-2 text-center text-sm text-[hsl(var(--text-secondary))]">No hay personas para este filtro</div>}
 </div>
 </div>
 )}
 {event.status === 'CANCELLED' && (
 <div className="animate-in fade-in slide-in-from-top-2 space-y-1.5">
  <label htmlFor="edit-event-cancellation-reason" className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--destructive))]">Razón de Cancelación *</label>
  <textarea id="edit-event-cancellation-reason" value={event.cancellation_reason || ''} onChange={e => setEvent({...event, cancellation_reason: e.target.value})} rows={3} placeholder="¿Por qué no se realizó este evento?" className="w-full px-4 py-1.5 rounded-lg border border-danger bg-[hsl(var(--danger-muted))] dark:bg-black/20 focus:ring-2 focus:ring-danger outline-none font-bold text-sm text-danger dark:text-danger resize-none placeholder:text-[hsl(var(--danger)/0.5)] dark:placeholder:text-[hsl(var(--destructive))]" />
 </div>
 )}
 <div className="space-y-1.5">
 <label htmlFor="edit-event-description" className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Descripción</label>
 <textarea id="edit-event-description" value={event.description || ''} onChange={e => setEvent({...event, description: e.target.value})} rows={3} className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-black/20 focus:ring-2 focus:ring-primary outline-none font-bold text-sm text-[hsl(var(--text-primary))] resize-none" />
 </div>
 <div className="space-y-1.5">
 <label htmlFor="edit-event-location" className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Ubicación</label>
 <input id="edit-event-location" type="text" value={event.location || ''} onChange={e => setEvent({...event, location: e.target.value})} className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-black/20 focus:ring-2 focus:ring-primary outline-none font-bold text-sm text-[hsl(var(--text-primary))]" />
 </div>
 <div className="grid grid-cols-2 gap-4">
 <div className="space-y-1.5">
 <label htmlFor="edit-event-start-time" className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Hora de Inicio</label>
 <input id="edit-event-start-time" type="time" value={event.start_time || ''} onChange={e => setEvent({...event, start_time: e.target.value})} className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-black/20 focus:ring-2 focus:ring-primary outline-none font-bold text-sm text-[hsl(var(--text-primary))]" />
 </div>
 <div className="space-y-1.5">
 <label htmlFor="edit-event-end-time" className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Hora de Finalización</label>
 <input id="edit-event-end-time" type="time" value={event.end_time || ''} onChange={e => setEvent({...event, end_time: e.target.value})} className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-black/20 focus:ring-2 focus:ring-primary outline-none font-bold text-sm text-[hsl(var(--text-primary))]" />
 </div>
 </div>
 </div>
 )}
 </WorkspaceDrawer>
 </ErrorBoundary>
  );
}
