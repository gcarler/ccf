"use client";

import React from 'react';
import { 
    Search, 
    Filter, 
    MoreHorizontal, 
    ChevronRight,
    Home,
    Columns,
    Layers
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
    leftActions?: React.ReactNode;
    rightActions?: React.ReactNode;
    onSearch?: (query: string) => void;
    onFilter?: () => void;
    onColumns?: () => void;
    onGroup?: () => void;
    onMore?: () => void;
    onAdd?: () => void;
    onAddOption?: (type: string) => void;
}

export default function WorkspaceToolbar({
    breadcrumbs,
    viewType,
    setViewType,
    availableViews,
    leftActions,
    rightActions,
    onSearch,
    onFilter,
    onColumns,
    onGroup,
    onMore,
    onAdd,
    onAddOption
}: WorkspaceToolbarProps) {
    return (
        <div className="min-h-10 bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] border-b border-[#e8eaed] dark:border-white/[0.06] flex flex-wrap items-center justify-between gap-1.5 px-2 py-1 sticky top-0 z-50 transition-colors duration-300 sm:flex-nowrap sm:gap-2 sm:py-0">
            {/* Left: leftActions + Breadcrumbs + View Switcher */}
            <div className="flex min-w-0 flex-1 items-center gap-1.5 overflow-hidden sm:gap-2">
                {leftActions && <>{leftActions}<div className="w-px h-4 bg-[hsl(var(--surface-3))] dark:bg-white/10 mx-0.5 shrink-0" /></>}
                <div className="hidden items-center gap-1 px-1.5 py-1 hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 rounded-md cursor-pointer text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] transition-colors shrink-0 sm:flex">
                    <Home size={13} />
                    <ChevronRight size={13} />
                </div>
                
                <nav className="flex min-w-0 items-center gap-0.5 overflow-hidden">
                    {breadcrumbs.map((bc, idx) => {
                        const isLast = idx === breadcrumbs.length - 1;
                        const content = (
                            <motion.div
                                initial={{ opacity: 0, x: -4 }}
                                animate={{ opacity: 1, x: 0 }}
                                className="flex min-w-0 items-center gap-1.5 px-2 py-1 hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 rounded-md cursor-pointer group transition-all"
                            >
                                {bc.icon && <bc.icon size={13} className="text-[hsl(var(--text-secondary))] group-hover:text-[hsl(var(--primary))] transition-colors shrink-0" />}
                                <span className={`text-xs font-semibold tracking-tight truncate ${isLast ? 'text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]' : 'text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]'}`}>
                                    {bc.label}
                                </span>
                            </motion.div>
                        );

                        return (
                            <div key={idx} className={`${isLast ? 'flex' : 'hidden md:flex'} min-w-0 items-center gap-0.5 shrink ${isLast ? 'max-w-[48vw] sm:max-w-[220px]' : 'max-w-[160px] lg:max-w-[200px]'}`}>
                                {bc.href ? <Link href={bc.href} prefetch={false}>{content}</Link> : content}
                                {idx < breadcrumbs.length - 1 && (
                                    <ChevronRight size={13} className="hidden text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] shrink-0 md:block" />
                                )}
                            </div>
                        );
                    })}
                </nav>

                {(setViewType && viewType) && <div className="hidden w-px h-4 bg-[hsl(var(--surface-3))] dark:bg-white/10 mx-1.5 shrink-0 sm:block" />}
                
                {setViewType && viewType && (
                    <div className="hidden sm:block">
                    <ViewSwitcher
                        viewType={viewType}
                        setViewType={setViewType}
                        availableViews={availableViews}
                    />
                    </div>
                )}
            </div>

            {/* Right: Search, Filter, Actions */}
            <div className="flex min-w-0 shrink-0 items-center gap-1">
                <div className="relative hidden lg:block group">
                    <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] group-focus-within:text-[hsl(var(--primary))] transition-colors" size={13} />
                    <input
                        type="text"
                        placeholder="Buscar en esta vista..."
                        onChange={(e) => onSearch?.(e.target.value)}
                        className="h-8 w-44 lg:w-56 bg-[hsl(var(--surface-1))] dark:bg-black/20 border border-[hsl(var(--border))] dark:border-white/[0.06] rounded-md pl-8 pr-3 text-xs font-medium placeholder:text-[hsl(var(--text-secondary))] dark:placeholder:text-[hsl(var(--text-secondary))] focus:ring-1 focus:ring-blue-500/30 focus:bg-[hsl(var(--bg-primary))] dark:focus:bg-[#252528] focus:w-64 outline-none transition-all duration-200"
                    />
                </div>

                <div className="flex min-w-0 items-center gap-0.5 overflow-x-auto scrollbar-none">
                    {onFilter && <ToolbarButton icon={Filter} onClick={onFilter} tooltip="Filtrar" />}
                    {onColumns && <ToolbarButton icon={Columns} onClick={onColumns} tooltip="Columnas" />}
                    {onGroup && <ToolbarButton icon={Layers} onClick={onGroup} tooltip="Agrupar" />}

                    {(onFilter || onColumns || onGroup) && (
                        <div className="w-px h-4 bg-[hsl(var(--surface-3))] dark:bg-white/10 mx-1" />
                    )}
                    
                    {rightActions}
                    
                    {onAdd && (
                        <SplitDropdownButton 
                            onMainClick={onAdd}
                            onOptionClick={onAddOption ? onAddOption : () => {}}
                        />
                    )}

                    {onMore && <ToolbarButton icon={MoreHorizontal} onClick={onMore} tooltip="Más opciones" />}
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
                className={`p-1 rounded-md transition-all ${
                    active
                    ? 'bg-blue-50 text-[hsl(var(--primary))] dark:bg-blue-500/10 dark:text-[hsl(var(--primary))]'
                    : 'text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:text-[hsl(var(--text-secondary))] dark:hover:bg-white/5 hover:text-[hsl(var(--text-primary))] dark:hover:text-[hsl(var(--text-secondary))]'
                }`}
            >
                <Icon size={13} />
            </button>
            <div className="absolute top-9 left-1/2 -translate-x-1/2 bg-[hsl(var(--bg-muted))] text-white text-[9px] font-semibold px-1.5 py-1 rounded opacity-0 group-hover/toolbar-btn:opacity-100 pointer-events-none transition-opacity whitespace-nowrap z-[100] shadow-xl border border-white/5 tracking-wider uppercase">
                {tooltip}
            </div>
        </div>
    );
}
