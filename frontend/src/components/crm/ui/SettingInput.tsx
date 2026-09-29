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
      <label className="text-xs font-bold text-[hsl(var(--muted-foreground))] uppercase tracking-wide pl-1">{label}</label>
      <input
        type={type}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        className="w-full bg-[hsl(var(--surface-1))] hover:bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-md px-4 py-2.5 text-xs font-medium text-[hsl(var(--foreground))] outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]/30 transition-all placeholder:text-[hsl(var(--muted-foreground))] disabled:opacity-50"
      />
    </div>
  );
}
