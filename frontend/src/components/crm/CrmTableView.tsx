"use client";

import { useMemo, useRef } from 'react';
import AgGridTable, { ColDef, type AgGridTableRef } from '@/components/ui/AgGridTable';



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
            <div className="size-7 rounded-md bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))] flex items-center justify-center font-bold text-xs flex-shrink-0">
                {initials}
            </div>
            <div>
                <div className="text-base font-bold text-[hsl(var(--foreground))] leading-tight">{data?.nombre_completo}</div>
                <div className="text-2xs text-[hsl(var(--muted-foreground))]">#{data?.id}</div>
            </div>
        </div>
    );
}

function RoleRenderer({ value }: any) {
    const isLeader = String(value ?? '').toLowerCase().includes('líder') || String(value ?? '').toLowerCase().includes('lider');
    return (
        <span className={`px-2.5 py-0.5 rounded-lg text-2xs font-bold uppercase tracking-wider ${isLeader ? 'bg-[hsl(var(--warning)/0.15)] text-[hsl(var(--warning))]' : 'bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))]'}`}>
            {value || 'Persona'}
        </span>
    );
}

export default function CrmTableView({ personas, search, onRowClick, isList = false }: Props) {
    const gridRef = useRef<AgGridTableRef>(null);

    const filtered = useMemo(
        () => personas.filter((m) => (m.nombre_completo || '').toLowerCase().includes(search.toLowerCase())),
        [personas, search]
    );

    const colDefs = useMemo<ColDef[]>(() => {
        const cols: ColDef[] = [
            { headerName: 'Persona', flex: 2, cellRenderer: AvatarNameRenderer },
            { field: 'email', headerName: 'Email', flex: 1, cellStyle: { fontSize: '12px', color: 'hsl(var(--muted-foreground))' } },
            { field: 'phone', headerName: 'Teléfono', width: 140, cellStyle: { fontSize: '12px', color: 'hsl(var(--muted-foreground))' } },
            { field: 'church_role', headerName: 'Rol', width: 140, cellRenderer: RoleRenderer },
        ];
        if (!isList) {
            cols.push(
                { field: 'spiritual_status', headerName: 'Estado Espiritual', width: 160, cellStyle: { fontSize: '11px', fontWeight: '600', color: 'hsl(var(--muted-foreground))', textTransform: 'uppercase', letterSpacing: '0.05em' } },
            );
        }
        return cols;
    }, [isList]);

    return (
        <div className="h-full min-w-0 rounded-lg overflow-hidden border border-[hsl(var(--border))] shadow-sm">
            <AgGridTable
                ref={gridRef}
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
