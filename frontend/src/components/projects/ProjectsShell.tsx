"use client";

import { ComponentType, ReactNode } from 'react';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { ViewType } from '@/components/ViewSwitcher';

export interface BreadcrumbOption {
    label: string;
    href?: string;
    icon?: ComponentType<{ size?: number | string }>;

}

interface ProjectsShellProps {
    breadcrumbs: BreadcrumbOption[];
    viewOptions?: ViewType[];
    viewType?: ViewType;
    onViewChange?: (view: ViewType) => void;
    onSearch?: (term: string) => void;
    rightActions?: ReactNode;
    children: ReactNode;
}

export default function ProjectsShell({
    breadcrumbs,
    viewOptions,
    viewType,
    onViewChange,
    onSearch,
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
                rightActions={rightActions}
            />
            <main className="flex-1 overflow-hidden h-full">
                <div className={
                    viewType && ['board', 'kanban', 'gantt', 'calendar', 'wiki'].includes(viewType)
                        ? "h-full animate-fade-in overflow-y-auto"
                        : "p-4 lg:p-4 space-y-3 animate-fade-in h-full overflow-y-auto"
                }>
                    {children}
                </div>
            </main>
        </>
    );
}
