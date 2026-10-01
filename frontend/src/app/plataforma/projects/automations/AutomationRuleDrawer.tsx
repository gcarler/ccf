"use client";

import React, { useState, useEffect } from "react";
import { RightPanel } from "@/components/ui/RightPanel";
import { apiFetch } from "@/lib/http";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import {
  CheckCircle2,
  Plus,
  RotateCw,
  AlertCircle,
  Bell,
  Zap,
  ArrowRightCircle,
  Clock,
  ShieldAlert,
  Sparkles,
  Loader2,
  LucideIcon,
  Save,
} from "lucide-react";
import clsx from "clsx";

export interface AutomationRule {
  id: string;
  name: string;
  trigger_type: string;
  action_type?: string | null;
  is_active: boolean;
  last_run?: string | null;
}

interface TriggerOption {
  id: string;
  label: string;
  description: string;
  icon: LucideIcon;
}

interface ActionOption {
  id: string;
  label: string;
  description: string;
  icon: LucideIcon;
}

const TRIGGER_OPTIONS: TriggerOption[] = [
  {
    id: "task_completed",
    label: "Tarea completada",
    description: "Se dispara cuando cualquier tarea pasa a estado completada.",
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
    description: "Se dispara ante cualquier transición de fase kanban.",
    icon: RotateCw,
  },
  {
    id: "deadline",
    label: "Cerca del deadline",
    description: "Se activa 24 horas antes del vencimiento límite.",
    icon: Clock,
  },
  {
    id: "overload",
    label: "Carga alta de tareas",
    description: "Alerta ante saturación de volumen por responsable.",
    icon: ShieldAlert,
  },
  {
    id: "manual",
    label: "Disparador manual",
    description: "Ejecución bajo demanda desde el panel de control.",
    icon: Sparkles,
  },
];

const ACTION_OPTIONS: ActionOption[] = [
  {
    id: "notification",
    label: "Notificar al equipo",
    description: "Emite notificación push/inbox al responsable o equipo.",
    icon: Bell,
  },
  {
    id: "set_priority",
    label: "Fijar prioridad Alta",
    description: "Escala la prioridad de la tarea a nivel urgente o alto.",
    icon: Zap,
  },
  {
    id: "change_phase",
    label: "Mover de fase",
    description: "Desplaza la tarea de lista o columna kanban.",
    icon: ArrowRightCircle,
  },
  {
    id: "archive",
    label: "Archivar tarea",
    description: "Mueve la tarea al histórico archivado del proyecto.",
    icon: AlertCircle,
  },
];

interface AutomationRuleDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  rule?: AutomationRule | null;
  onSaved: (rule: AutomationRule) => void;
}

export function AutomationRuleDrawer({
  isOpen,
  onClose,
  rule,
  onSaved,
}: AutomationRuleDrawerProps) {
  const { token } = useAuth();
  const [name, setName] = useState("");
  const [triggerType, setTriggerType] = useState("task_completed");
  const [actionType, setActionType] = useState("notification");
  const [isActive, setIsActive] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (rule) {
      setName(rule.name);
      setTriggerType(rule.trigger_type || "task_completed");
      setActionType(rule.action_type || "notification");
      setIsActive(rule.is_active !== false);
    } else {
      setName("");
      setTriggerType("task_completed");
      setActionType("notification");
      setIsActive(true);
    }
  }, [rule, isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      toast.error("Por favor ingresa un nombre para la regla");
      return;
    }

    if (!token) {
      toast.error("Debes iniciar sesión para guardar la regla");
      return;
    }

    setSaving(true);
    try {
      if (rule?.id) {
        // Update existing rule
        const updated = await apiFetch<AutomationRule>(`/admin/automations/${rule.id}`, {
          method: "PATCH",
          token,
          body: {
            name: name.trim(),
            trigger_type: triggerType,
            action_type: actionType,
            is_active: isActive,
          },
        });
        toast.success("Regla de automatización actualizada");
        onSaved(updated);
      } else {
        // Create new rule
        const created = await apiFetch<AutomationRule>("/admin/automations", {
          method: "POST",
          token,
          body: {
            name: name.trim(),
            trigger_type: triggerType,
            action_type: actionType,
            is_active: isActive,
          },
        });
        toast.success("Regla de automatización creada exitosamente");
        onSaved(created);
      }
      onClose();
    } catch {
      toast.error("Error al guardar la regla de automatización");
    } finally {
      setSaving(false);
    }
  };

  return (
    <RightPanel
      open={isOpen}
      onClose={onClose}
      title={rule ? "Editar Regla" : "Nueva Automatización"}
      subtitle="Constructor Trigger -> Action"
      description="Configura disparadores y acciones automáticas para tareas de proyecto."
      width="w-full sm:max-w-lg"
    >
      <form onSubmit={handleSubmit} className="space-y-5 p-4 text-[hsl(var(--foreground))]">
        {/* Nombre de la Regla */}
        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))] mb-1.5">
            Nombre de la Regla *
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="ej. Al completar tarea notificar al pastor"
            required
            className="w-full px-3 py-2 text-sm bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-lg focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
          />
        </div>

        {/* Trigger Selection */}
        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))] mb-2">
            1. ¿Cuándo debe ejecutarse? (Trigger)
          </label>
          <div className="grid grid-cols-1 gap-2">
            {TRIGGER_OPTIONS.map((opt) => {
              const Icon = opt.icon;
              const isSelected = triggerType === opt.id;
              return (
                <button
                  type="button"
                  key={opt.id}
                  onClick={() => setTriggerType(opt.id)}
                  className={clsx(
                    "flex items-start gap-3 p-3 rounded-lg border text-left transition-all",
                    isSelected
                      ? "border-[hsl(var(--primary))] bg-[hsl(var(--primary)/0.08)] shadow-sm"
                      : "border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] hover:border-[hsl(var(--primary)/0.4)]"
                  )}
                >
                  <div
                    className={clsx(
                      "size-8 rounded-md flex items-center justify-center shrink-0 border mt-0.5",
                      isSelected
                        ? "bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] border-[hsl(var(--primary))]"
                        : "bg-[hsl(var(--surface-2))] text-[hsl(var(--muted-foreground))] border-[hsl(var(--border))]"
                    )}
                  >
                    <Icon size={16} />
                  </div>
                  <div>
                    <div className="text-xs font-bold text-[hsl(var(--foreground))]">
                      {opt.label}
                    </div>
                    <div className="text-2xs text-[hsl(var(--muted-foreground))] mt-0.5 leading-snug">
                      {opt.description}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Action Selection */}
        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))] mb-2">
            2. ¿Qué acción realizar? (Action)
          </label>
          <div className="grid grid-cols-1 gap-2">
            {ACTION_OPTIONS.map((opt) => {
              const Icon = opt.icon;
              const isSelected = actionType === opt.id;
              return (
                <button
                  type="button"
                  key={opt.id}
                  onClick={() => setActionType(opt.id)}
                  className={clsx(
                    "flex items-start gap-3 p-3 rounded-lg border text-left transition-all",
                    isSelected
                      ? "border-[hsl(var(--primary))] bg-[hsl(var(--primary)/0.08)] shadow-sm"
                      : "border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] hover:border-[hsl(var(--primary)/0.4)]"
                  )}
                >
                  <div
                    className={clsx(
                      "size-8 rounded-md flex items-center justify-center shrink-0 border mt-0.5",
                      isSelected
                        ? "bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] border-[hsl(var(--primary))]"
                        : "bg-[hsl(var(--surface-2))] text-[hsl(var(--muted-foreground))] border-[hsl(var(--border))]"
                    )}
                  >
                    <Icon size={16} />
                  </div>
                  <div>
                    <div className="text-xs font-bold text-[hsl(var(--foreground))]">
                      {opt.label}
                    </div>
                    <div className="text-2xs text-[hsl(var(--muted-foreground))] mt-0.5 leading-snug">
                      {opt.description}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Estado Activo */}
        <div className="flex items-center justify-between p-3 rounded-lg bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))]">
          <div>
            <div className="text-xs font-semibold text-[hsl(var(--foreground))]">
              Regla Activa
            </div>
            <div className="text-2xs text-[hsl(var(--muted-foreground))]">
              Las reglas activas reaccionan inmediatamente a los eventos de proyecto.
            </div>
          </div>
          <input
            type="checkbox"
            checked={isActive}
            onChange={(e) => setIsActive(e.target.checked)}
            className="size-4 accent-[hsl(var(--primary))] rounded cursor-pointer"
          />
        </div>

        {/* Botones de Acción */}
        <div className="pt-3 border-t border-[hsl(var(--border))] flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            disabled={saving}
            className="px-3 py-1.5 text-xs font-semibold uppercase tracking-wider rounded-lg border border-[hsl(var(--border))] hover:bg-[hsl(var(--surface-2))] transition-colors"
          >
            Cancelar
          </button>
          <button
            type="submit"
            disabled={saving}
            className="flex items-center gap-1.5 px-4 py-1.5 text-xs font-semibold uppercase tracking-wider rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] hover:bg-[hsl(var(--primary))]/90 active:scale-95 transition-all shadow-md disabled:opacity-60"
          >
            {saving ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />}
            {rule ? "Actualizar Regla" : "Crear Regla"}
          </button>
        </div>
      </form>
    </RightPanel>
  );
}
