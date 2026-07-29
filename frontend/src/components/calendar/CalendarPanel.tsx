'use client';

import React from 'react';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import { Flag, Plus, RefreshCw } from 'lucide-react';
import clsx from 'clsx';
import PanelSection from '@/components/calendar/PanelSection';
import {
  CalEvent, CalEventType, CalendarView, CALENDAR_VIEW_META, VIEW_EVENT_TYPES, EVENT_TYPE_META,
} from '@/types/calendar';

interface CalendarPanelProps {
  calendarView: CalendarView;
  viewMeta: { label: string; description: string; color: string };
  todayVisibleEvents: CalEvent[];
  upcomingVisibleEvents: CalEvent[];
  eventTypeCounts: Partial<Record<CalEventType, number>>;
  activeTypes: CalEventType[];
  onToggleType: (type: CalEventType) => void;
  onRefresh: () => void;
  onCreate: (kind: 'event' | 'task' | 'project', preset?: string) => void;
  onViewChange: (view: CalendarView) => void;
  viewIcons: Record<CalendarView, React.ElementType>;
  createOptions: Array<{ label: string; kind: 'event' | 'task' | 'project'; preset: string }>;
}

export default function CalendarPanel({
  calendarView, viewMeta, todayVisibleEvents, upcomingVisibleEvents,
  eventTypeCounts, activeTypes, onToggleType, onRefresh, onCreate,
  onViewChange, viewIcons, createOptions,
}: CalendarPanelProps) {
  const activeViewTypes = VIEW_EVENT_TYPES[calendarView];
  const ViewIcon = viewIcons[calendarView];

  return (
    <aside className="w-[220px] shrink-0 border-l border-[hsl(var(--border))] dark:border-white/5 flex flex-col overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-[hsl(var(--border))] dark:border-white/5 shrink-0">
        <div className="flex items-center gap-2">
          <ViewIcon size={14} style={{ color: viewMeta.color }} />
          <h2 className="text-base font-bold text-[hsl(var(--text-primary))] dark:text-white">{viewMeta.label}</h2>
        </div>
        <button onClick={onRefresh} className="p-1 rounded-md text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 transition-colors" title="Actualizar">
          <RefreshCw size={12} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-hide py-3 space-y-4 px-3">
        <PanelSection title="Hoy">
          <div className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/[0.03] p-3 space-y-2">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Eventos visibles</p>
                <p className="text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white">{todayVisibleEvents.length}</p>
              </div>
              <div className="text-right">
                <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Fecha</p>
                <p className="text-xs font-bold text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">{format(new Date(), 'dd MMM', { locale: es })}</p>
              </div>
            </div>
            {todayVisibleEvents.length === 0 && (
              <p className="text-2xs text-[hsl(var(--text-secondary))] text-center py-1">Sin actividades hoy</p>
            )}
          </div>
        </PanelSection>

        <PanelSection title="Filtrar por tipo">
          <div className="space-y-1">
            {activeViewTypes.map(type => (
              <button
                key={type}
                onClick={() => onToggleType(type)}
                className={clsx(
                  'flex w-full items-center justify-between rounded-lg px-2.5 py-1.5 text-left transition-all',
                  activeTypes.includes(type) ? 'bg-[hsl(var(--bg-primary))] dark:bg-white/5 opacity-100' : 'opacity-40 hover:opacity-70',
                )}
              >
                <span className="flex items-center gap-2">
                  <span className="size-2 rounded-full shrink-0" style={{ backgroundColor: EVENT_TYPE_META[type].color }} />
                  <span className="text-xs font-semibold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">{EVENT_TYPE_META[type].label}</span>
                </span>
                <span className={clsx('rounded-full px-1.5 py-0.5 text-2xs font-bold', EVENT_TYPE_META[type].chip)}>
                  {eventTypeCounts[type] ?? 0}
                </span>
              </button>
            ))}
          </div>
        </PanelSection>

        <PanelSection title="Próximos">
          {upcomingVisibleEvents.length === 0 ? (
            <div className="bg-[hsl(var(--surface-1))] dark:bg-white/[0.03] rounded-md p-4 text-center border border-dashed border-[hsl(var(--border))] dark:border-white/5">
              <Flag size={16} className="text-[hsl(var(--text-secondary))] mx-auto mb-2" />
              <p className="text-2xs text-[hsl(var(--text-secondary))] leading-snug">Sin próximos eventos en {viewMeta.label}.</p>
            </div>
          ) : (
            <div className="space-y-1">
              {upcomingVisibleEvents.map(e => (
                <div key={e.id} className="flex items-start gap-2 px-2 py-1.5 rounded-lg cursor-pointer hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 transition-colors group">
                  <span className="size-2 rounded-full shrink-0 mt-1" style={{ backgroundColor: e.color }} />
                  <div className="min-w-0">
                    <p className="truncate text-xs font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] group-hover:text-[hsl(var(--primary))]">{e.title}</p>
                    <p className="text-2xs text-[hsl(var(--text-secondary))] font-medium">
                      {format(e.start, 'MMM d')}
                      {!e.allDay && ` · ${format(e.start, 'h:mm a')}`}
                    </p>
                    <span className={clsx('inline-flex rounded-full px-1 py-0.5 text-2xs font-semibold uppercase tracking-wide', EVENT_TYPE_META[e.type].chip)}>
                      {EVENT_TYPE_META[e.type].label}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </PanelSection>

        <PanelSection title="Acción rápida">
          <div className="space-y-1">
            {createOptions.slice(0, 3).map((opt, i) => (
              <button
                key={i}
                onClick={() => onCreate(opt.kind, opt.preset)}
                className="w-full flex items-center gap-2 px-2.5 py-2 rounded-lg text-xs font-medium text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 border border-[hsl(var(--border))] dark:border-white/5 transition-all text-left"
              >
                <Plus size={12} className="shrink-0" style={{ color: viewMeta.color }} />
                {opt.label}
              </button>
            ))}
          </div>
        </PanelSection>

        <PanelSection title="Cambiar vista">
          <div className="space-y-0.5">
            {(Object.keys(CALENDAR_VIEW_META) as CalendarView[]).map(v => {
              const meta = CALENDAR_VIEW_META[v];
              const Icon = viewIcons[v];
              const isActive = v === calendarView;
              return (
                <button
                  key={v}
                  onClick={() => onViewChange(v)}
                  className={clsx(
                    'w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs font-semibold transition-all text-left',
                    isActive ? 'text-white' : 'text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5',
                  )}
                  style={isActive ? { backgroundColor: meta.color } : {}}
                >
                  <Icon size={12} />
                  {meta.label}
                </button>
              );
            })}
          </div>
        </PanelSection>
      </div>
    </aside>
  );
}
