"use client";

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { CalendarDays, GraduationCap, HeartHandshake, Search, UsersRound } from 'lucide-react';
import clsx from 'clsx';
import { ApiError, apiFetch, extractErrorMessage } from '@/lib/http';
import { DSButton, DSSkeleton } from '@/design';
import EmptyState from '@/components/ui/EmptyState';
import MentorshipRequestDrawer from '@/components/academy/MentorshipRequestDrawer';
import { useAuth } from '@/context/AuthContext';
import { toast } from 'sonner';
import type { MentorProfile, MentorshipMentee, MentorshipRequest } from '@/types/academy';

type MentorshipTab = 'mentors' | 'requests' | 'mentees';

function mentorName(mentor: MentorProfile): string {
  return mentor.mentor_name ?? mentor.name ?? mentor.full_name ?? 'Mentor académico';
}

function displayList(value?: string[] | string | null): string[] {
  if (Array.isArray(value)) return value.filter((item) => item.trim().length > 0);
  if (typeof value === 'string' && value.trim()) return value.split(/[,;|]/).map((item) => item.trim()).filter(Boolean);
  return [];
}

function statusClass(status: string): string {
  const value = status.toLowerCase();
  if (['accepted', 'active', 'approved', 'completed'].includes(value)) return 'border-[hsl(var(--success)/0.3)] bg-[hsl(var(--success-muted))] text-[hsl(var(--success))]';
  if (['pending', 'requested', 'in_review'].includes(value)) return 'border-[hsl(var(--warning)/0.3)] bg-[hsl(var(--warning-muted))] text-[hsl(var(--warning-text))]';
  if (['rejected', 'declined', 'cancelled'].includes(value)) return 'border-[hsl(var(--destructive)/0.3)] bg-[hsl(var(--destructive)/0.08)] text-[hsl(var(--destructive))]';
  return 'border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))]';
}

function statusLabel(status: string): string {
  const value = status.toLowerCase();
  const labels: Record<string, string> = {
    accepted: 'Aceptada', active: 'Activa', approved: 'Aprobada', completed: 'Completada',
    pending: 'Pendiente', requested: 'Solicitada', in_review: 'En revisión',
    rejected: 'Rechazada', declined: 'Declinada', cancelled: 'Cancelada',
  };
  return labels[value] ?? status.replaceAll('_', ' ');
}

export default function StudentMentorshipPage() {
  const { token, isAuthenticated, user } = useAuth();
  const [activeTab, setActiveTab] = useState<MentorshipTab>('mentors');
  const [mentors, setMentors] = useState<MentorProfile[]>([]);
  const [requests, setRequests] = useState<MentorshipRequest[]>([]);
  const [mentees, setMentees] = useState<MentorshipMentee[]>([]);
  const [selectedMentor, setSelectedMentor] = useState<MentorProfile | null>(null);
  const [loadingMentors, setLoadingMentors] = useState(true);
  const [loadingRequests, setLoadingRequests] = useState(true);
  const [loadingMentees, setLoadingMentees] = useState(false);
  const [mentorsError, setMentorsError] = useState<string | null>(null);
  const [requestsError, setRequestsError] = useState<string | null>(null);
  const [menteesError, setMenteesError] = useState<string | null>(null);

  const isMentor = useMemo(() => {
    const role = String(user?.role ?? '').toLowerCase();
    return role.includes('mentor') || user?.permissions?.['academy:mentor'] === 'allow';
  }, [user]);

  const loadMentors = useCallback(async (signal?: AbortSignal) => {
    if (!token) {
      setLoadingMentors(false);
      return;
    }
    setLoadingMentors(true);
    setMentorsError(null);
    try {
      const data = await apiFetch<MentorProfile[]>('/academy/mentorship/available-mentors', { token, cache: 'no-store', signal });
      if (!signal?.aborted) setMentors(Array.isArray(data) ? data : []);
    } catch (error: unknown) {
      if (!signal?.aborted) {
        const message = extractErrorMessage(error, 'No pudimos cargar los mentores disponibles');
        setMentorsError(message);
        toast.error(message);
      }
    } finally {
      if (!signal?.aborted) setLoadingMentors(false);
    }
  }, [token]);

  const loadRequests = useCallback(async (signal?: AbortSignal) => {
    if (!token) {
      setLoadingRequests(false);
      return;
    }
    setLoadingRequests(true);
    setRequestsError(null);
    try {
      const data = await apiFetch<MentorshipRequest[]>('/academy/mentorship/my-requests', { token, cache: 'no-store', signal });
      if (!signal?.aborted) setRequests(Array.isArray(data) ? data : []);
    } catch (error: unknown) {
      if (!signal?.aborted) {
        const message = extractErrorMessage(error, 'No pudimos cargar tus solicitudes de mentoría');
        setRequestsError(message);
        toast.error(message);
      }
    } finally {
      if (!signal?.aborted) setLoadingRequests(false);
    }
  }, [token]);

  const loadMentees = useCallback(async (signal?: AbortSignal) => {
    if (!token || !isMentor) {
      setLoadingMentees(false);
      return;
    }
    setLoadingMentees(true);
    setMenteesError(null);
    try {
      const data = await apiFetch<MentorshipMentee[]>('/academy/mentorship/my-mentees', { token, cache: 'no-store', signal });
      if (!signal?.aborted) setMentees(Array.isArray(data) ? data : []);
    } catch (error: unknown) {
      if (!signal?.aborted) {
        if (error instanceof ApiError && error.status === 403) {
          setMentees([]);
        } else {
          const message = extractErrorMessage(error, 'No pudimos cargar tus mentorizados');
          setMenteesError(message);
          toast.error(message);
        }
      }
    } finally {
      if (!signal?.aborted) setLoadingMentees(false);
    }
  }, [isMentor, token]);

  useEffect(() => {
    if (!isAuthenticated || !token) {
      setLoadingMentors(false);
      setLoadingRequests(false);
      return undefined;
    }
    const controller = new AbortController();
    void loadMentors(controller.signal);
    void loadRequests(controller.signal);
    void loadMentees(controller.signal);
    return () => controller.abort();
  }, [isAuthenticated, loadMentees, loadMentors, loadRequests, token]);

  const tabs: { id: MentorshipTab; label: string; icon: typeof Search }[] = [
    { id: 'mentors', label: 'Buscar Mentor', icon: Search },
    { id: 'requests', label: 'Mis Solicitudes', icon: HeartHandshake },
    ...(isMentor ? [{ id: 'mentees' as const, label: 'Mis Mentorizados', icon: UsersRound }] : []),
  ];

  const handleRequested = async () => {
    await loadRequests();
    setActiveTab('requests');
  };

  return (
    <div className="min-h-full bg-[hsl(var(--bg-primary))] text-[hsl(var(--text-primary))]">
      <header className="border-b border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-4 py-5 sm:px-6">
        <div className="mx-auto flex w-full max-w-7xl items-center gap-3">
          <span className="grid size-12 shrink-0 place-items-center rounded-xl bg-[hsl(var(--primary)/0.12)] text-[hsl(var(--primary))]"><GraduationCap className="size-6" /></span>
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-wider text-[hsl(var(--primary))]">Acompañamiento académico</p>
            <h1 className="mt-1 text-xl font-bold sm:text-2xl">Mentoría</h1>
            <p className="mt-1 text-sm text-[hsl(var(--text-secondary))]">Conecta con mentores y da seguimiento a tu acompañamiento.</p>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-7xl space-y-5 px-4 py-5 sm:px-6">
        <nav className="flex gap-2 overflow-x-auto border-b border-[hsl(var(--border))] pb-3" aria-label="Secciones de mentoría">
          {tabs.map(({ id, label, icon: Icon }) => (
            <button key={id} type="button" onClick={() => setActiveTab(id)} aria-current={activeTab === id ? 'page' : undefined}
              className={clsx('inline-flex shrink-0 items-center gap-2 rounded-lg border px-3 py-2 text-sm font-semibold transition-colors', activeTab === id ? 'border-[hsl(var(--primary))] bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]' : 'border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))]')}>
              <Icon className="size-4" />{label}
            </button>
          ))}
        </nav>

        {activeTab === 'mentors' && (
          <section aria-labelledby="available-mentors-title">
            <h2 id="available-mentors-title" className="sr-only">Mentores disponibles</h2>
            {loadingMentors ? (
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3"><DSSkeleton className="h-56 rounded-xl" /><DSSkeleton className="h-56 rounded-xl" /><DSSkeleton className="h-56 rounded-xl" /></div>
            ) : mentorsError ? (
              <ErrorMessage message={mentorsError} />
            ) : mentors.length === 0 ? (
              <EmptyState title="No hay mentores disponibles" description="Cuando haya mentores disponibles para acompañarte, aparecerán aquí." icon={GraduationCap} />
            ) : (
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
                {mentors.map((mentor) => {
                  const expertise = displayList(mentor.expertise);
                  const availability = displayList(mentor.availability);
                  return (
                    <article key={mentor.id} className="flex min-w-0 flex-col justify-between rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4 shadow-sm">
                      <div>
                        <div className="flex items-center gap-3">
                          <span className="grid size-11 shrink-0 place-items-center rounded-full bg-[hsl(var(--primary)/0.12)] text-[hsl(var(--primary))]"><GraduationCap className="size-5" /></span>
                          <div className="min-w-0"><h3 className="truncate font-bold">{mentorName(mentor)}</h3><p className="text-xs text-[hsl(var(--text-secondary))]">Mentor académico</p></div>
                        </div>
                        {(mentor.bio || mentor.description) && <p className="mt-3 line-clamp-3 text-sm text-[hsl(var(--text-secondary))]">{mentor.bio ?? mentor.description}</p>}
                        <div className="mt-4">
                          <p className="text-xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Áreas de experiencia</p>
                          <div className="mt-2 flex flex-wrap gap-1.5">{expertise.length > 0 ? expertise.map((item) => <span key={item} className="rounded-full bg-[hsl(var(--surface-2))] px-2.5 py-1 text-xs">{item}</span>) : <span className="text-xs text-[hsl(var(--text-secondary))]">Información no disponible</span>}</div>
                        </div>
                        <div className="mt-4 flex items-start gap-2 text-xs text-[hsl(var(--text-secondary))]"><CalendarDays className="mt-0.5 size-3.5 shrink-0 text-[hsl(var(--primary))]" /><span>{mentor.availability_summary ?? (availability.length > 0 ? availability.join(' · ') : 'Consulta disponibilidad al solicitar')}</span></div>
                      </div>
                      <DSButton onClick={() => setSelectedMentor(mentor)} className="mt-5 inline-flex items-center justify-center gap-2"><HeartHandshake className="size-4" /> Solicitar</DSButton>
                    </article>
                  );
                })}
              </div>
            )}
          </section>
        )}

        {activeTab === 'requests' && (
          <section aria-label="Mis solicitudes de mentoría">
            {loadingRequests ? (
              <div className="space-y-3"><DSSkeleton className="h-24 rounded-xl" /><DSSkeleton className="h-24 rounded-xl" /></div>
            ) : requestsError ? (
              <ErrorMessage message={requestsError} />
            ) : requests.length === 0 ? (
              <EmptyState title="No tienes solicitudes de mentoría" description="Busca un mentor y envía una solicitud para iniciar." icon={HeartHandshake} />
            ) : (
              <div className="space-y-3">
                {requests.map((request) => (
                  <article key={request.id} className="flex flex-wrap items-start justify-between gap-3 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4">
                    <div className="min-w-0"><h3 className="font-semibold">{request.mentor_name ?? 'Solicitud de mentoría'}</h3>{request.message && <p className="mt-1 break-words text-sm text-[hsl(var(--text-secondary))]">{request.message}</p>}<p className="mt-2 text-xs text-[hsl(var(--text-secondary))]">Enviada: {formatDate(request.requested_at ?? request.created_at)}</p></div>
                    <span className={clsx('rounded-full border px-3 py-1 text-xs font-semibold', statusClass(request.status))}>{statusLabel(request.status)}</span>
                  </article>
                ))}
              </div>
            )}
          </section>
        )}

        {activeTab === 'mentees' && isMentor && (
          <section aria-label="Mis mentorizados">
            {loadingMentees ? (
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2"><DSSkeleton className="h-28 rounded-xl" /><DSSkeleton className="h-28 rounded-xl" /></div>
            ) : menteesError ? (
              <ErrorMessage message={menteesError} />
            ) : mentees.length === 0 ? (
              <EmptyState title="Aún no tienes mentorizados" description="Cuando se te asignen estudiantes, podrás dar seguimiento desde esta sección." icon={UsersRound} />
            ) : (
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
                {mentees.map((mentee) => <article key={mentee.id} className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4"><h3 className="font-semibold">{mentee.mentee_name}</h3>{mentee.status && <span className={clsx('mt-2 inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold', statusClass(mentee.status))}>{statusLabel(mentee.status)}</span>}{mentee.goals && mentee.goals.length > 0 && <p className="mt-3 text-sm text-[hsl(var(--text-secondary))]">Objetivos: {mentee.goals.join(', ')}</p>}</article>)}
              </div>
            )}
          </section>
        )}
      </main>

      <MentorshipRequestDrawer
        open={Boolean(selectedMentor)}
        onClose={() => setSelectedMentor(null)}
        mentor={selectedMentor}
        token={token}
        onRequested={handleRequested}
      />
    </div>
  );
}

function formatDate(value?: string | null): string {
  if (!value) return 'Fecha no disponible';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Fecha no disponible' : date.toLocaleDateString('es');
}

function ErrorMessage({ message }: { message: string }) {
  return <p role="alert" className="rounded-lg border border-[hsl(var(--destructive)/0.3)] bg-[hsl(var(--destructive)/0.05)] p-3 text-sm text-[hsl(var(--destructive))]">{message}</p>;
}
