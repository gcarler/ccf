"use client";

import React from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import {
    AlertTriangle,
    ArrowDown,
    ArrowUp,
    Minus,
} from 'lucide-react';
import clsx from 'clsx';
import { DSCard } from '@/design/components/DSCard';
import { DSSectionHeader } from '@/design/components/DSSectionHeader';

// ─── Types ─────────────────────────────────────────────────────────────────────────────

export interface SeoTrendPoint {
    label: string;
    value: number;
    metadata?: {
        captured_date?: string;
        total_pages?: number;
        pages_with_errors?: number;
        critical_issues?: number;
    };
}

export interface SeoTrendResponse {
    current_score: number | null;
    previous_score: number | null;
    change_vs_prior: number | null;
    /** Daily drop in points that triggers ``is_alert=True``. */
    is_alert: boolean;
    alert_threshold: number;
    total_pages: number;
    pages_with_errors: number;
    critical_issues: number;
    history_7d: SeoTrendPoint[];
    history_30d: SeoTrendPoint[];
    captured_at: string | null;
    has_data: boolean;
}

// ─── Sparkline (responsive) ──────────────────────────────────────────────────────────

const SPARKLINE_MAX_WIDTH = 360;
const SPARKLINE_MIN_WIDTH = 120;
const SPARKLINE_POINT_PX = 12;

function Sparkline({
    points,
    color = 'currentColor',
    height = 44,
    strokeWidth = 2,
    showDots = true,
}: {
    points: SeoTrendPoint[];
    color?: string;
    height?: number;
    strokeWidth?: number;
    showDots?: boolean;
}) {
    if (!points?.length) {
        return (
            <div className="flex items-center justify-center h-11 text-[11px] italic text-[hsl(var(--text-secondary))]">
                Sin datos
            </div>
        );
    }
    const padX = 4;
    const padY = 4;
    const innerH = height - padY * 2;
    // Clamp the viewBox width so mobile renderings don't stretch
    // the path & points. The SVG element itself is ``width: 100%``
    // + ``preserveAspectRatio="none"`` so it scales to the parent
    // container; only the internal coordinate system is bounded.
    const unclampedW = points.length * SPARKLINE_POINT_PX;
    const w = Math.min(
        SPARKLINE_MAX_WIDTH,
        Math.max(SPARKLINE_MIN_WIDTH, unclampedW),
    );
    const innerW = w - padX * 2;
    const values = points.map((p) => Math.max(0, Math.min(100, Number(p.value) || 0)));
    const maxV = Math.max(100, ...values);
    const minV = Math.min(0, ...values);
    const range = Math.max(1, maxV - minV);

    const coords = values.map((v, i) => {
        const x = padX + (i * innerW) / Math.max(1, values.length - 1);
        const y = padY + innerH - ((v - minV) / range) * innerH;
        return { x, y, v };
    });

    const path = coords
        .map((c, i) => (i === 0 ? `M ${c.x.toFixed(2)} ${c.y.toFixed(2)}` : `L ${c.x.toFixed(2)} ${c.y.toFixed(2)}`))
        .join(' ');

    const last = coords[coords.length - 1];

    return (
        <svg
            role="img"
            aria-label="SEO score sparkline"
            width="100%"
            viewBox={`0 0 ${w} ${height}`}
            preserveAspectRatio="none"
            style={{ color }}
        >
            <motion.path
                d={path}
                fill="none"
                stroke={color}
                strokeWidth={strokeWidth}
                strokeLinecap="round"
                strokeLinejoin="round"
                initial={{ pathLength: 0, opacity: 0 }}
                animate={{ pathLength: 1, opacity: 1 }}
                transition={{ duration: 0.7, ease: 'easeOut' }}
            />
            {showDots && coords.map((c, i) => (
                <circle
                    key={i}
                    cx={c.x}
                    cy={c.y}
                    r={i === coords.length - 1 ? 3 : 1.6}
                    fill={color}
                    opacity={i === coords.length - 1 ? 1 : 0.45}
                />
            ))}
            {last && (
                <text
                    x={last.x - 4}
                    y={Math.max(10, last.y - 4)}
                    textAnchor="end"
                    fontSize="9"
                    fontWeight={700}
                    fill={color}
                >
                    {last.v}
                </text>
            )}
        </svg>
    );
}

// ─── Card ────────────────────────────────────────────────────────────────────────────────

export function SeoTrendCard({ trend }: { trend: SeoTrendResponse }) {
    const score = trend.current_score ?? 0;
    const tone =
        score >= 70 ? 'emerald' :
        score >= 50 ? 'amber' :
        'rose';
    const accentHex =
        tone === 'emerald' ? '#10b981' :
        tone === 'amber' ? '#f59e0b' :
        '#f43f5e';

    const change = trend.change_vs_prior;
    const TrendIcon =
        change == null ? Minus :
        change > 0 ? ArrowUp :
        change < 0 ? ArrowDown :
        Minus;
    const trendTone =
        change == null ? 'blue' :
        change >= 0 ? 'emerald' :
        'rose';

    const formatCapturedAt = (iso: string | null) => {
        if (!iso) return '—';
        try {
            return new Date(iso).toLocaleString('es-CO', {
                day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
            });
        } catch {
            return iso;
        }
    };

    return (
        <DSCard padding="md">
            <DSSectionHeader
                eyebrow="SEO Global (Faro)"
                title="Tendencia de SEO Score"
                description="Score promedio diario de las páginas publicadas en el faro"
                actions={
                    trend.is_alert ? (
                        <span
                            className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-rose-100 dark:bg-rose-500/15 text-rose-700 dark:text-rose-300 text-[10px] font-bold uppercase tracking-wide"
                            title={`Bajó más de ${trend.alert_threshold} puntos`}
                        >
                            <AlertTriangle size={11} />
                            Alerta · -{Math.abs(change ?? 0)} pts
                        </span>
                    ) : (
                        <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-emerald-100 dark:bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 text-[10px] font-bold uppercase tracking-wide">
                            Saludable
                        </span>
                    )
                }
            />

            <div className="mt-3 grid grid-cols-1 md:grid-cols-3 gap-3">
                {/* ── Current score (giant) ── */}
                <div className="md:col-span-1">
                    <div className={clsx(
                        'rounded-lg p-3',
                        tone === 'emerald' && 'bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200/60 dark:border-emerald-500/20',
                        tone === 'amber' && 'bg-amber-50 dark:bg-amber-500/10 border border-amber-200/60 dark:border-amber-500/20',
                        tone === 'rose' && 'bg-rose-50 dark:bg-rose-500/10 border border-rose-200/60 dark:border-rose-500/20',
                    )}>
                        <p className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                            Score actual
                        </p>
                        <div className="flex items-end gap-2 mt-1">
                            <span
                                className="text-3xl font-bold leading-none tabular-nums"
                                style={{ color: accentHex }}
                            >
                                {score}
                            </span>
                            <span className="text-[12px] text-[hsl(var(--text-secondary))] mb-1">/ 100</span>
                        </div>
                        {change != null && (
                            <div className={clsx(
                                'mt-2 inline-flex items-center gap-1 text-[11px] font-semibold',
                                trendTone === 'emerald' && 'text-emerald-600 dark:text-emerald-400',
                                trendTone === 'rose' && 'text-rose-600 dark:text-rose-400',
                                trendTone === 'blue' && 'text-[hsl(var(--text-secondary))]',
                            )}>
                                <TrendIcon size={12} />
                                {change > 0 ? `+${change}` : change} pts vs día previo
                            </div>
                        )}
                        <p className="mt-2 text-[10px] text-[hsl(var(--text-secondary))]">
                            {trend.total_pages} págs auditadas · {trend.pages_with_errors} con errores
                        </p>
                    </div>
                </div>

                {/* ── 7d sparkline ── */}
                <div>
                    <div className="flex items-center justify-between mb-1">
                        <p className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                            Últimos 7 días
                        </p>
                        <span className="text-[10px] font-semibold text-[hsl(var(--text-secondary))] tabular-nums">
                            {trend.history_7d.length} pts
                        </span>
                    </div>
                    <Sparkline points={trend.history_7d} color={accentHex} height={56} />
                </div>

                {/* ── 30d sparkline ── */}
                <div>
                    <div className="flex items-center justify-between mb-1">
                        <p className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                            Últimos 30 días
                        </p>
                        <span className="text-[10px] font-semibold text-[hsl(var(--text-secondary))] tabular-nums">
                            {trend.history_30d.length} pts
                        </span>
                    </div>
                    <Sparkline points={trend.history_30d} color={accentHex} height={56} />
                </div>
            </div>

            {/* ── Alert banner ── */}
            {trend.is_alert && change != null && (
                <motion.div
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mt-3 flex items-start gap-2 rounded-lg border border-rose-300/60 dark:border-rose-500/30 bg-rose-50 dark:bg-rose-500/10 p-2.5"
                >
                    <span className="text-rose-600 dark:text-rose-400 mt-0.5 shrink-0 inline-flex items-center justify-center size-4">▼</span>
                    <div className="flex-1 min-w-0">
                        <p className="text-[12px] font-bold text-rose-700 dark:text-rose-300">
                            Caída de {Math.abs(change)} puntos en el último día
                        </p>
                        <p className="text-[11px] text-rose-700/80 dark:text-rose-300/80 mt-0.5">
                            Umbral de alerta: {trend.alert_threshold} pts. Score previo: {trend.previous_score} → actual: {trend.current_score}.
                        </p>
                    </div>
                </motion.div>
            )}

            {/* ── Footer: capture timestamp + deep link ── */}
            <div className="mt-3 flex items-center justify-between text-[10px] text-[hsl(var(--text-secondary))]">
                <span>
                    Último snapshot:{' '}
                    <span className="font-semibold text-[hsl(var(--text-primary))] dark:text-white">
                        {formatCapturedAt(trend.captured_at)}
                    </span>
                </span>
                <Link
                    href="/plataforma/cms/seo-audit"
                    className="font-semibold text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] hover:underline"
                >
                    Ver auditoría completa →
                </Link>
            </div>
        </DSCard>
    );
}
