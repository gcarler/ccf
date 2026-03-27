"use client";

import React from 'react';
import type { ColumnDef } from '@tanstack/react-table';
import { DataTable } from '@/components/ui/DataTable';
import type { ProjectRecord } from '@/types/projects';

interface ProjectTableViewProps {
    projects: ProjectRecord[];
    columns: ColumnDef<ProjectRecord>[];
    onRowClick: (project: ProjectRecord) => void;
}

export default function ProjectTableView({ projects, columns, onRowClick }: ProjectTableViewProps) {
    return (
        <div className="rounded-[2.5rem] border border-slate-200 dark:border-white/5 bg-white dark:bg-[#111418] shadow-xl overflow-hidden">
            <DataTable data={projects} columns={columns} onRowClick={onRowClick} />
        </div>
    );
}
