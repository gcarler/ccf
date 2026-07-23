"use client";

import React, { useEffect, useRef, useState } from "react";
import * as Popover from "@radix-ui/react-popover";
import clsx from "clsx";
import { AlertCircle, Calendar, ChevronDown, ChevronLeft } from "lucide-react";

const DAYS_ES = ["Do", "Lu", "Ma", "Mi", "Ju", "Vi", "Sa"];
const MONTHS_ES = [
  "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
  "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
];

function getDaysInMonth(year: number, month: number) {
  return new Date(year, month + 1, 0).getDate();
}

function getFirstDay(year: number, month: number) {
  return new Date(year, month, 1).getDay();
}

function formatRelative(date: Date): string {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const d = new Date(date);
  d.setHours(0, 0, 0, 0);
  const diff = Math.round((d.getTime() - today.getTime()) / 86400000);
  if (diff === 0) return "Hoy";
  if (diff === 1) return "Mañana";
  if (diff === -1) return "Ayer";
  if (diff < 0) return d.toLocaleDateString("es-PE", { day: "2-digit", month: "short" });
  if (diff <= 7) return `En ${diff}d`;
  return d.toLocaleDateString("es-PE", { day: "2-digit", month: "short" });
}

function toDateKey(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

interface InlineDatePickerProps {
  value?: string | null;
  onChange: (value: string | null) => void;
  disabled?: boolean;
}

export function InlineDatePicker({ value, onChange, disabled }: InlineDatePickerProps) {
  const [open, setOpen] = useState(false);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const parsed = value ? new Date(value + "T00:00:00") : null;
  const safeYear = parsed && !isNaN(parsed.getTime()) ? parsed.getFullYear() : today.getFullYear();
  const safeMonth = parsed && !isNaN(parsed.getTime()) ? parsed.getMonth() : today.getMonth();
  const [viewYear, setViewYear] = useState(safeYear);
  const [viewMonth, setViewMonth] = useState(safeMonth);

  // Tracks the last month/year the user navigated to manually via the chevron
  // buttons. If ``true``, an external ``value`` change won't clobber the
  // user's visible month — they explicitly chose it.
  const userTouchedViewRef = useRef<boolean>(false);

  // Sync the visible calendar month/year whenever the externally-provided value
  // changes (e.g. after a successful PATCH refresh) — but only if the user
  // hasn't manually navigated since the picker was opened. This avoids
  // yanking the calendar back when the user clicks "next month" and a
  // background refresh arrives.
  useEffect(() => {
    if (!value || userTouchedViewRef.current) return;
    const d = new Date(value + "T00:00:00");
    if (!isNaN(d.getTime())) {
      setViewYear(d.getFullYear());
      setViewMonth(d.getMonth());
    }
  }, [value]);

  // Reset the "user touched" flag whenever the popover (re-)opens so that the
  // first display starts on the value's month.
  useEffect(() => {
    if (open) userTouchedViewRef.current = false;
  }, [open]);

  const stepMonth = (delta: number) => {
    userTouchedViewRef.current = true;
    let m = viewMonth + delta;
    let y = viewYear;
    if (m > 11) { m = 0; y++; }
    else if (m < 0) { m = 11; y--; }
    setViewMonth(m);
    setViewYear(y);
  };

  const isOverdue = parsed && !isNaN(parsed.getTime()) && parsed < today;
  const isToday2 = parsed && !isNaN(parsed.getTime()) && parsed.toDateString() === today.toDateString();
  const label = parsed && !isNaN(parsed.getTime()) ? formatRelative(parsed) : null;

  const rawFD = getFirstDay(viewYear, viewMonth);
  const firstDay = isNaN(rawFD) ? 0 : Math.max(0, Math.min(6, rawFD));
  const daysCount = Math.max(0, getDaysInMonth(viewYear, viewMonth));
  const cells: (number | null)[] = [
    ...Array(firstDay).fill(null),
    ...Array.from({ length: daysCount }, (_, i) => i + 1),
  ];

  const selectDate = (date: Date) => {
    onChange(toDateKey(date));
    setOpen(false);
  };

  const selectDay = (day: number) => {
    selectDate(new Date(viewYear, viewMonth, day));
  };

  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger asChild>
        <button
          disabled={disabled}
          onClick={(e) => e.stopPropagation()}
          className={clsx(
            "group flex items-center gap-1.5 px-2 py-1 rounded-lg text-[12px] font-medium whitespace-nowrap transition-all",
            "hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5",
            open && "bg-[hsl(var(--surface-1))] dark:bg-white/5 ring-1 ring-[hsl(var(--border))] dark:ring-white/10",
            isOverdue ? "text-danger" : isToday2 ? "text-warning" : label ? "text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]" : "text-[hsl(var(--text-secondary))] dark:text-white/20",
            disabled && "opacity-50 cursor-not-allowed"
          )}
          aria-label="Seleccionar fecha límite"
        >
          {isOverdue ? <AlertCircle size={13} className="shrink-0" /> : <Calendar size={13} className="shrink-0" />}
          {label ?? <span className="group-hover:text-[hsl(var(--text-secondary))] transition-colors">—</span>}
          <ChevronDown size={10} className="opacity-60" />
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          className="z-[500] w-[248px] bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-secondary))] rounded-lg shadow-2xl border border-[hsl(var(--border))]/80 dark:border-white/10 p-3 select-none"
          sideOffset={6}
          align="start"
          onOpenAutoFocus={(e) => e.preventDefault()}
        >
          <div className="flex items-center justify-between mb-3">
            <button
              onClick={() => stepMonth(-1)}
              className="p-1 rounded-lg hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 text-[hsl(var(--text-secondary))]"
            >
              <ChevronLeft size={14} />
            </button>
            <span className="text-[12px] font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">
              {MONTHS_ES[viewMonth]} {viewYear}
            </span>
            <button
              onClick={() => stepMonth(1)}
              className="p-1 rounded-lg hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 text-[hsl(var(--text-secondary))]"
            >
              <ChevronDown size={14} />
            </button>
          </div>
          <div className="grid grid-cols-7 mb-1">
            {DAYS_ES.map((d) => (
              <div key={d} className="text-[9px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] text-center py-0.5">
                {d}
              </div>
            ))}
          </div>
          <div className="grid grid-cols-7 gap-y-0.5">
            {cells.map((day, i) => {
              if (!day) return <div key={`e-${i}`} />;
              const cd = new Date(viewYear, viewMonth, day);
              const isSelected = parsed && !isNaN(parsed.getTime()) && cd.toDateString() === parsed.toDateString();
              const isTodayCell = cd.toDateString() === today.toDateString();
              const isPast = cd < today && !isTodayCell;
              return (
                <button
                  key={day}
                  onClick={() => selectDay(day)}
                  className={clsx(
                    "size-8 rounded-lg text-[12px] font-medium transition-all mx-auto flex items-center justify-center",
                    isSelected
                      ? "bg-[hsl(var(--primary))] text-white font-bold shadow-sm"
                      : isTodayCell
                      ? "bg-info-soft text-info-text font-bold ring-1 ring-info/30"
                      : isPast
                      ? "text-[hsl(var(--text-secondary))] dark:text-white/20 hover:bg-[hsl(var(--surface-1))]"
                      : "text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5"
                  )}
                >
                  {day}
                </button>
              );
            })}
          </div>
          <div className="flex items-center gap-2 mt-3 pt-2 border-t border-[hsl(var(--border))] dark:border-white/5">
            <button
              onClick={() => {
                setViewYear(today.getFullYear());
                setViewMonth(today.getMonth());
                selectDate(today);
              }}
              className="flex-1 text-[11px] font-bold text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] py-1.5 rounded-lg hover:bg-[hsl(var(--info-muted))] dark:hover:bg-[hsl(var(--info)/0.1)] transition-colors"
            >
              Hoy
            </button>
            {value && (
              <button
                onClick={() => {
                  onChange(null);
                  setOpen(false);
                }}
                className="flex-1 text-[11px] font-bold text-danger py-1.5 rounded-lg hover:bg-[hsl(var(--danger-muted))] dark:hover:bg-[hsl(var(--danger)/0.1)] transition-colors"
              >
                Quitar
              </button>
            )}
          </div>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
