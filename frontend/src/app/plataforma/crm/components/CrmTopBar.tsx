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
        <header className="h-[48px] border-b border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] flex items-center justify-between px-4 sticky top-0 z-40">
            {/* Left: Breadcrumbs & View Switcher */}
            <div className="flex items-center gap-4">
                <div className="flex items-center gap-2 text-sm font-medium text-[hsl(var(--muted-foreground))]">
                    <HouseIcon size={14} className="text-[hsl(var(--muted-foreground))]" />
                    <ChevronRight size={10} className="text-[hsl(var(--muted-foreground))]" />
                    <span>Espacio del equipo</span>
                    <ChevronRight size={10} className="text-[hsl(var(--muted-foreground))]" />
                    <div className="flex items-center gap-1.5 text-[hsl(var(--foreground))] font-bold">
                        <Target size={14} className="text-[hsl(var(--primary))]" />
                        <span>{title}</span>
                    </div>
                </div>

                <div className="h-6 w-[1px] bg-[hsl(var(--border))] mx-1"></div>

                <div className="flex items-center gap-1">
                    <button
                        onClick={() => onViewChange('list')}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-bold transition-all ${view === 'list' ? 'bg-[hsl(var(--surface-2))] text-[hsl(var(--primary))] shadow-sm' : 'text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--surface-2))]'}`}
                    >
                        <List size={14} /> Lista
                    </button>
                    <button
                        onClick={() => onViewChange('board')}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-bold transition-all ${view === 'board' ? 'bg-[hsl(var(--surface-2))] text-[hsl(var(--primary))] shadow-sm' : 'text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--surface-2))]'}`}
                    >
                        <LayoutGrid size={14} /> Tablero
                    </button>
                </div>
            </div>

            {/* Center: Search Bar */}
            <div className="flex-1 max-w-[400px] mx-8 hidden lg:block">
                <div className="relative group">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--muted-foreground))] group-focus-within:text-[hsl(var(--primary))] transition-colors" size={14} />
                    <input
                        type="text"
                        placeholder="Buscar... Ctrl K"
                        className="w-full bg-[hsl(var(--surface-2))] border border-transparent focus:border-[hsl(var(--primary)/0.3)] rounded-lg pl-9 pr-4 py-1.5 text-xs transition-all outline-none placeholder:text-[hsl(var(--muted-foreground))] text-[hsl(var(--foreground))]"
                    />
                    <div className="absolute right-2 top-1/2 -translate-y-1/2 size-5 flex items-center justify-center bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] rounded text-2xs text-[hsl(var(--muted-foreground))] font-bold shadow-sm">
                        /
                    </div>
                </div>
            </div>

            {/* Right: Actions */}
            <div className="flex items-center gap-2">
                <div className="flex items-center gap-0.5 border-r border-[hsl(var(--border))] pr-2 mr-1">
                    <button className="p-2 text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] transition-colors" title="Agentes" aria-label="Agentes"><Zap size={18} /></button>
                    <button className="p-2 text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] transition-colors" title="Automatizar" aria-label="Automatizar"><Clock size={18} /></button>
                    <button className="p-2 text-[hsl(var(--primary))] hover:bg-[hsl(var(--primary)/0.1)] rounded-lg transition-colors flex items-center gap-1.5 text-xs font-bold">
                        <MessageSquare size={16} /> Ask AI
                    </button>
                </div>

                <button className="flex items-center gap-2 px-3 py-1.5 bg-[hsl(var(--primary))] border border-[hsl(var(--border))] hover:opacity-90 text-[hsl(var(--primary-foreground))] rounded-lg text-xs font-bold shadow-sm transition-all active:scale-95">
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
