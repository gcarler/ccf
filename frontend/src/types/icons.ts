import type { LucideIcon } from 'lucide-react';

/**
 * Generic icon component that only requires an optional `size` prop.
 * Used as the non-Lucide branch of `AppIcon`.
 */
export type GenericIconComponent = React.ComponentType<{ size?: number | string; className?: string }>;

/**
 * Generic icon type used across modules.
 *
 * Supports Lucide icons as well as custom icon components that accept an
 * optional `size` prop. This keeps breadcrumb/toolbar components reusable.
 */
export type AppIcon = LucideIcon | GenericIconComponent;
