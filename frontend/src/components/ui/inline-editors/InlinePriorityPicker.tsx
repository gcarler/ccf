"use client";

import React, { useState } from "react";
import * as Popover from "@radix-ui/react-popover";
import clsx from "clsx";
import { Check, ChevronDown } from "lucide-react";
import { PRIORITY_LABELS, type TaskPriority } from "@/lib/projects/constants";

const PRIORITY_OPTIONS: { value: TaskPriority; label: string; color: string; fill: string }[] = [
  { value: "low", label: PRIORITY_LABELS.low, color: "text-[hsl(var(--text-secondary))]", fill: "hsl(var(--text-secondary))" },
  { value: "medium", label: PRIORITY_LABELS.medium, color: "text-[hsl(var(--primary))]", fill: "hsl(var(--primary))" },
  { value: "high", label: PRIORITY_LABELS.high, color: "text-[hsl(var(--warning))]", fill: "hsl(var(--warning))" },
  { value: "urgent", label: PRIORITY_LABELS.urgent, color: "text-[hsl(var(--danger))]", fill: "hsl(var(--danger))" },
];

const FlagIcon = ({ fill, size = 14 }: { fill: string; size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill={fill} xmlns="http://www.w3.org/2000/svg">
    <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z" />
    <line x1="4" y1="22" x2="4" y2="15" stroke={fill} strokeWidth="2" strokeLinecap="round" />
  </svg>
);

interface InlinePriorityPickerProps {
  value: string;
  onChange: (value: TaskPriority) => void;
  disabled?: boolean;
  size?: "sm" | "md";
}

export function InlinePriorityPicker({ value, onChange, disabled, size = "md" }: InlinePriorityPickerProps) {
  const [open, setOpen] = useState(false);
  const cfg = PRIORITY_OPTIONS.find((p) => p.value === value) ?? PRIORITY_OPTIONS[1];

  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger asChild>
        <button
          disabled={disabled}
          onClick={(e) => e.stopPropagation()}
          className={clsx(
            "flex items-center gap-1.5 rounded-lg font-semibold transition-all",
            size === "sm" ? "px-2 py-0.5 text-[10px]" : "px-2.5 py-1 text-[11px]",
            "hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5",
            disabled && "opacity-50 cursor-not-allowed"
          )}
          aria-label="Cambiar prioridad"
        >
          <FlagIcon fill={cfg.fill} size={size === "sm" ? 11 : 13} />
          <span className={cfg.color}>{cfg.label}</span>
          <ChevronDown size={size === "sm" ? 9 : 10} className="text-[hsl(var(--text-secondary))]" />
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          className="z-[500] min-w-[160px] bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-secondary))] rounded-md shadow-2xl border border-[hsl(var(--border))]/80 dark:border-white/10 p-1.5"
          sideOffset={6}
          align="start"
          onOpenAutoFocus={(e) => e.preventDefault()}
        >
          <p className="text-[9px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] px-2 pt-1 pb-2">
            Prioridad
          </p>
          {PRIORITY_OPTIONS.map((p) => (
            <button
              key={p.value}
              onClick={() => {
                onChange(p.value);
                setOpen(false);
              }}
              className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 transition-colors"
            >
              <FlagIcon fill={p.fill} size={12} />
              <span className={clsx("text-[12px] font-semibold flex-1 text-left", p.color)}>{p.label}</span>
              {value === p.value && <Check size={12} className="text-[hsl(var(--primary))]" />}
            </button>
          ))}
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
