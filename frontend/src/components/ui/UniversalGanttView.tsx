"use client";

import React, { useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { 
    ChevronLeft, ChevronRight, Calendar, Info, 
    Clock, Zap, Layout
} from 'lucide-react';
import clsx from 'clsx';

export interface GanttItem {
    id: string | number;
    title: string;
    subtitle?: string;
    start_date: string; // ISO or YYYY-MM-DD
    end_date: string;
    color?: 'blue' | 'emerald' | 'amber' | 'rose' | 'sky';
    progress?: number; // 0-100
}

export interface UniversalGanttViewProps {
    items: GanttItem[];
    moduleName?: string;
    onItemClick?: (item: GanttItem) => void;
    onOptimize?: () => void;
    onItemMove?: (item: GanttItem, newStart: string, newEnd: string) => void;
    onItemResize?: (item: GanttItem, newEnd: string) => void;
}

const COLORS = {
    blue: 'bg-[hsl(var(--primary))] shadow-blue-500/20',
    sky: 'bg-sky-500 shadow-sky-500/20',
    emerald: 'bg-emerald-500 shadow-emerald-500/20',
    amber: 'bg-amber-500 shadow-amber-500/20',
    rose: 'bg-rose-500 shadow-rose-500/20',
};

const toDateKey = (date: Date) => {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
};

const addDays = (dateStr: string, days: number) => {
    const d = new Date(`${dateStr}T12:00:00`);
    d.setDate(d.getDate() + days);
    return toDateKey(d);
};

interface GanttBarItemProps {
    item: GanttItem;
    pos: number;
    width: number;
    idx: number;
    onClick?: (item: GanttItem) => void;
    onMove?: (item: GanttItem, start: string, end: string) => void;
    onResize?: (item: GanttItem, end: string) => void;
}

function GanttBarItem({ item, pos, width, idx, onClick, onMove, onResize }: GanttBarItemProps) {
    const [dragState, setDragState] = useState<{type: 'move'|'resize'; startX: number; currentX: number} | null>(null);

    const handlePointerDown = (e: React.PointerEvent, type: 'move'|'resize') => {
        if (type === 'move' && !onMove) return;
        if (type === 'resize' && !onResize) return;
        e.stopPropagation();
        (e.target as Element).setPointerCapture(e.pointerId);
        setDragState({ type, startX: e.clientX, currentX: e.clientX });
    };

    const handlePointerMove = (e: React.PointerEvent) => {
        if (!dragState) return;
        setDragState(prev => (prev ? { ...prev, currentX: e.clientX } : null));
    };

    const handlePointerUp = (e: React.PointerEvent) => {
        if (!dragState) return;
        (e.target as Element).releasePointerCapture(e.pointerId);
        const rawDeltaX = dragState.currentX - dragState.startX;
        const deltaDays = Math.round(rawDeltaX / 160);

        if (deltaDays !== 0) {
            if (dragState.type === 'move' && onMove) {
                onMove(item, addDays(item.start_date, deltaDays), addDays(item.end_date, deltaDays));
            } else if (dragState.type === 'resize' && onResize) {
                const newEnd = addDays(item.end_date, deltaDays);
                const s = new Date(item.start_date);
                if (new Date(newEnd) >= s) onResize(item, newEnd);
            }
        } else if (dragState.type === 'move') {
            onClick?.(item);
        }

        setDragState(null);
    };

    const isDragging = !!dragState;
    const deltaX = dragState ? dragState.currentX - dragState.startX : 0;
    const displayX = pos + (dragState?.type === 'move' ? deltaX : 0);
    const displayWidth = Math.max(140, width + (dragState?.type === 'resize' ? deltaX : 0));

    return (
        <>
            <motion.div
                initial={{ opacity: 0, x: pos - 20 }}
                animate={{ opacity: 1, x: displayX, width: displayWidth }}
                transition={{
                    type: isDragging ? false : "spring",
                    duration: isDragging ? 0 : 0.5,
                    bounce: 0,
                    delay: isDragging ? 0 : idx * 0.05
                }}
                onPointerDown={(e) => handlePointerDown(e, 'move')}
                onPointerMove={handlePointerMove}
                onPointerUp={handlePointerUp}
                className={clsx(
                    "absolute h-full rounded-lg p-4 flex items-center justify-between select-none shadow-lg group-hover:shadow-2xl",
                    COLORS[item.color || 'blue'],
                    isDragging ? "z-40 scale-[1.02] cursor-grabbing" : "cursor-pointer hover:scale-[1.02]"
                )}
            >
                <div className="flex items-center gap-3 overflow-hidden pointer-events-none">
                    <div className="size-8 rounded-md bg-white/20 flex items-center justify-center text-white shrink-0"><Clock size={16} /></div>
                    <div className="overflow-hidden">
                        <p className="font-semibold text-white uppercase tracking-tight truncate leading-none mb-1">{item.title}</p>
                        {item.subtitle && <p className="text-[9px] text-white/70 uppercase font-bold tracking-wide truncate">{item.subtitle}</p>}
                    </div>
                </div>
                {item.progress !== undefined && (
                    <div className="flex items-center gap-3 text-white/90 pointer-events-none mr-2">
                        <span className="font-semibold">{item.progress}%</span>
                        <div className="size-6 rounded-full border-2 border-white/20 flex items-center justify-center">
                            <div className="size-1.5 rounded-full bg-[hsl(var(--bg-primary))] animate-pulse" />
                        </div>
                    </div>
                )}
            </motion.div>
            {onResize && (
                <div
                    style={{ left: `${displayX + displayWidth - 12}px`, width: '24px' }}
                    onPointerDown={(e) => handlePointerDown(e, 'resize')}
                    onPointerMove={handlePointerMove}
                    onPointerUp={handlePointerUp}
                    className="absolute top-0 bottom-0 cursor-ew-resize flex items-center justify-center opacity-0 group-hover:opacity-100 hover:bg-white/20 rounded-r-lg transition-colors z-50"
                >
                    <div className="w-1 h-4 bg-white/50 rounded-full pointer-events-none" />
                </div>
            )}
        </>
    );
}

export default function UniversalGanttView({ items, moduleName = "Módulo", onItemClick, onOptimize, onItemMove, onItemResize }: UniversalGanttViewProps) {
    const scrollContainerRef = useRef<HTMLDivElement>(null);
    const [zoom, setZoom] = useState<'day' | 'week' | 'month'>('week');
    
    // Generate scale (current month as default)
    const today = new Date();
    const days = Array.from({ length: 30 }, (_, i) => {
        const d = new Date(today);
        d.setDate(today.getDate() + i - 5); // Start 5 days ago
        return d;
    });

    const scroll = (direction: 'left' | 'right') => {
        if (!scrollContainerRef.current) return;
        const amount = direction === 'left' ? -400 : 400;
        scrollContainerRef.current.scrollBy({ left: amount, behavior: 'smooth' });
    };

    const getPosition = (dateStr: string) => {
        const date = new Date(`${dateStr}T12:00:00`);
        const startIndex = days.findIndex(d => d.toDateString() === date.toDateString());
        if (startIndex === -1) {
            // Check if before or after
            if (date < days[0]) return -100;
            return days.length * 160;
        }
        return startIndex * 160; // 160px per day
    };

    const getWidth = (start: string, end: string) => {
        const s = new Date(`${start}T12:00:00`);
        const e = new Date(`${end}T12:00:00`);
        const diff = Math.max(1, Math.ceil((e.getTime() - s.getTime()) / (1000 * 60 * 60 * 24)));
        return (diff + 1) * 160 - 20; // gap handling
    };

    return (
        <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] rounded-lg border border-[hsl(var(--border))] overflow-hidden shadow-sm">
            
            {/* ─── Header de Controles ─── */}
            <div className="px-3 py-1.5 border-b border-[hsl(var(--border))] dark:border-white/5 flex items-center justify-between bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                <div className="flex items-center gap-4">
                    <div className="flex bg-[hsl(var(--bg-primary))] dark:bg-white/5 rounded-md border border-[hsl(var(--border))] dark:border-white/10 p-1 shadow-sm">
                        <button 
                            onClick={() => setZoom('day')}
                            className={clsx("px-4 py-1.5 text-[10px] font-semibold uppercase tracking-wide rounded-lg transition-all", zoom === 'day' ? "bg-[hsl(var(--bg-muted))] text-white dark:bg-white/10" : "text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))]")}
                        >Día</button>
                        <button 
                            onClick={() => setZoom('week')}
                            className={clsx("px-4 py-1.5 text-[10px] font-semibold uppercase tracking-wide rounded-lg transition-all", zoom === 'week' ? "bg-[hsl(var(--bg-muted))] text-white dark:bg-white/10" : "text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))]")}
                        >Semana</button>
                        <button 
                            onClick={() => setZoom('month')}
                            className={clsx("px-4 py-1.5 text-[10px] font-semibold uppercase tracking-wide rounded-lg transition-all", zoom === 'month' ? "bg-[hsl(var(--bg-muted))] text-white dark:bg-white/10" : "text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))]")}
                        >Mes</button>
                    </div>
                    <div className="h-6 w-px bg-[hsl(var(--surface-3))] dark:bg-white/10" />
                    <p className="text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] flex items-center gap-2">
                        <Layout size={14} className="text-[hsl(var(--primary))]" /> {moduleName}
                    </p>
                </div>

                <div className="flex items-center gap-2">
                    <div className="flex gap-1.5 mr-4">
                        <button onClick={() => scroll('left')} className="p-2.5 rounded-md bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-all shadow-sm"><ChevronLeft size={16} /></button>
                        <button onClick={() => scroll('right')} className="p-2.5 rounded-md bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-all shadow-sm"><ChevronRight size={16} /></button>
                    </div>
                    {onOptimize && (
                        <button
                            onClick={onOptimize}
                            className="px-3 py-2.5 bg-[hsl(var(--bg-muted))] dark:bg-[hsl(var(--primary))] text-white rounded-md text-[10px] font-semibold uppercase tracking-wide flex items-center gap-2 shadow-xl shadow-blue-500/10 hover:scale-105 transition-all"
                        >
                            <Zap size={14} /> Optimus Brain
                        </button>
                    )}
                </div>
            </div>

            {/* ─── Scroll Area ─── */}
            <div className="flex-1 overflow-hidden flex flex-col">
                {/* Timeline Header */}
                <div 
                    ref={scrollContainerRef}
                    className="flex-1 overflow-x-auto scroll-smooth scrollbar-none relative"
                >
                    <div className="min-w-max h-full flex flex-col">
                        {/* Days scale */}
                        <div className="flex border-b border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] sticky top-0 z-20">
                            {days.map((day, i) => (
                                <div key={i} className={clsx(
                                    "w-[160px] p-3 flex flex-col gap-1 border-r border-[hsl(var(--border))] dark:border-white/5",
                                    day.toDateString() === today.toDateString() ? "bg-blue-50/50 dark:bg-blue-500/5 text-[hsl(var(--primary))]" : "text-[hsl(var(--text-secondary))]"
                                )}>
                                    <span className="text-[10px] font-semibold uppercase tracking-tighter opacity-60">
                                        {day.toLocaleDateString('es-ES', { weekday: 'long' })}
                                    </span>
                                    <span className="text-lg font-bold tracking-tighter italic leading-none">
                                        {day.getDate()} {day.toLocaleDateString('es-ES', { month: 'short' }).toUpperCase()}
                                    </span>
                                </div>
                            ))}
                        </div>

                        {/* Content Grid */}
                        <div className="relative flex-1 bg-[hsl(var(--surface-1))]/20 dark:bg-transparent min-h-48">
                            {/* Vertical Grid Lines */}
                            <div className="absolute inset-0 flex">
                                {days.map((_, i) => (
                                    <div key={i} className="w-[160px] h-full border-r border-[hsl(var(--border))] dark:border-white/5 pointer-events-none" />
                                ))}
                            </div>

                            {/* Task/Item Bars */}
                            <div className="relative z-10 p-4 space-y-3">
                                {items.length === 0 ? (
                                    <div className="absolute inset-0 flex items-center justify-center p-4 opacity-20 select-none grayscale pointer-events-none">
                                        <div className="flex flex-col items-center gap-4">
                                            <Calendar size={120} strokeWidth={0.5} />
                                            <p className="text-[10px] font-semibold uppercase tracking-wide">No se detectan secuencias temporales activas</p>
                                        </div>
                                    </div>
                                ) : (
                                    items.map((item, idx) => {
                                        const pos = getPosition(item.start_date);
                                        const width = getWidth(item.start_date, item.end_date);
                                        
                                        return (
                                            <div key={item.id} className="h-8 relative group">
                                                <GanttBarItem
                                                    item={item}
                                                    pos={pos}
                                                    width={width}
                                                    idx={idx}
                                                    onClick={onItemClick}
                                                    onMove={onItemMove}
                                                    onResize={onItemResize}
                                                />
                                            </div>
                                        );
                                    })
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* ─── Footer Informativo ─── */}
            <div className="px-4 py-1.5 border-t border-[hsl(var(--border))] dark:border-white/5 bg-[hsl(var(--surface-1))] dark:bg-white/[0.02] flex items-center justify-between">
                <div className="flex gap-3">
                    <div className="flex items-center gap-2">
                        <div className="size-2 rounded-full bg-[hsl(var(--primary))]" />
                        <span className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">En Curso</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="size-2 rounded-full bg-sky-500" />
                        <span className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Planificado</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="size-2 rounded-full bg-emerald-500 shadow-lg shadow-emerald-500/20" />
                        <span className="font-semibold text-emerald-500 uppercase tracking-wide">Ejecución Exitosa</span>
                    </div>
                </div>
                <button className="flex items-center gap-2 font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide hover:text-[hsl(var(--primary))] transition-colors">
                    <Info size={14} /> Protocolo de Visualización
                </button>
            </div>
        </div>
    );
}
