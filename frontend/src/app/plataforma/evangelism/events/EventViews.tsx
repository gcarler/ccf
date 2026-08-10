'use client';

import type { EventDashboardStat, MinistryEvent } from '@/app/plataforma/evangelism/types';
import UniversalCalendarView, { type CalendarEvent } from '@/components/ui/UniversalCalendarView';
import UniversalGanttView, { type GanttItem } from '@/components/ui/UniversalGanttView';
import type { ViewType } from '@/components/ViewSwitcher';

interface EventBoardColumn {
  key: string;
  label: string;
  items: MinistryEvent[];
}

interface EventViewsProps {
  viewType: ViewType;
  boardColumns: EventBoardColumn[];
  calendarEvents: CalendarEvent[];
  ganttItems: GanttItem[];
  wikiNotes: string;
  onWikiNotesChange: (value: string) => void;
  onOpenEvent: (eventId: string) => void;
  eventTypeLabel: Record<string, string>;
  getTargetRoleLabel: (event: MinistryEvent) => string;
  getEventAttendanceStat: (event: MinistryEvent) => EventDashboardStat;
}

export default function EventViews({
  viewType,
  boardColumns,
  calendarEvents,
  ganttItems,
  wikiNotes,
  onWikiNotesChange,
  onOpenEvent,
  eventTypeLabel,
  getTargetRoleLabel,
  getEventAttendanceStat,
}: EventViewsProps) {
  return (
    <>
      {(viewType === 'board' || viewType === 'kanban') && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          {boardColumns.map((column) => (
            <section key={column.key} className="rounded-md border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] p-4 shadow-sm dark:bg-surface-card">
              <header className="mb-4 flex items-center justify-between">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{column.label}</h3>
                <span className="rounded-full bg-[hsl(var(--bg-muted))] px-2 py-0.5 font-semibold text-[hsl(var(--text-secondary))]">
                  {column.items.length}
                </span>
              </header>
              <div className="space-y-3">
                {column.items.map((event) => {
                  const attendanceStat = getEventAttendanceStat(event);
                  return (
                    <button
                      key={event.id}
                      onClick={() => onOpenEvent(event.id)}
                      className="w-full rounded-lg border border-[hsl(var(--border-primary))] p-4 text-left transition-all hover:border-[hsl(var(--primary)/0.3)] hover:shadow-lg"
                    >
                      <p className="text-sm font-semibold text-[hsl(var(--text-primary))]">{event.name}</p>
                      <p className="mt-1 text-xs text-[hsl(var(--text-secondary))]">{getTargetRoleLabel(event)}</p>
                      <div className="mt-3 flex items-center justify-between text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                        <span>{eventTypeLabel[event.event_type] ?? event.event_type}</span>
                        <span>{attendanceStat.rate}%</span>
                      </div>
                    </button>
                  );
                })}
                {column.items.length === 0 && <div className="py-2 text-center text-xs text-[hsl(var(--text-secondary))]">Sin eventos</div>}
              </div>
            </section>
          ))}
        </div>
      )}

      {viewType === 'calendar' && (
        <div className="rounded-md border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] p-4 shadow-sm dark:bg-surface-card">
          <UniversalCalendarView events={calendarEvents} title="Calendario de eventos" />
        </div>
      )}

      {viewType === 'gantt' && (
        <div className="rounded-md border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] p-4 shadow-sm dark:bg-surface-card">
          <UniversalGanttView items={ganttItems} moduleName="Eventos" />
        </div>
      )}

      {viewType === 'wiki' && (
        <section className="rounded-md border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] p-3 shadow-sm dark:bg-surface-card">
          <p className="mb-3 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Wiki de eventos</p>
          <textarea
            value={wikiNotes}
            onChange={(event) => onWikiNotesChange(event.target.value)}
            placeholder="Documenta protocolos, checklist de registro, roles y aprendizajes de cada evento..."
            className="min-h-[360px] w-full rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-muted))] p-4 text-sm font-medium text-[hsl(var(--text-primary))] outline-none focus:ring-2 focus:ring-primary dark:bg-black/20"
          />
        </section>
      )}
    </>
  );
}
