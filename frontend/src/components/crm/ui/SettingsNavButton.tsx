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
          ? "bg-[hsl(var(--surface-2))] text-[hsl(var(--foreground))] font-semibold"
          : "text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] hover:bg-[hsl(var(--surface-1))] font-medium"
      )}
    >
      <div className="flex items-center gap-3">
        <Icon size={14} className={clsx("transition-colors", active ? "text-[hsl(var(--primary))]" : "text-[hsl(var(--muted-foreground))] group-hover:text-[hsl(var(--foreground))]")} />
        <span className="text-xs">{label}</span>
      </div>
    </button>
  );
}
