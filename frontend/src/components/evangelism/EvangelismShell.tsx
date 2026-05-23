"use client";

import React from 'react';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import { ViewType } from '@/components/ViewSwitcher';
import { useAuth } from '@/context/AuthContext';
import { ShieldAlert } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

export interface BreadcrumbOption {
    label: string;
    href?: string;
    icon?: LucideIcon;
}

interface EvangelismShellProps {
    breadcrumbs: BreadcrumbOption[];
    viewOptions?: ViewType[];
    viewType?: ViewType;
    onViewChange?: (view: ViewType) => void;
    onSearch?: (term: string) => void;
    rightActions?: React.ReactNode;
    children: React.ReactNode;
    onAdd?: () => void;
    onAddOption?: (option: string) => void;
    onFilter?: () => void;
    onColumns?: () => void;
    onGroup?: () => void;
    onMore?: () => void;
}

export default function EvangelismShell({
    breadcrumbs,
    viewOptions,
    viewType,
    onViewChange,
    onSearch,
    rightActions,
    children,
    onAdd,
    onAddOption,
    onFilter,
    onColumns,
    onGroup,
    onMore
}: EvangelismShellProps) {
    const { user, loading } = useAuth();
    const role = (user?.role || '').toLowerCase();
    const isAuthorized = role === 'admin' || role === 'pastor';

    if (loading) {
        return (
            <div className="min-h-[60vh] flex items-center justify-center">
                <p className="text-sm font-bold text-slate-500">Cargando acceso...</p>
            </div>
        );
    }

    if (!isAuthorized) {
        return (
            <div className="min-h-[60vh] flex items-center justify-center p-3">
                <div className="max-w-md w-full rounded-lg border border-amber-200 bg-amber-50 px-3 py-8 text-center">
                    <div className="mx-auto mb-4 size-7 rounded-lg bg-amber-100 text-amber-700 flex items-center justify-center">
                        <ShieldAlert size={22} />
                    </div>
                    <h2 className="text-lg font-bold text-amber-900">Acceso restringido</h2>
                    <p className="mt-2 text-sm font-medium text-amber-800">
                        Este módulo requiere rol pastoral o administrativo.
                    </p>
                </div>
            </div>
        );
    }

    return (
        <WorkspaceLayout
            breadcrumbs={breadcrumbs}
            availableViews={viewOptions}
            viewType={viewType}
            setViewType={onViewChange}
            onSearch={onSearch}
            rightActions={rightActions}
            onAdd={onAdd}
            onAddOption={onAddOption}
            onFilter={onFilter}
            onColumns={onColumns}
            onGroup={onGroup}
            onMore={onMore}
        >
            <main className={viewType && ['board', 'kanban', 'gantt', 'calendar', 'wiki'].includes(viewType) ? "flex-1 overflow-hidden h-full" : "flex-1 overflow-y-auto scrollbar-thin"}>
                <div className={viewType && ['board', 'kanban', 'gantt', 'calendar', 'wiki'].includes(viewType) ? "h-full animate-fade-in" : "p-4 lg:p-3 space-y-6 animate-fade-in"}>
                    {children}
                </div>
            </main>
        </WorkspaceLayout>
    );
}
