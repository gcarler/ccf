import type { LucideIcon } from 'lucide-react';

/**
 * Generic icon component that only requires an optional `size` prop.
 * Used as the non-Lucide branch of `AppIcon`.
 */
export type GenericIconComponent = React.ComponentType<{ size?: number | string; className?: string }>;

/**
 * Generic icon type used across modules.
 *
 * Supports Lucide icons as well as any icon component that accepts an
 * optional `size` prop. This avoids `React.ComponentType<any>` and keeps
 * breadcrumb/toolbar components reusable.
 */
export type AppIcon = LucideIcon | GenericIconComponent;
