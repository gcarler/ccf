"use client";

import React from 'react';
import { ColumnDef } from '@tanstack/react-table';
import { DSTable } from '@/design';

interface DataTableProps {
    data: any[];
    columns: ColumnDef<any, any>[];
    onRowClick?: (row: any) => void;
}

/**
 * @deprecated Use `DSTable` from `@/design` instead.
 * `DataTable` is now a thin wrapper kept for backwards compatibility.
 */
export function DataTable({ data, columns, onRowClick }: DataTableProps) {
    return (
        <DSTable
            data={data}
            columns={columns}
            onRowClick={onRowClick}
            stickyHeader
            cursorPointer
            emptyMessage="No se encontraron resultados."
            className="flex-1 min-w-[620px] md:min-w-[800px] bg-[hsl(var(--bg-primary))]"
        />
    );
}
