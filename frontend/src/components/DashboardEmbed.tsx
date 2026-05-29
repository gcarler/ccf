"use client";

import React, { useState } from 'react';
import { BarChart3, ChevronDown, ChevronRight } from 'lucide-react';
import EmbeddedDashboard from './EmbeddedDashboard';

interface DashboardEmbedProps {
    module: string;
    label?: string;
    defaultOpen?: boolean;
}

export default function DashboardEmbed({
    module, label, defaultOpen = false,
}: DashboardEmbedProps) {
    const [open, setOpen] = useState(defaultOpen);
    
    const moduleLabels: Record<string, string> = {
        crm: 'CRM', academy: 'Academia', evangelism: 'Evangelismo',
        finance: 'Finanzas', agenda: 'Agenda', cms: 'CMS',
        projects: 'Proyectos', admin: 'Admin',
    };

    const displayLabel = label || moduleLabels[module] || module;

    return (
        <div className="bg-white dark:bg-[#16171a] border border-slate-200 dark:border-white/5 rounded-lg overflow-hidden">
            <button
                onClick={() => setOpen(!open)}
                className="w-full flex items-center gap-2 px-3 py-2 text-[11px] font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-white/[0.03] transition-colors"
            >
                {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                <BarChart3 size={14} className="text-indigo-500" />
                📊 Dashboard {displayLabel}
                <span className="ml-auto text-[9px] text-slate-400">
                    {open ? 'ocultar' : 'mostrar métricas'}
                </span>
            </button>
            {open && (
                <div className="border-t border-slate-100 dark:border-white/5">
                    <EmbeddedDashboard
                        module={module}
                        title={displayLabel}
                        compact
                        refreshInterval={30}
                        maxHeight="480px"
                    />
                </div>
            )}
        </div>
    );
}
