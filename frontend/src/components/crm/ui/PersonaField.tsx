'use client';

import React from 'react';

interface PersonaFieldProps {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  type?: string;
  required?: boolean;
}

export default function PersonaField({ label, value, onChange, placeholder, type = 'text', required = false }: PersonaFieldProps) {
  return (
    <div className="space-y-2">
      <label className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{label}</label>
      <input
        required={required}
        type={type}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-4 py-1.5 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-white/10 dark:bg-black/20 dark:text-white"
      />
    </div>
  );
}
