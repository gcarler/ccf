"use client";

import React, { useState, useEffect, useCallback } from 'react';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import { ViewType } from '@/components/ViewSwitcher';
import { useAuth } from '@/context/AuthContext';
import { ShieldAlert, Flame, Calendar, Scan, Zap, Home, Wrench } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { apiFetch } from '@/lib/http';
import { toast } from 'sonner';

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

interface StrategyItem {
    id: string | number;
    name: string;
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
    const { user, loading, token } = useAuth();
    const role = (user?.role || '').toLowerCase();
    const isAuthorized = role === 'admin' || role === 'pastor';
    const [strategies, setStrategies] = useState<StrategyItem[]>([]);

    const fetchStrategies = useCallback(async () => {
        if (!token) return;
        try {
            const result = await apiFetch<StrategyItem[]>('/evangelism/strategies', { token });
            setStrategies(Array.isArray(result) ? result : []);
        } catch {
            // Silently fail — sidebar still works without strategies
        }
    }, [token]);

    useEffect(() => {
        if (isAuthorized) fetchStrategies();
    }, [isAuthorized, fetchStrategies]);

    // Listen for newly created strategies
    useEffect(() => {
        const handleCreated = () => fetchStrategies();
        window.addEventListener('evangelism-strategy-created', handleCreated);
        return () => window.removeEventListener('evangelism-strategy-created', handleCreated);
    }, [fetchStrategies]);

    const sidebarSections = [
        {
            title: 'Estrategias',
            items: [
                { id: 'ev-strategies', label: 'Todas las Estrategias', href: '/plataforma/evangelism', icon: Flame, count: strategies.length },
                ...strategies.map((s: StrategyItem) => ({
                    id: `ev-strategy-${s.id}`,
                    label: s.name,
                    href: `/plataforma/evangelism/strategies/${s.id}`,
                    icon: Zap,
                })),
            ],
        },
        {
            title: 'Herramientas',
            items: [
                { id: 'ev-events', label: 'Eventos', href: '/plataforma/evangelism/events', icon: Calendar },
                { id: 'ev-faro', label: 'Faro en Casa', href: '/plataforma/evangelism/faro', icon: Home },
                { id: 'ev-scanner', label: 'Escáner ASST', href: '/plataforma/evangelism/scanner', icon: Scan },
            ],
        },
    ];

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
            sidebarTitle="Evangelismo & Eventos"
            sidebarSections={sidebarSections}
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
                <div className={viewType && ['board', 'kanban', 'gantt', 'calendar', 'wiki'].includes(viewType) ? "h-full animate-fade-in" : "p-4 lg:p-3 space-y-3 animate-fade-in"}>
                    {children}
                </div>
            </main>
        </WorkspaceLayout>
    );
}
