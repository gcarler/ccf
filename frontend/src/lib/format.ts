/**
 * Format helpers shared across the CCF frontend.
 * Extracted to eliminate the 12+ duplicate formatDate, 4 slugify, and 3 formatBytes
 * copies that were scattered across page and component files.
 */

/**
 * Format a date string (ISO or similar) into a localized date label.
 * Returns fallback when the value is missing or invalid.
 */
export function formatDate(
    value?: string | null,
    options?: {
        locale?: string;
        day?: "numeric" | "2-digit";
        month?: "numeric" | "2-digit" | "short" | "long";
        year?: "numeric" | "2-digit";
        fallback?: string;
    },
): string {
    const {
        locale = "es-CO",
        day = "2-digit",
        month = "short",
        year = "numeric",
        fallback = "—",
    } = options ?? {};

    if (!value) return fallback;
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return fallback;
    return date.toLocaleDateString(locale, { day, month, year });
}

/**
 * Convert a string into a URL-safe slug.
 * Lowercases, trims, replaces whitespace with dashes, strips non-alphanumeric
 * characters (except dashes and underscores), and collapses consecutive dashes.
 */
export function slugify(value: string): string {
    return value
        .toLowerCase()
        .trim()
        .replace(/\s+/g, "-")
        .replace(/[^a-z0-9\-_]/g, "")
        .replace(/-+/g, "-");
}

/**
 * Format a byte count into a human-readable size string.
 */
export function formatBytes(bytes?: number | null): string {
    if (!bytes) return "0 B";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}