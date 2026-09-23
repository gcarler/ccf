'use client';

import type { Dispatch, SetStateAction } from 'react';
import type { MinistryEvent, Persona } from '@/app/plataforma/evangelism/types';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import ErrorBoundary from '@/components/ErrorBoundary';
import { Calendar, Check } from 'lucide-react';

interface EventAttendanceDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  event: MinistryEvent | null;
  date: string;
  setDate: (value: string) => void;
  saving: boolean;
  onSave: (forceEmpty?: boolean) => void;
  loading: boolean;
  showScanner: boolean;
  setShowScanner: Dispatch<SetStateAction<boolean>>;
  scannerToken: string;
  setScannerToken: (value: string) => void;
  onScan: () => void;
  isScanning: boolean;
  search: string;
  setSearch: (value: string) => void;
  roleFilter: string;
  setRoleFilter: (value: string) => void;
  roleOptions: string[];
  statusFilter: 'ALL' | 'PENDING' | 'PRESENT';
  setStatusFilter: (value: 'ALL' | 'PENDING' | 'PRESENT') => void;
  onMarkFiltered: () => void;
  onClearFiltered: () => void;
  filteredPersonas: Persona[];
  attendedIds: string[];
  onToggle: (id: string) => void;
  universe: Persona[];
  getTargetRoleLabel: (event: MinistryEvent | null | undefined) => string;
}

export default function EventAttendanceDrawer({
  isOpen,
  onClose,
  event,
  date,
  setDate,
  saving,
  onSave,
  loading,
  showScanner,
  setShowScanner,
  scannerToken,
  setScannerToken,
  onScan,
  isScanning,
  search,
  setSearch,
  roleFilter,
  setRoleFilter,
  roleOptions,
  statusFilter,
  setStatusFilter,
  onMarkFiltered,
  onClearFiltered,
  filteredPersonas,
  attendedIds,
  onToggle,
  universe,
  getTargetRoleLabel,
}: EventAttendanceDrawerProps) {
  return (
  <ErrorBoundary moduleName="Eventos - Asistencia">
  <WorkspaceDrawer
 isOpen={isOpen}
 onClose={() => onClose()}
 title="Registro de Asistencia"
 subtitle={event?.name ?? 'Evento'}
 actions={
 <>
 <div className="flex items-center gap-2 mr-auto">
 <Calendar size={14} className="text-[hsl(var(--text-secondary))]" />
 <input
 type="date"
 value={date}
 onChange={e => setDate(e.target.value)}
 className="text-sm font-bold text-[hsl(var(--text-primary))] outline-none bg-transparent"
 />
 </div>
 <button disabled={saving} onClick={() => onClose()} className="px-4 py-2 text-xs font-bold text-[hsl(var(--text-secondary))] disabled:opacity-60">
 Cancelar
 </button>
 <button
 onClick={() => onSave()}
 disabled={saving || loading || String(event?.status || '').toUpperCase() === 'CANCELLED' || String(event?.status || '').toUpperCase() === 'CANCELED'}
 className="px-3 py-2 bg-[hsl(var(--success))] text-[hsl(var(--primary-foreground))] rounded-lg text-xs font-semibold uppercase tracking-wide shadow-lg hover:bg-[hsl(var(--success))] active:scale-95 transition-all disabled:opacity-60 disabled:active:scale-100"
 >
 {saving ? 'Guardando...' : 'Guardar asistencia'}
 </button>
 </>
 }
 >
 <div className="space-y-3">
 {/* Scanner section */}
 <div>
 <button
 onClick={() => setShowScanner(s => !s)}
 className={`px-4 py-2 rounded-md text-2xs font-semibold uppercase tracking-wide transition-all ${showScanner ? 'bg-[hsl(var(--destructive))] text-[hsl(var(--destructive-foreground))]' : 'bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] hover:opacity-80'}`}
 >
 {showScanner ? 'Cerrar Escáner' : 'Modo Escáner'}
 </button>
 </div>

 {showScanner && (
 <div className="p-4 bg-[hsl(var(--bg-primary))] rounded-lg space-y-4">
 <p className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide text-center">Ingresa el token del carnet (CCF-PER-ID-TOKEN)</p>
 <div className="flex gap-2">
 <input
 type="text"
 value={scannerToken}
 onChange={e => setScannerToken(e.target.value)}
 placeholder="CCF-PER-ID-XXXXXX"
 className="flex-1 bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border-primary))] rounded-md px-4 py-1.5 text-sm text-[hsl(var(--text-primary))] focus:outline-none focus:border-[hsl(var(--primary))]"
 onKeyDown={e => e.key === 'Enter' && onScan()}
 />
 <button
 onClick={onScan}
 disabled={isScanning || !scannerToken}
 className="px-4 py-1.5 bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))] disabled:opacity-50 text-[hsl(var(--primary-foreground))] rounded-md text-2xs font-semibold uppercase tracking-wide transition-all"
 >
 {isScanning ? 'Validando...' : 'Validar'}
 </button>
 </div>
 </div>
 )}

 <div className="grid gap-3 md:grid-cols-[1.2fr,0.9fr,0.8fr,auto,auto] md:items-center">
 <input
 type="text"
 value={search}
 onChange={e => setSearch(e.target.value)}
 placeholder="Buscar por nombre o correo..."
 className="w-full rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-muted))] px-4 py-1.5 text-sm font-bold text-[hsl(var(--text-primary))] outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]"
 />
 <select
 value={roleFilter}
 onChange={e => setRoleFilter(e.target.value)}
 className="w-full rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-muted))] px-4 py-1.5 text-sm font-bold text-[hsl(var(--text-primary))] outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]"
 >
 <option value="ALL">Todos los roles</option>
 {roleOptions.map((role) => (
 <option key={role} value={role}>{role}</option>
 ))}
 </select>
 <select
 value={statusFilter}
 onChange={e => setStatusFilter(e.target.value as 'ALL' | 'PENDING' | 'PRESENT')}
 className="w-full rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-muted))] px-4 py-1.5 text-sm font-bold text-[hsl(var(--text-primary))] outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]"
 >
 <option value="ALL">Todos</option>
 <option value="PENDING">Pendientes</option>
 <option value="PRESENT">Presentes</option>
 </select>
 <button
 onClick={onMarkFiltered}
 disabled={filteredPersonas.length === 0}
 className="px-4 py-1.5 rounded-lg border border-[hsl(var(--success)/0.3)] bg-[hsl(var(--success-muted))] text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--success))] transition-all hover:bg-[hsl(var(--success)/0.2)] disabled:opacity-50"
 >
 Marcar filtrados
 </button>
 <button
 onClick={onClearFiltered}
 disabled={filteredPersonas.length === 0}
 className="px-4 py-1.5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] transition-all hover:bg-[hsl(var(--bg-muted))] disabled:opacity-50"
 >
 Limpiar filtrados
 </button>
 </div>

 {/* Summary badge */}
 <div className="flex items-center justify-between px-4 py-1.5 bg-[hsl(var(--success-muted))] rounded-lg border border-[hsl(var(--success)/0.3)]">
 <div>
 <p className="text-sm font-bold text-[hsl(var(--text-secondary))]">Presentes</p>
 <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
 {loading ? 'Cargando sesión...' : `${filteredPersonas.length} visibles en esta búsqueda`}
 </p>
 </div>
 <p className="text-base font-bold text-success">{attendedIds.length} <span className="text-sm font-bold text-[hsl(var(--text-secondary))]">/ {universe.length}</span></p>
 </div>

 {!loading && (
 <div className="flex flex-wrap gap-2">
 <span className="rounded-full border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] px-3 py-1 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
 {event?.target_audience === 'ROLE'
 ? `Universo: ${getTargetRoleLabel(event)}`
 : 'Universo: toda la iglesia'}
 </span>
 <span className="rounded-full border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] px-3 py-1 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
 {roleFilter === 'ALL' ? 'Todos los roles visibles' : roleFilter}
 </span>
 <span className="rounded-full border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] px-3 py-1 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
 {statusFilter === 'ALL' ? 'Vista completa' : statusFilter === 'PENDING' ? 'Solo pendientes' : 'Solo presentes'}
 </span>
 </div>
 )}

 {/* Persona list */}
 <div className="grid grid-cols-1 gap-3">
 {loading ? (
 <div className="py-1.5 text-center text-[hsl(var(--text-secondary))] text-sm">Cargando asistencia registrada...</div>
 ) : filteredPersonas.map(persona => (
  <div
  key={persona.id}
  tabIndex={0}
  role="checkbox"
  aria-checked={attendedIds.includes(persona.id)}
  onClick={() => onToggle(persona.id)}
  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onToggle(persona.id); } }}
  className={`flex items-center p-4 rounded-lg cursor-pointer transition-all border ${attendedIds.includes(persona.id)
 ? 'bg-[hsl(var(--success-muted))] border-[hsl(var(--success))] shadow-sm'
 : 'bg-[hsl(var(--bg-muted))] border-[hsl(var(--border-primary))] hover:border-[hsl(var(--border-primary))] '
 }`}
 >
 <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center mr-4 transition-colors shrink-0 ${attendedIds.includes(persona.id)
 ? 'bg-[hsl(var(--success))] border-[hsl(var(--success))] text-[hsl(var(--primary-foreground))]'
 : 'border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))]'
 }`}>
 {attendedIds.includes(persona.id) && <Check size={12} strokeWidth={4} />}
 </div>
 <div>
 <p className={`font-bold text-sm ${attendedIds.includes(persona.id) ? 'text-[hsl(var(--success))]' : 'text-[hsl(var(--text-primary))]'}`}>
 {persona.nombre_completo}
 </p>
 <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
 {persona.church_role || 'Sin rol'}
 </p>
 </div>
 </div>
 ))}
 {!loading && filteredPersonas.length === 0 && (
 <div className="py-1.5 text-center text-[hsl(var(--text-secondary))] text-sm">
 {universe.length === 0 ? 'Este evento no tiene universo esperado configurado con personas disponibles' : 'No hay personas para este filtro'}
 </div>
 )}
 </div>
 </div>
  </WorkspaceDrawer>
  </ErrorBoundary>
  );
}
