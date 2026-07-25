/**
 * Centralized color palette for the Projects module.
 *
 * This module replaces hardcoded hex values with semantic-token-backed
 * options. The `value` field keeps the hex color sent to / received from the
 * API, while `token` and `preview` drive the UI with the design-system
 * semantic tokens defined in `globals.css`.
 */

export interface ProjectColorOption {
  /** Hex value used as the persisted project/phase color. */
  value: string;
  /** Human-readable label. */
  label: string;
  /** Semantic token name matching a CSS custom property (e.g. `primary`). */
  token: string;
  /** Tailwind class used to preview the color with `bg-[hsl(var(--token))]`. */
  preview: string;
}

/** Curated palette shown in project creation / settings. */
export const PROJECT_COLOR_OPTIONS: ProjectColorOption[] = [
  { value: '#2563eb', label: 'Azul ministerial', token: 'primary', preview: 'bg-[hsl(var(--primary))]' },
  { value: '#0891b2', label: 'Cyan teal', token: 'info', preview: 'bg-[hsl(var(--info))]' },
  { value: '#16a34a', label: 'Verde pastoral', token: 'success', preview: 'bg-[hsl(var(--success))]' },
  { value: '#f59e0b', label: 'Ámbar misión', token: 'warning', preview: 'bg-[hsl(var(--warning))]' },
  { value: '#ef4444', label: 'Rojo urgente', token: 'danger', preview: 'bg-[hsl(var(--danger))]' },
];

/** Default project color (first option). */
export const DEFAULT_PROJECT_COLOR = PROJECT_COLOR_OPTIONS[0].value;

/** Default phase color (neutral slate). */
export const DEFAULT_PHASE_COLOR = '#94a3b8';

/** Curated phase colors mapped to semantic / domain tokens. */
export const PHASE_COLOR_OPTIONS: ProjectColorOption[] = [
  { value: '#94a3b8', label: 'Gris', token: 'surface-2', preview: 'bg-[hsl(var(--surface-2))]' },
  { value: '#3b82f6', label: 'Azul', token: 'primary', preview: 'bg-[hsl(var(--primary))]' },
  { value: '#10b981', label: 'Verde', token: 'success', preview: 'bg-[hsl(var(--success))]' },
  { value: '#f59e0b', label: 'Ámbar', token: 'warning', preview: 'bg-[hsl(var(--warning))]' },
  { value: '#ef4444', label: 'Rojo', token: 'danger', preview: 'bg-[hsl(var(--danger))]' },
  { value: '#8b5cf6', label: 'Violeta', token: 'domain-iris', preview: 'bg-[hsl(var(--domain-iris))]' },
  { value: '#ec4899', label: 'Rosa', token: 'domain-pink', preview: 'bg-[hsl(var(--domain-pink))]' },
  { value: '#06b6d4', label: 'Cyan', token: 'domain-cyan', preview: 'bg-[hsl(var(--domain-cyan))]' },
  { value: '#84cc16', label: 'Lima', token: 'domain-lime', preview: 'bg-[hsl(var(--domain-lime))]' },
  { value: '#f97316', label: 'Naranja', token: 'domain-fuchsia', preview: 'bg-[hsl(var(--domain-fuchsia))]' },
];

/** Lookup a phase color option by its hex value. */
export function getPhaseColorOption(value: string): ProjectColorOption {
  return PHASE_COLOR_OPTIONS.find((option) => option.value === value) ?? PHASE_COLOR_OPTIONS[0];
}

/** Lookup a project color option by its hex value. */
export function getProjectColorOption(value: string): ProjectColorOption {
  return PROJECT_COLOR_OPTIONS.find((option) => option.value === value) ?? PROJECT_COLOR_OPTIONS[0];
}
