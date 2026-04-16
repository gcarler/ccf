"use client";

import React from 'react';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import { ViewType } from '@/components/ViewSwitcher';

export interface BreadcrumbOption {
    label: string;
    href?: string;
    icon?: any;
}

interface CrmShellProps {
    breadcrumbs: BreadcrumbOption[];
    viewOptions?: ViewType[];
    viewType?: ViewType;
    onViewChange?: (view: ViewType) => void;
    onSearch?: (term: string) => void;
    rightActions?: React.ReactNode;
    children: React.ReactNode;
}

export default function CrmShell({
    breadcrumbs,
    viewOptions,
    viewType,
    onViewChange,
    onSearch,
    rightActions,
    children
}: CrmShellProps) {
    return (
        <WorkspaceLayout
            breadcrumbs={breadcrumbs}
            availableViews={viewOptions}
            viewType={viewType}
            setViewType={onViewChange}
            onSearch={onSearch}
            rightActions={rightActions}
        >
            <main className={viewType && ['board', 'kanban', 'gantt', 'calendar', 'wiki'].includes(viewType) ? "flex-1 overflow-hidden h-full" : "flex-1 overflow-y-auto scrollbar-thin"}>
                <div className={viewType && ['board', 'kanban', 'gantt', 'calendar', 'wiki'].includes(viewType) ? "h-full animate-fade-in" : "p-4 lg:p-6 space-y-6 animate-fade-in"}>
                    {children}
                </div>
            </main>
        </WorkspaceLayout>
    );
}
