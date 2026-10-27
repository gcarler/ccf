"use client";

/**
 * Barra de Control PMI §4.3 & §4.5 del detalle de proyecto.
 *
 * Extraída de `frontend/src/app/plataforma/projects/[id]/page.tsx` (H-PROJ-UI-01)
 * para que el wiring (lista de acciones + selector de herramientas + métricas)
 * tenga su propia suite Vitest. Consolidación de herramientas (H-PROJ-UI-05):
 * las opciones viven agrupadas en `<optgroup>` — "Módulos del Hub" vs "Acciones
 * directas" — el valor refleja la herramienta activa y no existen botones
 * sueltos por fuera (EVM/Gobernanza ya viven en projectActions).
 */

import { useMemo } from "react";
import clsx from "clsx";

export interface ProjectActionRef {
  key: string;
  label: string;
  variant?: "warning" | "destructive";
}

interface ProjectPMIControlBarProps {
  statusLabel?: string;
  wbsAveragePct?: number;
  wbsPackagesCount?: number;
  actions: ProjectActionRef[];
  /** Key de la herramienta activa del hub, para reflejarla en el selector. */
  activeKey?: string | null;
  onSelectAction: (key: string) => void;
}

/** Acciones directas (fuera del Hub de gestión) que conviven en el menú. */
export const PROJECT_DIRECT_ACTION_KEYS = new Set([
  "whiteboard",
  "phases",
  "settings",
  "delete",
]);

export function isDirectActionKey(key: string): boolean {
  return PROJECT_DIRECT_ACTION_KEYS.has(key);
}

export default function ProjectPMIControlBar({
  statusLabel,
  wbsAveragePct = 0,
  wbsPackagesCount = 0,
  actions,
  activeKey = null,
  onSelectAction,
}: ProjectPMIControlBarProps) {
  // Deduplicación defensiva: nunca renderizar dos veces la misma herramienta.
  const dedupedActions = useMemo(() => {
    const seen = new Set<string>();
    return actions.filter((action) => {
      if (seen.has(action.key)) return false;
      seen.add(action.key);
      return true;
    });
  }, [actions]);

  const hubActions = dedupedActions.filter((action) => !isDirectActionKey(action.key));
  const directActions = dedupedActions.filter((action) => isDirectActionKey(action.key));

  return (
    <div
      data-testid="project-detail-pmi-control-bar"
      className="flex flex-wrap items-center justify-between gap-2 border-b border-[hsl(var(--border))] bg-[hsl(var(--surface-2)/0.45)] px-4 py-1.5 shrink-0"
    >
      <div className="flex flex-wrap items-center gap-3 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--muted-foreground))]">
        <span className="font-bold text-[hsl(var(--foreground))]">Control PMI §4.3 &amp; §4.5</span>
        <span>Etapa / Estado: {statusLabel || "active"}</span>
        <span>Avance WBS (0/50/100): {wbsAveragePct}%</span>
        <span>Paquetes WBS: {wbsPackagesCount} paquete(s)</span>
      </div>
      <div className="flex flex-wrap items-center gap-1.5">
        {/* Selector de herramientas con conmutación directa (no-modal): se pasa
            de Horas a Etiquetas/Riesgos/Drive sin cerrar la activa. La selección
            resuelve vía la acción canónica (onSelectAction) en la página. */}
        <label className="sr-only" htmlFor="project-detail-tools-switcher">
          Conmutar herramienta del proyecto
        </label>
        <select
          id="project-detail-tools-switcher"
          data-testid="project-detail-tools-switcher"
          value={activeKey ?? ""}
          onChange={(event) => {
            const key = event.currentTarget.value;
            if (key) onSelectAction(key);
          }}
          className={clsx(
            "rounded-md border px-2 py-1 text-2xs font-semibold uppercase tracking-wide transition-colors focus:outline-2 focus:outline-[hsl(var(--primary))]",
            activeKey
              ? "border-[hsl(var(--primary)/0.35)] bg-[hsl(var(--primary)/0.08)] text-[hsl(var(--primary))] hover:bg-[hsl(var(--primary)/0.16)]"
              : "border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--foreground))] hover:bg-[hsl(var(--surface-2))]"
          )}
        >
          <option value="">Herramientas…</option>
          {hubActions.length > 0 && (
            <optgroup label="Módulos del Hub">
              {hubActions.map((action) => (
                <option key={action.key} value={action.key}>
                  {action.label}
                </option>
              ))}
            </optgroup>
          )}
          {directActions.length > 0 && (
            <optgroup label="Acciones directas">
              {directActions.map((action) => (
                <option key={action.key} value={action.key}>
                  {action.label}
                </option>
              ))}
            </optgroup>
          )}
        </select>
      </div>
    </div>
  );
}
