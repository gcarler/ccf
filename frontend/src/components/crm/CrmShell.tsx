"use client";

import React from 'react';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
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
        <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-hidden animate-fade-in">
            <WorkspaceToolbar
                breadcrumbs={breadcrumbs}
                viewType={viewType}
                setViewType={onViewChange}
                availableViews={viewOptions}
                onSearch={onSearch}
                rightActions={rightActions}
            />
            <main className="flex-1 overflow-y-auto scrollbar-thin">
                <div className="p-4 lg:p-6 space-y-6">
                    {children}
                </div>
            </main>
        </div>
    );
}
