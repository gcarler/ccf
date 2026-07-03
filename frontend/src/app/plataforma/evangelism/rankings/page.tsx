'use client';

import EvangelismShell from '@/components/evangelism/EvangelismShell';
import EmptyState from '@/components/ui/EmptyState';
import Skeleton from '@/components/ui/Skeleton';
import { useAuth } from '@/context/AuthContext';
import { DSBadge, DSCard, DSMetric } from '@/design';
import { apiFetch } from '@/lib/http';
import {
  ArrowDownRight,
  ArrowUpRight,
  BarChart3,
  Crown,
  Medal,
  TrendingUp,
  Trophy,
  Users,
  User,
} from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import type { LucideIcon } from 'lucide-react';
import { toast } from 'sonner';

interface StrategyItem {
  id: string;
  name: string;
}

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

interface MonthlyStats {
  total_sessions: number;
  total_attendance: number;
  total_expected: number;
  avg_rate: number;
  new_visitors: number;
  new_conversions: number;
}

interface MonthlyComparison {
  current_month: MonthlyStats;
  previous_month: MonthlyStats;
}

interface LeaderRanking {
  leader_name: string;
  leader_id: string | null;
  group_id: string;
  group_name: string;
  attendance_pct: number;
  personas: number;
  visitors_this_month: number;
}

type RankBy = 'attendance' | 'growth' | 'visitors';

export default function RankingsPage() {
  const { token } = useAuth();
  const [strategies, setStrategies] = useState<StrategyItem[]>([]);
  const [selectedStrategy, setSelectedStrategy] = useState<string>('');
  const [activeTab, setActiveTab] = useState<RankBy>('attendance');
  const [groupRankings, setGroupRankings] = useState<GroupRanking[]>([]);
  const [monthlyComparison, setMonthlyComparison] = useState<MonthlyComparison | null>(null);
  const [leaders, setLeaders] = useState<LeaderRanking[]>([]);
  const [loadingGroups, setLoadingGroups] = useState(false);
  const [loadingMonthly, setLoadingMonthly] = useState(false);
  const [loadingLeaders, setLoadingLeaders] = useState(false);

  const fetchStrategies = useCallback(async () => {
    if (!token) return;
    try {
      const result = await apiFetch<StrategyItem[]>('/evangelism/strategies', { token });
      setStrategies(Array.isArray(result) ? result : []);
    } catch {
      // silent
    }
  }, [token]);

  const fetchGroupRankings = useCallback(
    async (by: RankBy) => {
      if (!token) return;
      setLoadingGroups(true);
      try {
        const query: Record<string, string> = { by };
        if (selectedStrategy) query.strategy_id = selectedStrategy;
        const result = await apiFetch<GroupRanking[]>('/evangelism/rankings/groups', {
          token,
          query,
        });
        setGroupRankings(Array.isArray(result) ? result : []);
      } catch (e: any) {
        toast.error(e?.message || 'Error al cargar rankings');
      } finally {
        setLoadingGroups(false);
      }
    },
    [token, selectedStrategy]
  );

  const fetchMonthlyComparison = useCallback(async () => {
    if (!token) return;
    setLoadingMonthly(true);
    try {
      const query: Record<string, string> = {};
      if (selectedStrategy) query.strategy_id = selectedStrategy;
      const result = await apiFetch<MonthlyComparison>('/evangelism/rankings/monthly-comparison', {
        token,
        query,
      });
      setMonthlyComparison(result);
    } catch (e: any) {
      toast.error(e?.message || 'Error al cargar comparación mensual');
    } finally {
      setLoadingMonthly(false);
    }
  }, [token, selectedStrategy]);

  const fetchLeaders = useCallback(async () => {
    if (!token) return;
    setLoadingLeaders(true);
    try {
      const query: Record<string, string> = {};
      if (selectedStrategy) query.strategy_id = selectedStrategy;
      const result = await apiFetch<LeaderRanking[]>('/evangelism/rankings/leaders', {
        token,
        query,
      });
      setLeaders(Array.isArray(result) ? result : []);
    } catch (e: any) {
      toast.error(e?.message || 'Error al cargar líderes');
    } finally {
      setLoadingLeaders(false);
    }
  }, [token, selectedStrategy]);

  useEffect(() => {
    fetchStrategies();
  }, [fetchStrategies]);

  useEffect(() => {
    fetchGroupRankings(activeTab);
  }, [activeTab, fetchGroupRankings]);

  useEffect(() => {
    fetchMonthlyComparison();
    fetchLeaders();
  }, [selectedStrategy, fetchMonthlyComparison, fetchLeaders]);

  const tabs: { id: RankBy; label: string; icon: LucideIcon }[] = [
    { id: 'attendance', label: 'Asistencia', icon: BarChart3 },
    { id: 'growth', label: 'Crecimiento', icon: TrendingUp },
    { id: 'visitors', label: 'Visitantes', icon: Users },
  ];

  const diffPct = (curr: number, prev: number) => {
    if (prev === 0) return curr > 0 ? 100 : 0;
    return Math.round(((curr - prev) / prev) * 100);
  };

  const renderPodiumIcon = (index: number) => {
    if (index === 0) return <Crown size={16} className="text-amber-400" />;
    if (index === 1) return <Medal size={16} className="text-slate-400" />;
    if (index === 2) return <Medal size={16} className="text-amber-700" />;
    return <span className="text-xs font-bold text-[hsl(var(--text-secondary))] w-4 text-center">{index + 1}</span>;
  };

  return (
    <EvangelismShell
      breadcrumbs={[
        { label: 'Evangelismo', href: '/plataforma/evangelism' },
        { label: 'Rankings' },
      ]}
    >
      <div className="p-4 space-y-5">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1">
              Métricas y Análisis
            </p>
            <h1 className="text-xl font-bold text-[hsl(var(--text-primary))] tracking-tight flex items-center gap-2">
              <Trophy size={22} className="text-amber-500" />
              Rankings de Grupos
            </h1>
          </div>
          <div className="w-full md:w-64">
            <label htmlFor="strategy-filter" className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] block mb-1.5">
              Filtrar por Estrategia
            </label>
            <select
              id="strategy-filter"
              value={selectedStrategy}
              onChange={(e) => setSelectedStrategy(e.target.value)}
              className="w-full bg-[hsl(var(--bg-muted))] dark:bg-black/20 border border-[hsl(var(--border-primary))] rounded-lg py-1.5 px-3 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500 appearance-none"
            >
              <option value="">Todas las estrategias</option>
              {strategies.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Monthly Comparison KPIs */}
        {loadingMonthly ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-28 rounded-lg" />
            ))}
          </div>
        ) : monthlyComparison ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <DSMetric
              label="Sesiones (este mes)"
              value={String(monthlyComparison.current_month.total_sessions)}
              trend={`vs ${monthlyComparison.previous_month.total_sessions} mes pasado`}
              tone="blue"
            />
            <DSMetric
              label="Asistencia Total"
              value={String(monthlyComparison.current_month.total_attendance)}
              trend={`${diffPct(monthlyComparison.current_month.total_attendance, monthlyComparison.previous_month.total_attendance)}% vs mes pasado`}
              tone="emerald"
            />
            <DSMetric
              label="Tasa Promedio"
              value={`${monthlyComparison.current_month.avg_rate}%`}
              trend={`vs ${monthlyComparison.previous_month.avg_rate}% mes pasado`}
              tone="amber"
            />
            <DSMetric
              label="Nuevos Visitantes"
              value={String(monthlyComparison.current_month.new_visitors)}
              trend={`vs ${monthlyComparison.previous_month.new_visitors} mes pasado`}
              tone="blue"
            />
          </div>
        ) : null}

        {/* Group Rankings Tabs */}
        <section>
          <div className="flex items-center gap-1 border-b border-[hsl(var(--border-primary))] mb-3">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
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
                <Skeleton key={i} className="h-16 rounded-lg" />
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
                  className="flex items-center gap-3 bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border-primary))] rounded-lg p-3 hover:shadow-md hover:border-blue-500/20 transition-all"
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
                          <ArrowUpRight size={14} className="text-emerald-500" />
                        ) : (
                          <ArrowDownRight size={14} className="text-rose-500" />
                        )}
                        <span
                          className={`text-sm font-bold ${
                            (group.growth || 0) >= 0 ? 'text-emerald-500' : 'text-rose-500'
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

        {/* Leaders Dashboard */}
        <section>
          <h2 className="text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-3 flex items-center gap-2">
            <User size={14} />
            Tablero de Líderes
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
                      <div className="size-9 rounded-lg bg-blue-100 dark:bg-blue-900/30 text-[hsl(var(--primary))] flex items-center justify-center shrink-0">
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
                        asistencia
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
      </div>
    </EvangelismShell>
  );
}
