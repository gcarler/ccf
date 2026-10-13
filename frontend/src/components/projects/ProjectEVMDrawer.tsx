"use client";

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import type { ProjectEVMMetrics, ProjectCurveSPoint, ProjectCurveSResponse } from '@/types/projects';
import {
    Activity,
    AlertTriangle,
    BarChart3,
    BookOpen,
    CheckCircle2,
    DollarSign,
    FileSpreadsheet,
    Grid,
    HelpCircle,
    Info,
    ListTree,
    RefreshCw,
    ShieldAlert,
} from 'lucide-react';
import clsx from 'clsx';
import { toast } from 'sonner';
import { ProjectQuadrantsMatrix } from './ProjectQuadrantsMatrix';
import { ProjectWBSTreeView } from './ProjectWBSTreeView';
import { ProjectAnyDocDrawer } from './ProjectAnyDocDrawer';
import { ProjectPMIKnowledgeDrawer } from './ProjectPMIKnowledgeDrawer';

interface ProjectEVMDrawerProps {
    projectId: string;
    projectTitle?: string;
    isOpen: boolean;
    onClose: () => void;
}

export function ProjectEVMDrawer({
    projectId,
    projectTitle = 'Proyecto',
    isOpen,
    onClose,
}: ProjectEVMDrawerProps) {
    const { token } = useAuth();
    const [activeTab, setActiveTab] = useState<'balance' | 'quadrants' | 'wbs'>('balance');
    const [anyDocOpen, setAnyDocOpen] = useState(false);
    const [pmiOpen, setPMIOpen] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [evmData, setEvmData] = useState<ProjectEVMMetrics | null>(null);
    const [curveData, setCurveData] = useState<ProjectCurveSPoint[]>([]);
    const [hoveredPoint, setHoveredPoint] = useState<ProjectCurveSPoint | null>(null);

    const loadData = useCallback(async () => {
        if (!projectId || !token) return;
        setLoading(true);
        setError(null);
        try {
            const curveRes = await apiFetch<ProjectCurveSResponse>(
                `/projects/${projectId}/evm/curve-s?points=10`,
                { token }
            );
            setEvmData(curveRes.summary);
            setCurveData(curveRes.points);
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : 'Error al cargar métricas de Valor Ganado';
            setError(msg);
            toast.error(msg);
        } finally {
            setLoading(false);
        }
    }, [projectId, token]);

    useEffect(() => {
        if (isOpen) {
            void loadData();
        }
    }, [isOpen, loadData]);

    // Cálculo de dimensiones y escalas SVG para la Curva S
    const chartConfig = useMemo(() => {
        if (!curveData || curveData.length === 0) return null;

        const width = 640;
        const height = 260;
        const paddingLeft = 60;
        const paddingRight = 30;
        const paddingTop = 25;
        const paddingBottom = 40;

        const plotW = width - paddingLeft - paddingRight;
        const plotH = height - paddingTop - paddingBottom;

        // Hallar valor máximo de Y (BAC o max de AC/EV/PV)
        const maxVal = Math.max(
            evmData?.bac || 1,
            ...curveData.map(p => Math.max(p.pv || 0, p.ev || 0, p.ac || 0))
        );

        const safeMax = maxVal > 0 ? maxVal * 1.1 : 100;

        const getX = (idx: number) => paddingLeft + (idx / Math.max(curveData.length - 1, 1)) * plotW;
        const getY = (val: number | null | undefined) => {
            if (val === null || val === undefined) return null;
            return paddingTop + plotH - (Math.min(val, safeMax) / safeMax) * plotH;
        };

        // Generar paths SVG
        const pvPoints = curveData.map((p, i) => `${getX(i)},${getY(p.pv)}`);
        const pvPath = `M ${pvPoints.join(' L ')}`;

        const evPoints = curveData
            .map((p, i) => (p.ev !== null ? `${getX(i)},${getY(p.ev)}` : null))
            .filter(Boolean);
        const evPath = evPoints.length > 0 ? `M ${evPoints.join(' L ')}` : '';

        const acPoints = curveData
            .map((p, i) => (p.ac !== null ? `${getX(i)},${getY(p.ac)}` : null))
            .filter(Boolean);
        const acPath = acPoints.length > 0 ? `M ${acPoints.join(' L ')}` : '';

        return {
            width,
            height,
            paddingLeft,
            paddingTop,
            plotW,
            plotH,
            safeMax,
            getX,
            getY,
            pvPath,
            evPath,
            acPath,
        };
    }, [curveData, evmData?.bac]);

    // Badges de CPI y SPI
    const getPerformanceBadge = (indexVal: number, type: 'cpi' | 'spi') => {
        const isGood = indexVal >= 1.0;
        const isWarning = indexVal >= 0.85 && indexVal < 1.0;

        const label = type === 'cpi'
            ? isGood ? 'Eficiente (Bajo presupuesto)' : isWarning ? 'Sobrecosto moderado' : 'Sobrecosto crítico'
            : isGood ? 'Al día o adelantado' : isWarning ? 'Atraso moderado' : 'Atraso crítico';

        const colorClass = isGood
            ? 'bg-[hsl(var(--success)/0.12)] border-[hsl(var(--success)/0.35)] text-[hsl(var(--success))]'
            : isWarning
            ? 'bg-[hsl(var(--warning)/0.12)] border-[hsl(var(--warning)/0.35)] text-[hsl(var(--warning))]'
            : 'bg-[hsl(var(--destructive)/0.12)] border-[hsl(var(--destructive)/0.35)] text-[hsl(var(--destructive))]';

        return { label, colorClass };
    };

    return (
        <>
            <div className="p-4 sm:p-6 space-y-6">
                {/* Selector de Pestañas Superiores y Acciones Rápidas */}
                <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2">
                    <div className="flex rounded-lg p-1 border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-xs font-semibold flex-1">
                        <button
                            type="button"
                            onClick={() => setActiveTab('balance')}
                            className={clsx(
                                "flex-1 py-1.5 px-3 rounded-md transition-all flex items-center justify-center gap-1.5",
                                activeTab === 'balance'
                                    ? "bg-[hsl(var(--surface-1))] text-[hsl(var(--foreground))] shadow-xs"
                                    : "text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]"
                            )}
                        >
                            <BarChart3 size={14} />
                            <span>Curva S</span>
                        </button>
                        <button
                            type="button"
                            onClick={() => setActiveTab('quadrants')}
                            className={clsx(
                                "flex-1 py-1.5 px-3 rounded-md transition-all flex items-center justify-center gap-1.5",
                                activeTab === 'quadrants'
                                    ? "bg-[hsl(var(--surface-1))] text-[hsl(var(--foreground))] shadow-xs"
                                    : "text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]"
                            )}
                        >
                            <Grid size={14} />
                            <span>4 Cuadrantes</span>
                        </button>
                        <button
                            type="button"
                            onClick={() => setActiveTab('wbs')}
                            className={clsx(
                                "flex-1 py-1.5 px-3 rounded-md transition-all flex items-center justify-center gap-1.5",
                                activeTab === 'wbs'
                                    ? "bg-[hsl(var(--surface-1))] text-[hsl(var(--foreground))] shadow-xs"
                                    : "text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]"
                            )}
                        >
                            <ListTree size={14} />
                            <span>EDT WBS</span>
                        </button>
                    </div>

                    <div className="flex items-center gap-1.5 shrink-0">
                        <button
                            type="button"
                            onClick={() => setAnyDocOpen(true)}
                            title="Conversor Universal AnyDoc"
                            className="px-2.5 py-1.5 rounded-lg text-xs font-medium border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] hover:bg-[hsl(var(--surface-2))] text-[hsl(var(--foreground))] transition-colors flex items-center gap-1.5"
                        >
                            <FileSpreadsheet size={13} className="text-[hsl(var(--primary))]" />
                            <span>AnyDoc</span>
                        </button>
                        <button
                            type="button"
                            onClick={() => setPMIOpen(true)}
                            title="Biblioteca Metodológica PMI"
                            className="px-2.5 py-1.5 rounded-lg text-xs font-medium border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] hover:bg-[hsl(var(--surface-2))] text-[hsl(var(--foreground))] transition-colors flex items-center gap-1.5"
                        >
                            <BookOpen size={13} className="text-[hsl(var(--warning))]" />
                            <span>Doctrina PMI</span>
                        </button>
                    </div>
                </div>

                {/* Vista 2: Matriz de 4 Cuadrantes y Pronósticos */}
                {activeTab === 'quadrants' && (
                    <ProjectQuadrantsMatrix
                        projectId={projectId}
                        projectTitle={projectTitle}
                    />
                )}

                {/* Vista 3: Organigrama WBS */}
                {activeTab === 'wbs' && (
                    <ProjectWBSTreeView
                        projectId={projectId}
                        projectTitle={projectTitle}
                    />
                )}

                {/* Vista 1: Curva S y Balance General */}
                {activeTab === 'balance' && (
                    <div className="space-y-6">
                        {/* Botón de recarga */}
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-1.5 text-xs text-[hsl(var(--muted-foreground))]">
                                <Info size={14} className="shrink-0 text-[hsl(var(--primary))]" />
                                <span>Fórmulas normativas estándar del Project Management Institute (PMI)</span>
                            </div>
                            <button
                                type="button"
                                onClick={() => void loadData()}
                                disabled={loading}
                                className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] hover:bg-[hsl(var(--surface-2))] transition-colors active:scale-95 disabled:opacity-50"
                            >
                                <RefreshCw size={13} className={clsx(loading && 'animate-spin')} />
                                Recalcular
                            </button>
                        </div>

                        {loading && !evmData && (
                            <div className="space-y-4 animate-pulse">
                                <div className="h-28 rounded-xl bg-[hsl(var(--surface-2))]" />
                                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                                    {[1, 2, 3, 4].map(i => (
                                        <div key={i} className="h-20 rounded-lg bg-[hsl(var(--surface-2))]" />
                                    ))}
                                </div>
                                <div className="h-64 rounded-xl bg-[hsl(var(--surface-2))]" />
                            </div>
                        )}

                        {error && !evmData && (
                            <div className="rounded-xl border border-[hsl(var(--destructive)/0.3)] bg-[hsl(var(--destructive)/0.08)] p-6 text-center space-y-3">
                                <AlertTriangle className="mx-auto text-[hsl(var(--destructive))]" size={28} />
                                <p className="text-sm font-semibold text-[hsl(var(--destructive))]">{error}</p>
                                <button
                                    type="button"
                                    onClick={() => void loadData()}
                                    className="px-4 py-2 text-xs font-medium uppercase rounded-lg bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] hover:bg-[hsl(var(--surface-2))]"
                                >
                                    Reintentar
                                </button>
                            </div>
                        )}

                        {evmData && (
                            <>
                                {/* 1. Header Semafórico y Diagnóstico Principal */}
                                <div
                            className={clsx(
                                "rounded-xl border p-4.5 space-y-3 transition-colors",
                                evmData.health_color === 'success' && "bg-[hsl(var(--success)/0.08)] border-[hsl(var(--success)/0.35)]",
                                evmData.health_color === 'warning' && "bg-[hsl(var(--warning)/0.08)] border-[hsl(var(--warning)/0.35)]",
                                evmData.health_color === 'destructive' && "bg-[hsl(var(--destructive)/0.08)] border-[hsl(var(--destructive)/0.35)]"
                            )}
                        >
                            <div className="flex flex-wrap items-center justify-between gap-2">
                                <div className="flex items-center gap-2">
                                    {evmData.health_color === 'success' && (
                                        <CheckCircle2 size={20} className="text-[hsl(var(--success))]" />
                                    )}
                                    {evmData.health_color === 'warning' && (
                                        <AlertTriangle size={20} className="text-[hsl(var(--warning))]" />
                                    )}
                                    {evmData.health_color === 'destructive' && (
                                        <ShieldAlert size={20} className="text-[hsl(var(--destructive))]" />
                                    )}
                                    <div>
                                        <h3 className="text-xs font-medium uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                                            Estado de Control Físico-Financiero
                                        </h3>
                                        <span className="text-sm font-bold text-[hsl(var(--foreground))]">
                                            {evmData.health_status.replace(/_/g, ' ')}
                                        </span>
                                    </div>
                                </div>

                                <div className="flex items-center gap-2 text-xs font-semibold">
                                    <span className="px-2.5 py-1 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))]">
                                        Razón Crítica (CR): <strong>{evmData.cr}</strong>
                                    </span>
                                </div>
                            </div>

                            {/* Comparativa Avance Físico vs Ejecución Financiera */}
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                                <div className="p-3 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))]">
                                    <div className="flex items-center justify-between text-xs">
                                        <span className="font-semibold text-[hsl(var(--muted-foreground))]">Avance Físico Real</span>
                                        <span className="font-extrabold text-[hsl(var(--primary))] text-sm">
                                            {evmData.progress_percentage}%
                                        </span>
                                    </div>
                                    <div className="w-full h-2 rounded-full bg-[hsl(var(--surface-2))] mt-2 overflow-hidden">
                                        <div
                                            className="h-full rounded-full bg-[hsl(var(--primary))] transition-all duration-500"
                                            style={{ width: `${Math.min(evmData.progress_percentage, 100)}%` }}
                                        />
                                    </div>
                                    <span className="text-2xs text-[hsl(var(--muted-foreground))] mt-1 block">
                                        Valor Ganado (EV): ${evmData.ev.toLocaleString('es-CO')}
                                    </span>
                                </div>

                                <div className="p-3 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))]">
                                    <div className="flex items-center justify-between text-xs">
                                        <span className="font-semibold text-[hsl(var(--muted-foreground))]">Ejecución Financiera</span>
                                        <span className={clsx(
                                            "font-extrabold text-sm",
                                            evmData.financial_percentage > evmData.progress_percentage
                                                ? "text-[hsl(var(--destructive))]"
                                                : "text-[hsl(var(--success))]"
                                        )}>
                                            {evmData.financial_percentage}%
                                        </span>
                                    </div>
                                    <div className="w-full h-2 rounded-full bg-[hsl(var(--surface-2))] mt-2 overflow-hidden">
                                        <div
                                            className={clsx(
                                                "h-full rounded-full transition-all duration-500",
                                                evmData.financial_percentage > evmData.progress_percentage
                                                    ? "bg-[hsl(var(--destructive))]"
                                                    : "bg-[hsl(var(--success))]"
                                            )}
                                            style={{ width: `${Math.min(evmData.financial_percentage, 100)}%` }}
                                        />
                                    </div>
                                    <span className="text-2xs text-[hsl(var(--muted-foreground))] mt-1 block">
                                        Costo Real Gastado (AC): ${evmData.ac.toLocaleString('es-CO')}
                                    </span>
                                </div>
                            </div>
                        </div>

                        {/* 2. Cuadrícula de Indicadores Nucleares (CPI, SPI, CV, SV) */}
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                            {/* CPI */}
                            <div className="p-3.5 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] space-y-1">
                                <span className="text-2xs font-medium uppercase tracking-wider text-[hsl(var(--muted-foreground))] flex items-center justify-between">
                                    CPI (Costo)
                                    <span className={clsx(
                                        "px-1.5 py-0.5 rounded text-2xs font-extrabold",
                                        getPerformanceBadge(evmData.cpi, 'cpi').colorClass
                                    )}>
                                        {evmData.cpi >= 1.0 ? '≥ 1.0' : '< 1.0'}
                                    </span>
                                </span>
                                <div className="text-xl font-extrabold text-[hsl(var(--foreground))]">
                                    {evmData.cpi.toFixed(2)}
                                </div>
                                <span className="text-2xs text-[hsl(var(--muted-foreground))] block truncate" title="Fórmula: EV / AC">
                                    {getPerformanceBadge(evmData.cpi, 'cpi').label}
                                </span>
                            </div>

                            {/* SPI */}
                            <div className="p-3.5 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] space-y-1">
                                <span className="text-2xs font-medium uppercase tracking-wider text-[hsl(var(--muted-foreground))] flex items-center justify-between">
                                    SPI (Tiempo)
                                    <span className={clsx(
                                        "px-1.5 py-0.5 rounded text-2xs font-extrabold",
                                        getPerformanceBadge(evmData.spi, 'spi').colorClass
                                    )}>
                                        {evmData.spi >= 1.0 ? '≥ 1.0' : '< 1.0'}
                                    </span>
                                </span>
                                <div className="text-xl font-extrabold text-[hsl(var(--foreground))]">
                                    {evmData.spi.toFixed(2)}
                                </div>
                                <span className="text-2xs text-[hsl(var(--muted-foreground))] block truncate" title="Fórmula: EV / PV">
                                    {getPerformanceBadge(evmData.spi, 'spi').label}
                                </span>
                            </div>

                            {/* Variación de Costo (CV) */}
                            <div className="p-3.5 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] space-y-1">
                                <span className="text-2xs font-medium uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                                    Variación Costo (CV)
                                </span>
                                <div className={clsx(
                                    "text-lg font-extrabold truncate",
                                    evmData.cv >= 0 ? "text-[hsl(var(--success))]" : "text-[hsl(var(--destructive))]"
                                )}>
                                    {evmData.cv >= 0 ? `+$${evmData.cv.toLocaleString('es-CO')}` : `-$${Math.abs(evmData.cv).toLocaleString('es-CO')}`}
                                </div>
                                <span className="text-2xs text-[hsl(var(--muted-foreground))] block">
                                    {evmData.cv >= 0 ? "Superávit generado" : "Sobrecosto actual"}
                                </span>
                            </div>

                            {/* Variación de Cronograma (SV) */}
                            <div className="p-3.5 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] space-y-1">
                                <span className="text-2xs font-medium uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                                    Variación Tiempo (SV)
                                </span>
                                <div className={clsx(
                                    "text-lg font-extrabold truncate",
                                    evmData.sv >= 0 ? "text-[hsl(var(--primary))]" : "text-[hsl(var(--warning))]"
                                )}>
                                    {evmData.sv >= 0 ? `+$${evmData.sv.toLocaleString('es-CO')}` : `-$${Math.abs(evmData.sv).toLocaleString('es-CO')}`}
                                </div>
                                <span className="text-2xs text-[hsl(var(--muted-foreground))] block">
                                    {evmData.sv >= 0 ? "Adelanto monetizado" : "Atraso monetizado"}
                                </span>
                            </div>
                        </div>

                        {/* 3. Gráfico Interactivo de la Curva S (PV vs EV vs AC) */}
                        <div className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4 space-y-3">
                            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[hsl(var(--border))] pb-3">
                                <div>
                                    <h4 className="text-xs font-medium uppercase tracking-wider text-[hsl(var(--foreground))] flex items-center gap-1.5">
                                        <BarChart3 size={15} className="text-[hsl(var(--primary))]" />
                                        Curva S de Desempeño Acumulado
                                    </h4>
                                    <p className="text-2xs text-[hsl(var(--muted-foreground))]">
                                        Comparativa temporal de Valor Planificado (PV), Valor Ganado (EV) y Costo Real (AC)
                                    </p>
                                </div>

                                {/* Leyenda interactiva */}
                                <div className="flex items-center gap-3 text-2xs font-semibold">
                                    <div className="flex items-center gap-1.5">
                                        <span className="w-3.5 h-0.5 border-t-2 border-dashed border-[hsl(var(--muted-foreground))]" />
                                        <span className="text-[hsl(var(--muted-foreground))]">PV (Planificado)</span>
                                    </div>
                                    <div className="flex items-center gap-1.5">
                                        <span className="w-3.5 h-1 rounded bg-[hsl(var(--primary))]" />
                                        <span className="text-[hsl(var(--foreground))]">EV (Ganado)</span>
                                    </div>
                                    <div className="flex items-center gap-1.5">
                                        <span className="w-3.5 h-1 rounded bg-[hsl(var(--destructive))]" />
                                        <span className="text-[hsl(var(--foreground))]">AC (Gastado)</span>
                                    </div>
                                </div>
                            </div>

                            {/* Canvas SVG de la Curva S */}
                            {chartConfig && (
                                <div className="relative overflow-x-auto pt-2">
                                    <svg
                                        viewBox={`0 0 ${chartConfig.width} ${chartConfig.height}`}
                                        className="w-full h-auto max-h-[300px] select-none"
                                        aria-label="Gráfico de Curva S EVM"
                                    >
                                        {/* Líneas de cuadrícula horizontal */}
                                        {[0, 0.25, 0.5, 0.75, 1].map((pct, i) => {
                                            const y = chartConfig.paddingTop + chartConfig.plotH * (1 - pct);
                                            const val = Math.round(chartConfig.safeMax * pct);
                                            return (
                                                <g key={i}>
                                                    <line
                                                        x1={chartConfig.paddingLeft}
                                                        y1={y}
                                                        x2={chartConfig.width - 30}
                                                        y2={y}
                                                        stroke="hsl(var(--border))"
                                                        strokeDasharray={pct === 0 || pct === 1 ? 'none' : '3 3'}
                                                        strokeWidth={0.75}
                                                    />
                                                    <text
                                                        x={chartConfig.paddingLeft - 8}
                                                        y={y + 3}
                                                        textAnchor="end"
                                                        fontSize={9}
                                                        fill="hsl(var(--muted-foreground))"
                                                    >
                                                        ${(val / 1000).toFixed(0)}k
                                                    </text>
                                                </g>
                                            );
                                        })}

                                        {/* Línea PV (Planificado) */}
                                        <path
                                            d={chartConfig.pvPath}
                                            fill="none"
                                            stroke="hsl(var(--muted-foreground))"
                                            strokeWidth={1.75}
                                            strokeDasharray="4 4"
                                        />

                                        {/* Línea EV (Valor Ganado Físico) */}
                                        {chartConfig.evPath && (
                                            <path
                                                d={chartConfig.evPath}
                                                fill="none"
                                                stroke="hsl(var(--primary))"
                                                strokeWidth={2.5}
                                                strokeLinecap="round"
                                            />
                                        )}

                                        {/* Línea AC (Costo Real) */}
                                        {chartConfig.acPath && (
                                            <path
                                                d={chartConfig.acPath}
                                                fill="none"
                                                stroke="hsl(var(--destructive))"
                                                strokeWidth={2.5}
                                                strokeLinecap="round"
                                            />
                                        )}

                                        {/* Puntos y etiquetas X */}
                                        {curveData.map((pt, idx) => {
                                            const x = chartConfig.getX(idx);
                                            const yPv = chartConfig.getY(pt.pv);
                                            const yEv = chartConfig.getY(pt.ev);
                                            const yAc = chartConfig.getY(pt.ac);

                                            return (
                                                <g key={idx} className="cursor-pointer" onMouseEnter={() => setHoveredPoint(pt)}>
                                                    {/* Marcador en el eje X */}
                                                    <text
                                                        x={x}
                                                        y={chartConfig.height - 10}
                                                        textAnchor="middle"
                                                        fontSize={9}
                                                        fill="hsl(var(--muted-foreground))"
                                                    >
                                                        {pt.label}
                                                    </text>

                                                    {/* Punto PV */}
                                                    {yPv !== null && (
                                                        <circle cx={x} cy={yPv} r={3} fill="hsl(var(--surface-1))" stroke="hsl(var(--muted-foreground))" strokeWidth={1.5} />
                                                    )}

                                                    {/* Punto EV */}
                                                    {yEv !== null && (
                                                        <circle cx={x} cy={yEv} r={4} fill="hsl(var(--primary))" stroke="hsl(var(--surface-1))" strokeWidth={1.5} />
                                                    )}

                                                    {/* Punto AC */}
                                                    {yAc !== null && (
                                                        <circle cx={x} cy={yAc} r={4} fill="hsl(var(--destructive))" stroke="hsl(var(--surface-1))" strokeWidth={1.5} />
                                                    )}
                                                </g>
                                            );
                                        })}
                                    </svg>
                                </div>
                            )}

                            {/* Tooltip o Resumen del Punto Seleccionado */}
                            {hoveredPoint && (
                                <div className="mt-2 p-2.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] flex flex-wrap items-center justify-between gap-3 text-xs">
                                    <span className="font-bold text-[hsl(var(--foreground))]">
                                        Fecha: {hoveredPoint.date} ({hoveredPoint.label})
                                    </span>
                                    <div className="flex items-center gap-4">
                                        <span className="text-[hsl(var(--muted-foreground))]">
                                            PV: <strong>${(hoveredPoint.pv || 0).toLocaleString('es-CO')}</strong>
                                        </span>
                                        {hoveredPoint.ev !== null && (
                                            <span className="text-[hsl(var(--primary))] font-semibold">
                                                EV: <strong>${(hoveredPoint.ev).toLocaleString('es-CO')}</strong>
                                            </span>
                                        )}
                                        {hoveredPoint.ac !== null && (
                                            <span className="text-[hsl(var(--destructive))] font-semibold">
                                                AC: <strong>${(hoveredPoint.ac).toLocaleString('es-CO')}</strong>
                                            </span>
                                        )}
                                        {hoveredPoint.cpi !== null && (
                                            <span className="text-2xs px-2 py-0.5 rounded border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))]">
                                                CPI: <strong>{hoveredPoint.cpi}</strong>
                                            </span>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* 4. Proyecciones al Cierre (EAC y VAC) */}
                        <div className="p-4 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] space-y-3">
                            <h4 className="text-xs font-medium uppercase tracking-wider text-[hsl(var(--foreground))] flex items-center gap-1.5">
                                <DollarSign size={14} className="text-[hsl(var(--primary))]" />
                                Pronóstico de Conclusión (Forecasting)
                            </h4>

                            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                                <div className="p-3 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))]">
                                    <span className="text-2xs uppercase text-[hsl(var(--muted-foreground))] font-semibold">
                                        Presupuesto Total (BAC)
                                    </span>
                                    <div className="text-base font-extrabold text-[hsl(var(--foreground))] mt-0.5">
                                        ${evmData.bac.toLocaleString('es-CO')}
                                    </div>
                                    <span className="text-2xs text-[hsl(var(--muted-foreground))]">Línea base autorizada</span>
                                </div>

                                <div className="p-3 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))]">
                                    <span className="text-2xs uppercase text-[hsl(var(--muted-foreground))] font-semibold">
                                        Costo Final Estimado (EAC)
                                    </span>
                                    <div className={clsx(
                                        "text-base font-extrabold mt-0.5",
                                        evmData.eac > evmData.bac ? "text-[hsl(var(--destructive))]" : "text-[hsl(var(--success))]"
                                    )}>
                                        ${evmData.eac.toLocaleString('es-CO')}
                                    </div>
                                    <span className="text-2xs text-[hsl(var(--muted-foreground))]">
                                        {evmData.eac > evmData.bac ? "Requiere ampliación presupuestal" : "Proyectado dentro del límite"}
                                    </span>
                                </div>

                                <div className="p-3 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))]">
                                    <span className="text-2xs uppercase text-[hsl(var(--muted-foreground))] font-semibold">
                                        Variación al Cierre (VAC)
                                    </span>
                                    <div className={clsx(
                                        "text-base font-extrabold mt-0.5",
                                        evmData.vac >= 0 ? "text-[hsl(var(--success))]" : "text-[hsl(var(--destructive))]"
                                    )}>
                                        {evmData.vac >= 0 ? `+$${evmData.vac.toLocaleString('es-CO')}` : `-$${Math.abs(evmData.vac).toLocaleString('es-CO')}`}
                                    </div>
                                    <span className="text-2xs text-[hsl(var(--muted-foreground))]">
                                        {evmData.vac >= 0 ? "Ahorro neto previsto al finalizar" : "Déficit total proyectado al finalizar"}
                                    </span>
                                </div>
                            </div>
                        </div>

                        {/* 5. Recomendaciones Estratégicas del PMI */}
                        {evmData.recommendations && evmData.recommendations.length > 0 && (
                            <div className="p-4 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] space-y-2.5">
                                <h4 className="text-xs font-medium uppercase tracking-wider text-[hsl(var(--foreground))] flex items-center gap-1.5">
                                    <HelpCircle size={14} className="text-[hsl(var(--primary))]" />
                                    Recomendaciones de Gestión
                                </h4>
                                <ul className="space-y-1.5 text-xs text-[hsl(var(--muted-foreground))]">
                                    {evmData.recommendations.map((rec, i) => (
                                        <li key={i} className="flex items-start gap-2">
                                            <span className="text-[hsl(var(--primary))] font-extrabold leading-none mt-1">•</span>
                                            <span>{rec}</span>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </>
                )}
                    </div>
                )}

                {/* Sub-Drawers Laterales (Fase 5: AnyDoc y Doctrina PMI) */}
                <ProjectAnyDocDrawer
                    projectId={projectId}
                    projectTitle={projectTitle}
                    isOpen={anyDocOpen}
                    onClose={() => setAnyDocOpen(false)}
                />
                <ProjectPMIKnowledgeDrawer
                    isOpen={pmiOpen}
                    onClose={() => setPMIOpen(false)}
                />
            </div>
        </>
    );
}

export default ProjectEVMDrawer;
