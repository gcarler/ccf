"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch, extractErrorMessage } from '@/lib/http';
import { toast } from 'sonner';
import { PeriodOffering, WellnessSignal } from '@/types/academy';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import EmptyState from '@/components/ui/EmptyState';
import { DSButton, DSSkeleton } from '@/design';
import OfferingGradesDrawer from '@/components/academy/OfferingGradesDrawer';
import WellnessDrawer from '@/components/academy/WellnessDrawer';
import CopilotDrawer from '@/components/academy/CopilotDrawer';
import {
  GraduationCap,
  Award,
  BookOpen,
  Users,
  Clock,
  Sparkles,
  HeartPulse,
  ShieldAlert,
  CheckCircle2,
  RefreshCw,
  Search,
  ListChecks,
  Lightbulb,
  BarChart3,
  Loader2,
} from 'lucide-react';
import clsx from 'clsx';

type DocenteTab = 'comisiones' | 'bienestar' | 'copiloto';

export default function DocentePortalPage() {
  const { token, isAuthenticated } = useAuth();
  const [offerings, setOfferings] = useState<PeriodOffering[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedOfferingId, setSelectedOfferingId] = useState<string>('');
  const [activeTab, setActiveTab] = useState<DocenteTab>('comisiones');

  // Drawers state
  const [gradesDrawerOpen, setGradesDrawerOpen] = useState(false);
  const [wellnessDrawerOpen, setWellnessDrawerOpen] = useState(false);
  const [copilotDrawerOpen, setCopilotDrawerOpen] = useState(false);

  // Direct Tab: Bienestar state
  const [tabSignals, setTabSignals] = useState<WellnessSignal[]>([]);
  const [loadingSignals, setLoadingSignals] = useState(false);
  const [detectingSignals, setDetectingSignals] = useState(false);
  const [resolvingSignalId, setResolvingSignalId] = useState<string | null>(null);

  // Direct Tab: Copiloto inline forms state
  const [copilotTopic, setCopilotTopic] = useState('');
  const [copilotRubricTitle, setCopilotRubricTitle] = useState('');

  const fetchMyOfferings = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const data = await apiFetch<PeriodOffering[]>('/academy/docente/my-offerings', {
        token,
        cache: 'no-store',
      });
      const list = Array.isArray(data) ? data : [];
      setOfferings(list);
      if (list.length > 0 && !selectedOfferingId) {
        setSelectedOfferingId(list[0].id);
      }
    } catch {
      toast.error('Error al sincronizar tus comisiones asignadas');
    } finally {
      setLoading(false);
    }
  }, [token, selectedOfferingId]);

  const fetchTabSignals = useCallback(async (offeringId: string) => {
    if (!token || !offeringId) return;
    setLoadingSignals(true);
    try {
      const data = await apiFetch<WellnessSignal[]>(
        `/academy/wellness/${offeringId}/signals`,
        { token, cache: 'no-store' }
      );
      setTabSignals(Array.isArray(data) ? data : []);
    } catch (err) {
      toast.error(extractErrorMessage(err, 'Error al cargar señales de la comisión'));
    } finally {
      setLoadingSignals(false);
    }
  }, [token]);

  useEffect(() => {
    if (isAuthenticated && token) {
      fetchMyOfferings();
    }
  }, [isAuthenticated, token, fetchMyOfferings]);

  useEffect(() => {
    if (activeTab === 'bienestar' && selectedOfferingId) {
      fetchTabSignals(selectedOfferingId);
    }
  }, [activeTab, selectedOfferingId, fetchTabSignals]);

  const handleDetectSignalsInTab = async () => {
    if (!token || !selectedOfferingId) return;
    setDetectingSignals(true);
    try {
      const res = await apiFetch<{ detected_count: number; summary: string }>(
        '/academy/wellness/detect',
        {
          token,
          method: 'POST',
          body: JSON.stringify({ offering_id: selectedOfferingId }),
        }
      );
      toast.success(res.summary);
      await fetchTabSignals(selectedOfferingId);
    } catch (err) {
      toast.error(extractErrorMessage(err, 'Error en el escaneo automático'));
    } finally {
      setDetectingSignals(false);
    }
  };

  const handleResolveSignalInTab = async (id: string) => {
    if (!token) return;
    setResolvingSignalId(id);
    try {
      await apiFetch<WellnessSignal>(`/academy/wellness/signals/${id}/resolve`, {
        token,
        method: 'POST',
      });
      toast.success('Señal resuelta satisfactoriamente');
      setTabSignals((prev) =>
        prev.map((s) => (s.id === id ? { ...s, is_resolved: true } : s))
      );
    } catch (err) {
      toast.error(extractErrorMessage(err, 'Error al resolver la señal'));
    } finally {
      setResolvingSignalId(null);
    }
  };

  const selectedOffering = offerings.find((o) => o.id === selectedOfferingId) || offerings[0];

  if (loading) {
    return (
      <div className="p-6 space-y-4 bg-[hsl(var(--bg-primary))] min-h-screen">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <DSSkeleton key={i} className="h-32 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] text-[hsl(var(--foreground))]">
      <WorkspaceToolbar
        breadcrumbs={[
          { label: 'Academia', icon: GraduationCap },
          { label: 'Portal Docente ERP', icon: Award },
        ]}
      />

      {/* Header */}
      <div className="px-6 py-4 border-b border-[hsl(var(--border))] bg-[hsl(var(--surface-1))]">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-2xs font-bold uppercase tracking-widest px-2 py-0.5 rounded bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))] border border-[hsl(var(--primary)/0.2)]">
                Cuerpo Docente Canónico
              </span>
              <span className="text-2xs font-bold uppercase tracking-widest px-2 py-0.5 rounded bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] border border-[hsl(var(--border))]">
                Campus OS Cognitivo
              </span>
            </div>
            <h1 className="text-2xl font-bold tracking-tight mt-1 text-[hsl(var(--foreground))]">
              Portal Docente & Copiloto IA
            </h1>
            <p className="text-xs text-[hsl(var(--text-secondary))] mt-0.5">
              Supervisión de comisiones, evaluación por cortes, monitor preventivo de bienestar estudiantil y copiloto pedagógico.
            </p>
          </div>

          {/* Selector de Comisión si hay comisiones */}
          {offerings.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-[hsl(var(--text-secondary))]">Comisión:</span>
              <select
                value={selectedOfferingId}
                onChange={(e) => setSelectedOfferingId(e.target.value)}
                className="px-3 py-1.5 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-xs font-semibold text-[hsl(var(--foreground))] focus:outline-none focus:border-[hsl(var(--primary))]"
              >
                {offerings.map((o) => (
                  <option key={o.id} value={o.id}>
                    {o.subject_code} - {o.subject_name} ({o.group_name})
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {/* Pestañas de Navegación del Portal Docente */}
        <div className="flex items-center gap-2 mt-4 pt-3 border-t border-[hsl(var(--border))]">
          <button
            type="button"
            onClick={() => setActiveTab('comisiones')}
            className={`px-3 py-1.5 text-xs font-bold rounded-lg transition-all flex items-center gap-1.5 ${
              activeTab === 'comisiones'
                ? 'bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] shadow-sm'
                : 'text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))]'
            }`}
          >
            <BookOpen className="size-3.5" />
            <span>Mis Comisiones & Notas</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('bienestar')}
            className={`px-3 py-1.5 text-xs font-bold rounded-lg transition-all flex items-center gap-1.5 ${
              activeTab === 'bienestar'
                ? 'bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] shadow-sm'
                : 'text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))]'
            }`}
          >
            <HeartPulse className="size-3.5" />
            <span>Monitor de Bienestar</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('copiloto')}
            className={`px-3 py-1.5 text-xs font-bold rounded-lg transition-all flex items-center gap-1.5 ${
              activeTab === 'copiloto'
                ? 'bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] shadow-sm'
                : 'text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))]'
            }`}
          >
            <Sparkles className="size-3.5" />
            <span>Copiloto Docente IA</span>
          </button>
        </div>
      </div>

      {/* Body */}
      <div className="p-6 flex-1 overflow-y-auto">
        {offerings.length === 0 ? (
          <EmptyState
            icon={BookOpen}
            title="No tienes comisiones docentes asignadas actualmente"
            description="Cuando la dirección académica te asigne a un grupo formativo para el período activo, aparecerá aquí."
          />
        ) : activeTab === 'comisiones' ? (
          /* TAB 1: COMISIONES & NOTAS */
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {offerings.map((off) => (
                <div
                  key={off.id}
                  className="p-5 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] shadow-sm flex flex-col justify-between hover:border-[hsl(var(--primary)/0.4)] transition-all"
                >
                  <div>
                    <div className="flex items-center justify-between">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-[hsl(var(--surface-2))] text-[hsl(var(--primary))] font-mono">
                        {off.subject_code} • {off.credits} Créditos
                      </span>
                      <span
                        className={clsx(
                          'px-2 py-0.5 rounded-full text-[10px] font-bold uppercase',
                          off.status === 'closed'
                            ? 'bg-[hsl(var(--destructive)/0.1)] text-[hsl(var(--destructive))]'
                            : 'bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))]'
                        )}
                      >
                        {off.status}
                      </span>
                    </div>

                    <h3 className="text-base font-bold text-[hsl(var(--foreground))] mt-2.5">
                      {off.subject_name}
                    </h3>
                    <p className="text-xs text-[hsl(var(--text-secondary))] mt-0.5 font-medium">
                      Grupo: <strong className="text-[hsl(var(--foreground))]">{off.group_name}</strong> • Período: {off.period_code}
                    </p>

                    <div className="mt-4 pt-3 border-t border-[hsl(var(--border))] space-y-1.5 text-xs text-[hsl(var(--text-secondary))]">
                      <div className="flex justify-between items-center">
                        <span className="flex items-center gap-1.5">
                          <Award className="size-3.5 text-[hsl(var(--primary))]" />
                          Esquema:
                        </span>
                        <span className="font-semibold text-[hsl(var(--foreground))]">
                          {off.grading_scheme_name || 'Estándar'}
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="flex items-center gap-1.5">
                          <Users className="size-3.5 text-[hsl(var(--primary))]" />
                          Estudiantes:
                        </span>
                        <span className="font-bold text-[hsl(var(--primary))]">
                          {off.enrolled_count} matriculados
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="mt-5 pt-3 border-t border-[hsl(var(--border))] space-y-2">
                    <button
                      type="button"
                      onClick={() => {
                        setSelectedOfferingId(off.id);
                        setGradesDrawerOpen(true);
                      }}
                      className="w-full py-2 text-xs font-bold rounded-xl bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] flex items-center justify-center gap-2 shadow-sm transition-all hover:opacity-90"
                    >
                      <Award className="size-4" />
                      <span>Calificar Cortes</span>
                    </button>

                    <div className="grid grid-cols-2 gap-2">
                      <button
                        type="button"
                        onClick={() => {
                          setSelectedOfferingId(off.id);
                          setWellnessDrawerOpen(true);
                        }}
                        className="py-1.5 px-2 text-[11px] font-semibold rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] text-[hsl(var(--foreground))] flex items-center justify-center gap-1.5 hover:bg-[hsl(var(--surface-3,var(--surface-2)))]"
                      >
                        <HeartPulse className="size-3.5 text-[hsl(var(--destructive))]" />
                        <span>Bienestar</span>
                      </button>

                      <button
                        type="button"
                        onClick={() => {
                          setSelectedOfferingId(off.id);
                          setCopilotDrawerOpen(true);
                        }}
                        className="py-1.5 px-2 text-[11px] font-semibold rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] text-[hsl(var(--primary))] flex items-center justify-center gap-1.5 hover:bg-[hsl(var(--surface-3,var(--surface-2)))]"
                      >
                        <Sparkles className="size-3.5" />
                        <span>Copiloto IA</span>
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : activeTab === 'bienestar' ? (
          /* TAB 2: MONITOR DE BIENESTAR */
          <div className="space-y-5">
            <div className="p-4 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] flex items-center justify-between flex-wrap gap-3">
              <div>
                <h3 className="font-bold text-sm text-[hsl(var(--foreground))] flex items-center gap-2">
                  <ShieldAlert className="size-4 text-[hsl(var(--primary))]" />
                  Señales de Riesgo de la Comisión ({selectedOffering?.subject_name})
                </h3>
                <p className="text-xs text-[hsl(var(--text-secondary))] mt-0.5">
                  Monitoreo de notas deficientes, inactividad socrática, defensas reprobadas y patrones de inasistencia.
                </p>
              </div>

              <div className="flex items-center gap-2">
                <DSButton
                  onClick={handleDetectSignalsInTab}
                  disabled={detectingSignals}
                  className="h-8 px-3 text-xs inline-flex items-center gap-1.5"
                >
                  {detectingSignals ? (
                    <>
                      <Loader2 className="size-3 animate-spin" />
                      <span>Detectando...</span>
                    </>
                  ) : (
                    <>
                      <RefreshCw className="size-3" />
                      <span>Detectar Riesgo Automático</span>
                    </>
                  )}
                </DSButton>

                <button
                  type="button"
                  onClick={() => setWellnessDrawerOpen(true)}
                  className="h-8 px-3 text-xs font-bold rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-[hsl(var(--foreground))] hover:bg-[hsl(var(--surface-3,var(--surface-2)))] flex items-center gap-1.5"
                >
                  <Search className="size-3" />
                  <span>Ver Panel Completo</span>
                </button>
              </div>
            </div>

            {loadingSignals ? (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <DSSkeleton key={i} className="h-16 w-full rounded-xl" />
                ))}
              </div>
            ) : tabSignals.length === 0 ? (
              <div className="p-10 text-center rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))]">
                <CheckCircle2 className="size-10 mx-auto text-[hsl(var(--primary))] opacity-60" />
                <h4 className="font-bold text-sm mt-3 text-[hsl(var(--foreground))]">
                  Comisión con Bienestar Saludable
                </h4>
                <p className="text-xs text-[hsl(var(--text-secondary))] mt-1">
                  No se registran señales críticas ni patrones de alerta temprana en este momento.
                </p>
              </div>
            ) : (
              <div className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] uppercase text-[10px] font-bold border-b border-[hsl(var(--border))]">
                      <tr>
                        <th className="py-2.5 px-4">Severidad</th>
                        <th className="py-2.5 px-4">Tipo de Señal</th>
                        <th className="py-2.5 px-4">Estudiante / Motivo</th>
                        <th className="py-2.5 px-4">Detección</th>
                        <th className="py-2.5 px-4">Estado</th>
                        <th className="py-2.5 px-4 text-right">Acción</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[hsl(var(--border))]">
                      {tabSignals.map((sig) => (
                        <tr key={sig.id} className="hover:bg-[hsl(var(--surface-2)/0.5)] transition-colors">
                          <td className="py-3 px-4">
                            <span
                              className={clsx(
                                'px-2 py-0.5 rounded text-[10px] font-bold uppercase',
                                sig.severity === 'critical' && 'bg-[hsl(var(--destructive)/0.15)] text-[hsl(var(--destructive))]',
                                sig.severity === 'high' && 'bg-[hsl(var(--warning,38_92%_50%)/0.15)] text-[hsl(var(--warning,38_92%_50%))]',
                                sig.severity === 'medium' && 'bg-[hsl(var(--primary)/0.15)] text-[hsl(var(--primary))]',
                                sig.severity === 'low' && 'bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))]'
                              )}
                            >
                              {sig.severity}
                            </span>
                          </td>
                          <td className="py-3 px-4 font-bold text-[hsl(var(--foreground))]">
                            {sig.signal_type}
                          </td>
                          <td className="py-3 px-4">
                            <div className="text-[hsl(var(--foreground))] font-medium">
                              {sig.student_name || sig.student_id}
                            </div>
                            <div className="text-[11px] text-[hsl(var(--text-secondary))] mt-0.5">
                              {(sig.details?.reason as string) || 'Sin detalle adicional'}
                            </div>
                          </td>
                          <td className="py-3 px-4 text-[hsl(var(--text-secondary))]">
                            {new Date(sig.detected_at).toLocaleDateString()}
                          </td>
                          <td className="py-3 px-4">
                            {sig.is_resolved ? (
                              <span className="text-[10px] font-bold text-[hsl(var(--primary))] flex items-center gap-1">
                                <CheckCircle2 className="size-3" /> Resuelta
                              </span>
                            ) : (
                              <span className="text-[10px] font-bold text-[hsl(var(--destructive))] flex items-center gap-1">
                                <Clock className="size-3" /> Pendiente
                              </span>
                            )}
                          </td>
                          <td className="py-3 px-4 text-right">
                            {!sig.is_resolved ? (
                              <button
                                type="button"
                                onClick={() => handleResolveSignalInTab(sig.id)}
                                disabled={resolvingSignalId === sig.id}
                                className="px-2.5 py-1 text-xs font-bold rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] hover:opacity-90 inline-flex items-center gap-1"
                              >
                                {resolvingSignalId === sig.id && <Loader2 className="size-3 animate-spin" />}
                                Resolver
                              </button>
                            ) : (
                              <span className="text-[11px] text-[hsl(var(--text-secondary))]">Completado</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        ) : (
          /* TAB 3: COPILOTO IA */
          <div className="space-y-6 max-w-4xl">
            <div className="p-5 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] space-y-4">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-bold text-base text-[hsl(var(--foreground))] flex items-center gap-2">
                    <Sparkles className="size-5 text-[hsl(var(--primary))]" />
                    Herramientas de Asistencia Docente Cognitiva
                  </h3>
                  <p className="text-xs text-[hsl(var(--text-secondary))] mt-0.5">
                    Generación de dinámicas pedagógicas basadas en el grafo de conocimiento, rúbricas de evaluación estructuradas y diagnóstico grupal.
                  </p>
                </div>

                <DSButton
                  onClick={() => setCopilotDrawerOpen(true)}
                  className="h-8 px-3 text-xs inline-flex items-center gap-1.5"
                >
                  <Sparkles className="size-3.5" />
                  <span>Abrir Copiloto en Drawer</span>
                </DSButton>
              </div>

              {/* 3 Sub-acciones solicitadas por requerimiento */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-3 border-t border-[hsl(var(--border))]">
                {/* (a) Sugerir Actividades */}
                <div className="p-4 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] flex flex-col justify-between space-y-3">
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-[hsl(var(--primary))] font-bold text-xs">
                      <Lightbulb className="size-4" />
                      <span>Sugerir Actividades</span>
                    </div>
                    <p className="text-[11px] text-[hsl(var(--text-secondary))]">
                      Ingresa un tema o concepto para deducir diálogos socráticos, ejercicios prácticos y recursos formativos.
                    </p>
                    <input
                      type="text"
                      value={copilotTopic}
                      onChange={(e) => setCopilotTopic(e.target.value)}
                      placeholder="Ej. Teología Paulina..."
                      className="w-full px-2.5 py-1.5 text-xs rounded border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--foreground))]"
                    />
                  </div>
                  <DSButton
                    onClick={() => setCopilotDrawerOpen(true)}
                    className="w-full h-8 text-xs inline-flex items-center justify-center gap-1.5"
                  >
                    <span>Sugerir Actividades</span>
                  </DSButton>
                </div>

                {/* (b) Generar Rúbrica */}
                <div className="p-4 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] flex flex-col justify-between space-y-3">
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-[hsl(var(--primary))] font-bold text-xs">
                      <ListChecks className="size-4" />
                      <span>Generar Rúbrica</span>
                    </div>
                    <p className="text-[11px] text-[hsl(var(--text-secondary))]">
                      Construye matrices evaluativas de 4 niveles ponderados para ensayos, proyectos o exámenes.
                    </p>
                    <input
                      type="text"
                      value={copilotRubricTitle}
                      onChange={(e) => setCopilotRubricTitle(e.target.value)}
                      placeholder="Título de la evaluación..."
                      className="w-full px-2.5 py-1.5 text-xs rounded border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--foreground))]"
                    />
                  </div>
                  <DSButton
                    onClick={() => setCopilotDrawerOpen(true)}
                    className="w-full h-8 text-xs inline-flex items-center justify-center gap-1.5"
                  >
                    <span>Generar Rúbrica</span>
                  </DSButton>
                </div>

                {/* (c) Analizar Rendimiento del Grupo */}
                <div className="p-4 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] flex flex-col justify-between space-y-3">
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-[hsl(var(--primary))] font-bold text-xs">
                      <BarChart3 className="size-4" />
                      <span>Rendimiento del Grupo</span>
                    </div>
                    <p className="text-[11px] text-[hsl(var(--text-secondary))]">
                      Diagnostica curvas de distribución de notas, conceptos con menor dominio en el grafo y estudiantes en riesgo.
                    </p>
                  </div>
                  <DSButton
                    onClick={() => setCopilotDrawerOpen(true)}
                    className="w-full h-8 text-xs inline-flex items-center justify-center gap-1.5"
                  >
                    <span>Analizar Rendimiento</span>
                  </DSButton>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Drawers Laterales Canónicos (0 Modales) */}
      <OfferingGradesDrawer
        open={gradesDrawerOpen}
        onClose={() => setGradesDrawerOpen(false)}
        offeringId={selectedOfferingId}
        token={token}
        onSuccess={() => fetchMyOfferings()}
      />

      <WellnessDrawer
        open={wellnessDrawerOpen}
        onClose={() => setWellnessDrawerOpen(false)}
        offeringId={selectedOfferingId}
        offeringTitle={selectedOffering?.subject_name || undefined}
        token={token}
        onSuccess={() => {
          fetchMyOfferings();
          if (selectedOfferingId) fetchTabSignals(selectedOfferingId);
        }}
      />

      <CopilotDrawer
        open={copilotDrawerOpen}
        onClose={() => setCopilotDrawerOpen(false)}
        offeringId={selectedOfferingId}
        offeringTitle={selectedOffering?.subject_name || undefined}
        token={token}
      />
    </div>
  );
}
