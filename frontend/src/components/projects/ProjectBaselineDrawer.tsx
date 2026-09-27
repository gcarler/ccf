"use client";

import React, { useState, useEffect, useCallback } from "react";
import { RightPanel } from "@/components/ui/RightPanel";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { apiFetch } from "@/lib/http";
import type { ProjectBaseline } from "@/types/projects";
import { Layers, Clock, Plus, History, Sparkles } from "lucide-react";
import clsx from "clsx";

interface Props {
  projectId: string;
  isOpen: boolean;
  onClose: () => void;
  onBaselineUpdated?: () => void;
}

export function ProjectBaselineDrawer({
  projectId,
  isOpen,
  onClose,
  onBaselineUpdated,
}: Props) {
  const { token } = useAuth();
  const { addToast } = useToast();

  const [loading, setLoading] = useState(false);
  const [latestBaseline, setLatestBaseline] = useState<ProjectBaseline | null>(null);
  const [baselinesHistory, setBaselinesHistory] = useState<ProjectBaseline[]>([]);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [baselineName, setBaselineName] = useState("");
  const [baselineDescription, setBaselineDescription] = useState("");
  const [saving, setSaving] = useState(false);

  const fetchBaselineData = useCallback(async () => {
    if (!projectId || !token) return;
    try {
      setLoading(true);
      const [latest, list] = await Promise.all([
        apiFetch<ProjectBaseline>(`/projects/${projectId}/baseline`, { token }).catch(() => null),
        apiFetch<ProjectBaseline[]>(`/projects/${projectId}/baselines`, { token }).catch(() => []),
      ]);
      setLatestBaseline(latest);
      setBaselinesHistory(Array.isArray(list) ? list : []);
    } catch {
      // fallback silencioso
    } finally {
      setLoading(false);
    }
  }, [projectId, token]);

  useEffect(() => {
    if (isOpen) {
      fetchBaselineData();
      setShowCreateForm(false);
      setBaselineName("");
      setBaselineDescription("");
    }
  }, [isOpen, fetchBaselineData]);

  const handleCreateBaseline = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !projectId) return;

    const name = baselineName.trim() || `Línea Base ${baselinesHistory.length + 1}`;

    try {
      setSaving(true);
      await apiFetch(`/projects/${projectId}/baseline`, {
        method: "POST",
        token,
        body: {
          name,
          description: baselineDescription.trim() || null,
        },
      });

      addToast({
        title: "Línea Base congelada",
        description: `Se registró '${name}' como instantánea planificada del proyecto.`,
      });

      await fetchBaselineData();
      setShowCreateForm(false);
      setBaselineName("");
      setBaselineDescription("");
      onBaselineUpdated?.();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Error al congelar línea base";
      addToast({
        title: "Error",
        description: msg,
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  };

  const totalVariance = latestBaseline?.total_variance_days ?? 0;
  const comparisons = latestBaseline?.comparisons || [];

  return (
    <RightPanel
      title="Línea Base y Control de Varianza (Gantt)"
      open={isOpen}
      onClose={onClose}
      width={520}
    >
      <div className="flex flex-col h-full space-y-5 p-5 text-[hsl(var(--foreground))] overflow-y-auto">
        {/* Banner de Concepto */}
        <div className="p-4 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] flex items-start gap-3 shadow-xs">
          <div className="p-2.5 rounded-lg bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))] shrink-0">
            <Layers size={20} />
          </div>
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-[hsl(var(--foreground))]">
              Instantánea de Cronograma (Baseline)
            </h4>
            <p className="text-2xs text-[hsl(var(--muted-foreground))] mt-1 leading-relaxed">
              Congela las fechas planificadas para comparar en tiempo real contra los avances reales en la vista Gantt y detectar desvíos temporales.
            </p>
          </div>
        </div>

        {/* Resumen de Varianza General */}
        {latestBaseline ? (
          <div className="p-4 rounded-xl bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-3xs uppercase font-black tracking-widest text-[hsl(var(--muted-foreground))]">
                  Línea Base Activa
                </span>
                <h3 className="text-sm font-black text-[hsl(var(--foreground))] mt-0.5">
                  {latestBaseline.name}
                </h3>
              </div>
              <span
                className={clsx(
                  "px-2.5 py-1 rounded-full text-2xs font-black tracking-wider uppercase border",
                  totalVariance > 0
                    ? "bg-[hsl(var(--destructive))]/10 border-[hsl(var(--destructive))]/30 text-[hsl(var(--destructive))]"
                    : "bg-[hsl(var(--success))]/10 border-[hsl(var(--success))]/30 text-[hsl(var(--success))]"
                )}
              >
                {totalVariance > 0 ? `+${totalVariance}d Desvío Acumulado` : "A Tiempo / Sin Desvíos"}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2.5 pt-2 border-t border-[hsl(var(--border))]/50 text-2xs">
              <div className="p-2.5 rounded-lg bg-[hsl(var(--surface-2))]">
                <span className="text-3xs text-[hsl(var(--muted-foreground))] block font-medium">Congelado el:</span>
                <span className="font-bold text-[hsl(var(--foreground))]">
                  {new Date(latestBaseline.created_at).toLocaleDateString("es-ES", {
                    day: "2-digit",
                    month: "short",
                    year: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
              </div>
              <div className="p-2.5 rounded-lg bg-[hsl(var(--surface-2))]">
                <span className="text-3xs text-[hsl(var(--muted-foreground))] block font-medium">Tareas Auditadas:</span>
                <span className="font-bold text-[hsl(var(--foreground))]">
                  {comparisons.length} tareas
                </span>
              </div>
            </div>
          </div>
        ) : (
          !loading && (
            <div className="p-5 text-center rounded-xl border border-dashed border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]/50 space-y-2">
              <Clock className="mx-auto text-[hsl(var(--muted-foreground))]" size={28} />
              <p className="text-xs font-bold text-[hsl(var(--foreground))]">Sin Línea Base Registrada</p>
              <p className="text-2xs text-[hsl(var(--muted-foreground))] max-w-xs mx-auto">
                No has congelado aún una versión planificada del cronograma para este proyecto.
              </p>
            </div>
          )
        )}

        {/* Botón / Formulario para Congelar Nueva Línea Base */}
        {!showCreateForm ? (
          <button
            onClick={() => setShowCreateForm(true)}
            className="w-full py-2.5 px-4 rounded-xl bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] font-bold text-xs uppercase tracking-wider hover:opacity-90 active:scale-98 transition-all flex items-center justify-center gap-2 shadow-sm cursor-pointer"
          >
            <Plus size={14} /> Congelar Nueva Línea Base
          </button>
        ) : (
          <form
            onSubmit={handleCreateBaseline}
            className="p-4 rounded-xl border border-[hsl(var(--primary))]/30 bg-[hsl(var(--surface-2))] space-y-3.5 shadow-sm"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-black uppercase tracking-wider text-[hsl(var(--primary))] flex items-center gap-1.5">
                <Sparkles size={14} /> Nueva Instantánea Planificada
              </span>
              <button
                type="button"
                onClick={() => setShowCreateForm(false)}
                className="text-2xs font-bold text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] cursor-pointer"
              >
                Cancelar
              </button>
            </div>

            <div className="space-y-1">
              <label className="text-2xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                Nombre de la Línea Base
              </label>
              <input
                type="text"
                value={baselineName}
                onChange={(e) => setBaselineName(e.target.value)}
                placeholder={`Línea Base ${baselinesHistory.length + 1}`}
                className="w-full px-3 py-2 rounded-lg bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] text-xs font-medium focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
              />
            </div>

            <div className="space-y-1">
              <label className="text-2xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                Descripción / Motivo del Congelamiento (Opcional)
              </label>
              <textarea
                value={baselineDescription}
                onChange={(e) => setBaselineDescription(e.target.value)}
                placeholder="Ej: Aprobación del comité ministerial para inicio de obra..."
                rows={2}
                className="w-full px-3 py-2 rounded-lg bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] text-xs font-medium focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))] resize-none"
              />
            </div>

            <button
              type="submit"
              disabled={saving}
              className="w-full py-2 px-3 rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] font-bold text-xs uppercase tracking-wider hover:opacity-90 active:scale-98 transition-all disabled:opacity-50 cursor-pointer"
            >
              {saving ? "Guardando instantánea..." : "Confirmar y Congelar Cronograma"}
            </button>
          </form>
        )}

        {/* Tabla Comparativa de Tareas (Planificado vs Real) */}
        {comparisons.length > 0 && (
          <div className="space-y-2.5">
            <h4 className="text-xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))] flex items-center justify-between">
              <span>Desglose de Varianza por Tarea</span>
              <span className="text-3xs font-semibold lowercase">
                {comparisons.filter((c) => c.variance_days > 0).length} con retraso
              </span>
            </h4>

            <div className="space-y-2">
              {comparisons.map((c) => {
                const isDelayed = c.variance_days > 0;
                const isAhead = c.variance_days < 0;

                const baseDueStr = c.baseline_due ? c.baseline_due.slice(0, 10) : "S/F";
                const curDueStr = c.current_due ? c.current_due.slice(0, 10) : "S/F";

                return (
                  <div
                    key={c.task_id}
                    className="p-3 rounded-xl bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] hover:border-[hsl(var(--border))]/80 transition-all space-y-2"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-bold text-[hsl(var(--foreground))] truncate">
                        {c.title}
                      </span>
                      <span
                        className={clsx(
                          "px-2 py-0.5 rounded text-3xs font-black tracking-tight shrink-0",
                          isDelayed
                            ? "bg-[hsl(var(--destructive))]/15 text-[hsl(var(--destructive))]"
                            : isAhead
                            ? "bg-[hsl(var(--primary))]/15 text-[hsl(var(--primary))]"
                            : "bg-[hsl(var(--success))]/15 text-[hsl(var(--success))]"
                        )}
                      >
                        {isDelayed
                          ? `+${c.variance_days}d Retraso`
                          : isAhead
                          ? `${c.variance_days}d Adelanto`
                          : "A Tiempo"}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-2xs text-[hsl(var(--muted-foreground))]">
                      <div>
                        <span className="text-3xs font-semibold block uppercase">Línea Base:</span>
                        <span className="font-medium text-[hsl(var(--foreground))]">
                          {baseDueStr} ({c.baseline_duration}d)
                        </span>
                      </div>
                      <div>
                        <span className="text-3xs font-semibold block uppercase">Cronograma Real:</span>
                        <span className="font-medium text-[hsl(var(--foreground))]">
                          {curDueStr} ({c.current_duration}d)
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Historial de Instantáneas Anteriores */}
        {baselinesHistory.length > 1 && (
          <div className="pt-3 border-t border-[hsl(var(--border))] space-y-2.5">
            <h4 className="text-xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))] flex items-center gap-1.5">
              <History size={14} /> Historial de Instantáneas ({baselinesHistory.length})
            </h4>
            <div className="space-y-1.5">
              {baselinesHistory.map((b) => (
                <div
                  key={b.id}
                  className="px-3 py-2 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] flex items-center justify-between text-2xs"
                >
                  <span className="font-bold text-[hsl(var(--foreground))]">{b.name}</span>
                  <span className="text-3xs text-[hsl(var(--muted-foreground))]">
                    {new Date(b.created_at).toLocaleDateString("es-ES", {
                      day: "2-digit",
                      month: "short",
                      year: "numeric",
                    })}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </RightPanel>
  );
}
