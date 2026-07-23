'use client';

import EmptyState from '@/components/ui/EmptyState';
import Skeleton from '@/components/ui/Skeleton';
import { DSBadge, DSCard } from '@/design';
import { User } from 'lucide-react';

interface LeaderRanking {
  leader_name: string;
  leader_id: string | null;
  group_id: string;
  group_name: string;
  attendance_pct: number;
  personas: number;
  visitors_this_month: number;
}

interface Props {
  leaders: LeaderRanking[];
  loadingLeaders: boolean;
}

export default function LeadersPanel({ leaders, loadingLeaders }: Props) {
  return (
    <section>
      <h2 className="text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-3 flex items-center gap-2">
        <User size={14} />
        Panel de líderes
      </h2>
      {loadingLeaders ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-16 rounded-lg" />
          ))}
        </div>
      ) : leaders.length === 0 ? (
        <EmptyState
          icon={User}
          title="Sin datos de líderes"
          description="No hay líderes asignados a grupos activos en este período."
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {leaders.map((leader) => (
            <DSCard key={leader.leader_id || leader.group_id} tone="light" className="hover:shadow-md transition-all">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="size-9 rounded-lg bg-[hsl(var(--info-muted))] dark:bg-[hsl(var(--info))]/30 text-[hsl(var(--primary))] flex items-center justify-center shrink-0">
                    <User size={18} />
                  </div>
                  <div>
                    <p className="text-sm font-bold text-[hsl(var(--text-primary))]">
                      {leader.leader_name}
                    </p>
                    <p className="text-[10px] text-[hsl(var(--text-secondary))] font-medium">
                    {leader.group_name} · {leader.personas} personas
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-lg font-bold text-[hsl(var(--text-primary))]">
                    {leader.attendance_pct}%
                  </p>
                  <p className="text-[9px] text-[hsl(var(--text-secondary))] font-semibold uppercase tracking-wide">
                    Asistencia
                  </p>
                </div>
              </div>
              <div className="mt-3 pt-3 border-t border-[hsl(var(--border-primary))] flex items-center justify-between">
                <DSBadge
                  tone={leader.visitors_this_month > 0 ? 'emerald' : 'slate'}
                  label={`${leader.visitors_this_month} visitantes este mes`}
                />
                <span className="text-[10px] text-[hsl(var(--text-secondary))] font-medium">
                  {leader.personas} personas
                </span>
              </div>
            </DSCard>
          ))}
        </div>
      )}
    </section>
  );
}
