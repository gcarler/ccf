"use client";

import React from 'react';
import clsx from 'clsx';

/**
 * DSTypography — primitivo tipográfico del Design System CCF.
 *
 * Centraliza el uso de las fuentes semánticas de la plataforma
 * (ver `globals.css` → `--font-*`, `--text-*`, `--weight-*`, `--tracking-*`):
 *
 *  - `display`  → Outfit (títulos públicos / hero)
 *  - `headline` → Outfit (encabezados de la plataforma)
 *  - `body`     → Inter (texto corrido, fuente base del workspace)
 *  - `label`    → Inter (etiquetas, micro-copy, UI compacta)
 *  - `mono`     → JetBrains Mono (datos técnicos, IDs, código)
 *
 * Las clases de tamaño (`text-2xs` … `text-4xl`), peso (`font-medium`,
 * `font-semibold`…) y tracking (`tracking-wide`…) están vinculadas a los
 * tokens CSS del sistema vía `tailwind.config.ts`.
 */

export type DSFontFamily = 'display' | 'headline' | 'body' | 'label' | 'mono';
export type DSFontSize = '2xs' | 'xs' | 'sm' | 'base' | 'md' | 'lg' | 'xl' | '2xl' | '3xl' | '4xl';
export type DSFontWeight = 'normal' | 'medium' | 'semibold' | 'bold' | 'extrabold';
export type DSTracking = 'tight' | 'normal' | 'wide' | 'wider' | 'widest';

export type DSTypographyTag =
    | 'h1' | 'h2' | 'h3' | 'h4' | 'h5' | 'h6'
    | 'p' | 'span' | 'div' | 'label' | 'code' | 'small' | 'strong';

const FAMILY_CLASS: Record<DSFontFamily, string> = {
    display: 'font-display',
    headline: 'font-headline',
    body: 'font-body',
    label: 'font-label',
    mono: 'font-mono',
};

const SIZE_CLASS: Record<DSFontSize, string> = {
    '2xs': 'text-2xs',
    'xs': 'text-xs',
    'sm': 'text-sm',
    'base': 'text-base',
    'md': 'text-md',
    'lg': 'text-lg',
    'xl': 'text-xl',
    '2xl': 'text-2xl',
    '3xl': 'text-3xl',
    '4xl': 'text-4xl',
};

const WEIGHT_CLASS: Record<DSFontWeight, string> = {
    normal: 'font-normal',
    medium: 'font-medium',
    semibold: 'font-semibold',
    bold: 'font-bold',
    extrabold: 'font-extrabold',
};

const TRACKING_CLASS: Record<DSTracking, string> = {
    tight: 'tracking-[var(--tracking-tight)]',
    normal: 'tracking-[var(--tracking-normal)]',
    wide: 'tracking-[var(--tracking-wide)]',
    wider: 'tracking-[var(--tracking-wider)]',
    widest: 'tracking-[var(--tracking-widest)]',
};

export interface DSTypographyProps extends React.HTMLAttributes<HTMLElement> {
    /** Etiqueta HTML a renderizar (por defecto `span`). */
    as?: DSTypographyTag;
    /** Familia tipográfica semántica (por defecto `body`). */
    family?: DSFontFamily;
    /** Tamaño de la escala semántica (por defecto `base` = 13px plataforma). */
    size?: DSFontSize;
    /** Peso tipográfico. Por defecto respeta el peso del elemento/base. */
    weight?: DSFontWeight;
    /** Espaciado entre letras. Por defecto `normal`. */
    tracking?: DSTracking;
    /** Transforma el texto a mayúsculas (patrón de labels de plataforma). */
    uppercase?: boolean;
    /** Trunca el texto con ellipsis en una línea. */
    truncate?: boolean;
}

export function DSTypography({
    as: Tag = 'span',
    family = 'body',
    size = 'base',
    weight,
    tracking,
    uppercase = false,
    truncate = false,
    className,
    children,
    ...props
}: DSTypographyProps) {
    return (
        <Tag
            className={clsx(
                FAMILY_CLASS[family],
                SIZE_CLASS[size],
                weight && WEIGHT_CLASS[weight],
                TRACKING_CLASS[tracking ?? 'normal'],
                uppercase && 'uppercase',
                truncate && 'truncate',
                className,
            )}
            {...props}
        >
            {children}
        </Tag>
    );
}

export default DSTypography;
