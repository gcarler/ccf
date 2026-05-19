"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import {
    Plus,
    Search,
    Edit3,
    BookOpen,
    Video,
    FileText,
    Clock,
    CheckCircle2,
    Loader2,
    Sparkles,
    Layout,
    Globe
} from 'lucide-react';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { ViewType } from '@/components/ViewSwitcher';
import UniversalCalendarView from '@/components/ui/UniversalCalendarView';
import UniversalGanttView from '@/components/ui/UniversalGanttView';
import UniversalWikiView from '@/components/ui/UniversalWikiView';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

const CONTENT_VIEWS: ViewType[] = ['grid', 'list', 'table', 'board', 'kanban', 'calendar', 'gantt', 'wiki'];

export default function AdminContentList() {
    const { token, isAuthenticated } = useAuth();
    const { addToast } = useToast();
    const router = useRouter();
    const [activeTab, setActiveTab] = useState<'courses' | 'sermons' | 'resources'>('courses');
    const [items, setItems] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [viewType, setViewType] = useState<ViewType>('list');

    const fetchData = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            if (activeTab === 'courses') {
                const data = await apiFetch<any[]>('/academy/courses/?published_only=false', { token, cache: 'no-store' });
                setItems(Array.isArray(data) ? data : []);
            } else {
                // Mock for sermons/resources until endpoints are ready
                setItems([]);
            }
        } catch (err) {
            console.error(err);
            addToast("Error al sincronizar contenidos", "error");
        } finally {
            setLoading(false);
        }
    }, [token, activeTab, addToast]);

    useEffect(() => {
        if (isAuthenticated) fetchData();
    }, [isAuthenticated, fetchData]);

    const filteredItems = items.filter(item => 
        (item.title || item.name || '').toLowerCase().includes(searchQuery.toLowerCase())
    );

    const groupedItems = [
        { id: 'published', label: 'Publicado', items: filteredItems.filter(item => item.is_published) },
        { id: 'draft', label: 'Borrador', items: filteredItems.filter(item => !item.is_published) },
    ];

    const calendarEvents = filteredItems.map(item => ({
        id: item.id,
        title: item.title || item.name || `Contenido #${item.id}`,
        date: (item.updated_at || item.created_at || new Date().toISOString()).split('T')[0],
        color: item.is_published ? 'emerald' as const : 'amber' as const,
        location: item.modality || activeTab,
    }));

    const ganttItems = filteredItems.map(item => {
        const start = item.created_at || item.updated_at || new Date().toISOString();
        const end = item.updated_at || start;
        return {
            id: item.id,
            title: item.title || item.name || `Contenido #${item.id}`,
            subtitle: item.code || item.modality || activeTab,
            start_date: start,
            end_date: end,
            color: item.is_published ? 'emerald' as const : 'amber' as const,
            progress: item.is_published ? 100 : 45,
        };
    });

    const openItem = (item: any) => {
        if (activeTab === 'courses') router.push(`/admin/content/courses/${item.id}`);
    };

    if (!isAuthenticated) return null;

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#0a0f16] font-display overflow-hidden">
            <style jsx global>{`
                .content-aura {
                    position: relative;
                }
                .content-aura::after {
                    content: '';
                    position: absolute;
                    inset: -1px;
                    background: linear-gradient(45deg, var(--aura-color, #3b82f610), transparent 60%);
                    z-index: -1;
                    border-radius: inherit;
                    opacity: 0;
                    transition: opacity 0.5s ease;
                }
                .content-aura:hover::after {
                    opacity: 1;
                }
            `}</style>

            <WorkspaceToolbar 
                breadcrumbs={[{ label: 'Admin', icon: Layout }, { label: 'Fábrica de Contenidos', icon: BookOpen }]}
                viewType={viewType}
                setViewType={setViewType}
                availableViews={CONTENT_VIEWS}
                onSearch={setSearchQuery}
                rightActions={
                    <button 
                        onClick={() => router.push('/admin/content/courses/new')}
                        className="flex items-center gap-3 px-8 py-3 bg-blue-600 text-white rounded-[1.5rem] text-[11px] font-black uppercase tracking-widest shadow-xl shadow-blue-500/20 active:scale-95 transition-all hover:bg-blue-700"
                    >
                        <Plus size={18} /> Crear Nuevo
                    </button>
                }
            />

            {/* Cinematic Tabs */}
            <div className="flex px-10 border-b border-slate-100 dark:border-white/5 bg-slate-50/50 dark:bg-white/5 shrink-0 relative overflow-hidden">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_#3b82f605_0%,_transparent_50%)] pointer-events-none" />
                <TabBtn label="Cursos Faro" active={activeTab === 'courses'} onClick={() => setActiveTab('courses')} icon={BookOpen} />
                <TabBtn label="Prédicas HD" active={activeTab === 'sermons'} onClick={() => setActiveTab('sermons')} icon={Video} />
                <TabBtn label="Guías y Material" active={activeTab === 'resources'} onClick={() => setActiveTab('resources')} icon={FileText} />
            </div>

            <main className="flex-1 overflow-y-auto scrollbar-thin p-8 lg:p-12 relative pb-40">
                <div className="max-w-6xl mx-auto space-y-10 relative z-10">
                    
                    {/* Search Bar Cinematic */}
                    <div className="relative group">
                        <Search className="absolute left-6 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-blue-600 transition-colors" size={22} />
                        <input 
                            value={searchQuery}
                            onChange={e => setSearchQuery(e.target.value)}
                            className="w-full bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[2.5rem] py-6 pl-16 pr-8 text-sm font-bold shadow-sm focus:ring-8 focus:ring-blue-500/5 focus:border-blue-500 transition-all outline-none"
                            placeholder={`Buscar en la biblioteca de ${activeTab === 'courses' ? 'cursos' : 'contenidos'}...`}
                        />
                    </div>

                    <AnimatePresence mode="wait">
                        {loading ? (
                            <div className="py-40 flex flex-col items-center justify-center gap-6 text-slate-400 font-black uppercase tracking-[0.5em] animate-pulse">
                                <Loader2 className="animate-spin" size={48} strokeWidth={1.5} /> Sincronizando Biblioteca...
                            </div>
                        ) : filteredItems.length > 0 && viewType === 'grid' ? (
                            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                                {filteredItems.map((item, i) => (
                                    <motion.button
                                        key={item.id}
                                        initial={{ opacity: 0, y: 18 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        transition={{ delay: i * 0.04 }}
                                        onClick={() => openItem(item)}
                                        className="text-left content-aura bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 p-7 rounded-[2.5rem] shadow-sm hover:shadow-2xl transition-all"
                                    >
                                        <div className={clsx("size-16 rounded-[1.5rem] flex items-center justify-center mb-8", item.is_published ? "bg-emerald-50 text-emerald-600" : "bg-amber-50 text-amber-600")}>
                                            <BookOpen size={30} strokeWidth={1.5} />
                                        </div>
                                        <h3 className="text-lg font-black text-slate-900 dark:text-white uppercase tracking-tight line-clamp-2">{item.title}</h3>
                                        <p className="mt-3 text-[10px] font-bold text-slate-400 uppercase tracking-widest">{item.code || activeTab} · {item.duration_hours || 0} horas</p>
                                        <span className={clsx("inline-flex mt-6 px-3 py-1 rounded-xl text-[9px] font-black uppercase tracking-widest", item.is_published ? "bg-emerald-50 text-emerald-600" : "bg-amber-50 text-amber-600")}>{item.is_published ? 'Publicado' : 'Borrador'}</span>
                                    </motion.button>
                                ))}
                            </motion.div>
                        ) : filteredItems.length > 0 && viewType === 'table' ? (
                            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="rounded-[2rem] border border-slate-200 dark:border-white/10 overflow-hidden bg-white dark:bg-white/5">
                                <table className="w-full text-left">
                                    <thead className="bg-slate-50 dark:bg-white/5">
                                        <tr>
                                            <th className="px-5 py-4 text-[10px] font-black uppercase tracking-widest text-slate-400">Contenido</th>
                                            <th className="px-5 py-4 text-[10px] font-black uppercase tracking-widest text-slate-400 hidden md:table-cell">Código</th>
                                            <th className="px-5 py-4 text-[10px] font-black uppercase tracking-widest text-slate-400 hidden lg:table-cell">Estado</th>
                                            <th className="px-5 py-4 text-[10px] font-black uppercase tracking-widest text-slate-400">Editar</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-slate-100 dark:divide-white/5">
                                        {filteredItems.map(item => (
                                            <tr key={item.id} onClick={() => openItem(item)} className="hover:bg-slate-50 dark:hover:bg-white/[0.03] cursor-pointer">
                                                <td className="px-5 py-4 text-sm font-bold text-slate-800 dark:text-slate-100">{item.title}</td>
                                                <td className="px-5 py-4 hidden md:table-cell text-[11px] font-mono text-slate-400">{item.code || '—'}</td>
                                                <td className="px-5 py-4 hidden lg:table-cell"><span className={clsx("px-2 py-0.5 rounded-full text-[9px] font-black uppercase", item.is_published ? "bg-emerald-50 text-emerald-600" : "bg-amber-50 text-amber-600")}>{item.is_published ? 'Publicado' : 'Borrador'}</span></td>
                                                <td className="px-5 py-4"><Edit3 size={16} className="text-blue-600" /></td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </motion.div>
                        ) : filteredItems.length > 0 && (viewType === 'board' || viewType === 'kanban') ? (
                            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                                {groupedItems.map(group => (
                                    <section key={group.id} className="rounded-[2.5rem] bg-slate-50 dark:bg-white/[0.03] border border-slate-200 dark:border-white/10 p-5">
                                        <div className="flex items-center justify-between mb-5">
                                            <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">{group.label}</span>
                                            <span className="text-[10px] font-black text-slate-400">{group.items.length}</span>
                                        </div>
                                        <div className="space-y-4">
                                            {group.items.map(item => (
                                                <button key={item.id} onClick={() => openItem(item)} className="w-full text-left bg-white dark:bg-white/[0.05] border border-slate-100 dark:border-white/5 rounded-[1.5rem] p-5 hover:border-blue-300 transition-all">
                                                    <p className="text-sm font-black text-slate-900 dark:text-white uppercase tracking-tight">{item.title}</p>
                                                    <p className="mt-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest">{item.code || item.modality || activeTab}</p>
                                                </button>
                                            ))}
                                        </div>
                                    </section>
                                ))}
                            </motion.div>
                        ) : filteredItems.length > 0 && viewType === 'calendar' ? (
                            <UniversalCalendarView
                                title="Calendario de contenidos"
                                events={calendarEvents}
                                onEventClick={(event) => {
                                    const item = filteredItems.find(entry => entry.id === event.id);
                                    if (item) openItem(item);
                                }}
                            />
                        ) : filteredItems.length > 0 && viewType === 'gantt' ? (
                            <UniversalGanttView
                                moduleName="Fábrica de contenidos"
                                items={ganttItems}
                                onItemClick={(item) => {
                                    const entry = filteredItems.find(content => content.id === item.id);
                                    if (entry) openItem(entry);
                                }}
                            />
                        ) : filteredItems.length > 0 && viewType === 'wiki' ? (
                            <UniversalWikiView moduleName="Fábrica de contenidos" storageKey={`admin-content-wiki-${activeTab}`} />
                        ) : filteredItems.length > 0 ? (
                            <motion.div 
                                initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                                className="grid grid-cols-1 gap-6"
                            >
                                {filteredItems.map((item, i) => (
                                    <motion.div 
                                        key={item.id}
                                        initial={{ opacity: 0, x: -20 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        transition={{ delay: i * 0.05 }}
                                        className="content-aura group bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 p-8 rounded-[3rem] shadow-sm hover:shadow-2xl transition-all duration-500 flex flex-col md:flex-row md:items-center justify-between gap-8"
                                        style={{ '--aura-color': item.is_published ? 'rgba(16, 185, 129, 0.1)' : 'rgba(245, 158, 11, 0.1)' } as any}
                                    >
                                        <div className="flex items-center gap-8 flex-1">
                                            <div className={clsx(
                                                "size-20 rounded-[2rem] flex items-center justify-center shadow-inner group-hover:scale-110 transition-all duration-500",
                                                item.is_published ? "bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600" : "bg-amber-50 dark:bg-amber-900/20 text-amber-600"
                                            )}>
                                                <BookOpen size={36} strokeWidth={1.5} />
                                            </div>
                                            <div className="flex-1 space-y-2">
                                                <div className="flex items-center gap-3">
                                                    <h3 className="text-xl font-black text-slate-900 dark:text-white uppercase tracking-tight leading-none group-hover:text-blue-600 transition-colors">{item.title}</h3>
                                                    <span className="px-2 py-0.5 bg-slate-100 dark:bg-white/10 rounded text-[8px] font-black text-slate-400 uppercase tracking-widest">{item.code}</span>
                                                </div>
                                                <div className="flex items-center gap-6 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                                                    <span className="flex items-center gap-1.5"><Clock size={12} /> {item.duration_hours} Horas</span>
                                                    <span className="flex items-center gap-1.5"><Globe size={12} /> {item.modality}</span>
                                                    <span className="flex items-center gap-1.5 text-blue-500"><CheckCircle2 size={12} /> {item.certificate_type}</span>
                                                </div>
                                            </div>
                                        </div>

                                        <div className="flex items-center gap-4 shrink-0">
                                            <div className={clsx(
                                                "px-4 py-1.5 rounded-xl text-[9px] font-black uppercase tracking-widest border",
                                                item.is_published ? "bg-emerald-50 text-emerald-600 border-emerald-100" : "bg-amber-50 text-amber-600 border-amber-100"
                                            )}>
                                                {item.is_published ? 'Publicado' : 'Borrador'}
                                            </div>
                                            <button 
                                                onClick={() => router.push(`/admin/content/courses/${item.id}`)}
                                                className="p-4 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-2xl shadow-xl hover:scale-110 active:scale-95 transition-all"
                                            >
                                                <Edit3 size={20} />
                                            </button>
                                        </div>
                                    </motion.div>
                                ))}
                            </motion.div>
                        ) : (
                            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="py-40 text-center space-y-6">
                                <div className="size-24 rounded-[2.5rem] bg-slate-50 dark:bg-white/5 border-2 border-dashed border-slate-200 dark:border-white/10 flex items-center justify-center mx-auto text-slate-300">
                                    <Sparkles size={40} strokeWidth={1} />
                                </div>
                                <div className="space-y-2">
                                    <p className="text-xl font-black text-slate-800 dark:text-white uppercase tracking-tight">Biblioteca en blanco</p>
                                    <p className="text-xs text-slate-400 font-bold uppercase tracking-widest">Comienza a crear el currículo de tu iglesia hoy mismo.</p>
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            </main>
        </div>
    );
}

function TabBtn({ label, active, onClick, icon: Icon }: any) {
    return (
        <button 
            onClick={onClick}
            className={clsx(
                "px-8 py-6 text-[11px] font-black uppercase tracking-[0.3em] transition-all relative flex items-center gap-3 shrink-0 border-b-2",
                active ? "text-blue-600 border-blue-600" : "text-slate-400 border-transparent hover:text-slate-600"
            )}
        >
            <Icon size={14} className={clsx(active ? "text-blue-600" : "text-slate-300")} />
            {label}
            {active && <motion.div layoutId="content-tab-active" className="absolute bottom-[-2px] left-0 right-0 h-1 bg-blue-600 rounded-t-full shadow-[0_0_15px_rgba(37,99,235,0.4)]" />}
        </button>
    );
}

