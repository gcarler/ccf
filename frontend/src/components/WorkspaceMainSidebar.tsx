"use client";

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
    ChevronDown, 
    ChevronRight,
    Settings2
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

export default function WorkspaceMainSidebar({ title, sections, isMini }: { title: string, sections?: any[], isMini?: boolean }) {
    const pathname = usePathname();
    const [expandedFolders, setExpandedFolders] = useState<string[]>(['Gestión', 'Operaciones', 'Inteligencia', 'Comunidad', 'Aprendizaje', 'Atención', 'General']);

    const toggleFolder = (title: string) => {
        setExpandedFolders(prev => prev.includes(title) ? prev.filter(f => f !== title) : [...prev, title]);
    };

    const renderItem = (item: any) => {
        const isActive = pathname === item.href || (item.href !== '/' && pathname?.startsWith(item.href));
        const Icon = item.icon;
        
        return (
            <Link key={item.id} href={item.href}>
                <div className={clsx(
                    "flex items-center gap-3 px-3 py-2 mx-2 rounded-xl transition-all group cursor-pointer mb-0.5",
                    isActive 
                        ? "bg-blue-600 text-white shadow-lg shadow-blue-500/20" 
                        : "text-slate-500 hover:bg-slate-100 dark:hover:bg-white/5 hover:text-slate-900 dark:hover:text-white"
                )}>
                    <Icon size={18} className={clsx(isActive ? "text-white" : "text-slate-400 group-hover:text-blue-500")} />
                    {!isMini && (
                        <>
                            <span className="text-[13px] font-bold flex-1 truncate leading-none">{item.label}</span>
                            {item.count && (
                                <span className={clsx(
                                    "px-1.5 py-0.5 rounded-md text-[9px] font-black leading-none",
                                    isActive ? "bg-white/20 text-white" : "bg-blue-100 text-blue-600"
                                )}>
                                    {item.count}
                                </span>
                            )}
                        </>
                    )}
                </div>
            </Link>
        );
    };

    return (
        <aside className="h-full flex flex-col bg-white dark:bg-[#1e1f21] transition-all duration-300">
            {/* Header: Dynamic Module Title */}
            <div className="h-14 flex items-center px-6 border-b border-slate-100 dark:border-white/5 shrink-0">
                {!isMini && <h2 className="text-[12px] font-black text-slate-400 dark:text-slate-500 tracking-[0.2em] uppercase truncate">{title}</h2>}
            </div>

            <div className="flex-1 overflow-y-auto scrollbar-hide py-4">
                {sections && sections.length > 0 && sections.map((group, idx) => (
                    <div key={group.title || idx} className="mb-6">
                        {!isMini && group.title && (
                            <div 
                                onClick={() => toggleFolder(group.title)}
                                className="flex items-center justify-between px-6 mb-2 cursor-pointer group/header"
                            >
                                <span className="text-[10px] font-black uppercase tracking-[0.25em] text-slate-400 group-hover/header:text-slate-600 transition-colors">{group.title}</span>
                                <ChevronDown size={12} className={clsx("text-slate-300 transition-transform", !expandedFolders.includes(group.title) && "-rotate-90")} />
                            </div>
                        )}
                        <AnimatePresence initial={false}>
                            {(!group.title || expandedFolders.includes(group.title)) && (
                                <motion.div
                                    initial={{ height: 0, opacity: 0 }}
                                    animate={{ height: 'auto', opacity: 1 }}
                                    exit={{ height: 0, opacity: 0 }}
                                    className="overflow-hidden"
                                >
                                    {group.items?.map(renderItem)}
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                ))}
            </div>

            {/* Footer */}
            <div className="p-4 mt-auto border-t border-slate-100 dark:border-white/5">
                <button className="w-full flex items-center justify-center gap-2 py-3 bg-slate-50 dark:bg-white/5 hover:bg-slate-100 dark:hover:bg-white/10 rounded-2xl text-[11px] font-black uppercase tracking-widest text-slate-600 dark:text-slate-300 transition-all border border-slate-200/50 dark:border-white/5 shadow-sm">
                    <Settings2 size={14} /> {!isMini && "Ajustes"}
                </button>
            </div>
        </aside>
    );
}
