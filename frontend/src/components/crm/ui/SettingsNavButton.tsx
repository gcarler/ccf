'use client';

import React, { ElementType } from 'react';
import clsx from 'clsx';

interface SettingsNavButtonProps {
  active: boolean;
  onClick: () => void;
  icon: ElementType;
  label: string;
}

export default function SettingsNavButton({ active, onClick, icon: Icon, label }: SettingsNavButtonProps) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        "w-full flex items-center justify-between px-3 py-2 rounded-lg transition-colors group",
        active
          ? "bg-[hsl(var(--surface-2))] dark:bg-white/10 text-[hsl(var(--text-primary))] dark:text-white font-semibold"
          : "text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] dark:hover:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 font-medium"
      )}
    >
      <div className="flex items-center gap-3">
        <Icon size={14} className={clsx("transition-colors", active ? "text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]" : "text-[hsl(var(--text-secondary))] group-hover:text-[hsl(var(--text-secondary))]")} />
        <span className="text-xs">{label}</span>
      </div>
    </button>
  );
}
