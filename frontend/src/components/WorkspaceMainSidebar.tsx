"use client";

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
    ChevronDown, 
    Plus,
    Hash,
    Layers,
    User,
    Search,
    MoreHorizontal,
    Layout,
    Clock,
    CheckCircle2,
    MessageCircle,
    Star,
    ChevronRight,
    Circle,
    Folder,
    Inbox,
    Home,
    CheckSquare,
    Calendar,
    LayoutDashboard,
    FileText,
    Bell,
    Users,
    BookOpen,
    Sparkles,
    Settings2
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

export default function WorkspaceMainSidebar({ title, sections, isMini }: { title: string, sections?: any[], isMini?: boolean }) {
    const pathname = usePathname();
    const [expandedFolders, setExpandedFolders] = useState<string[]>(['principal', 'herramientas', 'comunidad']);

    const toggleFolder = (id: string) => {
        setExpandedFolders(prev => prev.includes(id) ? prev.filter(f => f !== id) : [...prev, id]);
    };

    const navigationGroups = [
        {
            id: 'principal',
            label: 'Principal',
            items: [
                { id: 'home', label: 'Inicio', href: '/', icon: Home },
                { id: 'inbox', label: 'Inbox', href: '/inbox', icon: Inbox, count: 3 },
                { id: 'tasks', label: 'Mis Tareas', href: '/tasks', icon: CheckSquare },
                { id: 'projects', label: 'Portfolio', href: '/projects', icon: Folder },
            ]
        },
        {
            id: 'herramientas',
            label: 'Herramientas',
            items: [
                { id: 'calendar', label: 'Calendario', href: '/calendar', icon: Calendar },
                { id: 'whiteboard', label: 'Pizarra', href: '/whiteboard', icon: LayoutDashboard },
                { id: 'documents', label: 'Documentos', href: '/documents', icon: FileText },
                { id: 'reminders', label: 'Recordatorios', href: '/reminders', icon: Bell },
            ]
        },
        {
            id: 'comunidad',
            label: 'Comunidad',
            items: [
                { id: 'crm', label: 'Comunidad (CRM)', href: '/crm', icon: Users },
                { id: 'academy', label: 'Academia', href: '/academy', icon: BookOpen },
                { id: 'comentarios', label: 'Comentarios', href: '/projects/comments', icon: MessageCircle },
            ]
        }
    ];

    const renderItem = (item: any) => {
        const isActive = pathname === item.href || (item.href !== '/' && pathname?.startsWith(item.href));
        
        return (
            <Link key={item.id} href={item.href}>
                <div className={clsx(
                    "flex items-center gap-3 px-3 py-2 mx-2 rounded-xl transition-all group cursor-pointer mb-0.5",
                    isActive 
                        ? "bg-blue-600 text-white shadow-lg shadow-blue-500/20" 
                        : "text-slate-500 hover:bg-slate-100 dark:hover:bg-white/5 hover:text-slate-900 dark:hover:text-white"
                )}>
                    <item.icon size={18} className={clsx(isActive ? "text-white" : "text-slate-400 group-hover:text-blue-500")} />
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
        <aside className={clsx(
            "h-full flex flex-col bg-white dark:bg-[#1e1f21] border-r border-slate-100 dark:border-white/5 transition-all duration-300",
            isMini ? "w-20" : "w-72"
        )}>
            {/* Header: Dynamic Title */}
            <div className="h-14 flex items-center px-6 border-b border-slate-100 dark:border-white/5">
                <div className="flex items-center gap-3 truncate">
                    <div className="size-8 rounded-xl bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-lg">
                        <Sparkles size={16} />
                    </div>
                    {!isMini && <h2 className="text-[15px] font-black text-slate-800 dark:text-white tracking-tight truncate">{title}</h2>}
                </div>
            </div>

            <div className="flex-1 overflow-y-auto scrollbar-hide py-4">
                {navigationGroups.map(group => (
                    <div key={group.id} className="mb-6">
                        {!isMini && (
                            <div 
                                onClick={() => toggleFolder(group.id)}
                                className="flex items-center justify-between px-6 mb-2 cursor-pointer group/header"
                            >
                                <span className="text-[10px] font-black uppercase tracking-[0.25em] text-slate-400 group-hover/header:text-slate-600 transition-colors">{group.label}</span>
                                <ChevronDown size={12} className={clsx("text-slate-300 transition-transform", !expandedFolders.includes(group.id) && "-rotate-90")} />
                            </div>
                        )}
                        <AnimatePresence initial={false}>
                            {expandedFolders.includes(group.id) && (
                                <motion.div
                                    initial={{ height: 0, opacity: 0 }}
                                    animate={{ height: 'auto', opacity: 1 }}
                                    exit={{ height: 0, opacity: 0 }}
                                    className="overflow-hidden"
                                >
                                    {group.items.map(renderItem)}
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                ))}

                {/* Dinamic Sections (from Props) */}
                {sections && sections.length > 0 && (
                    <div className="pt-4 border-t border-slate-100 dark:border-white/5 mt-4">
                        <div className="px-6 mb-4 flex items-center justify-between">
                            <span className="text-[10px] font-black uppercase tracking-[0.25em] text-slate-400">Personalizado</span>
                        </div>
                        {sections.map(section => (
                            <div key={section.id || section.title} className="space-y-1">
                                {section.items?.map(renderItem)}
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Footer */}
            <div className="p-4 mt-auto border-t border-slate-100 dark:border-white/5">
                <button className="w-full flex items-center justify-center gap-2 py-3 bg-slate-50 dark:bg-white/5 hover:bg-slate-100 dark:hover:bg-white/10 rounded-2xl text-[11px] font-black uppercase tracking-widest text-slate-600 dark:text-slate-300 transition-all border border-slate-200/50 dark:border-white/5 shadow-sm">
                    <Settings2 size={14} /> {!isMini && "Configuración"}
                </button>
            </div>
        </aside>
    );
}
