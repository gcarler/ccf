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
        "py-1.5 px-4 rounded-lg text-[10px] font-bold uppercase tracking-wider text-left transition-all border disabled:opacity-50",
        active
          ? "bg-[hsl(var(--primary))] border-blue-600 text-white shadow-lg shadow-blue-500/20"
          : "bg-[hsl(var(--surface-1))] dark:bg-white/5 border-[hsl(var(--border))] dark:border-white/10 text-[hsl(var(--text-secondary))] hover:border-blue-500/30"
      )}
    >
      {label}
    </button>
  );
}
