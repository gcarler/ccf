'use client';

import type { EventDashboardStat, MinistryEvent } from '@/app/plataforma/evangelism/types';
import type { ViewType } from '@/components/ViewSwitcher';
import { Calendar, MoreVertical, Pencil, QrCode, Trash2 } from 'lucide-react';

interface EventCardViewsProps {
  viewType: ViewType;
  events: MinistryEvent[];
  onOpenEvent: (eventId: string) => void;
  getTargetRoleLabel: (event: MinistryEvent) => string;
  getEventAttendanceStat: (event: MinistryEvent) => EventDashboardStat;
  getVisualDate: (event: MinistryEvent) => string;
  eventTypeLabel: Record<string, string>;
  eventTypeColor: Record<string, string>;
  onOpenQr: (event: MinistryEvent) => void;
  onOpenAttendance: (event: MinistryEvent) => void;
  menuOpenId: string | null;
  onMenuToggle: (id: string) => void;
  onEdit: (event: MinistryEvent) => void;
  onDelete: (id: string) => void;
}

export default function EventCardViews({
  viewType,
  events,
  onOpenEvent,
  getTargetRoleLabel,
  getEventAttendanceStat,
  getVisualDate,
  eventTypeLabel,
  eventTypeColor,
  onOpenQr,
  onOpenAttendance,
  menuOpenId,
  onMenuToggle,
  onEdit,
  onDelete,
}: EventCardViewsProps) {
  return (
    <>
  {/* GRID VIEW */}
  {viewType === 'grid' && (
  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
 {events.length === 0 ? (
 <div className="col-span-3 py-1.5 text-center text-[hsl(var(--text-secondary))] text-sm">
 No hay eventos registrados
 </div>
 ) : events.map(ev => (
 (() => {
 const attendanceStat = getEventAttendanceStat(ev);
 return (
  <div
  key={ev.id}
  tabIndex={0}
  role="link"
  onClick={() => onOpenEvent(ev.id)}
  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onOpenEvent(ev.id); } }}
  className="p-4 rounded-md border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-card))] hover:border-[hsl(var(--primary)/0.3)] hover:shadow-[0_8px_30px_hsl(var(--primary)/0.12)] transition-all group flex flex-col justify-between cursor-pointer"
  >
 <div>
 <div className="flex justify-between items-start mb-4">
 <div className="flex gap-2 items-center">
 <div className="w-12 h-8 rounded-lg bg-info-muted text-[hsl(var(--primary))] flex items-center justify-center">
 <Calendar size={20} />
 </div>
 {ev.status === 'CANCELLED' && (
 <span className="px-3 py-1 text-2xs font-semibold uppercase tracking-wide rounded-full badge-danger group-hover:badge-danger" title={ev.cancellation_reason}>
 Cancelado
 </span>
 )}
 </div>
 <span className={`px-3 py-1 text-2xs font-semibold uppercase tracking-wide rounded-full ${eventTypeColor[ev.event_type] ?? 'bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))]'}`}>
 {eventTypeLabel[ev.event_type] ?? ev.event_type}
 </span>
 </div>
 <h3 className="text-sm font-semibold text-[hsl(var(--text-primary))] mb-2 truncate group-hover:text-[hsl(var(--primary))] transition-colors uppercase italic pr-4">
 {ev.name}
 </h3>
 <p className="text-sm font-medium text-[hsl(var(--text-secondary))] line-clamp-2">{ev.description || 'Evento comunitario de CCF.'}</p>
 <div className="mt-3 flex flex-wrap gap-2">
 <span className="px-2.5 py-1 rounded-full text-2xs font-semibold uppercase tracking-wide bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))]">
 {getTargetRoleLabel(ev)}
 </span>
 <span className="px-2.5 py-1 rounded-full text-2xs font-semibold uppercase tracking-wide badge-info group-hover:badge-info">
 Universo: {attendanceStat.expected}
 </span>
 <span className="px-2.5 py-1 rounded-full text-2xs font-semibold uppercase tracking-wide badge-success group-hover:badge-success">
 {attendanceStat.attended} / {attendanceStat.expected || 0} ({attendanceStat.rate}%)
 </span>
 </div>
 </div>
 <div className="mt-3 flex items-center justify-between gap-2">
 <button onClick={(e) => { e.stopPropagation(); onOpenQr(ev); }} className="size-8 flex items-center justify-center bg-[hsl(var(--bg-muted))] hover:bg-[hsl(var(--primary))] text-[hsl(var(--text-secondary))] hover:text-white rounded-md transition-all shrink-0" title="Generar QR">
 <QrCode size={16} />
 </button>
 <button onClick={(e) => { e.stopPropagation(); onOpenAttendance(ev); }} className="flex-1 py-1.5 bg-[hsl(var(--bg-muted))] group-hover:bg-[hsl(var(--primary))] text-[hsl(var(--text-secondary))] group-hover:text-white rounded-md text-2xs font-semibold uppercase tracking-wide transition-all">
 Panel de Asistencia
 </button>
 <div className="relative shrink-0" onClick={e => e.stopPropagation()}>
 <button
 onClick={() => onMenuToggle(ev.id)}
 className="size-8 flex items-center justify-center bg-[hsl(var(--bg-muted))] hover:bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))] rounded-md transition-all"
 >
 <MoreVertical size={16} />
 </button>
 {menuOpenId === ev.id && (
 <div className="absolute right-0 bottom-12 z-50 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-card))] border border-[hsl(var(--border-primary))] rounded-lg shadow-[0_8px_30px_hsl(var(--primary)/0.15)] overflow-hidden w-40 animate-in fade-in slide-in-from-bottom-2">
  <button
  onClick={() => onEdit(ev)}
  className="w-full flex items-center gap-3 px-4 py-1.5 text-sm font-bold text-[hsl(var(--text-primary))] hover:bg-info-muted dark:hover:bg-white/5 transition-all"
  >
  <Pencil size={14} className="text-[hsl(var(--primary))]" /> Editar
  </button>
  <button
  onClick={() => onDelete(ev.id)}
  className="w-full flex items-center gap-3 px-4 py-1.5 text-sm font-bold text-[hsl(var(--destructive))] hover:bg-danger-muted dark:hover:bg-[hsl(var(--danger)/0.1)] transition-all"
  >
  <Trash2 size={14} /> Eliminar
  </button>
 </div>
 )}
 </div>
 </div>
 </div>
 );
 })()
 ))}
 </div>
 )}

 {/* LIST VIEW */}
 {viewType === 'list' && (
 <div className="bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-card))] rounded-md border border-[hsl(var(--border-primary))] overflow-hidden shadow-sm divide-y divide-[hsl(var(--border-primary))]">
 {events.map(ev => {
 const attendanceStat = getEventAttendanceStat(ev);
 return (
 <div key={ev.id} className="flex items-center gap-4 px-4 py-2 hover:bg-[hsl(var(--bg-muted))] dark:hover:bg-white/5 transition-colors group">
 <div className="w-9 h-9 rounded-md bg-[hsl(var(--info-muted))] dark:bg-[hsl(var(--info)/0.2)] text-[hsl(var(--primary))] flex items-center justify-center shrink-0">
 <Calendar size={16} />
 </div>
 <div className="flex-1 min-w-0">
  <p
  tabIndex={0}
  role="link"
  onClick={() => onOpenEvent(ev.id)}
  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onOpenEvent(ev.id); } }}
  className="font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-primary))] text-sm truncate cursor-pointer hover:text-[hsl(var(--primary))] transition-colors"
  >
 {ev.name}
 </p>
 <p className="text-xs text-[hsl(var(--text-secondary))] truncate">{ev.description || 'Sin descripción'}</p>
 </div>
 <div className="flex gap-2 items-center">
 {ev.status === 'CANCELLED' && (
 <span className="px-2.5 py-0.5 rounded-full text-2xs font-semibold uppercase badge-danger group-hover:badge-danger" title={ev.cancellation_reason}>
 Cancelado
 </span>
 )}
 <span className="px-2.5 py-0.5 rounded-full text-2xs font-semibold uppercase bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))]">
 {getTargetRoleLabel(ev)}
 </span>
 <span className="px-2.5 py-0.5 rounded-full text-2xs font-semibold uppercase badge-info group-hover:badge-info">
 Universo: {attendanceStat.expected}
 </span>
 <span className="px-2.5 py-0.5 rounded-full text-2xs font-semibold uppercase badge-success group-hover:badge-success">
 {attendanceStat.attended} / {attendanceStat.expected || 0} ({attendanceStat.rate}%)
 </span>
 <span className={`px-2.5 py-0.5 rounded-full text-2xs font-semibold uppercase ${eventTypeColor[ev.event_type] ?? 'bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))]'}`}>
 {eventTypeLabel[ev.event_type] ?? ev.event_type}
 </span>
 </div>
 <button onClick={(e) => { e.stopPropagation(); onOpenQr(ev); }} className="px-3 py-1.5 rounded-md bg-[hsl(var(--info-muted))] dark:bg-[hsl(var(--info)/0.2)] text-[hsl(var(--primary))] text-2xs font-semibold uppercase opacity-0 group-hover:opacity-100 transition-opacity mr-2">
 QR
 </button>
 <button onClick={(e) => { e.stopPropagation(); onOpenAttendance(ev); }} className="px-3 py-1.5 rounded-md bg-[hsl(var(--info-muted))] dark:bg-[hsl(var(--info)/0.2)] text-[hsl(var(--primary))] text-2xs font-semibold uppercase opacity-0 group-hover:opacity-100 transition-opacity">
 Asistencia
 </button>
 </div>
 );
 })}
 </div>
 )}

 {viewType === 'table' && (
 <div className="overflow-x-auto rounded-md border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-card))] shadow-sm">
 <table className="w-full min-w-[480px] text-left">
 <thead className="bg-[hsl(var(--bg-muted))]">
 <tr>
 {['Evento', 'Tipo', 'Audiencia', 'Universo', 'Asistencia', 'Fecha visual'].map((label) => (
 <th key={label} className="px-3 py-2 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
 {label}
 </th>
 ))}
 </tr>
 </thead>
 <tbody>
 {events.map((event) => {
 const attendanceStat = getEventAttendanceStat(event);
 return (
 <tr key={event.id} className="border-t border-[hsl(var(--border-primary))] hover:bg-[hsl(var(--bg-muted))]">
 <td className="px-3 py-2">
 <button onClick={() => onOpenEvent(event.id)} className="font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-primary))] hover:text-[hsl(var(--primary))]">
 {event.name}
 </button>
 </td>
 <td className="px-3 py-2 text-xs font-bold text-[hsl(var(--text-secondary))]">{eventTypeLabel[event.event_type] ?? event.event_type}</td>
 <td className="px-3 py-2 text-xs text-[hsl(var(--text-secondary))]">{getTargetRoleLabel(event)}</td>
 <td className="px-3 py-2 text-xs text-[hsl(var(--text-secondary))]">{attendanceStat.expected}</td>
 <td className="px-3 py-2 text-xs font-bold text-success">{attendanceStat.rate}%</td>
 <td className="px-3 py-2 text-xs text-[hsl(var(--text-secondary))]">{getVisualDate(event)}</td>
 </tr>
 );
 })}
 </tbody>
 </table>
 {events.length === 0 && <div className="py-2 text-center text-sm text-[hsl(var(--text-secondary))]">No hay eventos registrados</div>}
 </div>
 )}
    </>
  );
}
