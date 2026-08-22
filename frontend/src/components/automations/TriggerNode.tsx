import React, { memo } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { Zap, Clock, UserPlus, Cake, Moon, TrendingDown, Sparkles, Layers, Activity, LucideIcon } from 'lucide-react';
import { AutomationWorkflowNode } from './types';

const TRIGGER_LABELS: Record<string, { label: string; icon: LucideIcon }> = {
  new_persona: { label: 'Nuevo Persona', icon: UserPlus },
  birthday: { label: 'Cumpleaños', icon: Cake },
  inactivity: { label: 'Inactividad (30 días)', icon: Moon },
  low_attendance: { label: 'Baja Asistencia', icon: TrendingDown },
  anniversary: { label: 'Aniversario Espiritual', icon: Sparkles },
  stage_change: { label: 'Cambio de Etapa Pipeline', icon: Layers },
};


export const TriggerNode = memo(({ data, selected }: NodeProps<AutomationWorkflowNode>) => {
  const triggerKey = data.automation?.trigger_event || 'new_persona';
  const triggerMeta = TRIGGER_LABELS[triggerKey] || { label: triggerKey, icon: Zap };
  const TriggerIcon = triggerMeta.icon;
  const isActive = data.automation?.is_active ?? true;
  const delayMinutes = data.automation?.delay_minutes ?? 0;

  return (
    <div
      className={`group relative min-w-[240px] max-w-[280px] rounded-xl border-2 transition-all duration-200 bg-[hsl(var(--bg-primary))] dark:bg-[#18191c] shadow-md hover:shadow-xl ${
        selected
          ? 'border-blue-500 ring-4 ring-blue-500/20 shadow-blue-500/10'
          : 'border-blue-200 dark:border-blue-900/50 hover:border-blue-400'
      }`}
    >
      {/* Top Accent Ribbon */}
      <div className="h-1.5 w-full bg-gradient-to-r from-blue-500 to-cyan-400 rounded-t-[10px]" />

      <div className="p-3.5 space-y-2.5">
        {/* Header */}
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-1.5 text-blue-600 dark:text-blue-400">
            <div className="p-1 rounded-md bg-blue-50 dark:bg-blue-950/60 border border-blue-200/60 dark:border-blue-800/60">
              <TriggerIcon size={14} />
            </div>
            <span className="text-[10px] font-extrabold uppercase tracking-wider">Disparador</span>
          </div>

          <div className="flex items-center gap-1.5">
            {delayMinutes > 0 && (
              <span className="flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-50 dark:bg-amber-950/60 text-amber-600 dark:text-amber-400 border border-amber-200/60 dark:border-amber-800/60">
                <Clock size={10} />
                +{delayMinutes}m
              </span>
            )}
            <span
              className={`size-2 rounded-full ${
                isActive ? 'bg-emerald-500 shadow-sm shadow-emerald-500/50 ring-2 ring-emerald-500/20' : 'bg-zinc-400'
              }`}
              title={isActive ? 'Activo' : 'Inactivo'}
            />
          </div>
        </div>

        {/* Content */}
        <div>
          <h4 className="text-xs font-bold text-[hsl(var(--text-primary))] dark:text-white line-clamp-1 leading-snug">
            {data.automation?.name || data.label || 'Disparador'}
          </h4>
          <p className="text-[11px] text-[hsl(var(--text-secondary))] mt-0.5 line-clamp-1 flex items-center gap-1">
            <Activity size={11} className="text-blue-500 shrink-0" />
            <span>{triggerMeta.label}</span>
          </p>
        </div>
      </div>

      {/* Output Handle */}
      <Handle
        type="source"
        position={Position.Bottom}
        className="!size-3 !bg-blue-500 !border-2 !border-white dark:!border-zinc-900 !rounded-full transition-transform hover:!scale-125 !bottom-[-6px]"
      />
    </div>
  );
});

TriggerNode.displayName = 'TriggerNode';
