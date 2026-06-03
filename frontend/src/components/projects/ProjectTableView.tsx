"use client";

import React, { useMemo, useRef, useState, useEffect } from 'react';
import { AgGridReact } from 'ag-grid-react';
import { AllCommunityModule, ModuleRegistry, themeQuartz, ColDef } from 'ag-grid-community';
import clsx from 'clsx';
import type { ProjectTaskRecord } from '@/types/projects';

ModuleRegistry.registerModules([AllCommunityModule]);

const STATUS_MAP: Record<string, { label: string; cls: string }> = {
    completed:   { label: 'Completado',  cls: 'bg-emerald-50 border-emerald-100 text-emerald-600' },
    in_progress: { label: 'En progreso', cls: 'bg-blue-50 border-blue-100 text-[hsl(var(--primary))]' },
    blocked:     { label: 'Bloqueado',   cls: 'bg-rose-50 border-rose-100 text-rose-600' },
    todo:        { label: 'Pendiente',   cls: 'bg-amber-50 border-amber-100 text-amber-700' },
};

const PRIORITY_MAP: Record<string, { label: string; cls: string }> = {
    urgent: { label: 'Urgente', cls: 'text-rose-600' },
    high:   { label: 'Alta',    cls: 'text-orange-500' },
    medium: { label: 'Media',   cls: 'text-amber-500' },
    normal: { label: 'Normal',  cls: 'text-[hsl(var(--primary))]' },
    low:    { label: 'Baja',    cls: 'text-slate-400' },
};

function TitleRenderer({ value, data }: any) {
    const st = data?.status === 'completed';
    return (
        <div className="flex items-center gap-2.5">
            <div className={clsx('size-4 rounded-full border-2 flex items-center justify-center flex-shrink-0',
                st ? 'bg-emerald-500 border-emerald-500 text-white' : 'border-slate-200 dark:border-white/20')}>
                {st && <span className="text-[8px] font-bold">✓</span>}
            </div>
            <span className="text-[13px] font-bold text-slate-700 dark:text-slate-200 truncate">{value}</span>
        </div>
    );
}

function StatusRenderer({ value }: any) {
    const s = STATUS_MAP[value?.toLowerCase()] ?? STATUS_MAP.todo;
    return <span className={clsx('px-2.5 py-0.5 rounded-lg text-[10px] font-semibold uppercase tracking-wide border', s.cls)}>{s.label}</span>;
}

function PriorityRenderer({ value }: any) {
    const p = PRIORITY_MAP[value?.toLowerCase()] ?? PRIORITY_MAP.normal;
    return <span className={clsx('text-[11px] font-bold uppercase tracking-wide', p.cls)}>⚑ {p.label}</span>;
}

function DateRenderer({ value }: any) {
    if (!value) return <span className="text-slate-300 dark:text-slate-600 text-xs">—</span>;
    return <span className="text-[11px] font-bold text-slate-400">{new Date(value).toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: '2-digit' })}</span>;
}

const lightTheme = themeQuartz.withParams({ fontFamily: 'inherit', fontSize: 12, rowHeight: 36, headerHeight: 36, backgroundColor: '#ffffff', foregroundColor: '#1e293b', borderColor: '#e2e8f0', oddRowBackgroundColor: '#f8fafc', headerBackgroundColor: '#f1f5f9', headerTextColor: '#475569', selectedRowBackgroundColor: '#eef2ff', accentColor: '#6366f1', cellHorizontalPaddingScale: 0.8 });
const darkTheme  = themeQuartz.withParams({ fontFamily: 'inherit', fontSize: 12, rowHeight: 36, headerHeight: 36, backgroundColor: 'rgb(15 23 42)', foregroundColor: '#e2e8f0', borderColor: 'rgba(255,255,255,0.08)', oddRowBackgroundColor: 'rgba(255,255,255,0.02)', headerBackgroundColor: 'rgba(255,255,255,0.04)', headerTextColor: '#94a3b8', selectedRowBackgroundColor: 'rgba(99,102,241,0.15)', accentColor: '#6366f1', cellHorizontalPaddingScale: 0.8 });

export default function ProjectTableView({ tasks }: { tasks: ProjectTaskRecord[] }) {
    const gridRef = useRef<AgGridReact>(null);
    const [isDark, setIsDark] = useState(false);

    useEffect(() => {
        const check = () => setIsDark(document.documentElement.classList.contains('dark'));
        check();
        const obs = new MutationObserver(check);
        obs.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
        return () => obs.disconnect();
    }, []);

    const colDefs = useMemo<ColDef[]>(() => [
        { field: 'title',    headerName: 'Tarea',        flex: 2, cellRenderer: TitleRenderer },
        { field: 'status',   headerName: 'Estado',       width: 140, cellRenderer: StatusRenderer },
        { field: 'assignee_id', headerName: 'Responsable', width: 130, valueFormatter: () => 'Sin asignar', cellStyle: { color: '#94a3b8', fontSize: '11px', fontWeight: '500' } },
        { field: 'due_date', headerName: 'Entrega',      width: 120, cellRenderer: DateRenderer },
        { field: 'priority', headerName: 'Prioridad',    width: 120, cellRenderer: PriorityRenderer },
    ], []);

    return (
        <div className="rounded-lg overflow-hidden border border-slate-100 dark:border-white/10 shadow-sm" style={{ height: Math.min(Math.max(tasks.length * 36 + 40, 200), 600) }}>
            <AgGridReact
                ref={gridRef}
                theme={isDark ? darkTheme : lightTheme}
                rowData={tasks}
                columnDefs={colDefs}
                defaultColDef={{ resizable: true, sortable: true, suppressMovable: false }}
                getRowId={(p) => String(p.data.id)}
                suppressCellFocus
            />
        </div>
    );
}
