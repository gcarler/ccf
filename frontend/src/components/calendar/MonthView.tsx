"use client";

import React, { useState, useMemo } from 'react';
import clsx from 'clsx';
import {
  format,
  startOfWeek,
  startOfMonth,
  endOfWeek,
  endOfMonth,
  eachDayOfInterval,
  isSameDay,
  isSameMonth,
  isToday,
} from 'date-fns';
import InlineEventPopover from '@/components/calendar/InlineEventPopover';
import { CalEvent, EVENT_TYPE_META } from '@/types/calendar';

interface MonthViewProps {
  currentDate: Date;
  events: CalEvent[];
  onSave?: (data: any) => void;
  onEventClick: (event: CalEvent) => void;
}

export default function MonthView({ currentDate, events, onSave, onEventClick }: MonthViewProps) {
  const [openPopoverDay, setOpenPopoverDay] = useState<string | null>(null);

  const days = useMemo(() => {
    const start = startOfWeek(startOfMonth(currentDate), { weekStartsOn: 0 });
    const end = endOfWeek(endOfMonth(currentDate), { weekStartsOn: 0 });
    return eachDayOfInterval({ start, end });
  }, [currentDate]);

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Day of week headers */}
      <div className="grid grid-cols-7 shrink-0 border-b border-slate-100 dark:border-white/5">
        {['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'].map(d => (
          <div
            key={d}
            className="py-2.5 text-center text-[10px] font-semibold uppercase tracking-wide text-slate-400"
          >
            {d}
          </div>
        ))}
      </div>
      {/* Day cells */}
      <div className="flex-1 grid grid-cols-7 overflow-y-auto scrollbar-hide">
        {days.map((day, idx) => {
          const dayEvents = events.filter(e => isSameDay(e.start, day));
          const inMonth = isSameMonth(day, currentDate);
          const dayKey = format(day, 'yyyy-MM-dd');
          return (
            <InlineEventPopover
              key={idx}
              open={openPopoverDay === dayKey}
              onOpenChange={(open) => setOpenPopoverDay(open ? dayKey : null)}
              day={day}
              onSave={onSave}
            >
              <div
                className={clsx(
                  'min-h-[100px] p-2 border-r border-b border-slate-100 dark:border-white/5 group transition-colors cursor-pointer hover:bg-slate-50/50 dark:hover:bg-white/[0.02]',
                  !inMonth && 'opacity-30',
                  openPopoverDay === dayKey && 'ring-2 ring-inset ring-blue-500/50'
                )}
              >
                <span
                  className={clsx(
                    'inline-flex size-6 items-center justify-center rounded-full text-[11px] font-bold transition-all',
                    isToday(day)
                      ? 'bg-[hsl(var(--primary))] text-white shadow-sm shadow-blue-400'
                      : 'text-slate-500 dark:text-slate-400 group-hover:text-slate-800 dark:group-hover:text-white'
                  )}
                >
                  {format(day, 'd')}
                </span>
                {dayEvents.slice(0, 2).map(e => (
                  <div
                    key={e.id}
                    onClick={(evt) => { evt.stopPropagation(); onEventClick(e); }}
                    className="truncate cursor-pointer rounded px-1 py-0.5 text-white mt-1"
                    style={{ backgroundColor: e.color }}
                  >
                    <div className="flex items-center gap-1">
                      <span className="text-[7px] font-semibold uppercase tracking-wide opacity-80">
                        {EVENT_TYPE_META[e.type].label}
                      </span>
                      <span className="truncate text-[9px] font-bold">{e.title}</span>
                    </div>
                  </div>
                ))}
                {dayEvents.length > 2 && (
                  <span className="text-[9px] text-slate-400 font-bold pl-0.5">
                    +{dayEvents.length - 2} más
                  </span>
                )}
              </div>
            </InlineEventPopover>
          );
        })}
      </div>
    </div>
  );
}
