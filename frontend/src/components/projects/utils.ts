/**
 * Re-export formatDate from the shared format module for backward compatibility.
 * Existing importers use `es-PE` locale, which is preserved via the options
 * parameter at the call site in ProjectsTableView.tsx.
 */
export { formatDate } from "@/lib/format";