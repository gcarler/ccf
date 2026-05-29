"use client";

import React from 'react';
import EmbeddedDashboard from './EmbeddedDashboard';

/**
 * DashboardPanel — A ready-to-use dashboard panel for any module page.
 * 
 * Usage:
 *   import DashboardPanel from '@/components/DashboardPanel';
 *   <DashboardPanel module="crm" title="CRM" refreshInterval={30} />
 * 
 * It auto-sizes and fits into any flex/grid container.
 */
interface DashboardPanelProps {
    module: string;
    title?: string;
    refreshInterval?: number;
    className?: string;
}

export default function DashboardPanel({
    module, title, refreshInterval = 30, className = '',
}: DashboardPanelProps) {
    return (
        <div className={`bg-white dark:bg-[#16171a] border border-slate-200 dark:border-white/5 rounded-lg overflow-hidden ${className}`}>
            <EmbeddedDashboard
                module={module}
                title={title}
                compact
                refreshInterval={refreshInterval}
                maxHeight="none"
            />
        </div>
    );
}
