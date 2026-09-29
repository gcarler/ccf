"use client";

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Award,
  BookOpenCheck,
  Flame,
  Medal,
  ShieldCheck,
  Sparkles,
  Trophy,
  Users,
} from 'lucide-react';
import clsx from 'clsx';
import { DSButton, DSSkeleton } from '@/design';
import EmptyState from '@/components/ui/EmptyState';
import AchievementVerifyDrawer from '@/components/academy/AchievementVerifyDrawer';
import { useAuth } from '@/context/AuthContext';
import { apiFetch, extractErrorMessage } from '@/lib/http';
import { toast } from 'sonner';
import type { Achievement, LeaderboardEntry, StudentAchievement } from '@/types/academy';

type AchievementType = Achievement['achievement_type'];
type AchievementTone = 'completion' | 'excellence' | 'defense' | 'streak' | 'milestone';

const typeDetails: Record<AchievementTone, { label: string; className: string; icon: typeof Award }> = {
  completion: { label: 'Finalización', className: 'border-[hsl(var(--success)/0.3)] bg-[hsl(var(--success-muted))] text-[hsl(var(--success))]', icon: BookOpenCheck },
  excellence: { label: 'Excelencia', className: 'border-[hsl(var(--warning)/0.3)] bg-[hsl(var(--warning-muted))] text-[hsl(var(--warning-text))]', icon: Sparkles },
  defense: { label: 'Defensa', className: 'border-[hsl(var(--primary)/0.3)] bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))]', icon: ShieldCheck },
  streak: { label: 'Racha', className: 'border-[hsl(var(--warning)/0.3)] bg-[hsl(var(--warning-muted))] text-[hsl(var(--warning-text))]', icon: Flame },
  milestone: { label: 'Hito', className: 'border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))]', icon: Medal },
};

function getTypeDetails(type: AchievementType) {
  return typeDetails[type as AchievementTone] ?? typeDetails.milestone;
}

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Fecha no disponible' : date.toLocaleDateString('es');
}

export default function StudentAchievementsPage() {
  const { token, isAuthenticated, user } = useAuth();
  const [myAchievements, setMyAchievements] = useState<StudentAchievement[]>([]);
  const [catalog, setCatalog] = useState<Achievement[]>([]);
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [selectedAward, setSelectedAward] = useState<StudentAchievement | null>(null);
  const [loadingMine, setLoadingMine] = useState(true);
  const [loadingCatalog, setLoadingCatalog] = useState(true);
  const [loadingLeaderboard, setLoadingLeaderboard] = useState(true);
  const [mineError, setMineError] = useState<string | null>(null);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [leaderboardError, setLeaderboardError] = useState<string | null>(null);

  const loadAchievements = useCallback(async (signal: AbortSignal) => {
    if (!token) {
      setLoadingMine(false);
      setLoadingCatalog(false);
      setLoadingLeaderboard(false);
      return;
    }

    setLoadingMine(true);
    setLoadingCatalog(true);
    setLoadingLeaderboard(true);
    setMineError(null);
    setCatalogError(null);
    setLeaderboardError(null);

    const requests = [
      apiFetch<StudentAchievement[]>('/academy/achievements/my', { token, cache: 'no-store', signal })
        .then((data) => setMyAchievements(Array.isArray(data) ? data : []))
        .catch((error: unknown) => {
          if (!signal.aborted) {
            const message = extractErrorMessage(error, 'No pudimos cargar tus logros');
            setMineError(message);
            toast.error(message);
          }
        })
        .finally(() => { if (!signal.aborted) setLoadingMine(false); }),
      apiFetch<Achievement[]>('/academy/achievements', { token, cache: 'no-store', signal })
        .then((data) => setCatalog(Array.isArray(data) ? data : []))
        .catch((error: unknown) => {
          if (!signal.aborted) {
            const message = extractErrorMessage(error, 'No pudimos cargar los logros disponibles');
            setCatalogError(message);
            toast.error(message);
          }
        })
        .finally(() => { if (!signal.aborted) setLoadingCatalog(false); }),
      apiFetch<LeaderboardEntry[]>('/academy/leaderboard', {
        token,
        cache: 'no-store',
        signal,
        query: { limit: 20 },
      })
        .then((data) => setLeaderboard(Array.isArray(data) ? data.slice(0, 20) : []))
        .catch((error: unknown) => {
          if (!signal.aborted) {
            const message = extractErrorMessage(error, 'No pudimos cargar el leaderboard');
            setLeaderboardError(message);
            toast.error(message);
          }
        })
        .finally(() => { if (!signal.aborted) setLoadingLeaderboard(false); }),
    ];

    await Promise.all(requests);
  }, [token]);

  useEffect(() => {
    if (!isAuthenticated || !token) {
      setLoadingMine(false);
      setLoadingCatalog(false);
      setLoadingLeaderboard(false);
      return undefined;
    }
    const controller = new AbortController();
    void loadAchievements(controller.signal);
    return () => controller.abort();
  }, [isAuthenticated, loadAchievements, token]);

  const earnedByAchievementId = useMemo(() => {
    const earned = new Map<string, StudentAchievement>();
    myAchievements.forEach((award) => {
      if (!earned.has(award.achievement_id)) earned.set(award.achievement_id, award);
    });
    return earned;
  }, [myAchievements]);

  const totalPoints = myAchievements.reduce((sum, award) => sum + (award.achievement?.points ?? 0), 0);

  return (
    <div className="min-h-full bg-[hsl(var(--bg-primary))] text-[hsl(var(--text-primary))]">
      <header className="border-b border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-4 py-5 sm:px-6">
        <div className="mx-auto flex w-full max-w-7xl items-center gap-3">
          <div className="grid size-12 shrink-0 place-items-center rounded-xl bg-[hsl(var(--primary)/0.12)] text-[hsl(var(--primary))]"><Trophy className="size-6" /></div>
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-wider text-[hsl(var(--primary))]">Campus OS Cognitivo</p>
            <h1 className="mt-1 text-xl font-bold sm:text-2xl">Logros y Leaderboard</h1>
            <p className="mt-1 text-sm text-[hsl(var(--text-secondary))]">Celebra tu progreso y verifica tus credenciales académicas.</p>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-7xl space-y-6 px-4 py-5 sm:px-6">
        <section className="rounded-2xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-5 shadow-sm" aria-labelledby="my-achievements-title">
          <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-[hsl(var(--primary))]">A</p>
              <h2 id="my-achievements-title" className="mt-1 text-lg font-bold">Mis logros</h2>
            </div>
            {!loadingMine && !mineError && <span className="rounded-full bg-[hsl(var(--primary)/0.1)] px-3 py-1 text-xs font-semibold text-[hsl(var(--primary))]">{totalPoints} puntos acumulados</span>}
          </div>
          {loadingMine ? (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2"><DSSkeleton className="h-48 rounded-xl" /><DSSkeleton className="h-48 rounded-xl" /></div>
          ) : mineError ? (
            <ErrorMessage message={mineError} />
          ) : myAchievements.length === 0 ? (
            <EmptyState title="Aún no tienes logros" description="Tus insignias y credenciales aparecerán aquí cuando alcances nuevos hitos." icon={Award} />
          ) : (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
              {myAchievements.map((award) => {
                const achievement = award.achievement;
                const details = getTypeDetails(achievement?.achievement_type ?? 'milestone');
                const Icon = details.icon;
                return (
                  <article key={award.id} className="flex min-w-0 flex-col justify-between rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-4">
                    <div>
                      <div className="flex items-start justify-between gap-3">
                        <span className={clsx('inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide', details.className)}><Icon className="size-3.5" />{details.label}</span>
                        <span className="shrink-0 rounded-full bg-[hsl(var(--primary)/0.1)] px-2.5 py-1 text-xs font-bold text-[hsl(var(--primary))]">+{achievement?.points ?? 0} pts</span>
                      </div>
                      <h3 className="mt-3 break-words text-base font-bold">{achievement?.title ?? 'Logro académico'}</h3>
                      {achievement?.description && <p className="mt-1 line-clamp-3 text-sm text-[hsl(var(--text-secondary))]">{achievement.description}</p>}
                      <p className="mt-3 text-xs text-[hsl(var(--text-secondary))]">Obtenido el {formatDate(award.earned_at)}</p>
                    </div>
                    <DSButton
                      variant="secondary"
                      className="mt-4 inline-flex items-center justify-center gap-2"
                      disabled={!award.credential_hash}
                      onClick={() => setSelectedAward(award)}
                      title={!award.credential_hash ? 'Este logro aún no tiene una credencial verificable' : undefined}
                    >
                      <ShieldCheck className="size-4" /> {award.credential_hash ? 'Verificar Credencial' : 'Credencial no disponible'}
                    </DSButton>
                  </article>
                );
              })}
            </div>
          )}
        </section>

        <section className="rounded-2xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-5 shadow-sm" aria-labelledby="achievement-catalog-title">
          <div className="mb-5">
            <p className="text-xs font-semibold uppercase tracking-wider text-[hsl(var(--primary))]">B</p>
            <h2 id="achievement-catalog-title" className="mt-1 text-lg font-bold">Logros disponibles</h2>
            <p className="mt-1 text-sm text-[hsl(var(--text-secondary))]">Explora los hitos que puedes alcanzar en tu recorrido académico.</p>
          </div>
          {loadingCatalog ? (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3"><DSSkeleton className="h-44 rounded-xl" /><DSSkeleton className="h-44 rounded-xl" /><DSSkeleton className="h-44 rounded-xl" /></div>
          ) : catalogError ? (
            <ErrorMessage message={catalogError} />
          ) : catalog.length === 0 ? (
            <EmptyState title="No hay logros disponibles" description="El catálogo de logros se mostrará aquí cuando esté configurado." icon={Trophy} />
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {catalog.map((achievement) => {
                const award = earnedByAchievementId.get(achievement.id);
                const details = getTypeDetails(achievement.achievement_type);
                const Icon = details.icon;
                const progressPercent = award ? 100 : 0;
                return (
                  <article key={achievement.id} className="min-w-0 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-4">
                    <div className="flex items-start justify-between gap-3">
                      <span className={clsx('inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide', details.className)}><Icon className="size-3.5" />{details.label}</span>
                      {award ? <span className="inline-flex shrink-0 items-center gap-1 text-xs font-semibold text-[hsl(var(--success))]"><ShieldCheck className="size-4" /> Obtenido</span> : <span className="shrink-0 text-xs font-medium text-[hsl(var(--text-secondary))]">Por desbloquear</span>}
                    </div>
                    <h3 className="mt-3 break-words text-base font-bold">{achievement.title}</h3>
                    {achievement.description && <p className="mt-1 line-clamp-3 min-h-10 text-sm text-[hsl(var(--text-secondary))]">{achievement.description}</p>}
                    <div className="mt-4 flex items-center justify-between text-xs">
                      <span className="font-semibold text-[hsl(var(--primary))]">{achievement.points} puntos</span>
                      <span className="text-[hsl(var(--text-secondary))]">{award ? 'Completado' : 'Progreso'}</span>
                    </div>
                    <div className="mt-2 h-2 overflow-hidden rounded-full bg-[hsl(var(--surface-3))]" role="progressbar" aria-label={`Progreso de ${achievement.title}`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={progressPercent}>
                      <div className={clsx('h-full rounded-full transition-all', award ? 'bg-[hsl(var(--success))]' : 'bg-[hsl(var(--primary))]')} style={{ width: `${progressPercent}%` }} />
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </section>

        <section className="rounded-2xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-5 shadow-sm" aria-labelledby="leaderboard-title">
          <div className="mb-5 flex items-start justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-[hsl(var(--primary))]">C</p>
              <h2 id="leaderboard-title" className="mt-1 text-lg font-bold">Leaderboard</h2>
              <p className="mt-1 text-sm text-[hsl(var(--text-secondary))]">Top 20 estudiantes por puntos acumulados.</p>
            </div>
            <Users className="size-5 text-[hsl(var(--primary))]" aria-hidden="true" />
          </div>
          {loadingLeaderboard ? (
            <div className="space-y-2"><DSSkeleton className="h-12 rounded-lg" /><DSSkeleton className="h-12 rounded-lg" /><DSSkeleton className="h-12 rounded-lg" /></div>
          ) : leaderboardError ? (
            <ErrorMessage message={leaderboardError} />
          ) : leaderboard.length === 0 ? (
            <EmptyState title="Leaderboard sin resultados" description="Aún no hay puntajes disponibles para el periodo actual." icon={Trophy} />
          ) : (
            <div className="overflow-x-auto rounded-xl border border-[hsl(var(--border))]">
              <table className="w-full min-w-[28rem] text-left text-sm">
                <thead className="bg-[hsl(var(--surface-2))] text-xs uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                  <tr><th scope="col" className="px-4 py-3">Puesto</th><th scope="col" className="px-4 py-3">Estudiante</th><th scope="col" className="px-4 py-3 text-right">Puntos</th></tr>
                </thead>
                <tbody className="divide-y divide-[hsl(var(--border))]">
                  {leaderboard.map((entry, index) => (
                    <tr key={entry.id} className={clsx(entry.student_id === user?.id && 'bg-[hsl(var(--primary)/0.06)]')}>
                      <td className="px-4 py-3 font-semibold"><span className="inline-flex items-center gap-2">{entry.rank ?? index + 1}{(entry.rank ?? index + 1) === 1 && <Trophy className="size-4 text-[hsl(var(--warning))]" aria-label="Primer puesto" />}</span></td>
                      <td className="px-4 py-3 font-medium">{entry.student_name}{entry.student_id === user?.id && <span className="ml-2 rounded-full bg-[hsl(var(--primary)/0.1)] px-2 py-0.5 text-[10px] font-semibold text-[hsl(var(--primary))]">Tú</span>}</td>
                      <td className="px-4 py-3 text-right font-bold text-[hsl(var(--primary))]">{entry.total_points}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </main>

      <AchievementVerifyDrawer
        open={Boolean(selectedAward)}
        onClose={() => setSelectedAward(null)}
        award={selectedAward}
        token={token}
      />
    </div>
  );
}

function ErrorMessage({ message }: { message: string }) {
  return <p role="alert" className="rounded-lg border border-[hsl(var(--destructive)/0.3)] bg-[hsl(var(--destructive)/0.05)] p-3 text-sm text-[hsl(var(--destructive))]">{message}</p>;
}
