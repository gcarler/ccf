"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import type { ProjectEVMAdvancedResponse } from '@/types/projects';
import {
    Activity,
    AlertOctagon,
    AlertTriangle,
    ArrowUpRight,
    Calendar,
    CheckCircle2,
    Clock,
    DollarSign,
    HelpCircle,
    Info,
    RefreshCw,
    ShieldAlert,
    TrendingDown,
    TrendingUp,
    Zap,
} from 'lucide-react';
import clsx from 'clsx';
import { toast } from 'sonner';

interface ProjectQuadrantsMatrixProps {
    projectId: string;
    projectTitle?: string;
    onRefresh?: () => void;
}

export function ProjectQuadrantsMatrix({
    projectId,
    projectTitle = 'Proyecto',
    onRefresh,
}: ProjectQuadrantsMatrixProps) {
    const { token } = useAuth();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [data, setData] = useState<ProjectEVMAdvancedResponse | null>(null);
    const [selectedModel, setSelectedModel] = useState<'typical' | 'atypical' | 'composite'>('typical');

    const loadAdvancedData = useCallback(async () => {
        if (!projectId || !token) return;
        setLoading(true);
        setError(null);
        try {
            const res = await apiFetch<ProjectEVMAdvancedResponse>(
                `/projects/${projectId}/evm-advanced`,
                { token }
            );
            setData(res);
            if (onRefresh) onRefresh();
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : 'Error al cargar EVM Avanzado';
            setError(msg);
            toast.error(msg);
        } finally {
            setLoading(false);
        }
    }, [projectId, token, onRefresh]);

    useEffect(() => {
        void loadAdvancedData();
    }, [loadAdvancedData]);

    if (loading && !data) {
        return (
            <div className="p-4 space-y-4 animate-pulse" data-testid="quadrants-loading-skeleton">
                <div className="h-64 rounded-xl bg-[hsl(var(--surface-2))]" />
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div className="h-28 rounded-lg bg-[hsl(var(--surface-2))]" />
                    <div className="h-28 rounded-lg bg-[hsl(var(--surface-2))]" />
                    <div className="h-28 rounded-lg bg-[hsl(var(--surface-2))]" />
                </div>
            </div>
        );
    }

    if (error && !data) {
        return (
            <div className="rounded-xl border border-[hsl(var(--destructive)/0.3)] bg-[hsl(var(--destructive)/0.08)] p-6 text-center space-y-3">
                <AlertTriangle className="mx-auto text-[hsl(var(--destructive))]" size={28} />
                <p className="text-sm font-semibold text-[hsl(var(--destructive))]">{error}</p>
                <button
                    type="button"
                    onClick={() => void loadAdvancedData()}
                    className="px-4 py-2 text-xs font-bold uppercase rounded-lg bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] hover:bg-[hsl(var(--surface-2))]"
                >
                    Reintentar
                </button>
            </div>
        );
    }

    if (!data) return null;

    const { quadrant, earned_schedule, forecast_models, tcpi, early_warnings } = data;
    const activeModel = forecast_models[selectedModel];

    return (
        <div className="space-y-6" data-testid="project-quadrants-matrix">
            {/* Cabecera y botón de refresco */}
            <div className="flex items-center justify-between">
                <div>
                    <h3 className="text-sm font-bold tracking-tight text-[hsl(var(--foreground))]">
                        Matriz de Control y Pronósticos PMI
                    </h3>
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">
                        Plano cartesiano CPI vs SPI • Alertas tempranas y Tiempo Ganado
                    </p>
                </div>
                <button
                    type="button"
                    onClick={() => void loadAdvancedData()}
                    disabled={loading}
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] hover:bg-[hsl(var(--surface-2))] transition-colors active:scale-95 disabled:opacity-50"
                >
                    <RefreshCw size={13} className={clsx(loading && 'animate-spin')} />
                    Actualizar
                </button>
            </div>

            {/* 1. Alertas Tempranas (Regla del 15% PMI) */}
            {early_warnings.length > 0 && (
                <div className="space-y-2">
                    <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                        <AlertOctagon size={14} className="text-[hsl(var(--destructive))]" />
                        <span>Alertas Tempranas de Desviación (Regla 15% PMI)</span>
                    </div>
                    <div className="grid grid-cols-1 gap-2">
                        {early_warnings.map((alert, idx) => (
                            <div
                                key={idx}
                                className={clsx(
                                    "p-3 rounded-lg border text-xs flex items-start gap-2.5 transition-colors",
                                    alert.level === 'critical'
                                        ? "bg-[hsl(var(--destructive)/0.08)] border-[hsl(var(--destructive)/0.3)] text-[hsl(var(--foreground))]"
                                        : "bg-[hsl(var(--warning)/0.08)] border-[hsl(var(--warning)/0.3)] text-[hsl(var(--foreground))]"
                                )}
                            >
                                {alert.level === 'critical' ? (
                                    <ShieldAlert size={16} className="text-[hsl(var(--destructive))] shrink-0 mt-0.5" />
                                ) : (
                                    <AlertTriangle size={16} className="text-[hsl(var(--warning))] shrink-0 mt-0.5" />
                                )}
                                <div className="space-y-0.5 flex-1">
                                    <div className="flex items-center justify-between">
                                        <span className="font-bold">{alert.title}</span>
                                        <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))]">
                                            {alert.threshold}
                                        </span>
                                    </div>
                                    <p className="text-[hsl(var(--muted-foreground))] text-[11px] leading-relaxed">
                                        {alert.detail}
                                    </p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* 2. Matriz de 4 Cuadrantes Gráfica */}
            <div className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4 sm:p-5 space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[hsl(var(--border))] pb-3">
                    <div className="flex items-center gap-2">
                        <div
                            className={clsx(
                                "w-3 h-3 rounded-full animate-pulse",
                                quadrant.badge_color === 'success' && "bg-[hsl(var(--success))]",
                                quadrant.badge_color === 'warning' && "bg-[hsl(var(--warning))]",
                                quadrant.badge_color === 'destructive' && "bg-[hsl(var(--destructive))]",
                                quadrant.badge_color === 'accent' && "bg-[hsl(var(--primary))]"
                            )}
                        />
                        <span className="text-xs font-extrabold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                            Cuadrante {quadrant.quadrant_number}:
                        </span>
                        <span className="text-xs font-bold text-[hsl(var(--foreground))]">
                            {quadrant.name}
                        </span>
                    </div>

                    <div className="flex items-center gap-2 text-xs font-mono font-semibold">
                        <span className="px-2 py-0.5 rounded bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))]">
                            CPI: <strong>{quadrant.cpi.toFixed(2)}</strong>
                        </span>
                        <span className="px-2 py-0.5 rounded bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))]">
                            SPI: <strong>{quadrant.spi.toFixed(2)}</strong>
                        </span>
                    </div>
                </div>

                {/* Plano Cartesiano SVG */}
                <div className="relative w-full aspect-[4/3] sm:aspect-[16/10] max-h-72 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2)/0.4)] overflow-hidden p-2">
                    <svg
                        className="w-full h-full"
                        viewBox="0 0 400 300"
                        preserveAspectRatio="none"
                    >
                        {/* 4 Zonas de Fondo */}
                        {/* Cuadrante II: Top-Left (SPI < 1.0, CPI >= 1.0) -> Riesgo / Aceleración */}
                        <rect x="0" y="0" width="200" height="150" fill="hsl(var(--warning))" fillOpacity="0.08" />
                        {/* Cuadrante I: Top-Right (SPI >= 1.0, CPI >= 1.0) -> Óptimo */}
                        <rect x="200" y="0" width="200" height="150" fill="hsl(var(--success))" fillOpacity="0.12" />
                        {/* Cuadrante III: Bottom-Left (SPI < 1.0, CPI < 1.0) -> Crítico */}
                        <rect x="0" y="150" width="200" height="150" fill="hsl(var(--destructive))" fillOpacity="0.12" />
                        {/* Cuadrante IV: Bottom-Right (SPI >= 1.0, CPI < 1.0) -> Falso Ahorro / Atención */}
                        <rect x="200" y="150" width="200" height="150" fill="hsl(var(--primary))" fillOpacity="0.08" />

                        {/* Líneas de Ejes Centrales (Punto de Equilibrio en 1.0, 1.0) */}
                        <line x1="200" y1="0" x2="200" y2="300" stroke="hsl(var(--border))" strokeWidth="2" strokeDasharray="4 3" />
                        <line x1="0" y1="150" x2="400" y2="150" stroke="hsl(var(--border))" strokeWidth="2" strokeDasharray="4 3" />

                        {/* Etiquetas de los Cuadrantes */}
                        <text x="10" y="20" fill="hsl(var(--warning))" fontSize="10" fontWeight="bold">II. RIESGO / ACELERACIÓN</text>
                        <text x="10" y="32" fill="hsl(var(--muted-foreground))" fontSize="8">Atrasado pero con Holgura Financiera</text>

                        <text x="210" y="20" fill="hsl(var(--success))" fontSize="10" fontWeight="bold">I. ZONA ÓPTIMA</text>
                        <text x="210" y="32" fill="hsl(var(--muted-foreground))" fontSize="8">Adelantado y Bajo Presupuesto</text>

                        <text x="10" y="170" fill="hsl(var(--destructive))" fontSize="10" fontWeight="bold">III. ZONA CRÍTICA</text>
                        <text x="10" y="182" fill="hsl(var(--muted-foreground))" fontSize="8">Atrasado y con Sobrecosto</text>

                        <text x="210" y="170" fill="hsl(var(--primary))" fontSize="10" fontWeight="bold">IV. ATENCIÓN / FALSO AHORRO</text>
                        <text x="210" y="182" fill="hsl(var(--muted-foreground))" fontSize="8">Adelantado pero con Sobrecosto</text>

                        {/* Punto central de equilibrio */}
                        <circle cx="200" cy="150" r="4" fill="hsl(var(--muted-foreground))" />
                        <text x="206" y="146" fill="hsl(var(--muted-foreground))" fontSize="9" fontWeight="bold">(1.0, 1.0)</text>

                        {/* Punto representativo del proyecto */}
                        {(() => {
                            const cx = (quadrant.point_x_pct / 100) * 400;
                            const cy = (quadrant.point_y_pct / 100) * 300;
                            return (
                                <g>
                                    <circle cx={cx} cy={cy} r="10" fill="hsl(var(--primary))" fillOpacity="0.25" className="animate-ping" />
                                    <circle cx={cx} cy={cy} r="6" fill="hsl(var(--primary))" stroke="hsl(var(--surface-1))" strokeWidth="2" />
                                    <text
                                        x={Math.min(cx + 8, 320)}
                                        y={Math.max(cy - 6, 20)}
                                        fill="hsl(var(--foreground))"
                                        fontSize="10"
                                        fontWeight="bold"
                                        className="drop-shadow-sm"
                                    >
                                        Proyecto ({quadrant.cpi.toFixed(2)}, {quadrant.spi.toFixed(2)})
                                    </text>
                                </g>
                            );
                        })()}
                    </svg>
                </div>

                <div className="p-3 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2)/0.5)] text-xs space-y-1">
                    <span className="font-bold text-[hsl(var(--foreground))]">Diagnóstico y Recomendación de Acción:</span>
                    <p className="text-[hsl(var(--muted-foreground))] leading-relaxed">
                        {quadrant.description} {quadrant.action_recommendation}
                    </p>
                </div>
            </div>

            {/* 3. Modelos de Pronóstico EAC (PMI / PMBOK) */}
            <div className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4 sm:p-5 space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[hsl(var(--border))] pb-3">
                    <div className="flex items-center gap-2">
                        <TrendingUp size={16} className="text-[hsl(var(--primary))]" />
                        <h4 className="text-xs font-bold uppercase tracking-wider text-[hsl(var(--foreground))]">
                            Modelos de Pronóstico al Cierre (EAC / ETC / VAC)
                        </h4>
                    </div>

                    {/* Selector de Modelo */}
                    <div className="flex rounded-lg p-0.5 border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-xs">
                        {(['typical', 'atypical', 'composite'] as const).map(key => (
                            <button
                                key={key}
                                type="button"
                                onClick={() => setSelectedModel(key)}
                                className={clsx(
                                    "px-2.5 py-1 font-semibold rounded-md transition-all",
                                    selectedModel === key
                                        ? "bg-[hsl(var(--surface-1))] text-[hsl(var(--foreground))] shadow-xs"
                                        : "text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]"
                                )}
                            >
                                {key === 'typical' && 'Típico'}
                                {key === 'atypical' && 'Atípico'}
                                {key === 'composite' && 'Combinado'}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Tarjeta del Modelo Seleccionado */}
                <div className="p-4 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2)/0.3)] space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                        <div>
                            <span className="text-xs font-bold text-[hsl(var(--primary))] uppercase tracking-tight">
                                {activeModel.title}
                            </span>
                            <p className="text-xs text-[hsl(var(--muted-foreground))] mt-0.5">
                                {activeModel.description}
                            </p>
                        </div>
                        <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] text-[hsl(var(--muted-foreground))]">
                            {activeModel.formula}
                        </span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
                        <div className="p-3 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))]">
                            <span className="text-[11px] font-semibold text-[hsl(var(--muted-foreground))]">
                                Costo Final Proyectado (EAC)
                            </span>
                            <div className="text-base font-bold text-[hsl(var(--foreground))] mt-1">
                                ${activeModel.eac.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                            </div>
                        </div>

                        <div className="p-3 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))]">
                            <span className="text-[11px] font-semibold text-[hsl(var(--muted-foreground))]">
                                Costo Restante para Terminar (ETC)
                            </span>
                            <div className="text-base font-bold text-[hsl(var(--foreground))] mt-1">
                                ${activeModel.etc.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                            </div>
                        </div>

                        <div className="p-3 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))]">
                            <span className="text-[11px] font-semibold text-[hsl(var(--muted-foreground))]">
                                Variación al Cierre (VAC)
                            </span>
                            <div
                                className={clsx(
                                    "text-base font-bold mt-1 flex items-center gap-1",
                                    activeModel.vac >= 0 ? "text-[hsl(var(--success))]" : "text-[hsl(var(--destructive))]"
                                )}
                            >
                                {activeModel.vac >= 0 ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
                                ${activeModel.vac.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                                <span className="text-[10px] font-normal">({activeModel.vac_percentage}%)</span>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Métricas de TCPI */}
                <div className="p-3 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] flex flex-wrap items-center justify-between gap-3 text-xs">
                    <div className="space-y-0.5">
                        <span className="font-bold text-[hsl(var(--foreground))]">
                            Índice de Desempeño del Trabajo por Completar (TCPI):
                        </span>
                        <p className="text-[hsl(var(--muted-foreground))] text-[11px]">
                            {tcpi.explanation}
                        </p>
                    </div>

                    <div className="flex items-center gap-2">
                        {typeof tcpi.tcpi_bac === 'number' && (
                            <span className="px-2 py-1 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] font-mono font-bold">
                                Meta BAC: {tcpi.tcpi_bac.toFixed(2)}
                            </span>
                        )}
                        <span
                            className={clsx(
                                "px-2 py-1 rounded-md text-[10px] font-bold uppercase",
                                tcpi.difficulty_level === 'feasible' && "bg-[hsl(var(--success)/0.15)] text-[hsl(var(--success))]",
                                tcpi.difficulty_level === 'moderate' && "bg-[hsl(var(--warning)/0.15)] text-[hsl(var(--warning))]",
                                (tcpi.difficulty_level === 'hard' || tcpi.difficulty_level === 'critical') &&
                                "bg-[hsl(var(--destructive)/0.15)] text-[hsl(var(--destructive))]"
                            )}
                        >
                            {tcpi.difficulty_level === 'feasible' && 'Holgado'}
                            {tcpi.difficulty_level === 'moderate' && 'Control Estricto'}
                            {tcpi.difficulty_level === 'hard' && 'Muy Exigente'}
                            {tcpi.difficulty_level === 'critical' && 'Presupuesto Agotado'}
                        </span>
                    </div>
                </div>
            </div>

            {/* 4. Tiempo Ganado (Earned Schedule - ES) */}
            <div className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4 sm:p-5 space-y-3">
                <div className="flex items-center gap-2 border-b border-[hsl(var(--border))] pb-3">
                    <Clock size={16} className="text-[hsl(var(--primary))]" />
                    <h4 className="text-xs font-bold uppercase tracking-wider text-[hsl(var(--foreground))]">
                        Control de Tiempo Ganado (Earned Schedule — ES)
                    </h4>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div className="p-3 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2)/0.4)]">
                        <span className="text-[11px] font-semibold text-[hsl(var(--muted-foreground))]">
                            Tiempo Ganado (ES)
                        </span>
                        <div className="text-sm font-bold text-[hsl(var(--foreground))] mt-0.5">
                            {earned_schedule.earned_schedule_days} días
                        </div>
                    </div>

                    <div className="p-3 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2)/0.4)]">
                        <span className="text-[11px] font-semibold text-[hsl(var(--muted-foreground))]">
                            Tiempo Transcurrido (AT)
                        </span>
                        <div className="text-sm font-bold text-[hsl(var(--foreground))] mt-0.5">
                            {earned_schedule.actual_time_days} días
                        </div>
                    </div>

                    <div className="p-3 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2)/0.4)]">
                        <span className="text-[11px] font-semibold text-[hsl(var(--muted-foreground))]">
                            Índice Temporal SPI(t)
                        </span>
                        <div
                            className={clsx(
                                "text-sm font-bold mt-0.5",
                                earned_schedule.schedule_performance_index_time >= 1.0
                                    ? "text-[hsl(var(--success))]"
                                    : "text-[hsl(var(--destructive))]"
                            )}
                        >
                            {earned_schedule.schedule_performance_index_time.toFixed(2)}
                        </div>
                    </div>

                    <div className="p-3 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2)/0.4)]">
                        <span className="text-[11px] font-semibold text-[hsl(var(--muted-foreground))]">
                            Fecha Proyectada (EDAC)
                        </span>
                        <div className="text-sm font-bold text-[hsl(var(--foreground))] mt-0.5">
                            {earned_schedule.projected_finish_date || `${earned_schedule.estimated_duration_at_completion_days}d`}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
