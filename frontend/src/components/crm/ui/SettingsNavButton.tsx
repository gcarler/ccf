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
          ? "bg-slate-100 dark:bg-white/10 text-slate-900 dark:text-white font-semibold"
          : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 hover:bg-slate-50 dark:hover:bg-white/5 font-medium"
      )}
    >
      <div className="flex items-center gap-3">
        <Icon size={14} className={clsx("transition-colors", active ? "text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]" : "text-slate-400 group-hover:text-slate-500")} />
        <span className="text-xs">{label}</span>
      </div>
    </button>
  );
}
