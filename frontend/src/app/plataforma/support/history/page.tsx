"use client";

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { History, Calendar, MessageSquare, CheckCircle, AlertCircle, Clock, ChevronRight, RotateCcw } from 'lucide-react';
import clsx from 'clsx';

const HISTORY = [
    { id: 'CCF-001', title: 'No puedo acceder a mi cuenta de Academia', date: '2026-04-10', closedDate: '2026-04-11', status: 'closed', resolution: 'Se restablecieron las credenciales correctamente. El agente Pedro A. verificó la identidad del usuario y actualizó la contraseña.', category: 'Acceso', rating: 5 },
    { id: 'CCF-002', title: 'Error al cargar el pipeline de consolidación', date: '2026-04-08', closedDate: null, status: 'in_progress', resolution: null, category: 'Bug', rating: null },
    { id: 'CCF-0XX', title: 'Solicitar permisos de administrador para módulo CMS', date: '2026-03-15', closedDate: '2026-03-16', status: 'closed', resolution: 'Permisos actualizados. Se asignó el rol "Editor CMS" al usuario solicitante.', category: 'Permisos', rating: 4 },
];

const STATUS_CONFIG: Record<string, any> = {
    closed: { icon: CheckCircle, label: 'Cerrado', color: 'text-success-text', bg: 'bg-success-soft dark:bg-[hsl(var(--success))]/10' },
    in_progress: { icon: Clock, label: 'En Proceso', color: 'text-[hsl(var(--primary))]', bg: 'bg-info-soft dark:bg-[hsl(var(--info))]/10' },
    open: { icon: AlertCircle, label: 'Abierto', color: 'text-warning-text', bg: 'bg-warning-soft dark:bg-[hsl(var(--warning))]/10' },
};

export default function SupportHistoryPage() {
    const [expanded, setExpanded] = useState<string | null>(null);

    return (
        <div className="h-full flex flex-col bg-[hsl(var(--surface-1))] dark:bg-[#0f1117]">
            <header className="h-8 border-b border-[hsl(var(--border))]/60 dark:border-white/5 flex items-center px-3 gap-3 shrink-0 bg-[hsl(var(--bg-primary))] dark:bg-[#1a1d27]">
                <History size={16} className="text-[hsl(var(--text-secondary))]" />
                <h1 className="text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Historial de Soporte</h1>
                <span className="ml-auto text-[10px] text-[hsl(var(--text-secondary))] font-bold">{HISTORY.length} conversaciones</span>
            </header>

            <div className="flex-1 overflow-y-auto p-3">
                <div className="max-w-3xl mx-auto space-y-3">
                    {HISTORY.length === 0 ? (
                        <div className="py-1.5 text-center">
                            <History size={40} className="mx-auto text-[hsl(var(--text-secondary))] mb-3" />
                            <p className="text-sm font-bold text-[hsl(var(--text-secondary))]">Sin historial de soporte</p>
                        </div>
                    ) : (
                        HISTORY.map((item, i) => {
                            const sc = STATUS_CONFIG[item.status];
                            const Icon = sc.icon;
                            const isExpanded = expanded === item.id;

                            return (
                                <motion.div
                                    key={item.id}
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: i * 0.05 }}
                                    className="bg-[hsl(var(--bg-primary))] dark:bg-[#1a1d27] rounded-lg border border-[hsl(var(--border))]/60 dark:border-white/5 shadow-sm overflow-hidden"
                                >
                                    {/* Header row */}
                                    <button
                                        onClick={() => setExpanded(isExpanded ? null : item.id)}
                                        className="w-full flex items-center gap-4 px-3 py-1.5 hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 transition-all text-left"
                                    >
                                        <div className={clsx("size-9 rounded-md flex items-center justify-center shrink-0", sc.bg)}>
                                            <Icon size={16} className={sc.color} />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2 mb-0.5">
                                                <span className="font-semibold text-[hsl(var(--text-secondary))] font-mono uppercase tracking-wide">{item.id}</span>
                                                <span className="text-[9px] text-[hsl(var(--text-secondary))]">·</span>
                                                <span className="text-[9px] text-[hsl(var(--text-secondary))] font-bold">{item.category}</span>
                                            </div>
                                            <p className="text-[13px] font-semibold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] truncate">{item.title}</p>
                                            <div className="flex items-center gap-3 mt-0.5">
                                                <span className="flex items-center gap-1 text-[10px] text-[hsl(var(--text-secondary))]">
                                                    <Calendar size={9} /> {item.date}
                                                </span>
                                                {item.closedDate && (
                                                    <>
                                                        <span className="text-[hsl(var(--text-secondary))] text-[10px]">→</span>
                                                        <span className="text-[10px] text-[hsl(var(--text-secondary))]">Cerrado: {item.closedDate}</span>
                                                    </>
                                                )}
                                                {item.rating && (
                                                    <span className="text-[10px] text-[hsl(var(--warning))] font-bold">{'★'.repeat(item.rating)}</span>
                                                )}
                                            </div>
                                        </div>
                                        <ChevronRight size={14} className={clsx("text-[hsl(var(--text-secondary))] transition-all shrink-0", isExpanded && "rotate-90")} />
                                    </button>

                                    {/* Expanded detail */}
                                    {isExpanded && (
                                        <motion.div
                                            initial={{ height: 0, opacity: 0 }}
                                            animate={{ height: 'auto', opacity: 1 }}
                                            className="border-t border-[hsl(var(--border))] dark:border-white/5 px-3 py-1.5 space-y-3"
                                        >
                                            {item.resolution ? (
                                                <div className="flex items-start gap-3 p-4 bg-success-soft dark:bg-[hsl(var(--success))]/10 rounded-md">
                                                    <MessageSquare size={14} className="text-[hsl(var(--success))] shrink-0 mt-0.5" />
                                                    <div>
                                                        <p className="font-semibold text-success-text uppercase tracking-wide mb-1">Resolución</p>
                                                        <p className="text-[12px] text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] leading-relaxed">{item.resolution}</p>
                                                    </div>
                                                </div>
                                            ) : (
                                                <p className="text-[12px] text-[hsl(var(--text-secondary))] italic">Ticket en proceso de resolución...</p>
                                            )}
                                            {item.status === 'closed' && (
                                                <button className="flex items-center gap-2 font-semibold text-[hsl(var(--primary))] hover:opacity-70 transition-opacity uppercase tracking-wide">
                                                    <RotateCcw size={11} /> Reabrir ticket
                                                </button>
                                            )}
                                        </motion.div>
                                    )}
                                </motion.div>
                            );
                        })
                    )}
                </div>
            </div>
        </div>
    );
}

