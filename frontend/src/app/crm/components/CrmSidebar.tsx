'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
    ChevronDown,
    ChevronRight,
    LayoutDashboard,
    Users,
    Calendar,
    MessageSquare,
    Columns,
    Heart,
    Home as HouseIcon,
    ShieldCheck,
    QrCode,
    Settings,
    Plus,
    Bell,
    CheckCircle2,
    Inbox,
    Clock,
    Target,
    Layers,
    Monitor,
    MoreHorizontal,
    Search,
    PieChart,
    UserPlus,
    Scan,
    MessageCircle
} from 'lucide-react';

export default function CrmSidebar() {
    const pathname = usePathname();
    const [expandedSpaces, setExpandedSpaces] = useState<string[]>(['ministerio', 'comunidad']);

    const toggleSpace = (id: string) => {
        setExpandedSpaces(prev =>
            prev.includes(id) ? prev.filter(s => s !== id) : [...prev, id]
        );
    };

    const isActive = (path: string) => {
        if (path === '/crm' || path === '/') return pathname === path;
        return pathname?.startsWith(path);
    };

    const navItem = (href: string, icon: React.ReactNode, label: string, color?: string, isLocked?: boolean) => (
        <Link
            href={href}
            className={`flex items-center gap-2.5 px-3 py-1.5 rounded-md text-[13px] font-medium transition-all group relative ${isActive(href)
                    ? 'bg-white/10 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
                }`}
        >
            <div className={`${isActive(href) ? 'text-white' : color || 'text-slate-500'} group-hover:scale-110 transition-transform shrink-0`}>
                {React.cloneElement(icon as React.ReactElement, { size: 18 })}
            </div>
            <span className="flex-1 truncate">{label}</span>
            {isLocked && <Clock size={12} className="text-slate-600" />}
            {isActive(href) && <div className="absolute left-0 w-1 h-4 bg-cu-purple rounded-r-full"></div>}
        </Link>
    );

    return (
        <div className="flex h-screen fixed left-0 top-0 z-[60]">
            {/* GLOBAL BAR (Far Left - Narrow) */}
            <div className="w-[56px] bg-[#1e2227] border-r border-white/5 flex flex-col items-center py-4 gap-4 shrink-0">
                <div className="size-8 rounded-lg bg-cu-purple flex items-center justify-center text-white font-bold text-sm shadow-lg mb-2 cursor-pointer hover:scale-105 transition-transform">
                    CC
                </div>

                <div className="flex flex-col gap-2 w-full items-center">
                    <button className="p-2.5 text-slate-400 hover:text-white hover:bg-white/5 rounded-xl transition-all">
                        <Inbox size={20} />
                    </button>
                    <button className="p-2.5 text-slate-400 hover:text-white hover:bg-white/5 rounded-xl transition-all">
                        <Clock size={20} />
                    </button>
                    <button className="p-2.5 text-slate-400 hover:text-white hover:bg-white/5 rounded-xl transition-all relative">
                        <Bell size={20} />
                        <span className="absolute top-2 right-2 size-2 bg-rose-500 rounded-full border-2 border-[#1e2227]"></span>
                    </button>
                </div>

                <div className="mt-auto flex flex-col gap-2 w-full items-center pb-4">
                    <button className="p-2.5 text-slate-400 hover:text-white hover:bg-white/5 rounded-xl transition-all">
                        <Monitor size={20} />
                    </button>
                    <div className="size-8 rounded-full bg-indigo-500/20 flex items-center justify-center text-indigo-400 font-bold text-[10px] border border-indigo-400/20 cursor-pointer">
                        JD
                    </div>
                </div>
            </div>

            {/* CONTEXT SIDEBAR (ClickUp Navigation) */}
            <aside className="w-[220px] bg-[#2a2e34] border-r border-white/5 flex flex-col text-slate-300 shadow-2xl overflow-hidden font-display">
                {/* Workspace Switcher */}
                <div className="p-3 border-b border-white/5 flex items-center justify-between group cursor-pointer hover:bg-white/5 transition-colors m-2 rounded-lg">
                    <div className="flex items-center gap-2.5 overflow-hidden">
                        <div className="size-6 rounded bg-gradient-to-tr from-cu-purple to-indigo-500 flex items-center justify-center text-white font-black text-[10px] shrink-0 shadow-md">
                            C
                        </div>
                        <h2 className="text-[13px] font-bold text-white truncate">Carlos&apos;s Workspace</h2>
                    </div>
                    <ChevronDown size={14} className="text-slate-500 group-hover:text-white transition-colors" />
                </div>

                {/* Main Navigation */}
                <div className="flex-1 overflow-y-auto px-2 py-2 space-y-6 scrollbar-thin scrollbar-thumb-white/10">
                    <div className="space-y-0.5">
                        {navItem('/crm', <LayoutDashboard />, 'Inicio')}
                        {navItem('/crm/analytics', <PieChart />, 'Analítica', 'text-blue-400')}
                        {navItem('/crm/messaging', <Inbox />, 'Bandeja de entrada')}
                        {navItem('/crm/tasks', <CheckCircle2 />, 'Mis tareas', 'text-emerald-500')}
                        <button className="w-full flex items-center gap-2.5 px-3 py-1.5 text-[13px] text-slate-500 hover:text-slate-300 transition-colors">
                            <MoreHorizontal size={18} />
                            <span>Más</span>
                        </button>
                    </div>

                    {/* FAVORITOS */}
                    <div className="space-y-0.5">
                        <div className="px-3 py-1 text-[11px] font-bold uppercase tracking-wider text-slate-500 flex items-center justify-between group">
                            Favoritos
                            <ChevronRight size={12} className="opacity-0 group-hover:opacity-100 transition-opacity" />
                        </div>
                        {navItem('/crm/pipeline', <Target />, 'Proyectos', 'text-cu-blue')}
                        {navItem('/crm/contacts', <UserPlus />, 'Leads/Contactos', 'text-amber-400')}
                    </div>

                    {/* ESPACIOS */}
                    <div className="space-y-1">
                        <div className="px-3 py-1 text-[11px] font-bold uppercase tracking-wider text-slate-500 flex items-center justify-between">
                            Espacios
                            <Plus size={14} className="hover:text-white cursor-pointer" />
                        </div>

                        {/* SPACE: MINISTERIO */}
                        <div className="space-y-0.5">
                            <button
                                onClick={() => toggleSpace('ministerio')}
                                className="w-full flex items-center gap-2 px-3 py-1 text-[12px] font-medium text-slate-400 hover:text-slate-200"
                            >
                                <div className="size-4 rounded bg-cu-purple/20 flex items-center justify-center text-cu-purple font-black text-[8px]">M</div>
                                <span className="flex-1 text-left">Ministerio</span>
                                {expandedSpaces.includes('ministerio') ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                            </button>
                            {expandedSpaces.includes('ministerio') && (
                                <div className="ml-6 space-y-0.5 border-l border-white/5 pl-2">
                                    {navItem('/crm/pipeline', <Layers />, 'Consolidación')}
                                    {navItem('/crm/counseling', <Heart />, 'Consejería')}
                                    {navItem('/crm/prayers', <MessageCircle />, 'Muro de Oración')}
                                    {navItem('/crm/groups', <HouseIcon />, 'Casas de Gloria')}
                                </div>
                            )}
                        </div>

                        {/* SPACE: COMUNIDAD */}
                        <div className="space-y-0.5">
                            <button
                                onClick={() => toggleSpace('comunidad')}
                                className="w-full flex items-center gap-2 px-3 py-1 text-[12px] font-medium text-slate-400 hover:text-slate-200"
                            >
                                <div className="size-4 rounded bg-emerald-500/20 flex items-center justify-center text-emerald-500 font-black text-[8px]">C</div>
                                <span className="flex-1 text-left">Comunidad</span>
                                {expandedSpaces.includes('comunidad') ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                            </button>
                            {expandedSpaces.includes('comunidad') && (
                                <div className="ml-6 space-y-0.5 border-l border-white/5 pl-2">
                                    {navItem('/crm/members', <Users />, 'Miembros')}
                                    {navItem('/crm/volunteers', <ShieldCheck />, 'Servidores')}
                                    {navItem('/crm/events', <Calendar />, 'Eventos')}
                                    {navItem('/crm/scanner', <Scan />, 'Escáner ASST')}
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* Footer Actions */}
                <div className="p-3 bg-[#1e2227]/50 border-t border-white/5">
                    {navItem('/crm/my-card', <QrCode />, 'Mi Carnet', 'text-emerald-400')}
                    {navItem('/crm/settings', <Settings />, 'Configuración')}
                </div>
            </aside>
        </div>
    );
}

