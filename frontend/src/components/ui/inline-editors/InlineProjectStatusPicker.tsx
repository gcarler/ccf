"use client";

import React, { useState } from "react";
import * as Popover from "@radix-ui/react-popover";
import clsx from "clsx";
import { Check, ChevronDown } from "lucide-react";
import { PROJECT_STATUSES, type ProjectStatus } from "@/lib/projects/constants";

// Re-export so existing `import { ProjectStatus } from '.../InlineProjectStatusPicker'`
// keeps compiling. Prefer importing from `@/lib/projects/constants` directly.
export type { ProjectStatus };

// Visual labels stay local — the dashboard header prefers friendlier Spanish
// ("En Marcha", "Alcanzado") than the canonical constants. Wire format lives
// in the enum; display copy stays per-component until a visible-only-i18n
// layer lands.
const PROJECT_STATUS_LABELS: Record<ProjectStatus, string> = {
  planning: "Planificación",
  active: "En Marcha",
  on_hold: "En Pausa",
  completed: "Alcanzado",
  archived: "Archivado",
};

const PROJECT_STATUS_OPTIONS: readonly ProjectStatus[] = PROJECT_STATUSES;

const STATUS_STYLES: Record<ProjectStatus, { dot: string; bg: string; text: string; border: string }> = {
  planning: {
    dot: "bg-[hsl(var(--text-secondary))]",
    bg: "bg-[hsl(var(--surface-2))] dark:bg-white/5",
    text: "text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]",
    border: "border-[hsl(var(--border))] dark:border-white/10",
  },
  active: {
    dot: "bg-info",
    bg: "bg-info-soft",
    text: "text-info-text",
    border: "border-info-muted dark:border-info/30",
  },
  on_hold: {
    dot: "bg-warning",
    bg: "bg-warning-soft",
    text: "text-warning-text",
    border: "border-warning-muted dark:border-warning/30",
  },
  completed: {
    dot: "bg-success",
    bg: "bg-success-soft",
    text: "text-success-text",
    border: "border-success-muted dark:border-success/30",
  },
  archived: {
    dot: "bg-[hsl(var(--text-secondary))]",
    bg: "bg-[hsl(var(--surface-2))] dark:bg-white/5",
    text: "text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]",
    border: "border-[hsl(var(--border))] dark:border-white/10",
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
