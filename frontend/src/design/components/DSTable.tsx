"use client";

import React, { useState } from 'react';
import {
    useReactTable,
    getCoreRowModel,
    getSortedRowModel,
    flexRender,
    SortingState,
    ColumnDef,
} from '@tanstack/react-table';
import { ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react';
import clsx from 'clsx';
import { typography } from '../tokens';

interface DSTableProps<T> {
    data: T[];
    columns: ColumnDef<T, any>[];
    sortable?: boolean;
    onRowClick?: (row: T) => void;
    emptyMessage?: string;
    compact?: boolean;
}

export function DSTable<T>({
    data,
    columns,
    sortable = true,
    onRowClick,
    emptyMessage = 'Sin datos',
    compact = false,
}: DSTableProps<T>) {
    const [sorting, setSorting] = useState<SortingState>([]);

    const table = useReactTable({
        data,
        columns,
        state: sortable ? { sorting } : undefined,
        onSortingChange: sortable ? setSorting : undefined,
        getCoreRowModel: getCoreRowModel(),
        getSortedRowModel: sortable ? getSortedRowModel() : undefined,
    });

    return (
        <div className="w-full overflow-auto">
            <table
                className="w-full text-left border-collapse"
                style={{ fontFamily: typography.family }}
            >
                <thead>
                    {table.getHeaderGroups().map((headerGroup) => (
                        <tr key={headerGroup.id}>
                            {headerGroup.headers.map((header) => {
                                const canSort = header.column.getCanSort();
                                const isSorted = header.column.getIsSorted();

                                return (
                                    <th
                                        key={header.id}
                                        onClick={header.column.getToggleSortingHandler()}
                                        className={clsx(
                                            'text-[9px] font-semibold uppercase tracking-wide',
                                            'text-[hsl(var(--text-secondary))]',
                                            'border-b border-[hsl(var(--border))] dark:border-white/5',
                                            'bg-[hsl(var(--surface-1))] dark:bg-black/20',
                                            compact ? 'px-2 py-1.5' : 'px-3 py-2',
                                            canSort && 'cursor-pointer hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 select-none transition-colors'
                                        )}
                                        style={{ width: header.getSize() !== 150 ? header.getSize() : 'auto' }}
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
                                colSpan={columns.length}
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
                                    onRowClick && 'cursor-pointer'
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
