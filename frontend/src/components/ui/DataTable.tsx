"use client";

import React, { useState } from 'react';
import {
    useReactTable,
    getCoreRowModel,
    getSortedRowModel,
    flexRender,
    SortingState,
} from '@tanstack/react-table';
import { ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react';
import clsx from 'clsx';

interface DataTableProps {
    data: any[];
    columns: any[];
    onRowClick?: (row: any) => void;
}

export function DataTable({ data, columns, onRowClick }: DataTableProps) {
    const [sorting, setSorting] = useState<SortingState>([]);

    const table = useReactTable({
        data,
        columns,
        state: { sorting },
        onSortingChange: setSorting,
        getCoreRowModel: getCoreRowModel(),
        getSortedRowModel: getSortedRowModel(),
    });

    return (
        <div className="flex-1 overflow-auto bg-white dark:bg-[#1e1f21]">
            <table className="w-full text-left border-collapse min-w-[800px]">
                <thead className="sticky top-0 bg-slate-50 dark:bg-black/20 z-10 shadow-sm">
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
                                            "py-2.5 px-4 text-[10px] font-black uppercase tracking-widest text-slate-400 border-b border-slate-200 dark:border-white/5 bg-slate-50 dark:bg-black/20",
                                            canSort && "cursor-pointer hover:bg-slate-100 dark:hover:bg-white/5 select-none transition-colors"
                                        )}
                                        style={{ width: header.getSize() !== 150 ? header.getSize() : 'auto' }}
                                    >
                                        <div className="flex items-center gap-1">
                                            {flexRender(header.column.columnDef.header, header.getContext())}
                                            {canSort && (
                                                <div className="flex-shrink-0 text-slate-300">
                                                    {{
                                                        asc: <ArrowUp size={12} className="text-blue-500" />,
                                                        desc: <ArrowDown size={12} className="text-blue-500" />,
                                                    }[isSorted as string] ?? <ArrowUpDown size={12} className="opacity-0 group-hover:opacity-100" />}
                                                </div>
                                            )}
                                        </div>
                                    </th>
                                );
                            })}
                        </tr>
                    ))}
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-white/5">
                    {table.getRowModel().rows.map((row) => (
                        <tr 
                            key={row.id} 
                            onClick={() => onRowClick?.(row.original)}
                            className="hover:bg-slate-50 dark:hover:bg-white/5 transition-colors cursor-pointer group"
                        >
                            {row.getVisibleCells().map((cell) => (
                                <td key={cell.id} className="py-1 px-4">
                                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                                </td>
                            ))}
                        </tr>
                    ))}
                    {table.getRowModel().rows.length === 0 && (
                        <tr>
                            <td colSpan={columns.length} className="h-24 text-center text-slate-400 font-medium">
                                No se encontraron resultados.
                            </td>
                        </tr>
                    )}
                </tbody>
            </table>
        </div>
    );
}
