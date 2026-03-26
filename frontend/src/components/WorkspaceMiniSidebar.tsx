"use client";

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
    Home,
    Bell,
    Inbox,
    Users,
    Layers,
    GraduationCap,
    BarChart3,
    Settings,
    Search,
    Plus,
    PanelLeft,
    Sparkles,
    Hash,
    MessageSquare,
    ClipboardList,
    Target
} from 'lucide-react';
import clsx from 'clsx';

export default function WorkspaceMiniSidebar({ isMini, onToggle }: { isMini?: boolean, onToggle?: () => void }) {
    const pathname = usePathname();

    const menuItems = [
        { id: 'home', icon: Home, label: 'Inicio', href: '/' },
        { id: 'inbox', icon: Inbox, label: 'Bandeja de Entrada', href: '/inbox' },
        { id: 'tasks', icon: ClipboardList, label: 'Mis Tareas', href: '/projects' },
        { id: 'ai', icon: Sparkles, label: 'Ask AI', href: '#', color: 'text-purple-500' },
    ];

    const teamItems = [
        { id: 'teams', icon: Users, label: 'Equipos', href: '/crm' },
        { id: 'spaces', icon: Layers, label: 'Espacios', href: '/projects' },
        { id: 'academy', icon: GraduationCap, label: 'Academia', href: '/academy' },
        { id: 'goals', icon: Target, label: 'Metas', href: '/admin' },
    ];

    return (
        <aside className="w-[56px] h-full bg-[#111213] flex flex-col items-center py-4 border-r border-white/5 shrink-0 z-[100]">
            {/* Top: Brand/Logo */}
            <div className="mb-6">
                <div className="size-8 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-lg shadow-blue-500/20 active:scale-95 transition-all cursor-pointer">
                    <span className="text-[14px] font-black italic">CCF</span>
                </div>
            </div>

            {/* Main Actions */}
            <div className="flex-1 w-full flex flex-col items-center gap-1 overflow-y-auto scrollbar-none">
                {menuItems.map((item) => (
                    <SidebarIcon key={item.id} {...item} active={pathname === item.href} />
                ))}
                
                <div className="w-6 h-[1px] bg-white/10 my-2" />
                
                {teamItems.map((item) => (
                    <SidebarIcon key={item.id} {...item} active={pathname === item.href} />
                ))}

                <button className="mt-2 size-9 rounded-xl border border-dashed border-white/10 flex items-center justify-center text-slate-500 hover:text-white hover:border-white/30 transition-all active:scale-95">
                    <Plus size={18} />
                </button>
            </div>

            {/* Bottom: Settings & Profile */}
            <div className="mt-auto flex flex-col items-center gap-2">
                <SidebarIcon id="notif" icon={Bell} label="Notificaciones" />
                <SidebarIcon id="settings" icon={Settings} label="Ajustes" />
                <div className="mt-2 size-8 rounded-full bg-indigo-600 flex items-center justify-center text-[10px] font-black text-white cursor-pointer ring-2 ring-transparent hover:ring-blue-500 transition-all">
                    JD
                </div>
            </div>
        </aside>
    );
}

function SidebarIcon({ icon: Icon, label, active, color, onSelect }: any) {
    return (
        <div className="relative group flex items-center justify-center w-full py-1">
            <button
                onClick={onSelect}
                className={clsx(
                    "size-9 rounded-xl flex items-center justify-center transition-all duration-200 relative",
                    active 
                        ? "bg-blue-600 text-white shadow-lg shadow-blue-500/20" 
                        : "text-slate-500 hover:text-slate-200 hover:bg-white/5"
                )}
            >
                <Icon size={20} className={color} strokeWidth={active ? 2.5 : 2} />
                {active && (
                    <div className="absolute left-[-4px] top-1/2 -translate-y-1/2 w-1.5 h-5 bg-blue-600 rounded-r-full shadow-[0_0_10px_rgba(37,99,235,0.5)]" />
                )}
            </button>
            
            {/* Tooltip */}
            <div className="absolute left-[64px] bg-slate-900 text-white text-[10px] font-black uppercase tracking-widest px-2.5 py-1.5 rounded-lg opacity-0 group-hover:opacity-100 pointer-events-none transition-all z-[200] whitespace-nowrap border border-white/10 shadow-2xl">
                {label}
            </div>
        </div>
    );
}
