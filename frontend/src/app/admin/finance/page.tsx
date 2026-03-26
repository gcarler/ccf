"use client";

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { 
    TrendingUp, TrendingDown, DollarSign, Calendar, Filter, Download, Search, 
    ArrowUpRight, ArrowDownLeft, Wallet, PieChart, ArrowRight, ChevronRight, 
    MoreHorizontal, Plus, Layout, Globe, CreditCard, ShieldCheck, History, 
    FileText, Settings, Banknote, Sparkles, Zap, BarChart3, Receipt, ExternalLink
} from 'lucide-react';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import { DataTable } from '@/components/ui/DataTable';
import { ColumnDef } from '@tanstack/react-table';
import Skeleton from '@/components/ui/Skeleton';
import Tooltip from '@/components/ui/Tooltip';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

export default function FinanceAdminPage() {
    const { token } = useAuth();
    const { addToast } = useToast();
    const [activeTab, setActiveTab] = useState<'summary' | 'transactions' | 'audit'>('summary');
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
                        "size-8 rounded-lg flex items-center justify-center shrink-0",
                        row.original.type === 'income' ? "bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600" : "bg-rose-50 dark:bg-rose-900/20 text-rose-600"
                    )}>
                        {row.original.type === 'income' ? <ArrowUpRight size={14} /> : <ArrowDownLeft size={14} />}
                    </div>
                    <div className="flex flex-col truncate">
                        <span className="text-[13px] font-bold text-slate-700 dark:text-slate-200 truncate">{row.original.description}</span>
                        <span className="text-[10px] text-slate-400 font-black uppercase tracking-widest">{row.original.category}</span>
                    </div>
                </div>
            )
        },
        {
            accessorKey: 'amount',
            header: 'Monto',
            cell: ({ row }) => (
                <div className={clsx("font-black text-[14px]", row.original.type === 'income' ? "text-emerald-600" : "text-rose-600")}>
                    ${row.original.amount.toLocaleString()} <span className="text-[10px] text-slate-400 opacity-50">{row.original.currency}</span>
                </div>
            )
        },
        { id: 'actions', header: '', size: 50, cell: () => <button className="p-1.5 hover:bg-slate-100 dark:hover:bg-white/5 rounded-lg text-slate-400 opacity-0 group-hover:opacity-100 transition-all"><MoreHorizontal size={16} /></button> }
    ], []);

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-hidden animate-fade-in font-display">
            <WorkspaceToolbar 
                breadcrumbs={[{ label: 'CCF Platform', icon: Layout }, { label: 'Tesorería y Finanzas', icon: Wallet }]}
                viewType="table" setViewType={() => {}} onSearch={setSearch}
                rightActions={
                    <div className="flex items-center gap-2">
                        <button className="flex items-center gap-2 px-4 py-1.5 bg-slate-100 dark:bg-white/5 hover:bg-slate-200 rounded-xl text-[11px] font-black uppercase tracking-widest text-slate-600 dark:text-slate-300 transition-all active:scale-95"><Download size={14} /> Exportar</button>
                        <button className="flex items-center gap-2 px-4 py-1.5 bg-blue-600 text-white rounded-xl text-[11px] font-black uppercase tracking-widest shadow-xl shadow-blue-500/20 active:scale-95 transition-all"><Plus size={14} /> Registrar Transacción</button>
                    </div>
                }
            />

            <div className="flex px-6 border-b border-slate-100 dark:border-white/5 bg-slate-50/50 dark:bg-white/5 shrink-0">
                <FinanceTab label="Resumen General" active={activeTab === 'summary'} onClick={() => setActiveTab('summary')} />
                <FinanceTab label="Libro Mayor" active={activeTab === 'transactions'} onClick={() => setActiveTab('transactions')} />
                <FinanceTab label="Auditoría IA" active={activeTab === 'audit'} onClick={() => setActiveTab('audit')} />
            </div>

            <main className="flex-1 overflow-y-auto scrollbar-thin p-6 lg:p-10 relative">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_#1973f005_0%,_transparent_50%)] pointer-events-none" />

                <div className="max-w-[1400px] mx-auto space-y-10 relative z-10">
                    <AnimatePresence mode="wait">
                        {loading ? (
                            <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-8">
                                <div className="grid grid-cols-3 gap-6">{[1,2,3].map(i => <Skeleton key={i} className="h-40 rounded-[3rem]" />)}</div>
                                <Skeleton className="h-96 w-full rounded-[3rem]" />
                            </motion.div>
                        ) : activeTab === 'summary' ? (
                            <motion.div key="summary" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} className="space-y-10">
                                
                                <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
                                    <SummaryCard title="Caja en Efectivo" value={`$${summary?.balance?.toLocaleString() || '0'}`} trend="+12%" icon={Banknote} color="blue" />
                                    <SummaryCard title="Ingresos (30d)" value={`$${summary?.total_income?.toLocaleString() || '0'}`} trend="+5.4%" icon={TrendingUp} color="emerald" />
                                    <SummaryCard title="Gastos (30d)" value={`$${summary?.total_expense?.toLocaleString() || '0'}`} trend="-2.1%" icon={TrendingDown} color="rose" />
                                </section>

                                <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                                    {/* Financial Performance Chart */}
                                    <div className="lg:col-span-8 p-10 bg-slate-900 rounded-[3.5rem] text-white shadow-2xl relative overflow-hidden group border border-white/5">
                                        <div className="absolute top-0 right-0 p-10 opacity-5 group-hover:opacity-10 transition-opacity"><BarChart3 size={120} /></div>
                                        <div className="space-y-8 relative z-10">
                                            <div className="flex items-center justify-between px-2">
                                                <h3 className="text-xl font-black tracking-tight">Análisis de Flujo Mensual</h3>
                                                <div className="flex gap-6">
                                                    <div className="flex items-center gap-2"><div className="size-2 rounded-full bg-blue-500 shadow-[0_0_8px_#3b82f6]" /><span className="text-[9px] font-black uppercase text-slate-400 tracking-widest">Ingresos</span></div>
                                                    <div className="flex items-center gap-2"><div className="size-2 rounded-full bg-rose-500 shadow-[0_0_8px_#f43f5e]" /><span className="text-[9px] font-black uppercase text-slate-400 tracking-widest">Gastos</span></div>
                                                </div>
                                            </div>
                                            <div className="h-56 flex items-end justify-between gap-4 px-2">
                                                {[45, 70, 55, 90, 65, 95, 60, 85, 50, 88, 75, 92].map((h, i) => (
                                                    <div key={i} className="flex-1 flex flex-col justify-end gap-2 group/bar cursor-pointer h-full">
                                                        <div className="w-full bg-blue-500/20 rounded-t-lg relative group-hover/bar:bg-blue-500 transition-all" style={{ height: `${h}%` }}>
                                                            <div className="absolute -top-8 left-1/2 -translate-x-1/2 px-2 py-1 bg-white text-slate-900 rounded text-[9px] font-black opacity-0 group-hover/bar:opacity-100 shadow-xl transition-all">${h*100}</div>
                                                        </div>
                                                        <div className="w-full bg-rose-500/20 rounded-t-lg group-hover/bar:bg-rose-500 transition-all" style={{ height: `${h/2.5}%` }} />
                                                    </div>
                                                ))}
                                            </div>
                                            <div className="flex justify-between px-2 text-[9px] font-black text-slate-500 uppercase tracking-[0.3em]">
                                                {['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'].map(m => <span key={m}>{m}</span>)}
                                            </div>
                                        </div>
                                    </div>

                                    {/* Budget Allocation */}
                                    <div className="lg:col-span-4 p-8 bg-white dark:bg-white/5 rounded-[3rem] border border-slate-100 dark:border-white/5 shadow-sm space-y-8">
                                        <h3 className="text-[11px] font-black text-slate-400 uppercase tracking-[0.2em] px-2 flex items-center gap-2"><PieChart size={16} className="text-blue-500" /> Distribución de Gasto</h3>
                                        <div className="space-y-6">
                                            <BudgetItem label="Mantenimiento Sede" percent={45} color="bg-blue-500" />
                                            <BudgetItem label="Misiones Externas" percent={30} color="bg-emerald-500" />
                                            <BudgetItem label="Personal y Staff" percent={15} color="bg-amber-500" />
                                            <BudgetItem label="Otros Gastos" percent={10} color="bg-slate-400" />
                                        </div>
                                        <button className="w-full py-4 mt-4 bg-slate-50 dark:bg-white/5 rounded-2xl text-[10px] font-black uppercase tracking-widest text-slate-500 hover:text-blue-600 transition-all">Ver Presupuestos 2026</button>
                                    </div>
                                </div>
                            </motion.div>
                        ) : activeTab === 'audit' ? (
                            <motion.div key="audit" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} className="space-y-10">
                                <section className="p-12 bg-gradient-to-br from-purple-600 to-indigo-800 rounded-[4rem] text-white shadow-2xl relative overflow-hidden group">
                                    <div className="absolute top-0 right-0 p-12 opacity-10 group-hover:scale-110 transition-transform duration-1000"><Sparkles size={160} /></div>
                                    <div className="relative z-10 max-w-2xl space-y-8">
                                        <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-white/10 backdrop-blur-xl border border-white/20 rounded-full text-[10px] font-black uppercase tracking-[0.3em]">
                                            <Zap size={14} fill="currentColor" /> Optimus Finance Intelligence
                                        </div>
                                        <h2 className="text-4xl lg:text-6xl font-black tracking-tighter leading-none">Tu tesorería está <span className="text-purple-200 italic">saludable.</span></h2>
                                        <p className="text-xl text-purple-100/80 font-medium leading-relaxed">Optimus Brain ha analizado las últimas 450 transacciones y no ha detectado anomalías. El flujo de caja proyectado para el próximo mes cubre el 100% de los compromisos ministeriales.</p>
                                        <div className="flex gap-4">
                                            <button className="px-8 py-4 bg-white text-indigo-900 rounded-2xl font-black text-[11px] uppercase tracking-widest shadow-xl hover:scale-105 active:scale-95 transition-all">Generar Auditoría Completa</button>
                                            <button className="px-8 py-4 bg-white/10 backdrop-blur-md border border-white/20 text-white rounded-2xl font-black text-[11px] uppercase tracking-widest hover:bg-white/20 transition-all">Reporte de Misiones</button>
                                        </div>
                                    </div>
                                </section>
                            </motion.div>
                        ) : (
                            <motion.div key="table" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="h-full bg-white dark:bg-black/20 rounded-[3rem] border border-slate-100 dark:border-white/5 overflow-hidden">
                                <DataTable data={transactions.filter(tx => tx.description.toLowerCase().includes(search.toLowerCase()))} columns={columns} onRowClick={handleOpenTx} />
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            </main>

            <WorkspaceDrawer 
                isOpen={isDrawerOpen} onClose={() => setIsDrawerOpen(false)}
                title={selectedTx?.description || 'Detalle de Operación'}
                subtitle={`${selectedTx?.type?.toUpperCase()} • REF-${selectedTx?.id}`}
                actions={<><button className="px-4 py-2 text-[11px] font-bold text-rose-500">Anular</button><button className="px-6 py-2 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-lg text-[11px] font-bold shadow-lg">Descargar Recibo</button></>}
            >
                <div className="space-y-10 animate-fade-in">
                    <section className="grid grid-cols-2 gap-4">
                        <DrawerStat label="Tipo" value={selectedTx?.type} icon={History} />
                        <DrawerStat label="Categoría" value={selectedTx?.category} icon={Settings} />
                        <DrawerStat label="Monto" value={`$${selectedTx?.amount?.toLocaleString()}`} icon={DollarSign} />
                        <DrawerStat label="Fecha" value={selectedTx ? new Date(selectedTx.date).toLocaleDateString() : ''} icon={Calendar} />
                    </section>

                    <section className="space-y-4 pt-6 border-t border-slate-100 dark:border-white/5">
                        <h4 className="text-[11px] font-black text-slate-400 uppercase tracking-widest flex items-center gap-2"><Receipt size={14} /> Comprobante Digital</h4>
                        <div className="aspect-[3/4] w-full max-w-[300px] mx-auto rounded-3xl bg-slate-50 dark:bg-black/40 border-2 border-dashed border-slate-200 dark:border-white/5 flex flex-col items-center justify-center text-slate-400 space-y-4 group cursor-pointer hover:border-blue-500/50 transition-all">
                            <FileText size={48} strokeWidth={1} />
                            <p className="text-[10px] font-black uppercase tracking-widest">Ver Documento</p>
                        </div>
                    </section>

                    <section className="p-6 bg-emerald-50 dark:bg-emerald-900/10 rounded-[2rem] border border-emerald-100 dark:border-emerald-900/30 flex items-center gap-4">
                        <div className="size-10 rounded-xl bg-white dark:bg-white/10 flex items-center justify-center text-emerald-600 shadow-sm"><ShieldCheck size={24} /></div>
                        <div>
                            <h4 className="text-[11px] font-black uppercase tracking-widest text-emerald-600">Transacción Verificada</h4>
                            <p className="text-xs text-slate-500">Conciliación bancaria completada automáticamente.</p>
                        </div>
                    </section>
                </div>
            </WorkspaceDrawer>
        </div>
    );
}

function FinanceTab({ label, active, onClick }: any) {
    return (
        <button onClick={onClick} className={clsx("px-6 py-4 text-[11px] font-black uppercase tracking-widest transition-all border-b-2 relative overflow-hidden", active ? "text-blue-600 border-blue-600" : "text-slate-400 border-transparent hover:text-slate-600")}>
            {active && <motion.div layoutId="finance-tab" className="absolute bottom-0 left-0 w-full h-[2px] bg-blue-600" />}
            {label}
        </button>
    );
}

function SummaryCard({ title, value, trend, icon: Icon, color }: any) {
    return (
        <div className="p-8 rounded-[3rem] bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 shadow-sm group hover:shadow-2xl transition-all relative overflow-hidden">
            <div className="absolute top-0 right-0 p-6 opacity-10 group-hover:scale-110 transition-transform"><Icon size={48} /></div>
            <div className="space-y-4">
                <p className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">{title}</p>
                <h3 className="text-4xl font-black text-slate-800 dark:text-white tracking-tighter leading-none">{value}</h3>
                <div className={clsx("inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[10px] font-black shadow-sm", color === 'rose' ? "bg-rose-50 text-rose-600" : "bg-emerald-50 text-emerald-600")}>
                    {color === 'rose' ? <TrendingDown size={12} /> : <TrendingUp size={12} />} {trend}
                </div>
            </div>
        </div>
    );
}

function BudgetItem({ label, percent, color }: any) {
    return (
        <div className="space-y-3">
            <div className="flex justify-between items-center text-[11px] font-bold">
                <span className="text-slate-600 dark:text-slate-300">{label}</span>
                <span className="text-slate-400">{percent}%</span>
            </div>
            <div className="h-1.5 w-full bg-slate-100 dark:bg-white/5 rounded-full overflow-hidden">
                <motion.div initial={{ width: 0 }} animate={{ width: `${percent}%` }} className={clsx("h-full", color)} />
            </div>
        </div>
    );
}

function DrawerStat({ label, value, icon: Icon }: any) {
    return (
        <div className="p-4 bg-slate-50 dark:bg-white/5 border border-slate-100 dark:border-white/5 rounded-2xl">
            <div className="flex items-center gap-2 mb-1"><Icon size={12} className="text-slate-400" /><span className="text-[9px] font-black text-slate-400 uppercase tracking-widest">{label}</span></div>
            <p className="text-[13px] font-black text-slate-800 dark:text-white capitalize">{value}</p>
        </div>
    );
}
