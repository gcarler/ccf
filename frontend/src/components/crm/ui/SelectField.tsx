'use client';

import React from 'react';

interface SelectFieldProps {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: string[];
  placeholder?: string;
}

export default function SelectField({ label, value, onChange, options, placeholder }: SelectFieldProps) {
  return (
    <div className="space-y-2">
      <label className="text-[10px] font-bold uppercase tracking-wide text-slate-400">{label}</label>
      <select
        value={value}
        onChange={e => onChange(e.target.value)}
        className="w-full rounded-lg border border-slate-200 bg-slate-50 px-4 py-1.5 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-white/10 dark:bg-black/20 dark:text-white"
      >
        <option value="">{placeholder ?? 'Seleccionar...'}</option>
        {options.map(o => <option key={o} value={o}>{o}</option>)}
      </select>
    </div>
  );
}
