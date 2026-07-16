"use client";

import React, { useState } from "react";
import * as Popover from "@radix-ui/react-popover";
import clsx from "clsx";
import { Check, ChevronDown } from "lucide-react";

export type ProjectStatus = "planning" | "active" | "on_hold" | "completed" | "archived";

export const PROJECT_STATUS_LABELS: Record<ProjectStatus, string> = {
  planning: "Planificación",
  active: "En Marcha",
  on_hold: "En Pausa",
  completed: "Alcanzado",
  archived: "Archivado",
};

const PROJECT_STATUS_OPTIONS: ProjectStatus[] = ["planning", "active", "on_hold", "completed", "archived"];

const STATUS_STYLES: Record<ProjectStatus, { dot: string; bg: string; text: string; border: string }> = {
  planning: {
    dot: "bg-[hsl(var(--text-secondary))]",
    bg: "bg-[hsl(var(--surface-2))] dark:bg-white/5",
    text: "text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]",
    border: "border-[hsl(var(--border))] dark:border-white/10",
  },
  active: {
    dot: "bg-[hsl(var(--primary))]",
    bg: "bg-blue-100 dark:bg-blue-500/20",
    text: "text-[hsl(var(--primary))] dark:text-blue-300",
    border: "border-blue-200 dark:border-blue-500/30",
  },
  on_hold: {
    dot: "bg-amber-500",
    bg: "bg-amber-100 dark:bg-amber-500/20",
    text: "text-amber-700 dark:text-amber-300",
    border: "border-amber-200 dark:border-amber-500/30",
  },
  completed: {
    dot: "bg-emerald-500",
    bg: "bg-emerald-100 dark:bg-emerald-500/20",
    text: "text-emerald-700 dark:text-emerald-300",
    border: "border-emerald-200 dark:border-emerald-500/30",
  },
  archived: {
    dot: "bg-slate-500",
    bg: "bg-slate-100 dark:bg-slate-500/20",
    text: "text-slate-700 dark:text-slate-300",
    border: "border-slate-200 dark:border-slate-500/30",
  },
};

interface InlineProjectStatusPickerProps {
  value: ProjectStatus | string;
  onChange: (value: ProjectStatus) => void;
  disabled?: boolean;
  size?: "sm" | "md";
}

export function InlineProjectStatusPicker({ value, onChange, disabled, size = "md" }: InlineProjectStatusPickerProps) {
  const [open, setOpen] = useState(false);
  const status = (PROJECT_STATUS_OPTIONS.includes(value as ProjectStatus) ? value : "planning") as ProjectStatus;
  const cfg = STATUS_STYLES[status];

  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger asChild>
        <button
          disabled={disabled}
          onClick={(e) => e.stopPropagation()}
          className={clsx(
            "flex items-center gap-1.5 rounded-md border font-semibold transition-all",
            size === "sm" ? "px-2 py-0.5 text-[10px]" : "px-2.5 py-1 text-[11px]",
            cfg.bg,
            cfg.text,
            cfg.border,
            "hover:brightness-95 dark:hover:brightness-110",
            disabled && "opacity-50 cursor-not-allowed"
          )}
          aria-label="Cambiar estado del proyecto"
        >
          <span className={clsx("size-1.5 rounded-full shrink-0", cfg.dot)} />
          {PROJECT_STATUS_LABELS[status]}
          <ChevronDown size={size === "sm" ? 9 : 10} className="opacity-60" />
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          className="z-[500] min-w-[180px] bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-secondary))] rounded-md shadow-2xl border border-[hsl(var(--border))]/80 dark:border-white/10 p-1.5"
          sideOffset={6}
          align="start"
          onOpenAutoFocus={(e) => e.preventDefault()}
        >
          <p className="text-[9px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] px-2 pt-1 pb-2">
            Estado del proyecto
          </p>
          {PROJECT_STATUS_OPTIONS.map((s) => {
            const style = STATUS_STYLES[s];
            return (
              <button
                key={s}
                onClick={() => {
                  onChange(s);
                  setOpen(false);
                }}
                className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 transition-colors"
              >
                <span className={clsx("size-2 rounded-full shrink-0", style.dot)} />
                <span className="text-[12px] font-semibold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] flex-1 text-left">
                  {PROJECT_STATUS_LABELS[s]}
                </span>
                {status === s && <Check size={12} className="text-[hsl(var(--primary))]" />}
              </button>
            );
          })}
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
