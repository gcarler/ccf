'use client';

import type { EventAudience, MinistryEvent, Persona, RoleDefinition } from '@/app/plataforma/evangelism/types';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import ErrorBoundary from '@/components/ErrorBoundary';
import { Pencil, QrCode, ExternalLink } from 'lucide-react';
import type { AudiencePresetData } from './EventCreateDrawer';
import { DSButton, DSInput, DSSelect } from '@/design';

interface EventEditDrawerProps {
  event: MinistryEvent | null;
  setEvent: React.Dispatch<React.SetStateAction<MinistryEvent | null>>;
  updatingId: string | null;
  onSave: (evId: string, payload: Partial<MinistryEvent> & {
    target_audience?: string;
    target_role_ids?: string[];
    target_persona_ids?: string[];
    requires_registration?: boolean;
    capacity_max?: number | null;
    registration_opens_at?: string | null;
    registration_closes_at?: string | null;
    waiting_list_enabled?: boolean;
    qr_mode?: string;
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
  onOpenFormStudio?: (event: MinistryEvent) => void;
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
  onOpenFormStudio,
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
 <DSButton variant="primary" disabled={!event || updatingId === event.id} onClick={() => event && onSave(event.id, {
   name: event.name,
   description: event.description,
   location: event.location,
   status: event.status,
   cancellation_reason: event.cancellation_reason,
   start_time: event.start_time,
   end_time: event.end_time,
   target_audience: event.target_audience || 'ALL',
   target_role_id: (event.target_audience || 'ALL') === 'ROLE' ? (event.target_role_ids?.[0] || event.target_role_id) : null,
   target_role_ids: (event.target_audience || 'ALL') === 'ROLE' ? (event.target_role_ids || getTargetRoleIds(event)) : [],
   target_persona_ids: (event.target_audience || 'ALL') === 'MANUAL' ? (event.target_persona_ids || []) : [],
   requires_registration: event.requires_registration,
   capacity_max: event.capacity_max,
   registration_opens_at: event.registration_opens_at,
   registration_closes_at: event.registration_closes_at,
   waiting_list_enabled: event.waiting_list_enabled,
   qr_mode: event.qr_mode,
 })} className="px-3 py-2 bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] rounded-lg text-xs font-semibold uppercase tracking-wide shadow-lg hover:bg-[hsl(var(--primary))] active:scale-95 transition-all flex items-center gap-2 disabled:opacity-60">
 {event && updatingId === event.id ? 'Guardando...' : 'Guardar'} <Pencil size={14} />
 </DSButton>
 </>
 }
 >
 {event && (
 <div className="space-y-3">
 <div className="space-y-1.5">
 <label htmlFor="edit-event-name" className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Nombre</label>
 <input id="edit-event-name" type="text" value={event.name} onChange={e => setEvent({...event, name: e.target.value})} className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] focus:ring-2 focus:ring-[hsl(var(--primary))] outline-none font-bold text-sm text-[hsl(var(--text-primary))]" />
 </div>
 <div className="space-y-1.5">
 <label htmlFor="edit-event-status" className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Estado</label>
 <select
 id="edit-event-status"
 value={event.status || 'SCHEDULED'}
 onChange={e => setEvent({...event, status: e.target.value})}
 className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] focus:ring-2 focus:ring-[hsl(var(--primary))] outline-none font-bold text-sm text-[hsl(var(--text-primary))] appearance-none"
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
 className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] focus:ring-2 focus:ring-[hsl(var(--primary))] outline-none font-bold text-sm text-[hsl(var(--text-primary))] appearance-none"
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
 className="min-h-[140px] w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] focus:ring-2 focus:ring-[hsl(var(--primary))] outline-none font-bold text-sm text-[hsl(var(--text-primary))] disabled:opacity-50"
 >
 {roles.map((role) => (
 <option key={role.id} value={role.id}>{role.name}</option>
 ))}
 </select>
 </div>
 </div>
 <div className="space-y-3 rounded-md border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-muted))] p-4">
 <div className="flex items-center justify-between gap-3">
 <div>
 <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Plantillas de audiencia</p>
 <p className="text-sm font-bold text-[hsl(var(--text-primary))] ">Aplica o guarda universos reutilizables</p>
 </div>
 <div className="flex items-center gap-2">
 <button type="button" onClick={onAddSuggestions} className="rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] px-4 py-2 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] transition-all hover:bg-[hsl(var(--bg-muted))] ">Sugerencias</button>
 <button type="button" onClick={() => onSavePreset({ target_audience: event.target_audience || 'ALL', target_role_ids: event.target_role_ids || [], target_persona_ids: event.target_persona_ids || [] })} className="rounded-lg bg-[hsl(var(--primary))] px-4 py-2 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--primary-foreground))] transition-all hover:bg-[hsl(var(--primary))]">Guardar actual</button>
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
 <button type="button" onClick={() => onApplyPreset(preset.id)} className="rounded-lg bg-[hsl(var(--bg-primary))] px-3 py-2 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--primary-foreground))] transition-all hover:opacity-85 ">Aplicar</button>
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
 <span className="rounded-full bg-[hsl(var(--info-muted))] px-3 py-1 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--primary))] ">{(event.target_persona_ids || []).length} seleccionadas</span>
 </div>
   <input id="edit-event-personas" value={manualSearch} onChange={e => setManualSearch(e.target.value)} placeholder="Buscar por nombre, correo o rol..." className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] focus:ring-2 focus:ring-[hsl(var(--primary))] outline-none font-bold text-sm text-[hsl(var(--text-primary))]" />
 <div className="max-h-48 space-y-2 overflow-y-auto rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-muted))] p-3">
 {manualPersonas.map((persona) => {
 const isSelected = (event.target_persona_ids || []).includes(persona.id);
 return (
 <button key={persona.id} type="button" onClick={() => setEvent({ ...event, target_persona_ids: isSelected ? (event.target_persona_ids || []).filter((value) => value !== persona.id) : [...(event.target_persona_ids || []), persona.id], })} className={`flex w-full items-center justify-between rounded-lg border px-4 py-1.5 text-left transition-all ${isSelected ? 'border-[hsl(var(--info))] bg-[hsl(var(--info-muted))]' : 'border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] '}`}>
 <div>
 <p className="text-sm font-bold text-[hsl(var(--text-primary))]">{persona.nombre_completo}</p>
 <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{persona.church_role || 'Sin rol'}</p>
 </div>
 <span className={`text-2xs font-semibold uppercase tracking-wide ${isSelected ? 'text-[hsl(var(--primary))] ' : 'text-[hsl(var(--text-secondary))]'}`}>{isSelected ? 'Incluida' : 'Agregar'}</span>
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
  <textarea id="edit-event-cancellation-reason" value={event.cancellation_reason || ''} onChange={e => setEvent({...event, cancellation_reason: e.target.value})} rows={3} placeholder="¿Por qué no se realizó este evento?" className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--destructive))] bg-[hsl(var(--destructive)/0.08)] focus:ring-2 focus:ring-[hsl(var(--destructive))] outline-none font-bold text-sm text-[hsl(var(--destructive))] resize-none placeholder:text-[hsl(var(--destructive)/0.5)]" />
 </div>
 )}
  {/* Pre-registro y Form Studio */}
 <div className="space-y-3 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--surface-2))] p-4">
 <div className="flex items-center justify-between gap-3">
 <div className="flex items-center gap-2">
 <div className="w-8 h-8 rounded-lg bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))] flex items-center justify-center">
 <QrCode size={18} />
 </div>
 <div>
 <p className="text-xs font-bold uppercase tracking-wide text-[hsl(var(--text-primary))]">Pre-registro con Código QR</p>
 <p className="text-2xs text-[hsl(var(--text-secondary))]">Emite pases digitales interactivos con correlativo único</p>
 </div>
 </div>
 <label className="relative inline-flex items-center cursor-pointer">
 <input
 type="checkbox"
 checked={Boolean(event.requires_registration)}
 onChange={e => setEvent({ ...event, requires_registration: e.target.checked })}
 className="sr-only peer"
 />
 <div className="w-11 h-6 bg-[hsl(var(--bg-muted))] peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-[hsl(var(--border-primary))] after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[hsl(var(--primary))]"></div>
 </label>
 </div>

 {event.requires_registration && (
 <div className="mt-3 pt-3 border-t border-[hsl(var(--border-primary))] space-y-3 animate-in fade-in slide-in-from-top-2 duration-300">
 <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
 <div className="space-y-1">
 <label htmlFor="edit-event-capacity" className="text-2xs font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">
 Aforo Máximo (Cupos)
 </label>
 <DSInput
 id="edit-event-capacity"
 type="number"
 min="1"
 placeholder="Ilimitado si está vacío"
 value={event.capacity_max ?? ''}
 onChange={e => setEvent({ ...event, capacity_max: e.target.value ? parseInt(e.target.value, 10) : null })}
 className="w-full px-3 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] text-sm text-[hsl(var(--text-primary))]"
 />
 </div>
 <div className="space-y-1">
 <label htmlFor="edit-event-qr-mode" className="text-2xs font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">
 Modo de Pase QR
 </label>
 <DSSelect
 id="edit-event-qr-mode"
 value={event.qr_mode || 'PER_REGISTRANT'}
 onChange={e => setEvent({ ...event, qr_mode: e.target.value as 'PER_REGISTRANT' | 'PER_EVENT' })}
 className="w-full px-3 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] text-sm"
 options={[
 { value: 'PER_REGISTRANT', label: 'Un QR por asistente (Recomendado)' },
 { value: 'PER_EVENT', label: 'Un QR global para el evento' },
 ]}
 />
 </div>
 </div>

 <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
 <div className="space-y-1">
 <label htmlFor="edit-event-reg-open" className="text-2xs font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">
 Apertura Pre-registro
 </label>
 <DSInput
 id="edit-event-reg-open"
 type="datetime-local"
 value={event.registration_opens_at ? event.registration_opens_at.slice(0, 16) : ''}
 onChange={e => setEvent({ ...event, registration_opens_at: e.target.value ? new Date(e.target.value).toISOString() : null })}
 className="w-full px-3 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] text-xs text-[hsl(var(--text-primary))]"
 />
 </div>
 <div className="space-y-1">
 <label htmlFor="edit-event-reg-close" className="text-2xs font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">
 Cierre Pre-registro
 </label>
 <DSInput
 id="edit-event-reg-close"
 type="datetime-local"
 value={event.registration_closes_at ? event.registration_closes_at.slice(0, 16) : ''}
 onChange={e => setEvent({ ...event, registration_closes_at: e.target.value ? new Date(e.target.value).toISOString() : null })}
 className="w-full px-3 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] text-xs text-[hsl(var(--text-primary))]"
 />
 </div>
 </div>

 <div className="flex items-center justify-between p-2 rounded-lg bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border-primary))]">
 <div>
 <p className="text-xs font-semibold text-[hsl(var(--text-primary))]">Lista de Espera Inteligente</p>
 <p className="text-2xs text-[hsl(var(--text-secondary))]">Si el aforo se llena, permite seguir registrando en cola</p>
 </div>
 <input
 type="checkbox"
 checked={Boolean(event.waiting_list_enabled)}
 onChange={e => setEvent({ ...event, waiting_list_enabled: e.target.checked })}
 className="rounded border-[hsl(var(--border-primary))] text-[hsl(var(--primary))] focus:ring-[hsl(var(--primary))]"
 />
 </div>

 {onOpenFormStudio && (
 <button
 type="button"
 onClick={() => onOpenFormStudio(event)}
 className="w-full py-2 px-3 rounded-lg border border-[hsl(var(--primary))] bg-[hsl(var(--primary)/0.08)] hover:bg-[hsl(var(--primary)/0.15)] text-[hsl(var(--primary))] text-xs font-bold uppercase tracking-wide flex items-center justify-center gap-2 transition-all"
 >
 <ExternalLink size={14} /> Abrir Form Studio para diseñar preguntas
 </button>
 )}
 </div>
 )}
 </div>

 <div className="space-y-1.5">
 <label htmlFor="edit-event-description" className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Descripción</label>
 <textarea id="edit-event-description" value={event.description || ''} onChange={e => setEvent({...event, description: e.target.value})} rows={3} className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] focus:ring-2 focus:ring-[hsl(var(--primary))] outline-none font-bold text-sm text-[hsl(var(--text-primary))] resize-none" />
 </div>
 <div className="space-y-1.5">
 <label htmlFor="edit-event-location" className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Ubicación</label>
 <input id="edit-event-location" type="text" value={event.location || ''} onChange={e => setEvent({...event, location: e.target.value})} className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] focus:ring-2 focus:ring-[hsl(var(--primary))] outline-none font-bold text-sm text-[hsl(var(--text-primary))]" />
 </div>
 <div className="grid grid-cols-2 gap-4">
 <div className="space-y-1.5">
 <label htmlFor="edit-event-start-time" className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Hora de Inicio</label>
 <input id="edit-event-start-time" type="time" value={event.start_time || ''} onChange={e => setEvent({...event, start_time: e.target.value})} className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] focus:ring-2 focus:ring-[hsl(var(--primary))] outline-none font-bold text-sm text-[hsl(var(--text-primary))]" />
 </div>
 <div className="space-y-1.5">
 <label htmlFor="edit-event-end-time" className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Hora de Finalización</label>
 <input id="edit-event-end-time" type="time" value={event.end_time || ''} onChange={e => setEvent({...event, end_time: e.target.value})} className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] focus:ring-2 focus:ring-[hsl(var(--primary))] outline-none font-bold text-sm text-[hsl(var(--text-primary))]" />
 </div>
 </div>
 </div>
 )}
 </WorkspaceDrawer>
 </ErrorBoundary>
  );
}
