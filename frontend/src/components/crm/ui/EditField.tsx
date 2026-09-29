'use client';

import React from 'react';

interface EditFieldProps {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  type?: string;
}

export default function EditField({ label, value, onChange, placeholder, type = 'text' }: EditFieldProps) {
  return (
    <div className="space-y-2">
      <label className="text-xs font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))]">{label}</label>
      <input
        type={type}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--foreground))] px-4 py-1.5 text-sm font-bold outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]/20"
      />
    </div>
  );
}
