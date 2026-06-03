"use client";

import React, { useEffect, useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    MessageSquare,
    Plus,
    Clock,
    CheckCircle,
    AlertCircle,
    Circle,
    ChevronRight,
    Search,
    Loader2,
} from 'lucide-react';
import clsx from 'clsx';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';

interface SupportTicket {
    id: number;
    user_id: number;
    subject: string;
    description: string;
    status: string;
    created_at: string;
    updated_at?: string | null;
}

const STATUS_ORDER = ['open', 'pending', 'in_progress', 'resolved', 'closed'];

const STATUS_CONFIG: Record<string, { icon: any; label: string; color: string; bg: string }> = {
    open: { icon: AlertCircle, label: 'Abierto', color: 'text-amber-600', bg: 'bg-amber-50 dark:bg-amber-500/10' },
    pending: { icon: Clock, label: 'Pendiente', color: 'text-slate-600', bg: 'bg-slate-100 dark:bg-white/5' },
    in_progress: { icon: Clock, label: 'En Proceso', color: 'text-[hsl(var(--primary))]', bg: 'bg-blue-50 dark:bg-blue-500/10' },
    resolved: { icon: CheckCircle, label: 'Resuelto', color: 'text-emerald-600', bg: 'bg-emerald-50 dark:bg-emerald-500/10' },
    closed: { icon: CheckCircle, label: 'Cerrado', color: 'text-emerald-600', bg: 'bg-emerald-50 dark:bg-emerald-500/10' },
};

export default function SupportTicketsPage() {
    const { token, user } = useAuth();
    const { addToast } = useToast();
    const [tickets, setTickets] = useState<SupportTicket[]>([]);
    const [search, setSearch] = useState('');
    const [filter, setFilter] = useState<string>('all');
    const [showNew, setShowNew] = useState(false);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [draft, setDraft] = useState({ subject: '', description: '' });

    useEffect(() => {
        if (!token) return;

        let alive = true;
        const loadTickets = async () => {
            setLoading(true);
            try {
                const data = await apiFetch<SupportTicket[]>('/support/', { token, cache: 'no-store' });
                if (alive) setTickets(Array.isArray(data) ? data : []);
            } catch (err) {
                console.error(err);
                if (alive) addToast('No se pudieron cargar los tickets', 'error');
            } finally {
                if (alive) setLoading(false);
            }
        };

        loadTickets();
        return () => {
            alive = false;
        };
    }, [addToast, token]);

    const filtered = useMemo(() => {
        const normalizedSearch = search.trim().toLowerCase();
        return tickets.filter((ticket) => {
            const status = normalizeStatus(ticket.status);
            const matchesFilter = filter === 'all' || status === filter;
            const matchesSearch = !normalizedSearch || [
                ticket.subject,
                ticket.description,
                String(ticket.id),
            ].some((value) => value.toLowerCase().includes(normalizedSearch));
            return matchesFilter && matchesSearch;
        });
    }, [filter, search, tickets]);

    const counts = useMemo(() => {
        return tickets.reduce<Record<string, number>>((acc, ticket) => {
            const status = normalizeStatus(ticket.status);
            acc[status] = (acc[status] ?? 0) + 1;
            return acc;
        }, {});
    }, [tickets]);

    const handleCreateTicket = async (event: React.FormEvent) => {
        event.preventDefault();
        if (!draft.subject.trim() || !draft.description.trim()) {
            addToast('Completa asunto y descripcion', 'warning');
            return;
        }

        setSubmitting(true);
        try {
            const created = await apiFetch<SupportTicket>('/support/', {
                method: 'POST',
                token,
                body: {
                    subject: draft.subject.trim(),
                    description: draft.description.trim(),
                    user_id: user?.id,
                },
            });
            setTickets((current) => [created, ...current]);
            setDraft({ subject: '', description: '' });
            setShowNew(false);
            addToast('Ticket creado correctamente', 'success');
        } catch (err) {
            console.error(err);
            addToast('No se pudo crear el ticket', 'error');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="h-full flex flex-col bg-slate-50 dark:bg-[#0f1117]">
            <header className="h-8 border-b border-slate-200/60 dark:border-white/5 flex items-center px-3 gap-4 shrink-0 bg-[hsl(var(--bg-primary))] dark:bg-[#1a1d27]">
                <MessageSquare size={16} className="text-[hsl(var(--primary))]" />
                <h1 className="text-[11px] font-semibold uppercase tracking-wide text-slate-400 flex-1">Mis Tickets de Soporte</h1>
                <div className="relative">
                    <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                    <input
                        value={search}
                        onChange={(event) => setSearch(event.target.value)}
                        placeholder="Buscar ticket..."
                        className="pl-9 pr-4 py-1.5 bg-slate-100 dark:bg-white/5 border-none rounded-md text-[12px] focus:ring-2 focus:ring-blue-500/20 w-56 transition-all text-slate-700 dark:text-slate-200"
                    />
                </div>
                <button
                    onClick={() => setShowNew(true)}
                    className="flex items-center gap-2 px-4 py-1.5 bg-[hsl(var(--primary))] text-white rounded-md text-[11px] font-semibold uppercase tracking-wide hover:bg-[hsl(var(--primary))] shadow-lg shadow-blue-500/20 transition-all"
                >
                    <Plus size={14} /> Nuevo Ticket
                </button>
            </header>

            <div className="flex items-center gap-1 px-3 py-3 border-b border-slate-200/60 dark:border-white/5 bg-[hsl(var(--bg-primary))] dark:bg-[#1a1d27] shrink-0">
                {['all', ...STATUS_ORDER].map((status) => (
                    <button
                        key={status}
                        onClick={() => setFilter(status)}
                        className={clsx(
                            'px-4 py-1.5 rounded-md text-[10px] font-semibold uppercase tracking-wide transition-all',
                            filter === status
                                ? 'bg-blue-50 dark:bg-blue-500/10 text-[hsl(var(--primary))]'
                                : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-300',
                        )}
                    >
                        {status === 'all' ? 'Todos' : STATUS_CONFIG[status]?.label ?? status}
                        <span className="ml-1.5 px-1.5 py-0.5 rounded-full bg-current/10 text-[9px]">
                            {status === 'all' ? tickets.length : counts[status] ?? 0}
                        </span>
                    </button>
                ))}
            </div>

            <div className="flex-1 overflow-y-auto p-3">
 <div className="w-full space-y-3">
                    {loading && (
                        <div className="flex items-center justify-center gap-2 rounded-lg border border-slate-200 bg-[hsl(var(--bg-primary))] p-3 text-sm font-bold text-slate-400 dark:border-white/10 dark:bg-[#1a1d27]">
                            <Loader2 size={16} className="animate-spin" /> Cargando tickets...
                        </div>
                    )}

                    <AnimatePresence>
                        {!loading && filtered.map((ticket, index) => {
                            const status = normalizeStatus(ticket.status);
                            const statusConfig = STATUS_CONFIG[status] ?? STATUS_CONFIG.open;
                            const Icon = statusConfig.icon;
                            return (
                                <motion.div
                                    key={ticket.id}
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: index * 0.04 }}
                                    className="bg-[hsl(var(--bg-primary))] dark:bg-[#1a1d27] rounded-lg border border-slate-200/60 dark:border-white/5 p-3 flex items-center gap-4 shadow-sm hover:shadow-md transition-all group"
                                >
                                    <div className={clsx('size-10 rounded-md flex items-center justify-center shrink-0', statusConfig.bg)}>
                                        <Icon size={18} className={statusConfig.color} />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-1">
                                            <span className="font-semibold text-slate-400 uppercase tracking-wide font-mono">CCF-{ticket.id}</span>
                                            <span className={clsx('px-1.5 py-0.5 rounded-full text-[9px] font-semibold uppercase tracking-wide', statusConfig.bg, statusConfig.color)}>
                                                {statusConfig.label}
                                            </span>
                                        </div>
                                        <p className="text-[13px] font-semibold text-slate-700 dark:text-slate-200 truncate group-hover:text-[hsl(var(--primary))] transition-colors">
                                            {ticket.subject}
                                        </p>
                                        <p className="text-[10px] text-slate-400 mt-0.5">
                                            Actualizado: {formatDate(ticket.updated_at ?? ticket.created_at)}
                                        </p>
                                    </div>
                                    <ChevronRight size={16} className="text-slate-300 group-hover:text-[hsl(var(--primary))] transition-colors shrink-0" />
                                </motion.div>
                            );
                        })}
                    </AnimatePresence>

                    {!loading && filtered.length === 0 && (
                        <div className="py-1.5 text-center">
                            <Circle size={40} className="mx-auto text-slate-200 mb-3" />
                            <p className="text-sm font-bold text-slate-400">No se encontraron tickets</p>
                        </div>
                    )}
                </div>
            </div>

            <WorkspaceDrawer
                isOpen={showNew}
                onClose={() => setShowNew(false)}
                title="Nuevo Ticket de Soporte"
                subtitle="Describe el problema o solicitud"
                actions={
                    <>
                        <button onClick={() => setShowNew(false)} className="px-4 py-2 text-[11px] font-bold text-slate-500 hover:text-slate-700 transition-colors">
                            Cancelar
                        </button>
                        <button
                            form="support-ticket-form"
                            type="submit"
                            disabled={submitting}
                            className="flex items-center gap-2 px-4 py-2 bg-[hsl(var(--primary))] text-white rounded-lg text-[11px] font-semibold uppercase tracking-wide shadow-lg shadow-blue-500/20 hover:bg-[hsl(var(--primary))] transition-all disabled:cursor-wait disabled:opacity-60"
                        >
                            {submitting ? <Loader2 size={14} className="animate-spin" /> : null}
                            Enviar Ticket
                        </button>
                    </>
                }
            >
                <form id="support-ticket-form" onSubmit={handleCreateTicket} className="space-y-3 mt-4">
                    <div className="space-y-1.5">
                        <label className="font-semibold text-slate-400 uppercase tracking-wide block">Asunto</label>
                        <input
                            value={draft.subject}
                            onChange={(event) => setDraft((current) => ({ ...current, subject: event.target.value }))}
                            placeholder="Describe brevemente el problema..."
                            className="w-full px-4 py-3 bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-md text-sm outline-none focus:ring-2 focus:ring-blue-500/20 text-slate-700 dark:text-slate-200"
                        />
                    </div>
                    <div className="space-y-1.5">
                        <label className="font-semibold text-slate-400 uppercase tracking-wide block">Descripcion</label>
                        <textarea
                            rows={4}
                            value={draft.description}
                            onChange={(event) => setDraft((current) => ({ ...current, description: event.target.value }))}
                            placeholder="Explica el problema en detalle..."
                            className="w-full px-4 py-3 bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-md text-sm outline-none focus:ring-2 focus:ring-blue-500/20 resize-none text-slate-700 dark:text-slate-200"
                        />
                    </div>
                </form>
            </WorkspaceDrawer>
        </div>
    );
}

function normalizeStatus(status: string | null | undefined) {
    if (!status) return 'open';
    if (status === 'abierto') return 'open';
    if (status === 'pendiente') return 'pending';
    if (status === 'en_progreso') return 'in_progress';
    if (status === 'resuelto') return 'resolved';
    if (status === 'cerrado') return 'closed';
    return status;
}

function formatDate(value: string) {
    return new Date(value).toLocaleDateString('es-CO', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
    });
}
