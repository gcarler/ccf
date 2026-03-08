"use client";

import React, { useState } from 'react';
import { ThemeProvider } from '../theme/ThemeContext';
import CrmSidebar from './components/CrmSidebar';
import CrmTopBar from './components/CrmTopBar';
import { usePathname } from 'next/navigation';

export default function CrmLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const pathname = usePathname();
    const [view, setView] = useState<'list' | 'board' | 'calendar'>('board');

    // Determine title based on pathname
    const getTitle = () => {
        const segments = pathname.split('/');
        const last = segments[segments.length - 1];
        if (last === 'crm') return 'Dashboard';
        if (last === 'pipeline') return 'Consolidación';
        if (last === 'members') return 'Miembros';
        if (last === 'events') return 'Eventos';
        if (last === 'messaging') return 'Mensajería';
        if (last === 'counseling') return 'Consejería';
        if (last === 'groups') return 'Casas de Gloria';
        if (last === 'volunteers') return 'Servidores';
        if (last === 'my-card') return 'Mi Carnet Digital';
        return last.charAt(0).toUpperCase() + last.slice(1);
    };

    return (
        <div className="min-h-screen bg-white dark:bg-[#111418] flex text-slate-900 dark:text-slate-100 font-sans selection:bg-cu-purple/20">
            {/* ClickUp Sidebar */}
            <CrmSidebar />

            {/* Main Wrapper */}
            <div className="flex-1 ml-[276px] flex flex-col min-h-screen overflow-hidden">
                {/* Unified Top Bar */}
                <CrmTopBar
                    title={getTitle()}
                    view={view}
                    onViewChange={setView}
                />

                {/* Content Area */}
                <main className="flex-1 overflow-y-auto bg-[#f6f8fa] dark:bg-[#1b1f24] p-6 lg:p-10">
                    <div className="max-w-[1600px] mx-auto">
                        {/* 
                            Passing view state to children via clone or context would be better, 
                            but for now we'll focus on the structural redesign.
                        */}
                        {children}
                    </div>
                </main>
            </div>
        </div>
    );
}


