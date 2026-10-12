"use client";

import { ReactNode } from 'react';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { ViewType } from '@/components/ViewSwitcher';
import type { AppIcon } from '@/types/icons';
import { UserMenuDropdown } from '@/components/WorkspaceLayout';

export interface BreadcrumbOption {
    label: string;
    href?: string;
    icon?: AppIcon;
}

interface ProjectsShellProps {
    breadcrumbs: BreadcrumbOption[];
    viewOptions?: ViewType[];
    viewType?: ViewType;
    onViewChange?: (view: ViewType) => void;
    onSearch?: (term: string) => void;
    searchValue?: string;
    rightActions?: ReactNode;
    children: ReactNode;
}

export default function ProjectsShell({
    breadcrumbs,
    viewOptions,
    viewType,
    onViewChange,
    onSearch,
    searchValue,
    rightActions,
    children
}: ProjectsShellProps) {
    return (
        <>
            <WorkspaceToolbar
                breadcrumbs={breadcrumbs}
                viewType={viewType}
                setViewType={onViewChange}
                availableViews={viewOptions}
                onSearch={onSearch}
                searchValue={searchValue}
                rightActions={
                    <div className="flex items-center gap-1.5 shrink-0">
                        {rightActions}
                        <div className="w-px h-4 bg-[hsl(var(--surface-3))] dark:bg-white/10 mx-0.5 shrink-0" />
                        <UserMenuDropdown />
                    </div>
                }
            />
            <section aria-label="Contenido de proyectos" className="flex-1 overflow-hidden h-full">
                <div className={
                    viewType && ['board', 'kanban', 'gantt', 'calendar', 'wiki'].includes(viewType)
                        ? "h-full animate-fade-in overflow-y-auto"
                        : "p-4 lg:p-4 space-y-3 animate-fade-in h-full overflow-y-auto"
                }>
                    {children}
                </div>
            </section>
        </>
    );
}
