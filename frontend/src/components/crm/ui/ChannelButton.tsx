'use client';

import React, { ElementType } from 'react';
import clsx from 'clsx';

interface ChannelButtonProps {
  active: boolean;
  onClick: () => void;
  icon: ElementType;
  label: string;
  disabled?: boolean;
}

export default function ChannelButton({ active, onClick, icon: Icon, label, disabled }: ChannelButtonProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={clsx(
        "flex items-center gap-2.5 px-4 py-2.5 rounded-md text-[10px] font-bold uppercase tracking-wide transition-all disabled:opacity-50",
        active ? "bg-[hsl(var(--surface-1))] dark:bg-[hsl(var(--primary))] text-[hsl(var(--primary))] dark:text-white shadow-xl shadow-blue-500/10" : "text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))]"
      )}
    >
      <Icon size={14} /> {label}
    </button>
  );
}
