"use client";

import React, { useState, useEffect, useCallback } from "react";
import { RightPanel } from "@/components/ui/RightPanel";
import ConfirmActionDrawer, { type ConfirmActionState } from "@/components/ConfirmActionDrawer";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";
import { apiFetch } from "@/lib/http";
import type {
  ProjectAutomationRule,
  ProjectAutomationRuleCreate,
  AutomationExecutionResult,
  ProjectTaskRecord,
} from "@/types/projects";
import { Zap, Play, Plus, Trash2, CheckCircle2, Clock, Filter, Check, RotateCw, Bell, ListPlus, ArrowRightCircle, AlertCircle, Power, Activity } from "lucide-react";
import clsx from "clsx";
import { TASK_TITLE_MAX_LENGTH } from "@/lib/projects/constants";

interface ProjectAutomationsDrawerProps {
  projectId: string;
  isOpen: boolean;
  onClose: () => void;
  tasks?: ProjectTaskRecord[];
}

const TRIGGER_OPTIONS = [
  {
    id: "task_completed",
    label: "Tarea completada",
    description: "Se dispara cuando cualquier tarea pasa a estado completado.",
    icon: CheckCircle2,
  },
  {
    id: "task_created",
    label: "Tarea creada",
    description: "Se dispara inmediatamente al registrarse una nueva tarea.",
    icon: Plus,
  },
  {
    id: "status_changed",
    label: "Cambio de estado",
    description: "Se dispara ante cualquier transición de estado kanban.",
    icon: RotateCw,
  },
  {
    id: "priority_changed",
    label: "Cambio de prioridad",
    description: "Se dispara cuando se escala la prioridad de una tarea.",
    icon: AlertCircle,
  },
];

const ACTION_OPTIONS = [
  {
    id: "notify_assignee",
    label: "Notificar y registrar bitácora",
    description: "Emite una alerta ministerial y registra el evento en la bitácora.",
    icon: Bell,
  },
  {
    id: "create_followup_task",
    label: "Crear tarea de seguimiento",
    description: "Genera automáticamente una nueva tarea dependiente o de revisión.",
    icon: ListPlus,
  },
  {
    id: "change_phase",
    label: "Mover tarea a otra fase",
    description: "Desplaza la tarea de nodo kanban automáticamente.",
    icon: ArrowRightCircle,
  },
  {
    id: "set_priority",
    label: "Escalar prioridad a Urgente",
    description: "Aumenta automáticamente el nivel de prioridad de la tarea.",
    icon: Zap,
  },
];

export function ProjectAutomationsDrawer({
  projectId,
  isOpen,
  onClose,
  tasks = [],
}: ProjectAutomationsDrawerProps) {
  const { token } = useAuth();
  const { addToast } = useToast();

  const [activeTab, setActiveTab] = useState<"rules" | "builder" | "test">("rules");
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [rules, setRules] = useState<ProjectAutomationRule[]>([]);
  const [testingRuleId, setTestingRuleId] = useState<string | null>(null);
  const [lastTestResults, setLastTestResults] = useState<AutomationExecutionResult[]>([]);
  const [confirmAction, setConfirmAction] = useState<ConfirmActionState>(null);

  // Form State para Builder
  const [ruleName, setRuleName] = useState("");
  const [ruleDescription, setRuleDescription] = useState("");
  const [selectedTrigger, setSelectedTrigger] = useState("task_completed");
  const [conditionPriority, setConditionPriority] = useState("all");
  const [conditionStatus, setConditionStatus] = useState("all");
  const [selectedAction, setSelectedAction] = useState("notify_assignee");
  const [followupTitle, setFollowupTitle] = useState("");
  const [followupDuration, setFollowupDuration] = useState("3");
  const [targetPhaseName, setTargetPhaseName] = useState("Revisión");

  const loadRules = useCallback(async () => {
    if (!token || !projectId) return;
    setLoading(true);
    setLoadError(null);
    try {
      const data = await apiFetch<ProjectAutomationRule[]>(
        `/projects/${projectId}/automations`,
        { token }
      );
      if (Array.isArray(data)) {
        setRules(data);
      }
    } catch {
      setLoadError("No se pudieron cargar las reglas de automatización.");
      addToast({
        title: "Error de conexión",
        message: "No se pudieron cargar las reglas de automatización.",
        type: "error",
      });
    } finally {
      setLoading(false);
    }
  }, [token, projectId, addToast]);

  useEffect(() => {
    if (isOpen) {
      loadRules();
    }
  }, [isOpen, loadRules]);

  const handleToggleActive = async (rule: ProjectAutomationRule) => {
    if (!token) return;
    const nextState = !rule.is_active;
    try {
      await apiFetch<ProjectAutomationRule>(
        `/projects/${projectId}/automations/${rule.id}`,
        {
          token,
          method: "PATCH",
          body: JSON.stringify({ is_active: nextState }),
        }
      );
      setRules((prev) =>
        prev.map((r) => (r.id === rule.id ? { ...r, is_active: nextState } : r))
      );
      addToast({
        title: nextState ? "Automatización activada" : "Automatización pausada",
        message: `La regla '${rule.name}' ahora está ${nextState ? "activa" : "inactiva"}.`,
        type: "info",
      });
    } catch {
      addToast({
        title: "Error al actualizar",
        message: "No se pudo cambiar el estado de la automatización.",
        type: "error",
      });
    }
  };

  const confirmDeleteRule = async (ruleId: string) => {
    if (!token) throw new Error("Debes iniciar sesión para eliminar la regla.");
    try {
      await apiFetch(`/projects/${projectId}/automations/${ruleId}`, {
        token,
        method: "DELETE",
      });
      setRules((prev) => prev.filter((r) => r.id !== ruleId));
      addToast({
        title: "Regla eliminada",
        message: "La automatización se eliminó correctamente.",
        type: "success",
      });
    } catch {
      addToast({
        title: "Error al eliminar",
        message: "No se pudo eliminar la regla.",
        type: "error",
      });
      throw new Error("No se pudo eliminar la regla de automatización.");
    }
  };

  const handleDeleteRule = (rule: ProjectAutomationRule) => {
    setConfirmAction({
      title: "Eliminar automatización",
      description: `¿Seguro que deseas eliminar “${rule.name}”? La regla dejará de ejecutarse.`,
      confirmLabel: "Eliminar",
      destructive: true,
      onConfirm: () => confirmDeleteRule(rule.id),
    });
  };

  const handleCreateRule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !ruleName.trim()) {
      addToast({
        title: "Campo requerido",
        message: "Por favor asigna un nombre descriptivo a la automatización.",
        type: "warning",
      });
      return;
    }

    setSubmitting(true);
    const conditionData: Record<string, string> = {};
    if (conditionPriority !== "all") conditionData.priority = conditionPriority;
    if (conditionStatus !== "all") conditionData.status = conditionStatus;

    const actionData: Record<string, unknown> = {};
    if (selectedAction === "create_followup_task") {
      actionData.title = followupTitle.trim() || `Seguimiento: ${ruleName}`;
      actionData.duration_days = parseInt(followupDuration, 10) || 3;
      actionData.priority = "medium";
    } else if (selectedAction === "change_phase") {
      actionData.phase_name = targetPhaseName.trim();
    } else if (selectedAction === "set_priority") {
      actionData.priority = "urgent";
    }

    const payload: ProjectAutomationRuleCreate = {
      project_id: projectId,
      name: ruleName.trim(),
      description: ruleDescription.trim() || null,
      trigger_event: selectedTrigger,
      condition_data: conditionData,
      action_type: selectedAction,
      action_data: actionData,
      is_active: true,
    };

    try {
      const created = await apiFetch<ProjectAutomationRule>(
        `/projects/${projectId}/automations`,
        {
          token,
          method: "POST",
          body: JSON.stringify(payload),
        }
      );
      setRules((prev) => [created, ...prev]);
      addToast({
        title: "Automatización creada",
        message: `Regla '${created.name}' guardada y activa.`,
        type: "success",
      });
      // Limpiar formulario y cambiar a lista
      setRuleName("");
      setRuleDescription("");
      setFollowupTitle("");
      setActiveTab("rules");
    } catch {
      addToast({
        title: "Error al crear",
        message: "No se pudo guardar la regla de automatización.",
        type: "error",
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleTestEvaluate = async (triggerEvent: string) => {
    if (!token) return;
    setTestingRuleId("evaluating");
    try {
      const sampleTask = tasks[0];
      const results = await apiFetch<AutomationExecutionResult[]>(
        `/projects/${projectId}/automations/evaluate`,
        {
          token,
          method: "POST",
          body: JSON.stringify({
            trigger_event: triggerEvent,
            task_id: sampleTask ? sampleTask.id : null,
            dry_run: true,
            context_data: {
              task_title: sampleTask ? sampleTask.title : "Tarea de Prueba",
              priority: sampleTask ? sampleTask.priority : "high",
              status: sampleTask ? sampleTask.status : "completed",
            },
          }),
        }
      );
      setLastTestResults(results);
      addToast({
        title: "Vista previa completada",
        message: `Se previsualizaron ${results.length} reglas activas; no se guardaron cambios.`,
        type: "info",
      });
    } catch {
      addToast({
        title: "Error en prueba",
        message: "No se pudieron ejecutar las reglas para este disparador.",
        type: "error",
      });
    } finally {
      setTestingRuleId(null);
    }
  };

  return (
    <>
    <RightPanel
      isOpen={isOpen}
      onClose={onClose}
      title="Motor de Automatizaciones"
      subtitle="Disparadores reactivos, reglas de flujo y acciones automáticas"
      width="w-full md:w-[650px]"
    >
      <div className="flex flex-col h-full space-y-4">
        {/* Navigation Tabs */}
        <div className="flex items-center gap-1 border-b border-[hsl(var(--border))] pb-2">
          <button
            onClick={() => setActiveTab("rules")}
            className={clsx(
              "px-3 py-1.5 rounded-md text-xs font-bold transition-all flex items-center gap-1.5",
              activeTab === "rules"
                ? "bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] shadow-sm"
                : "text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] hover:text-[hsl(var(--text-primary))]"
            )}
          >
            <Zap size={14} />
            <span>Reglas ({rules.length})</span>
          </button>

          <button
            onClick={() => setActiveTab("builder")}
            className={clsx(
              "px-3 py-1.5 rounded-md text-xs font-bold transition-all flex items-center gap-1.5",
              activeTab === "builder"
                ? "bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] shadow-sm"
                : "text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] hover:text-[hsl(var(--text-primary))]"
            )}
          >
            <Plus size={14} />
            <span>Nueva Regla</span>
          </button>

          <button
            onClick={() => setActiveTab("test")}
            className={clsx(
              "px-3 py-1.5 rounded-md text-xs font-bold transition-all flex items-center gap-1.5",
              activeTab === "test"
                ? "bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] shadow-sm"
                : "text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] hover:text-[hsl(var(--text-primary))]"
            )}
          >
            <Play size={14} />
            <span>Vista previa</span>
          </button>
        </div>

        <div
          role="status"
          className="flex items-start gap-2 rounded-md border border-[hsl(var(--warning))]/40 bg-[hsl(var(--warning))]/10 p-3 text-xs text-[hsl(var(--text-primary))]"
        >
          <AlertCircle size={16} className="mt-0.5 shrink-0 text-[hsl(var(--warning))]" aria-hidden="true" />
          <p>
            Las reglas se guardan, pero los cambios de tareas todavía no disparan su ejecución automática.
            La pestaña «Vista previa» solo simula resultados y no aplica acciones.
          </p>
        </div>

        {/* Tab 1: Rules List */}
        {activeTab === "rules" && (
          <div className="flex-1 overflow-y-auto space-y-3 pr-1">
            {loading ? (
              <div className="p-8 text-center space-y-2">
                <RotateCw className="animate-spin mx-auto text-[hsl(var(--primary))]" size={24} />
                <p className="text-xs text-[hsl(var(--text-secondary))] font-medium">
                  Cargando automatizaciones del proyecto...
                </p>
              </div>
            ) : loadError && rules.length === 0 ? (
              <div role="alert" className="p-8 text-center bg-[hsl(var(--surface-1))] rounded-lg border border-[hsl(var(--border))] space-y-3">
                <AlertCircle size={24} className="mx-auto text-[hsl(var(--destructive))]" />
                <h4 className="text-sm font-bold text-[hsl(var(--text-primary))]">No se cargaron las automatizaciones</h4>
                <p className="text-xs text-[hsl(var(--text-secondary))]">{loadError}</p>
                <button
                  type="button"
                  onClick={loadRules}
                  className="px-3 py-1.5 rounded-md bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] text-xs font-bold"
                >
                  Reintentar
                </button>
              </div>
            ) : rules.length === 0 ? (
              <div className="p-8 text-center bg-[hsl(var(--surface-1))] rounded-lg border border-[hsl(var(--border))] space-y-3">
                <div className="size-10 rounded-full bg-[hsl(var(--surface-2))] flex items-center justify-center mx-auto text-[hsl(var(--text-secondary))]">
                  <Zap size={20} />
                </div>
                <div>
                  <h4 className="text-sm font-bold text-[hsl(var(--text-primary))]">Sin automatizaciones configuradas</h4>
                  <p className="text-xs text-[hsl(var(--text-secondary))] mt-1 max-w-sm mx-auto">
                    Crea reglas reactivas para mover tareas, crear tareas de seguimiento o notificar responsables automáticamente.
                  </p>
                </div>
                <button
                  onClick={() => setActiveTab("builder")}
                  className="px-3 py-1.5 rounded-md bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] text-xs font-bold inline-flex items-center gap-1.5 shadow-sm hover:opacity-90 transition-all"
                >
                  <Plus size={14} />
                  <span>Crear primera regla</span>
                </button>
              </div>
            ) : (
              <>
              {loadError && (
                <div role="alert" className="flex items-center justify-between gap-3 rounded-md border border-[hsl(var(--destructive))]/30 bg-[hsl(var(--destructive))]/5 p-3 text-xs text-[hsl(var(--danger-text))]">
                  <span>{loadError} Se muestran las reglas cargadas anteriormente.</span>
                  <button type="button" onClick={loadRules} className="font-semibold text-[hsl(var(--primary))]">Reintentar</button>
                </div>
              )}
              {rules.map((rule) => {
                const triggerObj = TRIGGER_OPTIONS.find((t) => t.id === rule.trigger_event);
                const actionObj = ACTION_OPTIONS.find((a) => a.id === rule.action_type);
                const TriggerIcon = triggerObj ? triggerObj.icon : Zap;
                const ActionIcon = actionObj ? actionObj.icon : ArrowRightCircle;

                return (
                  <div
                    key={rule.id}
                    className={clsx(
                      "p-3 rounded-lg border transition-all space-y-3",
                      rule.is_active
                        ? "bg-[hsl(var(--surface-1))] border-[hsl(var(--border))] shadow-sm"
                        : "bg-[hsl(var(--surface-2))]/50 border-[hsl(var(--border))]/60 opacity-75"
                    )}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <div
                          className={clsx(
                            "size-8 rounded-md flex items-center justify-center text-[hsl(var(--primary-foreground))]",
                            rule.is_active ? "bg-[hsl(var(--primary))]" : "bg-[hsl(var(--text-secondary))]"
                          )}
                        >
                          <Zap size={16} />
                        </div>
                        <div>
                          <h4 className="text-xs font-bold text-[hsl(var(--text-primary))] leading-tight">
                            {rule.name}
                          </h4>
                          {rule.description && (
                            <p className="text-3xs text-[hsl(var(--text-secondary))] mt-0.5 line-clamp-1">
                              {rule.description}
                            </p>
                          )}
                        </div>
                      </div>

                      <div className="flex items-center gap-1.5">
                        <button
                          onClick={() => handleToggleActive(rule)}
                          className={clsx(
                            "px-2 py-0.5 rounded text-3xs font-bold uppercase transition-all flex items-center gap-1 border",
                            rule.is_active
                              ? "bg-[hsl(var(--success))]/10 border-[hsl(var(--success))]/30 text-[hsl(var(--success))]"
                              : "bg-[hsl(var(--surface-2))] border-[hsl(var(--border))] text-[hsl(var(--text-secondary))]"
                          )}
                          title={rule.is_active ? "Desactivar regla" : "Activar regla"}
                        >
                          <Power size={10} />
                          <span>{rule.is_active ? "Activa" : "Pausada"}</span>
                        </button>

                        <button
                          onClick={() => handleDeleteRule(rule)}
                          className="p-1 rounded text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--destructive))] transition-colors"
                          title="Eliminar regla"
                          aria-label={`Eliminar regla ${rule.name}`}
                        >
                          <Trash2 size={13} />
                        </button>
                      </div>
                    </div>

                    {/* Diagrama de flujo visual: Cuando -> Si -> Ejecutar */}
                    <div className="p-2 rounded-md bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] grid grid-cols-1 md:grid-cols-3 gap-2 text-2xs">
                      <div className="flex items-center gap-1.5 min-w-0">
                        <div className="p-1 rounded bg-[hsl(var(--surface-3))] text-[hsl(var(--primary))] shrink-0">
                          <TriggerIcon size={12} />
                        </div>
                        <div className="min-w-0">
                          <span className="block text-3xs font-bold uppercase text-[hsl(var(--text-secondary))]">Cuando</span>
                          <span className="font-semibold text-[hsl(var(--text-primary))] truncate block">
                            {triggerObj ? triggerObj.label : rule.trigger_event}
                          </span>
                        </div>
                      </div>

                      <div className="flex items-center gap-1.5 min-w-0 border-t md:border-t-0 md:border-l border-[hsl(var(--border))] pt-1 md:pt-0 md:pl-2">
                        <div className="p-1 rounded bg-[hsl(var(--surface-3))] text-[hsl(var(--warning))] shrink-0">
                          <Filter size={12} />
                        </div>
                        <div className="min-w-0">
                          <span className="block text-3xs font-bold uppercase text-[hsl(var(--text-secondary))]">Si cumple</span>
                          <span className="font-semibold text-[hsl(var(--text-primary))] truncate block">
                            {Object.keys(rule.condition_data || {}).length > 0
                              ? Object.entries(rule.condition_data).map(([k, v]) => `${k}:${String(v)}`).join(", ")
                              : "Sin condición previa"}
                          </span>
                        </div>
                      </div>

                      <div className="flex items-center gap-1.5 min-w-0 border-t md:border-t-0 md:border-l border-[hsl(var(--border))] pt-1 md:pt-0 md:pl-2">
                        <div className="p-1 rounded bg-[hsl(var(--surface-3))] text-[hsl(var(--success))] shrink-0">
                          <ActionIcon size={12} />
                        </div>
                        <div className="min-w-0">
                          <span className="block text-3xs font-bold uppercase text-[hsl(var(--text-secondary))]">Ejecutar</span>
                          <span className="font-semibold text-[hsl(var(--text-primary))] truncate block">
                            {actionObj ? actionObj.label : rule.action_type}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Metadata & Ejecuciones */}
                    <div className="flex items-center justify-between text-3xs text-[hsl(var(--text-secondary))] pt-1 border-t border-[hsl(var(--border))]/60">
                      <div className="flex items-center gap-3">
                        <span className="flex items-center gap-1">
                          <Activity size={10} />
                          {rule.execution_count} ejecuciones
                        </span>
                        {rule.last_triggered_at && (
                          <span className="flex items-center gap-1">
                            <Clock size={10} />
                            Última: {new Date(rule.last_triggered_at).toLocaleDateString()}
                          </span>
                        )}
                      </div>
                      <span className="italic">Por: {rule.creator_name || "Sistema"}</span>
                    </div>
                  </div>
                );
              })}
              </>
            )}
          </div>
        )}

        {/* Tab 2: Visual Rule Builder */}
        {activeTab === "builder" && (
          <form onSubmit={handleCreateRule} className="flex-1 overflow-y-auto space-y-4 pr-1">
            <div className="space-y-1">
              <label htmlFor="automation-rule-name" className="text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                Nombre de la regla *
              </label>
              <input
                type="text"
                id="automation-rule-name"
                value={ruleName}
                onChange={(e) => setRuleName(e.target.value)}
                placeholder="Ej: Auto-crear revisión al completar tareas críticas"
                className="w-full px-3 py-1.5 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-xs text-[hsl(var(--text-primary))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
                required
              />
            </div>

            <div className="space-y-1">
              <label htmlFor="automation-rule-description" className="text-2xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                Descripción (opcional)
              </label>
              <textarea
                value={ruleDescription}
                id="automation-rule-description"
                onChange={(e) => setRuleDescription(e.target.value)}
                placeholder="Propósito operativo de esta automatización..."
                rows={2}
                className="w-full px-3 py-1.5 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-xs text-[hsl(var(--text-primary))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
              />
            </div>

            {/* Paso 1: Disparador */}
            <div className="p-3 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] space-y-2">
              <div className="flex items-center gap-2">
                <span className="size-5 rounded-full bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] text-3xs font-bold flex items-center justify-center">
                  1
                </span>
                <h4 className="text-xs font-bold text-[hsl(var(--text-primary))]">
                  ¿Cuándo debe ejecutarse? (Disparador)
                </h4>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-2">
                {TRIGGER_OPTIONS.map((opt) => {
                  const Icon = opt.icon;
                  const isSelected = selectedTrigger === opt.id;
                  return (
                    <button
                      key={opt.id}
                      type="button"
                      aria-pressed={isSelected}
                      onClick={() => setSelectedTrigger(opt.id)}
                      className={clsx(
                        "p-2.5 rounded-md border text-left transition-all flex items-start gap-2",
                        isSelected
                          ? "border-[hsl(var(--primary))] bg-[hsl(var(--primary))]/5 shadow-sm"
                          : "border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] hover:bg-[hsl(var(--surface-3))]"
                      )}
                    >
                      <div
                        className={clsx(
                          "p-1.5 rounded shrink-0",
                          isSelected ? "bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]" : "bg-[hsl(var(--surface-3))] text-[hsl(var(--text-secondary))]"
                        )}
                      >
                        <Icon size={14} />
                      </div>
                      <div className="min-w-0">
                        <div className="text-xs font-bold text-[hsl(var(--text-primary))] flex items-center justify-between">
                          <span>{opt.label}</span>
                          {isSelected && <Check size={12} className="text-[hsl(var(--primary))]" />}
                        </div>
                        <p className="text-3xs text-[hsl(var(--text-secondary))] mt-0.5 line-clamp-2">
                          {opt.description}
                        </p>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Paso 2: Condición */}
            <div className="p-3 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] space-y-2">
              <div className="flex items-center gap-2">
                <span className="size-5 rounded-full bg-[hsl(var(--warning-muted))] text-[hsl(var(--warning-text))] text-3xs font-bold flex items-center justify-center">
                  2
                </span>
                <h4 className="text-xs font-bold text-[hsl(var(--text-primary))]">
                  ¿Bajo qué condiciones? (Filtro opcional)
                </h4>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-2">
                <div className="space-y-1">
                  <label htmlFor="automation-condition-priority" className="text-3xs font-bold text-[hsl(var(--text-secondary))] uppercase">Prioridad de la tarea</label>
                  <select
                    id="automation-condition-priority"
                    value={conditionPriority}
                    onChange={(e) => setConditionPriority(e.target.value)}
                    className="w-full px-2.5 py-1.5 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-xs text-[hsl(var(--text-primary))]"
                  >
                    <option value="all">Cualquier prioridad</option>
                    <option value="urgent">Solo Urgente</option>
                    <option value="high">Solo Alta</option>
                    <option value="medium">Solo Media</option>
                    <option value="low">Solo Baja</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label htmlFor="automation-condition-status" className="text-3xs font-bold text-[hsl(var(--text-secondary))] uppercase">Estado de la tarea</label>
                  <select
                    id="automation-condition-status"
                    value={conditionStatus}
                    onChange={(e) => setConditionStatus(e.target.value)}
                    className="w-full px-2.5 py-1.5 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-xs text-[hsl(var(--text-primary))]"
                  >
                    <option value="all">Cualquier estado</option>
                    <option value="todo">Por Hacer</option>
                    <option value="in_progress">En Curso</option>
                    <option value="review">Revisión</option>
                    <option value="completed">Completado</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Paso 3: Acción */}
            <div className="p-3 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] space-y-2">
              <div className="flex items-center gap-2">
                <span className="size-5 rounded-full bg-[hsl(var(--success))] text-[hsl(var(--primary-foreground))] text-3xs font-bold flex items-center justify-center">
                  3
                </span>
                <h4 className="text-xs font-bold text-[hsl(var(--text-primary))]">
                  ¿Qué acción ejecutar? (Efecto)
                </h4>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-2">
                {ACTION_OPTIONS.map((act) => {
                  const Icon = act.icon;
                  const isSelected = selectedAction === act.id;
                  return (
                    <button
                      key={act.id}
                      type="button"
                      aria-pressed={isSelected}
                      onClick={() => setSelectedAction(act.id)}
                      className={clsx(
                        "p-2.5 rounded-md border text-left transition-all flex items-start gap-2",
                        isSelected
                          ? "border-[hsl(var(--success))] bg-[hsl(var(--success))]/5 shadow-sm"
                          : "border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] hover:bg-[hsl(var(--surface-3))]"
                      )}
                    >
                      <div
                        className={clsx(
                          "p-1.5 rounded shrink-0",
                          isSelected ? "bg-[hsl(var(--success))] text-[hsl(var(--primary-foreground))]" : "bg-[hsl(var(--surface-3))] text-[hsl(var(--text-secondary))]"
                        )}
                      >
                        <Icon size={14} />
                      </div>
                      <div className="min-w-0">
                        <div className="text-xs font-bold text-[hsl(var(--text-primary))] flex items-center justify-between">
                          <span>{act.label}</span>
                          {isSelected && <Check size={12} className="text-[hsl(var(--success))]" />}
                        </div>
                        <p className="text-3xs text-[hsl(var(--text-secondary))] mt-0.5 line-clamp-2">
                          {act.description}
                        </p>
                      </div>
                    </button>
                  );
                })}
              </div>

              {/* Parámetros de acción según selección */}
              {selectedAction === "create_followup_task" && (
                <div className="pt-2 border-t border-[hsl(var(--border))] mt-2 space-y-2">
                  <div className="space-y-1">
                    <label htmlFor="automation-followup-title" className="text-3xs font-bold uppercase text-[hsl(var(--text-secondary))]">Título de la nueva tarea</label>
                    <input
                      type="text"
                      id="automation-followup-title"
                      value={followupTitle}
                      onChange={(e) => setFollowupTitle(e.target.value)}
                      maxLength={TASK_TITLE_MAX_LENGTH}
                      placeholder="Ej: Auditoría y entrega formal"
                      className="w-full px-2.5 py-1 rounded border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-xs text-[hsl(var(--text-primary))]"
                    />
                  </div>
                  <div className="space-y-1">
                    <label htmlFor="automation-followup-duration" className="text-3xs font-bold uppercase text-[hsl(var(--text-secondary))]">Plazo (días de duración)</label>
                    <input
                      type="number"
                      id="automation-followup-duration"
                      min={1}
                      max={60}
                      value={followupDuration}
                      onChange={(e) => setFollowupDuration(e.target.value)}
                      className="w-24 px-2.5 py-1 rounded border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-xs text-[hsl(var(--text-primary))]"
                    />
                  </div>
                </div>
              )}

              {selectedAction === "change_phase" && (
                <div className="pt-2 border-t border-[hsl(var(--border))] mt-2 space-y-1">
                  <label htmlFor="automation-target-phase" className="text-3xs font-bold uppercase text-[hsl(var(--text-secondary))]">Fase de destino</label>
                  <input
                    type="text"
                    id="automation-target-phase"
                    value={targetPhaseName}
                    onChange={(e) => setTargetPhaseName(e.target.value)}
                    placeholder="Ej: Revisión o Completado"
                    className="w-full px-2.5 py-1 rounded border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-xs text-[hsl(var(--text-primary))]"
                  />
                </div>
              )}
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setActiveTab("rules")}
                className="px-3 py-1.5 rounded-md border border-[hsl(var(--border))] text-xs font-semibold text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))]"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="px-4 py-1.5 rounded-md bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] text-xs font-bold shadow-sm hover:opacity-90 disabled:opacity-50 transition-all flex items-center gap-1.5"
              >
                {submitting ? (
                  <>
                    <RotateCw className="animate-spin" size={14} />
                    <span>Guardando...</span>
                  </>
                ) : (
                  <>
                    <Zap size={14} />
                    <span>Crear Automatización</span>
                  </>
                )}
              </button>
            </div>
          </form>
        )}

        {/* Tab 3: Simulator & Test */}
        {activeTab === "test" && (
          <div className="flex-1 overflow-y-auto space-y-3 pr-1">
            <div className="p-3 bg-[hsl(var(--surface-1))] rounded-lg border border-[hsl(var(--border))] space-y-2">
              <h4 className="text-xs font-bold text-[hsl(var(--text-primary))]">Vista previa de automatizaciones</h4>
              <p className="text-2xs text-[hsl(var(--text-secondary))]">
                Evalúa las reglas activas para este evento sin crear tareas, modificar datos ni registrar actividad:
              </p>

              <div className="grid grid-cols-2 gap-2 pt-2">
                <button
                  onClick={() => handleTestEvaluate("task_completed")}
                  disabled={testingRuleId !== null}
                  className="p-2 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] hover:bg-[hsl(var(--surface-3))] text-xs font-bold text-[hsl(var(--text-primary))] flex items-center justify-center gap-1.5 transition-all active:scale-95 disabled:opacity-50"
                >
                  <CheckCircle2 size={14} className="text-[hsl(var(--success))]" />
                  <span>Previsualizar: tarea completada</span>
                </button>

                <button
                  onClick={() => handleTestEvaluate("task_created")}
                  disabled={testingRuleId !== null}
                  className="p-2 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] hover:bg-[hsl(var(--surface-3))] text-xs font-bold text-[hsl(var(--text-primary))] flex items-center justify-center gap-1.5 transition-all active:scale-95 disabled:opacity-50"
                >
                  <Plus size={14} className="text-[hsl(var(--primary))]" />
                  <span>Previsualizar: tarea creada</span>
                </button>
              </div>
            </div>

            {/* Test Results Output */}
            {lastTestResults.length > 0 && (
              <div className="p-3 bg-[hsl(var(--surface-1))] rounded-lg border border-[hsl(var(--border))] space-y-2">
                <div className="flex items-center justify-between">
                  <h5 className="text-xs font-bold text-[hsl(var(--text-primary))]">Resultado de la vista previa</h5>
                  <span className="text-3xs font-semibold text-[hsl(var(--text-secondary))]">
                    {lastTestResults.length} regla(s) procesadas
                  </span>
                </div>

                <div className="space-y-1.5">
                  {lastTestResults.map((res, i) => (
                    <div
                      key={i}
                      className={clsx(
                        "p-2 rounded-md border text-2xs flex items-start gap-2",
                        res.status === "would_execute"
                          ? "bg-[hsl(var(--primary))]/10 border-[hsl(var(--primary))]/30 text-[hsl(var(--text-primary))]"
                          : res.status === "executed"
                          ? "bg-[hsl(var(--success))]/10 border-[hsl(var(--success))]/30 text-[hsl(var(--text-primary))]"
                          : res.status === "skipped_condition"
                          ? "bg-[hsl(var(--surface-2))] border-[hsl(var(--border))] text-[hsl(var(--text-secondary))]"
                          : "bg-[hsl(var(--destructive))]/10 border-[hsl(var(--destructive))]/30 text-[hsl(var(--destructive))]"
                      )}
                    >
                      <div className="p-1 rounded shrink-0 mt-0.5">
                        {res.status === "would_execute" ? (
                          <Zap size={12} className="text-[hsl(var(--primary))]" />
                        ) : res.status === "executed" ? (
                          <Check size={12} className="text-[hsl(var(--success))]" />
                        ) : res.status === "skipped_condition" ? (
                          <Filter size={12} className="text-[hsl(var(--text-secondary))]" />
                        ) : (
                          <AlertCircle size={12} className="text-[hsl(var(--destructive))]" />
                        )}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="font-bold flex items-center justify-between">
                          <span>{res.rule_name}</span>
                          <span className="uppercase text-3xs font-extrabold tracking-wider">
                            {res.status === "would_execute" ? "Se ejecutaría" : res.status}
                          </span>
                        </div>
                        {res.details && (
                          <p className="text-3xs opacity-85 mt-0.5">{res.details}</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </RightPanel>
      <ConfirmActionDrawer action={confirmAction} onClose={() => setConfirmAction(null)} />
    </>
  );
}
