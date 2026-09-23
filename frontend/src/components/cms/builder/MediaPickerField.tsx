"use client";

import React from "react";

// Global coordinator ref to connect static Puck custom fields with the React Page component state
let mediaPickerTriggerRef: ((onChange: (url: string) => void, currentValue: string) => void) | null = null;

export function setMediaPickerTrigger(fn: ((onChange: (url: string) => void, currentValue: string) => void) | null) {
  mediaPickerTriggerRef = fn;
}

export function getMediaPickerTrigger() {
  return mediaPickerTriggerRef;
}

export interface MediaPickerFieldProps {
  label?: string;
  value: string;
  onChange: (url: string) => void;
}

export default function MediaPickerField({ label, value, onChange }: MediaPickerFieldProps) {
  return (
    <div className="flex flex-col gap-1.5 my-2">
      {label && (
        <label className="text-xs font-semibold text-[hsl(var(--foreground))]">
          {label}
        </label>
      )}
      <div className="flex items-center gap-2">
        {value && (
          <img
            src={value}
            alt="Vista previa"
            className="w-10 h-10 object-cover rounded border border-[hsl(var(--border))] shrink-0"
            onError={(e) => {
              (e.target as HTMLElement).style.display = "none";
            }}
          />
        )}
        <button
          type="button"
          onClick={() => {
            if (mediaPickerTriggerRef) {
              mediaPickerTriggerRef(onChange, value || "");
            }
          }}
          className="px-2.5 py-1 bg-[hsl(var(--surface-2))] hover:bg-[hsl(var(--surface-2))]/80 text-xs font-semibold rounded border border-[hsl(var(--border))] text-[hsl(var(--foreground))] transition-colors"
        >
          {value ? "Cambiar Imagen" : "Seleccionar Imagen"}
        </button>
        {value && (
          <button
            type="button"
            onClick={() => onChange("")}
            className="px-2 py-1 text-xs text-[hsl(var(--destructive))] hover:opacity-80 font-medium transition-colors"
            title="Quitar imagen"
          >
            Quitar
          </button>
        )}
      </div>
      {value && (
        <span className="text-3xs text-[hsl(var(--muted-foreground))] truncate max-w-[200px]" title={value}>
          {value}
        </span>
      )}
    </div>
  );
}
