"use client";

import clsx from 'clsx';
import {
    PROJECT_STATUS_LABELS,
    getPriorityOption,
    getStatusOption,
    getValidProjectStatus,
} from '@/lib/projects/constants';
import { getNodeOption } from '@/lib/projects/constants';
import type { ProjectStatus } from '@/lib/projects/constants';

/**
 * Librería de badges del módulo de Proyectos.
 *
 * Consolidación canónica del renderizado de estado/prioridad/nodo que antes
 * estaba duplicado (STATUS_CLS / PRIORITY_CLS locales en cada vista). Todos
 * los estilos derivan de las configs visuales compartidas en
 * `@/lib/projects/constants` (STATUS_OPTIONS, PRIORITY_OPTIONS,
 * PROJECT_STATUS_BADGE) y usan exclusivamente tokens semánticos del design
 * system (`hsl(var(--*))`).
 */

/**
 * Visual badge classes for the project status enum. Semantic tokens only —
 * no hardcoded palette colors. Light mode uses muted bg + dark text; dark
 * mode uses soft bg + bright text (same convention as globals.css badges).
 */
const PROJECT_STATUS_BADGE: Record<ProjectStatus, string> = {
    planning: 'bg-[hsl(var(--warning-muted))] text-[hsl(var(--warning-text))] border-[hsl(var(--warning)/0.3)] dark:bg-[hsl(var(--warning)/0.2)] dark:text-[hsl(var(--warning))]',
    active:   'bg-[hsl(var(--info-muted))] text-[hsl(var(--info-text))] border-[hsl(var(--info)/0.3)] dark:bg-[hsl(var(--info)/0.2)] dark:text-[hsl(var(--info))]',
    on_hold:  'bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] border-[hsl(var(--border))] dark:bg-[hsl(var(--surface-2))] dark:border-[hsl(var(--border))]',
    completed: 'bg-[hsl(var(--success-muted))] text-[hsl(var(--success-text))] border-[hsl(var(--success)/0.3)] dark:bg-[hsl(var(--success)/0.2)] dark:text-[hsl(var(--success))]',
    archived: 'bg-[hsl(var(--surface-3))] text-[hsl(var(--muted-foreground))] border-[hsl(var(--border))] dark:bg-[hsl(var(--surface-3))] dark:border-[hsl(var(--border))]',
};

const BASE_BADGE_CLS =
    'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-2xs font-semibold uppercase tracking-wide border whitespace-nowrap';

export interface TaskStatusBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
    /** Slug de estado de tarea (canónico o slug de fase). */
    value: string | null | undefined;
    /** Oculta el punto de color junto al label. */
    hideDot?: boolean;
    /** Estilo inline para el punto (colores hex de fases dinámicas). */
    dotStyle?: React.CSSProperties;
}

/** Badge del estado de una tarea (canónico o de fase dinámica). */
export function TaskStatusBadge({ value, hideDot = false, dotStyle, className, ...props }: TaskStatusBadgeProps) {
    const opt: ReturnType<typeof getStatusOption> = getStatusOption((value ?? '').toLowerCase());
    return (
        <span className={clsx(BASE_BADGE_CLS, opt.bg, opt.text, opt.border, className)} {...props}>
            {!hideDot && <span className={clsx('size-1.5 rounded-full shrink-0', opt.dot)} style={dotStyle} />}
            {opt.label}
        </span>
    );
}

export interface TaskPriorityBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
    /** Slug de prioridad (`low` | `medium` | `high` | `urgent`). */
    value: string | null | undefined;
    /** Oculta el punto de color junto al label. */
    hideDot?: boolean;
}

/** Badge de la prioridad de una tarea. */
export function TaskPriorityBadge({ value, hideDot = false, className, ...props }: TaskPriorityBadgeProps) {
    const opt = getPriorityOption((value ?? '').toLowerCase());
    return (
        <span className={clsx(BASE_BADGE_CLS, 'border-transparent', opt.color, className)} {...props}>
            {!hideDot && <span className={clsx('size-1.5 rounded-full shrink-0', opt.dot)} />}
            {opt.label}
        </span>
    );
}

export interface ProjectStatusBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
    /** Estado canónico del proyecto (`planning` | `active` | `on_hold` | `completed` | `archived`). */
    value: string | null | undefined;
    /** Label visual alternativo (p. ej. "En Marcha" en vez de "Activo"). */
    label?: string;
}

/** Badge del estado de un proyecto (enum canónico de 5 valores). */
export function ProjectStatusBadge({ value, label, className, ...props }: ProjectStatusBadgeProps) {
    const status = getValidProjectStatus(value);
    return (
        <span className={clsx(BASE_BADGE_CLS, PROJECT_STATUS_BADGE[status], className)} {...props}>
            {label ?? PROJECT_STATUS_LABELS[status]}
        </span>
    );
}

export interface TaskNodeBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
    /** Slug del nodo operativo (`nutrition` | `digital`). */
    value: string | null | undefined;
}

/** Badge del nodo operativo de una tarea. */
export function TaskNodeBadge({ value, className, ...props }: TaskNodeBadgeProps) {
    const opt = getNodeOption(value);
    return (
        <span
            className={clsx(
                BASE_BADGE_CLS,
                'border-transparent',
                opt ? opt.color : 'text-[hsl(var(--muted-foreground))]',
                className,
            )}
            {...props}
        >
            {opt && <span className={clsx('size-1.5 rounded-full shrink-0', opt.dot)} />}
            {opt ? opt.label : 'Sin nodo'}
        </span>
    );
}
