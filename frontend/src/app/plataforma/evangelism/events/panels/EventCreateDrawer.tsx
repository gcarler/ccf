'use client';

import type { Persona, RoleDefinition } from '@/app/plataforma/evangelism/types';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import ErrorBoundary from '@/components/ErrorBoundary';
import { Check } from 'lucide-react';
import React from 'react';
import { DSButton, DSInput, DSSelect } from '@/design';

const DAY_LABELS = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'];

export interface EventCreateForm {
  name: string;
  description: string;
  event_type: string;
  /** Vacío representa el Universo completo; un UUID limita el evento a una sede. */
  sede_id?: string;
  target_audience: string;
  target_role_id: string;
  target_role_ids: string[];
  target_persona_ids: string[];
  day_of_week: string;
  month_day: string;
  fixed_date: string;
  start_time: string;
  end_time: string;
}

export interface EventSedeOption {
  id: string;
  name: string;
}

export interface AudiencePresetData {
  id: string;
  name: string;
  target_audience: 'ALL' | 'ROLE' | 'MANUAL';
  target_role_ids: string[];
  target_persona_ids: string[];
}

interface EventCreateDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  saving: boolean;
  onSubmit: (e: React.FormEvent) => void;
  form: EventCreateForm;
  setForm: React.Dispatch<React.SetStateAction<EventCreateForm>>;
  roles: RoleDefinition[];
  sedes: EventSedeOption[];
  presets: AudiencePresetData[];
  onApplyPreset: (presetId: string) => void;
  onDeletePreset: (presetId: string) => void;
  onAddSuggestions: () => void;
  onSavePreset: (source: { target_audience: string; target_role_ids?: Array<string | number>; target_persona_ids?: Array<string | number> }) => void;
  manualSearch: string;
  setManualSearch: (value: string) => void;
  manualPersonas: Persona[];
}

export default function EventCreateDrawer({
  isOpen,
  onClose,
  saving,
  onSubmit,
  form,
  setForm,
  roles,
  sedes,
  presets,
  onApplyPreset,
  onDeletePreset,
  onAddSuggestions,
  onSavePreset,
  manualSearch,
  setManualSearch,
  manualPersonas,
}: EventCreateDrawerProps) {
  return (
  <ErrorBoundary moduleName="Eventos - Crear">
  <WorkspaceDrawer
  isOpen={isOpen}
  onClose={() => onClose()}
  title="Nuevo Evento"
 subtitle="Configura un evento de la iglesia"
 actions={
 <>
 <DSButton type="button" variant="ghost" disabled={saving} onClick={() => onClose()} className="px-4 py-2 text-xs font-bold text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] transition-colors disabled:opacity-60">
 Cancelar
 </DSButton>
 <DSButton
 variant="primary"
 form="create-event-form"
 type="submit"
 disabled={saving}
 className="px-3 py-2 bg-[hsl(var(--primary))] text-white rounded-lg text-xs font-semibold uppercase tracking-wide shadow-lg hover:bg-[hsl(var(--primary))] active:scale-95 transition-all flex items-center gap-2 disabled:opacity-60 disabled:active:scale-100"
 >
 {saving ? 'Guardando...' : 'Guardar'} <Check size={14} />
 </DSButton>
 </>
 }
 >
 <form id="create-event-form" onSubmit={onSubmit} className="space-y-3">
 <div className="space-y-1.5">
 <label htmlFor="event-name" className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Nombre del Evento *</label>
 <DSInput
 id="event-name"
 required
 value={form.name}
 onChange={e => setForm({ ...form, name: e.target.value })}
 className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-black/20 focus:ring-2 focus:ring-primary outline-none font-bold text-sm text-[hsl(var(--text-primary))]"
 placeholder="Ej: Servicio Dominical"
 />
 </div>

 <div className="space-y-1.5">
 <label htmlFor="event-sede" className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Universo del Evento</label>
 <DSSelect
 id="event-sede"
 value={form.sede_id}
 onChange={e => setForm({ ...form, sede_id: e.target.value })}
 className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-black/20 focus:ring-2 focus:ring-primary outline-none font-bold text-sm text-[hsl(var(--text-primary))] appearance-none"
 options={[{ value: '', label: 'Universo completo — Todas las sedes' }, ...sedes.map((sede) => ({ value: sede.id, label: sede.name }))]}
 />
 <p className="text-2xs text-[hsl(var(--text-secondary))]">“Todas las sedes” permite registrar personas de toda la base de datos.</p>
 </div>

 <div className="space-y-1.5">
 <label htmlFor="event-type" className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Tipo de Evento *</label>
 <DSSelect
 id="event-type"
 required
 value={form.event_type}
 onChange={e => setForm({ ...form, event_type: e.target.value })}
 className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-black/20 focus:ring-2 focus:ring-primary outline-none font-bold text-sm text-[hsl(var(--text-primary))] appearance-none"
 options={[
 { value: 'PERMANENT', label: 'Semanal / Rutinario' },
 { value: 'MONTHLY', label: 'Mensual' },
 { value: 'ANNUAL', label: 'Anual' },
 { value: 'ONCE', label: 'Única Vez / Fecha Fija' },
 { value: 'SPECIAL', label: 'Especial / Campaña' },
 { value: 'GROUPS', label: 'Temporada - fuera del templo' },
 { value: 'ONLINE', label: 'En Línea / Transmisión' },
 ]}
 />
 </div>

 <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
 <div className="space-y-1.5">
 <label htmlFor="event-audience" className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Universo Esperado</label>
 <DSSelect
 id="event-audience"
 value={form.target_audience}
 onChange={e => setForm({
 ...form,
 target_audience: e.target.value,
 target_role_id: e.target.value === 'ROLE' ? form.target_role_id : '',
 target_role_ids: e.target.value === 'ROLE' ? form.target_role_ids : [],
 target_persona_ids: e.target.value === 'MANUAL' ? form.target_persona_ids : [],
 })}
 className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-black/20 focus:ring-2 focus:ring-primary outline-none font-bold text-sm text-[hsl(var(--text-primary))] appearance-none"
 options={[
 { value: 'ALL', label: 'Toda la iglesia' },
 { value: 'ROLE', label: 'Uno o varios roles' },
 { value: 'MANUAL', label: 'Selección manual' },
 ]}
 />
 </div>
 <div className="space-y-1.5">
 <label htmlFor="event-roles" className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Roles esperados</label>
 <DSSelect
 id="event-roles"
 multiple
 disabled={form.target_audience !== 'ROLE'}
 value={form.target_role_ids}
 onChange={e => {
 const selectedValues = Array.from(e.target.selectedOptions).map((option) => option.value);
 setForm({ ...form, target_role_ids: selectedValues, target_role_id: selectedValues[0] || '' });
 }}
 className="min-h-[140px] w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-black/20 focus:ring-2 focus:ring-primary outline-none font-bold text-sm text-[hsl(var(--text-primary))] disabled:opacity-50"
 options={roles.map((role) => ({ value: role.id, label: role.name }))}
 />
 </div>
 </div>

 <div className="space-y-3 rounded-md border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-muted))] dark:bg-black/20 p-4">
 <div className="flex items-center justify-between gap-3">
 <div>
 <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Plantillas de audiencia</p>
 <p className="text-sm font-bold text-[hsl(var(--text-primary))] ">Guarda y reaplica universos esperados frecuentes</p>
 </div>
 <div className="flex items-center gap-2">
 <DSButton
 type="button"
 onClick={onAddSuggestions}
 className="rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] px-4 py-2 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] transition-all hover:bg-[hsl(var(--bg-muted))] dark:hover:bg-white/10"
 >
 Sugerencias
 </DSButton>
 <DSButton
 type="button"
 onClick={() => onSavePreset(form)}
 className="rounded-lg bg-[hsl(var(--primary))] px-4 py-2 text-2xs font-semibold uppercase tracking-wide text-white transition-all hover:bg-[hsl(var(--primary))]"
 >
 Guardar actual
 </DSButton>
 </div>
 </div>
 <div className="space-y-2">
 {presets.length === 0 ? (
 <div className="rounded-lg border border-dashed border-[hsl(var(--border-primary))] px-4 py-2 text-center text-sm text-[hsl(var(--text-secondary))]">
 Aun no hay plantillas guardadas
 </div>
 ) : presets.map((preset) => (
 <div key={preset.id} className="flex items-center justify-between gap-3 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] px-4 py-1.5">
 <div className="min-w-0">
 <p className="truncate text-sm font-bold text-[hsl(var(--text-primary))]">{preset.name}</p>
 <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
 {preset.target_audience === 'ALL'
 ? 'Toda la iglesia'
 : preset.target_audience === 'ROLE'
 ? `${preset.target_role_ids.length} roles`
 : `${preset.target_persona_ids.length} personas`}
 </p>
 </div>
 <div className="flex items-center gap-2">
 <DSButton
 type="button"
 onClick={() => onApplyPreset(preset.id)}
 className="rounded-lg bg-[hsl(var(--bg-primary))] px-3 py-2 text-2xs font-semibold uppercase tracking-wide text-white transition-all hover:opacity-85 "
 >
 Aplicar
 </DSButton>
 <DSButton
 type="button"
 onClick={() => onDeletePreset(preset.id)}
 className="rounded-lg border border-[hsl(var(--border-primary))] px-3 py-2 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] transition-all hover:bg-[hsl(var(--bg-muted))]"
 >
 Borrar
 </DSButton>
 </div>
 </div>
 ))}
 </div>
 </div>

 {form.target_audience === 'MANUAL' && (
 <div className="space-y-3">
 <div className="flex items-center justify-between gap-3">
  <label htmlFor="event-personas" className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Personas esperadas</label>
 <span className="rounded-full bg-[hsl(var(--info-muted))] dark:bg-[hsl(var(--info)/0.2)] px-3 py-1 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--primary))] dark:text-info">
 {form.target_persona_ids.length} seleccionadas
 </span>
 </div>
 <DSInput
 id="event-personas"
 value={manualSearch}
 onChange={e => setManualSearch(e.target.value)}
 placeholder="Buscar por nombre, correo o rol..."
 className="w-full rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-black/20 px-4 py-1.5 text-sm font-bold text-[hsl(var(--text-primary))] outline-none focus:ring-2 focus:ring-primary"
 />
 <div className="max-h-48 space-y-2 overflow-y-auto rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-muted))] dark:bg-black/20 p-3">
 {manualPersonas.map((persona) => {
 const isSelected = form.target_persona_ids.includes(persona.id);
 return (
 <DSButton
 key={persona.id}
 type="button"
 onClick={() => setForm({
 ...form,
 target_persona_ids: isSelected
 ? form.target_persona_ids.filter((value) => value !== persona.id)
 : [...form.target_persona_ids, persona.id],
 })}
 className={`flex w-full items-center justify-between rounded-lg border px-4 py-1.5 text-left transition-all ${
 isSelected
 ? 'border-info bg-info-muted dark:border-info dark:bg-[hsl(var(--info)/0.2)]'
 : 'border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] '
 }`}
 >
 <div>
 <p className="text-sm font-bold text-[hsl(var(--text-primary))]">{persona.nombre_completo}</p>
 <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{persona.church_role || 'Sin rol'}</p>
 </div>
 <span className={`text-2xs font-semibold uppercase tracking-wide ${isSelected ? 'text-[hsl(var(--primary))] dark:text-info' : 'text-[hsl(var(--text-secondary))]'}`}>
 {isSelected ? 'Incluida' : 'Agregar'}
 </span>
 </DSButton>
 );
 })}
 {manualPersonas.length === 0 && (
 <div className="py-2 text-center text-sm text-[hsl(var(--text-secondary))]">No hay personas para este filtro</div>
 )}
 </div>
 </div>
 )}

 <div className="grid grid-cols-2 gap-4">
 <div className="space-y-1.5">
 <label htmlFor="event-start-time" className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Hora de Inicio *</label>
 <DSInput
 id="event-start-time"
 type="time"
 required
 value={form.start_time}
 onChange={e => setForm({ ...form, start_time: e.target.value })}
 className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-black/20 focus:ring-2 focus:ring-primary outline-none font-bold text-sm text-[hsl(var(--text-primary))]"
 />
 </div>
 <div className="space-y-1.5">
 <label htmlFor="event-end-time" className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Hora de Finalización *</label>
 <DSInput
 id="event-end-time"
 type="time"
 required
 value={form.end_time}
 onChange={e => setForm({ ...form, end_time: e.target.value })}
 className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-black/20 focus:ring-2 focus:ring-primary outline-none font-bold text-sm text-[hsl(var(--text-primary))]"
 />
 </div>
 </div>

 {['PERMANENT', 'GROUPS', 'ONLINE'].includes(form.event_type) && (
 <div className="space-y-1.5">
 <label htmlFor="event-day-of-week" className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Día de la Semana</label>
 <DSSelect
 id="event-day-of-week"
 value={form.day_of_week}
 onChange={e => setForm({ ...form, day_of_week: e.target.value })}
 className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-black/20 focus:ring-2 focus:ring-primary outline-none font-bold text-sm "
 options={DAY_LABELS.map((d, i) => ({ value: String(i), label: d }))}
 />
 </div>
 )}

 {['ONCE', 'SPECIAL'].includes(form.event_type) && (
 <div className="space-y-1.5">
 <label htmlFor="event-fixed-date" className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Fecha Exacta</label>
 <DSInput
 id="event-fixed-date"
 type="date"
 value={form.fixed_date}
 onChange={e => setForm({ ...form, fixed_date: e.target.value })}
 className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-black/20 focus:ring-2 focus:ring-primary outline-none font-bold text-sm "
 />
 </div>
 )}

 {['ANNUAL', 'MONTHLY'].includes(form.event_type) && (
 <div className="space-y-1.5">
 <label htmlFor="event-month-day" className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Día(s) del Mes / Año</label>
 <DSInput
 id="event-month-day"
 value={form.month_day}
 onChange={e => setForm({ ...form, month_day: e.target.value })}
 className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-black/20 focus:ring-2 focus:ring-primary outline-none font-bold text-sm "
 placeholder="Ej: 15 de cada mes, o 24 Dic"
 />
 </div>
 )}

 <div className="space-y-1.5">
 <label htmlFor="event-description" className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Descripción</label>
 <textarea
 id="event-description"
 value={form.description}
 onChange={e => setForm({ ...form, description: e.target.value })}
 rows={3}
 className="w-full px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-black/20 focus:ring-2 focus:ring-primary outline-none font-bold text-sm resize-none"
 placeholder="Breve descripción del evento..."
 />
 </div>
 </form>
  </WorkspaceDrawer>
  </ErrorBoundary>
  );
}
