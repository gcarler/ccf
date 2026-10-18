"use client";

import { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import {
    Plus,
    RefreshCcw,
    MessageSquare,
    Clock,
    ArrowRight,
    Search,
    ShieldCheck,
} from 'lucide-react';
import clsx from 'clsx';
import type { ProjectActivityItem } from '@/types/projects';

interface Props {
    activities: ProjectActivityItem[];
    onRefresh?: () => void;
}

type PmiActivityCategory = 'ALL' | 'SCOPE' | 'TRANSITION' | 'COMMUNICATION';

function getPmiCategory(kind: string): 'SCOPE' | 'TRANSITION' | 'COMMUNICATION' | 'SYSTEM' {
    if (kind === 'project_created' || kind === 'task_created') return 'SCOPE';
    if (kind === 'status_changed') return 'TRANSITION';
    if (kind === 'comment_added') return 'COMMUNICATION';
    return 'SYSTEM';
}

function getPmiBadgeMeta(kind: string): { label: string; className: string } {
    const category = getPmiCategory(kind);
    switch (category) {
        case 'SCOPE':
            return {
                label: 'Alcance EDT',
                className: 'bg-[hsl(var(--success)/0.14)] text-[hsl(var(--success))]',
            };
        case 'TRANSITION':
            return {
                label: 'Transición de Fase',
                className: 'bg-[hsl(var(--warning)/0.15)] text-[hsl(var(--warning))]',
            };
        case 'COMMUNICATION':
            return {
                label: 'Comunicación',
                className: 'bg-[hsl(var(--primary)/0.14)] text-[hsl(var(--primary))]',
            };
        default:
            return {
                label: 'Evento de Sistema',
                className: 'bg-[hsl(var(--surface-2))] text-[hsl(var(--muted-foreground))]',
            };
    }
}

const PMI_FILTER_PILLS: Array<{ id: PmiActivityCategory; label: string }> = [
    { id: 'ALL', label: 'Todos' },
    { id: 'SCOPE', label: 'Alcance' },
    { id: 'TRANSITION', label: 'Transiciones' },
    { id: 'COMMUNICATION', label: 'Comunicaciones' },
];

export default function ProjectActivityFeed({ activities, onRefresh }: Props) {
    const [categoryFilter, setCategoryFilter] = useState<PmiActivityCategory>('ALL');
    const [searchQuery, setSearchQuery] = useState('');

    const sorted = useMemo(
        () =>
            [...activities].sort(
                (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
            ),
        [activities]
    );

    const pmiCounts = useMemo(() => {
        let scope = 0;
        let transition = 0;
        let communication = 0;
        for (const log of sorted) {
            const cat = getPmiCategory(log.kind);
            if (cat === 'SCOPE') scope += 1;
            else if (cat === 'TRANSITION') transition += 1;
            else if (cat === 'COMMUNICATION') communication += 1;
        }
        return { scope, transition, communication };
    }, [sorted]);

    const filteredLogs = useMemo(() => {
        const q = searchQuery.trim().toLowerCase();
        return sorted.filter((log) => {
            if (categoryFilter !== 'ALL' && getPmiCategory(log.kind) !== categoryFilter) {
                return false;
            }
            if (q) {
                const haystack = [log.task_title, log.project_title, log.description]
                    .filter(Boolean)
                    .join(' ')
                    .toLowerCase();
                if (!haystack.includes(q)) return false;
            }
            return true;
        });
    }, [sorted, categoryFilter, searchQuery]);

    return (
        <div className="flex flex-col h-full bg-[hsl(var(--surface-1))] overflow-hidden font-display">
            <header className="p-3 border-b border-[hsl(var(--border))] flex items-center justify-between bg-[hsl(var(--surface-1))]">
                <div>
                    <h3 className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))]">Historia del Proyecto</h3>
                    <p className="text-2xs font-medium text-[hsl(var(--primary))] uppercase mt-0.5">Trazabilidad y Eventos</p>
                </div>
                <div className="flex items-center gap-1.5">
                    {onRefresh && (
                        <button
                            type="button"
                            onClick={onRefresh}
                            aria-label="Actualizar historia"
                            title="Actualizar historia"
                            className="size-7 rounded-md border border-[hsl(var(--border))] flex items-center justify-center text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--primary))] hover:bg-[hsl(var(--surface-2))] transition-colors"
                        >
                            <RefreshCcw size={12} />
                        </button>
                    )}
                    <div className="size-7 rounded-md bg-[hsl(var(--primary)/0.1)] flex items-center justify-center text-[hsl(var(--primary))]">
                        <Clock size={12} />
                    </div>
                </div>
            </header>

            {/* Resumen y Filtro de Trazabilidad PMI §4.5 */}
            <div className="p-3 border-b border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] space-y-2.5">
                <div
                    data-testid="activity-feed-pmi-summary"
                    className="grid grid-cols-3 gap-1.5"
                >
                    <div className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] px-2 py-1.5">
                        <p className="text-3xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))] flex items-center gap-1">
                            <ShieldCheck size={10} className="text-[hsl(var(--success))]" />
                            Alcance / Altas
                        </p>
                        <p className="text-xs font-bold text-[hsl(var(--foreground))] mt-0.5">
                            {pmiCounts.scope}
                        </p>
                    </div>
                    <div className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] px-2 py-1.5">
                        <p className="text-3xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                            Cambios de Fase
                        </p>
                        <p className="text-xs font-bold text-[hsl(var(--foreground))] mt-0.5">
                            {pmiCounts.transition}
                        </p>
                    </div>
                    <div className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] px-2 py-1.5">
                        <p className="text-3xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                            Comunicaciones
                        </p>
                        <p className="text-xs font-bold text-[hsl(var(--foreground))] mt-0.5">
                            {pmiCounts.communication}
                        </p>
                    </div>
                </div>

                <div
                    data-testid="activity-feed-pmi-filter"
                    className="space-y-2"
                >
                    <div className="flex items-center gap-1 flex-wrap">
                        {PMI_FILTER_PILLS.map((pill) => {
                            const active = categoryFilter === pill.id;
                            return (
                                <button
                                    key={pill.id}
                                    type="button"
                                    onClick={() => setCategoryFilter(pill.id)}
                                    className={clsx(
                                        'px-2 py-1 rounded-md text-2xs font-bold uppercase tracking-wider transition-all border',
                                        active
                                            ? 'bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] border-[hsl(var(--primary))]'
                                            : 'bg-[hsl(var(--surface-2))] text-[hsl(var(--muted-foreground))] border-[hsl(var(--border))] hover:text-[hsl(var(--foreground))]'
                                    )}
                                >
                                    {pill.label}
                                </button>
                            );
                        })}
                    </div>

                    <div className="relative">
                        <Search
                            size={12}
                            className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[hsl(var(--muted-foreground))]"
                        />
                        <input
                            type="text"
                            data-testid="activity-feed-search-input"
                            aria-label="Buscar en bitácora de trazabilidad"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            placeholder="Filtrar por paquete, proyecto o descripción..."
                            className="w-full pl-7 pr-2.5 py-1.5 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-xs text-[hsl(var(--foreground))] placeholder:text-[hsl(var(--muted-foreground))] outline-none focus:border-[hsl(var(--primary))]"
                        />
                    </div>
                </div>
            </div>

            <div className="flex-1 overflow-y-auto scrollbar-hide p-3 space-y-4 relative">
                {/* Línea de conexión temporal */}
                <div className="absolute left-[2.25rem] top-8 bottom-8 w-[1px] bg-[hsl(var(--border))]" />

                {filteredLogs.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-40 text-center space-y-3 opacity-40">
                        <Clock size={24} />
                        <p className="text-2xs font-semibold uppercase tracking-wide">Sin registros en la historia aún</p>
                    </div>
                ) : (
                    filteredLogs.map((log, idx) => {
                        const badge = getPmiBadgeMeta(log.kind);
                        return (
                            <motion.div
                                key={log.id}
                                initial={{ opacity: 0, x: 10 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: idx * 0.05 }}
                                className="relative flex gap-4 group"
                            >
                                <div className={clsx(
                                    "size-7 rounded-md flex items-center justify-center z-10 shadow-sm transition-transform group-hover:scale-110",
                                    getIconBg(log.kind)
                                )}>
                                    {getIcon(log.kind)}
                                </div>

                                <div className="flex-1 min-w-0 space-y-1">
                                    <div className="flex items-center justify-between gap-2 flex-wrap">
                                        <div className="flex items-center gap-1.5 min-w-0">
                                            <span className="text-xs font-bold text-[hsl(var(--foreground))] truncate">
                                                {log.task_title || log.project_title || 'Sistema'}
                                            </span>
                                            <span
                                                data-testid={`activity-feed-pmi-badge-${log.id}`}
                                                className={clsx(
                                                    'px-1.5 py-0.5 rounded text-3xs font-bold uppercase tracking-wider shrink-0',
                                                    badge.className
                                                )}
                                            >
                                                {badge.label}
                                            </span>
                                        </div>
                                        <span className="text-2xs font-medium text-[hsl(var(--muted-foreground))] whitespace-nowrap">
                                            {formatRelative(log.created_at)}
                                        </span>
                                    </div>
                                    <p className="text-sm font-medium text-[hsl(var(--muted-foreground))] leading-snug">
                                        {log.description}
                                    </p>
                                </div>
                            </motion.div>
                        );
                    })
                )}
            </div>
        </div>
    );
}

function getIcon(type: string) {
    switch (type) {
        case 'project_created': return <Plus size={14} className="text-[hsl(var(--success,var(--primary)))]" />;
        case 'task_created': return <Plus size={14} className="text-[hsl(var(--primary))]" />;
        case 'status_changed': return <RefreshCcw size={14} className="text-[hsl(var(--warning,var(--primary)))]" />;
        case 'comment_added': return <MessageSquare size={14} className="text-[hsl(var(--primary))]" />;
        default: return <ArrowRight size={14} className="text-[hsl(var(--muted-foreground))]" />;
    }
}

function getIconBg(type: string) {
    switch (type) {
        case 'project_created': return "bg-[hsl(var(--success)/0.15)]";
        case 'task_created': return "bg-[hsl(var(--primary)/0.15)]";
        case 'status_changed': return "bg-[hsl(var(--warning)/0.15)]";
        case 'comment_added': return "bg-[hsl(var(--primary)/0.15)]";
        default: return "bg-[hsl(var(--surface-2))]";
    }
}

function formatRelative(date: string) {
    const now = new Date();
    const then = new Date(date);
    const diff = (now.getTime() - then.getTime()) / 1000;

    if (diff < 60) return 'Ahora';
    if (diff < 3600) return `${Math.floor(diff / 60)}m`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h`;

    // Check if it was yesterday
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today.getTime() - 86400000);
    const eventDate = new Date(then.getFullYear(), then.getMonth(), then.getDate());

    if (eventDate.getTime() === today.getTime()) return 'Hoy';
    if (eventDate.getTime() === yesterday.getTime()) return 'Ayer';

    return then.toLocaleDateString(undefined, { day: '2-digit', month: 'short' });
}
