'use client';

import EmptyState from '@/components/ui/EmptyState';
import { DSSkeleton } from '@/design';
import { DSBadge } from '@/design';
import {
  ArrowDownRight,
  ArrowUpRight,
  BarChart3,
  Crown,
  Medal,
  TrendingUp,
  Users,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

interface GroupRanking {
  group_id: string;
  group_name: string;
  attendance_rate?: number;
  present?: number;
  expected?: number;
  growth?: number;
  current_personas?: number;
  previous_personas?: number;
  visitors?: number;
}

type RankBy = 'attendance' | 'growth' | 'visitors';

interface Props {
  groupRankings: GroupRanking[];
  loadingGroups: boolean;
  activeTab: RankBy;
  onTabChange: (tab: RankBy) => void;
}

const tabs: { id: RankBy; label: string; icon: LucideIcon }[] = [
  { id: 'attendance', label: 'Asistencia', icon: BarChart3 },
  { id: 'growth', label: 'Crecimiento', icon: TrendingUp },
  { id: 'visitors', label: 'Visitantes', icon: Users },
];

function renderPodiumIcon(index: number) {
  if (index === 0) return <Crown size={16} className="text-[hsl(var(--warning))]" />;
  if (index === 1) return <Medal size={16} className="text-slate-400" />;
  if (index === 2) return <Medal size={16} className="text-warning-text" />;
  return <span className="text-xs font-bold text-[hsl(var(--text-secondary))] w-4 text-center">{index + 1}</span>;
}

export default function GroupRankingsPanel({ groupRankings, loadingGroups, activeTab, onTabChange }: Props) {
  return (
    <section>
      <div className="flex items-center gap-1 border-b border-[hsl(var(--border-primary))] mb-3">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className={`flex items-center gap-1.5 px-3 py-2 text-[10px] font-semibold uppercase tracking-wide border-b-2 -mb-[1px] transition-all ${
                isActive
                  ? 'text-[hsl(var(--primary))] border-[hsl(var(--primary))]'
                  : 'text-[hsl(var(--text-secondary))] border-transparent hover:text-[hsl(var(--text-primary))]'
              }`}
            >
              <Icon size={14} />
              {tab.label}
            </button>
          );
        })}
      </div>

      {loadingGroups ? (
        <div className="space-y-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <DSSkeleton key={i} className="h-16 rounded-lg" />
          ))}
        </div>
      ) : groupRankings.length === 0 ? (
        <EmptyState
          icon={BarChart3}
          title="Sin datos de rankings"
          description="No hay grupos con datos suficientes para generar rankings en este período."
        />
      ) : (
        <div className="space-y-2">
          {groupRankings.map((group, index) => (
            <div
              key={group.group_id}
              className="flex items-center gap-3 bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border-primary))] rounded-lg p-3 hover:shadow-md hover:border-[hsl(var(--info)/100%)]/20 transition-all"
            >
              <div className="shrink-0 w-8 flex justify-center">
                {renderPodiumIcon(index)}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-bold text-[hsl(var(--text-primary))] truncate">
                  {group.group_name}
                </p>
                {activeTab === 'attendance' && (
                  <p className="text-[10px] text-[hsl(var(--text-secondary))] font-medium">
                    {group.present} presentes / {group.expected} esperados
                  </p>
                )}
                {activeTab === 'growth' && (
                  <p className="text-[10px] text-[hsl(var(--text-secondary))] font-medium">
                    {group.current_personas} actuales (antes {group.previous_personas})
                  </p>
                )}
                {activeTab === 'visitors' && (
                  <p className="text-[10px] text-[hsl(var(--text-secondary))] font-medium">
                    {group.visitors} visitantes nuevos este mes
                  </p>
                )}
              </div>
              <div className="shrink-0 text-right">
                {activeTab === 'attendance' && (
                  <DSBadge
                    tone={
                      (group.attendance_rate || 0) >= 80
                        ? 'emerald'
                        : (group.attendance_rate || 0) >= 50
                        ? 'amber'
                        : 'slate'
                    }
                    label={`${group.attendance_rate}%`}
                  />
                )}
                {activeTab === 'growth' && (
                  <div className="flex items-center gap-1">
                    {(group.growth || 0) >= 0 ? (
                      <ArrowUpRight size={14} className="text-[hsl(var(--success))]" />
                    ) : (
                      <ArrowDownRight size={14} className="text-[hsl(var(--danger))]" />
                    )}
                    <span
                      className={`text-sm font-bold ${
                        (group.growth || 0) >= 0 ? 'text-[hsl(var(--success))]' : 'text-[hsl(var(--danger))]'
                      }`}
                    >
                      {group.growth && group.growth > 0 ? '+' : ''}
                      {group.growth}
                    </span>
                  </div>
                )}
                {activeTab === 'visitors' && (
                  <DSBadge tone="blue" label={`${group.visitors} visitantes`} />
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
