"use client";

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { MessageSquare, Plus, Clock, CheckCircle, AlertCircle, Circle, ChevronRight, Search, Filter, Tag } from 'lucide-react';
import clsx from 'clsx';

const TICKETS = [
    { id: 'CCF-001', title: 'No puedo acceder a mi cuenta de Academia', category: 'Acceso', status: 'open', priority: 'high', created: '2026-04-10', updated: 'Hace 2h' },
    { id: 'CCF-002', title: 'Error al cargar el pipeline de consolidación', category: 'Bug', status: 'in_progress', priority: 'medium', created: '2026-04-08', updated: 'Hace 5h' },
    { id: 'CCF-003', title: 'Solicitud de nuevo módulo: Finances v2', category: 'Feature', status: 'closed', priority: 'low', created: '2026-03-30', updated: 'Ayer' },
    { id: 'CCF-004', title: 'Reporte de bienvenida no llega al email', category: 'Email', status: 'open', priority: 'medium', created: '2026-04-12', updated: 'Hace 30 min' },
];

const STATUS_CONFIG: Record<string, { icon: any, label: string, color: string, bg: string }> = {
    open: { icon: AlertCircle, label: 'Abierto', color: 'text-amber-600', bg: 'bg-amber-50 dark:bg-amber-500/10' },
    in_progress: { icon: Clock, label: 'En Proceso', color: 'text-blue-600', bg: 'bg-blue-50 dark:bg-blue-500/10' },
    closed: { icon: CheckCircle, label: 'Cerrado', color: 'text-emerald-600', bg: 'bg-emerald-50 dark:bg-emerald-500/10' },
};

const PRIORITY_COLOR: Record<string, string> = {
    high: 'text-rose-500 bg-rose-50 dark:bg-rose-500/10',
    medium: 'text-amber-500 bg-amber-50 dark:bg-amber-500/10',
    low: 'text-slate-400 bg-slate-100 dark:bg-white/5',
};

export default function SupportTicketsPage() {
    const [search, setSearch] = useState('');
    const [filter, setFilter] = useState<string>('all');
    const [showNew, setShowNew] = useState(false);

    const filtered = TICKETS.filter(t =>
        (filter === 'all' || t.status === filter) &&
        (t.title.toLowerCase().includes(search.toLowerCase()) || t.id.includes(search))
    );

    return (
        <div className="h-full flex flex-col bg-slate-50 dark:bg-[#0f1117]">
            {/* Toolbar */}
            <header className="h-14 border-b border-slate-200/60 dark:border-white/5 flex items-center px-6 gap-4 shrink-0 bg-white dark:bg-[#1a1d27]">
                <MessageSquare size={16} className="text-blue-500" />
                <h1 className="text-[11px] font-black uppercase tracking-widest text-slate-400 flex-1">Mis Tickets de Soporte</h1>
                <div className="relative">
                    <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                    <input
                        value={search}
                        onChange={e => setSearch(e.target.value)}
                        placeholder="Buscar ticket..."
                        className="pl-9 pr-4 py-1.5 bg-slate-100 dark:bg-white/5 border-none rounded-xl text-[12px] focus:ring-2 focus:ring-blue-500/20 w-56 transition-all text-slate-700 dark:text-slate-200"
                    />
                </div>
                <button
                    onClick={() => setShowNew(true)}
                    className="flex items-center gap-2 px-4 py-1.5 bg-blue-600 text-white rounded-xl text-[11px] font-black uppercase tracking-widest hover:bg-blue-700 shadow-lg shadow-blue-500/20 transition-all"
                >
                    <Plus size={14} /> Nuevo Ticket
                </button>
            </header>

            {/* Filter tabs */}
            <div className="flex items-center gap-1 px-6 py-3 border-b border-slate-200/60 dark:border-white/5 bg-white dark:bg-[#1a1d27] shrink-0">
                {['all', 'open', 'in_progress', 'closed'].map(s => (
                    <button
                        key={s}
                        onClick={() => setFilter(s)}
                        className={clsx(
                            "px-4 py-1.5 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all",
                            filter === s
                                ? "bg-blue-50 dark:bg-blue-500/10 text-blue-600"
                                : "text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
                        )}
                    >
                        {s === 'all' ? 'Todos' : STATUS_CONFIG[s]?.label ?? s}
                        <span className="ml-1.5 px-1.5 py-0.5 rounded-full bg-current/10 text-[9px]">
                            {s === 'all' ? TICKETS.length : TICKETS.filter(t => t.status === s).length}
                        </span>
                    </button>
                ))}
            </div>

            {/* Ticket List */}
            <div className="flex-1 overflow-y-auto p-6">
                <div className="max-w-4xl mx-auto space-y-3">
                    <AnimatePresence>
                        {filtered.map((ticket, i) => {
                            const sc = STATUS_CONFIG[ticket.status];
                            const Icon = sc.icon;
                            return (
                                <motion.div
                                    key={ticket.id}
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: i * 0.04 }}
                                    className="bg-white dark:bg-[#1a1d27] rounded-2xl border border-slate-200/60 dark:border-white/5 p-5 flex items-center gap-4 shadow-sm hover:shadow-md transition-all cursor-pointer group"
                                >
                                    <div className={clsx("size-10 rounded-xl flex items-center justify-center shrink-0", sc.bg)}>
                                        <Icon size={18} className={sc.color} />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-1">
                                            <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest font-mono">{ticket.id}</span>
                                            <span className={clsx("px-1.5 py-0.5 rounded-full text-[9px] font-black uppercase tracking-widest", PRIORITY_COLOR[ticket.priority])}>
                                                {ticket.priority}
                                            </span>
                                            <span className="flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-slate-100 dark:bg-white/5 text-[9px] font-black text-slate-500 uppercase tracking-widest">
                                                <Tag size={8} /> {ticket.category}
                                            </span>
                                        </div>
                                        <p className="text-[13px] font-semibold text-slate-700 dark:text-slate-200 truncate group-hover:text-blue-600 transition-colors">
                                            {ticket.title}
                                        </p>
                                        <p className="text-[10px] text-slate-400 mt-0.5">Actualizado: {ticket.updated}</p>
                                    </div>
                                    <ChevronRight size={16} className="text-slate-300 group-hover:text-blue-500 transition-colors shrink-0" />
                                </motion.div>
                            );
                        })}
                    </AnimatePresence>

                    {filtered.length === 0 && (
                        <div className="py-20 text-center">
                            <Circle size={40} className="mx-auto text-slate-200 mb-3" />
                            <p className="text-sm font-bold text-slate-400">No se encontraron tickets</p>
                        </div>
                    )}
                </div>
            </div>

            {/* New Ticket Modal */}
            <AnimatePresence>
                {showNew && (
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                        className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-6"
                        onClick={() => setShowNew(false)}>
                        <motion.div initial={{ scale: 0.95, y: 20 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.95, y: 20 }}
                            onClick={e => e.stopPropagation()}
                            className="w-full max-w-lg bg-white dark:bg-[#1a1d27] rounded-3xl border border-slate-200 dark:border-white/5 p-8 shadow-2xl space-y-5">
                            <p className="text-base font-black text-slate-800 dark:text-white">Nuevo Ticket de Soporte</p>
                            <div>
                                <label className="text-[9px] font-black text-slate-400 uppercase tracking-widest block mb-1.5">Asunto</label>
                                <input placeholder="Describe brevemente el problema..." className="w-full px-4 py-3 bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl text-sm outline-none focus:ring-2 focus:ring-blue-500/20 text-slate-700 dark:text-slate-200" />
                            </div>
                            <div>
                                <label className="text-[9px] font-black text-slate-400 uppercase tracking-widest block mb-1.5">Descripción</label>
                                <textarea rows={4} placeholder="Explica el problema en detalle..." className="w-full px-4 py-3 bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl text-sm outline-none focus:ring-2 focus:ring-blue-500/20 resize-none text-slate-700 dark:text-slate-200" />
                            </div>
                            <div className="flex gap-3 pt-2">
                                <button onClick={() => setShowNew(false)} className="flex-1 py-3 rounded-xl border border-slate-200 dark:border-white/10 text-sm font-bold text-slate-500 hover:bg-slate-50 dark:hover:bg-white/5 transition-all">Cancelar</button>
                                <button onClick={() => setShowNew(false)} className="flex-1 py-3 rounded-xl bg-blue-600 text-white text-sm font-black hover:bg-blue-700 transition-all shadow-lg shadow-blue-500/20">Enviar Ticket</button>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}

