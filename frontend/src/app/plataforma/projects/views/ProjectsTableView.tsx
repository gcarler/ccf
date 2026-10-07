'use client';

import { useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { DataTable } from '@/components/ui/DataTable';
import { InlineTextInput } from '@/components/ui/inline-editors/InlineTextInput';
import { PROJECT_TITLE_MAX_LENGTH } from '@/lib/projects/constants';
import { InlineProjectStatusPicker } from '@/components/ui/inline-editors/InlineProjectStatusPicker';
import { formatDate } from '@/components/projects/utils';
import { normalizeProjectColor } from '@/lib/projects/palette';
import { ArrowUpRight } from 'lucide-react';
import type { ProjectRecord } from '@/types/projects';
import type { ColumnDef } from '@tanstack/react-table';
import type { BaseProjectViewProps } from './types';

interface ProjectsTableViewProps extends BaseProjectViewProps {}

export default function ProjectsTableView({ projects, onUpdate }: ProjectsTableViewProps) {
    const router = useRouter();

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
                                className="size-8 rounded-lg flex items-center justify-center font-semibold text-[hsl(var(--primary-foreground))]"
                                style={{ backgroundColor: normalizeProjectColor(project.color) }}
                            >
                                {project.title.slice(0, 2).toUpperCase()}
                            </div>
                            <div className="min-w-0">
                                <InlineTextInput
                                    value={project.title}
                                    onChange={(v) => onUpdate(project.id, { title: v })}
                                    placeholder="Título del proyecto"
                                    maxLength={PROJECT_TITLE_MAX_LENGTH}
                                    className="text-base font-bold text-[hsl(var(--foreground))] truncate"
                                    inputClassName="text-base"
                                />
                                <p className="text-xs text-[hsl(var(--muted-foreground))] truncate">
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
                accessorKey: 'task_count',
                header: 'Tareas',
                cell: ({ row }) => {
                    const tasks = row.original.task_count ?? row.original.tasks?.length ?? 0;
                    return (
                        <span className="text-sm font-semibold text-[hsl(var(--foreground))]">
                            {tasks}
                        </span>
                    );
                },
            },
            {
                accessorKey: 'created_at',
                header: 'Creado',
                cell: ({ getValue }) => (
                    <span className="text-sm text-[hsl(var(--muted-foreground))]">
                        {formatDate(getValue() as string, { locale: 'es-PE' })}
                    </span>
                ),
            },
            {
                id: 'actions',
                header: 'Acción',
                cell: ({ row }) => (
                    <button
                        type="button"
                        onClick={() => router.push(`/plataforma/projects/${row.original.id}?view=list`)}
                        aria-label={`Abrir proyecto ${row.original.title}`}
                        className="inline-flex size-9 items-center justify-center rounded-md text-[hsl(var(--muted-foreground))] transition-colors hover:bg-[hsl(var(--surface-2))] hover:text-[hsl(var(--foreground))] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsl(var(--ring))]"
                    >
                        <ArrowUpRight size={16} aria-hidden="true" />
                    </button>
                ),
            },
        ],
        [onUpdate, router]
    );

    return (
        <div className="pb-4">
            <DataTable
                columns={columns}
                data={projects}
            />
        </div>
    );
}
