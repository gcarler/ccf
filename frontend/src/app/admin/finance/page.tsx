"use client";

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { 
    TrendingUp, TrendingDown, DollarSign, Calendar, Download,
    ArrowUpRight, ArrowDownLeft, Wallet, PieChart,
    MoreHorizontal, Plus, Layout, ShieldCheck, History,
    FileText, Settings, Banknote, Sparkles, Zap, BarChart3, Receipt
} from 'lucide-react';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import { DataTable } from '@/components/ui/DataTable';
import UniversalCalendarView from '@/components/ui/UniversalCalendarView';
import UniversalGanttView from '@/components/ui/UniversalGanttView';
import UniversalWikiView from '@/components/ui/UniversalWikiView';
import { ColumnDef } from '@tanstack/react-table';
import Skeleton from '@/components/ui/Skeleton';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import type { ViewType } from '@/components/ViewSwitcher';

const FINANCE_VIEWS: ViewType[] = ['grid', 'table', 'list', 'board', 'kanban', 'calendar', 'gantt', 'wiki'];

export default function FinanceAdminPage() {
    const { token } = useAuth();
    const [activeTab, setActiveTab] = useState<'summary' | 'transactions' | 'audit'>('summary');
    const [viewType, setViewType] = useState<ViewType>('grid');
    const [transactions, setTransactions] = useState<any[]>([]);
    const [summary, setSummary] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [selectedTx, setSelectedTx] = useState<any>(null);
    const [isDrawerOpen, setIsDrawerOpen] = useState(false);

    const fetchData = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const [txData, summaryData] = await Promise.all([
                apiFetch<any[]>('/finance/transactions', { token, cache: 'no-store' }),
                apiFetch<any>('/finance/summary', { token, cache: 'no-store' })
            ]);
            setTransactions(Array.isArray(txData) ? txData : []);
            setSummary(summaryData);
        } catch (e) { console.error(e); }
        finally { setLoading(false); }
    }, [token]);

    useEffect(() => { fetchData(); }, [fetchData]);

    const handleOpenTx = (tx: any) => {
        setSelectedTx(tx);
        setIsDrawerOpen(true);
    };

    const columns = useMemo<ColumnDef<any>[]>(() => [
        { accessorKey: 'id', header: '#', size: 60, cell: info => <span className="text-[11px] font-bold text-slate-400">#{info.getValue() as number}</span> },
        {
            accessorKey: 'description',
            header: 'Concepto / Descripción',
            size: 350,
            cell: ({ row }) => (
                <div className="flex items-center gap-3 truncate">
                    <div className={clsx(
                        "size-8 rounded-lg flex items-center justify-center shrink-0 shadow-sm",
                        row.original.type === 'income' ? "bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600" : "bg-rose-50 dark:bg-rose-900/20 text-rose-600"
                    )}>
                        {row.original.type === 'income' ? <ArrowUpRight size={14} /> : <ArrowDownLeft size={14} />}
                    </div>
                    <div className="flex flex-col truncate">
                        <span className="text-[13px] font-bold text-slate-700 dark:text-slate-200 truncate">{row.original.description}</span>
                        <span className="text-[10px] text-slate-400 font-black uppercase tracking-widest leading-none mt-0.5">{row.original.category}</span>
                    </div>
                </div>
            )
        },
        {
            accessorKey: 'amount',
            header: 'Monto',
            cell: ({ row }) => (
                <div className={clsx("font-black text-[14px] flex items-baseline gap-1", row.original.type === 'income' ? "text-emerald-600" : "text-rose-600")}>
                    <span>${row.original.amount.toLocaleString()}</span>
                    <span className="text-[9px] text-slate-400 font-black opacity-50 uppercase">{row.original.currency}</span>
                </div>
            )
        },
        { id: 'actions', header: '', size: 50, cell: () => <button className="p-1.5 hover:bg-slate-100 dark:hover:bg-white/5 rounded-lg text-slate-400 opacity-0 group-hover:opacity-100 transition-all"><MoreHorizontal size={16} /></button> }
    ], []);
    const filteredTransactions = useMemo(() => transactions.filter(tx =>
        String(tx.description || '').toLowerCase().includes(search.toLowerCase()) ||
        String(tx.category || '').toLowerCase().includes(search.toLowerCase())
    ), [transactions, search]);
    const groupedTransactions = useMemo(() => ['income', 'expense'].map((type) => ({
        type,
        items: filteredTransactions.filter((tx) => (tx.type || 'expense') === type),
    })), [filteredTransactions]);
    const calendarEvents = useMemo(() => filteredTransactions.map((tx) => ({
        id: tx.id,
        title: tx.description,
        date: (tx.date || tx.created_at || new Date().toISOString()).slice(0, 10),
        color: tx.type === 'income' ? 'emerald' as const : 'rose' as const,
        location: tx.category,
    })), [filteredTransactions]);
    const ganttItems = useMemo(() => filteredTransactions.map((tx) => ({
        id: tx.id,
        title: tx.description,
        subtitle: tx.category || tx.type,
        start_date: (tx.date || tx.created_at || new Date().toISOString()).slice(0, 10),
        end_date: (tx.updated_at || tx.date || tx.created_at || new Date().toISOString()).slice(0, 10),
        color: tx.type === 'income' ? 'emerald' as const : 'rose' as const,
        progress: 100,
    })), [filteredTransactions]);

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-hidden animate-fade-in font-display">
            <style jsx global>{`
                .aura-effect {
                    position: relative;
                }
                .aura-effect::after {
                    content: '';
                    position: absolute;
                    inset: -2px;
                    background: linear-gradient(45deg, var(--aura-color, transparent), transparent 40%);
                    z-index: -1;
                    border-radius: inherit;
                    opacity: 0;
                    transition: opacity 0.5s ease;
                }
                .aura-effect:hover::after {
                    opacity: 1;
                }
                .shimmer-metal {
                    position: relative;
                    overflow: hidden;
                }
                .shimmer-metal::after {
                    content: '';
                    position: absolute;
                    top: 0;
                    left: -100%;
                    width: 50%;
                    height: 100%;
                    background: linear-gradient(
                        90deg,
                        transparent,
                        rgba(255, 255, 255, 0.2),
                        transparent
                    );
                    animation: metal-shimmer 3s infinite;
                }
                @keyframes metal-shimmer {
                    0% { left: -100%; }
                    100% { left: 200%; }
                }
                .stacked-glass {
                    background: rgba(255, 255, 255, 0.7);
                    backdrop-filter: blur(20px) saturate(180%);
                    -webkit-backdrop-filter: blur(20px) saturate(180%);
                    border: 1px solid rgba(255, 255, 255, 0.3);
                }
                .dark .stacked-glass {
                    background: rgba(30, 31, 33, 0.8);
                    border: 1px solid rgba(255, 255, 255, 0.05);
                }
            `}</style>

            <WorkspaceToolbar 
                breadcrumbs={[{ label: 'CCF Platform', icon: Layout }, { label: 'Tesorería y Finanzas', icon: Wallet }]}
                viewType={viewType} setViewType={setViewType} availableViews={FINANCE_VIEWS} onSearch={setSearch}
                rightActions={
                    <div className="flex items-center gap-2">
                        <button className="flex items-center gap-2 px-4 py-1.5 bg-slate-100 dark:bg-white/5 hover:bg-slate-200 rounded-xl text-[11px] font-black uppercase tracking-widest text-slate-600 dark:text-slate-300 transition-all active:scale-95"><Download size={14} /> Exportar</button>
                        <button className="flex items-center gap-2 px-4 py-1.5 bg-blue-600 text-white rounded-xl text-[11px] font-black uppercase tracking-widest shadow-xl shadow-blue-500/20 active:scale-95 transition-all"><Plus size={14} /> Registrar Transacción</button>
                    </div>
                }
            />

            <div className="flex px-6 border-b border-slate-100 dark:border-white/5 bg-slate-50/50 dark:bg-white/5 shrink-0 overflow-x-auto no-scrollbar">
                <FinanceTab label="Resumen General" active={activeTab === 'summary'} onClick={() => setActiveTab('summary')} />
                <FinanceTab label="Libro Mayor" active={activeTab === 'transactions'} onClick={() => setActiveTab('transactions')} />
                <FinanceTab label="Auditoría IA" active={activeTab === 'audit'} onClick={() => setActiveTab('audit')} />
            </div>

            <main className="flex-1 overflow-y-auto scrollbar-thin p-6 lg:p-10 relative">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_#1973f008_0%,_transparent_50%)] pointer-events-none" />

                <div className="max-w-[1400px] mx-auto space-y-10 relative z-10">
                    <AnimatePresence mode="wait">
                        {loading ? (
                            <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-8">
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">{[1,2,3].map(i => <Skeleton key={i} className="h-44 rounded-[3rem]" />)}</div>
                                <Skeleton className="h-96 w-full rounded-[3rem]" />
                            </motion.div>
                        ) : viewType === 'list' ? (
                            <motion.div key="list" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-2">
                                {filteredTransactions.map((tx) => (
                                    <button key={tx.id} onClick={() => handleOpenTx(tx)} className="flex w-full items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-4 text-left dark:border-white/10 dark:bg-white/5">
                                        <div>
                                            <p className="text-sm font-black text-slate-900 dark:text-white">{tx.description}</p>
                                            <p className="text-xs font-semibold text-slate-400">{tx.category}</p>
                                        </div>
                                        <span className={clsx("font-black", tx.type === 'income' ? "text-emerald-600" : "text-rose-600")}>${Number(tx.amount || 0).toLocaleString()}</span>
                                    </button>
                                ))}
                            </motion.div>
                        ) : viewType === 'board' || viewType === 'kanban' ? (
                            <motion.div key="board" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-4 overflow-x-auto">
                                {groupedTransactions.map((column) => (
                                    <section key={column.type} className="w-96 shrink-0 rounded-2xl border border-slate-200 bg-slate-50 p-3 dark:border-white/10 dark:bg-white/[0.03]">
                                        <div className="mb-3 flex items-center justify-between px-1">
                                            <p className="text-[10px] font-black uppercase tracking-widest text-slate-500">{column.type}</p>
                                            <span className="text-[10px] font-black text-slate-400">{column.items.length}</span>
                                        </div>
                                        <div className="space-y-2">
                                            {column.items.map((tx) => (
                                                <button key={tx.id} onClick={() => handleOpenTx(tx)} className="w-full rounded-xl border border-slate-200 bg-white p-3 text-left dark:border-white/10 dark:bg-white/5">
                                                    <p className="text-xs font-black text-slate-900 dark:text-white">{tx.description}</p>
                                                    <p className="mt-1 text-[10px] font-semibold text-slate-400">${Number(tx.amount || 0).toLocaleString()} · {tx.category}</p>
                                                </button>
                                            ))}
                                        </div>
                                    </section>
                                ))}
                            </motion.div>
                        ) : viewType === 'calendar' ? (
                            <motion.div key="calendar" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="h-[720px]">
                                <UniversalCalendarView events={calendarEvents} title="Calendario financiero" onEventClick={(event) => {
                                    const tx = filteredTransactions.find((item) => item.id === event.id);
                                    if (tx) handleOpenTx(tx);
                                }} />
                            </motion.div>
                        ) : viewType === 'gantt' ? (
                            <motion.div key="gantt" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="h-[720px]">
                                <UniversalGanttView items={ganttItems} moduleName="Finanzas" onItemClick={(item) => {
                                    const tx = filteredTransactions.find((entry) => entry.id === item.id);
                                    if (tx) handleOpenTx(tx);
                                }} />
                            </motion.div>
                        ) : viewType === 'wiki' ? (
                            <motion.div key="wiki" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                                <UniversalWikiView moduleName="Finanzas" storageKey="wiki_admin_finance" />
                            </motion.div>
                        ) : viewType === 'table' ? (
                            <motion.div
                                key="table-view"
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                className="h-full bg-white dark:bg-black/20 rounded-[3.5rem] border border-slate-100 dark:border-white/5 overflow-hidden shadow-sm"
                            >
                                <DataTable data={filteredTransactions} columns={columns} onRowClick={handleOpenTx} />
                            </motion.div>
                        ) : activeTab === 'summary' ? (
                            <motion.div 
                                key="summary" 
                                initial={{ opacity: 0, y: 20 }} 
                                animate={{ opacity: 1, y: 0 }} 
                                exit={{ opacity: 0, y: -20 }} 
                                transition={{ duration: 0.5, ease: [0.23, 1, 0.32, 1] }}
                                className="space-y-10"
                            >
                                <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
                                    <SummaryCard title="Caja en Efectivo" value={`$${summary?.balance?.toLocaleString() || '0'}`} trend="+12%" icon={Banknote} color="blue" auraColor="rgba(59, 130, 246, 0.2)" />
                                    <SummaryCard title="Ingresos (30d)" value={`$${summary?.total_income?.toLocaleString() || '0'}`} trend="+5.4%" icon={TrendingUp} color="emerald" auraColor="rgba(16, 185, 129, 0.2)" />
                                    <SummaryCard title="Gastos (30d)" value={`$${summary?.total_expense?.toLocaleString() || '0'}`} trend="-2.1%" icon={TrendingDown} color="rose" auraColor="rgba(244, 63, 94, 0.2)" />
                                </section>

                                <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                                    {/* Financial Performance Chart */}
                                    <div className="lg:col-span-8 p-10 bg-slate-900 rounded-[3.5rem] text-white shadow-2xl relative overflow-hidden group border border-white/5 animate-in fade-in slide-in-from-bottom-4 duration-700">
                                        <div className="absolute top-0 right-0 p-10 opacity-5 group-hover:opacity-10 group-hover:rotate-12 transition-all duration-700"><BarChart3 size={140} /></div>
                                        <div className="space-y-10 relative z-10">
                                            <div className="flex items-center justify-between px-2">
                                                <div className="space-y-1">
                                                    <h3 className="text-2xl font-black tracking-tight uppercase">Análisis de Flujo Mensual</h3>
                                                    <p className="text-xs text-slate-400 font-bold uppercase tracking-widest">Periodo Fiscal 2026</p>
                                                </div>
                                                <div className="flex gap-6">
                                                    <div className="flex items-center gap-2"><div className="size-2 rounded-full bg-blue-500 shadow-[0_0_12px_#3b82f6]" /><span className="text-[9px] font-black uppercase text-slate-400 tracking-widest">Ingresos</span></div>
                                                    <div className="flex items-center gap-2"><div className="size-2 rounded-full bg-rose-500 shadow-[0_0_12px_#f43f5e]" /><span className="text-[9px] font-black uppercase text-slate-400 tracking-widest">Gastos</span></div>
                                                </div>
                                            </div>
                                            <div className="h-64 flex items-end justify-between gap-4 px-2">
                                                {[45, 70, 55, 90, 65, 95, 60, 85, 50, 88, 75, 92].map((h, i) => (
                                                    <motion.div 
                                                        key={i} 
                                                        initial={{ height: 0, opacity: 0 }}
                                                        animate={{ height: '100%', opacity: 1 }}
                                                        transition={{ delay: i * 0.05 + 0.3 }}
                                                        className="flex-1 flex flex-col justify-end gap-2 group/bar cursor-pointer h-full"
                                                    >
                                                        <div className="w-full bg-blue-500/20 rounded-t-xl relative group-hover/bar:bg-blue-500 group-hover/bar:shadow-[0_0_20px_rgba(59,130,246,0.4)] transition-all duration-300" style={{ height: `${h}%` }}>
                                                            <div className="absolute -top-10 left-1/2 -translate-x-1/2 px-3 py-1.5 bg-white text-slate-900 rounded-xl text-[10px] font-black opacity-0 group-hover/bar:opacity-100 shadow-2xl transition-all scale-90 group-hover/bar:scale-100">${(h*100).toLocaleString()}</div>
                                                        </div>
                                                        <div className="w-full bg-rose-500/20 rounded-t-xl group-hover/bar:bg-rose-500 transition-all duration-300" style={{ height: `${h/2.5}%` }} />
                                                    </motion.div>
                                                ))}
                                            </div>
                                            <div className="flex justify-between px-2 text-[10px] font-black text-slate-500 uppercase tracking-[0.3em]">
                                                {['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'].map(m => <span key={m}>{m}</span>)}
                                            </div>
                                        </div>
                                    </div>

                                    {/* Budget Allocation */}
                                    <div className="lg:col-span-4 p-8 bg-white dark:bg-white/5 rounded-[3.5rem] border border-slate-100 dark:border-white/5 shadow-sm space-y-8 animate-in fade-in slide-in-from-right-4 duration-700">
                                        <h3 className="text-[11px] font-black text-slate-400 uppercase tracking-[0.2em] px-2 flex items-center gap-2"><PieChart size={16} className="text-blue-500" /> Distribución de Gasto</h3>
                                        <div className="space-y-8 px-2">
                                            <BudgetItem label="Mantenimiento Sede" percent={45} color="bg-blue-500" />
                                            <BudgetItem label="Misiones Externas" percent={30} color="bg-emerald-500" />
                                            <BudgetItem label="Personal y Staff" percent={15} color="bg-amber-500" />
                                            <BudgetItem label="Otros Gastos" percent={10} color="bg-slate-400" />
                                        </div>
                                        <button className="w-full py-5 mt-4 bg-slate-50 dark:bg-white/5 rounded-3xl text-[10px] font-black uppercase tracking-widest text-slate-500 hover:text-blue-600 hover:bg-blue-50 transition-all transform active:scale-95 shadow-sm">Ver Presupuestos 2026</button>
                                    </div>
                                </div>
                            </motion.div>
                        ) : activeTab === 'audit' ? (
                            <motion.div 
                                key="audit" 
                                initial={{ opacity: 0, scale: 0.95 }} 
                                animate={{ opacity: 1, scale: 1 }} 
                                exit={{ opacity: 0, scale: 0.95 }}
                                className="space-y-10"
                            >
                                <section className="p-12 lg:p-20 bg-gradient-to-br from-slate-900 via-indigo-950 to-sky-900 rounded-[4rem] text-white shadow-2xl relative overflow-hidden group">
                                    <div className="absolute top-0 right-0 p-12 opacity-10 group-hover:scale-110 group-hover:rotate-12 transition-all duration-1000"><Sparkles size={240} /></div>
                                    <div className="absolute -bottom-20 -left-20 size-96 bg-blue-500/10 blur-[100px] rounded-full" />
                                    
                                    <div className="relative z-10 max-w-3xl space-y-10">
                                        <div className="inline-flex items-center gap-3 px-5 py-2 bg-white/5 backdrop-blur-2xl border border-white/10 rounded-full text-[11px] font-black uppercase tracking-[0.3em] shadow-2xl">
                                            <Zap size={16} className="text-amber-400" fill="currentColor" /> Optimus Finance Intelligence
                                        </div>
                                        <h2 className="text-5xl lg:text-7xl font-black tracking-tighter leading-none">
                                            Tu tesorería está <br/>
                                            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-emerald-400 italic">saludable y protegida.</span>
                                        </h2>
                                        <p className="text-xl text-slate-300 font-medium leading-relaxed max-w-2xl">
                                            Optimus Brain ha analizado las últimas 450 transacciones y no ha detectado anomalías. El flujo de caja proyectado para el próximo mes cubre el 100% de los compromisos ministeriales con un excedente del 12% para fondo de reserva.
                                        </p>
                                        <div className="flex flex-wrap gap-4 pt-4">
                                            <button className="px-10 py-5 bg-white text-slate-900 rounded-[2rem] font-black text-xs uppercase tracking-widest shadow-2xl shadow-white/10 hover:translate-y-[-4px] active:scale-95 transition-all">Generar Auditoría Completa</button>
                                            <button className="px-10 py-5 bg-white/10 backdrop-blur-md border border-white/10 text-white rounded-[2rem] font-black text-xs uppercase tracking-widest hover:bg-white/20 transition-all">Reporte de Misiones</button>
                                        </div>
                                    </div>
                                </section>
                            </motion.div>
                        ) : (
                            <motion.div 
                                key="table" 
                                initial={{ opacity: 0 }} 
                                animate={{ opacity: 1 }} 
                                className="h-full bg-white dark:bg-black/20 rounded-[3.5rem] border border-slate-100 dark:border-white/5 overflow-hidden shadow-sm"
                            >
                                <DataTable
                                    data={filteredTransactions}
                                    columns={columns}
                                    onRowClick={handleOpenTx}
                                />
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            </main>

            <WorkspaceDrawer 
                isOpen={isDrawerOpen} onClose={() => setIsDrawerOpen(false)}
                title={selectedTx?.description || 'Detalle de Operación'}
                subtitle={`${selectedTx?.type?.toUpperCase()} • REF-${selectedTx?.id}`}
                actions={<><button className="px-4 py-2 text-[11px] font-bold text-rose-500 hover:bg-rose-50 rounded-xl transition-all">Anular</button><button className="px-6 py-2 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-xl text-[11px] font-black uppercase tracking-widest shadow-xl">Descargar Recibo</button></>}
            >
                <div className="space-y-10 animate-in fade-in slide-in-from-right-4 duration-500">
                    <section className="grid grid-cols-2 gap-4">
                        <DrawerStat label="Tipo" value={selectedTx?.type} icon={History} />
                        <DrawerStat label="Categoría" value={selectedTx?.category} icon={Settings} />
                        <DrawerStat label="Monto" value={`$${selectedTx?.amount?.toLocaleString()}`} icon={DollarSign} />
                        <DrawerStat label="Fecha" value={selectedTx ? new Date(selectedTx.date).toLocaleDateString() : ''} icon={Calendar} />
                    </section>

                    <section className="space-y-4 pt-6 border-t border-slate-100 dark:border-white/5">
                        <h4 className="text-[11px] font-black text-slate-400 uppercase tracking-widest flex items-center gap-2"><Receipt size={14} /> Comprobante Digital</h4>
                        <div className="aspect-[3/4] w-full max-w-[320px] mx-auto rounded-[2.5rem] bg-slate-50 dark:bg-black/40 border-2 border-dashed border-slate-200 dark:border-white/5 flex flex-col items-center justify-center text-slate-400 space-y-4 group cursor-pointer hover:border-blue-500/50 hover:bg-white transition-all duration-500">
                            <div className="p-6 bg-white dark:bg-white/5 rounded-3xl shadow-sm group-hover:scale-110 group-hover:rotate-3 transition-all duration-500">
                                <FileText size={56} strokeWidth={1} className="text-slate-300 group-hover:text-blue-500" />
                            </div>
                            <p className="text-[10px] font-black uppercase tracking-widest group-hover:text-blue-600 transition-colors">Ver Documento Escaneado</p>
                        </div>
                    </section>

                    <section className="p-8 bg-emerald-50 dark:bg-emerald-900/10 rounded-[2.5rem] border border-emerald-100 dark:border-emerald-900/30 flex items-center gap-5 shadow-sm relative overflow-hidden">
                        <div className="absolute top-0 right-0 p-4 opacity-10 rotate-12"><ShieldCheck size={80} /></div>
                        <div className="size-12 rounded-2xl bg-white dark:bg-white/10 flex items-center justify-center text-emerald-600 shadow-sm relative z-10"><ShieldCheck size={28} /></div>
                        <div className="relative z-10">
                            <h4 className="text-[11px] font-black uppercase tracking-widest text-emerald-700">Transacción Verificada</h4>
                            <p className="text-xs text-emerald-600/70 font-bold">Conciliación bancaria completada automáticamente.</p>
                        </div>
                    </section>
                </div>
            </WorkspaceDrawer>
        </div>
    );
}

function FinanceTab({ label, active, onClick }: any) {
    return (
        <button onClick={onClick} className={clsx("px-8 py-5 text-[11px] font-black uppercase tracking-widest transition-all border-b-2 relative overflow-hidden shrink-0", active ? "text-blue-600 border-blue-600" : "text-slate-400 border-transparent hover:text-slate-600 hover:bg-white/50")}>
            {active && <motion.div layoutId="finance-tab" className="absolute bottom-0 left-0 w-full h-[2.5px] bg-blue-600" />}
            {label}
        </button>
    );
}

function SummaryCard({ title, value, trend, icon: Icon, color, auraColor }: any) {
    return (
        <div 
            className="aura-effect p-8 rounded-[3.5rem] bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 shadow-sm group hover:shadow-2xl transition-all duration-500 relative overflow-hidden"
            style={{ '--aura-color': auraColor } as any}
        >
            <div className="absolute top-0 right-0 p-8 opacity-5 group-hover:opacity-10 group-hover:scale-125 group-hover:rotate-12 transition-all duration-700"><Icon size={64} /></div>
            <div className="space-y-5 relative z-10">
                <p className="text-[10px] font-black text-slate-400 uppercase tracking-[0.25em]">{title}</p>
                <h3 className="text-4xl font-black text-slate-800 dark:text-white tracking-tighter leading-none">{value}</h3>
                <div className={clsx("inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full text-[10px] font-black shadow-sm border border-black/5", color === 'rose' ? "bg-rose-50 text-rose-600" : "bg-emerald-50 text-emerald-600")}>
                    {color === 'rose' ? <TrendingDown size={14} /> : <TrendingUp size={14} />} {trend}
                </div>
            </div>
        </div>
    );
}

function BudgetItem({ label, percent, color }: any) {
    return (
        <div className="space-y-3 group/item">
            <div className="flex justify-between items-center text-[11px] font-black uppercase tracking-tight">
                <span className="text-slate-500 dark:text-slate-400 group-hover/item:text-slate-800 transition-colors">{label}</span>
                <span className="text-slate-400 group-hover/item:text-blue-600 transition-colors">{percent}%</span>
            </div>
            <div className="h-2 w-full bg-slate-100 dark:bg-white/5 rounded-full overflow-hidden shadow-inner">
                <motion.div 
                    initial={{ width: 0 }} 
                    animate={{ width: `${percent}%` }} 
                    transition={{ duration: 1, ease: "easeOut" }}
                    className={clsx("h-full shimmer-metal relative", color)} 
                />
            </div>
        </div>
    );
}

function DrawerStat({ label, value, icon: Icon }: any) {
    return (
        <div className="p-5 bg-slate-50 dark:bg-white/5 border border-slate-100 dark:border-white/5 rounded-3xl transition-all hover:bg-white hover:shadow-sm">
            <div className="flex items-center gap-2 mb-1.5"><Icon size={14} className="text-slate-400" /><span className="text-[9px] font-black text-slate-400 uppercase tracking-widest">{label}</span></div>
            <p className="text-[15px] font-black text-slate-800 dark:text-white capitalize tracking-tight">{value}</p>
        </div>
    );
}

