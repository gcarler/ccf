"use client";

import React, { useState } from 'react';
import {
  Award,
  BarChart3,
  BookOpen,
  Brain,
  CheckCircle2,
  Clock,
  FileSpreadsheet,
  FileText,
  Lightbulb,
  ListChecks,
  Loader2,
  Send,
  Sparkles,
  TrendingUp,
  Users,
} from 'lucide-react';
import { DSButton, DSSkeleton } from '@/design';
import { RightPanel } from '@/components/ui/RightPanel';
import { apiFetch, extractErrorMessage } from '@/lib/http';
import { toast } from 'sonner';
import type {
  ClassPerformanceReport,
  CopilotRubric,
  CopilotSuggestion,
  WeeklyReport,
} from '@/types/academy';

interface CopilotDrawerProps {
  open: boolean;
  onClose: () => void;
  offeringId: string;
  offeringTitle?: string | null;
  token: string | null;
}

type CopilotMode = 'activities' | 'rubric' | 'performance' | 'weekly';

export default function CopilotDrawer({
  open,
  onClose,
  offeringId,
  offeringTitle,
  token,
}: CopilotDrawerProps) {
  const [activeMode, setActiveMode] = useState<CopilotMode>('activities');

  // Mode 1: Activities state
  const [topicInput, setTopicInput] = useState('');
  const [loadingActivities, setLoadingActivities] = useState(false);
  const [suggestions, setSuggestions] = useState<CopilotSuggestion[]>([]);

  // Mode 2: Rubric state
  const [rubricTitle, setRubricTitle] = useState('');
  const [rubricCompetencies, setRubricCompetencies] = useState('');
  const [loadingRubric, setLoadingRubric] = useState(false);
  const [generatedRubric, setGeneratedRubric] = useState<CopilotRubric | null>(null);

  // Mode 3: Performance state
  const [loadingPerformance, setLoadingPerformance] = useState(false);
  const [performanceReport, setPerformanceReport] = useState<ClassPerformanceReport | null>(null);

  // Mode 4: Weekly report state
  const [loadingWeekly, setLoadingWeekly] = useState(false);
  const [weeklyReport, setWeeklyReport] = useState<WeeklyReport | null>(null);

  // Handlers
  const handleSuggestActivities = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !topicInput.trim() || !offeringId) return;
    setLoadingActivities(true);
    try {
      const res = await apiFetch<{ suggestions: CopilotSuggestion[] }>(
        '/api/academy/copilot/suggest-activities',
        {
          token,
          method: 'POST',
          body: JSON.stringify({ offering_id: offeringId, topic: topicInput.trim() }),
        }
      );
      setSuggestions(res.suggestions || []);
      toast.success('Actividades sugeridas generadas a partir del grafo de conocimiento');
    } catch (err) {
      toast.error(extractErrorMessage(err, 'Error al generar sugerencias'));
    } finally {
      setLoadingActivities(false);
    }
  };

  const handleGenerateRubric = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !rubricTitle.trim()) return;
    setLoadingRubric(true);
    try {
      const compList = rubricCompetencies
        .split(',')
        .map((c) => c.trim())
        .filter(Boolean);
      const res = await apiFetch<CopilotRubric>(
        '/api/academy/copilot/generate-rubric',
        {
          token,
          method: 'POST',
          body: JSON.stringify({ title: rubricTitle.trim(), competencies: compList }),
        }
      );
      setGeneratedRubric(res);
      toast.success('Rúbrica estructurada generada con éxito');
    } catch (err) {
      toast.error(extractErrorMessage(err, 'Error al generar la rúbrica'));
    } finally {
      setLoadingRubric(false);
    }
  };

  const handleAnalyzePerformance = async () => {
    if (!token || !offeringId) return;
    setLoadingPerformance(true);
    try {
      const res = await apiFetch<ClassPerformanceReport>(
        '/api/academy/copilot/analyze-class-performance',
        {
          token,
          method: 'POST',
          body: JSON.stringify({ offering_id: offeringId }),
        }
      );
      setPerformanceReport(res);
      toast.success('Análisis de rendimiento grupal actualizado');
    } catch (err) {
      toast.error(extractErrorMessage(err, 'Error al analizar el rendimiento'));
    } finally {
      setLoadingPerformance(false);
    }
  };

  const handleFetchWeeklyReport = async () => {
    if (!token || !offeringId) return;
    setLoadingWeekly(true);
    try {
      const res = await apiFetch<WeeklyReport>(
        `/api/academy/copilot/weekly-report/${offeringId}`,
        { token, cache: 'no-store' }
      );
      setWeeklyReport(res);
      toast.success('Reporte semanal generado');
    } catch (err) {
      toast.error(extractErrorMessage(err, 'Error al obtener reporte semanal'));
    } finally {
      setLoadingWeekly(false);
    }
  };

  return (
    <RightPanel
      open={open}
      onClose={onClose}
      title={
        <div className="flex items-center gap-2">
          <Sparkles className="size-5 text-[hsl(var(--primary))]" />
          <span>Copiloto Docente IA</span>
        </div>
      }
      subtitle={offeringTitle || 'Comisión Académica'}
      width="w-full sm:max-w-3xl"
    >
      <div className="space-y-5 text-xs text-[hsl(var(--foreground))]">
        {/* Selector de Modos / Pestañas */}
        <div className="grid grid-cols-4 gap-1.5 p-1 rounded-xl bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))]">
          <button
            type="button"
            onClick={() => setActiveMode('activities')}
            className={`py-2 px-2 text-center rounded-lg font-bold text-[11px] transition-all flex flex-col sm:flex-row items-center justify-center gap-1.5 ${
              activeMode === 'activities'
                ? 'bg-[hsl(var(--surface-1))] text-[hsl(var(--primary))] shadow-sm'
                : 'text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--foreground))]'
            }`}
          >
            <Lightbulb className="size-3.5" />
            <span>Actividades</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveMode('rubric')}
            className={`py-2 px-2 text-center rounded-lg font-bold text-[11px] transition-all flex flex-col sm:flex-row items-center justify-center gap-1.5 ${
              activeMode === 'rubric'
                ? 'bg-[hsl(var(--surface-1))] text-[hsl(var(--primary))] shadow-sm'
                : 'text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--foreground))]'
            }`}
          >
            <ListChecks className="size-3.5" />
            <span>Rúbrica</span>
          </button>
          <button
            type="button"
            onClick={() => {
              setActiveMode('performance');
              if (!performanceReport) handleAnalyzePerformance();
            }}
            className={`py-2 px-2 text-center rounded-lg font-bold text-[11px] transition-all flex flex-col sm:flex-row items-center justify-center gap-1.5 ${
              activeMode === 'performance'
                ? 'bg-[hsl(var(--surface-1))] text-[hsl(var(--primary))] shadow-sm'
                : 'text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--foreground))]'
            }`}
          >
            <BarChart3 className="size-3.5" />
            <span>Rendimiento</span>
          </button>
          <button
            type="button"
            onClick={() => {
              setActiveMode('weekly');
              if (!weeklyReport) handleFetchWeeklyReport();
            }}
            className={`py-2 px-2 text-center rounded-lg font-bold text-[11px] transition-all flex flex-col sm:flex-row items-center justify-center gap-1.5 ${
              activeMode === 'weekly'
                ? 'bg-[hsl(var(--surface-1))] text-[hsl(var(--primary))] shadow-sm'
                : 'text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--foreground))]'
            }`}
          >
            <FileSpreadsheet className="size-3.5" />
            <span>Semanal</span>
          </button>
        </div>

        {/* 1. MODO: SUGERIR ACTIVIDADES */}
        {activeMode === 'activities' && (
          <div className="space-y-4">
            <form onSubmit={handleSuggestActivities} className="p-4 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] space-y-3">
              <div>
                <label className="font-bold text-xs text-[hsl(var(--foreground))] block mb-1">
                  Tema o Unidad Pedagógica a Explorar:
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={topicInput}
                    onChange={(e) => setTopicInput(e.target.value)}
                    placeholder="Ej. Hermenéutica Bíblica, Gracia y Justificación, Ética Pastoral..."
                    className="flex-1 px-3 py-2 text-xs rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-[hsl(var(--foreground))] focus:outline-none focus:border-[hsl(var(--primary))]"
                  />
                  <DSButton
                    type="submit"
                    disabled={loadingActivities || !topicInput.trim()}
                    className="h-9 px-4 text-xs inline-flex items-center gap-1.5"
                  >
                    {loadingActivities ? <Loader2 className="size-3.5 animate-spin" /> : <Sparkles className="size-3.5" />}
                    <span>Sugerir Actividades</span>
                  </DSButton>
                </div>
              </div>
              <p className="text-[11px] text-[hsl(var(--text-secondary))]">
                El motor analiza la topología de conceptos del grafo cognitivo para armar diálogos socráticos, ejercicios prácticos y recursos.
              </p>
            </form>

            {loadingActivities ? (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <DSSkeleton key={i} className="h-20 w-full rounded-xl" />
                ))}
              </div>
            ) : suggestions.length > 0 ? (
              <div className="space-y-3">
                <span className="font-bold text-xs uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                  Actividades Sugeridas ({suggestions.length})
                </span>
                {suggestions.map((sug, idx) => (
                  <div key={idx} className="p-4 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] space-y-2">
                    <div className="flex items-start justify-between gap-2">
                      <h5 className="font-bold text-xs text-[hsl(var(--foreground))] flex items-center gap-1.5">
                        <Brain className="size-4 text-[hsl(var(--primary))]" />
                        {sug.title}
                      </h5>
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-[hsl(var(--surface-2))] text-[hsl(var(--primary))] flex items-center gap-1">
                        <Clock className="size-3" />
                        {sug.estimated_duration_minutes} min
                      </span>
                    </div>
                    <p className="text-[11px] text-[hsl(var(--text-secondary))] leading-relaxed">
                      {sug.description}
                    </p>
                    {sug.aligned_nodes.length > 0 && (
                      <div className="pt-2 border-t border-[hsl(var(--border))] flex items-center gap-1.5 flex-wrap">
                        <span className="text-[10px] font-bold text-[hsl(var(--text-secondary))]">Nodos alineados:</span>
                        {sug.aligned_nodes.map((nodeTitle, nIdx) => (
                          <span key={nIdx} className="px-2 py-0.5 rounded-full text-[10px] bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))] font-medium">
                            {nodeTitle}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        )}

        {/* 2. MODO: GENERAR RÚBRICA */}
        {activeMode === 'rubric' && (
          <div className="space-y-4">
            <form onSubmit={handleGenerateRubric} className="p-4 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] space-y-3">
              <div>
                <label className="font-bold text-xs text-[hsl(var(--foreground))] block mb-1">
                  Título de la Asignación o Evaluación:
                </label>
                <input
                  type="text"
                  value={rubricTitle}
                  onChange={(e) => setRubricTitle(e.target.value)}
                  placeholder="Ej. Ensayo Argumentativo: Discipulado y Misión Integral"
                  className="w-full px-3 py-2 text-xs rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-[hsl(var(--foreground))] focus:outline-none focus:border-[hsl(var(--primary))]"
                />
              </div>

              <div>
                <label className="font-bold text-xs text-[hsl(var(--foreground))] block mb-1">
                  Competencias Académicas a Evaluar (separadas por comas):
                </label>
                <input
                  type="text"
                  value={rubricCompetencies}
                  onChange={(e) => setRubricCompetencies(e.target.value)}
                  placeholder="Ej. Pensamiento crítico, Rigor exegético, Aplicación pastoral"
                  className="w-full px-3 py-2 text-xs rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-[hsl(var(--foreground))] focus:outline-none focus:border-[hsl(var(--primary))]"
                />
              </div>

              <div className="pt-2 flex justify-end">
                <DSButton
                  type="submit"
                  disabled={loadingRubric || !rubricTitle.trim()}
                  className="h-9 px-4 text-xs inline-flex items-center gap-1.5"
                >
                  {loadingRubric ? <Loader2 className="size-3.5 animate-spin" /> : <ListChecks className="size-3.5" />}
                  <span>Generar Rúbrica Estructurada</span>
                </DSButton>
              </div>
            </form>

            {loadingRubric ? (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <DSSkeleton key={i} className="h-28 w-full rounded-xl" />
                ))}
              </div>
            ) : generatedRubric ? (
              <div className="space-y-3">
                <div className="p-3 rounded-lg bg-[hsl(var(--surface-2))] flex items-center justify-between">
                  <span className="font-bold text-xs text-[hsl(var(--foreground))]">
                    Rúbrica: {generatedRubric.title}
                  </span>
                  <span className="text-[10px] uppercase font-bold text-[hsl(var(--primary))]">
                    4 Criterios (100% Ponderado)
                  </span>
                </div>

                {generatedRubric.criteria.map((crit, cIdx) => (
                  <div key={cIdx} className="p-4 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] space-y-2">
                    <div className="flex items-center justify-between">
                      <h5 className="font-bold text-xs text-[hsl(var(--foreground))]">
                        {crit.criterion}
                      </h5>
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))]">
                        Peso: {crit.weight}%
                      </span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2 border-t border-[hsl(var(--border))] text-[11px]">
                      <div className="p-2 rounded bg-[hsl(var(--surface-2))]">
                        <strong className="text-[10px] block uppercase font-bold text-[hsl(var(--destructive))]">
                          Nivel 1 — Insuficiente
                        </strong>
                        <span className="text-[hsl(var(--text-secondary))]">{crit.levels.level_1_insufficient}</span>
                      </div>
                      <div className="p-2 rounded bg-[hsl(var(--surface-2))]">
                        <strong className="text-[10px] block uppercase font-bold text-[hsl(var(--warning,38_92%_50%))]">
                          Nivel 2 — Básico
                        </strong>
                        <span className="text-[hsl(var(--text-secondary))]">{crit.levels.level_2_basic}</span>
                      </div>
                      <div className="p-2 rounded bg-[hsl(var(--surface-2))]">
                        <strong className="text-[10px] block uppercase font-bold text-[hsl(var(--primary))]">
                          Nivel 3 — Competente
                        </strong>
                        <span className="text-[hsl(var(--text-secondary))]">{crit.levels.level_3_competent}</span>
                      </div>
                      <div className="p-2 rounded bg-[hsl(var(--surface-2))]">
                        <strong className="text-[10px] block uppercase font-bold text-[hsl(var(--foreground))]">
                          Nivel 4 — Ejemplar
                        </strong>
                        <span className="text-[hsl(var(--text-secondary))]">{crit.levels.level_4_exemplary}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        )}

        {/* 3. MODO: RENDIMIENTO GRUPAL */}
        {activeMode === 'performance' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="font-bold text-xs uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                Diagnóstico de Rendimiento de la Comisión
              </span>
              <DSButton
                onClick={handleAnalyzePerformance}
                disabled={loadingPerformance}
                className="h-8 px-3 text-xs inline-flex items-center gap-1.5"
              >
                {loadingPerformance ? <Loader2 className="size-3 animate-spin" /> : <TrendingUp className="size-3" />}
                <span>Actualizar Análisis</span>
              </DSButton>
            </div>

            {loadingPerformance ? (
              <div className="space-y-3">
                <DSSkeleton className="h-24 w-full rounded-xl" />
                <DSSkeleton className="h-32 w-full rounded-xl" />
              </div>
            ) : performanceReport ? (
              <div className="space-y-4">
                {/* Cuadrícula de KPIs */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  <div className="p-3 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-center">
                    <span className="text-[10px] text-[hsl(var(--text-secondary))] block">Estudiantes</span>
                    <span className="font-bold text-lg text-[hsl(var(--foreground))]">{performanceReport.total_students}</span>
                  </div>
                  <div className="p-3 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-center">
                    <span className="text-[10px] text-[hsl(var(--text-secondary))] block">Promedio General</span>
                    <span className="font-bold text-lg text-[hsl(var(--primary))]">{performanceReport.average_grade}</span>
                  </div>
                  <div className="p-3 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-center">
                    <span className="text-[10px] text-[hsl(var(--text-secondary))] block">Notas &gt;= 80</span>
                    <span className="font-bold text-lg text-[hsl(var(--foreground))]">
                      {(performanceReport.grade_distribution['90-100'] || 0) + (performanceReport.grade_distribution['80-89'] || 0)}
                    </span>
                  </div>
                  <div className="p-3 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-center">
                    <span className="text-[10px] text-[hsl(var(--text-secondary))] block">En Riesgo (&lt; 70)</span>
                    <span className="font-bold text-lg text-[hsl(var(--destructive))]">
                      {performanceReport.grade_distribution['under_70'] || 0}
                    </span>
                  </div>
                </div>

                {/* Nodos Débiles del Grafo Cognitivo */}
                {performanceReport.weak_knowledge_nodes.length > 0 && (
                  <div className="p-4 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] space-y-2">
                    <span className="font-bold text-xs text-[hsl(var(--foreground))] flex items-center gap-1.5">
                      <Brain className="size-4 text-[hsl(var(--destructive))]" />
                      Nodos de Conocimiento con Menor Dominio Grupal
                    </span>
                    <div className="space-y-1.5 pt-1">
                      {performanceReport.weak_knowledge_nodes.map((node, nI) => (
                        <div key={nI} className="flex items-center justify-between p-2 rounded bg-[hsl(var(--surface-2))] text-[11px]">
                          <span className="font-medium text-[hsl(var(--foreground))]">{node.title}</span>
                          <span className="font-bold text-[hsl(var(--destructive))]">
                            Dominio: {(node.average_mastery * 100).toFixed(0)}%
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Recomendaciones Pedagógicas */}
                <div className="p-4 rounded-xl border border-[hsl(var(--primary)/0.3)] bg-[hsl(var(--primary)/0.04)] space-y-2">
                  <span className="font-bold text-xs text-[hsl(var(--primary))] flex items-center gap-1.5">
                    <Lightbulb className="size-4" />
                    Recomendaciones Pedagógicas del Copiloto
                  </span>
                  <ul className="list-disc pl-4 space-y-1 text-[11px] text-[hsl(var(--foreground))]">
                    {performanceReport.pedagogical_recommendations.map((rec, rIdx) => (
                      <li key={rIdx}>{rec}</li>
                    ))}
                  </ul>
                </div>
              </div>
            ) : null}
          </div>
        )}

        {/* 4. MODO: REPORTE SEMANAL */}
        {activeMode === 'weekly' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="font-bold text-xs uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                Reporte Ejecutivo Semanal
              </span>
              <DSButton
                onClick={handleFetchWeeklyReport}
                disabled={loadingWeekly}
                className="h-8 px-3 text-xs inline-flex items-center gap-1.5"
              >
                {loadingWeekly ? <Loader2 className="size-3 animate-spin" /> : <FileSpreadsheet className="size-3" />}
                <span>Generar Informe</span>
              </DSButton>
            </div>

            {loadingWeekly ? (
              <div className="space-y-3">
                <DSSkeleton className="h-28 w-full rounded-xl" />
                <DSSkeleton className="h-28 w-full rounded-xl" />
              </div>
            ) : weeklyReport ? (
              <div className="space-y-3">
                <div className="p-4 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] space-y-3">
                  <div className="flex items-center justify-between border-b border-[hsl(var(--border))] pb-2">
                    <span className="font-bold text-xs text-[hsl(var(--foreground))]">
                      {weeklyReport.week_period}
                    </span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))]">
                      Asistencia: {weeklyReport.average_attendance_percent}%
                    </span>
                  </div>

                  <div className="grid grid-cols-3 gap-2 text-center text-[11px]">
                    <div className="p-2 rounded bg-[hsl(var(--surface-2))]">
                      <span className="text-[10px] text-[hsl(var(--text-secondary))] block">Promedio Notas</span>
                      <span className="font-bold text-sm text-[hsl(var(--foreground))]">{weeklyReport.grades_summary.average}</span>
                    </div>
                    <div className="p-2 rounded bg-[hsl(var(--surface-2))]">
                      <span className="text-[10px] text-[hsl(var(--text-secondary))] block">Avance en Grafo</span>
                      <span className="font-bold text-sm text-[hsl(var(--primary))]">{weeklyReport.knowledge_graph_progress_percent}%</span>
                    </div>
                    <div className="p-2 rounded bg-[hsl(var(--surface-2))]">
                      <span className="text-[10px] text-[hsl(var(--text-secondary))] block">Alertas Preventivas</span>
                      <span className="font-bold text-sm text-[hsl(var(--destructive))]">{weeklyReport.wellness_alerts_count}</span>
                    </div>
                  </div>

                  <div className="space-y-1.5 pt-2 border-t border-[hsl(var(--border))]">
                    <span className="font-bold text-[11px] text-[hsl(var(--foreground))] block">
                      Puntos Clave & Acciones de la Semana:
                    </span>
                    <ul className="space-y-1">
                      {weeklyReport.key_highlights.map((h, hIdx) => (
                        <li key={hIdx} className="flex items-start gap-1.5 text-[11px] text-[hsl(var(--text-secondary))]">
                          <CheckCircle2 className="size-3.5 text-[hsl(var(--primary))] shrink-0 mt-0.5" />
                          <span>{h}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        )}
      </div>
    </RightPanel>
  );
}
