/**
 * CCF UI Kit — Barrel unificado.
 *
 * Re-exports todos los componentes de las capas `design/` y `components/ui/`.
 * Uso: import { DSCard, Skeleton, PersonaSelect } from '@/components';
 */

// ── Design System primitives (DS*) ────────────────────────────────────────
export { DSBadge } from '../design/components/DSBadge';
export { DSButton } from '../design/components/DSButton';
export { DSCard } from '../design/components/DSCard';
export { DSChart } from '../design/components/DSChart';
export { DSMetric } from '../design/components/DSMetric';
export { DSToolbarChip } from '../design/components/DSToolbarChip';
export { DSSectionHeader } from '../design/components/DSSectionHeader';
export { DSSkeleton } from '../design/components/DSSkeleton';
export { DSCommandEntry } from '../design/components/DSCommandEntry';

// ── Feedback ──────────────────────────────────────────────────────────────
export { default as Skeleton } from './ui/Skeleton';
export { default as EmptyState } from './ui/EmptyState';
export { default as Tooltip } from './ui/Tooltip';

// ── Data display ──────────────────────────────────────────────────────────
export { DataTable } from './ui/DataTable';
export { default as TableView } from './ui/TableView';
export { default as UniversalTableView } from './ui/UniversalTableView';
export { default as OptimizedImage } from './ui/OptimizedImage';

// ── Forms & pickers ───────────────────────────────────────────────────────
export { default as PersonaSelect } from './ui/PersonaSelect';
export { default as StatusPicker } from './ui/StatusPicker';
export { default as SplitDropdownButton } from './ui/SplitDropdownButton';

// ── Panels & drawers ──────────────────────────────────────────────────────
export { default as SidePanel } from './ui/SidePanel';
export { default as RightPanel } from './ui/RightPanel';
export { default as TextPromptDrawer } from './ui/TextPromptDrawer';
export { default as TaskEditDrawer } from './ui/TaskEditDrawer';
export { default as UniversalCreationDrawer } from './ui/UniversalCreationDrawer';

// ── Views ─────────────────────────────────────────────────────────────────
export { default as UniversalCalendarView } from './ui/UniversalCalendarView';
export { default as UniversalGanttView } from './ui/UniversalGanttView';
export { default as UniversalListView } from './ui/UniversalListView';
export { default as UniversalWikiView } from './ui/UniversalWikiView';

// ── App-level singletons ──────────────────────────────────────────────────
export { CommandCenter } from './ui/CommandCenter';
export { default as ThemeToggle } from './ui/ThemeToggle';
export { default as MeshChat } from './ui/MeshChat';
