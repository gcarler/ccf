"use client";

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
    LayoutDashboard, Inbox, ClipboardList, Sparkles, Users,
    Briefcase, GraduationCap, Target, Settings, Bell,
    Plus, PanelLeftClose
} from 'lucide-react';
import clsx from 'clsx';

export default function WorkspaceMiniSidebar({ onHide }: { onHide?: () => void }) {
    const pathname = usePathname();

    const menuItems = [
        { id: 'dashboard', icon: LayoutDashboard, label: 'Dashboard', href: '/' },
        { id: 'inbox', icon: Inbox, label: 'Bandeja de Entrada', href: '/inbox' },
        { id: 'tasks', icon: ClipboardList, label: 'Mis Tareas', href: '/projects' },
        { id: 'ai', icon: Sparkles, label: 'Ask AI', href: '#', color: 'text-purple-500' },
    ];

    const teamItems = [
        { id: 'teams', icon: Users, label: 'Equipos', href: '/crm' },
        { id: 'spaces', icon: Briefcase, label: 'Proyectos', href: '/projects' },
        { id: 'academy', icon: GraduationCap, label: 'Academia', href: '/academy' },
        { id: 'goals', icon: Target, label: 'Metas', href: '/admin' },
    ];

    return (
        <aside className="w-[52px] h-full bg-[#1e1f21] dark:bg-[#18191b] flex flex-col items-center py-4 rounded-2xl shadow-xl border border-slate-200 dark:border-white/10 shrink-0 z-[100] transition-all duration-300">
            {/* Top action: Hide Menu */}
            <div className="mb-6 flex items-center w-full justify-center">
                <button 
                    onClick={onHide} 
                    className="size-8 shrink-0 rounded-xl bg-white/5 text-slate-400 hover:bg-blue-600 hover:text-white flex items-center justify-center shadow-lg active:scale-95 transition-all cursor-pointer group relative"
                >
                    <PanelLeftClose size={16} />
                    <div className="absolute left-[44px] top-1/2 -translate-y-1/2 bg-slate-900 text-white text-[10px] font-black uppercase tracking-widest px-2.5 py-1.5 rounded-lg opacity-0 group-hover:opacity-100 pointer-events-none transition-all z-[200] whitespace-nowrap border border-white/10 shadow-2xl">
                        Ocultar Menú
                    </div>
                </button>
            </div>

            {/* Main Actions */}
            <div className="flex-1 flex flex-col gap-1 overflow-y-auto scrollbar-none w-full items-center">
                {menuItems.map((item) => (
                    <SidebarIcon key={item.id} {...item} active={pathname === item.href} />
                ))}
                
                <div className="h-[1px] bg-white/10 my-3 shrink-0 w-5" />
                
                {teamItems.map((item) => (
                    <SidebarIcon key={item.id} {...item} active={pathname === item.href} />
                ))}

                <button className="mt-2 rounded-xl border border-dashed border-white/10 flex items-center text-slate-500 hover:text-white hover:border-white/30 transition-all active:scale-95 shrink-0 size-8 justify-center">
                    <Plus size={16} />
                </button>
            </div>

            {/* Bottom: Settings & Profile */}
            <div className="mt-auto flex flex-col gap-2 shrink-0 pt-4 w-full items-center pb-4">
                <SidebarIcon id="notif" icon={Bell} label="Notificaciones" />
                <SidebarIcon id="settings" icon={Settings} label="Ajustes" />
                
                <div className="mt-2 flex items-center gap-3 transition-all justify-center">
                    <div className="size-8 shrink-0 rounded-full bg-indigo-600 flex items-center justify-center text-[10px] font-black text-white cursor-pointer ring-2 ring-transparent hover:ring-blue-500 shadow-lg">
                        JD
                    </div>
                </div>
            </div>
        </aside>
    );
}



function SidebarIcon({ icon: Icon, label, active, color, onSelect, href }: any) {
    const baseClasses = clsx(
        "rounded-xl flex items-center transition-all duration-200 relative size-8 justify-center shrink-0",
        active 
            ? "bg-blue-600 text-white shadow-[0_0_15px_rgba(37,99,235,0.3)]" 
            : "text-slate-500 hover:text-slate-200 hover:bg-white/5"
    );

    const innerContent = (
        <>
            <Icon size={18} className={color} strokeWidth={active ? 2.5 : 2} />
            {active && (
                <div className="absolute left-[-6px] top-1/2 -translate-y-1/2 w-1 h-4 bg-blue-600 rounded-r-full shadow-[0_0_10px_rgba(37,99,235,0.5)]" />
            )}
        </>
    );

    return (
        <div className="relative group py-1.5 cursor-pointer w-full flex justify-center">
            {href ? (
                <Link href={href} className={baseClasses}>
                    {innerContent}
                </Link>
            ) : (
                <button onClick={onSelect} className={baseClasses}>
                    {innerContent}
                </button>
            )}
            
            {/* Tooltip ONLY when collapsed */}
            <div className="absolute left-[44px] top-1/2 -translate-y-1/2 bg-slate-900 text-white text-[10px] font-black uppercase tracking-widest px-2.5 py-1.5 rounded-lg opacity-0 group-hover:opacity-100 pointer-events-none transition-all z-[200] whitespace-nowrap border border-white/10 shadow-2xl">
                {label}
            </div>
        </div>
    );
}
