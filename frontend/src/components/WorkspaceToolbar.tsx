"use client";

import React from 'react';
import { 
    Search, 
    Filter, 
    MoreHorizontal, 
    Plus, 
    Download, 
    Share2, 
    ChevronRight,
    Home,
    Settings,
    Columns,
    Layers,
    Clock
} from 'lucide-react';
import ViewSwitcher, { ViewType } from './ViewSwitcher';
import { motion } from 'framer-motion';
import SplitDropdownButton from './ui/SplitDropdownButton';
import Link from 'next/link';

interface Breadcrumb {
    label: string;
    href?: string;
    icon?: any;
}

interface WorkspaceToolbarProps {
    breadcrumbs: Breadcrumb[];
    viewType?: ViewType;
    setViewType?: (v: ViewType) => void;
    availableViews?: ViewType[];
    rightActions?: React.ReactNode;
    onSearch?: (query: string) => void;
    onFilter?: () => void;
    onAdd?: () => void;
    onAddOption?: (type: 'task' | 'document' | 'reminder' | 'whiteboard' | 'panel') => void;
}

export default function WorkspaceToolbar({
    breadcrumbs,
    viewType,
    setViewType,
    availableViews,
    rightActions,
    onSearch,
    onFilter,
    onAdd,
    onAddOption
}: WorkspaceToolbarProps) {
    return (
        <div className="h-12 bg-white dark:bg-[#1e1f21] border-b border-[#e8eaed] dark:border-white/[0.06] flex items-center justify-between px-4 sticky top-0 z-50 transition-colors duration-300">
            {/* Left: Breadcrumbs & View Switcher */}
            <div className="flex items-center gap-2 overflow-hidden">
                <div className="flex items-center gap-1 px-1.5 py-1 hover:bg-slate-100 dark:hover:bg-white/5 rounded-md cursor-pointer text-slate-300 dark:text-slate-600 transition-colors shrink-0">
                    <Home size={13} />
                    <ChevronRight size={11} />
                </div>
                
                <nav className="flex items-center gap-0.5 overflow-hidden">
                    {breadcrumbs.map((bc, idx) => {
                        const content = (
                            <motion.div 
                                initial={{ opacity: 0, x: -4 }}
                                animate={{ opacity: 1, x: 0 }}
                                className="flex items-center gap-1.5 px-2 py-1 hover:bg-slate-100 dark:hover:bg-white/5 rounded-md cursor-pointer group transition-all"
                            >
                                {bc.icon && <bc.icon size={12} className="text-slate-400 group-hover:text-blue-500 transition-colors shrink-0" />}
                                <span className={`text-[12px] font-semibold tracking-tight truncate ${idx === breadcrumbs.length - 1 ? 'text-slate-800 dark:text-slate-100' : 'text-slate-500 dark:text-slate-400'}`}>
                                    {bc.label}
                                </span>
                            </motion.div>
                        );

                        return (
                            <div key={idx} className="flex items-center gap-0.5 shrink-0 max-w-[200px]">
                                {bc.href ? <Link href={bc.href}>{content}</Link> : content}
                                {idx < breadcrumbs.length - 1 && (
                                    <ChevronRight size={11} className="text-slate-300 dark:text-slate-600 shrink-0" />
                                )}
                            </div>
                        );
                    })}
                </nav>

                <div className="w-px h-4 bg-slate-200 dark:bg-white/10 mx-1.5 shrink-0" />
                
                {setViewType && viewType && (
                    <ViewSwitcher
                        viewType={viewType}
                        setViewType={setViewType}
                        availableViews={availableViews}
                    />
                )}
            </div>

            {/* Right: Search, Filter, Actions */}
            <div className="flex items-center gap-1.5">
                <div className="relative hidden md:block group">
                    <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-300 dark:text-slate-600 group-focus-within:text-blue-500 transition-colors" size={13} />
                    <input 
                        type="text" 
                        placeholder="Buscar en esta vista..."
                        onChange={(e) => onSearch?.(e.target.value)}
                        className="h-7 w-44 lg:w-56 bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/[0.06] rounded-lg pl-8 pr-3 text-[11px] font-medium placeholder:text-slate-300 dark:placeholder:text-slate-600 focus:ring-1 focus:ring-blue-500/30 focus:bg-white dark:focus:bg-[#252528] focus:w-64 outline-none transition-all duration-200"
                    />
                </div>

                <div className="flex items-center gap-0.5">
                    <ToolbarButton icon={Filter} onClick={onFilter} tooltip="Filtrar" />
                    <ToolbarButton icon={Columns} tooltip="Columnas" />
                    <ToolbarButton icon={Layers} tooltip="Agrupar" />
                    
                    <div className="w-px h-4 bg-slate-200 dark:bg-white/10 mx-1" />
                    
                    {rightActions}
                    
                    {onAdd && (
                        <SplitDropdownButton 
                            onMainClick={onAdd}
                            onOptionClick={onAddOption ? onAddOption : () => {}}
                        />
                    )}

                    <ToolbarButton icon={MoreHorizontal} tooltip="Más opciones" />
                </div>
            </div>
        </div>
    );
}

function ToolbarButton({ icon: Icon, onClick, tooltip, active }: { icon: any, onClick?: () => void, tooltip: string, active?: boolean }) {
    return (
        <div className="relative group/toolbar-btn">
            <button 
                onClick={onClick}
                className={`p-1.5 rounded-md transition-all ${
                    active 
                    ? 'bg-blue-50 text-blue-600 dark:bg-blue-500/10 dark:text-blue-400' 
                    : 'text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-white/5 hover:text-slate-700 dark:hover:text-slate-200'
                }`}
            >
                <Icon size={14} />
            </button>
            <div className="absolute top-9 left-1/2 -translate-x-1/2 bg-slate-900 text-white text-[9px] font-bold px-1.5 py-1 rounded opacity-0 group-hover/toolbar-btn:opacity-100 pointer-events-none transition-opacity whitespace-nowrap z-[100] shadow-xl border border-white/5 tracking-wider uppercase">
                {tooltip}
            </div>
        </div>
    );
}
