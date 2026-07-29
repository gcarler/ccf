'use client';

import { useMemo } from 'react';
import { DataTable } from '@/components/ui/DataTable';
import { InlineTextInput } from '@/components/ui/inline-editors/InlineTextInput';
import { InlineProjectStatusPicker } from '@/components/ui/inline-editors/InlineProjectStatusPicker';
import { formatDate } from '@/components/projects/utils';
import type { ProjectRecord } from '@/types/projects';
import type { ColumnDef } from '@tanstack/react-table';
import type { BaseProjectViewProps } from './types';

interface ProjectsTableViewProps extends BaseProjectViewProps {}

export default function ProjectsTableView({ projects, onUpdate }: ProjectsTableViewProps) {
    const columns = useMemo<ColumnDef<ProjectRecord>[]>(
        () => [
            {
                accessorKey: 'title',
                header: 'Proyecto',
                cell: ({ row }) => {
                    const project = row.original;
                    return (
                        <div className="flex items-center gap-3">
                            <div
                                className="size-8 rounded-lg flex items-center justify-center font-semibold text-white"
                                style={{ backgroundColor: project.color || 'hsl(var(--primary))' }}
                            >
                                {project.title.slice(0, 2).toUpperCase()}
                            </div>
                            <div className="min-w-0">
                                <InlineTextInput
                                    value={project.title}
                                    onChange={(v) => onUpdate(project.id, { title: v })}
                                    placeholder="Título del proyecto"
                                    className="text-base font-bold text-[hsl(var(--text-primary))] dark:text-white truncate"
                                    inputClassName="text-base"
                                />
                                <p className="text-xs text-[hsl(var(--text-secondary))] truncate">
                                    {project.description || 'Sin descripción'}
                                </p>
                            </div>
                        </div>
                    );
                },
            },
            {
                accessorKey: 'status',
                header: 'Estado',
                cell: ({ row }) => {
                    const project = row.original;
                    return (
                        <InlineProjectStatusPicker
                            value={project.status || 'active'}
                            onChange={(v) => onUpdate(project.id, { status: v })}
                            size="sm"
                        />
                    );
                },
            },
            {
                accessorKey: 'tasks',
                header: 'Tareas',
                cell: ({ row }) => {
                    const tasks = row.original.tasks?.length || 0;
                    return (
                        <span className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">
                            {tasks}
                        </span>
                    );
                },
            },
            {
                accessorKey: 'created_at',
                header: 'Creado',
                cell: ({ getValue }) => (
                    <span className="text-sm text-[hsl(var(--text-secondary))]">
                        {formatDate(getValue() as string)}
                    </span>
                ),
            },
        ],
        [onUpdate]
    );

    return (
        <div className="pb-4">
            <DataTable columns={columns} data={projects} />
        </div>
    );
}
