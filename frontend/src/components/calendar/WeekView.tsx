'use client';

import React, { useCallback, useMemo } from 'react';
import { format, isToday } from 'date-fns';
import { es } from 'date-fns/locale';
import clsx from 'clsx';
import InlineEventPopover from '@/components/calendar/InlineEventPopover';
import { CalEvent, EVENT_TYPE_META, HOURS, HOUR_HEIGHT, minutesToTop, formatHour } from '@/types/calendar';
import type { ViewMode } from '@/types/calendar';

interface WeekViewProps {
  weekDays: Date[];
  visibleEvents: CalEvent[];
  viewColor: string;
  nowLine: number;
  openPopoverDay: string | null;
  onOpenPopover: (day: string | null) => void;
  onSave: (data: { title: string; type: 'event' | 'task'; description: string; location: string; date: Date }) => Promise<void>;
  onEventClick: (event: CalEvent) => void;
}

export default function WeekView({
  weekDays, visibleEvents, viewColor, nowLine, openPopoverDay,
  onOpenPopover, onSave, onEventClick,
}: WeekViewProps) {
  const getEventsForDay = useCallback(
    (day: Date) => visibleEvents.filter(e => {
      const d = new Date(e.start);
      return d.getFullYear() === day.getFullYear() && d.getMonth() === day.getMonth() && d.getDate() === day.getDate();
    }),
    [visibleEvents],
  );

  const getAllDayForDay = useCallback(
    (day: Date) => getEventsForDay(day).filter(e => e.allDay),
    [getEventsForDay],
  );

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Day headers */}
      <div className="flex shrink-0 border-b border-[hsl(var(--border))] dark:border-white/5">
        <div className="w-16 shrink-0" />
        {weekDays.map((day, i) => (
          <div key={i} className="flex-1 min-w-0 flex flex-col items-center py-2 border-l border-[hsl(var(--border))] dark:border-white/5 first:border-l-0">
            <span className="text-2xs font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide">
              {format(day, 'EEE', { locale: es })}
            </span>
            <span className={clsx(
              'size-8 flex items-center justify-center rounded-full text-sm font-bold mt-0.5',
              isToday(day)
                ? 'text-white shadow-lg'
                : 'text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5',
            )}
              style={isToday(day) ? { backgroundColor: viewColor } : {}}
            >
              {format(day, 'd')}
            </span>
          </div>
        ))}
      </div>

      {/* All-day row */}
      <div className="flex shrink-0 border-b border-[hsl(var(--border))] dark:border-white/5 min-h-[28px]">
        <div className="w-16 shrink-0 flex items-center justify-end pr-2">
          <span className="text-2xs text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] font-bold">Todo el día</span>
        </div>
        {weekDays.map((day, i) => {
          const dayAllDay = getAllDayForDay(day);
          return (
            <div key={i} className="flex-1 border-l border-[hsl(var(--border))] dark:border-white/5 px-1 py-0.5 first:border-l-0">
              {dayAllDay.map(e => (
                <div
                  key={e.id}
                  onClick={() => onEventClick(e)}
                  className="truncate cursor-pointer rounded px-1.5 py-0.5 text-white mb-0.5"
                  style={{ backgroundColor: e.color }}
                >
                  <div className="flex items-center gap-1">
                    <span className="text-2xs font-semibold uppercase tracking-wide opacity-80">
                      {EVENT_TYPE_META[e.type].label}
                    </span>
                    <span className="truncate text-2xs font-bold">{e.title}</span>
                  </div>
                </div>
              ))}
            </div>
          );
        })}
      </div>

      {/* Timed grid */}
      <div className="flex-1 overflow-y-auto scrollbar-thin">
        <div className="flex" style={{ height: HOUR_HEIGHT * 24 }}>
          <div className="w-16 shrink-0 relative">
            {HOURS.map(h => (
              <div key={h} className="absolute left-0 right-0 flex items-start justify-end pr-3"
                style={{ top: h * HOUR_HEIGHT - 7 }}>
                {h > 0 && <span className="text-2xs text-[hsl(var(--text-secondary))] font-bold">{formatHour(h)}</span>}
              </div>
            ))}
          </div>
          {weekDays.map((day, i) => (
            <div key={i} className="flex-1 border-l border-[hsl(var(--border))] dark:border-white/5 relative cursor-pointer first:border-l-0">
              {HOURS.map(h => (
                <div key={h} className="absolute left-0 right-0 border-t border-[hsl(var(--border))] dark:border-white/[0.04]"
                  style={{ top: h * HOUR_HEIGHT }} />
              ))}
              {isToday(day) && (
                <div className="absolute left-0 right-0 z-10 pointer-events-none" style={{ top: nowLine }}>
                  <div className="flex items-center">
                    <div className="size-2.5 rounded-full -ml-1.5 shrink-0" style={{ backgroundColor: viewColor }} />
                    <div className="flex-1 h-px" style={{ backgroundColor: viewColor }} />
                  </div>
                </div>
              )}
              <InlineEventPopover
                open={openPopoverDay === format(day, 'yyyy-MM-dd')}
                onOpenChange={(open) => onOpenPopover(open ? format(day, 'yyyy-MM-dd') : null)}
                day={day}
                onSave={onSave}
              >
                <div className="absolute inset-0">
                  {getEventsForDay(day).filter(e => !e.allDay).map(e => {
                    const top = minutesToTop(e.start);
                    const h = Math.max(24, ((e.end?.getTime() ?? e.start.getTime() + 3600000) - e.start.getTime()) / 60000 * (HOUR_HEIGHT / 60));
                    return (
                      <div key={e.id}
                        onClick={(evt) => { evt.stopPropagation(); onEventClick(e); }}
                        className="absolute left-1 right-1 rounded-lg px-2 py-1 overflow-hidden cursor-pointer hover:brightness-95 transition-all z-20 shadow-sm"
                        style={{ top, height: h, backgroundColor: e.color + '20', borderLeft: `3px solid ${e.color}` }}
                      >
                        <p className="text-2xs font-bold truncate" style={{ color: e.color }}>
                          {format(e.start, 'h:mm a')} · {e.title}
                        </p>
                        {e.location && (
                          <p className="text-2xs truncate opacity-60" style={{ color: e.color }}>{e.location}</p>
                        )}
                      </div>
                    );
                  })}
                </div>
              </InlineEventPopover>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
