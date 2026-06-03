"use client";

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import { } from 'lucide-react';
import EmbeddedDashboard from './EmbeddedDashboard';
import type { LucideIcon } from 'lucide-react';

interface DashboardTab {
    id: string;
    label: string;
    icon: LucideIcon;
}

interface DashboardTabsProps {
    module: string;
    title?: string;
    tabs: DashboardTab[];
    children: React.ReactNode;
    defaultTab?: string;
    refreshInterval?: number;
    dashboardHeight?: string;
}

export default function DashboardTabs({
    module, title, tabs, children, defaultTab,
    refreshInterval = 30, dashboardHeight = '500px',
}: DashboardTabsProps) {
    const [activeTab, setActiveTab] = useState(defaultTab || tabs[0]?.id || 'dashboard');
    const isDashboard = activeTab === 'dashboard';

    return (
        <div className="flex flex-col h-full">
            {/* Tabs */}
            <div className="flex items-center gap-1 px-4 pt-2 pb-0 border-b border-slate-200 dark:border-white/5 no-print">
                {tabs.map(tab => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        className={clsx(
                            'flex items-center gap-1.5 px-3 py-2 text-[11px] font-semibold rounded-t-lg transition-all border-b-2 -mb-[1px]',
                            activeTab === tab.id
                                ? 'text-[hsl(var(--primary))] dark:text-blue-400 border-[hsl(var(--primary))] bg-[hsl(var(--bg-primary))] dark:bg-[#16171a]'
                                : 'text-slate-400 border-transparent hover:text-slate-600 dark:hover:text-slate-300 hover:border-slate-300'
                        )}
                    >
                        <tab.icon size={14} />
                        {tab.label}
                    </button>
                ))}
            </div>

            {/* Content */}
            <div className="flex-1 overflow-hidden">
                <AnimatePresence mode="wait">
                    {isDashboard ? (
                        <motion.div
                            key="dashboard"
                            initial={{ opacity: 0, y: 8 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -8 }}
                            transition={{ duration: 0.15 }}
                            className="h-full overflow-y-auto"
                        >
                            <EmbeddedDashboard
                                module={module}
                                title={title}
                                refreshInterval={refreshInterval}
                                maxHeight={dashboardHeight}
                            />
                        </motion.div>
                    ) : (
                        <motion.div
                            key="content"
                            initial={{ opacity: 0, y: 8 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -8 }}
                            transition={{ duration: 0.15 }}
                            className="h-full overflow-y-auto"
                        >
                            {children}
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </div>
    );
}

export { EmbeddedDashboard };
