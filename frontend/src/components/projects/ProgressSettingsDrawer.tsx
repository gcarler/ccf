"use client";

import React, { useState, useEffect } from "react";
import { RightPanel } from "@/components/ui/RightPanel";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { apiFetch } from "@/lib/http";
import {
  Sliders,
  CheckCircle2,
  ListTodo,
  Milestone,
  Activity,
  Save,
  AlertTriangle,
  AlertOctagon,
  Sparkles,
} from "lucide-react";
import clsx from "clsx";

interface ProgressSettingsDrawerProps {
  projectId: string;
  isOpen: boolean;
  onClose: () => void;
  currentMode?: "auto_tasks" | "milestones" | "manual";
  manualProgress?: number;
  currentHealthOverride?: string | null;
  onSaved?: () => void;
}

export function ProgressSettingsDrawer({
  projectId,
  isOpen,
  onClose,
  currentMode = "auto_tasks",
  manualProgress = 0,
  currentHealthOverride = null,
  onSaved,
}: ProgressSettingsDrawerProps) {
  const { token } = useAuth();
  const { addToast } = useToast();

  const [mode, setMode] = useState<"auto_tasks" | "milestones" | "manual">(currentMode);
  const [progressVal, setProgressVal] = useState<number>(manualProgress);
  const [healthOverride, setHealthOverride] = useState<string | null>(currentHealthOverride);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setMode(currentMode);
      setProgressVal(manualProgress);
      setHealthOverride(currentHealthOverride);
    }
  }, [isOpen, currentMode, manualProgress, currentHealthOverride]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectId || !token) return;

    try {
      setSaving(true);
      await apiFetch(`/projects/${projectId}`, {
        method: "PATCH",
        token,
        body: {
          progress_mode: mode,
          manual_progress: mode === "manual" ? Number(progressVal) : 0,
          health_override: healthOverride || null,
        },
      });

      addToast({
        title: "Avance configurado",
        description: "El motor de avance y salud del proyecto ha sido actualizado.",
        variant: "success",
      });

      onSaved?.();
      onClose();
    } catch {
      addToast({
        title: "Error al guardar",
        description: "No se pudo actualizar la configuración de avance.",
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  };

  const MODES = [
    {
      id: "auto_tasks" as const,
      title: "Automático por Tareas",
      description: "El % se calcula dividiendo las tareas completadas entre el total de tareas activas.",
      icon: ListTodo,
      badge: "Recomendado",
    },
    {
      id: "milestones" as const,
      title: "Automático por Hitos",
      description: "El % se calcula según el cumplimiento de los hitos y entregables fijados.",
      icon: Milestone,
      badge: "Estratégico",
    },
    {
      id: "manual" as const,
      title: "Manual",
      description: "Permite establecer libremente el porcentaje de avance general del proyecto.",
      icon: Sliders,
      badge: "Personalizado",
    },
  ];

  const HEALTH_OPTIONS = [
    {
      id: null,
      label: "Automático",
      description: "Se determina por tareas vencidas y fechas límites.",
      icon: Activity,
      color: "text-[hsl(var(--foreground))]",
      border: "border-[hsl(var(--border))]",
    },
    {
      id: "on_track",
      label: "En Camino (Verde)",
      description: "El proyecto avanza según cronograma sin bloqueos.",
      icon: CheckCircle2,
      color: "text-[hsl(var(--success))]",
      border: "border-[hsl(var(--success))]/40",
    },
    {
      id: "at_risk",
      label: "En Riesgo (Ámbar)",
      description: "Existen tareas retrasadas o riesgos inminentes.",
      icon: AlertTriangle,
      color: "text-[hsl(var(--warning))]",
      border: "border-[hsl(var(--warning))]/40",
    },
    {
      id: "off_track",
      label: "Retrasado (Rojo)",
      description: "Críticamente fuera de plazo con bloqueos severos.",
      icon: AlertOctagon,
      color: "text-[hsl(var(--destructive))]",
      border: "border-[hsl(var(--destructive))]/40",
    },
  ];

  return (
    <RightPanel
      title="Motor de Avance y Salud del Proyecto"
      open={isOpen}
      onClose={onClose}
      width={420}
    >
      <form onSubmit={handleSave} className="flex flex-col h-full space-y-4 p-4 text-[hsl(var(--foreground))]">
        {/* Intro Banner */}
        <div className="p-3 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] flex items-start gap-2.5 shadow-sm">
          <div className="p-2 rounded-lg bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))] shrink-0">
            <Sparkles size={18} />
          </div>
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-[hsl(var(--foreground))]">
              Cálculo Inteligente de Progreso
            </h4>
            <p className="text-2xs text-[hsl(var(--muted-foreground))] mt-0.5">
              Define la regla de cálculo del porcentaje global y el estado del semáforo de salud.
            </p>
          </div>
        </div>

        {/* Mode Selector */}
        <div className="space-y-2">
          <label className="text-2xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
            Modo de Cálculo de Avance
          </label>
          <div className="space-y-2">
            {MODES.map((m) => {
              const Icon = m.icon;
              const isSelected = mode === m.id;
              return (
                <div
                  key={m.id}
                  onClick={() => setMode(m.id)}
                  className={clsx(
                    "p-3 rounded-xl border cursor-pointer transition-all flex items-start gap-3",
                    isSelected
                      ? "border-[hsl(var(--primary))] bg-[hsl(var(--primary))]/5 shadow-sm"
                      : "border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] hover:border-[hsl(var(--border))]/80"
                  )}
                >
                  <div
                    className={clsx(
                      "p-2 rounded-lg shrink-0 mt-0.5",
                      isSelected
                        ? "bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]"
                        : "bg-[hsl(var(--surface-3))] text-[hsl(var(--muted-foreground))]"
                    )}
                  >
                    <Icon size={16} />
                  </div>
                  <div className="flex-1 space-y-0.5">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-[hsl(var(--foreground))]">
                        {m.title}
                      </span>
                      <span className="text-3xs font-black uppercase tracking-wider px-1.5 py-0.5 rounded bg-[hsl(var(--surface-3))] text-[hsl(var(--muted-foreground))]">
                        {m.badge}
                      </span>
                    </div>
                    <p className="text-2xs text-[hsl(var(--muted-foreground))] leading-relaxed">
                      {m.description}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Manual Progress Slider (only when manual is selected) */}
        {mode === "manual" && (
          <div className="p-3.5 rounded-xl border border-[hsl(var(--primary))]/30 bg-[hsl(var(--surface-2))] space-y-2.5 animate-in fade-in duration-200">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-[hsl(var(--foreground))]">
                Porcentaje de Avance Manual
              </span>
              <span className="text-xs font-black text-[hsl(var(--primary))]">
                {Math.round(progressVal)}%
              </span>
            </div>
            <input
              type="range"
              min={0}
              max={100}
              value={progressVal}
              onChange={(e) => setProgressVal(Number(e.target.value))}
              className="w-full accent-[hsl(var(--primary))] cursor-pointer"
            />
            <div className="flex justify-between text-3xs text-[hsl(var(--muted-foreground))]">
              <span>0% Inicio</span>
              <span>50% Mitad</span>
              <span>100% Terminado</span>
            </div>
          </div>
        )}

        {/* Health Override / Semáforo */}
        <div className="space-y-2 pt-1">
          <label className="text-2xs font-bold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
            Semáforo de Salud Operativa
          </label>
          <div className="grid grid-cols-2 gap-2">
            {HEALTH_OPTIONS.map((h) => {
              const isSelected = healthOverride === h.id;
              const Icon = h.icon;
              return (
                <div
                  key={String(h.id)}
                  onClick={() => setHealthOverride(h.id)}
                  className={clsx(
                    "p-2.5 rounded-xl border cursor-pointer transition-all space-y-1",
                    isSelected
                      ? clsx("bg-[hsl(var(--surface-3))]", h.border, "ring-1 ring-[hsl(var(--primary))]")
                      : "border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] hover:border-[hsl(var(--border))]/80"
                  )}
                >
                  <div className="flex items-center gap-1.5">
                    <Icon size={14} className={h.color} />
                    <span className="text-2xs font-bold text-[hsl(var(--foreground))]">
                      {h.label}
                    </span>
                  </div>
                  <p className="text-3xs text-[hsl(var(--muted-foreground))] leading-tight">
                    {h.description}
                  </p>
                </div>
              );
            })}
          </div>
        </div>

        {/* Footer Actions */}
        <div className="mt-auto pt-3 border-t border-[hsl(var(--border))] flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="px-3.5 py-1.5 text-2xs font-bold uppercase tracking-wider rounded-lg border border-[hsl(var(--border))] text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--surface-2))]"
          >
            Cancelar
          </button>
          <button
            type="submit"
            disabled={saving}
            className="px-4 py-1.5 text-2xs font-bold uppercase tracking-wider rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] hover:opacity-90 active:scale-95 transition-all flex items-center gap-1.5 shadow"
          >
            <Save size={13} /> {saving ? "Guardando..." : "Aplicar Cambios"}
          </button>
        </div>
      </form>
    </RightPanel>
  );
}

