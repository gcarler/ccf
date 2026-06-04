'use client';

import React from 'react';
import { Search, LayoutGrid, List, ChevronRight, MessageSquare, Zap, Target, Clock } from 'lucide-react';

interface CrmTopBarProps {
    title: string;
    view: 'list' | 'board' | 'calendar';
    onViewChange: (view: 'list' | 'board' | 'calendar') => void;
}

export default function CrmTopBar({ title, view, onViewChange }: CrmTopBarProps) {
    return (
        <header className="h-[48px] border-b border-slate-200 dark:border-white/5 bg-[hsl(var(--surface-1))] dark:bg-[#111418] flex items-center justify-between px-4 sticky top-0 z-40">
            {/* Left: Breadcrumbs & View Switcher */}
            <div className="flex items-center gap-4">
                <div className="flex items-center gap-2 text-[12px] font-medium text-slate-500">
                    <HouseIcon size={14} className="text-slate-400" />
                    <ChevronRight size={10} className="text-slate-300" />
                    <span>Espacio del equipo</span>
                    <ChevronRight size={10} className="text-slate-300" />
                    <div className="flex items-center gap-1.5 text-slate-900 dark:text-white font-bold">
                        <Target size={14} className="text-cu-blue" />
                        <span>{title}</span>
                    </div>
                </div>

                <div className="h-6 w-[1px] bg-slate-200 dark:bg-white/10 mx-1"></div>

                <div className="flex items-center gap-1">
                    <button
                        onClick={() => onViewChange('list')}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-[11px] font-bold transition-all ${view === 'list' ? 'bg-slate-100 dark:bg-white/5 text-cu-blue shadow-sm' : 'text-slate-500 hover:bg-slate-50 dark:hover:bg-white/5'}`}
                    >
                        <List size={14} /> Lista
                    </button>
                    <button
                        onClick={() => onViewChange('board')}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-[11px] font-bold transition-all ${view === 'board' ? 'bg-slate-100 dark:bg-white/5 text-cu-blue shadow-sm' : 'text-slate-500 hover:bg-slate-50 dark:hover:bg-white/5'}`}
                    >
                        <LayoutGrid size={14} /> Tablero
                    </button>
                </div>
            </div>

            {/* Center: Search Bar */}
            <div className="flex-1 max-w-[400px] mx-8 hidden lg:block">
                <div className="relative group">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-cu-blue transition-colors" size={14} />
                    <input
                        type="text"
                        placeholder="Buscar... Ctrl K"
                        className="w-full bg-slate-100/50 dark:bg-white/5 border border-transparent focus:border-cu-blue/30 rounded-lg pl-9 pr-4 py-1.5 text-xs transition-all outline-none placeholder:text-slate-400"
                    />
                    <div className="absolute right-2 top-1/2 -translate-y-1/2 size-5 flex items-center justify-center bg-[hsl(var(--surface-1))] dark:bg-slate-800 border border-slate-200 dark:border-white/10 rounded text-[10px] text-slate-400 font-bold shadow-sm">
                        /
                    </div>
                </div>
            </div>

            {/* Right: Actions */}
            <div className="flex items-center gap-2">
                <div className="flex items-center gap-0.5 border-r border-slate-200 dark:border-white/10 pr-2 mr-1">
                    <button className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-white transition-colors" title="Agentes"><Zap size={18} /></button>
                    <button className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-white transition-colors" title="Automatizar"><Clock size={18} /></button>
                    <button className="p-2 text-cu-blue hover:bg-cu-blue/10 rounded-lg transition-colors flex items-center gap-1.5 text-xs font-bold">
                        <MessageSquare size={16} /> Ask AI
                    </button>
                </div>

                <button className="flex items-center gap-2 px-3 py-1.5 bg-slate-900 border border-slate-800 hover:bg-black text-white rounded-lg text-xs font-bold shadow-md transition-all active:scale-95">
                    Add Tarea
                </button>
            </div>
        </header>
    );
}

// Minimal icons fix
function HouseIcon({ size, className }: { size: number, className?: string }) {
    return <svg xmlns="http://www.w3.org/2000/svg" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" /><polyline points="9 22 9 12 15 12 15 22" /></svg>;
}

