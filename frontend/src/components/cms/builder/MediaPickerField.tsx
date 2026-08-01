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
        <label className="text-xs font-semibold text-gray-700 dark:text-gray-300">
          {label}
        </label>
      )}
      <div className="flex items-center gap-2">
        {value && (
          <img
            src={value}
            alt="Vista previa"
            className="w-10 h-10 object-cover rounded border border-gray-200 dark:border-white/10 shrink-0"
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
          className="px-2.5 py-1 bg-gray-100 hover:bg-gray-200 dark:bg-white/5 dark:hover:bg-white/10 text-xs font-semibold rounded border border-gray-300 dark:border-white/10 text-gray-800 dark:text-gray-200 transition-colors"
        >
          {value ? "Cambiar Imagen" : "Seleccionar Imagen"}
        </button>
        {value && (
          <button
            type="button"
            onClick={() => onChange("")}
            className="px-2 py-1 text-xs text-red-600 hover:text-red-700 dark:text-red-400 font-medium transition-colors"
            title="Quitar imagen"
          >
            Quitar
          </button>
        )}
      </div>
      {value && (
        <span className="text-3xs text-gray-500 truncate max-w-[200px]" title={value}>
          {value}
        </span>
      )}
    </div>
  );
}
