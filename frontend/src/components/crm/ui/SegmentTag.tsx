'use client';

import React from 'react';
import clsx from 'clsx';

interface SegmentTagProps {
  label: string;
  active: boolean;
  onClick: () => void;
  disabled?: boolean;
}

export default function SegmentTag({ label, active, onClick, disabled }: SegmentTagProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={clsx(
        "py-1.5 px-4 rounded-lg text-xs font-bold uppercase tracking-wider text-left transition-all border disabled:opacity-50",
        active
          ? "bg-[hsl(var(--primary))] border-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] shadow-md"
          : "bg-[hsl(var(--surface-1))] border-[hsl(var(--border))] text-[hsl(var(--muted-foreground))] hover:border-[hsl(var(--primary)/0.4)]"
      )}
    >
      {label}
    </button>
  );
}
