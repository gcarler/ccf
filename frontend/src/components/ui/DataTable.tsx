"use client";

import React from 'react';
import { ColumnDef } from '@tanstack/react-table';
import { DSTable } from '@/design';

interface DataTableProps<TData = Record<string, unknown>, TValue = unknown> {
    data: TData[];
    columns: ColumnDef<TData, TValue>[];
    onRowClick?: (row: TData) => void;
    /** Activa el menú "Columnas" (checklist de visibilidad) — ver getVisibleLeafColumns(). */
    enableColumnVisibility?: boolean;
    /** Activa la columna inicial de checkboxes para selección de filas (bulk actions). */
    enableRowSelection?: boolean;
    /** Callback con las filas seleccionadas cuando enableRowSelection está activo. */
    onSelectionChange?: (selectedRows: TData[]) => void;
}

/**
 * @note Obsolete: use `DSTable` from `@/design` instead.
 * `DataTable` is now a thin wrapper kept for backwards compatibility.
 */
export function DataTable<TData = Record<string, unknown>, TValue = unknown>({
    data,
    columns,
    onRowClick,
    enableColumnVisibility = false,
    enableRowSelection = false,
    onSelectionChange,
}: DataTableProps<TData, TValue>) {
    return (
        <DSTable
            data={data}
            columns={columns}
            onRowClick={onRowClick}
            stickyHeader
            cursorPointer
            emptyMessage="No se encontraron resultados."
            className="flex-1 min-w-[620px] md:min-w-[800px] bg-[hsl(var(--bg-primary))]"
            enableColumnVisibility={enableColumnVisibility}
            enableRowSelection={enableRowSelection}
            onSelectionChange={onSelectionChange}
        />
    );
}
