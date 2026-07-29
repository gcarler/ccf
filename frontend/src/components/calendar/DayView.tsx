'use client';

import React, { useCallback, useRef } from 'react';
import { format, isToday } from 'date-fns';
import { es } from 'date-fns/locale';
import clsx from 'clsx';
import InlineEventPopover from '@/components/calendar/InlineEventPopover';
import { CalEvent, EVENT_TYPE_META, HOURS, HOUR_HEIGHT, minutesToTop, formatHour } from '@/types/calendar';

interface DayViewProps {
  currentDate: Date;
  visibleEvents: CalEvent[];
  viewColor: string;
  nowLine: number;
  openPopoverDay: string | null;
  onOpenPopover: (day: string | null) => void;
  onSave: (data: { title: string; type: 'event' | 'task'; description: string; location: string; date: Date }) => Promise<void>;
  onEventClick: (event: CalEvent) => void;
}

export default function DayView({
  currentDate, visibleEvents, viewColor, nowLine, openPopoverDay,
  onOpenPopover, onSave, onEventClick,
}: DayViewProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  const getEventsForDay = useCallback(
    (day: Date) => visibleEvents.filter(e => {
      const d = new Date(e.start);
      return d.getFullYear() === day.getFullYear() && d.getMonth() === day.getMonth() && d.getDate() === day.getDate();
    }),
    [visibleEvents],
  );

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div ref={scrollRef} className="flex-1 overflow-y-auto scrollbar-thin">
        <div className="flex" style={{ height: HOUR_HEIGHT * 24 }}>
          <div className="w-20 shrink-0 relative">
            {HOURS.map(h => (
              <div key={h} className="absolute left-0 right-0 flex items-start justify-end pr-3"
                style={{ top: h * HOUR_HEIGHT - 7 }}>
                {h > 0 && <span className="text-2xs text-[hsl(var(--text-secondary))] font-bold">{formatHour(h)}</span>}
              </div>
            ))}
          </div>
          <InlineEventPopover
            open={openPopoverDay === format(currentDate, 'yyyy-MM-dd')}
            onOpenChange={(open) => onOpenPopover(open ? format(currentDate, 'yyyy-MM-dd') : null)}
            day={currentDate}
            onSave={onSave}
          >
            <div className="flex-1 relative cursor-pointer">
              {HOURS.map(h => (
                <div key={h} className="absolute left-0 right-0 border-t border-[hsl(var(--border))] dark:border-white/[0.04]"
                  style={{ top: h * HOUR_HEIGHT }} />
              ))}
              {isToday(currentDate) && (
                <div className="absolute left-0 right-0 z-10 pointer-events-none" style={{ top: nowLine }}>
                  <div className="flex items-center">
                    <div className="size-2.5 rounded-full -ml-1.5 shrink-0" style={{ backgroundColor: viewColor }} />
                    <div className="flex-1 h-px" style={{ backgroundColor: viewColor }} />
                  </div>
                </div>
              )}
              {getEventsForDay(currentDate).map(e => {
                const top = minutesToTop(e.start);
                const h = Math.max(24, ((e.end?.getTime() ?? e.start.getTime() + 3600000) - e.start.getTime()) / 60000 * (HOUR_HEIGHT / 60));
                return (
                  <div key={e.id}
                    onClick={(evt) => { evt.stopPropagation(); onEventClick(e); }}
                    className="absolute left-1 right-4 rounded-md px-3 py-2 shadow-md cursor-pointer hover:brightness-95 transition-all"
                    style={{ top, height: h, backgroundColor: e.color + '20', borderLeft: `4px solid ${e.color}` }}
                  >
                    <div className="mb-1">
                      <span className={clsx('inline-flex rounded-full px-1.5 py-0.5 text-2xs font-semibold uppercase tracking-wide', EVENT_TYPE_META[e.type].chip)}>
                        {EVENT_TYPE_META[e.type].label}
                      </span>
                    </div>
                    <p className="text-xs font-bold" style={{ color: e.color }}>{e.title}</p>
                    <p className="text-2xs text-[hsl(var(--text-secondary))]">{format(e.start, 'h:mm a')}</p>
                    {e.location && <p className="text-2xs text-[hsl(var(--text-secondary))] mt-0.5">{e.location}</p>}
                  </div>
                );
              })}
            </div>
          </InlineEventPopover>
        </div>
      </div>
    </div>
  );
}
