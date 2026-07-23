'use client';

import React from 'react';

interface SettingInputProps {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  type?: string;
  disabled?: boolean;
}

export default function SettingInput({ label, value, onChange, placeholder, type = "text", disabled = false }: SettingInputProps) {
  return (
    <div className="space-y-1.5">
      <label className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide pl-1">{label}</label>
      <input
        type={type}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        className="w-full bg-[hsl(var(--surface-1))] hover:bg-[hsl(var(--surface-2))] dark:bg-black/20 dark:hover:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-md px-4 py-2.5 text-xs font-medium text-[hsl(var(--text-primary))] dark:text-white outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]/30 transition-all placeholder:text-[hsl(var(--text-secondary))] disabled:opacity-50"
      />
    </div>
  );
}
