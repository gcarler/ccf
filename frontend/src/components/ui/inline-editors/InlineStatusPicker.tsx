"use client";

import React, { useState } from "react";
import * as Popover from "@radix-ui/react-popover";
import clsx from "clsx";
import { Check, ChevronDown } from "lucide-react";
import { STATUS_LABELS, type TaskStatus } from "@/lib/projects/constants";

const STATUS_OPTIONS: { value: TaskStatus; label: string; dot: string; bg: string; text: string; border: string }[] = [
  {
    value: "todo",
    label: STATUS_LABELS.todo,
    dot: "bg-[hsl(var(--surface-3))]",
    bg: "bg-[hsl(var(--surface-2))]",
    text: "text-[hsl(var(--text-secondary))]",
    border: "border-[hsl(var(--border))]",
  },
  {
    value: "in_progress",
    label: STATUS_LABELS.in_progress,
    dot: "bg-[hsl(var(--primary))]",
    bg: "bg-[hsl(var(--info-muted))]",
    text: "text-[hsl(var(--info))]",
    border: "border-[hsl(var(--info))]/30",
  },
  {
    value: "review",
    label: STATUS_LABELS.review,
    dot: "bg-[hsl(var(--warning))]",
    bg: "bg-[hsl(var(--warning-muted))]",
    text: "text-[hsl(var(--warning-text))]",
    border: "border-[hsl(var(--warning))]/30",
  },
  {
    value: "completed",
    label: STATUS_LABELS.completed,
    dot: "bg-[hsl(var(--success))]",
    bg: "bg-[hsl(var(--success-muted))]",
    text: "text-[hsl(var(--success-text))]",
    border: "border-[hsl(var(--success))]/30",
  },
];

interface InlineStatusPickerProps {
  value: string;
  onChange: (value: TaskStatus) => void;
  disabled?: boolean;
  size?: "sm" | "md";
}

export function InlineStatusPicker({ value, onChange, disabled, size = "md" }: InlineStatusPickerProps) {
  const [open, setOpen] = useState(false);
  const cfg = STATUS_OPTIONS.find((s) => s.value === value) ?? STATUS_OPTIONS[0];

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
          aria-label="Cambiar estado"
        >
          <span className={clsx("size-1.5 rounded-full shrink-0", cfg.dot)} />
          {cfg.label}
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
            Estado
          </p>
          {STATUS_OPTIONS.map((s) => (
            <button
              key={s.value}
              onClick={() => {
                onChange(s.value);
                setOpen(false);
              }}
              className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 transition-colors"
            >
              <span className={clsx("size-2 rounded-full shrink-0", s.dot)} />
              <span className="text-[12px] font-semibold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] flex-1 text-left">
                {s.label}
              </span>
              {value === s.value && <Check size={12} className="text-[hsl(var(--primary))]" />}
            </button>
          ))}
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
