"use client";

import '@/lib/agGrid';
import React, { useMemo, useRef, useState, useEffect } from 'react';
import { AgGridReact } from 'ag-grid-react';
import { themeQuartz, ColDef } from 'ag-grid-community';

const lightTheme = themeQuartz.withParams({ fontFamily: 'inherit', fontSize: 12, rowHeight: 40, headerHeight: 36, backgroundColor: 'hsl(var(--bg-primary))', foregroundColor: 'hsl(var(--text-primary))', borderColor: 'hsl(var(--border))', oddRowBackgroundColor: 'hsl(var(--surface-1))', headerBackgroundColor: 'hsl(var(--surface-2))', headerTextColor: 'hsl(var(--text-secondary))', selectedRowBackgroundColor: 'hsl(var(--primary)/0.1)', accentColor: 'hsl(var(--primary))', cellHorizontalPaddingScale: 0.8 });
const darkTheme  = themeQuartz.withParams({ fontFamily: 'inherit', fontSize: 12, rowHeight: 40, headerHeight: 36, backgroundColor: 'hsl(var(--admin-bg-secondary))', foregroundColor: 'hsl(var(--text-secondary))', borderColor: 'hsla(0,0%,100%,0.08)', oddRowBackgroundColor: 'hsla(0,0%,100%,0.02)', headerBackgroundColor: 'hsla(0,0%,100%,0.04)', headerTextColor: 'hsl(var(--text-secondary))', selectedRowBackgroundColor: 'hsla(var(--primary-hsl),0.15)', accentColor: 'hsl(var(--primary))', cellHorizontalPaddingScale: 0.8 });

interface Props {
    personas: any[];
    search: string;
    onRowClick: (persona: any) => void;
    isList?: boolean;
}

function AvatarNameRenderer({ data }: any) {
    const initials = data?.nombre_completo?.charAt(0) ?? '';
    return (
        <div className="flex items-center gap-2.5 h-full">
            <div className="size-7 rounded-md bg-gradient-to-br from-[hsl(var(--info))] to-[hsl(var(--info))] dark:from-[hsl(var(--info)/40%)] dark:to-[hsl(var(--info)/20%)] text-[hsl(var(--primary))] flex items-center justify-center font-bold text-xs flex-shrink-0">
                {initials}
            </div>
            <div>
                <div className="text-[13px] font-bold text-[hsl(var(--text-primary))] dark:text-white leading-tight">{data?.nombre_completo}</div>
                <div className="text-[10px] text-[hsl(var(--text-secondary))]">#{data?.id}</div>
            </div>
        </div>
    );
}

function RoleRenderer({ value }: any) {
    const isLeader = String(value ?? '').toLowerCase().includes('líder') || String(value ?? '').toLowerCase().includes('lider');
    return (
        <span className={`px-2.5 py-0.5 rounded-lg text-[10px] font-bold uppercase tracking-wider ${isLeader ? 'bg-[hsl(var(--warning)/0.15)] text-[hsl(var(--warning))] dark:bg-[hsl(var(--warning)/0.2)]' : 'bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))] dark:bg-[hsl(var(--primary)/0.15)]'}`}>
            {value || 'Persona'}
        </span>
    );
}

export default function CrmTableView({ personas, search, onRowClick, isList = false }: Props) {
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
        () => personas.filter((m) => (m.nombre_completo || '').toLowerCase().includes(search.toLowerCase())),
        [personas, search]
    );

    const colDefs = useMemo<ColDef[]>(() => {
        const cols: ColDef[] = [
            { headerName: 'Persona', flex: 2, cellRenderer: AvatarNameRenderer },
            { field: 'email', headerName: 'Email', flex: 1, cellStyle: { fontSize: '12px', color: 'hsl(var(--text-secondary))' } },
            { field: 'phone', headerName: 'Teléfono', width: 140, cellStyle: { fontSize: '12px', color: 'hsl(var(--text-secondary))' } },
            { field: 'church_role', headerName: 'Rol', width: 140, cellRenderer: RoleRenderer },
        ];
        if (!isList) {
            cols.push(
                { field: 'spiritual_status', headerName: 'Estado Espiritual', width: 160, cellStyle: { fontSize: '11px', fontWeight: '600', color: 'hsl(var(--text-secondary))', textTransform: 'uppercase', letterSpacing: '0.05em' } },
            );
        }
        return cols;
    }, [isList]);

    return (
        <div className="h-full min-w-0 rounded-lg overflow-hidden border border-[hsl(var(--border))] dark:border-white/10 shadow-sm">
            <AgGridReact
                ref={gridRef}
                theme={isDark ? darkTheme : lightTheme}
                rowData={filtered}
                columnDefs={colDefs}
                defaultColDef={{ resizable: true, sortable: true, filter: true, minWidth: 96 }}
                getRowId={(p) => String(p.data.id)}
                onRowClicked={(e) => onRowClick(e.data)}
                rowStyle={{ cursor: 'pointer' }}
                suppressCellFocus
                domLayout="autoHeight"
            />
        </div>
    );
}
