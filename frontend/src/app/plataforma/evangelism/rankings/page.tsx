'use client';

import EvangelismShell from '@/components/evangelism/EvangelismShell';
import { DSSkeleton } from '@/design';
import { useAuth } from '@/context/AuthContext';
import { DSMetric } from '@/design';
import { apiFetch } from '@/lib/http';
import {
  Trophy,
} from 'lucide-react';
import dynamic from 'next/dynamic';
import { useCallback, useEffect, useState } from 'react';

const GroupRankingsPanel = dynamic(
  () => import('./components/GroupRankingsPanel'),
  { ssr: false }
);
const LeadersPanel = dynamic(
  () => import('./components/LeadersPanel'),
  { ssr: false }
);

interface StrategyItem {
  id: string;
  name: string;
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
      const result = await apiFetch<StrategyItem[]>('/evangelism/strategies', { token, silent: true });
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
          silent: true,
          query,
        });
        setGroupRankings(Array.isArray(result) ? result : []);
    } catch {
      setGroupRankings([]);
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
        silent: true,
        query,
      });
      setMonthlyComparison(result);
    } catch {
      setMonthlyComparison(null);
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
        silent: true,
        query,
      });
      setLeaders(Array.isArray(result) ? result : []);
    } catch {
      setLeaders([]);
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

  const diffPct = (curr: number, prev: number) => {
    if (prev === 0) return curr > 0 ? 100 : 0;
    return Math.round(((curr - prev) / prev) * 100);
  };

  return (
    <EvangelismShell
      breadcrumbs={[
        { label: 'Evangelismo', href: '/plataforma/evangelism' },
        { label: 'Ranking' },
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
              <Trophy size={22} className="text-[hsl(var(--warning))]" />
              Ranking de grupos
            </h1>
          </div>
          <div className="w-full md:w-64">
            <label htmlFor="strategy-filter" className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] block mb-1.5">
              Filtrar por estrategia
            </label>
            <select
              id="strategy-filter"
              value={selectedStrategy}
              onChange={(e) => setSelectedStrategy(e.target.value)}
              className="w-full bg-[hsl(var(--bg-muted))] dark:bg-black/20 border border-[hsl(var(--border-primary))] rounded-lg py-1.5 px-3 text-sm font-bold outline-none focus:ring-2 focus:ring-[hsl(var(--primary))] appearance-none"
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
              <DSSkeleton key={i} className="h-28 rounded-lg" />
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
              label="Asistencia total"
              value={String(monthlyComparison.current_month.total_attendance)}
              trend={`${diffPct(monthlyComparison.current_month.total_attendance, monthlyComparison.previous_month.total_attendance)}% vs mes pasado`}
              tone="emerald"
            />
            <DSMetric
              label="Tasa promedio"
              value={`${monthlyComparison.current_month.avg_rate}%`}
              trend={`vs ${monthlyComparison.previous_month.avg_rate}% mes pasado`}
              tone="amber"
            />
            <DSMetric
              label="Nuevos visitantes"
              value={String(monthlyComparison.current_month.new_visitors)}
              trend={`vs ${monthlyComparison.previous_month.new_visitors} mes pasado`}
              tone="blue"
            />
          </div>
        ) : null}

        {/* Pestañas de rankings por grupo */}
        <GroupRankingsPanel
          groupRankings={groupRankings}
          loadingGroups={loadingGroups}
          activeTab={activeTab}
          onTabChange={setActiveTab}
        />

        {/* Panel de líderes */}
        <LeadersPanel leaders={leaders} loadingLeaders={loadingLeaders} />
      </div>
    </EvangelismShell>
  );
}
