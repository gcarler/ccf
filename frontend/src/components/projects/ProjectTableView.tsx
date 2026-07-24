"use client";

import '@/lib/agGrid';
import { useMemo, useRef, useEffect } from 'react';
import { AgGridReact } from 'ag-grid-react';
import { ColDef } from 'ag-grid-community';
import clsx from 'clsx';
import type { ProjectTaskRecord } from '@/types/projects';
import { getStatusOption, getPriorityOption } from '@/lib/projects/constants';
import { useIsDark, agGridCompactLightTheme, agGridCompactDarkTheme } from '@/lib/projects/agGridTheme';

const STATUS_CLS: Record<string, string> = {
    completed:   'bg-success-soft border-[hsl(var(--success)/20%)] text-success-text',
    in_progress: 'bg-info-soft border-[hsl(var(--info)/20%)] text-[hsl(var(--primary))]',
    review:      'bg-warning-soft border-[hsl(var(--warning)/20%)] text-warning-text',
    todo:        'bg-slate-50 border-slate-100 text-slate-600',
};

const PRIORITY_CLS: Record<string, string> = {
    urgent: 'text-danger-text',
    high:   'text-orange-500',
    medium: 'text-[hsl(var(--primary))]',
    low:    'text-[hsl(var(--text-secondary))]',
};

function TitleRenderer({ value, data }: { value: string; data: { id?: string; status?: string } }) {
    const st = data?.status === 'completed';
    return (
        <div className="flex items-center gap-2.5">
            <div className={clsx('size-4 rounded-full border-2 flex items-center justify-center flex-shrink-0',
                st ? 'bg-[hsl(var(--success))] border-[hsl(var(--success)/100%)] text-white' : 'border-[hsl(var(--border))] dark:border-white/20')}>
                {st && <span className="text-[8px] font-bold">✓</span>}
            </div>
            <span className="text-[13px] font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] truncate">{value}</span>
        </div>
    );
}

function StatusRenderer({ value }: { value: string }) {
    const opt = getStatusOption(value?.toLowerCase());
    return <span className={clsx('px-2.5 py-0.5 rounded-lg text-[10px] font-semibold uppercase tracking-wide border', STATUS_CLS[opt.value])}>{opt.label}</span>;
}

function PriorityRenderer({ value }: { value: string }) {
    const opt = getPriorityOption(value?.toLowerCase());
    return <span className={clsx('text-[11px] font-bold uppercase tracking-wide', PRIORITY_CLS[opt.value])}>⚑ {opt.label}</span>;
}

function AssigneeRenderer({ value }: { value: string | null | undefined }) {
    if (!value) return <span className="text-[11px] text-[hsl(var(--text-secondary))]">—</span>;
    return (
        <span
            className="text-[11px] font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]"
            title={value}
        >
            {String(value).replace(/-/g, '').slice(0, 8)}
        </span>
    );
}

function DateRenderer({ value }: { value: string }) {
    if (!value) return <span className="text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] text-xs">—</span>;
    return <span className="text-[11px] font-bold text-[hsl(var(--text-secondary))]">{new Date(value).toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: '2-digit' })}</span>;
}

export default function ProjectTableView({ tasks }: { tasks: ProjectTaskRecord[] }) {
    const gridRef = useRef<AgGridReact>(null);
    const isDark = useIsDark();

    const colDefs = useMemo<ColDef[]>(() => [
        { field: 'title',    headerName: 'Tarea',        flex: 2, cellRenderer: TitleRenderer },
        { field: 'status',   headerName: 'Estado',       width: 140, cellRenderer: StatusRenderer },
        { field: 'assignee_id', headerName: 'Responsable', width: 130, cellRenderer: AssigneeRenderer },
        { field: 'due_date', headerName: 'Entrega',      width: 120, cellRenderer: DateRenderer },
        { field: 'priority', headerName: 'Prioridad',    width: 120, cellRenderer: PriorityRenderer },
    ], []);

    return (
        <div className="min-w-0 rounded-lg overflow-hidden border border-[hsl(var(--border))] dark:border-white/10 shadow-sm" style={{ height: Math.min(Math.max(tasks.length * 36 + 40, 200), 600) }}>
            <AgGridReact
                ref={gridRef}
                theme={isDark ? agGridCompactDarkTheme : agGridCompactLightTheme}
                rowData={tasks}
                columnDefs={colDefs}
                defaultColDef={{ resizable: true, sortable: true, suppressMovable: false, minWidth: 96 }}
                getRowId={(p) => String(p.data.id)}
                suppressCellFocus
            />
        </div>
    );
}
