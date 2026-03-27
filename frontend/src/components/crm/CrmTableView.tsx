"use client";

import React, { useMemo } from 'react';
import { DataTable } from '@/components/ui/DataTable';
import type { ColumnDef } from '@tanstack/react-table';

interface CrmTableViewProps {
    members: any[];
    search: string;
    columns: ColumnDef<any>[];
    onRowClick: (member: any) => void;
}

export default function CrmTableView({ members, search, columns, onRowClick }: CrmTableViewProps) {
    const filtered = useMemo(
        () => members.filter((m) => m.name.toLowerCase().includes(search.toLowerCase())),
        [members, search]
    );

    return (
        <div className="h-full flex flex-col">
            <DataTable data={filtered} columns={columns} onRowClick={onRowClick} />
        </div>
    );
}
