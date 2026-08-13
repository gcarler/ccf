"use client";

import React, { useState } from "react";
import MediaPicker from "@/components/cms/builder/MediaPicker";

interface CmsMediaUrlFieldProps {
  label: string;
  value: string;
  token?: string | null;
  disabled?: boolean;
  onChange: (url: string) => void;
}

export default function CmsMediaUrlField({
  label,
  value,
  token,
  disabled = false,
  onChange,
}: CmsMediaUrlFieldProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className="space-y-1.5">
      <label className="text-xs font-medium text-[hsl(var(--text-secondary))]">{label}</label>
      <div className="flex gap-2">
        <input
          type="url"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          disabled={disabled}
          placeholder="https://... o selecciona desde la biblioteca"
          className="min-w-0 flex-1 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] px-3 py-2 text-sm dark:border-white/10 dark:bg-[hsl(var(--admin-bg-secondary))]"
        />
        <button
          type="button"
          onClick={() => setOpen(true)}
          disabled={disabled || !token}
          className="shrink-0 rounded-md bg-[hsl(var(--primary))] px-3 py-2 text-xs font-semibold text-white transition-colors hover:bg-[hsl(var(--primary-hover))] disabled:cursor-not-allowed disabled:opacity-50"
        >
          Biblioteca
        </button>
      </div>
      {value && (
        <div className="overflow-hidden rounded-md border border-[hsl(var(--border))] dark:border-white/10">
          <img src={value} alt="Vista previa" className="max-h-40 w-full object-cover" />
        </div>
      )}
      {open && (
        <MediaPicker
          open
          token={token}
          selectedUrl={value}
          onClose={() => setOpen(false)}
          onSelect={(item) => {
            const url = typeof item === "string" ? item : item?.url || "";
            onChange(url);
            setOpen(false);
          }}
        />
      )}
    </div>
  );
}
