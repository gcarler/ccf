"use client";

import React from 'react';
import { 
    Layout, 
    Users, 
    GraduationCap, 
    Globe, 
    Settings, 
    PanelLeftClose,
    Plus,
    Target
} from 'lucide-react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import Tooltip from '@/components/ui/Tooltip';
import clsx from 'clsx';
import { useCreation } from '@/context/CreationContext';

export default function WorkspaceMiniSidebar({ onHide }: { onHide: () => void }) {
    const pathname = usePathname();
    const router = useRouter();
    const { openModal } = useCreation();

    const items = [
        { id: 'projects', icon: Target, href: '/projects', label: 'Proyectos' },
        { id: 'academy', icon: GraduationCap, href: '/academy', label: 'Academia' },
        { id: 'crm', icon: Users, href: '/crm', label: 'Comunidad' },
        { id: 'cms', icon: Globe, href: '/cms', label: 'Sitio Web' },
    ];

    return (
        <aside className="w-16 h-full bg-slate-900 dark:bg-black rounded-[2rem] flex flex-col items-center py-6 gap-4 shadow-2xl relative border border-white/5">
            {/* Global Add Button */}
            <button 
                onClick={() => openModal('task')}
                className="size-10 rounded-2xl bg-blue-600 text-white flex items-center justify-center hover:scale-110 active:scale-95 transition-all shadow-lg shadow-blue-500/40 group relative mb-4"
            >
                <Plus size={20} />
                <div className="absolute left-14 px-2 py-1 bg-slate-800 text-white text-[10px] font-bold rounded opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap transition-opacity z-[100]">
                    Creación Rápida
                </div>
            </button>

            {items.map((item) => {
                const isActive = pathname?.startsWith(item.href);
                return (
                    <Tooltip key={item.id} content={item.label} position="right">
                        <Link href={item.href}>
                            <div className={clsx(
                                "size-10 rounded-2xl flex items-center justify-center transition-all cursor-pointer group mb-1",
                                isActive 
                                    ? "bg-white/10 text-white shadow-inner" 
                                    : "text-slate-500 hover:bg-white/5 hover:text-slate-300"
                            )}>
                                <item.icon size={20} className={clsx(isActive && "text-blue-400")} />
                            </div>
                        </Link>
                    </Tooltip>
                );
            })}

            <div className="mt-auto flex flex-col items-center gap-4">
                <Tooltip content="Ajustes de Workspace" position="right">
                    <div className="size-10 rounded-2xl flex items-center justify-center text-slate-500 hover:bg-white/5 hover:text-slate-300 transition-all cursor-pointer">
                        <Settings size={20} />
                    </div>
                </Tooltip>
                
                <button 
                    onClick={onHide}
                    className="size-10 rounded-2xl flex items-center justify-center text-slate-600 hover:text-rose-400 transition-all group"
                >
                    <PanelLeftClose size={20} />
                </button>
            </div>
        </aside>
    );
}
