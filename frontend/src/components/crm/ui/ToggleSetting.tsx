'use client';

import React, { ElementType } from 'react';
import { motion } from 'framer-motion';
import clsx from 'clsx';

interface ToggleSettingProps {
  icon: ElementType;
  color: string;
  title: string;
  desc: string;
  active: boolean;
  onToggle: (active: boolean) => void;
  disabled?: boolean;
}

export default function ToggleSetting({ icon: Icon, color, title, desc, active, onToggle, disabled = false }: ToggleSettingProps) {
  return (
    <div className="flex items-center justify-between p-4 rounded-md bg-slate-50 dark:bg-white/[0.02] border border-slate-100 dark:border-white/5 transition-colors group">
      <div className="flex items-center gap-4">
        <div className={clsx("size-9 rounded-lg flex items-center justify-center shrink-0", color)}>
          <Icon size={16} strokeWidth={2.5} />
        </div>
        <div>
          <h4 className="font-bold text-slate-800 dark:text-white text-xs">{title}</h4>
          <p className="text-[12px] text-slate-500 dark:text-slate-400">{desc}</p>
        </div>
      </div>
      <button
        disabled={disabled}
        onClick={() => !disabled && onToggle(!active)}
        className={clsx(
          "relative inline-flex h-5 w-9 items-center rounded-full transition-all duration-300 outline-none disabled:opacity-50",
          active ? "bg-[hsl(var(--primary))]" : "bg-slate-300 dark:bg-slate-600"
        )}
      >
        <motion.div
          animate={{ x: active ? 18 : 2 }}
          className="size-4 rounded-full bg-[hsl(var(--surface-1))] shadow-sm"
        />
      </button>
    </div>
  );
}
