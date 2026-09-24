"use client";

import { useMemo, useRef } from 'react';
import AgGridTable, { ColDef, type AgGridTableRef } from '@/components/ui/AgGridTable';
import clsx from 'clsx';
import type { ProjectTaskRecord } from '@/types/projects';
import { getStatusOption, getPriorityOption } from '@/lib/projects/constants';

const STATUS_CLS: Record<string, string> = {
    completed:   'bg-[hsl(var(--success)/0.1)] border-[hsl(var(--success)/0.2)] text-[hsl(var(--success))]',
    in_progress: 'bg-[hsl(var(--info)/0.1)] border-[hsl(var(--info)/0.2)] text-[hsl(var(--info))]',
    review:      'bg-[hsl(var(--warning)/0.1)] border-[hsl(var(--warning)/0.2)] text-[hsl(var(--warning))]',
    todo:        'bg-[hsl(var(--surface-2))] border-[hsl(var(--border))] text-[hsl(var(--muted-foreground))]',
};

const PRIORITY_CLS: Record<string, string> = {
    urgent: 'text-[hsl(var(--destructive))]',
    high:   'text-[hsl(var(--warning))]',
    medium: 'text-[hsl(var(--primary))]',
    low:    'text-[hsl(var(--muted-foreground))]',
};

function TitleRenderer({ value, data }: { value: string; data: { id?: string; status?: string } }) {
    const st = data?.status === 'completed';
    return (
        <div className="flex items-center gap-2.5">
            <div className={clsx('size-4 rounded-full border-2 flex items-center justify-center flex-shrink-0',
                st ? 'bg-[hsl(var(--success))] border-[hsl(var(--success))] text-[hsl(var(--primary-foreground))]' : 'border-[hsl(var(--border))]')}>
                {st && <span className="text-2xs font-bold">✓</span>}
            </div>
            <span className="text-base font-bold text-[hsl(var(--foreground))] truncate">{value}</span>
        </div>
    );
}

function StatusRenderer({ value }: { value: string }) {
    const opt = getStatusOption(value?.toLowerCase());
    return <span className={clsx('px-2.5 py-0.5 rounded-lg text-2xs font-semibold uppercase tracking-wide border', STATUS_CLS[opt.value])}>{opt.label}</span>;
}

function PriorityRenderer({ value }: { value: string }) {
    const opt = getPriorityOption(value?.toLowerCase());
    return <span className={clsx('text-xs font-bold uppercase tracking-wide', PRIORITY_CLS[opt.value])}>⚑ {opt.label}</span>;
}

function AssigneeRenderer({ value }: { value: string | null | undefined }) {
    if (!value) return <span className="text-xs text-[hsl(var(--muted-foreground))]">—</span>;
    return (
        <span
            className="text-xs font-bold text-[hsl(var(--foreground))]"
            title={value}
        >
            {String(value).replace(/-/g, '').slice(0, 8)}
        </span>
    );
}

function DateRenderer({ value }: { value: string }) {
    if (!value) return <span className="text-[hsl(var(--muted-foreground))] text-xs">—</span>;
    return <span className="text-xs font-bold text-[hsl(var(--muted-foreground))]">{new Date(value).toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: '2-digit' })}</span>;
}

export default function ProjectTableView({ tasks }: { tasks: ProjectTaskRecord[] }) {
    const gridRef = useRef<AgGridTableRef>(null);

    const colDefs = useMemo<ColDef[]>(() => [
        { field: 'title',    headerName: 'Tarea',        flex: 2, cellRenderer: TitleRenderer },
        { field: 'status',   headerName: 'Estado',       width: 140, cellRenderer: StatusRenderer },
        { field: 'assignee_id', headerName: 'Responsable', width: 130, cellRenderer: AssigneeRenderer },
        { field: 'due_date', headerName: 'Entrega',      width: 120, cellRenderer: DateRenderer },
        { field: 'priority', headerName: 'Prioridad',    width: 120, cellRenderer: PriorityRenderer },
    ], []);

    // Inline height is dynamic (based on row count) and cannot be expressed with
    // static Tailwind classes. It is intentionally kept as an inline style.
    const height = Math.min(Math.max(tasks.length * 36 + 40, 200), 600);

    return (
        <div className="min-w-0 rounded-lg overflow-hidden border border-[hsl(var(--border))] shadow-sm" style={{ height }}>
            <AgGridTable
                ref={gridRef}
                density="compact"
                rowData={tasks}
                columnDefs={colDefs}
                defaultColDef={{ resizable: true, sortable: true, suppressMovable: false, minWidth: 96 }}
                getRowId={(p) => String(p.data.id)}
                suppressCellFocus
            />
        </div>
    );
}
