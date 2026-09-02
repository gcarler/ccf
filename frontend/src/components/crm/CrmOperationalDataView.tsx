"use client";

import React from "react";
import { Database, ExternalLink } from "lucide-react";

export type CrmOperationalDataItem = {
  id: string;
  title: string;
  subtitle?: string;
  meta?: string;
  status?: string;
};

export default function CrmOperationalDataView({
  moduleName,
  items,
  onSelect,
}: {
  moduleName: string;
  items: CrmOperationalDataItem[];
  onSelect?: (item: CrmOperationalDataItem) => void;
}) {
  return (
    <section
      aria-label={`${moduleName} vista operativa`}
      className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4 dark:border-white/10 dark:bg-white/[0.03]"
    >
      <div className="mb-4 flex items-center gap-3 border-b border-[hsl(var(--border))] pb-3 dark:border-white/10">
        <div className="flex size-9 items-center justify-center rounded-lg bg-[hsl(var(--info-muted))] text-[hsl(var(--primary))] dark:bg-[hsl(var(--primary)/0.15)]">
          <Database size={18} aria-hidden="true" />
        </div>
        <div>
          <h2 className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white">{moduleName}</h2>
          <p className="text-xs text-[hsl(var(--text-secondary))]">Vista operativa con datos registrados</p>
        </div>
      </div>
      {items.length === 0 ? (
        <p className="py-10 text-center text-sm font-medium text-[hsl(var(--text-secondary))]">
          No hay registros para mostrar.
        </p>
      ) : (
        <div className="grid gap-2 md:grid-cols-2">
          {items.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => onSelect?.(item)}
              disabled={!onSelect}
              className="flex w-full items-center justify-between rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-3 text-left transition-colors hover:border-[hsl(var(--primary)/0.5)] disabled:cursor-default dark:border-white/10 dark:bg-white/[0.02]"
            >
              <span className="min-w-0">
                <span className="block truncate text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-white">{item.title}</span>
                {item.subtitle && <span className="mt-1 block truncate text-xs text-[hsl(var(--text-secondary))]">{item.subtitle}</span>}
                {item.meta && <span className="mt-1 block text-2xs text-[hsl(var(--text-secondary))]">{item.meta}</span>}
              </span>
              {onSelect && <ExternalLink size={15} className="ml-3 shrink-0 text-[hsl(var(--primary))]" aria-hidden="true" />}
            </button>
          ))}
        </div>
      )}
    </section>
  );
}
