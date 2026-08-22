import React, { memo } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { GitBranch, Split, HelpCircle } from 'lucide-react';
import { AutomationWorkflowNode } from './types';

const OPERATOR_LABELS: Record<string, string> = {
  always: 'Siempre',
  equals: '==',
  ne: '!=',
  contains: 'contiene',
  starts_with: 'comienza con',
  in: 'en lista',
  gt: '>',
  lt: '<',
};

export const ConditionNode = memo(({ data, selected }: NodeProps<AutomationWorkflowNode>) => {
  const condConfig = data.condition_config;
  const operatorLabel = OPERATOR_LABELS[condConfig?.operator || 'equals'] || condConfig?.operator || '==';
  const fieldName = condConfig?.field || 'variable';
  const targetValue = condConfig?.value || '';

  return (
    <div
      className={`group relative min-w-[240px] max-w-[280px] rounded-xl border-2 transition-all duration-200 bg-[hsl(var(--bg-primary))] dark:bg-[#18191c] shadow-md hover:shadow-xl ${
        selected
          ? 'border-blue-500 ring-4 ring-blue-500/20 shadow-blue-500/10'
          : 'border-blue-200 dark:border-blue-900/50 hover:border-blue-400'
      }`}
    >
      {/* Input Handle */}
      <Handle
        type="target"
        position={Position.Top}
        className="!size-3 !bg-blue-500 !border-2 !border-white dark:!border-zinc-900 !rounded-full transition-transform hover:!scale-125 !top-[-6px]"
      />

      {/* Top Accent Ribbon */}
      <div className="h-1.5 w-full bg-gradient-to-r from-blue-500 to-cyan-400 rounded-t-[10px]" />

      <div className="p-3.5 space-y-2.5">
        {/* Header */}
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-1.5 text-blue-600 dark:text-blue-400">
            <div className="p-1 rounded-md bg-blue-50 dark:bg-blue-950/60 border border-blue-200/60 dark:border-blue-800/60">
              <GitBranch size={14} />
            </div>
            <span className="text-[10px] font-extrabold uppercase tracking-wider">Condición / Regla</span>
          </div>

          <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 border border-blue-200/60 dark:border-blue-800/60 flex items-center gap-1">
            <Split size={10} />
            Branch
          </span>
        </div>

        {/* Content */}
        <div>
          <h4 className="text-xs font-bold text-[hsl(var(--text-primary))] dark:text-white line-clamp-1 leading-snug">
            {data.automation?.name || data.label || 'Evaluar Condición'}
          </h4>
          <div className="mt-1.5 px-2 py-1 rounded bg-[hsl(var(--surface-2))] dark:bg-white/5 border border-[hsl(var(--border))]/60 dark:border-white/5 flex items-center gap-1.5 text-[11px] font-mono text-[hsl(var(--text-secondary))]">
            <HelpCircle size={11} className="text-blue-500 shrink-0" />
            <span className="text-blue-600 dark:text-blue-400 font-bold truncate">{fieldName}</span>
            <span className="text-[hsl(var(--text-secondary))] font-bold">{operatorLabel}</span>
            <span className="text-[hsl(var(--text-primary))] dark:text-zinc-200 font-bold truncate">
              {targetValue ? `"${targetValue}"` : '—'}
            </span>
          </div>
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

ConditionNode.displayName = 'ConditionNode';
