"use client";

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { BookOpenCheck, CalendarDays, Plus, Users, UsersRound } from 'lucide-react';
import clsx from 'clsx';
import { DSButton, DSSkeleton } from '@/design';
import EmptyState from '@/components/ui/EmptyState';
import StudyGroupDrawer from '@/components/academy/StudyGroupDrawer';
import { useAuth } from '@/context/AuthContext';
import { apiFetch, extractErrorMessage } from '@/lib/http';
import { toast } from 'sonner';
import type { AcademicTranscriptSummary, StudyGroup } from '@/types/academy';

interface OfferingOption {
  id: string;
  name: string;
  periodCode: string;
}

function normalizeOfferings(record: AcademicTranscriptSummary): OfferingOption[] {
  const byId = new Map<string, OfferingOption>();
  record.subjects.forEach((subject) => {
    if (subject.offering_id && !byId.has(subject.offering_id)) {
      byId.set(subject.offering_id, {
        id: subject.offering_id,
        name: subject.subject_name,
        periodCode: subject.period_code,
      });
    }
  });
  return [...byId.values()].sort((left, right) => right.periodCode.localeCompare(left.periodCode));
}

export default function StudyGroupsPage() {
  const { token, isAuthenticated, user } = useAuth();
  const [offerings, setOfferings] = useState<OfferingOption[]>([]);
  const [selectedOfferingId, setSelectedOfferingId] = useState('');
  const [groups, setGroups] = useState<StudyGroup[]>([]);
  const [myGroups, setMyGroups] = useState<StudyGroup[]>([]);
  const [loadingOfferings, setLoadingOfferings] = useState(true);
  const [loadingGroups, setLoadingGroups] = useState(true);
  const [loadingMyGroups, setLoadingMyGroups] = useState(true);
  const [groupsError, setGroupsError] = useState<string | null>(null);
  const [myGroupsError, setMyGroupsError] = useState<string | null>(null);
  const [membershipGroupId, setMembershipGroupId] = useState<string | null>(null);
  const [isCreateOpen, setIsCreateOpen] = useState(false);

  const selectedOffering = useMemo(
    () => offerings.find((offering) => offering.id === selectedOfferingId) ?? null,
    [offerings, selectedOfferingId],
  );

  const loadOfferings = useCallback(async (signal?: AbortSignal) => {
    if (!token) {
      setLoadingOfferings(false);
      return;
    }
    setLoadingOfferings(true);
    try {
      const record = await apiFetch<AcademicTranscriptSummary>('/academy/me/academic-record', { token, cache: 'no-store', signal });
      if (signal?.aborted) return;
      const list = normalizeOfferings(record);
      setOfferings(list);
      setSelectedOfferingId((current) => list.some((offering) => offering.id === current) ? current : list[0]?.id ?? '');
    } catch (error: unknown) {
      if (!signal?.aborted) toast.error(extractErrorMessage(error, 'No pudimos cargar tus comisiones'));
    } finally {
      if (!signal?.aborted) setLoadingOfferings(false);
    }
  }, [token]);

  const loadMyGroups = useCallback(async (signal?: AbortSignal) => {
    if (!token) {
      setLoadingMyGroups(false);
      return;
    }
    setLoadingMyGroups(true);
    setMyGroupsError(null);
    try {
      const data = await apiFetch<StudyGroup[]>('/academy/study-groups/my', { token, cache: 'no-store', signal });
      if (!signal?.aborted) setMyGroups(Array.isArray(data) ? data : []);
    } catch (error: unknown) {
      if (!signal?.aborted) {
        const message = extractErrorMessage(error, 'No pudimos cargar tus grupos');
        setMyGroupsError(message);
        toast.error(message);
      }
    } finally {
      if (!signal?.aborted) setLoadingMyGroups(false);
    }
  }, [token]);

  const loadGroups = useCallback(async (offeringId: string, signal?: AbortSignal) => {
    if (!token || !offeringId) {
      setGroups([]);
      setLoadingGroups(false);
      return;
    }
    setLoadingGroups(true);
    setGroupsError(null);
    try {
      const data = await apiFetch<StudyGroup[]>(`/academy/study-groups/${offeringId}`, { token, cache: 'no-store', signal });
      if (!signal?.aborted) setGroups(Array.isArray(data) ? data : []);
    } catch (error: unknown) {
      if (!signal?.aborted) {
        const message = extractErrorMessage(error, 'No pudimos cargar los grupos de esta comisión');
        setGroupsError(message);
        toast.error(message);
      }
    } finally {
      if (!signal?.aborted) setLoadingGroups(false);
    }
  }, [token]);

  useEffect(() => {
    if (!isAuthenticated || !token) {
      setLoadingOfferings(false);
      setLoadingMyGroups(false);
      return undefined;
    }
    const controller = new AbortController();
    void loadOfferings(controller.signal);
    void loadMyGroups(controller.signal);
    return () => controller.abort();
  }, [isAuthenticated, loadMyGroups, loadOfferings, token]);

  useEffect(() => {
    if (!selectedOfferingId) {
      setGroups([]);
      setLoadingGroups(false);
      return undefined;
    }
    const controller = new AbortController();
    void loadGroups(selectedOfferingId, controller.signal);
    return () => controller.abort();
  }, [loadGroups, selectedOfferingId]);

  const refreshGroups = useCallback(async () => {
    if (selectedOfferingId) await loadGroups(selectedOfferingId);
    await loadMyGroups();
  }, [loadGroups, loadMyGroups, selectedOfferingId]);

  const handleMembership = async (group: StudyGroup, isMember: boolean) => {
    if (!token || membershipGroupId) return;
    setMembershipGroupId(group.id);
    try {
      await apiFetch(isMember ? `/academy/study-groups/${group.id}/leave` : `/academy/study-groups/${group.id}/join`, {
        method: isMember ? 'DELETE' : 'POST',
        token,
      });
      toast.success(isMember ? 'Saliste del grupo' : 'Te uniste al grupo');
      await refreshGroups();
    } catch (error: unknown) {
      toast.error(extractErrorMessage(error, isMember ? 'No pudimos salir del grupo' : 'No pudimos unirnos al grupo'));
    } finally {
      setMembershipGroupId(null);
    }
  };

  const myGroupIds = useMemo(() => new Set(myGroups.map((group) => group.id)), [myGroups]);

  return (
    <div className="min-h-full bg-[hsl(var(--bg-primary))] text-[hsl(var(--text-primary))]">
      <header className="border-b border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-4 py-5 sm:px-6">
        <div className="mx-auto flex w-full max-w-7xl items-center justify-between gap-4">
          <div className="flex min-w-0 items-center gap-3">
            <span className="grid size-12 shrink-0 place-items-center rounded-xl bg-[hsl(var(--primary)/0.12)] text-[hsl(var(--primary))]"><UsersRound className="size-6" /></span>
            <div className="min-w-0">
              <p className="text-xs font-semibold uppercase tracking-wider text-[hsl(var(--primary))]">Aprendizaje colaborativo</p>
              <h1 className="mt-1 text-xl font-bold sm:text-2xl">Grupos de estudio</h1>
              <p className="mt-1 text-sm text-[hsl(var(--text-secondary))]">Encuentra compañeros y aprende en comunidad.</p>
            </div>
          </div>
          <DSButton onClick={() => setIsCreateOpen(true)} disabled={!selectedOfferingId} className="inline-flex shrink-0 items-center gap-2"><Plus className="size-4" /> Crear Grupo</DSButton>
        </div>
      </header>

      <main className="mx-auto w-full max-w-7xl space-y-6 px-4 py-5 sm:px-6">
        <section className="rounded-2xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-5 shadow-sm" aria-labelledby="my-study-groups-title">
          <div className="mb-4 flex items-center gap-2"><Users className="size-5 text-[hsl(var(--primary))]" /><h2 id="my-study-groups-title" className="text-lg font-bold">Mis grupos</h2></div>
          {loadingMyGroups ? (
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2"><DSSkeleton className="h-28 rounded-xl" /><DSSkeleton className="h-28 rounded-xl" /></div>
          ) : myGroupsError ? (
            <ErrorMessage message={myGroupsError} />
          ) : myGroups.length === 0 ? (
            <EmptyState title="Todavía no participas en grupos" description="Únete a un grupo o crea uno para estudiar en equipo." icon={UsersRound} />
          ) : (
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              {myGroups.map((group) => <GroupCard key={group.id} group={group} isMember onMembershipChange={handleMembership} loading={membershipGroupId === group.id} currentUserId={user?.id} />)}
            </div>
          )}
        </section>

        <section className="rounded-2xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-5 shadow-sm" aria-labelledby="available-study-groups-title">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 id="available-study-groups-title" className="text-lg font-bold">Grupos por comisión</h2>
              <p className="mt-1 text-sm text-[hsl(var(--text-secondary))]">Selecciona una comisión para ver sus grupos disponibles.</p>
            </div>
            {!loadingOfferings && offerings.length > 0 && (
              <label className="flex items-center gap-2 text-sm">
                <span className="sr-only">Comisión</span>
                <select value={selectedOfferingId} onChange={(event) => setSelectedOfferingId(event.target.value)} className="max-w-xs rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] px-3 py-2 text-sm text-[hsl(var(--text-primary))]">
                  {offerings.map((offering) => <option key={offering.id} value={offering.id}>{offering.name} · {offering.periodCode}</option>)}
                </select>
              </label>
            )}
          </div>
          {loadingOfferings || loadingGroups ? (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3"><DSSkeleton className="h-52 rounded-xl" /><DSSkeleton className="h-52 rounded-xl" /></div>
          ) : offerings.length === 0 ? (
            <EmptyState title="No hay comisiones disponibles" description="Tus comisiones académicas aparecerán aquí para que encuentres grupos de estudio." icon={BookOpenCheck} />
          ) : groupsError ? (
            <ErrorMessage message={groupsError} />
          ) : groups.length === 0 ? (
            <EmptyState title="Aún no hay grupos en esta comisión" description="Puedes crear el primero e invitar a otros estudiantes." icon={UsersRound} />
          ) : (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
              {groups.map((group) => <GroupCard key={group.id} group={group} isMember={myGroupIds.has(group.id)} onMembershipChange={handleMembership} loading={membershipGroupId === group.id} currentUserId={user?.id} />)}
            </div>
          )}
        </section>
      </main>

      <StudyGroupDrawer
        open={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        offeringId={selectedOffering?.id ?? null}
        offeringName={selectedOffering?.name}
        token={token}
        onCreated={refreshGroups}
      />
    </div>
  );
}

function GroupCard({
  group,
  isMember,
  onMembershipChange,
  loading,
  currentUserId,
}: {
  group: StudyGroup;
  isMember: boolean;
  onMembershipChange: (group: StudyGroup, isMember: boolean) => Promise<void>;
  loading: boolean;
  currentUserId?: string;
}) {
  const isFull = group.members_count >= group.max_members;
  return (
    <article className="flex min-w-0 flex-col justify-between rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-4">
      <div>
        <div className="flex items-start justify-between gap-2">
          <h3 className="break-words text-base font-bold">{group.name}</h3>
          <span className={clsx('shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase', isFull ? 'border-[hsl(var(--warning)/0.3)] bg-[hsl(var(--warning-muted))] text-[hsl(var(--warning-text))]' : 'border-[hsl(var(--success)/0.3)] bg-[hsl(var(--success-muted))] text-[hsl(var(--success))]')}>
            {isFull ? 'Completo' : 'Abierto'}
          </span>
        </div>
        {group.description && <p className="mt-2 line-clamp-3 text-sm text-[hsl(var(--text-secondary))]">{group.description}</p>}
        <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-[hsl(var(--text-secondary))]">
          <span className="inline-flex items-center gap-1.5"><Users className="size-3.5" />{group.members_count}/{group.max_members} integrantes</span>
          <span className="inline-flex items-center gap-1.5"><CalendarDays className="size-3.5" />{formatDate(group.created_at)}</span>
        </div>
        {group.creator_name && <p className="mt-2 text-xs text-[hsl(var(--text-secondary))]">Creado por {group.creator_name}</p>}
        {group.members.some((member) => member.student_id === currentUserId) && <p className="mt-2 text-xs font-medium text-[hsl(var(--primary))]">Ya formas parte de este grupo.</p>}
      </div>
      <DSButton
        variant={isMember ? 'secondary' : 'primary'}
        disabled={loading || (!isMember && isFull)}
        loading={loading}
        onClick={() => void onMembershipChange(group, isMember)}
        className="mt-4 w-full"
      >
        {isMember ? 'Salir del grupo' : isFull ? 'Sin cupos disponibles' : 'Unirse'}
      </DSButton>
    </article>
  );
}

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Fecha no disponible' : date.toLocaleDateString('es');
}

function ErrorMessage({ message }: { message: string }) {
  return <p role="alert" className="rounded-lg border border-[hsl(var(--destructive)/0.3)] bg-[hsl(var(--destructive)/0.05)] p-3 text-sm text-[hsl(var(--destructive))]">{message}</p>;
}
