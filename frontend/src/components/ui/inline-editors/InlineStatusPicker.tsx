"use client";

import React, { useMemo, useState } from "react";
import * as Popover from "@radix-ui/react-popover";
import clsx from "clsx";
import { Check, ChevronDown } from "lucide-react";
import { buildStatusOptions } from "@/lib/projects/constants";
import type { PhaseDef } from "@/context/ProjectUpdateContext";

interface InlineStatusPickerProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  size?: "sm" | "md";
  /** Dynamic project phases; overrides the 4 canonical slugs when provided. */
  phases?: PhaseDef[];
}

export function InlineStatusPicker({ value, onChange, disabled, size = "md", phases }: InlineStatusPickerProps) {
  const [open, setOpen] = useState(false);
  const options = useMemo(() => buildStatusOptions(phases), [phases]);
  const cfg = options.find((s) => s.value === value) ?? options[0];

  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger asChild>
        <button
          disabled={disabled}
          onClick={(e) => e.stopPropagation()}
          className={clsx(
            "flex items-center gap-1.5 rounded-md border font-semibold transition-all",
            size === "sm" ? "px-2 py-0.5 text-2xs" : "px-2.5 py-1 text-xs",
            cfg.bg,
            cfg.text,
            cfg.border,
            "hover:brightness-95 dark:hover:brightness-110",
            disabled && "opacity-50 cursor-not-allowed"
          )}
          aria-label="Cambiar estado"
        >
          <span className={clsx("size-1.5 rounded-full shrink-0", cfg.dot)} style={cfg.dotStyle} />
          {cfg.label}
          <ChevronDown size={size === "sm" ? 9 : 10} className="opacity-60" />
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          className="z-[500] min-w-[180px] bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-secondary))] rounded-md shadow-2xl border border-[hsl(var(--border))]/80 dark:border-[hsl(var(--border))] p-1.5"
          sideOffset={6}
          align="start"
          onOpenAutoFocus={(e) => e.preventDefault()}
        >
          <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] px-2 pt-1 pb-2">
            Estado
          </p>
          {options.map((s) => (
            <button
              key={s.value}
              onClick={() => {
                onChange(s.value);
                setOpen(false);
              }}
              className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg hover:bg-[hsl(var(--surface-1))] dark:hover:bg-[hsl(var(--surface-2))] transition-colors"
            >
              <span className={clsx("size-2 rounded-full shrink-0", s.dot)} style={s.dotStyle} />
              <span className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] flex-1 text-left">
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
