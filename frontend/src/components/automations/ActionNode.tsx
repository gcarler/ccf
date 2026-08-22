import React, { memo } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { MessageSquare, Send, CheckSquare, Mail, PlayCircle, Clock, LucideIcon } from 'lucide-react';
import { AutomationWorkflowNode } from './types';

const ACTION_META: Record<string, { label: string; icon: LucideIcon }> = {
  send_whatsapp: { label: 'Enviar WhatsApp', icon: MessageSquare },
  send_sms: { label: 'Enviar SMS', icon: Send },
  create_task: { label: 'Crear Tarea Pastoral', icon: CheckSquare },
  send_email: { label: 'Enviar Correo', icon: Mail },
};


export const ActionNode = memo(({ data, selected }: NodeProps<AutomationWorkflowNode>) => {
  const actionType = data.automation?.action_type || 'send_whatsapp';
  const meta = ACTION_META[actionType] || { label: actionType, icon: PlayCircle };
  const ActionIcon = meta.icon;
  const isActive = data.automation?.is_active ?? true;
  const delayMinutes = data.automation?.delay_minutes ?? 0;

  const payload = data.automation?.action_payload || {};
  let previewText = '';
  if (actionType === 'create_task') {
    previewText = typeof payload.task_title === 'string' ? payload.task_title : 'Nueva tarea asignada';
  } else {
    previewText = typeof payload.message === 'string' ? payload.message : 'Mensaje automático...';
  }

  return (
    <div
      className={`group relative min-w-[240px] max-w-[280px] rounded-xl border-2 transition-all duration-200 bg-[hsl(var(--bg-primary))] dark:bg-[#18191c] shadow-md hover:shadow-xl ${
        selected
          ? 'border-emerald-500 ring-4 ring-emerald-500/20 shadow-emerald-500/10'
          : 'border-emerald-200 dark:border-emerald-900/50 hover:border-emerald-400'
      }`}
    >
      {/* Input Handle */}
      <Handle
        type="target"
        position={Position.Top}
        className="!size-3 !bg-emerald-500 !border-2 !border-white dark:!border-zinc-900 !rounded-full transition-transform hover:!scale-125 !top-[-6px]"
      />

      {/* Top Accent Ribbon */}
      <div className="h-1.5 w-full bg-gradient-to-r from-emerald-500 to-teal-400 rounded-t-[10px]" />

      <div className="p-3.5 space-y-2.5">
        {/* Header */}
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400">
            <div className="p-1 rounded-md bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200/60 dark:border-emerald-800/60">
              <ActionIcon size={14} />
            </div>
            <span className="text-[10px] font-extrabold uppercase tracking-wider">Acción</span>
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
            {data.automation?.name || data.label || 'Ejecutar Acción'}
          </h4>
          <p className="text-[11px] font-medium text-emerald-600 dark:text-emerald-400 mt-0.5">
            {meta.label}
          </p>
          {previewText && (
            <p className="text-[11px] text-[hsl(var(--text-secondary))] mt-1 line-clamp-2 bg-[hsl(var(--surface-2))] dark:bg-white/5 p-1.5 rounded border border-[hsl(var(--border))]/50 dark:border-white/5 italic">
              &quot;{previewText}&quot;
            </p>
          )}
        </div>
      </div>

      {/* Output Handle for Action Chaining */}
      <Handle
        type="source"
        position={Position.Bottom}
        className="!size-3 !bg-emerald-500 !border-2 !border-white dark:!border-zinc-900 !rounded-full transition-transform hover:!scale-125 !bottom-[-6px]"
      />
    </div>
  );
});

ActionNode.displayName = 'ActionNode';
