"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import {
    CreditCard,
    Smartphone,
    Banknote,
    Plus,
    Edit3,
    Mail,
    FileText,
    Settings,
    ShieldCheck,
    Layout,
    DollarSign,
    Zap,
    Palette,
    Sparkles,
    Check
} from 'lucide-react';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import type { ViewType } from '@/components/ViewSwitcher';
import UniversalCalendarView from '@/components/ui/UniversalCalendarView';
import UniversalGanttView from '@/components/ui/UniversalGanttView';
import UniversalWikiView from '@/components/ui/UniversalWikiView';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import Skeleton from '@/components/ui/Skeleton';

interface Category {
    id: number;
    name: string;
    description: string;
    color: string;
    active: boolean;
}
const DONATION_CONFIG_VIEWS: ViewType[] = ['grid', 'list', 'table', 'board', 'kanban', 'calendar', 'gantt', 'wiki'];

export default function DonationConfig() {
    const { token, isAuthenticated } = useAuth();
    const { addToast } = useToast();
    const [categories, setCategories] = useState<Category[]>([]);
    const [loading, setLoading] = useState(true);
    const [titheEnabled, setTitheEnabled] = useState(true);
    const [viewType, setViewType] = useState<ViewType>('grid');

    const fetchCategories = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const data = await apiFetch<Category[]>('/admin/donation-categories', { token, cache: 'no-store' });
            setCategories(Array.isArray(data) ? data : []);
        } catch (err) {
            console.error(err);
            addToast("Error al sincronizar categorías contables", "error");
        } finally {
            setLoading(false);
        }
    }, [token, addToast]);

    useEffect(() => {
        if (isAuthenticated) fetchCategories();
    }, [isAuthenticated, fetchCategories]);

    if (!isAuthenticated) return null;

    const groupedCategories = [
        { id: 'active', label: 'Activos', rows: categories.filter((cat) => cat.active) },
        { id: 'inactive', label: 'Inactivos', rows: categories.filter((cat) => !cat.active) },
    ];

    const calendarEvents = categories.map((cat, index) => ({
        id: cat.id,
        title: cat.name,
        date: new Date(Date.now() + index * 86400000).toISOString().split('T')[0],
        color: cat.active ? 'emerald' as const : 'amber' as const,
        location: cat.description,
    }));

    const ganttItems = categories.map((cat, index) => {
        const date = new Date(Date.now() + index * 86400000).toISOString();
        return {
            id: cat.id,
            title: cat.name,
            subtitle: cat.description,
            start_date: date,
            end_date: date,
            color: cat.active ? 'emerald' as const : 'amber' as const,
            progress: cat.active ? 100 : 35,
        };
    });

    const renderList = () => (
        <div className="space-y-4">
            {categories.map((cat) => (
                <div key={cat.id} className="config-aura p-3 bg-white dark:bg-white/5 rounded-lg border border-slate-100 dark:border-white/5 flex items-center justify-between gap-5" style={{ '--aura-color': 'rgba(59, 130, 246, 0.1)' } as any}>
                    <div>
                        <h3 className="text-sm font-semibold text-slate-900 dark:text-white uppercase tracking-tight">{cat.name}</h3>
                        <p className="mt-1 text-[10px] text-slate-400 font-bold uppercase tracking-wide">{cat.description || 'Fondo ministerial'}</p>
                    </div>
                    <span className={clsx("px-2 py-0.5 rounded-full text-[9px] font-semibold uppercase", cat.active ? "bg-emerald-50 text-emerald-600" : "bg-amber-50 text-amber-600")}>{cat.active ? 'Activo' : 'Inactivo'}</span>
                </div>
            ))}
        </div>
    );

    const renderTable = () => (
        <div className="rounded-lg border border-slate-200 dark:border-white/10 overflow-hidden bg-white dark:bg-white/5">
            <table className="w-full text-left">
                <thead className="bg-slate-50 dark:bg-white/5">
                    <tr>
                        <th className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400">Fondo</th>
                        <th className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400 hidden md:table-cell">Descripción</th>
                        <th className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400">Estado</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-white/5">
                    {categories.map((cat) => (
                        <tr key={cat.id} className="hover:bg-slate-50 dark:hover:bg-white/[0.03]">
                            <td className="px-3 py-1.5 text-sm font-bold text-slate-800 dark:text-slate-100">{cat.name}</td>
                            <td className="px-3 py-1.5 hidden md:table-cell text-[11px] text-slate-500">{cat.description || '—'}</td>
                            <td className="px-3 py-1.5"><span className={clsx("px-2 py-0.5 rounded-full text-[9px] font-semibold uppercase", cat.active ? "bg-emerald-50 text-emerald-600" : "bg-amber-50 text-amber-600")}>{cat.active ? 'Activo' : 'Inactivo'}</span></td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );

    const renderBoard = () => (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {groupedCategories.map((group) => (
                <section key={group.id} className="rounded-lg bg-slate-50 dark:bg-white/[0.03] border border-slate-200 dark:border-white/10 p-3">
                    <div className="flex items-center justify-between mb-5">
                        <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">{group.label}</span>
                        <span className="font-semibold text-slate-400">{group.rows.length}</span>
                    </div>
                    <div className="space-y-3">
                        {group.rows.map((cat) => (
                            <div key={cat.id} className="bg-white dark:bg-white/[0.05] border border-slate-100 dark:border-white/5 rounded-lg p-4">
                                <p className="text-sm font-semibold text-slate-900 dark:text-white uppercase tracking-tight">{cat.name}</p>
                                <p className="mt-2 text-[10px] font-bold text-slate-400">{cat.description || 'Fondo ministerial'}</p>
                            </div>
                        ))}
                    </div>
                </section>
            ))}
        </div>
    );

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#0a0f16] overflow-hidden animate-fade-in font-display">
            <style jsx global>{`
                .config-aura {
                    position: relative;
                }
                .config-aura::after {
                    content: '';
                    position: absolute;
                    inset: -1px;
                    background: linear-gradient(45deg, var(--aura-color, #3b82f610), transparent 60%);
                    z-index: -1;
                    border-radius: inherit;
                    opacity: 0;
                    transition: opacity 0.5s ease;
                }
                .config-aura:hover::after {
                    opacity: 1;
                }
            `}</style>

            <WorkspaceToolbar 
                breadcrumbs={[{ label: 'Ajustes', icon: Settings }, { label: 'Finanzas', icon: DollarSign }, { label: 'Estructura de Recaudación', icon: ShieldCheck }]}
                viewType={viewType}
                setViewType={setViewType}
                availableViews={DONATION_CONFIG_VIEWS}
                rightActions={
                    <button className="flex items-center gap-2 px-4 py-3 bg-blue-600 text-white rounded-lg text-[11px] font-semibold uppercase tracking-wide shadow-xl shadow-blue-500/20 active:scale-95 transition-all">
                        <Zap size={16} /> Aplicar Protocolo
                    </button>
                }
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin p-4 lg:p-4 relative pb-4">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_#3b82f605_0%,_transparent_50%)] pointer-events-none" />

                <div className="max-w-5xl mx-auto space-y-3 relative z-10">
                    
                    {/* Hero Config Section Cinematic */}
                    <header className="space-y-4">
                        <motion.div 
                            initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}
                            className="inline-flex items-center gap-2 px-4 py-1.5 bg-blue-500/10 text-blue-600 rounded-full text-[10px] font-semibold uppercase tracking-wide border border-blue-500/20"
                        >
                            <Sparkles size={12} className="animate-pulse" /> Ingeniería de Tesorería v3.9
                        </motion.div>
                        <h1 className="text-xl lg:text-xl font-black text-slate-900 dark:text-white tracking-tighter leading-none">
                            Estructura de <br/> <span className="text-blue-600 italic text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-400">Recaudación Pro.</span>
                        </h1>
                        <p className="text-lg text-slate-500 dark:text-slate-400 font-medium max-w-2xl leading-relaxed">
                            Define el flujo de bendición. Configura canales de pago, fondos específicos y automatización de certificados tributarios.
                        </p>
                    </header>

                    {viewType === 'list' ? (
                        renderList()
                    ) : viewType === 'table' ? (
                        renderTable()
                    ) : viewType === 'board' || viewType === 'kanban' ? (
                        renderBoard()
                    ) : viewType === 'calendar' ? (
                        <UniversalCalendarView events={calendarEvents} title="Calendario de fondos" />
                    ) : viewType === 'gantt' ? (
                        <UniversalGanttView items={ganttItems} moduleName="Estructura de recaudación" />
                    ) : viewType === 'wiki' ? (
                        <UniversalWikiView moduleName="Estructura de recaudación" storageKey="wiki_admin_donation_config" />
                    ) : (
                    <>
                    {/* Master Switch Cinematic */}
                    <motion.section 
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="p-4 bg-slate-900 rounded-lg text-white shadow-2xl relative overflow-hidden group border border-white/5 flex flex-col md:flex-row items-center justify-between gap-3"
                    >
                        <div className="absolute top-0 right-0 w-96 h-96 bg-blue-600/10 rounded-full blur-[120px] group-hover:bg-blue-600/20 transition-all duration-1000" />
                        <div className="relative z-10 space-y-3 text-center md:text-left">
                            <h3 className="text-lg font-bold tracking-tight uppercase">Pasarela de Diezmo Digital</h3>
                            <p className="text-xs font-bold text-slate-400 uppercase tracking-wide leading-loose">Habilitar transacciones en línea seguras para toda la congregación.</p>
                        </div>
                        <button
                            onClick={() => setTitheEnabled(!titheEnabled)}
                            className={clsx(
                                "relative w-20 h-10 rounded-full transition-all duration-500 z-10 shrink-0",
                                titheEnabled ? 'bg-blue-600 shadow-[0_0_30px_rgba(37,99,235,0.6)]' : 'bg-slate-800 border border-white/10'
                            )}
                        >
                            <motion.div 
                                animate={{ x: titheEnabled ? 44 : 4 }}
                                className="absolute top-1.5 size-7 bg-white rounded-full shadow-2xl flex items-center justify-center text-blue-600"
                            >
                                {titheEnabled ? <Check size={14} strokeWidth={4} /> : <div className="size-1 bg-slate-300 rounded-full" />}
                            </motion.div>
                        </button>
                    </motion.section>

                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
                        {/* Payment Channels */}
                        <section className="lg:col-span-5 space-y-3">
                            <div className="flex items-center gap-3 px-4">
                                <CreditCard size={18} className="text-blue-600" />
                                <h2 className="text-[11px] font-semibold uppercase tracking-wide text-slate-400 leading-none">Canales Autorizados</h2>
                            </div>
                            <div className="bg-slate-50 dark:bg-white/5 rounded-lg border border-slate-100 dark:border-white/5 divide-y divide-slate-100 dark:divide-white/10 overflow-hidden shadow-sm">
                                <PaymentMethodItem icon={CreditCard} label="Tarjeta Global" active />
                                <PaymentMethodItem icon={Smartphone} label="Pasarelas Móviles" active />
                                <PaymentMethodItem icon={Banknote} label="Transferencia Directa" />
                            </div>
                        </section>

                        {/* Categories Cinematic */}
                        <section className="lg:col-span-7 space-y-3">
                            <div className="flex items-center justify-between px-4">
                                <div className="flex items-center gap-3">
                                    <Layout size={18} className="text-blue-600" />
                                    <h2 className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">Fondos y Destinos</h2>
                                </div>
                                <button className="font-semibold text-blue-600 uppercase tracking-wide flex items-center gap-2 hover:scale-105 transition-transform"><Plus size={16} /> Crear Fondo</button>
                            </div>
                            
                            <div className="grid grid-cols-1 gap-4">
                                <AnimatePresence>
                                    {loading ? (
                                        [1,2,3].map(i => <Skeleton key={i} className="h-24 w-full rounded-lg" />)
                                    ) : categories.length > 0 ? categories.map((cat, i) => (
                                        <motion.div 
                                            key={cat.id}
                                            initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.05 }}
                                            className="config-aura group p-3 bg-white dark:bg-white/5 rounded-lg border border-slate-100 dark:border-white/5 flex items-center justify-between shadow-sm hover:shadow-2xl transition-all duration-500"
                                            style={{ '--aura-color': 'rgba(59, 130, 246, 0.1)' } as any}
                                        >
                                            <div className="flex items-center gap-3">
                                                <div className={clsx("size-4 rounded-full shadow-[0_0_12px_currentColor] transition-transform group-hover:scale-150 duration-500", 
                                                    cat.color === 'emerald' ? 'text-emerald-500 bg-emerald-500' :
                                                    cat.color === 'amber' ? 'text-amber-500 bg-amber-500' :
                                                    cat.color === 'rose' ? 'text-rose-500 bg-rose-500' : 'text-blue-500 bg-blue-500'
                                                )} />
                                                <div>
                                                    <p className="text-sm font-semibold text-slate-900 dark:text-white uppercase tracking-tight leading-none mb-1">{cat.name}</p>
                                                    <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wide">{cat.description || 'Fondo para actividades ministeriales'}</p>
                                                </div>
                                            </div>
                                            <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                                <button className="p-3 bg-slate-50 dark:bg-white/10 rounded-md text-slate-400 hover:text-blue-600 transition-all shadow-sm"><Edit3 size={16} /></button>
                                            </div>
                                        </motion.div>
                                    )) : (
                                        <div className="py-1.5 text-center bg-slate-50 dark:bg-white/5 rounded-lg border-2 border-dashed border-slate-200 dark:border-white/10">
                                            <p className="font-semibold text-slate-400 uppercase tracking-wide">Sin categorías configuradas</p>
                                        </div>
                                    )}
                                </AnimatePresence>
                            </div>
                        </section>
                    </div>

                    {/* Certs Automation Cinematic */}
                    <motion.section 
                        initial={{ opacity: 0, y: 30 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.3 }}
                        className="p-4 lg:p-4 bg-slate-50 dark:bg-white/5 rounded-lg border border-slate-100 dark:border-white/5 space-y-3 relative overflow-hidden group shadow-inner"
                    >
                        <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:scale-110 group-hover:rotate-6 transition-all duration-1000"><FileText size={200} /></div>
                        
                        <div className="flex flex-col lg:flex-row items-center justify-between gap-3 relative z-10">
                            <div className="space-y-6 text-center lg:text-left">
                                <div className="inline-flex items-center gap-3 px-4 py-1.5 bg-white dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-full text-[10px] font-semibold uppercase tracking-wide text-slate-500 shadow-sm">
                                    <Zap size={14} className="text-amber-500" fill="currentColor" /> Automatización de Flujo
                                </div>
                                <h3 className="text-xl lg:text-lg font-black text-slate-900 dark:text-white uppercase tracking-tighter leading-none">Certificación de <br/> <span className="text-blue-600 italic">Generosidad.</span></h3>
                                <p className="text-lg text-slate-500 dark:text-slate-400 font-medium max-w-md leading-relaxed">
                                    Emite automáticamente reportes de donación en PDF con firma digital institucional tras cada validación de tesorería.
                                </p>
                            </div>
                            <div className="flex flex-col sm:flex-row gap-4 shrink-0 w-full lg:w-auto">
                                <button className="flex-1 px-4 py-2 bg-white dark:bg-white/10 border border-slate-200 dark:border-white/10 text-slate-900 dark:text-white rounded-lg font-black text-[11px] uppercase tracking-wide shadow-2xl hover:bg-slate-50 transition-all active:scale-95 flex items-center justify-center gap-3"><Palette size={18} /> Estilo Documental</button>
                                <button className="flex-1 px-4 py-2 bg-slate-900 dark:bg-blue-600 text-white rounded-lg font-black text-[11px] uppercase tracking-wide shadow-2xl hover:translate-y-[-4px] transition-all active:scale-95 flex items-center justify-center gap-3 shadow-blue-500/20"><Mail size={18} /> Validar Email</button>
                            </div>
                        </div>
                    </motion.section>
                    </>
                    )}
                </div>
            </main>
        </div>
    );
}

function PaymentMethodItem({ icon: Icon, label, active }: any) {
    return (
        <div className="flex items-center justify-between p-4 group hover:bg-white dark:hover:bg-white/5 transition-all duration-500 cursor-pointer">
            <div className="flex items-center gap-3">
                <div className={clsx(
                    "size-7 rounded-lg flex items-center justify-center transition-all shadow-inner",
                    active ? "bg-blue-600 text-white shadow-[0_0_20px_rgba(37,99,235,0.3)]" : "bg-white dark:bg-white/5 text-slate-300 dark:text-slate-600 border border-slate-100 dark:border-white/10"
                )}>
                    <Icon size={28} strokeWidth={1.5} />
                </div>
                <div>
                    <p className="text-sm font-semibold text-slate-900 dark:text-white uppercase tracking-tight leading-none mb-1">{label}</p>
                    <p className={clsx("text-[10px] font-bold uppercase tracking-wide", active ? "text-emerald-500" : "text-slate-400")}>{active ? 'Servicio Activo' : 'Offline'}</p>
                </div>
            </div>
            <div className={clsx(
                "size-2.5 rounded-full transition-all duration-500",
                active ? "bg-emerald-500 shadow-[0_0_12px_#10b981]" : "bg-slate-200 dark:bg-white/10"
            )} />
        </div>
    );
}


