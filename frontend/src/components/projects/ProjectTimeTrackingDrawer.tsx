"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { RightPanel } from "@/components/ui/RightPanel";
import ConfirmActionDrawer, { type ConfirmActionState } from "@/components/ConfirmActionDrawer";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { apiFetch } from "@/lib/http";
import type {
  ProjectTimeLog,
  ProjectTimeLogCreate,
  ProjectTimeTrackingSummary,
} from "@/types/projects";
import { Clock, Play, Pause, RotateCcw, CheckCircle2, Trash2, CheckSquare, PieChart, ListFilter, Layers, Save, Plus } from "lucide-react";
import clsx from "clsx";

interface ProjectTimeTrackingDrawerProps {
  projectId: string;
  isOpen: boolean;
  onClose: () => void;
  tasks?: Array<{ id: string; title: string }>;
  onTimeLogged?: () => void;
}

type ActiveTab = "stopwatch" | "manual" | "logs";

export function ProjectTimeTrackingDrawer({
  projectId,
  isOpen,
  onClose,
  tasks = [],
  onTimeLogged,
}: ProjectTimeTrackingDrawerProps) {
  const { token } = useAuth();
  const { addToast } = useToast();

  const [activeTab, setActiveTab] = useState<ActiveTab>("stopwatch");
  const [logs, setLogs] = useState<ProjectTimeLog[]>([]);
  const [summary, setSummary] = useState<ProjectTimeTrackingSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [confirmAction, setConfirmAction] = useState<ConfirmActionState>(null);

  // ── Filtros ──
  const [filterBillable, setFilterBillable] = useState<string>("all");
  const [filterTaskId, setFilterTaskId] = useState<string>("all");

  // ── Formulario Manual ──
  const [manualTaskId, setManualTaskId] = useState<string>("");
  const [manualHours, setManualHours] = useState<string>("1.0");
  const [manualDate, setManualDate] = useState<string>(() => {
    return new Date().toISOString().split("T")[0];
  });
  const [manualDesc, setManualDesc] = useState<string>("");
  const [manualBillable, setManualBillable] = useState<boolean>(true);

  // ── Cronómetro en Vivo (Stopwatch) ──
  const [timerRunning, setTimerRunning] = useState<boolean>(false);
  const [timerSeconds, setTimerSeconds] = useState<number>(0);
  const [timerTaskId, setTimerTaskId] = useState<string>("");
  const [timerDesc, setTimerDesc] = useState<string>("");
  const [timerBillable, setTimerBillable] = useState<boolean>(true);
  const timerIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Cargar datos
  const fetchData = useCallback(async () => {
    if (!projectId || !token || !isOpen) return;
    setLoading(true);
    try {
      const [logsRes, summaryRes] = await Promise.all([
        apiFetch<ProjectTimeLog[]>(`/projects/${projectId}/time-logs`, { token }),
        apiFetch<ProjectTimeTrackingSummary>(`/projects/${projectId}/time-tracking-summary`, { token }),
      ]);
      setLogs(Array.isArray(logsRes) ? logsRes : []);
      setSummary(summaryRes || null);
    } catch {
      addToast("Error al cargar los registros de tiempo", "error");
    } finally {
      setLoading(false);
    }
  }, [projectId, token, isOpen, addToast]);

  useEffect(() => {
    if (isOpen) {
      fetchData();
    }
  }, [isOpen, fetchData]);

  // Manejo de Cronómetro
  useEffect(() => {
    if (timerRunning) {
      timerIntervalRef.current = setInterval(() => {
        setTimerSeconds((prev) => prev + 1);
      }, 1000);
    } else {
      if (timerIntervalRef.current) {
        clearInterval(timerIntervalRef.current);
        timerIntervalRef.current = null;
      }
    }
    return () => {
      if (timerIntervalRef.current) {
        clearInterval(timerIntervalRef.current);
      }
    };
  }, [timerRunning]);

  const handleStartTimer = () => {
    setTimerRunning(true);
  };

  const handlePauseTimer = () => {
    setTimerRunning(false);
  };

  const handleResetTimer = () => {
    setTimerRunning(false);
    setTimerSeconds(0);
  };

  const formatStopwatchTime = (totalSecs: number) => {
    const hours = Math.floor(totalSecs / 3600);
    const minutes = Math.floor((totalSecs % 3600) / 60);
    const seconds = totalSecs % 60;
    return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  };

  // Guardar desde cronómetro
  const handleSaveTimer = async () => {
    if (timerSeconds < 10) {
      addToast("El cronómetro debe acumular al menos 10 segundos para registrar", "warning");
      return;
    }
    setSaving(true);
    try {
      const hoursDecimal = Math.max(0.02, Math.round((timerSeconds / 3600) * 100) / 100);
      const payload: ProjectTimeLogCreate = {
        task_id: timerTaskId || null,
        hours: hoursDecimal,
        description: timerDesc.trim() || "Sesión de cronómetro",
        is_billable: timerBillable,
        date: new Date().toISOString(),
      };

      await apiFetch<ProjectTimeLog>(`/projects/${projectId}/time-logs`, {
        method: "POST",
        token,
        body: JSON.stringify(payload),
      });

      addToast(`Tiempo registrado: ${hoursDecimal} hrs`, "success");
      setTimerRunning(false);
      setTimerSeconds(0);
      setTimerDesc("");
      fetchData();
      onTimeLogged?.();
    } catch {
      addToast("Error al guardar registro del cronómetro", "error");
    } finally {
      setSaving(false);
    }
  };

  // Guardar registro manual
  const handleSaveManual = async (e: React.FormEvent) => {
    e.preventDefault();
    const parsedHours = parseFloat(manualHours);
    if (isNaN(parsedHours) || parsedHours <= 0) {
      addToast("Por favor ingresa un número válido de horas (> 0)", "warning");
      return;
    }

    setSaving(true);
    try {
      const payload: ProjectTimeLogCreate = {
        task_id: manualTaskId || null,
        hours: Math.round(parsedHours * 100) / 100,
        description: manualDesc.trim() || "Trabajo dedicado",
        is_billable: manualBillable,
        date: manualDate ? new Date(`${manualDate}T12:00:00Z`).toISOString() : new Date().toISOString(),
      };

      await apiFetch<ProjectTimeLog>(`/projects/${projectId}/time-logs`, {
        method: "POST",
        token,
        body: JSON.stringify(payload),
      });

      addToast("Registro de tiempo creado con éxito", "success");
      setManualHours("1.0");
      setManualDesc("");
      fetchData();
      onTimeLogged?.();
      setActiveTab("logs");
    } catch {
      addToast("Error al guardar registro manual", "error");
    } finally {
      setSaving(false);
    }
  };

  // Eliminar registro
  const handleDeleteLog = async (logId: string) => {
    try {
      await apiFetch(`/projects/${projectId}/time-logs/${logId}`, {
        method: "DELETE",
        token,
      });
      addToast("Registro de tiempo eliminado", "info");
      await fetchData();
      onTimeLogged?.();
    } catch (error) {
      addToast("Error al eliminar el registro", "error");
      throw error;
    }
  };

  const requestDeleteLog = (log: ProjectTimeLog) => {
    setConfirmAction({
      title: "Eliminar registro de tiempo",
      description: `¿Seguro que deseas eliminar el registro de ${log.hours.toFixed(2)} horas${log.description ? ` (“${log.description}”)` : ""}? Se quitará del total del proyecto.`,
      confirmLabel: "Eliminar",
      destructive: true,
      onConfirm: () => handleDeleteLog(log.id),
    });
  };

  const filteredLogs = logs.filter((l) => {
    if (filterBillable === "billable" && !l.is_billable) return false;
    if (filterBillable === "non_billable" && l.is_billable) return false;
    if (filterTaskId !== "all") {
      if (filterTaskId === "general" && l.task_id) return false;
      if (filterTaskId !== "general" && l.task_id !== filterTaskId) return false;
    }
    return true;
  });

  const billablePercent =
    summary && summary.total_hours > 0
      ? Math.round((summary.billable_hours / summary.total_hours) * 100)
      : 0;

  return (
    <RightPanel
      isOpen={isOpen}
      onClose={onClose}
      title="Registro de Tiempo y Hojas de Horas"
      className="w-full max-w-2xl"
    >
      <div className="flex flex-col gap-5 p-6 text-sm" style={{ color: "hsl(var(--text-primary))" }}>
        {/* KPI CARDS & RESUMEN DE TIEMPO */}
        <div
          className="rounded-xl p-5 border"
          style={{
            backgroundColor: "hsl(var(--surface-1))",
            borderColor: "hsl(var(--border))",
          }}
        >
          <div
            className="flex items-center justify-between pb-3 border-b"
            style={{ borderColor: "hsl(var(--border))" }}
          >
            <div className="flex items-center gap-2">
              <Clock className="w-5 h-5" style={{ color: "hsl(var(--primary))" }} />
              <span className="font-semibold text-base">Hojas de Horas del Proyecto</span>
            </div>
            <div
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold"
              style={{ backgroundColor: "hsl(var(--surface-2))" }}
            >
              <PieChart className="w-3.5 h-3.5" style={{ color: "hsl(var(--success))" }} />
              <span>Facturable: {billablePercent}%</span>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-4">
            <div className="flex flex-col">
              <span className="text-xs" style={{ color: "hsl(var(--text-secondary))" }}>Total Horas</span>
              <span className="text-lg font-bold" style={{ color: "hsl(var(--primary))" }}>
                {(summary?.total_hours ?? 0).toFixed(2)}h
              </span>
            </div>
            <div className="flex flex-col">
              <span className="text-xs" style={{ color: "hsl(var(--text-secondary))" }}>Facturables</span>
              <span className="text-lg font-bold" style={{ color: "hsl(var(--success))" }}>
                {(summary?.billable_hours ?? 0).toFixed(2)}h
              </span>
            </div>
            <div className="flex flex-col">
              <span className="text-xs" style={{ color: "hsl(var(--text-secondary))" }}>No Facturables</span>
              <span className="text-lg font-bold" style={{ color: "hsl(var(--warning))" }}>
                {(summary?.non_billable_hours ?? 0).toFixed(2)}h
              </span>
            </div>
            <div className="flex flex-col">
              <span className="text-xs" style={{ color: "hsl(var(--text-secondary))" }}>Registros</span>
              <span className="text-lg font-bold">
                {summary?.total_logs ?? 0}
              </span>
            </div>
          </div>

          {/* Barra de proporción facturable */}
          <div className="mt-4">
            <div
              className="w-full h-2 rounded-full overflow-hidden"
              style={{ backgroundColor: "hsl(var(--surface-2))" }}
            >
              <div
                className="h-full transition-all duration-300 rounded-full"
                style={{
                  width: `${Math.min(100, Math.max(0, billablePercent))}%`,
                  backgroundColor: "hsl(var(--success))",
                }}
              />
            </div>
          </div>
        </div>

        {/* NAVEGACIÓN POR PESTAÑAS */}
        <div
          className="flex items-center gap-1 p-1 rounded-xl border"
          style={{
            backgroundColor: "hsl(var(--surface-2))",
            borderColor: "hsl(var(--border))",
          }}
        >
          <button
            type="button"
            onClick={() => setActiveTab("stopwatch")}
            className={clsx(
              "flex-1 py-2 px-3 rounded-lg text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2 transition-all",
              activeTab === "stopwatch"
                ? "shadow-sm"
                : "opacity-75 hover:opacity-100"
            )}
            style={{
              backgroundColor: activeTab === "stopwatch" ? "hsl(var(--surface-1))" : "transparent",
              color: activeTab === "stopwatch" ? "hsl(var(--primary))" : "hsl(var(--text-secondary))",
            }}
          >
            <Clock className="w-4 h-4" />
            Cronómetro
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("manual")}
            className={clsx(
              "flex-1 py-2 px-3 rounded-lg text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2 transition-all",
              activeTab === "manual"
                ? "shadow-sm"
                : "opacity-75 hover:opacity-100"
            )}
            style={{
              backgroundColor: activeTab === "manual" ? "hsl(var(--surface-1))" : "transparent",
              color: activeTab === "manual" ? "hsl(var(--primary))" : "hsl(var(--text-secondary))",
            }}
          >
            <Plus className="w-4 h-4" />
            Entrada Manual
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("logs")}
            className={clsx(
              "flex-1 py-2 px-3 rounded-lg text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2 transition-all",
              activeTab === "logs"
                ? "shadow-sm"
                : "opacity-75 hover:opacity-100"
            )}
            style={{
              backgroundColor: activeTab === "logs" ? "hsl(var(--surface-1))" : "transparent",
              color: activeTab === "logs" ? "hsl(var(--primary))" : "hsl(var(--text-secondary))",
            }}
          >
            <Layers className="w-4 h-4" />
            Historial ({logs.length})
          </button>
        </div>

        {/* TAB 1: CRONÓMETRO EN VIVO */}
        {activeTab === "stopwatch" && (
          <div
            className="flex flex-col items-center gap-5 p-6 rounded-xl border text-center"
            style={{
              backgroundColor: "hsl(var(--surface-1))",
              borderColor: "hsl(var(--border))",
            }}
          >
            <div className="flex items-center gap-2">
              <span
                className={clsx(
                  "w-2.5 h-2.5 rounded-full",
                  timerRunning ? "animate-pulse" : ""
                )}
                style={{
                  backgroundColor: timerRunning
                    ? "hsl(var(--success))"
                    : timerSeconds > 0
                    ? "hsl(var(--warning))"
                    : "hsl(var(--text-secondary))",
                }}
              />
              <span className="text-xs uppercase font-bold tracking-widest" style={{ color: "hsl(var(--text-secondary))" }}>
                {timerRunning ? "Registrando tiempo activo" : timerSeconds > 0 ? "Pausa" : "Listo para iniciar"}
              </span>
            </div>

            {/* Contador Digital Grande */}
            <div
              className="text-5xl sm:text-6xl font-black font-mono tracking-widest py-3 px-6 rounded-2xl border select-none"
              style={{
                backgroundColor: "hsl(var(--surface-2))",
                borderColor: "hsl(var(--border))",
                color: timerRunning ? "hsl(var(--primary))" : "hsl(var(--foreground))",
              }}
            >
              {formatStopwatchTime(timerSeconds)}
            </div>

            {/* Botones de Control del Cronómetro */}
            <div className="flex items-center gap-3">
              {!timerRunning ? (
                <button
                  type="button"
                  onClick={handleStartTimer}
                  className="px-6 py-2.5 rounded-xl font-bold flex items-center gap-2 transition-all shadow-md active:scale-95"
                  style={{
                    backgroundColor: "hsl(var(--primary))",
                    color: "hsl(var(--primary-foreground))",
                  }}
                >
                  <Play className="w-5 h-5 fill-current" />
                  Iniciar
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handlePauseTimer}
                  className="px-6 py-2.5 rounded-xl font-bold flex items-center gap-2 transition-all shadow-md active:scale-95"
                  style={{
                    backgroundColor: "hsl(var(--warning))",
                    color: "hsl(var(--foreground))",
                  }}
                >
                  <Pause className="w-5 h-5 fill-current" />
                  Pausar
                </button>
              )}

              <button
                type="button"
                onClick={handleResetTimer}
                disabled={timerSeconds === 0}
                className="p-2.5 rounded-xl border transition-all active:scale-95 disabled:opacity-40"
                style={{
                  backgroundColor: "hsl(var(--surface-2))",
                  borderColor: "hsl(var(--border))",
                  color: "hsl(var(--text-secondary))",
                }}
                title="Reiniciar a 0"
              >
                <RotateCcw className="w-5 h-5" />
              </button>

              <button
                type="button"
                onClick={handleSaveTimer}
                disabled={timerSeconds < 10 || saving}
                className="px-5 py-2.5 rounded-xl font-bold flex items-center gap-2 transition-all shadow-md active:scale-95 disabled:opacity-40"
                style={{
                  backgroundColor: "hsl(var(--success))",
                  color: "hsl(var(--foreground))",
                }}
              >
                <CheckCircle2 className="w-5 h-5" />
                Guardar Tiempo
              </button>
            </div>

            {/* Metadatos asociados al cronómetro */}
            <div
              className="w-full text-left space-y-3 pt-4 mt-2 border-t"
              style={{ borderColor: "hsl(var(--border))" }}
            >
              <div>
                <label className="block text-xs font-semibold mb-1" style={{ color: "hsl(var(--text-secondary))" }}>
                  Tarea Asociada (opcional)
                </label>
                <select
                  value={timerTaskId}
                  onChange={(e) => setTimerTaskId(e.target.value)}
                  className="w-full py-2 px-3 rounded-lg border text-sm"
                  style={{
                    backgroundColor: "hsl(var(--surface-2))",
                    borderColor: "hsl(var(--border))",
                    color: "hsl(var(--foreground))",
                  }}
                >
                  <option value="">General del Proyecto (sin tarea específica)</option>
                  {tasks.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.title}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold mb-1" style={{ color: "hsl(var(--text-secondary))" }}>
                  Descripción de la Actividad
                </label>
                <input
                  type="text"
                  placeholder="¿En qué estás trabajando?"
                  value={timerDesc}
                  onChange={(e) => setTimerDesc(e.target.value)}
                  className="w-full py-2 px-3 rounded-lg border text-sm"
                  style={{
                    backgroundColor: "hsl(var(--surface-2))",
                    borderColor: "hsl(var(--border))",
                    color: "hsl(var(--foreground))",
                  }}
                />
              </div>

              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="timer-billable"
                  checked={timerBillable}
                  onChange={(e) => setTimerBillable(e.target.checked)}
                  className="rounded cursor-pointer"
                  style={{ accentColor: "hsl(var(--primary))" }}
                />
                <label htmlFor="timer-billable" className="text-xs font-medium cursor-pointer">
                  Marcar tiempo como facturable
                </label>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: ENTRADA MANUAL */}
        {activeTab === "manual" && (
          <form
            onSubmit={handleSaveManual}
            className="flex flex-col gap-4 p-5 rounded-xl border"
            style={{
              backgroundColor: "hsl(var(--surface-1))",
              borderColor: "hsl(var(--border))",
            }}
          >
            <div className="flex items-center gap-2 pb-2 border-b" style={{ borderColor: "hsl(var(--border))" }}>
              <Plus className="w-4 h-4" style={{ color: "hsl(var(--primary))" }} />
              <span className="font-semibold text-sm">Registrar Horas Dedicadas Manualmente</span>
            </div>

            <div>
              <label className="block text-xs font-semibold mb-1" style={{ color: "hsl(var(--text-secondary))" }}>
                Tarea Asociada
              </label>
              <select
                value={manualTaskId}
                onChange={(e) => setManualTaskId(e.target.value)}
                className="w-full py-2 px-3 rounded-lg border text-sm"
                style={{
                  backgroundColor: "hsl(var(--surface-2))",
                  borderColor: "hsl(var(--border))",
                  color: "hsl(var(--foreground))",
                }}
              >
                <option value="">General del Proyecto (sin tarea específica)</option>
                {tasks.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.title}
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold mb-1" style={{ color: "hsl(var(--text-secondary))" }}>
                  Horas Dedicadas * (ej. 1.5)
                </label>
                <input
                  type="number"
                  step="0.25"
                  min="0.1"
                  required
                  value={manualHours}
                  onChange={(e) => setManualHours(e.target.value)}
                  className="w-full py-2 px-3 rounded-lg border text-sm"
                  style={{
                    backgroundColor: "hsl(var(--surface-2))",
                    borderColor: "hsl(var(--border))",
                    color: "hsl(var(--foreground))",
                  }}
                />
              </div>

              <div>
                <label className="block text-xs font-semibold mb-1" style={{ color: "hsl(var(--text-secondary))" }}>
                  Fecha de Ejecución *
                </label>
                <input
                  type="date"
                  required
                  value={manualDate}
                  onChange={(e) => setManualDate(e.target.value)}
                  className="w-full py-2 px-3 rounded-lg border text-sm"
                  style={{
                    backgroundColor: "hsl(var(--surface-2))",
                    borderColor: "hsl(var(--border))",
                    color: "hsl(var(--foreground))",
                  }}
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold mb-1" style={{ color: "hsl(var(--text-secondary))" }}>
                Descripción del Trabajo Realizado
              </label>
              <textarea
                rows={3}
                placeholder="Detalle de actividades, avances o entregables..."
                value={manualDesc}
                onChange={(e) => setManualDesc(e.target.value)}
                className="w-full py-2 px-3 rounded-lg border text-sm"
                style={{
                  backgroundColor: "hsl(var(--surface-2))",
                  borderColor: "hsl(var(--border))",
                  color: "hsl(var(--foreground))",
                }}
              />
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="manual-billable"
                checked={manualBillable}
                onChange={(e) => setManualBillable(e.target.checked)}
                className="rounded cursor-pointer"
                style={{ accentColor: "hsl(var(--primary))" }}
              />
              <label htmlFor="manual-billable" className="text-xs font-medium cursor-pointer">
                Marcar tiempo como facturable
              </label>
            </div>

            <button
              type="submit"
              disabled={saving}
              className="mt-2 py-2.5 px-4 rounded-xl font-bold flex items-center justify-center gap-2 transition-all shadow-md active:scale-95 disabled:opacity-50"
              style={{
                backgroundColor: "hsl(var(--primary))",
                color: "hsl(var(--primary-foreground))",
              }}
            >
              <Save className="w-4 h-4" />
              {saving ? "Guardando..." : "Guardar Entrada de Tiempo"}
            </button>
          </form>
        )}

        {/* TAB 3: HISTORIAL & DESGLOSE */}
        {activeTab === "logs" && (
          <div className="flex flex-col gap-4">
            {/* DESGLOSE POR MIEMBROS Y TAREAS */}
            {summary && (summary.by_member.length > 0 || summary.by_task.length > 0) && (
              <div
                className="p-4 rounded-xl border space-y-3"
                style={{
                  backgroundColor: "hsl(var(--surface-1))",
                  borderColor: "hsl(var(--border))",
                }}
              >
                <span className="text-xs font-bold uppercase tracking-wider block" style={{ color: "hsl(var(--text-secondary))" }}>
                  Distribución de Horas por Colaborador
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  {summary.by_member.map((m) => (
                    <div
                      key={m.persona_id}
                      className="p-2.5 rounded-lg border text-xs space-y-1.5"
                      style={{
                        backgroundColor: "hsl(var(--surface-2))",
                        borderColor: "hsl(var(--border))",
                      }}
                    >
                      <div className="flex items-center justify-between font-bold">
                        <span className="truncate max-w-[140px]">{m.persona_name}</span>
                        <span style={{ color: "hsl(var(--primary))" }}>{m.total_hours.toFixed(2)}h</span>
                      </div>
                      <div
                        className="h-1.5 w-full rounded-full overflow-hidden"
                        style={{ backgroundColor: "hsl(var(--surface-1))" }}
                      >
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${Math.min(100, (m.total_hours / (summary.total_hours || 1)) * 100)}%`,
                            backgroundColor: "hsl(var(--primary))",
                          }}
                        />
                      </div>
                      <div className="flex justify-between text-3xs" style={{ color: "hsl(var(--text-secondary))" }}>
                        <span>{m.logs_count} registro(s)</span>
                        <span style={{ color: "hsl(var(--success))" }}>{m.billable_hours.toFixed(2)}h fact.</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* FILTROS DEL HISTORIAL */}
            <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
              <div className="flex items-center gap-2">
                <ListFilter className="w-4 h-4" style={{ color: "hsl(var(--text-secondary))" }} />
                <select
                  value={filterBillable}
                  onChange={(e) => setFilterBillable(e.target.value)}
                  className="py-1 px-2.5 rounded-lg border text-xs"
                  style={{
                    backgroundColor: "hsl(var(--surface-2))",
                    borderColor: "hsl(var(--border))",
                    color: "hsl(var(--foreground))",
                  }}
                >
                  <option value="all">Todas las horas</option>
                  <option value="billable">Solo Facturables</option>
                  <option value="non_billable">No Facturables</option>
                </select>

                <select
                  value={filterTaskId}
                  onChange={(e) => setFilterTaskId(e.target.value)}
                  className="py-1 px-2.5 rounded-lg border text-xs max-w-[180px] truncate"
                  style={{
                    backgroundColor: "hsl(var(--surface-2))",
                    borderColor: "hsl(var(--border))",
                    color: "hsl(var(--foreground))",
                  }}
                >
                  <option value="all">Todas las tareas</option>
                  <option value="general">General del Proyecto</option>
                  {tasks.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.title}
                    </option>
                  ))}
                </select>
              </div>

              <span className="text-xs" style={{ color: "hsl(var(--text-secondary))" }}>
                Mostrando {filteredLogs.length} de {logs.length}
              </span>
            </div>

            {/* LISTA DE REGISTROS */}
            {loading ? (
              <div className="py-8 text-center text-xs" style={{ color: "hsl(var(--text-secondary))" }}>
                Cargando registros de tiempo...
              </div>
            ) : filteredLogs.length === 0 ? (
              <div
                className="py-10 text-center rounded-xl border text-xs space-y-2"
                style={{
                  backgroundColor: "hsl(var(--surface-1))",
                  borderColor: "hsl(var(--border))",
                  color: "hsl(var(--text-secondary))",
                }}
              >
                <Clock className="w-8 h-8 mx-auto opacity-40" />
                <p className="font-semibold">No se encontraron registros de tiempo</p>
                <p className="text-3xs">Usa el cronómetro o la entrada manual para registrar horas.</p>
              </div>
            ) : (
              <div className="flex flex-col gap-2.5">
                {filteredLogs.map((log) => (
                  <div
                    key={log.id}
                    className="p-3.5 rounded-xl border flex items-center justify-between gap-3 transition-all hover:shadow-sm"
                    style={{
                      backgroundColor: "hsl(var(--surface-1))",
                      borderColor: "hsl(var(--border))",
                    }}
                  >
                    <div className="flex flex-col gap-1 min-w-0 flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-bold text-xs" style={{ color: "hsl(var(--foreground))" }}>
                          {log.persona_name || "Colaborador"}
                        </span>
                        <span
                          className="px-2 py-0.5 rounded text-3xs font-semibold"
                          style={{
                            backgroundColor: log.is_billable
                              ? "hsl(var(--success) / 0.15)"
                              : "hsl(var(--surface-2))",
                            color: log.is_billable
                              ? "hsl(var(--success))"
                              : "hsl(var(--text-secondary))",
                          }}
                        >
                          {log.is_billable ? "Facturable" : "No Facturable"}
                        </span>
                        <span className="text-3xs" style={{ color: "hsl(var(--text-secondary))" }}>
                          {log.date ? new Date(log.date).toLocaleDateString("es-CO") : ""}
                        </span>
                      </div>

                      <p className="text-xs truncate" style={{ color: "hsl(var(--foreground))" }}>
                        {log.description || "Sin descripción"}
                      </p>

                      <div className="flex items-center gap-1.5 text-3xs" style={{ color: "hsl(var(--text-secondary))" }}>
                        <CheckSquare className="w-3 h-3" />
                        <span className="truncate">{log.task_title || "General del Proyecto"}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      <span
                        className="text-sm font-black font-mono px-2 py-1 rounded-md"
                        style={{
                          backgroundColor: "hsl(var(--surface-2))",
                          color: "hsl(var(--primary))",
                        }}
                      >
                        {log.hours.toFixed(2)}h
                      </span>

                      <button
                        type="button"
                        onClick={() => requestDeleteLog(log)}
                        className="p-1.5 rounded-lg border transition-all hover:opacity-100 opacity-60"
                        style={{
                          borderColor: "hsl(var(--border))",
                          color: "hsl(var(--destructive))",
                        }}
                        title="Eliminar registro"
                        aria-label={`Eliminar registro de ${log.hours.toFixed(2)} horas${log.description ? `: ${log.description}` : ""}`}
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
      <ConfirmActionDrawer action={confirmAction} onClose={() => setConfirmAction(null)} />
    </RightPanel>
  );
}
