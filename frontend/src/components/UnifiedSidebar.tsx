"use client";

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import OptimizedImage from "@/components/ui/OptimizedImage";
import {
    Home, Inbox, Users, GraduationCap, Target, Settings, Bell,
    ChevronDown, ChevronRight, Layout, Folder, ChevronLeft,
    BrainCircuit
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import { useContentBlock } from '@/hooks/useContent';
import { SITE_NAME } from '@/lib/site-config';

export default function UnifiedSidebar({
    title,
    sections = []
}: {
    title?: string,
    sections?: any[]
}) {
    const pathname = usePathname();
    const [isMini, setIsMini] = useState(false);
    const { data: logoBranding } = useContentBlock('logo_branding');
    const logoUrl: string | undefined = logoBranding?.logo_url;
    const logoDisplayName: string = logoBranding?.site_name || title || SITE_NAME;
    const [expandedFolders, setExpandedFolders] = useState<string[]>(['contextual-root', 'Income']);

    // Persist sidebar state
    useEffect(() => {
        const savedState = localStorage.getItem('ccf_unified_sidebar_mini');
        if (savedState) {
            setIsMini(savedState === 'true');
        }
    }, []);

    const toggleSidebar = () => {
        const newState = !isMini;
        setIsMini(newState);
        localStorage.setItem('ccf_unified_sidebar_mini', newState ? 'true' : 'false');
    };

    const toggleFolder = (id: string, e?: React.MouseEvent) => {
        if (e) {
            e.preventDefault();
            e.stopPropagation();
        }
        setExpandedFolders(prev => prev.includes(id) ? prev.filter(f => f !== id) : [...prev, id]);
    };

    // Global items matching the mock structure roughly
    const GLOBAL_MAIN = [
        { id: 'dashboard', label: 'Inicio', href: '/', icon: Home },
        { id: 'inbox', label: 'Bandeja de Entrada', href: '/plataforma/inbox', icon: Inbox },
        { id: 'crm', label: 'CRM / Equipos', href: '/plataforma/crm', icon: Users },
        { id: 'academy', label: 'Academia', href: '/plataforma/academy', icon: GraduationCap },
        { id: 'projects', label: 'Proyectos', href: '/plataforma/projects', icon: Layout },
        { id: 'agents', label: 'Agentes IA', href: '/plataforma/agents', icon: BrainCircuit },
    ];

    const GLOBAL_SETTINGS = [
        { id: 'goals', label: 'Metas', href: '/plataforma/admin', icon: Target },
        { id: 'notifications', label: 'Notificaciones', href: '/plataforma/inbox', icon: Bell },
        { id: 'settings', label: 'Ajustes', href: '/plataforma/settings', icon: Settings },
    ];

    const renderItem = (item: any, depth = 0, hasChildren = false, isExpanded = false, onToggle?: (e: React.MouseEvent) => void) => {
        const isActive = (pathname || '') === item.href || (item.href !== '/' && (pathname || '').startsWith(item.href));
        
        return (
            <div key={item.id} className="relative w-full">
                {item.href && !hasChildren ? (
                    <Link
                        href={item.href}
                        className={clsx(
                            "flex items-center gap-3 py-2 rounded-md transition-all cursor-pointer group relative",
                            isMini ? "justify-center px-0 w-10 mx-auto" : "px-3 w-full",
                            isActive 
                                ? "bg-slate-100 dark:bg-white/10 text-slate-900 dark:text-white font-bold" 
                                : "text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 hover:bg-slate-50 dark:hover:bg-white/5"
                        )}
                    >
                        {/* Nested indicator line */}
                        {depth > 0 && !isMini && (
                            <div className="absolute left-[15px] top-[-8px] bottom-1/2 w-[1px] bg-slate-200 dark:bg-white/10" />
                        )}
                        {depth > 0 && !isMini && (
                            <div className="absolute left-[15px] top-1/2 w-3 h-[1px] bg-slate-200 dark:bg-white/10" />
                        )}

                        {item.icon && (
                            <item.icon 
                                size={20} 
                                strokeWidth={isActive ? 2.5 : 2} 
                                className={clsx(
                                    isActive ? "text-slate-900 dark:text-white" : "text-slate-400 group-hover:text-slate-600 dark:group-hover:text-slate-300",
                                    depth > 0 && !isMini && "ml-4"
                                )} 
                            />
                        )}
                        
                        {!isMini && <span className="text-[13px] truncate flex-1">{item.label}</span>}
                    </Link>
                ) : (
                    <div
                        onClick={onToggle}
                        className={clsx(
                            "flex items-center gap-3 py-2 rounded-md transition-all cursor-pointer group relative",
                            isMini ? "justify-center px-0 w-10 mx-auto" : "px-3 w-full",
                            isActive 
                                ? "bg-slate-100 dark:bg-white/10 text-slate-900 dark:text-white font-bold" 
                                : "text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 hover:bg-slate-50 dark:hover:bg-white/5"
                        )}
                    >
                        {item.icon && (
                            <item.icon 
                                size={20} 
                                strokeWidth={isActive ? 2.5 : 2} 
                                className={clsx(
                                    isActive ? "text-slate-900 dark:text-white" : "text-slate-400 group-hover:text-slate-600 dark:group-hover:text-slate-300",
                                    depth > 0 && !isMini && "ml-4"
                                )} 
                            />
                        )}
                        
                        {!isMini && <span className="text-[13px] truncate flex-1">{item.label}</span>}

                        {!isMini && hasChildren && (
                            <ChevronDown 
                                size={14} 
                                className={clsx("text-slate-400 transition-transform duration-200", !isExpanded && "-rotate-90")} 
                            />
                        )}
                    </div>
                )}
            </div>
        );
    };

    return (
        <aside
            className={clsx(
                "h-[100dvh] bg-white/80 dark:bg-[#18191b]/80 backdrop-blur-xl border-r border-slate-200 dark:border-white/5 flex flex-col z-50 shrink-0 transition-all duration-300 relative font-sans",
                isMini ? "w-[72px]" : "w-[260px]"
            )}
        >            {/* Toggle Button `< >` positioned absolutely on the right edge */}
            <div className="absolute right-0 translate-x-1/2 top-3 z-[60]">
                <button 
                    onClick={toggleSidebar}
                    className="w-6 h-6 rounded-full bg-[hsl(var(--bg-primary))] dark:bg-[#2a2b2d] border border-slate-200 dark:border-white/10 shadow-sm flex items-center justify-center text-slate-500 hover:text-[hsl(var(--primary))] transition-all active:scale-95"
                >
                    {isMini ? <ChevronRight size={12} strokeWidth={3} /> : <div className="flex -space-x-1"><ChevronLeft size={12} strokeWidth={3}/><ChevronRight size={12} strokeWidth={3}/></div>}
                </button>
            </div>

            {/* Sidebar Header (Logo) */}
            <div className="h-12 flex items-center px-3 shrink-0">
                <div className="flex items-center gap-3 w-full">
                    <div className="w-8 h-8 rounded-md bg-slate-900 dark:bg-[hsl(var(--bg-primary))] flex items-center justify-center shrink-0 overflow-hidden">
                        {logoUrl ? (
                            <OptimizedImage src={logoUrl} alt={logoDisplayName} fill className="w-full h-full object-contain p-1" />
                        ) : (
                            <div className="w-3.5 h-3.5 rounded-full border-2 border-white dark:border-slate-900 relative">
                                <div className="absolute top-[-2px] right-[-2px] w-1.5 h-1.5 bg-[hsl(var(--bg-primary))] dark:bg-slate-900" />
                            </div>
                        )}
                    </div>
                    {!isMini && (
                        <div className="flex-1 overflow-hidden">
                            <span className="font-semibold text-slate-900 dark:text-white tracking-tight">{logoDisplayName}</span>
                        </div>
                    )}
                </div>
            </div>

            {/* Content Area */}
            <div className="flex-1 overflow-y-auto overflow-x-hidden scrollbar-none py-2 px-3 flex flex-col gap-3">
                
                {/* 1. Global Module Navigation (MAIN) */}
                <div className="flex flex-col gap-1">
                    {!isMini && <span className="px-3 text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-2">Main</span>}
                    {GLOBAL_MAIN.map(item => renderItem(item))}
                </div>

                {/* 2. Contextual Sections (e.g. from Projects layout) */}
                {sections && sections.length > 0 && (
                    <div className="flex flex-col gap-1">
                        {!isMini && <span className="px-3 text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-2">Contextual Tools</span>}
                        
                        <div className="flex flex-col gap-0.5">
                            {renderItem(
                                { id: 'contextual-root', label: sections[0]?.label || 'Herramientas', icon: Folder }, 
                                0, 
                                true, 
                                expandedFolders.includes('contextual-root'), 
                                (e) => toggleFolder('contextual-root', e)
                            )}
                            
                            {/* Nested Contextual Items */}
                            <AnimatePresence initial={false}>
                                {!isMini && expandedFolders.includes('contextual-root') && (
                                    <motion.div 
                                        initial={{ height: 0, opacity: 0 }}
                                        animate={{ height: 'auto', opacity: 1 }}
                                        exit={{ height: 0, opacity: 0 }}
                                        className="overflow-hidden relative pl-4 ml-6 border-l border-slate-200 dark:border-white/10 mt-1 space-y-0.5"
                                    >
                                        {sections.flatMap((section: any) => section.items || []).map((item: any) => (
                                            <Link key={item.id} href={item.href || '/'} className="flex items-center px-2 py-1.5 text-[12px] text-slate-500 hover:text-slate-800 dark:hover:text-white rounded-md transition-colors w-full group">
                                                <span className="truncate">{item.label}</span>
                                            </Link>
                                        ))}
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </div>
                    </div>
                )}

                {/* 3. Global Settings */}
                <div className="flex flex-col gap-1 mt-auto shrink-0 pb-4">
                    {!isMini && <span className="px-3 text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-2">Settings</span>}
                    {GLOBAL_SETTINGS.map(item => renderItem(item))}
                </div>

            </div>
        </aside>
    );
}
