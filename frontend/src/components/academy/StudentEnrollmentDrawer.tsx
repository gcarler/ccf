"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { RightPanel } from '@/components/ui/RightPanel';
import { apiFetch } from '@/lib/http';
import { toast } from 'sonner';
import { PeriodOffering, StudentEnrollment } from '@/types/academy';
import { Users, UserPlus, Trash2, Search, Loader2, BookOpen } from 'lucide-react';

interface StudentEnrollmentDrawerProps {
  open: boolean;
  onClose: () => void;
  offering: PeriodOffering | null;
  token: string | null;
  onEnrollmentChanged?: () => void;
}

export default function StudentEnrollmentDrawer({
  open,
  onClose,
  offering,
  token,
  onEnrollmentChanged,
}: StudentEnrollmentDrawerProps) {
  const [enrollments, setEnrollments] = useState<StudentEnrollment[]>([]);
  const [loading, setLoading] = useState(false);
  const [personaIdInput, setPersonaIdInput] = useState('');
  const [enrolling, setEnrolling] = useState(false);
  const [removingId, setRemovingId] = useState<string | null>(null);

  const fetchEnrollments = useCallback(async () => {
    if (!offering || !token) return;
    setLoading(true);
    try {
      const data = await apiFetch<StudentEnrollment[]>(
        `/academy/admin/offerings/${offering.id}/students`,
        { token }
      );
      setEnrollments(data || []);
    } catch {
      toast.error('Error al cargar la lista de estudiantes inscritos');
    } finally {
      setLoading(false);
    }
  }, [offering, token]);

  useEffect(() => {
    if (open && offering) {
      fetchEnrollments();
      setPersonaIdInput('');
    }
  }, [open, offering, fetchEnrollments]);

  const handleEnroll = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!offering || !token || !personaIdInput.trim()) return;

    setEnrolling(true);
    try {
      await apiFetch(`/academy/admin/offerings/${offering.id}/students`, {
        method: 'POST',
        token,
        body: JSON.stringify({ persona_id: personaIdInput.trim() }),
      });
      toast.success('Estudiante matriculado con éxito');
      setPersonaIdInput('');
      fetchEnrollments();
      onEnrollmentChanged?.();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Error al matricular estudiante';
      toast.error(msg);
    } finally {
      setEnrolling(false);
    }
  };

  const handleWithdraw = async (personaId: string) => {
    if (!offering || !token) return;
    setRemovingId(personaId);
    try {
      await apiFetch(`/academy/admin/offerings/${offering.id}/students/${personaId}`, {
        method: 'DELETE',
        token,
      });
      toast.success('Estudiante retirado de la comisión');
      fetchEnrollments();
      onEnrollmentChanged?.();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Error al retirar estudiante';
      toast.error(msg);
    } finally {
      setRemovingId(null);
    }
  };

  return (
    <RightPanel
      open={open}
      onClose={onClose}
      title="Matrícula de Estudiantes"
      subtitle={offering ? `${offering.subject_name || 'Comisión'} - ${offering.group_name}` : ''}
      width={560}
    >
      <div className="space-y-6 p-6">
        {/* Offering info card */}
        {offering && (
          <div className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-4 text-xs space-y-1">
            <div className="flex items-center gap-2 font-semibold text-[hsl(var(--foreground))]">
              <BookOpen className="h-4 w-4 text-[hsl(var(--primary))]" />
              <span>{offering.subject_name} ({offering.subject_code})</span>
            </div>
            <div className="text-[hsl(var(--muted-foreground))] flex gap-4 pt-1">
              <span>Período: <strong>{offering.period_code || 'Activo'}</strong></span>
              <span>Créditos: <strong>{offering.credits}</strong></span>
              <span>Cupo: <strong>{enrollments.length} / {offering.quota_max}</strong></span>
            </div>
          </div>
        )}

        {/* Enrollment Form */}
        <form onSubmit={handleEnroll} className="space-y-3">
          <label className="text-xs font-semibold uppercase tracking-wider text-[hsl(var(--foreground))] flex items-center gap-1.5">
            <UserPlus className="h-3.5 w-3.5 text-[hsl(var(--primary))]" />
            Matricular Estudiante (UUID de Persona)
          </label>
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[hsl(var(--muted-foreground))]" />
              <input
                type="text"
                placeholder="UUID de la persona (Axioma 1)"
                value={personaIdInput}
                onChange={(e) => setPersonaIdInput(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--foreground))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]"
              />
            </div>
            <button
              type="submit"
              disabled={enrolling || !personaIdInput.trim()}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] text-xs font-semibold transition-opacity disabled:opacity-50 hover:opacity-90"
            >
              {enrolling ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <UserPlus className="h-3.5 w-3.5" />}
              Matricular
            </button>
          </div>
        </form>

        {/* Enrolled list */}
        <div className="space-y-3">
          <div className="flex items-center justify-between border-b border-[hsl(var(--border))] pb-2">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-[hsl(var(--foreground))] flex items-center gap-1.5">
              <Users className="h-3.5 w-3.5 text-[hsl(var(--primary))]" />
              Estudiantes Matriculados ({enrollments.length})
            </h4>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-12 text-[hsl(var(--muted-foreground))]">
              <Loader2 className="h-6 w-6 animate-spin" />
            </div>
          ) : enrollments.length === 0 ? (
            <div className="rounded-xl border border-dashed border-[hsl(var(--border))] p-8 text-center text-xs text-[hsl(var(--muted-foreground))]">
              No hay estudiantes inscritos en esta comisión aún.
            </div>
          ) : (
            <div className="divide-y divide-[hsl(var(--border))] rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] overflow-hidden">
              {enrollments.map((enr) => (
                <div key={enr.id} className="flex items-center justify-between p-3 text-xs hover:bg-[hsl(var(--surface-2))] transition-colors">
                  <div className="space-y-0.5">
                    <p className="font-semibold text-[hsl(var(--foreground))]">
                      {enr.student_name || 'Estudiante'}
                    </p>
                    <p className="font-mono text-[10px] text-[hsl(var(--muted-foreground))]">
                      {enr.persona_id}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="rounded-full px-2 py-0.5 text-[10px] font-semibold bg-[hsl(var(--primary)/0.15)] text-[hsl(var(--primary))]">
                      {enr.status}
                    </span>
                    <button
                      type="button"
                      disabled={removingId === enr.persona_id}
                      onClick={() => handleWithdraw(enr.persona_id)}
                      className="p-1 rounded text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--destructive))] transition-colors"
                      title="Retirar estudiante"
                    >
                      {removingId === enr.persona_id ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <Trash2 className="h-3.5 w-3.5" />
                      )}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </RightPanel>
  );
}
