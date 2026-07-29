"use client";

import React, { useState, useMemo, useRef, useEffect } from 'react';
import {
    useReactTable,
    getCoreRowModel,
    getSortedRowModel,
    flexRender,
    SortingState,
    ColumnDef,
    VisibilityState,
    RowSelectionState,
    ColumnPinningState,
} from '@tanstack/react-table';
import { ArrowUpDown, ArrowUp, ArrowDown, Columns3, Check, ChevronDown } from 'lucide-react';
import clsx from 'clsx';

const TANSTACK_DEFAULT_WIDTH = 150;

interface DSTableProps<T> {
    data: T[];
    columns: ColumnDef<T, any>[];
    sortable?: boolean;
    onRowClick?: (row: T) => void;
    emptyMessage?: string;
    compact?: boolean;
    stickyHeader?: boolean;
    cursorPointer?: boolean;
    className?: string;
    /** Activa el menú "Columnas" (checklist de visibilidad) — ver getVisibleLeafColumns(). */
    enableColumnVisibility?: boolean;
    /** Activa la columna inicial de checkboxes para selección de filas (bulk actions). */
    enableRowSelection?: boolean;
    /** Callback con las filas seleccionadas cuando enableRowSelection está activo. */
    onSelectionChange?: (selectedRows: T[]) => void;
}

export function DSTable<T>({
    data,
    columns,
    sortable = true,
    onRowClick,
    emptyMessage = 'Sin datos',
    compact = false,
    stickyHeader,
    cursorPointer,
    className,
    enableColumnVisibility = false,
    enableRowSelection = false,
    onSelectionChange,
}: DSTableProps<T>) {
    const [sorting, setSorting] = useState<SortingState>([]);
    const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({});
    const [rowSelection, setRowSelection] = useState<RowSelectionState>({});
    const [columnMenuOpen, setColumnMenuOpen] = useState(false);
    const menuRef = useRef<HTMLDivElement>(null);

    // Click-outside cierra el menú de visibilidad de columnas.
    useEffect(() => {
        if (!columnMenuOpen) return;
        const handler = (e: MouseEvent) => {
            if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
                setColumnMenuOpen(false);
            }
        };
        document.addEventListener('mousedown', handler);
        return () => document.removeEventListener('mousedown', handler);
    }, [columnMenuOpen]);

    // Columna de selección (checkbox) al inicio — pin a izquierda para bulk actions.
    const selectionColumn = useMemo<ColumnDef<T, any>>(
        () => ({
            id: '__select',
            header: ({ table }) => (
                <input
                    type="checkbox"
                    aria-label="Seleccionar todas las filas"
                    checked={table.getIsAllRowsSelected()}
                    ref={(el) => {
                        if (el) el.indeterminate = table.getIsSomeRowsSelected();
                    }}
                    onChange={table.getToggleAllRowsSelectedHandler()}
                    onClick={(e) => e.stopPropagation()}
                    className="size-3.5 cursor-pointer accent-[hsl(var(--primary))]"
                />
            ),
            cell: ({ row }) => (
                <input
                    type="checkbox"
                    aria-label={`Seleccionar fila ${row.index + 1}`}
                    checked={row.getIsSelected()}
                    onChange={row.getToggleSelectedHandler()}
                    onClick={(e) => e.stopPropagation()}
                    className="size-3.5 cursor-pointer accent-[hsl(var(--primary))]"
                />
            ),
            enableSorting: false,
            size: 36,
        }),
        [],
    );

    const effectiveColumns = useMemo<ColumnDef<T, any>[]>(() => {
        if (!enableRowSelection) return columns;
        return [selectionColumn, ...columns];
    }, [columns, enableRowSelection, selectionColumn]);

    // Pin de la columna de selección a la izquierda para que permanezca visible al scroll horizontal.
    const columnPinning = useMemo<ColumnPinningState>(
        () => (enableRowSelection ? { left: ['__select'] } : {}),
        [enableRowSelection],
    );

    const table = useReactTable<T>({
        data,
        columns: effectiveColumns,
        state: {
            ...(sortable ? { sorting } : {}),
            columnVisibility,
            rowSelection: enableRowSelection ? rowSelection : undefined,
            columnPinning,
        },
        onSortingChange: sortable ? setSorting : undefined,
        onColumnVisibilityChange: setColumnVisibility,
        ...(enableRowSelection
            ? {
                  enableRowSelection: true,
                  onRowSelectionChange: setRowSelection,
              }
            : {}),
        getCoreRowModel: getCoreRowModel(),
        getSortedRowModel: sortable ? getSortedRowModel() : undefined,
    });

    // Notifica al padre cada vez que cambia la selección de filas.
    useEffect(() => {
        if (!enableRowSelection || !onSelectionChange) return;
        const selected = table.getSelectedRowModel().rows.map((r) => r.original);
        onSelectionChange(selected);
    }, [rowSelection, enableRowSelection, onSelectionChange, table]);

    return (
        <div className={clsx('w-full overflow-auto', className)}>
            {enableColumnVisibility && (
                <div className="flex justify-end mb-2">
                    <div className="relative" ref={menuRef}>
                        <button
                            type="button"
                            onClick={() => setColumnMenuOpen((v) => !v)}
                            className={clsx(
                                'inline-flex items-center gap-1.5 text-xs font-medium',
                                'px-2.5 py-1.5 rounded-md border',
                                'border-[hsl(var(--border))] dark:border-white/10',
                                'bg-[hsl(var(--surface-1))] dark:bg-black/20',
                                'text-[hsl(var(--text-primary))] dark:text-white',
                                'hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5',
                                'transition-colors',
                            )}
                            aria-haspopup="menu"
                            aria-expanded={columnMenuOpen}
                        >
                            <Columns3 size={12} />
                            Columnas
                            <ChevronDown
                                size={12}
                                className={clsx('transition-transform', columnMenuOpen && 'rotate-180')}
                            />
                        </button>
                        {columnMenuOpen && (
                            <div
                                role="menu"
                                aria-label="Visibilidad de columnas"
                                className={clsx(
                                    'absolute right-0 z-20 mt-1 w-56 max-h-72 overflow-y-auto',
                                    'rounded-md border shadow-lg',
                                    'border-[hsl(var(--border))] dark:border-white/10',
                                    'bg-[hsl(var(--surface-1))] dark:bg-black/40',
                                    'py-1',
                                )}
                            >
                                {/* Checklist de visibilidad: usa getVisibleLeafColumns()
                                     indirectamente via table.getAllLeafColumns() — toggle
                                     on/off por cada columna visible del usuario. */}
                                {table.getAllLeafColumns().map((column) => {
                                    if (column.id === '__select') return null;
                                    const visible = column.getIsVisible();
                                    return (
                                        <button
                                            key={column.id}
                                            type="button"
                                            role="menuitemcheckbox"
                                            aria-checked={visible}
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                column.toggleVisibility(!visible);
                                            }}
                                            className={clsx(
                                                'flex w-full items-center gap-2 px-3 py-1.5 text-xs text-left',
                                                'text-[hsl(var(--text-primary))] dark:text-white',
                                                'hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5',
                                                'transition-colors',
                                            )}
                                        >
                                            <span
                                                className={clsx(
                                                    'flex size-4 items-center justify-center rounded border',
                                                    visible
                                                        ? 'bg-[hsl(var(--primary))] border-[hsl(var(--primary))]'
                                                        : 'border-[hsl(var(--border))] dark:border-white/20',
                                                )}
                                            >
                                                {visible && <Check size={11} className="text-[hsl(var(--primary-foreground))]" />}
                                            </span>
                                            <span className="truncate">
                                                {typeof column.columnDef.header === 'string'
                                                    ? column.columnDef.header
                                                    : column.id}
                                            </span>
                                        </button>
                                    );
                                })}
                            </div>
                        )}
                    </div>
                </div>
            )}
            <table
                className="w-full text-left border-collapse font-sans"
            >
                <thead>
                    {table.getHeaderGroups().map((headerGroup) => (
                        <tr key={headerGroup.id} className={clsx(stickyHeader && 'sticky top-0 z-10 shadow-sm')}>
                            {headerGroup.headers.map((header) => {
                                const canSort = header.column.getCanSort();
                                const isSorted = header.column.getIsSorted();

                                return (
                                    <th
                                        key={header.id}
                                        onClick={header.column.getToggleSortingHandler()}
                                        className={clsx(
                                            'text-2xs font-semibold uppercase tracking-wide',
                                            'text-[hsl(var(--text-secondary))]',
                                            'border-b border-[hsl(var(--border))] dark:border-white/5',
                                            'bg-[hsl(var(--surface-1))] dark:bg-black/20',
                                            compact ? 'px-2 py-1.5' : 'px-3 py-2',
                                            canSort && 'cursor-pointer hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 select-none transition-colors'
                                        )}
                                        style={{ width: header.getSize() !== TANSTACK_DEFAULT_WIDTH ? header.getSize() : 'auto' }}
                                    >
                                        <div className="flex items-center gap-1.5">
                                            {flexRender(header.column.columnDef.header, header.getContext())}
                                            {canSort && (
                                                <span className="text-[hsl(var(--text-secondary))]">
                                                    {isSorted === 'asc' ? (
                                                        <ArrowUp size={10} />
                                                    ) : isSorted === 'desc' ? (
                                                        <ArrowDown size={10} />
                                                    ) : (
                                                        <ArrowUpDown size={10} className="opacity-50" />
                                                    )}
                                                </span>
                                            )}
                                        </div>
                                    </th>
                                );
                            })}
                        </tr>
                    ))}
                </thead>
                <tbody>
                    {table.getRowModel().rows.length === 0 ? (
                        <tr>
                            <td
                                colSpan={effectiveColumns.length}
                                className="px-3 py-8 text-center text-xs text-[hsl(var(--text-secondary))]"
                            >
                                {emptyMessage}
                            </td>
                        </tr>
                    ) : (
                        table.getRowModel().rows.map((row) => (
                            <tr
                                key={row.id}
                                onClick={() => onRowClick?.(row.original)}
                                className={clsx(
                                    'border-b border-[hsl(var(--border))] dark:border-white/5 last:border-0',
                                    'hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5',
                                    'transition-colors',
                                    (onRowClick || cursorPointer) && 'cursor-pointer',
                                    enableRowSelection && row.getIsSelected() && 'bg-[hsl(var(--surface-2))] dark:bg-white/5',
                                )}
                            >
                                {row.getVisibleCells().map((cell) => (
                                    <td
                                        key={cell.id}
                                        className={clsx(
                                            'text-xs text-[hsl(var(--text-primary))] dark:text-white',
                                            compact ? 'px-2 py-1.5' : 'px-3 py-2'
                                        )}
                                    >
                                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                                    </td>
                                ))}
                            </tr>
                        ))
                    )}
                </tbody>
            </table>
        </div>
    );
}
