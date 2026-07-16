
"use client";

import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { DEFAULT_TASK_PRIORITY } from '@/lib/projects/constants';
import type { ProjectTaskRecord } from '@/types/projects';
import { InlineStatusPicker, InlinePriorityPicker, InlineDatePicker, InlineUserPicker } from '@/components/ui/inline-editors';
import { useProjectTasks } from '@/hooks/useProjectTasks';
import * as Popover from '@radix-ui/react-popover';
import {
AllCommunityModule,
ColDef,
GetRowIdParams,
ICellRendererParams,
ModuleRegistry,themeQuartz,
} from '@/lib/ag-grid-community-no-style';
import { AgGridReact } from 'ag-grid-react';
import clsx from 'clsx';
import { AnimatePresence,motion } from 'framer-motion';
import {
Check,
Circle,
Eye,EyeOff,Filter,
Layers,
MessageSquare,
Plus,
Settings2,
X
} from 'lucide-react';
import { useCallback,useEffect,useMemo,useRef,useState } from 'react';
import TitleCellEditor from './TitleCellEditor';

ModuleRegistry.registerModules([AllCommunityModule]);

// ─── Status / Priority configs ─────────────────────────────────────────────────
const STATUS_OPTIONS = [
    { value:'todo',        label:'Pendiente',   dot:'bg-[hsl(var(--surface-2))]',   bg:'bg-[hsl(var(--surface-2))] dark:bg-white/5',            text:'text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]',      border:'border-[hsl(var(--border))] dark:border-white/10' },
    { value:'in_progress', label:'En Progreso', dot:'bg-[hsl(var(--primary))]',    bg:'bg-blue-100 dark:bg-blue-500/20',         text:'text-[hsl(var(--primary))] dark:text-blue-300',        border:'border-blue-200 dark:border-blue-500/30' },
    { value:'review',      label:'En Revisión', dot:'bg-amber-500',   bg:'bg-amber-100 dark:bg-amber-500/20',       text:'text-amber-700 dark:text-amber-300',      border:'border-amber-200 dark:border-amber-500/30' },
    { value:'completed',   label:'Completado',  dot:'bg-emerald-500', bg:'bg-emerald-100 dark:bg-emerald-500/20',   text:'text-emerald-700 dark:text-emerald-300',  border:'border-emerald-200 dark:border-emerald-500/30' },
] as const;
function getStatus(val: string) { return STATUS_OPTIONS.find(s => s.value === val) ?? STATUS_OPTIONS[0]; }

const PRIORITY_OPTIONS = [
    { value:'low',    label:'Baja',    color:'text-[hsl(var(--text-secondary))]',  fill:'#94a3b8' },
    { value:'medium', label:'Media',   color:'text-[hsl(var(--primary))]',   fill:'#3b82f6' },
    { value:'high',   label:'Alta',    color:'text-orange-500', fill:'#f97316' },
    { value:'urgent', label:'Urgente', color:'text-rose-500',   fill:'#ef4444' },
] as const;
function getPriority(val: string) { return PRIORITY_OPTIONS.find(p => p.value === val) ?? PRIORITY_OPTIONS[1]; }

const FlagIcon = ({ fill, size = 14 }: { fill: string; size?: number }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={fill} xmlns="http://www.w3.org/2000/svg">
        <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z" />
        <line x1="4" y1="22" x2="4" y2="15" stroke={fill} strokeWidth="2" strokeLinecap="round"/>
    </svg>
);

// ─── AG Grid Themes ────────────────────────────────────────────────────────────
const lightTheme = themeQuartz.withParams({ fontFamily: 'inherit', fontSize: 12, rowHeight: 40, headerHeight: 36, backgroundColor: '#ffffff', foregroundColor: '#1e293b', borderColor: '#e2e8f0', oddRowBackgroundColor: '#f8fafc', headerBackgroundColor: '#f1f5f9', headerTextColor: '#475569', selectedRowBackgroundColor: '#eef2ff', accentColor: '#6366f1', cellHorizontalPaddingScale: 0.8 });
const darkTheme  = themeQuartz.withParams({ fontFamily: 'inherit', fontSize: 12, rowHeight: 40, headerHeight: 36, backgroundColor: 'rgb(15 23 42)', foregroundColor: '#e2e8f0', borderColor: 'rgba(255,255,255,0.08)', oddRowBackgroundColor: 'rgba(255,255,255,0.02)', headerBackgroundColor: 'rgba(255,255,255,0.04)', headerTextColor: '#94a3b8', selectedRowBackgroundColor: 'rgba(99,102,241,0.15)', accentColor: '#6366f1', cellHorizontalPaddingScale: 0.8 });

// ─── AG Grid Cell Renderers (use context for callbacks) ────────────────────────
function TitleRenderer(params: ICellRendererParams) {
    if (params.data?.__isGroup) return null;
    const task = params.data as ProjectTaskRecord;
    return (
        <div className="flex items-center gap-2 h-full w-full text-left group">
            <div className={clsx('size-4 rounded-full border-2 flex items-center justify-center flex-shrink-0',
                task.status === 'completed' ? 'bg-emerald-500 border-emerald-500 text-white' : 'border-[hsl(var(--border))] dark:border-white/20')}>
                {task.status === 'completed' && <span className="text-[7px] font-bold">✓</span>}
            </div>
            <span className="text-[13px] font-semibold truncate group-hover:text-[hsl(var(--primary))] transition-colors">
                {task.title}
            </span>
            {(task.comments_count ?? 0) > 0 && (
                <span className="ml-auto flex items-center gap-0.5 text-[hsl(var(--text-secondary))] shrink-0">
                    <MessageSquare size={11} /><span className="text-[10px]">{task.comments_count}</span>
                </span>
            )}
        </div>
    );
}

function StatusRenderer(params: ICellRendererParams) {
    if (params.data?.__isGroup) return null;
    const { applyChangeRef } = params.context ?? {};
    const task = params.data as ProjectTaskRecord;
    return <InlineStatusPicker value={task.status ?? 'todo'} onChange={(v) => applyChangeRef?.current?.(task.id, 'status', v)} />;
}

function PriorityRenderer(params: ICellRendererParams) {
    if (params.data?.__isGroup) return null;
    const { applyChangeRef } = params.context ?? {};
    const task = params.data as ProjectTaskRecord;
    return <InlinePriorityPicker value={task.priority ?? 'medium'} onChange={(v) => applyChangeRef?.current?.(task.id, 'priority', v)} />;
}

function DateRenderer(params: ICellRendererParams) {
    if (params.data?.__isGroup) return null;
    const { applyChangeRef } = params.context ?? {};
    const task = params.data as ProjectTaskRecord;
    return <InlineDatePicker value={task.due_date} onChange={(v) => applyChangeRef?.current?.(task.id, 'due_date', v)} />;
}

function AssigneeRenderer(params: ICellRendererParams) {
    if (params.data?.__isGroup) return null;
    const { applyChangeRef } = params.context ?? {};
    const task = params.data as ProjectTaskRecord;
    return <InlineUserPicker value={task.assignee_id} onChange={(id, name) => applyChangeRef?.current?.(task.id, 'assignee_id', id, { assignee_name: name })} />;
}

// ─── Props / Types ─────────────────────────────────────────────────────────────
interface Props {
    projectId?: string | number;
    tasks: ProjectTaskRecord[];
    onOpenTask: (task: ProjectTaskRecord) => void;
    onAddTask: (status: string, dueDate?: string, title?: string) => Promise<void> | void;
    onTaskUpdated?: (taskId: number, field: string, value: any) => void;
}

type GroupKey = 'status' | 'priority' | 'none';
type ColumnId = 'title' | 'status' | 'priority' | 'assignee' | 'due_date' | 'comments';
const ALL_COLUMNS: { id: ColumnId; label: string }[] = [
    { id: 'title',    label: 'Nombre' },
    { id: 'status',   label: 'Estado' },
    { id: 'priority', label: 'Prioridad' },
    { id: 'assignee', label: 'Asignado' },
    { id: 'due_date', label: 'Fecha límite' },
    { id: 'comments', label: 'Comentarios' },
];
type ActiveFilter = { field: 'status' | 'priority'; value: string; label: string };

// ─── Main Component ────────────────────────────────────────────────────────────
export default function TaskTableView({ projectId, tasks, onOpenTask, onAddTask, onTaskUpdated }: Props) {
    const { token } = useAuth();
    const { updateTask } = useProjectTasks();
    const gridRef = useRef<AgGridReact>(null);
    const [isDark, setIsDark] = useState(false);
    const [overrides, setOverrides] = useState<Record<string, Partial<ProjectTaskRecord>>>({});
    const [groupBy, setGroupBy]     = useState<GroupKey>('status');
    const [activeFilters, setActiveFilters] = useState<ActiveFilter[]>([]);
    const [visibleCols, setVisibleCols] = useState<Set<ColumnId>>(new Set<ColumnId>(['title','status','priority','assignee','due_date']));
    const [cfgOpen, setCfgOpen]     = useState(false);
    const [filterOpen, setFilterOpen] = useState(false);
    const [groupOpen, setGroupOpen]   = useState(false);
    const [quickAddGroup, setQuickAddGroup] = useState<string | null>(null);
    const [quickAddTitle, setQuickAddTitle] = useState('');
    const [isLoaded, setIsLoaded]   = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Dark mode detection
    useEffect(() => {
        const check = () => setIsDark(document.documentElement.classList.contains('dark'));
        check();
        const obs = new MutationObserver(check);
        obs.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
        return () => obs.disconnect();
    }, []);

    // Preferences persistence
    useEffect(() => {
        const key = projectId ? `ccf_task_table_prefs_${projectId}` : 'ccf_task_table_prefs';
        try {
            const stored = localStorage.getItem(key);
            if (stored) {
                const p = JSON.parse(stored);
                if (p.groupBy) setGroupBy(p.groupBy);
                if (p.activeFilters) setActiveFilters(p.activeFilters);
                if (p.visibleCols) setVisibleCols(new Set(p.visibleCols));
            }
        } catch { /* ignore */ }
        setIsLoaded(true);
    }, [projectId]);

    useEffect(() => {
        if (!isLoaded) return;
        const key = projectId ? `ccf_task_table_prefs_${projectId}` : 'ccf_task_table_prefs';
        try { localStorage.setItem(key, JSON.stringify({ groupBy, activeFilters, visibleCols: Array.from(visibleCols) })); } catch { /* ignore */ }
    }, [isLoaded, projectId, groupBy, activeFilters, visibleCols]);

    // Optimistic update via shared hook
    const applyChange = useCallback(async (taskId: number | string, field: string, value: any, extraOpt: Record<string, any> = {}) => {
        setOverrides(prev => ({ ...prev, [taskId]: { ...prev[taskId], [field]: value, ...extraOpt } }));
        const updated = await updateTask(String(taskId), { [field]: value }, { optimistic: false });
        if (updated) {
            onTaskUpdated?.(Number(taskId), field, value);
        } else {
            setOverrides(prev => { const n = { ...prev }; delete n[taskId]; return n; });
        }
    }, [updateTask, onTaskUpdated]);

    // Stable ref for applyChange so cell renderers always have latest version
    const applyChangeRef = useRef(applyChange);
    useEffect(() => { applyChangeRef.current = applyChange; }, [applyChange]);

    // Trigger title edit on double click for the title column
    const handleCellDoubleClicked = useCallback((e: any) => {
        if (e.colDef.field === 'title' && !e.data?.__isGroup) {
            e.event?.stopPropagation?.();
            e.api.startEditingCell({ rowIndex: e.rowIndex, colKey: 'title' });
        }
    }, []);

    // Resolve optimistic overrides
    const resolveTask = useCallback((t: ProjectTaskRecord): ProjectTaskRecord => ({ ...t, ...(overrides[t.id] ?? {}) }), [overrides]);

    // Process: filter
    const processed = useMemo(() => {
        let list = tasks.map(resolveTask);
        for (const f of activeFilters) {
            list = list.filter(t => f.field === 'status' ? t.status === f.value : t.priority === f.value);
        }
        return list;
    }, [tasks, activeFilters, resolveTask]);

    // Flatten with group headers
    const rowData = useMemo(() => {
        if (groupBy === 'none') return processed;
        const groups: Record<string, ProjectTaskRecord[]> = {};
        processed.forEach(t => {
            const k = groupBy === 'priority' ? (t.priority ?? DEFAULT_TASK_PRIORITY) : (t.status ?? 'todo');
            if (!groups[k]) groups[k] = [];
            groups[k].push(t);
        });
        const order: string[] = groupBy === 'priority' ? PRIORITY_OPTIONS.map(p => p.value) : STATUS_OPTIONS.map(s => s.value);
        const flat: any[] = [];
        const sorted = Object.entries(groups).sort(([a],[b]) => (order.indexOf(a as any) ?? 99) - (order.indexOf(b as any) ?? 99));
        sorted.forEach(([key, rows]) => {
            flat.push({ __isGroup: true, __groupKey: key, __groupCount: rows.length, id: `__group__${key}` });
            flat.push(...rows);
        });
        return flat;
    }, [processed, groupBy]);

    // Column definitions
    const colDefs = useMemo<ColDef[]>(() => {
        const cols: ColDef[] = [];
        if (visibleCols.has('title'))    cols.push({ field: 'title',      headerName: 'Nombre',       flex: 3, minWidth: 220, cellRenderer: TitleRenderer, cellEditor: TitleCellEditor, editable: true, sortable: true });
        if (visibleCols.has('status'))   cols.push({ field: 'status',     headerName: 'Estado',       width: 160, cellRenderer: StatusRenderer, sortable: true });
        if (visibleCols.has('priority')) cols.push({ field: 'priority',   headerName: 'Prioridad',    width: 140, cellRenderer: PriorityRenderer, sortable: true });
        if (visibleCols.has('assignee')) cols.push({ field: 'assignee_id',headerName: 'Asignado',     width: 160, cellRenderer: AssigneeRenderer, sortable: false });
        if (visibleCols.has('due_date')) cols.push({ field: 'due_date',   headerName: 'Fecha límite', width: 140, cellRenderer: DateRenderer, sortable: true });
        return cols.map(c => ({ ...c, resizable: true, suppressHeaderMenuButton: false }));
    }, [visibleCols]);

    // Full-width group row renderer
    const isFullWidthRow = useCallback((p: any) => !!p.rowNode.data?.__isGroup, []);
    const fullWidthCellRenderer = useCallback(({ data: row }: any) => {
        const label = groupBy === 'priority'
            ? (getPriority(row.__groupKey)?.label ?? row.__groupKey)
            : (getStatus(row.__groupKey)?.label ?? row.__groupKey);
        const dot = groupBy === 'status' ? getStatus(row.__groupKey)?.dot : undefined;
        return (
            <div className="flex items-center gap-2.5 px-4 h-full bg-[hsl(var(--surface-1))] dark:bg-white/[0.03] border-b border-[hsl(var(--border))] dark:border-white/5">
                {dot && <span className={clsx('size-2 rounded-full flex-shrink-0', dot)} />}
                <span className="text-[11px] font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">{label}</span>
                <span className="text-[10px] font-semibold text-[hsl(var(--text-secondary))] bg-[hsl(var(--surface-3))] dark:bg-white/10 rounded-full px-2 py-0.5">{row.__groupCount}</span>
                <button onClick={() => setQuickAddGroup(row.__groupKey)}
                    className="ml-auto flex items-center gap-1 text-[10px] font-semibold text-[hsl(var(--primary))] hover:text-[hsl(var(--primary)/0.8)] transition-colors">
                    <Plus size={11} /> Agregar
                </button>
            </div>
        );
    }, [groupBy]);

    // AG Grid context
    const gridContext = useMemo(() => ({ applyChangeRef, onOpenTask, token }), [onOpenTask, token]);

    const getRowId = useCallback((p: GetRowIdParams) => String((p.data as any).id), []);
    const getRowHeight = useCallback((p: any) => p.data?.__isGroup ? 32 : 40, []);

    // Quick add task
    const handleQuickAdd = async (status: string, title: string) => {
        try {
            await apiFetch(`/projects/${projectId}/tasks`, { method: 'POST', body: { title, status, priority: 'medium' }, token: token ?? undefined });
            onAddTask(status);
            setError(null);
        } catch {
            setError('No se pudo crear la tarea rápida.');
        }
        setQuickAddGroup(null);
        setQuickAddTitle('');
    };

    return (
        <div className="flex min-w-0 flex-col h-full bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-secondary))] font-sans overflow-hidden">

            {error && (
                <div className="mx-3 mt-3 rounded-md border border-amber-200 bg-amber-50 p-3 text-amber-900 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-200">
                    <p className="text-[11px] font-bold uppercase tracking-wide">{error}</p>
                </div>
            )}

            {/* ── TOOLBAR ── */}
            <div className="shrink-0 flex min-w-0 items-center gap-1.5 px-3 py-1.5 border-b border-[hsl(var(--border))] dark:border-white/[0.06] bg-[hsl(var(--surface-1))]/60 dark:bg-black/10 flex-wrap">

                {/* Column visibility */}
                <Popover.Root open={cfgOpen} onOpenChange={setCfgOpen}>
                    <Popover.Trigger asChild>
                        <button className={clsx('flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-semibold transition-all', cfgOpen ? 'bg-blue-50 dark:bg-blue-500/10 text-[hsl(var(--primary))]' : 'text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] dark:hover:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5')}>
                            <Settings2 size={12} /> Columnas
                        </button>
                    </Popover.Trigger>
                    <Popover.Portal>
                        <Popover.Content sideOffset={6} align="start" className="z-[500] w-52 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-secondary))] rounded-md shadow-2xl border border-[hsl(var(--border))]/80 dark:border-white/10 p-2">
                            <p className="text-[9px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] px-2 py-1.5">Columnas visibles</p>
                            {ALL_COLUMNS.map(col => (
                                <button key={col.id} onClick={() => setVisibleCols(prev => { const n = new Set(prev); if (n.has(col.id)) { if (col.id !== 'title') n.delete(col.id); } else n.add(col.id); return n; })}
                                    className="w-full flex items-center gap-2.5 px-2 py-1.5 rounded-lg hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 transition-colors">
                                    {visibleCols.has(col.id) ? <Eye size={13} className="text-[hsl(var(--primary))] shrink-0" /> : <EyeOff size={13} className="text-[hsl(var(--text-secondary))] shrink-0" />}
                                    <span className={clsx('text-[12px] font-medium flex-1 text-left', visibleCols.has(col.id) ? 'text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]' : 'text-[hsl(var(--text-secondary))]')}>{col.label}</span>
                                    {col.id === 'title' && <span className="text-[9px] text-[hsl(var(--text-secondary))]">fijo</span>}
                                </button>
                            ))}
                        </Popover.Content>
                    </Popover.Portal>
                </Popover.Root>

                <div className="w-px h-4 bg-[hsl(var(--surface-3))] dark:bg-white/10" />

                {/* Group by */}
                <Popover.Root open={groupOpen} onOpenChange={setGroupOpen}>
                    <Popover.Trigger asChild>
                        <button className={clsx('flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-semibold transition-all', groupBy !== 'status' ? 'bg-blue-50 dark:bg-blue-500/10 text-[hsl(var(--primary))]' : 'text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] dark:hover:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5')}>
                            <Layers size={12} /> Agrupar{groupBy !== 'none' ? `: ${groupBy === 'status' ? 'Estado' : 'Prioridad'}` : ''}
                        </button>
                    </Popover.Trigger>
                    <Popover.Portal>
                        <Popover.Content sideOffset={6} align="start" className="z-[500] w-52 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-secondary))] rounded-md shadow-2xl border border-[hsl(var(--border))]/80 dark:border-white/10 p-1.5">
                            <p className="text-[9px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] px-2 pt-1 pb-2">Agrupar por</p>
                            {([['status','Estado'],['priority','Prioridad'],['none','Sin agrupación']] as const).map(([k, lbl]) => (
                                <button key={k} onClick={() => { setGroupBy(k); setGroupOpen(false); }}
                                    className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 transition-colors">
                                    <span className="text-[12px] font-semibold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] flex-1 text-left">{lbl}</span>
                                    {groupBy === k && <Check size={12} className="text-[hsl(var(--primary))]" />}
                                </button>
                            ))}
                        </Popover.Content>
                    </Popover.Portal>
                </Popover.Root>

                {/* Filter */}
                <Popover.Root open={filterOpen} onOpenChange={setFilterOpen}>
                    <Popover.Trigger asChild>
                        <button className={clsx('flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-semibold transition-all', activeFilters.length > 0 ? 'bg-blue-50 dark:bg-blue-500/10 text-[hsl(var(--primary))]' : 'text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] dark:hover:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5')}>
                            <Filter size={12} /> Filtrar{activeFilters.length > 0 ? ` (${activeFilters.length})` : ''}
                        </button>
                    </Popover.Trigger>
                    <Popover.Portal>
                        <Popover.Content sideOffset={6} align="start" className="z-[500] w-64 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-secondary))] rounded-md shadow-2xl border border-[hsl(var(--border))]/80 dark:border-white/10 p-2">
                            <p className="text-[9px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] px-2 py-1.5">Por Estado</p>
                            <div className="flex flex-wrap gap-1.5 px-2 pb-2">
                                {STATUS_OPTIONS.map(s => {
                                    const active = activeFilters.some(f => f.field === 'status' && f.value === s.value);
                                    return <button key={s.value} onClick={() => setActiveFilters(prev => active ? prev.filter(f => !(f.field==='status' && f.value===s.value)) : [...prev, { field: 'status', value: s.value, label: s.label }])}
                                        className={clsx('flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-semibold border transition-all', active ? `${s.bg} ${s.text} ${s.border} ring-2 ring-blue-500/30` : `${s.bg} ${s.text} ${s.border} opacity-60 hover:opacity-100`)}>
                                        <div className={clsx('size-1.5 rounded-full', s.dot)} />{s.label}
                                    </button>;
                                })}
                            </div>
                            <p className="text-[9px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] px-2 py-1.5 border-t border-[hsl(var(--border))] dark:border-white/5">Por Prioridad</p>
                            <div className="flex flex-wrap gap-1.5 px-2 pb-2">
                                {PRIORITY_OPTIONS.map(p => {
                                    const active = activeFilters.some(f => f.field === 'priority' && f.value === p.value);
                                    return <button key={p.value} onClick={() => setActiveFilters(prev => active ? prev.filter(f => !(f.field==='priority' && f.value===p.value)) : [...prev, { field: 'priority', value: p.value, label: p.label }])}
                                        className={clsx('flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-semibold border transition-all bg-[hsl(var(--surface-1))] dark:bg-white/5 border-[hsl(var(--border))] dark:border-white/10', active ? 'ring-2 ring-blue-500/30 opacity-100' : 'opacity-60 hover:opacity-100', p.color)}>
                                        <FlagIcon fill={p.fill} size={11} />{p.label}
                                    </button>;
                                })}
                            </div>
                            {activeFilters.length > 0 && <button onClick={() => setActiveFilters([])} className="w-full text-[11px] font-bold text-rose-500 py-1.5 hover:bg-rose-50 dark:hover:bg-rose-500/10 rounded-lg transition-colors border-t border-[hsl(var(--border))] dark:border-white/5 mt-1">Limpiar filtros</button>}
                        </Popover.Content>
                    </Popover.Portal>
                </Popover.Root>

                <div className="ml-0 sm:ml-auto flex min-w-0 items-center gap-1.5 overflow-x-auto">
                    {activeFilters.length > 0 && (
                        <div className="flex min-w-0 gap-1">
                            {activeFilters.map((f, i) => <span key={i} className="flex shrink-0 items-center gap-1 px-2 py-0.5 rounded-full bg-blue-50 dark:bg-blue-500/10 text-[hsl(var(--primary))] text-[10px] font-semibold">{f.label}<button onClick={() => setActiveFilters(p => p.filter((_,j) => j !== i))}><X size={9} /></button></span>)}
                        </div>
                    )}
                    <button onClick={() => onAddTask('todo')} className="flex shrink-0 items-center gap-1.5 px-3 py-1.5 text-[11px] font-bold rounded-lg bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary)/0.85)] text-white transition-colors">
                        <Plus size={13} /> Nueva tarea
                    </button>
                </div>
            </div>

            {/* Quick add row */}
            <AnimatePresence>
                {quickAddGroup && (
                    <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}
                        className="shrink-0 flex min-w-0 items-center gap-3 px-4 py-2.5 bg-blue-50/50 dark:bg-blue-500/5 border-b border-[hsl(var(--border))] dark:border-white/5">
                        <Circle size={15} className="text-[hsl(var(--text-secondary))] shrink-0" />
                        <input
                            autoFocus
                            value={quickAddTitle}
                            onChange={e => setQuickAddTitle(e.target.value)}
                            onKeyDown={e => {
                                if (e.key === 'Enter' && quickAddTitle.trim()) handleQuickAdd(quickAddGroup, quickAddTitle.trim());
                                if (e.key === 'Escape') { setQuickAddGroup(null); setQuickAddTitle(''); }
                            }}
                            placeholder="Nombre de la tarea... (Enter para crear)"
                            className="flex-1 text-[13px] font-medium text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] bg-transparent outline-none placeholder:text-[hsl(var(--text-secondary))]"
                        />
                        <button onClick={() => quickAddTitle.trim() && handleQuickAdd(quickAddGroup, quickAddTitle.trim())} className="px-3 py-1 bg-[hsl(var(--primary))] text-white text-[11px] font-bold rounded-lg hover:bg-[hsl(var(--primary))] transition-colors shrink-0">Crear</button>
                        <button onClick={() => { setQuickAddGroup(null); setQuickAddTitle(''); }} className="p-1.5 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] rounded-lg transition-colors"><X size={13} /></button>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Grid */}
            <div className="flex-1 min-w-0 min-h-0">
                {tasks.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full gap-3 text-[hsl(var(--text-secondary))]">
                        <Circle size={28} className="text-[hsl(var(--text-secondary))] dark:text-white/10" />
                        <p className="text-sm font-medium">Sin tareas en este proyecto</p>
                        <button onClick={() => onAddTask('todo')} className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-lg bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary)/0.85)] text-white transition-colors">
                            <Plus size={13} /> Crear primera tarea
                        </button>
                    </div>
                ) : (
                    <AgGridReact
                        ref={gridRef}
                        theme={isDark ? darkTheme : lightTheme}
                        rowData={rowData as any[]}
                        columnDefs={colDefs}
                        defaultColDef={{ resizable: true, sortable: false, filter: false, editable: false, suppressMovable: false, minWidth: 96 }}
                        context={gridContext}
                        getRowId={getRowId}
                        getRowHeight={getRowHeight}
                        isFullWidthRow={groupBy !== 'none' ? isFullWidthRow : undefined}
                        fullWidthCellRenderer={groupBy !== 'none' ? fullWidthCellRenderer : undefined}
                        onRowDoubleClicked={(e) => { if (!e.data?.__isGroup) onOpenTask(e.data); }}
                        onCellDoubleClicked={handleCellDoubleClicked}
                        onCellValueChanged={(e) => {
                            if (e.colDef.field === 'title' && !e.data?.__isGroup) {
                                const taskId = String(e.data.id);
                                const newTitle = e.newValue;
                                if (newTitle && newTitle.trim()) {
                                    applyChangeRef.current?.(taskId, 'title', newTitle.trim());
                                }
                            }
                        }}
                        rowStyle={{ cursor: 'pointer' }}
                        suppressCellFocus
                        animateRows
                        enableCellTextSelection
                    />
                )}
            </div>
        </div>
    );
}
