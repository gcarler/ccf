"use client";

import React, { useMemo, useRef, useState, useEffect } from 'react';
import { AgGridReact } from 'ag-grid-react';
import { AllCommunityModule, ModuleRegistry, themeQuartz, ColDef } from 'ag-grid-community';

ModuleRegistry.registerModules([AllCommunityModule]);

const lightTheme = themeQuartz.withParams({ fontFamily: 'inherit', fontSize: 12, rowHeight: 40, headerHeight: 36, backgroundColor: '#ffffff', foregroundColor: '#1e293b', borderColor: '#e2e8f0', oddRowBackgroundColor: '#f8fafc', headerBackgroundColor: '#f1f5f9', headerTextColor: '#475569', selectedRowBackgroundColor: '#eef2ff', accentColor: '#6366f1', cellHorizontalPaddingScale: 0.8 });
const darkTheme  = themeQuartz.withParams({ fontFamily: 'inherit', fontSize: 12, rowHeight: 40, headerHeight: 36, backgroundColor: 'rgb(15 23 42)', foregroundColor: '#e2e8f0', borderColor: 'rgba(255,255,255,0.08)', oddRowBackgroundColor: 'rgba(255,255,255,0.02)', headerBackgroundColor: 'rgba(255,255,255,0.04)', headerTextColor: '#94a3b8', selectedRowBackgroundColor: 'rgba(99,102,241,0.15)', accentColor: '#6366f1', cellHorizontalPaddingScale: 0.8 });

interface Props {
    members: any[];
    search: string;
    onRowClick: (member: any) => void;
    isList?: boolean;
}

function AvatarNameRenderer({ data }: any) {
    const initials = data?.nombre_completo?.charAt(0) ?? '';
    return (
        <div className="flex items-center gap-2.5 h-full">
            <div className="size-7 rounded-md bg-gradient-to-br from-blue-100 to-blue-200 dark:from-blue-900/40 dark:to-blue-800/20 text-[hsl(var(--primary))] flex items-center justify-center font-bold text-xs flex-shrink-0">
                {initials}
            </div>
            <div>
                <div className="text-[13px] font-bold text-slate-900 dark:text-white leading-tight">{data?.nombre_completo}</div>
                <div className="text-[10px] text-slate-400">#{data?.id}</div>
            </div>
        </div>
    );
}

function RoleRenderer({ value }: any) {
    const isLeader = String(value ?? '').toLowerCase().includes('líder') || String(value ?? '').toLowerCase().includes('lider');
    return (
        <span className={`px-2.5 py-0.5 rounded-lg text-[10px] font-bold uppercase tracking-wider ${isLeader ? 'bg-orange-100 text-orange-600 dark:bg-orange-900/30' : 'bg-blue-50 text-[hsl(var(--primary))] dark:bg-blue-900/30'}`}>
            {value || 'Miembro'}
        </span>
    );
}

export default function CrmTableView({ members, search, onRowClick, isList = false }: Props) {
    const gridRef = useRef<AgGridReact>(null);
    const [isDark, setIsDark] = useState(false);

    useEffect(() => {
        const check = () => setIsDark(document.documentElement.classList.contains('dark'));
        check();
        const obs = new MutationObserver(check);
        obs.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
        return () => obs.disconnect();
    }, []);

    const filtered = useMemo(
        () => members.filter((m) => (m.nombre_completo || '').toLowerCase().includes(search.toLowerCase())),
        [members, search]
    );

    const colDefs = useMemo<ColDef[]>(() => {
        const cols: ColDef[] = [
            { headerName: 'Miembro', flex: 2, cellRenderer: AvatarNameRenderer },
            { field: 'email', headerName: 'Email', flex: 1, cellStyle: { fontSize: '12px', color: '#64748b' } },
            { field: 'phone', headerName: 'Teléfono', width: 140, cellStyle: { fontSize: '12px', color: '#64748b' } },
            { field: 'church_role', headerName: 'Rol', width: 140, cellRenderer: RoleRenderer },
        ];
        if (!isList) {
            cols.push(
                { field: 'spiritual_status', headerName: 'Estado Espiritual', width: 160, cellStyle: { fontSize: '11px', fontWeight: '600', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' } },
            );
        }
        return cols;
    }, [isList]);

    return (
        <div className="h-full rounded-lg overflow-hidden border border-slate-200 dark:border-white/10 shadow-sm">
            <AgGridReact
                ref={gridRef}
                theme={isDark ? darkTheme : lightTheme}
                rowData={filtered}
                columnDefs={colDefs}
                defaultColDef={{ resizable: true, sortable: true, filter: true }}
                getRowId={(p) => String(p.data.id)}
                onRowClicked={(e) => onRowClick(e.data)}
                rowStyle={{ cursor: 'pointer' }}
                suppressCellFocus
                domLayout="autoHeight"
            />
        </div>
    );
}
