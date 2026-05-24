"use client";

import React from 'react';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { ViewType } from '@/components/ViewSwitcher';

export interface BreadcrumbOption {
    label: string;
    href?: string;
    icon?: any;
}

interface AdminShellProps {
    breadcrumbs: BreadcrumbOption[];
    viewOptions?: ViewType[];
    viewType?: ViewType;
    onViewChange?: (view: ViewType) => void;
    rightActions?: React.ReactNode;
    children: React.ReactNode;
}

export default function AdminShell({
    breadcrumbs,
    viewOptions,
    viewType,
    onViewChange,
    rightActions,
    children
}: AdminShellProps) {
    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-hidden animate-fade-in">
            <WorkspaceToolbar
                breadcrumbs={breadcrumbs}
                viewType={viewType as any}
                setViewType={onViewChange as any}
                availableViews={viewOptions}
                rightActions={rightActions}
            />
            <main className="flex-1 overflow-y-auto scrollbar-thin">
                <div className="p-4 lg:p-3 space-y-3">
                    {children}
                </div>
            </main>
        </div>
    );
}
