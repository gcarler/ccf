'use client';

import React, { ElementType } from 'react';

interface QuickStatProps {
  label: string;
  value: any;
  icon: ElementType;
  color: string;
}

export default function QuickStat({ label, value, icon: Icon, color }: QuickStatProps) {
  return (
    <div className="px-4 py-2 bg-slate-50 dark:bg-black/20 rounded-lg flex items-center gap-4 border border-slate-100 dark:border-white/5 min-w-[180px]">
      <Icon size={20} className={color} />
      <div>
        <p className="text-[9px] font-bold text-slate-400 uppercase tracking-wide">{label}</p>
        <p className="text-sm font-bold text-slate-800 dark:text-white leading-none mt-1">{value ?? '—'}</p>
      </div>
    </div>
  );
}
