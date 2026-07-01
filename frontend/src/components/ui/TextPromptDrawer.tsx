"use client";

import React from "react";
import WorkspaceDrawer from "@/components/WorkspaceDrawer";

interface TextPromptDrawerProps {
  isOpen: boolean;
  title: string;
  subtitle?: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  onClose: () => void;
  onSubmit: () => void;
  placeholder?: string;
  submitLabel?: string;
  cancelLabel?: string;
  inputType?: React.HTMLInputTypeAttribute;
}

export default function TextPromptDrawer({
  isOpen,
  title,
  subtitle,
  label,
  value,
  onChange,
  onClose,
  onSubmit,
  placeholder,
  submitLabel = "Guardar",
  cancelLabel = "Cancelar",
  inputType = "text",
}: TextPromptDrawerProps) {
  return (
    <WorkspaceDrawer
      isOpen={isOpen}
      onClose={onClose}
      title={title}
      subtitle={subtitle}
      actions={
        <>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md border border-[hsl(var(--border))] px-4 py-2 text-xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={onSubmit}
            className="rounded-md bg-[hsl(var(--primary))] px-4 py-2 text-xs font-semibold uppercase tracking-wide text-white"
          >
            {submitLabel}
          </button>
        </>
      }
    >
      <div className="space-y-3">
        <label className="block text-xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
          {label}
        </label>
        <input
          type={inputType}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="w-full rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] px-4 py-3 text-sm text-[hsl(var(--text-primary))] outline-none focus:border-[hsl(var(--primary))]"
          autoFocus
        />
      </div>
    </WorkspaceDrawer>
  );
}
