import type { Strategy } from '../../../types';
import { ArrowLeft, Clock, Trash2, Users } from 'lucide-react';
import { STATUS_COLORS, STATUS_LABELS, TYPOLOGY_COLORS, TYPOLOGY_LABELS } from '../strategyDetailShared';

interface StrategyHeaderProps {
  strategy: Strategy;
  groupCount: number | null;
  canManage: boolean;
  onDelete: () => void;
  onBack: () => void;
}

export default function StrategyHeader({ strategy, groupCount, canManage, onDelete, onBack }: StrategyHeaderProps) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div className="flex items-start gap-3">
        <button onClick={onBack}
          className="p-1.5 rounded-lg hover:bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))] dark:hover:text-white transition-all mt-1">
          <ArrowLeft size={16} />
        </button>
        <div>
          <h1 className="text-xl font-bold text-[hsl(var(--text-primary))]">{strategy.name}</h1>
          <div className="flex items-center gap-3 mt-1 text-xs text-[hsl(var(--text-secondary))] font-medium flex-wrap">
            {strategy.typology && (
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold"
                style={{ backgroundColor: `${TYPOLOGY_COLORS[strategy.typology]}18`, color: TYPOLOGY_COLORS[strategy.typology] }}>
                {TYPOLOGY_LABELS[strategy.typology]}
              </span>
            )}
            {strategy.recurrence && <span className="inline-flex items-center gap-1.5"><Clock size={12} />{strategy.recurrence}</span>}
            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold"
              style={{ backgroundColor: `${STATUS_COLORS[strategy.status]}18`, color: STATUS_COLORS[strategy.status] }}>
              {STATUS_LABELS[strategy.status]}
            </span>
            {groupCount !== null && (
              <span className="inline-flex items-center gap-1.5"><Users size={12} />{groupCount} grupo{groupCount !== 1 ? 's' : ''}</span>
            )}
          </div>
        </div>
      </div>
      {canManage ? (
        <button onClick={onDelete}
          className="p-2 rounded-lg text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--destructive))] hover:bg-red-50 dark:hover:bg-red-500/10 transition-all" title="Eliminar estrategia">
          <Trash2 size={16} />
        </button>
      ) : null}
    </div>
  );
}
