"use client";

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
    ChevronDown, 
    Plus,
    Hash,
    Layers,
    MessageSquare,
    User,
    Search,
    FolderKanban,
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
    Edit3,
    Archive,
    Trash2,
    Settings2,
    Copy,
    ExternalLink
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

interface SidebarItem {
    id: string;
    label: string;
    href: string;
    icon?: any;
    count?: number;
    status?: string | number;
}

const INICIO_ITEMS = [
    { id: 'respuestas', label: 'Respuestas', href: '/projects/responses', icon: Inbox },
    { id: 'comentarios', label: 'Comentarios asignados', href: '/projects/comments', icon: MessageCircle },
    { id: 'tareas', label: 'Mis tareas', href: '/projects/tasks', icon: CheckCircle2 },
    { id: 'mas', label: 'Más', href: '/projects/more', icon: MoreHorizontal }
];

const CANALES = [
    { id: 'general', label: 'General / Carlos...', href: '/projects/general', icon: Hash },
    { id: 'welcome', label: 'Welcome', href: '/projects/welcome', icon: Hash },
];

const MENSAJES = [
    { id: 'dm1', label: 'gscarlos777@gmail.com', href: '#', icon: User },
    { id: 'dm2', label: 'Carlos Ernesto Gómez', href: '#', icon: User, status: 'busy' },
];

function ContextMenuItem({ icon: Icon, label, color = "text-slate-600 dark:text-slate-300" }: { icon: any, label: string, color?: string }) {
    return (
        <div className={`flex items-center gap-3 px-3 py-1.5 hover:bg-slate-100 dark:hover:bg-white/5 cursor-pointer transition-colors group/menu`}>
            <Icon size={14} className={`${color} group-hover/menu:scale-110 transition-transform`} />
            <span className={`text-[12px] font-medium ${color}`}>{label}</span>
        </div>
    );
}

export default function WorkspaceMainSidebar({ title, sections }: { title: string, sections?: any[] }) {
    const pathname = usePathname();
    const [expandedFolders, setExpandedFolders] = useState<string[]>(['espacios', 'proyectos', 'navigation']);
    const [activeMenu, setActiveMenu] = useState<string | null>(null);

    const toggleFolder = (id: string) => {
        setExpandedFolders(prev => prev.includes(id) ? prev.filter(f => f !== id) : [...prev, id]);
    };

    const renderItem = (item: any, depth = 0) => {
        const isActive = item.href === '/' || item.href === '/admin' || item.href === '/academy' || item.href === '/crm' || item.href === '/projects'
            ? (pathname || '') === item.href
            : (pathname || '').startsWith(item.href);
        
        return (
            <div key={item.id} className="relative">
                <Link
                    href={item.href}
                    className={clsx(
                        "flex items-center justify-between px-2 py-1.5 rounded-lg transition-all group cursor-pointer relative",
                        isActive 
                            ? "bg-blue-50/50 dark:bg-blue-500/10 text-blue-600 dark:text-blue-400 font-bold" 
                            : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-white/5"
                    )}
                >
                    {depth > 0 && <div className="absolute left-[-12px] top-[-8px] bottom-0 w-[1px] bg-slate-200 dark:bg-white/5" />}
                    {depth > 0 && <div className="absolute left-[-12px] top-1/2 w-3 h-[1px] bg-slate-200 dark:bg-white/5" />}

                    <div className="flex items-center gap-2 overflow-hidden">
                        {item.icon && <item.icon size={14} strokeWidth={isActive ? 2.5 : 2} className={isActive ? "text-blue-600 dark:text-blue-400" : "text-slate-400 group-hover:text-slate-500"} />}
                        <span className="truncate text-[12px]">{item.label}</span>
                    </div>
                    
                    <div className="flex items-center gap-1.5">
                        {item.count !== undefined && (
                            <span className="text-[9px] font-black bg-slate-200 dark:bg-white/10 px-1.5 py-0.5 rounded text-slate-500">{item.count}</span>
                        )}
                        <button 
                            onClick={(e) => { e.preventDefault(); e.stopPropagation(); setActiveMenu(activeMenu === item.id ? null : item.id); }}
                            className="opacity-0 group-hover:opacity-100 p-0.5 hover:bg-slate-200 dark:hover:bg-white/10 rounded transition-all text-slate-400"
                        >
                            <MoreHorizontal size={14} />
                        </button>
                        {item.status === 'busy' && <div className="w-1.5 h-1.5 rounded-full bg-slate-300 border border-slate-400" />}
                    </div>
                </Link>

                <AnimatePresence>
                    {activeMenu === item.id && (
                        <>
                            <div className="fixed inset-0 z-[100]" onClick={() => setActiveMenu(null)} />
                            <motion.div 
                                initial={{ opacity: 0, scale: 0.95, y: -10 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: 0.95, y: -10 }}
                                className="absolute right-0 top-10 w-48 bg-white dark:bg-[#2a2b2d] rounded-xl shadow-2xl border border-slate-200 dark:border-white/10 py-1.5 z-[110] overflow-hidden"
                            >
                                <div className="px-3 py-1.5 mb-1 border-b border-slate-100 dark:border-white/5 flex items-center gap-2">
                                     <div className="w-2 h-2 rounded-full bg-blue-500" />
                                     <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest truncate">{item.label}</span>
                                </div>
                                <ContextMenuItem icon={Edit3} label="Renombrar" />
                                <ContextMenuItem icon={Copy} label="Duplicar" />
                                <ContextMenuItem icon={Star} label="Añadir a favoritos" />
                                <div className="h-[1px] bg-slate-100 dark:bg-white/5 my-1" />
                                <ContextMenuItem icon={Archive} label="Archivar" />
                                <ContextMenuItem icon={Trash2} label="Borrar" color="text-rose-500" />
                            </motion.div>
                        </>
                    )}
                </AnimatePresence>
            </div>
        );
    };

    return (
        <aside className="w-[260px] bg-[#f9fafb] dark:bg-[#18191b] border-r border-slate-200 dark:border-white/5 flex flex-col z-40 shrink-0 shadow-[-10px_0_20px_rgba(0,0,0,0.05)_inset]">
            {/* Sidebar Header */}
            <div className="h-12 flex items-center justify-between px-4 border-b border-slate-200 dark:border-white/5 bg-white dark:bg-[#1e1f21]">
                <div className="flex items-center gap-2 overflow-hidden cursor-pointer hover:bg-slate-50 dark:hover:bg-white/5 p-1 rounded-md transition-colors">
                    <span className="text-[13px] font-black text-slate-800 dark:text-slate-100 truncate">{title}</span>
                    <ChevronDown size={14} className="text-slate-400 shrink-0" />
                </div>
                <button className="p-1.5 hover:bg-slate-100 dark:hover:bg-white/5 rounded-md transition-colors text-slate-400">
                    <Search size={14} />
                </button>
            </div>

            {/* Navigation Content */}
            <div className="flex-1 overflow-y-auto py-4 px-3 space-y-6 scrollbar-thin">
                
                {/* Global Navigation (Start) */}
                <div className="space-y-1">
                    <div className="flex items-center justify-between px-2 mb-2">
                        <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">Inicio</span>
                        <button className="p-1 hover:bg-slate-200 dark:hover:bg-white/10 rounded-md text-slate-400"><Plus size={12} /></button>
                    </div>
                    <div className="space-y-0.5">
                        {INICIO_ITEMS.map((item) => renderItem(item))}
                    </div>
                </div>

                <div className="h-[1px] bg-slate-200 dark:bg-white/5 mx-2" />

                {/* Spaces Tree (ClickUp Style) */}
                <div className="space-y-1">
                    <div className="flex items-center justify-between px-2 mb-2">
                        <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">Espacios</span>
                        <div className="flex items-center gap-1">
                            <button className="p-1 hover:bg-slate-200 dark:hover:bg-white/10 rounded-md text-slate-400"><Search size={12} /></button>
                            <button className="p-1 hover:bg-slate-200 dark:hover:bg-white/10 rounded-md text-slate-400"><Plus size={12} /></button>
                        </div>
                    </div>

                    {/* Espacio Root */}
                    <div className="space-y-0.5" id="espacios">
                        <div 
                            className="flex items-center gap-2 px-2 py-1.5 text-[13px] font-bold text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/5 rounded-lg cursor-pointer transition-all group/space"
                            onClick={() => toggleFolder('espacios')}
                        >
                            <ChevronDown size={14} className={clsx("text-slate-400 transition-transform", !expandedFolders.includes('espacios') && "-rotate-90")} />
                            <div className="w-5 h-5 rounded bg-purple-600 flex items-center justify-center text-[10px] text-white shadow-sm font-black shrink-0">E</div>
                            <span className="flex-1 truncate">Espacio del equipo [ES]</span>
                            <MoreHorizontal size={14} className="text-slate-400 opacity-0 group-hover/space:opacity-100 transition-opacity" />
                        </div>
                        
                        {expandedFolders.includes('espacios') && (
                            <div className="ml-5 pl-2 border-l border-slate-200 dark:border-white/5 space-y-0.5 mt-1 relative">
                                {/* Folder: Proyectos */}
                                <div 
                                    className="flex items-center gap-2 px-2 py-1.5 text-[12px] font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-white/5 rounded-lg cursor-pointer transition-colors group/folder relative"
                                    onClick={(e) => { e.stopPropagation(); toggleFolder('proyectos'); }}
                                >
                                    <div className="absolute left-[-8px] top-1/2 w-2 h-[1px] bg-slate-200 dark:bg-white/5" />
                                    <ChevronDown size={14} className={clsx("text-slate-400 transition-transform", !expandedFolders.includes('proyectos') && "-rotate-90")} />
                                    <Folder size={14} className="text-slate-400 fill-slate-200 dark:fill-white/5" />
                                    <span className="flex-1 truncate">Proyectos</span>
                                    <Plus size={12} className="text-slate-400 opacity-0 group-hover/folder:opacity-100" />
                                </div>
                                
                                {/* Projects inside Folder */}
                                {expandedFolders.includes('proyectos') && (
                                    <div className="ml-5 pl-2 border-l border-slate-200 dark:border-white/5 space-y-0.5 mt-1 relative">
                                        {renderItem({ id: 'p1', label: 'Proyecto 1', href: '/projects', icon: Layout, count: 5 }, 1)}
                                        {renderItem({ id: 'p2', label: 'Diseño Web', href: '/projects/2', icon: Layout, count: 2 }, 1)}
                                        {renderItem({ id: 'p3', label: 'Lanzamiento App', href: '/projects/3', icon: Layout }, 1)}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>

                <div className="h-[1px] bg-slate-200 dark:bg-white/5 mx-2" />

                {/* Direct Messages */}
                <div className="space-y-1">
                    <div className="flex items-center justify-between px-2 mb-2">
                        <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">Mensajes Directos</span>
                        <button className="p-1 hover:bg-slate-200 dark:hover:bg-white/10 rounded-md text-slate-400"><Plus size={12} /></button>
                    </div>
                    <div className="space-y-0.5">
                        {MENSAJES.map((item) => renderItem(item))}
                    </div>
                </div>
            </div>

            {/* Footer Action */}
            <div className="p-3 bg-white dark:bg-[#18191b] border-t border-slate-200 dark:border-white/5 mt-auto">
                <button className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-xl text-[11px] font-black uppercase tracking-widest hover:scale-[1.02] active:scale-95 transition-all shadow-lg">
                    <Plus size={16} /> Invitar al Equipo
                </button>
            </div>
        </aside>
    );
}
